#!/usr/bin/env python3
"""
set_pool.py — Calls set_pool() on the YieldVault with the SimplePool package hash.

This connects the vault to the real AMM so execute_swap moves actual CSPR.

Usage (from repo root, with venv active):
  python smart-contract/scripts/set_pool.py

Reads credentials from smart-contract/scripts/.livenet.env.
Reads vault/pool hashes from agent/.env.
"""

import asyncio
import base64
import os
import sys
from pathlib import Path

SCRIPT_DIR  = Path(__file__).resolve().parent
REPO_ROOT   = SCRIPT_DIR.parent.parent
PROXY_WASM  = REPO_ROOT / "smart-contract" / "vendor" / "odra-casper-rpc-client" / "resources" / "proxy_caller_with_return.wasm"
LIVENET_ENV = SCRIPT_DIR / ".livenet.env"
AGENT_ENV   = REPO_ROOT / "agent" / ".env"

CHAIN_NAME = "casper-test"
RPC_HOST   = "node.testnet.cspr.cloud"
RPC_URL    = f"https://{RPC_HOST}/rpc"
GAS_MOTES  = 10_000_000_000  # 10 CSPR

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


def _load_key(key_path: Path, pycspr):
    der = base64.b64decode(Path(key_path).read_text().strip()
                           .replace("-----BEGIN PRIVATE KEY-----", "")
                           .replace("-----END PRIVATE KEY-----", "")
                           .replace("-----BEGIN EC PRIVATE KEY-----", "")
                           .replace("-----END EC PRIVATE KEY-----", "")
                           .strip())
    seed = der[-_ED25519_SEED:]
    pvk, pbk = pycspr.crypto.get_key_pair_from_bytes(seed, pycspr.KeyAlgorithm.ED25519)
    return pycspr.PrivateKey(pvk, pbk, pycspr.KeyAlgorithm.ED25519)


async def call_set_pool(vault_package_hash: str, pool_package_hash: str):
    live_env = _load_file_env(LIVENET_ENV)
    api_key  = live_env.get("CSPR_CLOUD_AUTH_TOKEN", "").strip()
    key_path = Path(live_env.get("ODRA_CASPER_LIVENET_SECRET_KEY_PATH", "")).expanduser()

    if not api_key:
        print("ERROR: CSPR_CLOUD_AUTH_TOKEN missing from .livenet.env"); sys.exit(1)
    if not key_path.exists():
        print(f"ERROR: secret key not found at {key_path}"); sys.exit(1)
    if not PROXY_WASM.exists():
        print(f"ERROR: proxy WASM not found at {PROXY_WASM}"); sys.exit(1)

    import pycspr
    from pycspr.api.rpc.connection import ConnectionInfo
    from pycspr.types.cl import CLV_ByteArray, CLV_Key, CLV_KeyType, CLV_List, CLV_String, CLV_U512, CLV_U8
    from pycspr.types.node.rpc import DeployArgument, DeployOfModuleBytes
    from pycspr.serializer.binary.node_rpc.encoder import _encode_deploy_argument, _vector_to_bytes
    from pycspr.serializer.binary.cl_value import encode as encode_cl_value
    from pycspr.serializer.utils.cl_value_to_cl_type import encode as cl_value_to_cl_type
    from pycspr.serializer.binary.cl_type import encode as encode_cl_type

    _patch_requests(api_key)

    private_key = _load_key(key_path, pycspr)
    client = pycspr.NodeRpcClient(ConnectionInfo(host=RPC_HOST, port=443))
    wasm_bytes = PROXY_WASM.read_bytes()

    # Encode the single arg: pool = Key::Hash(<pool_package_hash_bytes>)
    pool_key = CLV_Key(
        identifier=bytes.fromhex(pool_package_hash),
        key_type=CLV_KeyType.HASH,
    )

    # Serialize as RuntimeArgs binary (what the proxy wasm forwards to set_pool)
    arguments = [DeployArgument("pool", pool_key)]
    runtime_args_bytes = _vector_to_bytes([_encode_deploy_argument(a) for a in arguments])

    session = DeployOfModuleBytes(
        args={
            "package_hash":   CLV_ByteArray(bytes.fromhex(vault_package_hash)),
            "entry_point":    CLV_String("set_pool"),
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

    print(f"Calling set_pool on vault {vault_package_hash[:16]}...")
    print(f"  pool = Key::Hash({pool_package_hash[:16]}...)")
    tx_hash = await client.account_put_deploy(deploy)
    print(f"\n[OK] set_pool submitted!")
    print(f"  deploy hash: {tx_hash}")
    print(f"  Explorer:    https://testnet.cspr.live/deploy/{tx_hash}")
    print(f"\n  Wait ~60s, then check Named Keys on the vault contract.")
    print(f"  https://testnet.cspr.live/contract/{vault_package_hash}")
    return tx_hash


def main():
    agent_env = _load_file_env(AGENT_ENV)
    vault_pkg = agent_env.get("VAULT_PACKAGE_HASH", "").replace("hash-", "").strip()
    pool_pkg  = agent_env.get("POOL_PACKAGE_HASH", "").replace("hash-", "").strip()

    if not vault_pkg:
        print("ERROR: VAULT_PACKAGE_HASH not in agent/.env"); sys.exit(1)
    if not pool_pkg:
        print("ERROR: POOL_PACKAGE_HASH not in agent/.env"); sys.exit(1)

    print(f"VAULT_PACKAGE_HASH : {vault_pkg}")
    print(f"POOL_PACKAGE_HASH  : {pool_pkg}")
    print()

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(call_set_pool(vault_pkg, pool_pkg))


if __name__ == "__main__":
    main()
