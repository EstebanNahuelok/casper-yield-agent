import asyncio
from contextlib import AsyncExitStack

import httpx
import structlog
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from ..config import settings

log = structlog.get_logger()

CONNECT_TIMEOUT = 10.0  # segundos

# En modo HTTP el servidor exige estos headers en cada request (RemoteRequestMiddleware).
# X-CSPR-Cloud-Api-Key : la API key de cspr.cloud
# X-Casper-Network     : "mainnet" | "testnet"
def _auth_headers() -> dict[str, str]:
    return {
        "X-CSPR-Cloud-Api-Key": settings.cspr_cloud_api_key,
        "X-Casper-Network": settings.casper_network,
    }


class MCPConnectionError(Exception):
    """El servidor MCP no está disponible o perdió la conexión."""


class CasperMCPClient:
    """
    Cliente para el Casper MCP Server (balance, precios, contratos).

    Usa streamablehttp_client (POST + SSE opcional), NO sse_client (GET SSE).
    El servidor .NET usa WithHttpTransport que espera POST a /mcp — un GET
    devuelve 405 Method Not Allowed.

    El servidor debe arrancarse con --transport http (no --transport sse):
        CasperMcp.exe --transport http --network testnet --port 3001

    La ruta por defecto del servidor es /mcp (no /sse).
    La API key de CSPR.cloud va en el header X-CSPR-Cloud-Api-Key de cada
    request — en modo HTTP no se pasa por CLI, sino por header.
    """

    def __init__(self):
        self._session: ClientSession | None = None
        self._stack: AsyncExitStack | None = None
        self._cached_balance: float | None = None

    @property
    def is_connected(self) -> bool:
        return self._session is not None

    async def connect(self) -> None:
        """
        Intenta conectar al MCP Server. Si falla lanza MCPConnectionError.
        Seguro de llamar múltiples veces: cierra la conexión previa si existe.
        """
        await self.disconnect()

        stack = AsyncExitStack()
        try:
            read, write, _ = await asyncio.wait_for(
                stack.enter_async_context(
                    streamablehttp_client(settings.casper_mcp_url, headers=_auth_headers())
                ),
                timeout=CONNECT_TIMEOUT,
            )
            session: ClientSession = await stack.enter_async_context(
                ClientSession(read, write)
            )
            await asyncio.wait_for(session.initialize(), timeout=CONNECT_TIMEOUT)

            self._session = session
            self._stack = stack
            log.info("casper_mcp.connected", url=settings.casper_mcp_url)

        except Exception as exc:
            await stack.aclose()
            raise MCPConnectionError(
                f"No se pudo conectar a Casper MCP ({settings.casper_mcp_url}): {exc}"
            ) from exc

    async def disconnect(self) -> None:
        if self._stack:
            try:
                await self._stack.aclose()
            except Exception:
                pass
        self._session = None
        self._stack = None
        log.info("casper_mcp.disconnected")

    async def _call(self, tool_name: str, args: dict) -> dict:
        if not self.is_connected:
            raise MCPConnectionError("Cliente no conectado al MCP Server")
        try:
            return await self._session.call_tool(tool_name, args)
        except Exception as exc:
            await self.disconnect()
            raise MCPConnectionError(f"Llamada MCP '{tool_name}' falló: {exc}") from exc

    async def get_account_balance(self) -> dict:
        return await self._call(
            "GetAccountBalance",
            {"publicKey": settings.vault_public_key},
        )

    async def get_ft_rate_latest(self, contract_package_hash: str) -> dict:
        return await self._call(
            "GetFtDexRateLatest",
            {"contractPackageHash": contract_package_hash},
        )

    async def get_recent_swaps(self, limit: int = 10) -> dict:
        return await self._call(
            "GetSwaps",
            {"contractPackageHash": settings.scspr_contract_hash, "count": limit},
        )

    async def get_vault_total_locked(self) -> float:
        """
        Returns the CSPR balance of the vault's __contract_main_purse via Casper RPC.

        Casper 2.x path:
          1. state_get_item(contract_hash) → named_keys → __contract_main_purse URef
          2. query_balance(purse_uref) → motes (U512 string)

        Returns CSPR float (motes / 1e9). On 429 rate-limit, returns last known balance.
        Returns 0.0 only if no prior successful read exists.
        """
        # Intentar primero con nodo público (sin rate limit), luego cspr.cloud como fallback
        rpc_candidates = [
            ("https://rpc.testnet.casperlabs.io", {"Content-Type": "application/json"}, 10.0),
            (
                f"https://node.{settings.casper_network}.cspr.cloud/rpc",
                {"Authorization": settings.cspr_cloud_api_key, "Content-Type": "application/json"},
                15.0,
            ),
        ]

        for rpc_url, auth_headers, timeout in rpc_candidates:
            try:
                async with httpx.AsyncClient(timeout=timeout) as http:
                    # 1. State root hash
                    r = await http.post(rpc_url, headers=auth_headers, json={
                        "jsonrpc": "2.0", "method": "chain_get_state_root_hash",
                        "params": {}, "id": 1,
                    })
                    r.raise_for_status()
                    state_root = r.json()["result"]["state_root_hash"]

                    # 2. Contract entity → __contract_main_purse URef
                    r = await http.post(rpc_url, headers=auth_headers, json={
                        "jsonrpc": "2.0", "method": "state_get_item",
                        "params": {
                            "state_root_hash": state_root,
                            "key": settings.vault_contract_hash,
                            "path": [],
                        }, "id": 2,
                    })
                    r.raise_for_status()
                    named_keys_raw = (
                        r.json()
                        .get("result", {})
                        .get("stored_value", {})
                        .get("Contract", {})
                        .get("named_keys", [])
                    )
                    named_keys = {nk["name"]: nk["key"] for nk in named_keys_raw}
                    purse_uref = named_keys.get("__contract_main_purse")
                    if not purse_uref:
                        log.warning("vault_rpc.no_main_purse", keys=list(named_keys.keys()))
                        return 0.0

                    # 3. Purse balance via Casper 2.x query_balance
                    r = await http.post(rpc_url, headers=auth_headers, json={
                        "jsonrpc": "2.0", "method": "query_balance",
                        "params": {"purse_identifier": {"purse_uref": purse_uref}},
                        "id": 3,
                    })
                    r.raise_for_status()
                    motes = int(r.json()["result"]["balance"])
                    balance = motes / 1_000_000_000
                    self._cached_balance = balance
                    log.info("vault_rpc.balance", motes=motes, cspr=balance, rpc=rpc_url[:30])
                    return balance

            except Exception as exc:
                log.warning("vault_rpc.node_failed", rpc=rpc_url[:30], error=repr(exc)[:120])
                continue

        # Todos los nodos fallaron — usar cache si existe
        if self._cached_balance is not None:
            log.warning("vault_rpc.all_nodes_failed_using_cache", cached_cspr=self._cached_balance)
            return self._cached_balance
        log.warning("vault_rpc.all_nodes_failed", fallback=0.0)
        return 0.0
