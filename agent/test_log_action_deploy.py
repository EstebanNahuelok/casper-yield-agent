"""
Script temporal: construye (y firma) el deploy de
`log_action(action_type: String, params: String)` para el YieldVault usando
pycspr_signer, sin enviarlo todavía.

`params` se serializa como JSON string (reasoning + deploy_hash), respetando
MAX_PARAMS_LEN = 512 bytes (vault.rs).
"""

import json

from pycspr.types.cl import CLV_String

from src.chain.pycspr_signer import build_contract_call_deploy, load_owner_private_key

CONTRACT_PACKAGE_HASH = "a44b0f0f83462cdc10172a0576ec760363fc1f25ca6dd92da9df1e2200a78c88"

MAX_PARAMS_LEN = 512  # vault.rs


def _build_params(reasoning: str, deploy_hash: str | None) -> str:
    """
    Serializa reasoning + deploy_hash como JSON string para `params`, truncando
    `reasoning` si es necesario para no exceder MAX_PARAMS_LEN bytes en UTF-8.
    """
    payload = {"reasoning": reasoning, "deploy_hash": deploy_hash or ""}
    params = json.dumps(payload, ensure_ascii=False)

    while len(params.encode("utf-8")) > MAX_PARAMS_LEN and payload["reasoning"]:
        payload["reasoning"] = payload["reasoning"][:-1]
        params = json.dumps(payload, ensure_ascii=False)

    return params


def main():
    private_key = load_owner_private_key()
    print(f"signer pbk: {private_key.pbk.hex()}")

    # Valores mock para validar la serialización (NO representan una decisión real)
    reasoning = (
        "APY del pool (12.4%) supera al actual (9.1%) con slippage estimado de 0.5%, "
        "por lo que conviene rotar la posición."
    )
    deploy_hash = "602f337ce1dc46f1b91809fe8d938ed0987761b421f6c505a36e1a646f4c5820"

    params = _build_params(reasoning, deploy_hash)
    print(f"params ({len(params.encode('utf-8'))} bytes): {params}")

    args = {
        "action_type": CLV_String("SWAP"),
        "params": CLV_String(params),
    }

    deploy = build_contract_call_deploy(
        private_key=private_key,
        contract_package_hash=CONTRACT_PACKAGE_HASH,
        entry_point="log_action",
        args=args,
        attached_motes=0,
    )

    print(f"deploy hash (pre-submit): {deploy.hash.hex()}")
    print(f"approvals: {len(deploy.approvals)}")
    print("OK - deploy construido y firmado correctamente (no enviado)")


if __name__ == "__main__":
    main()
