import asyncio
import json
from datetime import datetime, timezone

import structlog

from .chain.executor import ChainExecutor
from .config import settings
from .llm.swarm import SwarmDecisionEngine
from .mcp_clients.casper_client import CasperMCPClient, MCPConnectionError
from .mcp_clients.trade_client import CSPRTradeRestClient, TradeClientError
from .state.models import Action, Decision, MarketData
from .state.store import state_store

log = structlog.get_logger()

MCP_RETRY_INTERVAL = 30  # segundos entre intentos de reconexión al Casper MCP local


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

    - balance: total_locked del contrato vault via Casper RPC (named key → URef → U512)
    - apy: estimado desde la ratio de reserves del par WCSPR/sCSPR en api.cspr.trade
    - slippage: calculado con la fórmula AMM (x*y=k, 0.3% fee) para el 50% del balance
    """
    balance = await casper.get_vault_total_locked()

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
        timestamp=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Ciclo de decisión
# ---------------------------------------------------------------------------

async def _run_cycle(
    casper: CasperMCPClient,
    trade: CSPRTradeRestClient,
    llm: SwarmDecisionEngine,
    executor: ChainExecutor,
) -> None:
    # 1. Observar
    await state_store.update_status("observing")
    market = await _collect_market_data(casper, trade)

    if market.balance_cspr == 0.0:
        log.warning("agent.skip_cycle", reason="balance=0.0 (RPC fallido), reintentando en el próximo ciclo")
        await state_store.record_error("Balance no disponible (RPC error) — ciclo saltado")
        return

    await state_store.update_market_data(market)
    log.info(
        "agent.market_data",
        balance_cspr=round(market.balance_cspr, 4),
        current_apy=market.current_apy,
        pool_apy=market.pool_apy,
        slippage=market.estimated_slippage,
    )

    # 2. Decidir con el enjambre
    await state_store.update_status("deciding")
    market_summary = json.dumps(market.model_dump(), default=str, ensure_ascii=False)
    decision, votes = await llm.decide_with_votes(market_summary)
    log.info("agent.decision", action=decision.action, reasoning=decision.reasoning)

    # 2b. Completar amount_out con la quote real del AMM (necesario para execute_swap)
    if decision.action == Action.SWAP and decision.amount:
        quote = await trade.get_quote(decision.amount)
        decision.amount_out = quote.get("amount_out", 0.0)

    # 2c. Si el enjambre vota HOLD pero hay sCSPR en el vault, exit position (SWAP_BACK)
    if decision.action == Action.HOLD:
        current_state = await state_store.get()
        scspr_held = current_state.scspr_balance_cspr
        if scspr_held > 0:
            decision = Decision(
                action=Action.SWAP_BACK,
                reasoning=(
                    f"Exiting sCSPR position ({scspr_held:.4f} sCSPR held): swarm voted HOLD "
                    f"indicating unfavorable conditions to maintain position. "
                    f"Original reasoning: {decision.reasoning}"
                ),
                amount=scspr_held,
                token_in="sCSPR",
                token_out="CSPR",
            )
            log.info("agent.swap_back_triggered", scspr_held=scspr_held)

    # 3. Ejecutar si corresponde
    deploy_hash: str | None = None
    if decision.action in (Action.SWAP, Action.SWAP_BACK):
        await state_store.update_status("executing")
        deploy_hash = await executor.execute_swap(decision)
        log.info("agent.swap_done", action=decision.action, deploy_hash=deploy_hash)

    # 4. Loguear on-chain siempre (auditable por el jurado)
    try:
        await executor.log_action(decision, deploy_hash)
    except Exception as log_exc:
        log.warning("agent.log_action_failed", error=str(log_exc))

    # 5. Actualizar estado para el frontend
    await state_store.record_decision(decision, deploy_hash, swarm_votes=votes)


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------

async def agent_loop() -> None:
    casper = CasperMCPClient()
    trade = CSPRTradeRestClient()   # stateless REST, no necesita connect()
    llm = SwarmDecisionEngine()

    log.info("agent.starting", check_interval=settings.check_interval_seconds)
    await state_store.update_status("connecting")

    # Espera activa hasta que el Casper MCP local esté disponible
    await _connect_with_retry(casper)

    executor = ChainExecutor()

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
