import structlog

from ..config import settings
from ..mcp_clients.casper_client import CasperMCPClient
from ..state.models import Decision

log = structlog.get_logger()


class ChainExecutor:
    """Ejecuta decisiones del agente on-chain vía el contrato YieldVault."""

    def __init__(self, casper_client: CasperMCPClient):
        self._casper = casper_client

    async def initialize_contract(self) -> None:
        """
        Llama a init firmado con la owner key para registrar el agente en el contrato.

        Se llama una vez en el startup del agente. Si el contrato ya fue
        inicializado, el error se loguea y la ejecución continúa normalmente.
        """
        log.info(
            "chain.init",
            contract=settings.vault_contract_hash,
            owner=settings.vault_owner_public_key,
            agent=settings.vault_public_key,
        )
        try:
            await self._casper.call_contract(
                contract_hash=settings.vault_contract_hash,
                entry_point="init",
                args={"agent": settings.vault_public_key},
                secret_key=settings.vault_owner_secret_key,
            )
            log.info("chain.init_ok")
        except Exception as exc:
            log.warning("chain.init_skipped", reason=str(exc))

    async def execute_swap(self, decision: Decision) -> str:
        """
        Llama a execute_swap firmado con la agent key. Devuelve el deploy hash.

        El contrato valida que msg.sender sea el agente registrado en init.
        """
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
                "amount": str(int(decision.amount * 1_000_000_000)),  # CSPR → motes
                "token_in": decision.token_in,
                "token_out": decision.token_out,
            },
            # secret_key omitido → usa settings.vault_owner_secret_key
        )
        deploy_hash = result.get("deployHash") or result.get("deploy_hash", "unknown")
        log.info("chain.swap_submitted", deploy_hash=deploy_hash)
        return deploy_hash

    async def log_action(self, decision: Decision, deploy_hash: str | None = None) -> None:
        """
        Loguea la decisión on-chain firmado con la agent key.

        El contrato valida que msg.sender sea el agente registrado en init.
        """
        log.info("chain.log_action", action=decision.action, deploy_hash=deploy_hash)
        await self._casper.call_contract(
            contract_hash=settings.vault_contract_hash,
            entry_point="log_action",
            args={
                "action": decision.action.value,
                "reasoning": decision.reasoning[:256],  # límite de string on-chain
                "deploy_hash": deploy_hash or "",
            },
            # secret_key omitido → usa settings.vault_owner_secret_key
        )
