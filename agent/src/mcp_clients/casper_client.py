import asyncio
from contextlib import AsyncExitStack

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

    async def call_contract(
        self,
        contract_hash: str,
        entry_point: str,
        args: dict,
        secret_key: str | None = None,
    ) -> dict:
        return await self._call(
            "CallContract",
            {
                "contractHash": contract_hash,
                "entryPoint": entry_point,
                "args": args,
                "secretKey": secret_key or settings.vault_owner_secret_key,
                "network": settings.casper_network,
            },
        )
