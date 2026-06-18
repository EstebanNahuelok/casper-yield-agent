#!/usr/bin/env python3
"""
deploy_esteban.py — Seeds the SimplePool with CSPR after WASM contracts are deployed.

The WASM deployment (SimplePool + YieldVault) is now handled by deploy_esteban.mjs
(Node.js / casper-js-sdk) since it requires TransactionV1 (Casper 2.x).

This script handles the seed_cspr step only, using proxy_caller_with_return.wasm
(legacy Deploy format, which still works for calling existing contracts).

Usage:
  python scripts/deploy_esteban.py --seed-only --pool-pkg <package_hash_hex>
"""

import argparse
import asyncio
import base64
import os
import sys
import time
from pathlib import Path

SCRIPT_DIR  = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
PROXY_WASM  = PROJECT_DIR / "vendor" / "odra-casper-rpc-client" / "resources" / "proxy_caller_with_return.wasm"
LIVENET_ENV = SCRIPT_DIR / ".livenet.env"

CHAIN_NAME = "casper-test"
RPC_HOST   = "node.testnet.cspr.cloud"
RPC_URL    = f"https://{RPC_HOST}/rpc"
GAS_CALL   = 10_000_000_000  # 10 CSPR

SEED_CSPR  = 200  # CSPR to seed pool with
ED25519_SEED = 32


def _load_env() -> dict:
    env: dict = {}
    if LIVENET_ENV.exists():
        for raw in LIVENET_ENV.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    for key in ("CSPR_CLOUD_AUTH_TOKEN", "ODRA_CASPER_LIVENET_SECRET_KEY_PATH"):
        if key in os.environ:
            env[key] = os.environ[key]
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
    der = base64.b64decode(Path(key_path).read_text().strip())
    seed = der[-ED25519_SEED:]
    pvk, pbk = pycspr.crypto.get_key_pair_from_bytes(seed, pycspr.KeyAlgorithm.ED25519)
    return pycspr.PrivateKey(pvk, pbk, pycspr.KeyAlgorithm.ED25519)


async def _submit(client, private_key, pycspr, payment, session) -> str:
    params = pycspr.create_deploy_parameters(
        account=private_key,
        chain_name=CHAIN_NAME,
        ttl="30m",
        gas_price=1,
    )
    deploy = pycspr.create_deploy(params, payment, session)
    deploy.approve(private_key)
    return await client.account_put_deploy(deploy)


async def seed_pool(pool_package_hash: str):
    env = _load_env()
    api_key  = env.get("CSPR_CLOUD_AUTH_TOKEN", "").strip()
    key_path = Path(env.get("ODRA_CASPER_LIVENET_SECRET_KEY_PATH", "")).expanduser()

    if not api_key:
        print("ERROR: CSPR_CLOUD_AUTH_TOKEN missing from .livenet.env"); sys.exit(1)
    if not key_path.exists():
        print(f"ERROR: secret key not found at {key_path}"); sys.exit(1)
    if not PROXY_WASM.exists():
        print(f"ERROR: {PROXY_WASM} not found"); sys.exit(1)

    import pycspr
    from pycspr.api.rpc.connection import ConnectionInfo
    from pycspr.types.cl import CLV_ByteArray, CLV_List, CLV_String, CLV_U512, CLV_U8
    from pycspr.types.node.rpc import DeployOfModuleBytes

    _patch_requests(api_key)

    private_key = _load_key(key_path, pycspr)
    client = pycspr.NodeRpcClient(ConnectionInfo(host=RPC_HOST, port=443))
    proxy_wasm = PROXY_WASM.read_bytes()

    seed_motes = SEED_CSPR * 1_000_000_000

    # Encode empty args (seed_cspr takes no parameters beyond the attached value)
    from pycspr.types.node.rpc import DeployArgument
    from pycspr.serializer.binary.node_rpc.encoder import _encode_deploy_argument, _vector_to_bytes
    empty_args_bytes = _vector_to_bytes([])  # zero-length vector of args

    seed_session = DeployOfModuleBytes(
        args={
            "package_hash":   CLV_ByteArray(bytes.fromhex(pool_package_hash)),
            "entry_point":    CLV_String("seed_cspr"),
            "args":           CLV_List([CLV_U8(b) for b in empty_args_bytes]),
            "attached_value": CLV_U512(seed_motes),
            "amount":         CLV_U512(seed_motes),
        },
        module_bytes=proxy_wasm,
    )
    seed_payment = pycspr.create_standard_payment(GAS_CALL + seed_motes)

    print(f"\n[4] Seeding pool {pool_package_hash[:16]}... with {SEED_CSPR} CSPR...")
    seed_hash = await _submit(client, private_key, pycspr, seed_payment, seed_session)
    print(f"  seed_cspr deploy hash: {seed_hash}")
    print(f"  Explorer: https://testnet.cspr.live/deploy/{seed_hash}")
    print(f"\n  Pool seeded! Wait ~60s for confirmation, then start the agent.")
    return seed_hash


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-only", action="store_true", help="Only run the seed_cspr step")
    parser.add_argument("--pool-pkg", required=False, help="Pool package hash (hex, no 'hash-' prefix)")
    args = parser.parse_args()

    if args.seed_only:
        if not args.pool_pkg:
            print("ERROR: --pool-pkg is required with --seed-only")
            sys.exit(1)
        pool_pkg = args.pool_pkg.replace("hash-", "").strip()
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(seed_pool(pool_pkg))
    else:
        print("This script only supports --seed-only mode.")
        print("For WASM deployment, use: node scripts/deploy_esteban.mjs")
        sys.exit(1)


if __name__ == "__main__":
    main()
