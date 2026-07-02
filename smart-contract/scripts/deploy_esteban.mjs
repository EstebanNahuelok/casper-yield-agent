#!/usr/bin/env node
/**
 * deploy_esteban.mjs — Deploys SimplePool + new YieldVault using TransactionV1 (Casper 2.x).
 *
 * Steps:
 *   1. Deploy SimplePool.wasm  (SessionBuilder → putTransaction)
 *   2. Deploy YieldVault.wasm  (SessionBuilder → putTransaction)
 *   3. Call vault.set_pool(pool_address) via ContractCallBuilder
 *
 * After this, run the seed step:
 *   python scripts/deploy_esteban.py --seed-only --pool-pkg <package_hash>
 *
 * Usage:
 *   node scripts/deploy_esteban.mjs
 */

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { createRequire } from 'module';
import https from 'https';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_DIR  = join(__dirname, '..');
const FRONTEND_DIR = join(PROJECT_DIR, '..', 'frontend');

// Load casper-js-sdk from the frontend node_modules
const require = createRequire(import.meta.url);
const sdk = require(join(FRONTEND_DIR, 'node_modules', 'casper-js-sdk'));
const { RpcClient, HttpHandler, SessionBuilder, ContractCallBuilder, PrivateKey, KeyAlgorithm, CLValue, CLTypeUInt8, Args, Key } = sdk;

// ── Configuration ─────────────────────────────────────────────────────────────
const API_KEY    = '019e9858-3950-7a48-9236-b704ba3e82f2';
const RPC_HOST   = 'node.testnet.cspr.cloud';
const RPC_URL    = `https://${RPC_HOST}/rpc`;
const CHAIN      = 'casper-test';
const OWNER_HASH = '9aff699d6b6be610644357d8fc1eb1f3c622110b553f9402a0e836ecbfc96b84';

const GAS_DEPLOY = 500_000_000_000; // 500 CSPR — gas for WASM install
const GAS_CALL   = 10_000_000_000;  // 10 CSPR  — gas for entry point call

const INITIAL_SCSPR_MOTES = 187_000_000_000n; // 187 sCSPR in motes

const POOL_WASM        = join(PROJECT_DIR, 'wasm', 'simple_pool.wasm');
const VAULT_WASM       = join(PROJECT_DIR, 'wasm', 'yield_vault.wasm');
const PROXY_CALLER_WASM = join(PROJECT_DIR, 'vendor', 'odra-casper-rpc-client', 'resources', 'proxy_caller_with_return.wasm');
const PEM_PATH   = join(PROJECT_DIR, '..', 'casper-key.pem');
const ENV_PATH   = join(__dirname, '.livenet.env');

const SEED_CSPR_MOTES = 200_000_000_000n; // 200 CSPR to seed pool

// ── Helpers ───────────────────────────────────────────────────────────────────
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

/** Raw JSON-RPC POST — bypasses casper-js-sdk deserialization quirks. */
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
        res.on('end', () => {
          try { resolve(JSON.parse(data)); }
          catch (e) { reject(e); }
        });
      }
    );
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

async function getNamedKeys(apiKey) {
  const resp = await rpcPost('query_global_state',
    { key: `account-hash-${OWNER_HASH}`, path: [] }, apiKey);
  const namedKeys =
    resp?.result?.stored_value?.Account?.named_keys ??
    resp?.result?.stored_value?.AddressableEntity?.named_keys ??
    [];
  return namedKeys; // [{name, key}, ...]
}

async function pollForNewKeys(knownKeys, apiKey, label, timeoutMs = 300_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    await sleep(8_000);
    try {
      const keys = await getNamedKeys(apiKey);
      const newKeys = keys.filter(nk => !knownKeys.has(nk.name));
      if (newKeys.length > 0) {
        console.log(`  New keys for ${label}:`, newKeys.map(nk => `${nk.name}=${nk.key}`));
        return keys;
      }
      console.log(`  Polling for ${label}... (${keys.length} total, 0 new)`);
    } catch (e) {
      console.log('  Poll error:', e.message ?? e);
    }
  }
  throw new Error(`Timeout waiting for ${label} keys`);
}

async function waitForTx(rpc, txHash, label) {
  console.log(`  Watching tx ${txHash.slice(0, 16)}...`);
  const deadline = Date.now() + 300_000;
  while (Date.now() < deadline) {
    await sleep(8_000);
    try {
      const info = await rpc.getTransactionByTransactionHash(txHash);
      const execResult = info?.executionInfo?.executionResult;
      if (execResult) {
        // SDK may camelCase or preserve snake_case; check both
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
      // not yet in chain, keep polling
    }
  }
  throw new Error(`Timeout waiting for ${label}`);
}

function findHash(keys, namePattern) {
  const found = keys.find(nk => nk.name.includes(namePattern));
  if (!found) return '';
  // Key may be "hash-<hex>", "contract-package-wasm-<hex>", "package-<hex>", or raw hex
  const key = found.key;
  return key
    .replace(/^contract-package-wasm-/, '')
    .replace(/^contract-package-/, '')
    .replace(/^package-wasm-/, '')
    .replace(/^package-/, '')
    .replace(/^hash-/, '');
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function seedOnly(poolPkg) {
  const env    = loadEnv();
  const apiKey = env.CSPR_CLOUD_AUTH_TOKEN ?? API_KEY;
  const pem        = readFileSync(PEM_PATH, 'utf-8');
  const privateKey = PrivateKey.fromPem(pem, KeyAlgorithm.ED25519);
  const handler = new HttpHandler(RPC_URL);
  handler.setCustomHeaders({ Authorization: apiKey });
  const rpc = new RpcClient(handler);
  const proxyWasm = new Uint8Array(readFileSync(PROXY_CALLER_WASM));
  const poolHashBytes = Buffer.from(poolPkg, 'hex');
  const seedArgs = Args.fromMap({
    package_hash:   CLValue.newCLByteArray(poolHashBytes),
    entry_point:    CLValue.newCLString('seed_cspr'),
    // Empty RuntimeArgs serialized = 4 zero bytes, passed as List<U8>
    args:           CLValue.newCLList(CLTypeUInt8, [0,0,0,0].map(b => CLValue.newCLUint8(b))),
    attached_value: CLValue.newCLUInt512(SEED_CSPR_MOTES),
    amount:         CLValue.newCLUInt512(SEED_CSPR_MOTES),
  });
  const seedTx = new SessionBuilder()
    .from(privateKey.publicKey)
    .wasm(proxyWasm)
    // no .installOrUpgrade() → regular session call
    .runtimeArgs(seedArgs)
    .chainName(CHAIN)
    .payment(Number(SEED_CSPR_MOTES) + GAS_CALL)
    .build();
  seedTx.sign(privateKey);
  const seedPut    = await rpc.putTransaction(seedTx);
  const seedTxHash = seedPut.transactionHash?.toHex?.() ?? String(seedPut.transactionHash);
  console.log('seed_cspr tx hash:', seedTxHash);
  await waitForTx(rpc, seedTxHash, 'seed_cspr');
  console.log('Pool seeded with 200 CSPR!');
  console.log(`https://testnet.cspr.live/transaction/${seedTxHash}`);
}

async function main() {
  const env    = loadEnv();
  const apiKey = env.CSPR_CLOUD_AUTH_TOKEN ?? API_KEY;

  const pem        = readFileSync(PEM_PATH, 'utf-8');
  const privateKey = PrivateKey.fromPem(pem, KeyAlgorithm.ED25519);
  console.log('Public key:', privateKey.publicKey.toHex());

  const handler = new HttpHandler(RPC_URL);
  handler.setCustomHeaders({ Authorization: apiKey });
  const rpc = new RpcClient(handler);

  const poolWasm  = new Uint8Array(readFileSync(POOL_WASM));
  const vaultWasm = new Uint8Array(readFileSync(VAULT_WASM));
  console.log(`Pool WASM:  ${poolWasm.length.toLocaleString()} bytes`);
  console.log(`Vault WASM: ${vaultWasm.length.toLocaleString()} bytes`);

  // ── 0. Snapshot named keys ──────────────────────────────────────────────────
  console.log('\n[0] Snapshotting current named keys...');
  const initKeys = await getNamedKeys(apiKey);
  const knownBefore = new Set(initKeys.map(nk => nk.name));
  console.log('  Existing:', [...knownBefore]);

  // ── 1. Deploy SimplePool ────────────────────────────────────────────────────
  console.log('\n[1] Deploying SimplePool...');
  // Odra requires these config args for every fresh contract install
  const poolArgs = Args.fromMap({
    odra_cfg_package_hash_key_name: CLValue.newCLString('SimplePool_package_hash'),
    odra_cfg_allow_key_override:    CLValue.newCLValueBool(true),
    odra_cfg_is_upgradable:         CLValue.newCLValueBool(true),
    odra_cfg_is_upgrade:            CLValue.newCLValueBool(false),
    initial_scspr_reserve:          CLValue.newCLUInt512(INITIAL_SCSPR_MOTES),
  });
  const poolTx = new SessionBuilder()
    .from(privateKey.publicKey)
    .wasm(poolWasm)
    .installOrUpgrade()
    .runtimeArgs(poolArgs)
    .chainName(CHAIN)
    .payment(GAS_DEPLOY)
    .build();
  poolTx.sign(privateKey);

  const poolPut   = await rpc.putTransaction(poolTx);
  const poolTxHash = poolPut.transactionHash?.toHex?.() ?? String(poolPut.transactionHash);
  console.log('  Pool tx hash:', poolTxHash);

  await waitForTx(rpc, poolTxHash, 'SimplePool deploy');
  const afterPool     = await pollForNewKeys(knownBefore, apiKey, 'SimplePool');
  const knownAfterPool = new Set(afterPool.map(nk => nk.name));

  // Odra names the keys: <ModuleName>_package_hash, <ModuleName>_contract_hash
  // ModuleName = "SimplePool" → snake_case → "simple_pool"? or PascalCase? Let's check both
  const newPoolKeys = afterPool.filter(nk => !knownBefore.has(nk.name));
  const poolPackageHash  = findHash(newPoolKeys, 'package_hash') || findHash(newPoolKeys, 'package');
  const poolContractHash = findHash(newPoolKeys.filter(nk => !nk.name.includes('package')), '_hash') ||
                           findHash(newPoolKeys, '_hash');
  console.log('  Pool contract hash:', poolContractHash);
  console.log('  Pool package hash: ', poolPackageHash);
  if (!poolPackageHash) {
    console.log('  All new pool keys:', newPoolKeys);
    throw new Error('Could not detect pool package hash');
  }

  // ── 2. Deploy YieldVault ────────────────────────────────────────────────────
  console.log('\n[2] Deploying YieldVault...');
  const agentKey  = Key.newKey(`account-hash-${OWNER_HASH}`);
  // Use YieldVault2 key name to avoid conflicting with the existing YieldVault deploy
  const vaultArgs = Args.fromMap({
    odra_cfg_package_hash_key_name: CLValue.newCLString('YieldVault2_package_hash'),
    odra_cfg_allow_key_override:    CLValue.newCLValueBool(true),
    odra_cfg_is_upgradable:         CLValue.newCLValueBool(true),
    odra_cfg_is_upgrade:            CLValue.newCLValueBool(false),
    agent:                          CLValue.newCLKey(agentKey),
  });
  const vaultTx   = new SessionBuilder()
    .from(privateKey.publicKey)
    .wasm(vaultWasm)
    .installOrUpgrade()
    .runtimeArgs(vaultArgs)
    .chainName(CHAIN)
    .payment(GAS_DEPLOY)
    .build();
  vaultTx.sign(privateKey);

  const vaultPut    = await rpc.putTransaction(vaultTx);
  const vaultTxHash = vaultPut.transactionHash?.toHex?.() ?? String(vaultPut.transactionHash);
  console.log('  Vault tx hash:', vaultTxHash);

  await waitForTx(rpc, vaultTxHash, 'YieldVault deploy');
  const afterVault      = await pollForNewKeys(knownAfterPool, apiKey, 'YieldVault2');
  const newVaultKeys    = afterVault.filter(nk => !knownAfterPool.has(nk.name));
  const vaultPackageHash  = findHash(newVaultKeys, 'YieldVault2_package_hash') ||
                            findHash(newVaultKeys, 'package_hash') || findHash(newVaultKeys, 'package');
  const vaultContractHash = findHash(newVaultKeys.filter(nk => !nk.name.includes('package')), 'YieldVault2') ||
                            findHash(newVaultKeys.filter(nk => !nk.name.includes('package')), '_hash') ||
                            findHash(newVaultKeys, '_hash');
  console.log('  Vault contract hash:', vaultContractHash);
  console.log('  Vault package hash: ', vaultPackageHash);
  if (!vaultPackageHash) {
    console.log('  All new vault keys:', newVaultKeys);
    throw new Error('Could not detect vault package hash');
  }

  // ── 3. Call vault.set_pool(pool_address) ────────────────────────────────────
  console.log('\n[3] Setting pool address in vault...');
  // Odra Address for a contract = Key::Hash(package_hash_bytes)
  const poolAddrKey  = Key.newKey(`hash-${poolPackageHash}`);
  const setPoolArgs  = Args.fromMap({ pool: CLValue.newCLKey(poolAddrKey) });
  const setPoolTx    = new ContractCallBuilder()
    .from(privateKey.publicKey)
    .byPackageHash(vaultPackageHash)
    .entryPoint('set_pool')
    .runtimeArgs(setPoolArgs)
    .chainName(CHAIN)
    .payment(GAS_CALL)
    .build();
  setPoolTx.sign(privateKey);

  const setPoolPut    = await rpc.putTransaction(setPoolTx);
  const setPoolTxHash = setPoolPut.transactionHash?.toHex?.() ?? String(setPoolPut.transactionHash);
  console.log('  set_pool tx hash:', setPoolTxHash);
  await waitForTx(rpc, setPoolTxHash, 'set_pool');

  // ── 4. Seed pool with 200 CSPR via proxy_caller (TransactionV1 session) ─────
  console.log('\n[4] Seeding pool with 200 CSPR...');
  const proxyWasm = new Uint8Array(readFileSync(PROXY_CALLER_WASM));
  // Empty RuntimeArgs serialised as Casper binary: 4-byte little-endian count = 0
  const emptyArgs = new Uint8Array([0, 0, 0, 0]);
  const poolHashBytes = Buffer.from(poolPackageHash, 'hex');
  const seedArgs = Args.fromMap({
    package_hash:   CLValue.newCLByteArray(poolHashBytes),
    entry_point:    CLValue.newCLString('seed_cspr'),
    // Empty RuntimeArgs serialized = 4 zero bytes, passed as List<U8>
    args:           CLValue.newCLList(CLTypeUInt8, [0,0,0,0].map(b => CLValue.newCLUint8(b))),
    attached_value: CLValue.newCLUInt512(SEED_CSPR_MOTES),
    amount:         CLValue.newCLUInt512(SEED_CSPR_MOTES),
  });
  const seedTx = new SessionBuilder()
    .from(privateKey.publicKey)
    .wasm(proxyWasm)
    // no .installOrUpgrade() → regular session call
    .runtimeArgs(seedArgs)
    .chainName(CHAIN)
    .payment(Number(SEED_CSPR_MOTES) + GAS_CALL)
    .build();
  seedTx.sign(privateKey);
  const seedPut    = await rpc.putTransaction(seedTx);
  const seedTxHash = seedPut.transactionHash?.toHex?.() ?? String(seedPut.transactionHash);
  console.log('  seed_cspr tx hash:', seedTxHash);
  await waitForTx(rpc, seedTxHash, 'seed_cspr');

  // ── Summary ─────────────────────────────────────────────────────────────────
  console.log('\n' + '='.repeat(60));
  console.log('  DEPLOYMENT COMPLETE');
  console.log('='.repeat(60));
  console.log(`VAULT_CONTRACT_HASH=hash-${vaultContractHash}`);
  console.log(`VAULT_PACKAGE_HASH=${vaultPackageHash}`);
  console.log(`POOL_CONTRACT_HASH=hash-${poolContractHash}`);
  console.log(`POOL_PACKAGE_HASH=${poolPackageHash}`);
  console.log();
  console.log(`Vault: https://testnet.cspr.live/contract-package/${vaultPackageHash}`);
  console.log(`Pool:  https://testnet.cspr.live/contract-package/${poolPackageHash}`);
  console.log(`Pool deploy tx:  https://testnet.cspr.live/transaction/${poolTxHash}`);
  console.log(`Vault deploy tx: https://testnet.cspr.live/transaction/${vaultTxHash}`);
  console.log(`set_pool tx:     https://testnet.cspr.live/transaction/${setPoolTxHash}`);
  console.log(`seed_cspr tx:    https://testnet.cspr.live/transaction/${seedTxHash}`);
}

const args = process.argv.slice(2);
if (args[0] === '--seed-only') {
  const poolPkg = args[1]?.replace('hash-', '').trim();
  if (!poolPkg) { console.error('Usage: node deploy_esteban.mjs --seed-only <pool_package_hash>'); process.exit(1); }
  seedOnly(poolPkg).catch(e => { console.error('\nFATAL:', e.message ?? e); process.exit(1); });
} else {
  main().catch(e => { console.error('\nFATAL:', e.message ?? e); process.exit(1); });
}
