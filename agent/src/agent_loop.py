import asyncio
import json
from datetime import datetime

import structlog

from .chain.executor import ChainExecutor
from .config import settings
from .llm.groq import GroqDecisionEngine
from .mcp_clients.casper_client import CasperMCPClient, MCPConnectionError
from .mcp_clients.trade_client import CSPRTradeRestClient, TradeClientError
from .state.models import Action, MarketData
from .state.store import state_store

log = structlog.get_logger()

MCP_RETRY_INTERVAL = 30  # segundos entre intentos de reconexión al Casper MCP local


# ---------------------------------------------------------------------------
# Helpers de parseo de la respuesta del Casper MCP
# ---------------------------------------------------------------------------

def _parse_balance(raw) -> float:
    """Balance en motes → CSPR. Tolera dict con 'balance', int, o float."""
    if isinstance(raw, (int, float)):
        return float(raw) / 1_000_000_000
    if isinstance(raw, dict):
        motes = raw.get("balance") or raw.get("data", {}).get("balance", 0)
        return float(motes) / 1_000_000_000
    return 0.0


# ---------------------------------------------------------------------------
# Conexión con reintento (solo para el Casper MCP local)
# ---------------------------------------------------------------------------

async def _connect_with_retry(casper: CasperMCPClient) -> None:
    """
    Intenta conectar al Casper MCP Server indefinidamente.
    Espera MCP_RETRY_INTERVAL segundos entre intentos.
    El loop no arranca hasta que haya conexión.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            await casper.connect()
            log.info("casper_mcp.ready", attempt=attempt)
            return
        except MCPConnectionError as exc:
            log.warning(
                "casper_mcp.unavailable",
                attempt=attempt,
                retry_in=MCP_RETRY_INTERVAL,
                error=str(exc),
            )
            await state_store.update_status(
                f"waiting_mcp (intento {attempt}, reintentando en {MCP_RETRY_INTERVAL}s)"
            )
            await state_store.record_error(str(exc))
            await asyncio.sleep(MCP_RETRY_INTERVAL)


# ---------------------------------------------------------------------------
# Recolección de datos de mercado
# ---------------------------------------------------------------------------

async def _collect_market_data(
    casper: CasperMCPClient,
    trade: CSPRTradeRestClient,
) -> MarketData:
    """
    Recolecta todos los datos necesarios para la decisión del ciclo.

    - balance: Casper MCP local (en motes → CSPR)
    - apy: estimado desde la ratio de reserves del par WCSPR/sCSPR en api.cspr.trade
    - slippage: calculado con la fórmula AMM (x*y=k, 0.3% fee) para el 50% del balance
    """
    balance_raw = await casper.get_account_balance()
    balance = _parse_balance(balance_raw)

    # APY de sCSPR anualizado desde la ratio de reserves (stateless REST)
    pool_apy = await trade.estimate_scspr_apy()
    # current_apy: tomamos el mismo valor (no hay otra fuente de APY actual)
    current_apy = pool_apy

    # Slippage exacto para el 50% del balance disponible
    swap_amount_cspr = max(1.0, balance * 0.5)
    quote = await trade.get_quote(swap_amount_cspr)
    slippage = quote.get("slippage_pct", 0.0)

    # Precio USD de CSPR: quote de 1 CSPR (rate spot, no usamos para la decisión)
    spot_quote = await trade.get_quote(1.0)
    cspr_price_usd = spot_quote.get("spot_rate", 0.0)

    return MarketData(
        balance_cspr=balance,
        current_apy=current_apy,
        pool_apy=pool_apy,
        estimated_slippage=slippage,
        cspr_price_usd=cspr_price_usd,
        timestamp=datetime.utcnow(),
    )


# ---------------------------------------------------------------------------
# Ciclo de decisión
# ---------------------------------------------------------------------------

async def _run_cycle(
    casper: CasperMCPClient,
    trade: CSPRTradeRestClient,
    llm: GroqDecisionEngine,
    executor: ChainExecutor,
) -> None:
    # 1. Observar
    await state_store.update_status("observing")
    market = await _collect_market_data(casper, trade)
    await state_store.update_market_data(market)
    log.info(
        "agent.market_data",
        balance_cspr=round(market.balance_cspr, 4),
        current_apy=market.current_apy,
        pool_apy=market.pool_apy,
        slippage=market.estimated_slippage,
    )

    # 2. Decidir con Gemini
    await state_store.update_status("deciding")
    market_summary = json.dumps(market.model_dump(), default=str, ensure_ascii=False)
    decision = await llm.decide(market_summary)
    log.info("agent.decision", action=decision.action, reasoning=decision.reasoning)

    # 3. Ejecutar si corresponde
    deploy_hash: str | None = None
    if decision.action == Action.SWAP:
        await state_store.update_status("executing")
        deploy_hash = await executor.execute_swap(decision)
        log.info("agent.swap_done", deploy_hash=deploy_hash)

    # 4. Loguear on-chain siempre (auditable por el jurado)
    await executor.log_action(decision, deploy_hash)

    # 5. Actualizar estado para el frontend
    await state_store.record_decision(decision, deploy_hash)


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------

async def agent_loop() -> None:
    casper = CasperMCPClient()
    trade = CSPRTradeRestClient()   # stateless REST, no necesita connect()
    llm = GroqDecisionEngine()

    log.info("agent.starting", check_interval=settings.check_interval_seconds)
    await state_store.update_status("connecting")

    # Espera activa hasta que el Casper MCP local esté disponible
    await _connect_with_retry(casper)

    executor = ChainExecutor(casper)
    await state_store.update_status("running")
    log.info("agent.loop_started")

    try:
        while True:
            try:
                await _run_cycle(casper, trade, llm, executor)

            except MCPConnectionError as exc:
                log.warning("agent.mcp_lost", error=str(exc))
                await state_store.record_error(f"MCP desconectado: {exc}")
                await state_store.update_status("reconnecting")
                await _connect_with_retry(casper)
                await state_store.update_status("running")
                continue  # no dormir: ejecutar ciclo inmediatamente tras reconectar

            except TradeClientError as exc:
                # api.cspr.trade tuvo un error transitorio; el próximo ciclo reintenta
                log.error("agent.trade_error", error=str(exc))
                await state_store.record_error(f"CSPR.trade error: {exc}")

            except Exception as exc:
                log.error("agent.cycle_error", error=str(exc), exc_info=True)
                await state_store.record_error(str(exc))

            finally:
                current = await state_store.get()
                if current.status not in ("reconnecting", "waiting_mcp", "stopped"):
                    await state_store.update_status("running")

            await asyncio.sleep(settings.check_interval_seconds)

    except asyncio.CancelledError:
        log.info("agent.cancelled")
    finally:
        await casper.disconnect()
        await trade.close()
        await state_store.update_status("stopped")
        log.info("agent.stopped")
