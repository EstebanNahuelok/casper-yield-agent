import json

import structlog
from pycspr.types.cl import CLV_String, CLV_U512

from ..config import settings
from ..state.models import Decision
from .pycspr_signer import build_contract_call_deploy, load_owner_private_key, submit_deploy

log = structlog.get_logger()

MAX_PARAMS_LEN = 512  # límite de bytes para `params` en log_action (vault.rs)


def _build_log_params(reasoning: str, deploy_hash: str | None) -> str:
    """Serializa reasoning + deploy_hash como JSON, truncando para no exceder MAX_PARAMS_LEN bytes."""
    payload = {"reasoning": reasoning, "deploy_hash": deploy_hash or ""}
    params = json.dumps(payload, ensure_ascii=False)

    while len(params.encode("utf-8")) > MAX_PARAMS_LEN and payload["reasoning"]:
        payload["reasoning"] = payload["reasoning"][:-1]
        params = json.dumps(payload, ensure_ascii=False)

    return params


class ChainExecutor:
    """Ejecuta decisiones del agente on-chain vía el contrato YieldVault, firmando con pycspr."""

    async def execute_swap(self, decision: Decision) -> str:
        """
        Llama a execute_swap(token_in, token_out, amount_in, amount_out) firmado con la
        owner key. Devuelve el deploy hash.
        """
        amount_in_motes = int(decision.amount * 1_000_000_000)  # CSPR → motes
        amount_out_motes = int((decision.amount_out or 0.0) * 1_000_000_000)
        log.info(
            "chain.execute_swap",
            amount_in=decision.amount,
            amount_out=decision.amount_out,
            token_in=decision.token_in,
            token_out=decision.token_out,
        )

        private_key = load_owner_private_key()
        deploy = build_contract_call_deploy(
            private_key=private_key,
            contract_package_hash=settings.vault_package_hash,
            entry_point="execute_swap",
            args={
                "token_in": CLV_String(decision.token_in),
                "token_out": CLV_String(decision.token_out),
                "amount_in": CLV_U512(amount_in_motes),
                "amount_out": CLV_U512(amount_out_motes),
            },
        )
        deploy_hash = await submit_deploy(deploy)
        log.info("chain.swap_submitted", deploy_hash=deploy_hash)
        return deploy_hash

    async def log_action(self, decision: Decision, deploy_hash: str | None = None) -> None:
        """
        Loguea la decisión on-chain vía log_action(action_type, params), firmado con la
        owner key. `params` incluye reasoning + deploy_hash serializados como JSON.
        """
        params = _build_log_params(decision.reasoning, deploy_hash)
        log.info("chain.log_action", action=decision.action, deploy_hash=deploy_hash)

        private_key = load_owner_private_key()
        deploy = build_contract_call_deploy(
            private_key=private_key,
            contract_package_hash=settings.vault_package_hash,
            entry_point="log_action",
            args={
                "action_type": CLV_String(decision.action.value),
                "params": CLV_String(params),
            },
        )
        await submit_deploy(deploy)
