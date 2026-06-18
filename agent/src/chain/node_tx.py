"""
Submits Casper contract calls via casper-js-sdk (Node.js) as TransactionV1 (Casper 2.x).
Replaces pycspr_signer.py which used the legacy Deploy format (account_put_deploy).
"""

import asyncio
import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path

import structlog

from ..config import settings

log = structlog.get_logger()

_THIS_DIR = Path(__file__).resolve().parent
_NODE_SIGNER = _THIS_DIR / "node_signer.mjs"

_CHAIN_NAME = "casper-test" if settings.casper_network == "testnet" else "casper"
GAS_PAYMENT_MOTES = 10_000_000_000  # 10 CSPR


def _write_pem_temp(secret_key_b64: str) -> str:
    """
    Wraps a base64 PKCS8 ED25519 private key in PEM format and writes to a temp file.
    Returns the temp file path (caller must delete it).
    """
    pem = (
        "-----BEGIN PRIVATE KEY-----\n"
        + secret_key_b64
        + "\n-----END PRIVATE KEY-----\n"
    )
    fd, path = tempfile.mkstemp(suffix=".pem")
    with os.fdopen(fd, "wb") as f:
        f.write(pem.encode("ascii"))
    return path


async def submit_contract_call(
    contract_package_hash: str,
    entry_point: str,
    args: list[tuple[str, str, str]],
    payment: int = GAS_PAYMENT_MOTES,
) -> str:
    """
    Submits a contract call via ContractCallBuilder (TransactionV1) using node_signer.mjs.

    args: list of (name, type, value) triples where type is 'CLString' or 'CLUInt512'.
          Values must be strings (numbers as string for CLUInt512).

    Returns the transaction hash as a hex string.
    """
    pem_path = _write_pem_temp(settings.vault_owner_secret_key)
    try:
        payload = {
            "contract_package_hash": contract_package_hash,
            "entry_point": entry_point,
            "args": [[n, t, v] for n, t, v in args],
            "pem_path": pem_path,
            "api_key": settings.cspr_cloud_api_key,
            "payment": payment,
            "chain": _CHAIN_NAME,
        }
        payload_json = json.dumps(payload)

        log.debug("node_tx.call", entry_point=entry_point, pkg=contract_package_hash[:16])
        proc = await asyncio.create_subprocess_exec(
            "node",
            str(_NODE_SIGNER),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(input=payload_json.encode())
        if stderr:
            log.warning("node_tx.stderr", text=stderr.decode())
        result = json.loads(stdout.decode().strip())
        if "error" in result:
            raise RuntimeError(f"node_signer error: {result['error']}")
        tx_hash = result["tx_hash"]
        log.info("node_tx.submitted", tx_hash=tx_hash, entry_point=entry_point)
        return tx_hash
    finally:
        os.unlink(pem_path)
