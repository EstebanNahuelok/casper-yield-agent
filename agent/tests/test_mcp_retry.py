import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.mcp_clients.casper_client import CasperMCPClient, MCPConnectionError
from src.state.store import StateStore


@pytest.mark.asyncio
async def test_connect_raises_mcp_connection_error_on_failure():
    client = CasperMCPClient()
    with patch("src.mcp_clients.casper_client.sse_client") as mock_sse:
        mock_sse.return_value.__aenter__ = AsyncMock(side_effect=ConnectionRefusedError("refused"))
        with pytest.raises(MCPConnectionError):
            await client.connect()


@pytest.mark.asyncio
async def test_call_raises_mcp_connection_error_when_not_connected():
    client = CasperMCPClient()
    # Sin llamar connect(), _session es None
    with pytest.raises(MCPConnectionError, match="no conectado"):
        await client._call("GetAccountBalance", {})


@pytest.mark.asyncio
async def test_connect_with_retry_retries_on_failure():
    """_connect_with_retry debe reintentar y eventualmente conectar."""
    from src.agent_loop import _connect_with_retry
    from src.state.store import StateStore

    # Parchear state_store para aislar el test
    store = StateStore()
    call_count = 0

    async def fake_connect():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise MCPConnectionError("server not ready")

    client = CasperMCPClient()
    client.connect = fake_connect

    with (
        patch("src.agent_loop.state_store", store),
        patch("src.agent_loop.MCP_RETRY_INTERVAL", 0),  # sin sleep en tests
    ):
        await _connect_with_retry(client)

    assert call_count == 3
