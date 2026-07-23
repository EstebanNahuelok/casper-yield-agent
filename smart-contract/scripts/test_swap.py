#!/usr/bin/env python3
"""
test_swap.py — Ejecuta execute_swap directamente para verificar que CSPR se mueve al pool.

Llama al entry point execute_swap del YieldVault usando la misma firma pycspr que el agente,
lo que fuerza una llamada cross-contract real al SimplePool (set_pool debe estar configurado).

Usage (desde repo root, con venv activo):
  python smart-contract/scripts/test_swap.py
"""

import asyncio
import base64
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT  = SCRIPT_DIR.parent.parent
PROXY_WASM = REPO_ROOT / "smart-contract" / "vendor" / "odra-casper-rpc-client" / "resources" / "proxy_caller_with_return.wasm"
AGENT_ENV  = REPO_ROOT / "agent" / ".env"
LIVENET_ENV = SCRIPT_DIR / ".livenet.env"

CHAIN_NAME = "casper-test"
RPC_HOST   = "node.testnet.cspr.cloud"
RPC_URL    = f"https://{RPC_HOST}/rpc"
GAS_MOTES  = 10_000_000_000  # 10 CSPR gas

SWAP_AMOUNT_CSPR = 5.0  # CSPR a enviar al pool (conservador para prueba)

_ED25519_SEED = 32


def _load_file_env(path: Path) -> dict:
    env: dict = {}
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def _patch_requests(api_key: str):
    import requests as _req
    _orig = _req.post
    def _patched(url, **kwargs):
        if RPC_HOST in url or "127.0.0.1" in url or "localhost" in url:
            url = RPC_URL
        h = dict(kwargs.pop("headers", None) or {})
        h["Authorization"] = api_key
        return _orig(url, headers=h, **kwargs)
    _req.post = _patched


def _load_key_from_b64(b64_der: str, pycspr):
    der = base64.b64decode(b64_der)
    seed = der[-_ED25519_SEED:]
    pvk, pbk = pycspr.crypto.get_key_pair_from_bytes(seed, pycspr.KeyAlgorithm.ED25519)
    return pycspr.PrivateKey(pvk, pbk, pycspr.KeyAlgorithm.ED25519)


async def run_test_swap(vault_pkg: str, swap_cspr: float, api_key: str, secret_key_b64: str):
    import pycspr
    from pycspr.api.rpc.connection import ConnectionInfo
    from pycspr.types.cl import CLV_ByteArray, CLV_List, CLV_String, CLV_U512, CLV_U8
    from pycspr.types.node.rpc import DeployArgument, DeployOfModuleBytes
    from pycspr.serializer.binary.node_rpc.encoder import _encode_deploy_argument, _vector_to_bytes

    _patch_requests(api_key)

    private_key = _load_key_from_b64(secret_key_b64, pycspr)
    client = pycspr.NodeRpcClient(ConnectionInfo(host=RPC_HOST, port=443))
    wasm_bytes = PROXY_WASM.read_bytes()

    amount_in_motes  = int(swap_cspr * 1_000_000_000)
    amount_out_motes = int(swap_cspr * 0.9 * 1_000_000_000)  # rough estimate

    # Encode execute_swap args (same as ChainExecutor.execute_swap in the agent)
    arguments = [
        DeployArgument("token_in",   CLV_String("CSPR")),
        DeployArgument("token_out",  CLV_String("sCSPR")),
        DeployArgument("amount_in",  CLV_U512(amount_in_motes)),
        DeployArgument("amount_out", CLV_U512(amount_out_motes)),
    ]
    runtime_args_bytes = _vector_to_bytes([_encode_deploy_argument(a) for a in arguments])

    session = DeployOfModuleBytes(
        args={
            "package_hash":   CLV_ByteArray(bytes.fromhex(vault_pkg)),
            "entry_point":    CLV_String("execute_swap"),
            "args":           CLV_List([CLV_U8(b) for b in runtime_args_bytes]),
            "attached_value": CLV_U512(0),
            "amount":         CLV_U512(0),
        },
        module_bytes=wasm_bytes,
    )
    payment = pycspr.create_standard_payment(GAS_MOTES)
    params  = pycspr.create_deploy_parameters(
        account=private_key,
        chain_name=CHAIN_NAME,
        ttl="30m",
        gas_price=1,
    )
    deploy = pycspr.create_deploy(params, payment, session)
    deploy.approve(private_key)

    print(f"\nLlamando execute_swap({swap_cspr} CSPR -> sCSPR) en vault {vault_pkg[:16]}...")
    tx_hash = await client.account_put_deploy(deploy)
    print(f"\n[OK] execute_swap submitted!")
    print(f"  deploy hash : {tx_hash}")
    print(f"  Explorer    : https://testnet.cspr.live/deploy/{tx_hash}")
    return tx_hash


def main():
    agent_env = _load_file_env(AGENT_ENV)
    live_env  = _load_file_env(LIVENET_ENV)

    vault_pkg  = agent_env.get("VAULT_PACKAGE_HASH", "").replace("hash-", "").strip()
    secret_key = agent_env.get("VAULT_OWNER_SECRET_KEY", "").strip()
    api_key    = live_env.get("CSPR_CLOUD_AUTH_TOKEN", agent_env.get("CSPR_CLOUD_API_KEY", "")).strip()

    if not vault_pkg:
        print("ERROR: VAULT_PACKAGE_HASH not in agent/.env"); sys.exit(1)
    if not secret_key:
        print("ERROR: VAULT_OWNER_SECRET_KEY not in agent/.env"); sys.exit(1)
    if not api_key:
        print("ERROR: CSPR_CLOUD_AUTH_TOKEN not in .livenet.env"); sys.exit(1)
    if not PROXY_WASM.exists():
        print(f"ERROR: proxy WASM not found at {PROXY_WASM}"); sys.exit(1)

    print(f"VAULT_PACKAGE_HASH : {vault_pkg}")
    print(f"SWAP_AMOUNT_CSPR   : {SWAP_AMOUNT_CSPR}")
    print()

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_test_swap(vault_pkg, SWAP_AMOUNT_CSPR, api_key, secret_key))


if __name__ == "__main__":
    main()
