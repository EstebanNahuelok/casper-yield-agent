#!/usr/bin/env python3
"""
deposit_py.py — Deposita CSPR en el YieldVault sin compilar Rust.

Usa pycspr 1.2.x + el proxy_caller_with_return.wasm de Odra para llamar
el entry point payable 'deposit'. El WASM adjunta los CSPR al call antes
de invocar el contrato, emulando lo que haría el CLI de Rust.

Requisitos:
    pip install pycspr

    scripts/.livenet.env con:
        CSPR_CLOUD_AUTH_TOKEN=tu_token
        ODRA_CASPER_LIVENET_SECRET_KEY_PATH=/ruta/a/secret_key.pem

Uso:
    python scripts/deposit_py.py 500    # deposita 500 CSPR
    python scripts/deposit_py.py        # default: 200 CSPR
"""

import asyncio
import os
import sys
import traceback
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
LIVENET_ENV = SCRIPT_DIR / ".livenet.env"
PROXY_WASM  = (
    PROJECT_DIR
    / "vendor"
    / "odra-casper-rpc-client"
    / "resources"
    / "proxy_caller_with_return.wasm"
)

# ── Contrato ───────────────────────────────────────────────────────────────────
CONTRACT_PACKAGE_HASH = "a44b0f0f83462cdc10172a0576ec760363fc1f25ca6dd92da9df1e2200a78c88"

# ── Defaults ───────────────────────────────────────────────────────────────────
CHAIN_NAME_DEFAULT = "casper-test"
RPC_PORT           = 7777
CSPR_CLOUD_RPC     = "https://node.testnet.cspr.cloud"
# Gas para el proxy WASM (más costoso que un call directo a un contrato)
GAS_PAYMENT_MOTES  = 10_000_000_000  # 10 CSPR


# ── Config ─────────────────────────────────────────────────────────────────────

def _load_env() -> dict:
    env: dict = {}
    if LIVENET_ENV.exists():
        for raw in LIVENET_ENV.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    for key in (
        "CSPR_CLOUD_AUTH_TOKEN",
        "ODRA_CASPER_LIVENET_SECRET_KEY_PATH",
        "ODRA_CASPER_LIVENET_CHAIN_NAME",
    ):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


# ── Auth ───────────────────────────────────────────────────────────────────────

def _patch_requests_auth(token: str) -> None:
    """
    Monkey-patch requests.post para inyectar el header Authorization de cspr.cloud
    y redirigir las llamadas del cliente pycspr (que apunta a 127.0.0.1:7777)
    directamente a https://node.testnet.cspr.cloud sin levantar un proxy local.
    """
    import requests as _req
    _original_post = _req.post

    def _post_with_auth(url, **kwargs):
        if f"127.0.0.1:{RPC_PORT}" in url:
            url = f"{CSPR_CLOUD_RPC}/rpc"
        headers = dict(kwargs.pop("headers", None) or {})
        headers["Authorization"] = token
        return _original_post(url, headers=headers, **kwargs)

    _req.post = _post_with_auth
    print(f"[deposit] Auth lista → {CSPR_CLOUD_RPC}")


# ── Key ────────────────────────────────────────────────────────────────────────

def _load_private_key(key_path: Path, pycspr):
    """
    Carga la clave privada desde un PEM.
    Detecta ED25519 (prefijo 01 en Casper) vs SECP256K1 (prefijo 02).
    """
    pem_text = key_path.read_text(errors="ignore").upper()
    algo = (
        pycspr.KeyAlgorithm.SECP256K1
        if "EC PRIVATE" in pem_text
        else pycspr.KeyAlgorithm.ED25519
    )
    print(f"[deposit] Algoritmo : {algo.name}")

    # get_key_pair_from_pem_file devuelve (pvk_bytes, pbk_bytes)
    pvk_bytes, pbk_bytes = pycspr.get_key_pair_from_pem_file(str(key_path), algo)
    return pycspr.PrivateKey(pvk_bytes, pbk_bytes, algo)


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    cspr_amount  = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    amount_motes = cspr_amount * 1_000_000_000

    env = _load_env()

    token = env.get("CSPR_CLOUD_AUTH_TOKEN", "").strip()
    if not token:
        print("ERROR: CSPR_CLOUD_AUTH_TOKEN no configurado.")
        print(f"  Añadí CSPR_CLOUD_AUTH_TOKEN=tu_token a {LIVENET_ENV}")
        sys.exit(1)

    key_path = Path(env.get("ODRA_CASPER_LIVENET_SECRET_KEY_PATH", "")).expanduser()
    if not key_path.exists():
        print(f"ERROR: secret_key.pem no encontrado en '{key_path}'")
        sys.exit(1)

    chain_name = env.get("ODRA_CASPER_LIVENET_CHAIN_NAME", CHAIN_NAME_DEFAULT)

    print(f"[deposit] Cantidad  : {cspr_amount} CSPR = {amount_motes:,} motes")
    print(f"[deposit] Contrato  : {CONTRACT_PACKAGE_HASH}")
    print(f"[deposit] Cadena    : {chain_name}")
    print(f"[deposit] Clave     : {key_path}")

    # Verificar pycspr
    try:
        import pycspr
        from pycspr.types.cl import (
            CLV_ByteArray,
            CLV_List,
            CLV_String,
            CLV_U8,
            CLV_U512,
        )
        from pycspr.types.node.rpc import DeployOfModuleBytes
        from pycspr.api.rpc.connection import ConnectionInfo
    except ImportError as exc:
        print(f"\nERROR: pycspr no instalado o versión incorrecta ({exc})")
        print("  Ejecutá: pip install pycspr==1.2.0")
        sys.exit(1)

    # Verificar WASM
    if not PROXY_WASM.exists():
        print(f"\nERROR: proxy_caller WASM no encontrado en:\n  {PROXY_WASM}")
        sys.exit(1)
    wasm_bytes = pycspr.read_wasm(PROXY_WASM)
    print(f"[deposit] WASM      : {len(wasm_bytes):,} bytes")

    # Cargar clave
    try:
        private_key = _load_private_key(key_path, pycspr)
    except Exception as exc:
        print(f"\nERROR: No se pudo cargar la clave privada: {exc}")
        sys.exit(1)

    print(f"[deposit] Cuenta    : {private_key.pbk.hex()[:20]}...")

    _patch_requests_auth(token)

    await _send_deposit(
        pycspr=pycspr,
        clv=(CLV_ByteArray, CLV_List, CLV_U8, CLV_U512, CLV_String),
        DeployOfModuleBytes=DeployOfModuleBytes,
        ConnectionInfo=ConnectionInfo,
        private_key=private_key,
        wasm_bytes=wasm_bytes,
        amount_motes=amount_motes,
        chain_name=chain_name,
        cspr_amount=cspr_amount,
    )


async def _send_deposit(
    pycspr,
    clv,
    DeployOfModuleBytes,
    ConnectionInfo,
    private_key,
    wasm_bytes: bytes,
    amount_motes: int,
    chain_name: str,
    cspr_amount: int,
):
    CLV_ByteArray, CLV_List, CLV_U8, CLV_U512, CLV_String = clv

    # Runtime args para proxy_caller_with_return.wasm (odra-core consts):
    #   "package_hash"    → ByteArray(32)  contrato package hash
    #   "entry_point"     → String         nombre del entry point
    #   "args"            → List(U8)       RuntimeArgs serializados de deposit()
    #                        deposit() sin args → u32 LE 0 = [0x00]*4
    #   "attached_value"  → U512           motes a adjuntar (attached_value del contrato)
    #   "amount"          → U512           mismo valor (requerido por el WASM para el purse)
    pkg_hash_bytes = bytes.fromhex(CONTRACT_PACKAGE_HASH)

    # RuntimeArgs vacío serializado: u32 LE = 0 → 4 bytes cero
    empty_runtime_args = CLV_List([CLV_U8(0), CLV_U8(0), CLV_U8(0), CLV_U8(0)])

    session = DeployOfModuleBytes(
        args={
            "package_hash":    CLV_ByteArray(pkg_hash_bytes),
            "entry_point":     CLV_String("deposit"),
            "args":            empty_runtime_args,
            "attached_value":  CLV_U512(amount_motes),
            "amount":          CLV_U512(amount_motes),
        },
        module_bytes=wasm_bytes,
    )

    payment = pycspr.create_standard_payment(GAS_PAYMENT_MOTES)

    params = pycspr.create_deploy_parameters(
        account=private_key,
        chain_name=chain_name,
        ttl="30m",
        gas_price=1,
    )

    deploy = pycspr.create_deploy(params, payment, session)
    deploy.approve(private_key)

    # El proxy local inyecta el Authorization header hacia cspr.cloud
    client = pycspr.NodeRpcClient(ConnectionInfo(host="127.0.0.1", port=RPC_PORT))

    print("[deposit] Enviando deploy a Casper Testnet...")
    try:
        deploy_hash = await client.account_put_deploy(deploy)
    except Exception as exc:
        print(f"\nERROR al enviar el deploy: {exc}")
        traceback.print_exc()
        sys.exit(1)

    print()
    print("=" * 60)
    print(f"  Deposit enviado : {cspr_amount} CSPR")
    print(f"  Deploy hash     : {deploy_hash}")
    print(f"  Explorer        : https://testnet.cspr.live/deploy/{deploy_hash}")
    print(f"  Contrato        : https://testnet.cspr.live/contract-package/{CONTRACT_PACKAGE_HASH}")
    print("=" * 60)
    print()
    print("  El deploy tarda ~2 minutos en finalizarse en la red.")


if __name__ == "__main__":
    # pycspr uses synchronous `requests` inside async functions.
    # ProactorEventLoop (Windows default ≥3.8) raises [Errno 22] with sync I/O
    # inside coroutines — SelectorEventLoop handles it correctly.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
