#!/usr/bin/env python3
"""
test_rpc.py — Diagnostico directo del RPC de Casper para el vault contract.
Corre desde agent/:  py test_rpc.py
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# Cargar .env antes de importar settings
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(Path(__file__).parent / "src"))

import httpx
from config import settings

RPC_URL = f"https://node.{settings.casper_network}.cspr.cloud/rpc"
AUTH_HEADERS = {
    "Authorization": settings.cspr_cloud_api_key,
    "Content-Type": "application/json",
}


async def rpc_call(http: httpx.AsyncClient, method: str, params: dict, id_: int) -> dict:
    print(f"\n{'='*60}")
    print(f"METHOD: {method}")
    print(f"PARAMS: {json.dumps(params, indent=2)}")
    r = await http.post(RPC_URL, headers=AUTH_HEADERS, json={
        "jsonrpc": "2.0", "method": method, "params": params, "id": id_,
    })
    print(f"HTTP STATUS: {r.status_code}")
    data = r.json()
    print(f"RESPONSE:\n{json.dumps(data, indent=2)[:5000]}")
    return data


async def main():
    print(f"RPC URL:       {RPC_URL}")
    print(f"Contract hash: {settings.vault_contract_hash}")
    print(f"API key:       {settings.cspr_cloud_api_key[:12]}..." if settings.cspr_cloud_api_key else "API key: (VACÍA!)")

    async with httpx.AsyncClient(timeout=30.0) as http:
        # 1. State root hash
        d = await rpc_call(http, "chain_get_state_root_hash", {}, 1)
        if "error" in d:
            print(f"\nFALLÓ chain_get_state_root_hash: {d['error']}")
            return
        if "result" not in d:
            print(f"\nRespuesta sin 'result': {d}")
            return

        state_root = d["result"]["state_root_hash"]
        print(f"\nstate_root_hash OK: {state_root}")

        # 2a. state_get_item (Casper 1.x API)
        d2 = await rpc_call(http, "state_get_item", {
            "state_root_hash": state_root,
            "key": settings.vault_contract_hash,
            "path": [],
        }, 2)

        # 2b. query_global_state (Casper 2.x / Condor API)
        d3 = await rpc_call(http, "query_global_state", {
            "state_root_hash": state_root,
            "key": settings.vault_contract_hash,
            "path": [],
        }, 3)

        # 3. Extraer __contract_main_purse del Contract
        sv = d2.get("result", {}).get("stored_value", {})
        print(f"\nstored_value keys: {list(sv.keys())}")
        named_keys_raw = sv.get("Contract", {}).get("named_keys", [])
        named_keys = {nk["name"]: nk["key"] for nk in named_keys_raw}
        print(f"named_keys: {list(named_keys.keys())}")

        purse_uref = named_keys.get("__contract_main_purse")
        print(f"__contract_main_purse URef: {purse_uref}")
        if not purse_uref:
            print("ERROR: __contract_main_purse NOT FOUND")
            return

        # 4a. Casper 2.x: query_balance con purse_uref
        print("\n--- query_balance (Casper 2.x) ---")
        d4 = await rpc_call(http, "query_balance", {
            "purse_identifier": {"purse_uref": purse_uref},
        }, 4)
        if "result" in d4:
            motes = int(d4["result"].get("balance", 0))
            print(f"\n>>> query_balance = {motes} motes = {motes / 1e9} CSPR")

        # 4b. Casper 1.x: balance-{uref_addr} key
        print("\n--- state_get_item balance key (Casper 1.x) ---")
        uref_addr = purse_uref.removeprefix("uref-").rsplit("-", 1)[0]
        balance_key = f"balance-{uref_addr}"
        print(f"balance_key = {balance_key}")
        d5 = await rpc_call(http, "state_get_item", {
            "state_root_hash": state_root,
            "key": balance_key,
            "path": [],
        }, 5)
        cl = d5.get("result", {}).get("stored_value", {}).get("CLValue", {})
        if cl:
            parsed = cl.get("parsed", "0")
            motes = int(parsed) if parsed else 0
            print(f"\n>>> balance key = {motes} motes = {motes / 1e9} CSPR")


if __name__ == "__main__":
    asyncio.run(main())
