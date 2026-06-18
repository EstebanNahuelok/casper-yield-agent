import json

import structlog

from ..config import settings
from ..state.models import Decision
from .node_tx import submit_contract_call

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
    """Ejecuta decisiones del agente on-chain vía el contrato YieldVault (TransactionV1)."""

    async def execute_swap(self, decision: Decision) -> str:
        """
        Llama a execute_swap(token_in, token_out, amount_in, amount_out).
        Devuelve el tx hash.
        """
        amount_in_motes = int(decision.amount * 1_000_000_000)
        amount_out_motes = int((decision.amount_out or 0.0) * 1_000_000_000)
        log.info(
            "chain.execute_swap",
            amount_in=decision.amount,
            amount_out=decision.amount_out,
            token_in=decision.token_in,
            token_out=decision.token_out,
        )

        tx_hash = await submit_contract_call(
            contract_package_hash=settings.vault_package_hash,
            entry_point="execute_swap",
            args=[
                ("token_in",  "CLString",  decision.token_in),
                ("token_out", "CLString",  decision.token_out),
                ("amount_in",  "CLUInt512", str(amount_in_motes)),
                ("amount_out", "CLUInt512", str(amount_out_motes)),
            ],
        )
        log.info("chain.swap_submitted", tx_hash=tx_hash)
        return tx_hash

    async def log_action(self, decision: Decision, deploy_hash: str | None = None) -> None:
        """
        Loguea la decisión on-chain vía log_action(action_type, params).
        `params` incluye reasoning + deploy_hash serializados como JSON.
        """
        params = _build_log_params(decision.reasoning, deploy_hash)
        log.info("chain.log_action", action=decision.action, deploy_hash=deploy_hash)

        await submit_contract_call(
            contract_package_hash=settings.vault_package_hash,
            entry_point="log_action",
            args=[
                ("action_type", "CLString", decision.action.value),
                ("params",      "CLString", params),
            ],
        )
