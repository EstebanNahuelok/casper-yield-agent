#!/usr/bin/env node
/**
 * node_signer.mjs — Submits a Casper contract call via TransactionV1 (Casper 2.x).
 *
 * Reads JSON from stdin:
 * {
 *   "contract_package_hash": "<64-char hex>",
 *   "entry_point": "execute_swap",
 *   "args": [["name", "CLString"|"CLUInt512", "value"], ...],
 *   "pem_path": "/path/to/secret_key.pem",
 *   "api_key": "cspr-cloud-token",
 *   "payment": 10000000000,
 *   "chain": "casper-test"
 * }
 *
 * Writes JSON to stdout: {"tx_hash": "..."} or {"error": "..."}
 */

import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { readFileSync } from 'fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
// From agent/src/chain/ up 3 levels → project root, then into frontend/
const FRONTEND_DIR = join(__dirname, '..', '..', '..', 'frontend');

const require = createRequire(import.meta.url);
const sdk = require(join(FRONTEND_DIR, 'node_modules', 'casper-js-sdk'));
const { RpcClient, HttpHandler, ContractCallBuilder, PrivateKey, KeyAlgorithm, CLValue, Args } = sdk;

async function readStdin() {
  return new Promise((resolve, reject) => {
    let data = '';
    process.stdin.setEncoding('utf-8');
    process.stdin.on('data', chunk => { data += chunk; });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', reject);
  });
}

async function main() {
  let input;
  try {
    const raw = await readStdin();
    input = JSON.parse(raw);
  } catch (e) {
    console.log(JSON.stringify({ error: `Failed to read input: ${e.message}` }));
    process.exit(1);
  }

  const { contract_package_hash, entry_point, args: argDefs, pem_path, api_key, payment, chain } = input;
  // Primary: CasperLabs public RPC (no rate limits). Fallback: cspr.cloud with API key.
  const PUBLIC_RPC  = chain === 'casper'
    ? 'https://rpc.mainnet.casperlabs.io'
    : 'https://rpc.testnet.casperlabs.io';
  const CLOUD_RPC   = chain === 'casper'
    ? 'https://node.mainnet.cspr.cloud/rpc'
    : 'https://node.testnet.cspr.cloud/rpc';

  async function tryPutTransaction(tx, rpcUrl, extraHeaders = {}) {
    const handler = new HttpHandler(rpcUrl);
    if (Object.keys(extraHeaders).length) handler.setCustomHeaders(extraHeaders);
    const rpc = new RpcClient(handler);
    const put = await rpc.putTransaction(tx);
    return put.transactionHash?.toHex?.() ?? String(put.transactionHash);
  }

  try {
    const pem        = readFileSync(pem_path, 'utf-8');
    const privateKey = PrivateKey.fromPem(pem, KeyAlgorithm.ED25519);

    // Build runtime args: each entry is [name, type, value]
    const argsMap = {};
    for (const [name, type, value] of argDefs) {
      if (type === 'CLString') {
        argsMap[name] = CLValue.newCLString(value);
      } else if (type === 'CLUInt512') {
        argsMap[name] = CLValue.newCLUInt512(BigInt(value));
      } else {
        throw new Error(`Unknown arg type: ${type}`);
      }
    }

    const tx = new ContractCallBuilder()
      .from(privateKey.publicKey)
      .byPackageHash(contract_package_hash)
      .entryPoint(entry_point)
      .runtimeArgs(Args.fromMap(argsMap))
      .chainName(chain ?? 'casper-test')
      .payment(payment ?? 10_000_000_000)
      .ttl(1800000)
      .build();
    tx.sign(privateKey);

    let txHash;
    try {
      txHash = await tryPutTransaction(tx, PUBLIC_RPC);
    } catch (publicErr) {
      process.stderr.write(`[node_signer] public RPC failed (${publicErr.message}), trying cspr.cloud\n`);
      txHash = await tryPutTransaction(tx, CLOUD_RPC, { Authorization: api_key });
    }
    console.log(JSON.stringify({ tx_hash: txHash }));
  } catch (e) {
    // Log full error details for debugging
    const detail = e?.data ?? e?.response ?? e?.cause ?? '';
    const msg = e.message ?? String(e);
    process.stderr.write(`[node_signer] Error: ${msg}\n`);
    if (detail) process.stderr.write(`[node_signer] Detail: ${JSON.stringify(detail)}\n`);
    console.log(JSON.stringify({ error: msg, detail: String(detail) }));
    process.exit(1);
  }
}

main();
