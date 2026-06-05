"""
Cliente REST para https://api.cspr.trade

Reemplaza al cliente MCP de CSPR.trade (que devuelve 405).
Endpoints utilizados:
  GET /pairs   → reserves actuales del par WCSPR/sCSPR
  GET /swaps   → historial de swaps (no usado actualmente)

Cálculo de quotes: fórmula AMM x*y=k con 0.3% de fee (igual que Uniswap v2).
Cálculo de APY: ratio reserve0/reserve1 anualizado desde la fecha de creación del par.
"""

from datetime import datetime, timezone

import httpx
import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ..config import settings

log = structlog.get_logger()

API_BASE = "https://api.cspr.trade"

# Hashes confirmados consultando GET /tokens y GET /pairs
WCSPR_HASH = "8df5d26790e18cf0404502c62ce5dc9025800ad6975c97466e20506c39c505b6"
SCSPR_HASH = "a4f6d5e6ce046b7e8e32356b1395b69573ba2481fc86b85f9183f149366b60f1"
# Par WCSPR(token0) / sCSPR(token1) — el de mayor liquidez
WCSPR_SCSPR_PAIR_HASH = "99227bb4082ce12f9198651c7eec88dbdb290030da1dfe17cef487bd7d2fe68b"
PAIR_CREATED_AT = datetime(2026, 1, 29, 17, 30, 28, tzinfo=timezone.utc)

# AMM fee: 0.3% → numerador 997, denominador 1000
AMM_FEE_NUMERATOR = 997
AMM_FEE_DENOMINATOR = 1000

_RETRYABLE = (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError)


class TradeClientError(Exception):
    """Error al comunicarse con api.cspr.trade."""


class CSPRTradeRestClient:
    """
    Cliente REST para api.cspr.trade.

    No requiere API key ni sesión MCP. Stateless: cada llamada es un GET
    independiente con reintento automático ante fallos de red.
    """

    def __init__(self):
        self._http = httpx.AsyncClient(
            base_url=API_BASE,
            timeout=15.0,
            headers={"Accept": "application/json"},
        )

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=8),
        reraise=True,
    )
    async def _get(self, path: str, params: dict | None = None) -> dict:
        try:
            r = await self._http.get(path, params=params)
            r.raise_for_status()
        except _RETRYABLE:
            raise
        except httpx.HTTPStatusError as exc:
            raise TradeClientError(
                f"api.cspr.trade {exc.response.status_code} en {path}: {exc.response.text[:200]}"
            ) from exc
        return r.json()

    async def get_pair_reserves(self) -> tuple[int, int, datetime]:
        """
        Devuelve (reserve_wcspr_motes, reserve_scspr_motes, pair_timestamp).
        reserve0 = WCSPR (token0), reserve1 = sCSPR (token1).
        """
        data = await self._get(
            "/pairs",
            params={"token1ContractPackageHash": SCSPR_HASH, "page_size": 20},
        )
        for pair in data.get("data", []):
            if pair.get("contract_package_hash") == WCSPR_SCSPR_PAIR_HASH:
                r0 = int(pair.get("reserve0") or 0)
                r1 = int(pair.get("reserve1") or 0)
                ts_str = pair.get("timestamp", PAIR_CREATED_AT.isoformat())
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except ValueError:
                    ts = PAIR_CREATED_AT
                return r0, r1, ts
        raise TradeClientError("Par WCSPR/sCSPR no encontrado en api.cspr.trade")

    def _amm_quote(self, amount_in: int, reserve_in: int, reserve_out: int) -> dict:
        """
        Fórmula AMM x*y=k con 0.3% de fee.
        Devuelve amount_out exacto y price_impact_pct.
        """
        if reserve_in <= 0 or reserve_out <= 0 or amount_in <= 0:
            return {"amount_out_motes": 0, "amount_out": 0.0, "price_impact_pct": 0.0, "slippage_pct": 0.0}

        amt_with_fee = amount_in * AMM_FEE_NUMERATOR
        amount_out = (reserve_out * amt_with_fee) // (reserve_in * AMM_FEE_DENOMINATOR + amt_with_fee)

        spot_rate = reserve_out / reserve_in            # sCSPR por WCSPR al precio de mercado
        exec_rate = amount_out / amount_in              # sCSPR por WCSPR en esta operación
        price_impact = max(0.0, (1 - exec_rate / spot_rate) * 100) if spot_rate > 0 else 0.0

        return {
            "amount_out_motes": int(amount_out),
            "amount_out": amount_out / 1e9,
            "spot_rate": round(spot_rate, 8),
            "exec_rate": round(exec_rate, 8),
            "price_impact_pct": round(price_impact, 4),
            "slippage_pct": round(price_impact, 4),
        }

    async def get_quote(self, amount_cspr: float) -> dict:
        """
        Quote exacto para CSPR → sCSPR usando reserves del AMM.
        amount_cspr: cantidad en CSPR (human-readable, no motes).
        """
        r0, r1, _ = await self.get_pair_reserves()
        amount_in_motes = int(amount_cspr * 1e9)
        quote = self._amm_quote(amount_in_motes, r0, r1)
        log.debug("trade_rest.quote", amount_cspr=amount_cspr, **quote)
        return quote

    async def estimate_scspr_apy(self) -> float:
        """
        Estima el APY de sCSPR a partir de la ratio de reserves.

        sCSPR es un liquid staking token que empieza 1:1 con WCSPR y va
        apreciándose a medida que acumula rewards de staking.
        ratio = reserve_wcspr / reserve_scspr → yield total acumulado desde creación.
        Lo anualizamos dividiendo por los meses transcurridos × 12.
        """
        r0, r1, _ = await self.get_pair_reserves()
        if r1 <= 0:
            return 12.0  # fallback: APY base de staking en Casper

        ratio = r0 / r1  # WCSPR por sCSPR (> 1 si sCSPR se apreció)
        total_yield_pct = max(0.0, ratio - 1.0) * 100

        months_elapsed = max(
            1.0,
            (datetime.now(timezone.utc) - PAIR_CREATED_AT).days / 30.44,
        )
        apy = total_yield_pct * (12.0 / months_elapsed)
        log.debug(
            "trade_rest.apy",
            ratio=round(ratio, 6),
            total_yield_pct=round(total_yield_pct, 4),
            months_elapsed=round(months_elapsed, 1),
            apy=round(apy, 2),
        )
        return round(apy, 2)

    async def close(self) -> None:
        await self._http.aclose()
