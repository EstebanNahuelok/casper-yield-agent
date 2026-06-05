import structlog

from ..config import settings
from ..mcp_clients.casper_client import CasperMCPClient
from ..state.models import Decision

log = structlog.get_logger()


class ChainExecutor:
    """Ejecuta decisiones del agente on-chain vía el contrato YieldVault."""

    def __init__(self, casper_client: CasperMCPClient):
        self._casper = casper_client

    async def execute_swap(self, decision: Decision) -> str:
        """Llama a execute_swap en el contrato YieldVault. Devuelve el deploy hash."""
        log.info(
            "chain.execute_swap",
            amount=decision.amount,
            token_in=decision.token_in,
            token_out=decision.token_out,
        )
        result = await self._casper.call_contract(
            contract_hash=settings.vault_contract_hash,
            entry_point="execute_swap",
            args={
                "amount": str(int(decision.amount * 1_000_000_000)),  # motes
                "token_in": decision.token_in,
                "token_out": decision.token_out,
            },
        )
        deploy_hash = result.get("deployHash") or result.get("deploy_hash", "unknown")
        log.info("chain.swap_submitted", deploy_hash=deploy_hash)
        return deploy_hash

    async def log_action(self, decision: Decision, deploy_hash: str | None = None) -> None:
        """Loguea la decisión on-chain en el contrato YieldVault."""
        log.info("chain.log_action", action=decision.action, deploy_hash=deploy_hash)
        await self._casper.call_contract(
            contract_hash=settings.vault_contract_hash,
            entry_point="log_action",
            args={
                "action": decision.action.value,
                "reasoning": decision.reasoning[:256],  # límite de string on-chain
                "deploy_hash": deploy_hash or "",
            },
        )
