#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# ── require token ──────────────────────────────────────────────────────────────
if [ -z "${CSPR_CLOUD_AUTH_TOKEN:-}" ]; then
  echo "ERROR: CSPR_CLOUD_AUTH_TOKEN is not set."
  echo ""
  echo "  1. Register free at https://cspr.cloud"
  echo "  2. Copy your API token"
  echo "  3. Run: export CSPR_CLOUD_AUTH_TOKEN=your_token_here"
  echo "  4. Run this script again"
  exit 1
fi

echo "[deploy] Token: ${CSPR_CLOUD_AUTH_TOKEN:0:8}... (${#CSPR_CLOUD_AUTH_TOKEN} chars)"

# ── start proxy ────────────────────────────────────────────────────────────────
echo "[deploy] Starting auth proxy (ports 7777 / 9999)..."
python3 scripts/cspr_proxy.py &
PROXY_PID=$!
trap 'kill $PROXY_PID 2>/dev/null || true' EXIT

# wait for proxy to be ready
for i in {1..10}; do
  if curl -s --connect-timeout 1 http://127.0.0.1:7777/ >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done
echo "[deploy] Proxy ready."

# ── build CLI if needed ────────────────────────────────────────────────────────
echo "[deploy] Building CLI binary..."
cargo build --bin yield_vault_cli 2>&1 | grep -E "^error|Compiling yield_vault|Finished" || true

CLI="./target/debug/yield_vault_cli"
if [ ! -f "$CLI" ]; then
  echo "ERROR: CLI binary not found at $CLI"
  exit 1
fi

# ── deploy ────────────────────────────────────────────────────────────────────
echo "[deploy] Deploying YieldVault to casper-test..."
DEPLOY_OUTPUT=$("$CLI" deploy 2>&1)
echo "$DEPLOY_OUTPUT"

# ── extract deploy hash ───────────────────────────────────────────────────────
DEPLOY_HASH=$(echo "$DEPLOY_OUTPUT" | grep -oE '[0-9a-f]{64}' | head -1)
if [ -z "$DEPLOY_HASH" ]; then
  echo "WARNING: Could not extract deploy hash from output."
fi

# ── extract contract package hash ────────────────────────────────────────────
CONTRACT_PACKAGE_HASH=$(echo "$DEPLOY_OUTPUT" | grep -i "package.hash\|contract.package" | grep -oE '[0-9a-f]{64}' | head -1)

# ── save deploy-info.env ──────────────────────────────────────────────────────
DEPLOY_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
cat > deploy-info.env <<EOF
DEPLOY_HASH=${DEPLOY_HASH:-UNKNOWN}
CONTRACT_PACKAGE_HASH=${CONTRACT_PACKAGE_HASH:-UNKNOWN}
PUBLIC_KEY=01c3acc1af3faa221073e5928bf74d58ad9ad9e58be2bdc39218a25e5ddff72309
ACCOUNT_HASH=account-hash-9aff699d6b6be610644357d8fc1eb1f3c622110b553f9402a0e836ecbfc96b84
NETWORK=casper-test
DEPLOY_DATE=${DEPLOY_DATE}
EOF

echo ""
echo "══════════════════════════════════════════════"
echo "  Deploy info saved to deploy-info.env"
echo "══════════════════════════════════════════════"
cat deploy-info.env

if [ -n "$DEPLOY_HASH" ] && [ "$DEPLOY_HASH" != "UNKNOWN" ]; then
  echo ""
  echo "  Explorer: https://testnet.cspr.live/transaction/${DEPLOY_HASH}"
fi
