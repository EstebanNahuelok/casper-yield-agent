"""
Firma y envío de transacciones de contrato vía pycspr, sin pasar por el MCP Server
(CasperMcp no expone un tool "CallContract" — solo lectura + transfer/delegate nativos).

Usa el mismo mecanismo que smart-contract/scripts/deposit_py.py: el proxy_caller_with_return.wasm
de Odra como session code, que reenvía la llamada a (package_hash, entry_point, args, attached_value).
"""

import base64
import threading
from pathlib import Path

import pycspr
from pycspr.api.rpc.connection import ConnectionInfo
from pycspr import KeyAlgorithm
from pycspr.crypto import get_key_pair_from_bytes
from pycspr.types.cl import CLV_ByteArray, CLV_List, CLV_String, CLV_U512, CLV_U8, CLV_Value
from pycspr.types.node.rpc import DeployArgument, DeployOfModuleBytes
from pycspr.serializer.binary.node_rpc.encoder import _encode_deploy_argument, _vector_to_bytes

from ..config import settings

# El proxy WASM de Odra vive en smart-contract/, sibling de agent/
_PROXY_WASM_PATH = (
    Path(__file__).resolve().parents[3]
    / "smart-contract"
    / "vendor"
    / "odra-casper-rpc-client"
    / "resources"
    / "proxy_caller_with_return.wasm"
)

GAS_PAYMENT_MOTES = 10_000_000_000  # 10 CSPR, igual que deposit_py.py
RPC_HOST = f"node.{settings.casper_network}.cspr.cloud"
RPC_URL = f"https://{RPC_HOST}/rpc"

_ED25519_SEED_LENGTH = 32

_patch_lock = threading.Lock()
_patched = False


def _patch_requests_auth(api_key: str) -> None:
    """
    Redirige todas las llamadas POST de pycspr (que apuntan a
    http://node.<network>.cspr.cloud:443/rpc, construido a partir de
    ConnectionInfo(host, port)) hacia RPC_URL (https) e inyecta el header
    Authorization. Idempotente: el patch se aplica una sola vez por proceso.
    """
    global _patched
    with _patch_lock:
        if _patched:
            return

        import requests as _req
        _original_post = _req.post

        def _post_with_auth(url, **kwargs):
            if RPC_HOST in url:
                url = RPC_URL
            headers = dict(kwargs.pop("headers", None) or {})
            headers["Authorization"] = api_key
            return _original_post(url, headers=headers, **kwargs)

        _req.post = _post_with_auth
        _patched = True


def load_owner_private_key() -> "pycspr.PrivateKey":
    """
    Construye un PrivateKey ED25519 a partir de VAULT_OWNER_SECRET_KEY (base64 DER/PKCS8).
    El DER PKCS8 de ED25519 termina con los 32 bytes del seed crudo (igual que pycspr's
    get_pvk_from_pem_file, que toma pvk[-32:] del PEM decodificado).
    """
    der = base64.b64decode(settings.vault_owner_secret_key)
    seed = der[-_ED25519_SEED_LENGTH:]
    pvk, pbk = get_key_pair_from_bytes(seed, KeyAlgorithm.ED25519)
    return pycspr.PrivateKey(pvk, pbk, KeyAlgorithm.ED25519)


def _encode_runtime_args(args: dict[str, CLV_Value]) -> bytes:
    """Serializa un dict de CLValues al formato binario RuntimeArgs que espera el proxy WASM."""
    arguments = [DeployArgument(name, value) for name, value in args.items()]
    return _vector_to_bytes([_encode_deploy_argument(a) for a in arguments])


def build_contract_call_deploy(
    private_key: "pycspr.PrivateKey",
    contract_package_hash: str,
    entry_point: str,
    args: dict[str, CLV_Value],
    attached_motes: int = 0,
) -> "pycspr.types.node.rpc.Deploy":
    """
    Construye y firma un deploy que invoca `entry_point` del contrato identificado por
    `contract_package_hash` (hex, sin prefijo "hash-"/"package-"), pasándole `args` como
    RuntimeArgs. Usa proxy_caller_with_return.wasm como session code (igual que deposit_py.py).
    """
    if not _PROXY_WASM_PATH.exists():
        raise FileNotFoundError(f"Proxy WASM no encontrado: {_PROXY_WASM_PATH}")

    wasm_bytes = pycspr.read_wasm(_PROXY_WASM_PATH)
    pkg_hash_bytes = bytes.fromhex(contract_package_hash)
    runtime_args_bytes = _encode_runtime_args(args)

    session = DeployOfModuleBytes(
        args={
            "package_hash": CLV_ByteArray(pkg_hash_bytes),
            "entry_point": CLV_String(entry_point),
            "args": CLV_List([CLV_U8(b) for b in runtime_args_bytes]),
            "attached_value": CLV_U512(attached_motes),
            "amount": CLV_U512(attached_motes),
        },
        module_bytes=wasm_bytes,
    )

    payment = pycspr.create_standard_payment(GAS_PAYMENT_MOTES)
    params = pycspr.create_deploy_parameters(
        account=private_key,
        chain_name="casper-test" if settings.casper_network == "testnet" else "casper",
        ttl="30m",
        gas_price=1,
    )

    deploy = pycspr.create_deploy(params, payment, session)
    deploy.approve(private_key)
    return deploy


async def submit_deploy(deploy: "pycspr.types.node.rpc.Deploy") -> str:
    """Envía el deploy firmado a node.<network>.cspr.cloud/rpc y devuelve el deploy hash."""
    _patch_requests_auth(settings.cspr_cloud_api_key)
    client = pycspr.NodeRpcClient(ConnectionInfo(host=RPC_HOST, port=443))
    return await client.account_put_deploy(deploy)
