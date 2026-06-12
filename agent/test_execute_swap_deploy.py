"""
Script temporal: construye (y firma) el deploy de
`execute_swap(token_in: String, token_out: String, amount_in: U512, amount_out: U512)`
para el YieldVault usando pycspr_signer, sin enviarlo todavía.

Valores de ejemplo (mock): en la integración real, amount_in/amount_out vienen de
Decision + la quote de cspr.trade (ver comentario al final sobre amount_out).
"""

from pycspr.types.cl import CLV_String, CLV_U512

from src.chain.pycspr_signer import build_contract_call_deploy, load_owner_private_key

CONTRACT_PACKAGE_HASH = "a44b0f0f83462cdc10172a0576ec760363fc1f25ca6dd92da9df1e2200a78c88"


def main():
    private_key = load_owner_private_key()
    print(f"signer pbk: {private_key.pbk.hex()}")

    # Valores mock para validar la serialización (NO representan una decisión real)
    amount_in_motes = int(10 * 1_000_000_000)  # 10 CSPR
    amount_out_motes = int(9.95 * 1_000_000_000)  # 9.95 sCSPR (slippage ~0.5%)

    args = {
        "token_in": CLV_String("CSPR"),
        "token_out": CLV_String("sCSPR"),
        "amount_in": CLV_U512(amount_in_motes),
        "amount_out": CLV_U512(amount_out_motes),
    }

    deploy = build_contract_call_deploy(
        private_key=private_key,
        contract_package_hash=CONTRACT_PACKAGE_HASH,
        entry_point="execute_swap",
        args=args,
        attached_motes=0,
    )

    print(f"deploy hash (pre-submit): {deploy.hash.hex()}")
    print(f"approvals: {len(deploy.approvals)}")
    print("OK - deploy construido y firmado correctamente (no enviado)")


if __name__ == "__main__":
    main()
