#!/usr/bin/env node
/**
 * upgrade_contracts.mjs — Upgrades SimplePool + YieldVault in-place (same package hashes).
 *
 * Sets odra_cfg_is_upgrade=true so the existing contract state is preserved:
 *   - Pool: cspr_reserve, scspr_reserve intact
 *   - Vault: pool_address, scspr_balance, total_locked, user balances intact
 *
 * After upgrade, vault.execute_swap dispatches on token_in:
 *   "CSPR"  -> swap_cspr_for_scspr (forward, existing behavior)
 *   "sCSPR" -> swap_scspr_for_cspr (reverse, new)
 *
 * Usage (from repo root, after cargo odra build -b casper):
 *   node smart-contract/scripts/upgrade_contracts.mjs
 */

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { createRequire } from 'module';
import https from 'https';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_DIR  = join(__dirname, '..');
const FRONTEND_DIR = join(PROJECT_DIR, '..', 'frontend');

const require = createRequire(import.meta.url);
const sdk = require(join(FRONTEND_DIR, 'node_modules', 'casper-js-sdk'));
const { RpcClient, HttpHandler, SessionBuilder, PrivateKey, KeyAlgorithm, CLValue, Args } = sdk;

const RPC_HOST   = 'node.testnet.cspr.cloud';
const RPC_URL    = `https://${RPC_HOST}/rpc`;
const CHAIN      = 'casper-test';
const GAS_DEPLOY = 500_000_000_000n; // 500 CSPR

const POOL_WASM  = join(PROJECT_DIR, 'wasm', 'simple_pool.wasm');
const VAULT_WASM = join(PROJECT_DIR, 'wasm', 'yield_vault.wasm');
const PEM_PATH   = join(PROJECT_DIR, '..', 'casper-key.pem');
const ENV_PATH   = join(__dirname, '.livenet.env');

function loadEnv() {
  try {
    return Object.fromEntries(
      readFileSync(ENV_PATH, 'utf-8')
        .split('\n')
        .filter(l => l.includes('=') && !l.startsWith('#'))
        .map(l => { const [k, ...v] = l.split('='); return [k.trim(), v.join('=').trim()]; })
    );
  } catch { return {}; }
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function rpcPost(method, params, apiKey) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({ jsonrpc: '2.0', method, params, id: 1 });
    const req = https.request(
      { host: RPC_HOST, port: 443, path: '/rpc', method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: apiKey,
                   'Content-Length': Buffer.byteLength(body) } },
      res => {
        let data = '';
        res.on('data', c => { data += c; });
        res.on('end', () => { try { resolve(JSON.parse(data)); } catch (e) { reject(e); } });
      }
    );
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

async function waitForTx(rpc, txHash, label) {
  console.log(`  Watching ${label}: ${txHash.slice(0, 20)}...`);
  const deadline = Date.now() + 300_000;
  while (Date.now() < deadline) {
    await sleep(8_000);
    try {
      const info = await rpc.getTransactionByTransactionHash(txHash);
      const execResult = info?.executionInfo?.executionResult;
      if (execResult) {
        const errMsg =
          execResult.Version2?.errorMessage ??
          execResult.Version2?.error_message ??
          execResult.Version1?.Failure?.errorMessage ??
          execResult.Version1?.Failure?.error_message;
        if (errMsg) throw new Error(`${label} failed: ${errMsg}`);
        console.log(`  ${label} confirmed!`);
        return;
      }
    } catch (e) {
      if (e.message?.includes(' failed:')) throw e;
    }
  }
  throw new Error(`Timeout waiting for ${label}`);
}

async function main() {
  const env    = loadEnv();
  const apiKey = env.CSPR_CLOUD_AUTH_TOKEN;
  if (!apiKey) { console.error('ERROR: CSPR_CLOUD_AUTH_TOKEN missing from .livenet.env'); process.exit(1); }

  const pem        = readFileSync(PEM_PATH, 'utf-8');
  const privateKey = PrivateKey.fromPem(pem, KeyAlgorithm.ED25519);
  console.log('Upgrading contracts as:', privateKey.publicKey.toHex());

  const handler = new HttpHandler(RPC_URL);
  handler.setCustomHeaders({ Authorization: apiKey });
  const rpc = new RpcClient(handler);

  const poolWasm  = new Uint8Array(readFileSync(POOL_WASM));
  const vaultWasm = new Uint8Array(readFileSync(VAULT_WASM));
  console.log(`Pool WASM:  ${poolWasm.length.toLocaleString()} bytes`);
  console.log(`Vault WASM: ${vaultWasm.length.toLocaleString()} bytes`);

  // ── 1. Upgrade SimplePool ─────────────────────────────────────────────────
  // odra_cfg_is_upgrade=true: adds a new version to the existing SimplePool_package_hash.
  // Pool state (cspr_reserve, scspr_reserve) is preserved. New entry point: swap_scspr_for_cspr.
  console.log('\n[1] Upgrading SimplePool...');
  const poolArgs = Args.fromMap({
    odra_cfg_package_hash_key_name: CLValue.newCLString('SimplePool_package_hash'),
    odra_cfg_allow_key_override:    CLValue.newCLValueBool(true),
    odra_cfg_is_upgradable:         CLValue.newCLValueBool(true),
    odra_cfg_is_upgrade:            CLValue.newCLValueBool(true),
  });
  const poolTx = new SessionBuilder()
    .from(privateKey.publicKey)
    .wasm(poolWasm)
    .installOrUpgrade()
    .runtimeArgs(poolArgs)
    .chainName(CHAIN)
    .payment(Number(GAS_DEPLOY))
    .build();
  poolTx.sign(privateKey);

  const poolPut    = await rpc.putTransaction(poolTx);
  const poolTxHash = poolPut.transactionHash?.toHex?.() ?? String(poolPut.transactionHash);
  console.log('  tx hash:', poolTxHash);
  await waitForTx(rpc, poolTxHash, 'SimplePool upgrade');

  // ── 2. Upgrade YieldVault ─────────────────────────────────────────────────
  // odra_cfg_is_upgrade=true: adds a new version to YieldVault2_package_hash.
  // Vault state (pool_address, scspr_balance, balances) is preserved.
  // execute_swap now dispatches on token_in: "CSPR" or "sCSPR".
  console.log('\n[2] Upgrading YieldVault...');
  const vaultArgs = Args.fromMap({
    odra_cfg_package_hash_key_name: CLValue.newCLString('YieldVault2_package_hash'),
    odra_cfg_allow_key_override:    CLValue.newCLValueBool(true),
    odra_cfg_is_upgradable:         CLValue.newCLValueBool(true),
    odra_cfg_is_upgrade:            CLValue.newCLValueBool(true),
  });
  const vaultTx = new SessionBuilder()
    .from(privateKey.publicKey)
    .wasm(vaultWasm)
    .installOrUpgrade()
    .runtimeArgs(vaultArgs)
    .chainName(CHAIN)
    .payment(Number(GAS_DEPLOY))
    .build();
  vaultTx.sign(privateKey);

  const vaultPut    = await rpc.putTransaction(vaultTx);
  const vaultTxHash = vaultPut.transactionHash?.toHex?.() ?? String(vaultPut.transactionHash);
  console.log('  tx hash:', vaultTxHash);
  await waitForTx(rpc, vaultTxHash, 'YieldVault upgrade');

  console.log('\n' + '='.repeat(60));
  console.log('  UPGRADE COMPLETE — same package hashes, state preserved');
  console.log('='.repeat(60));
  console.log(`Pool upgrade:  https://testnet.cspr.live/transaction/${poolTxHash}`);
  console.log(`Vault upgrade: https://testnet.cspr.live/transaction/${vaultTxHash}`);
  console.log('\nNo config changes needed — package hashes are unchanged.');
}

main().catch(e => { console.error('\nFATAL:', e.message ?? e); process.exit(1); });
