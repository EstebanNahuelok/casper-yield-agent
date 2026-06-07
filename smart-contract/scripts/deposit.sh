#!/usr/bin/env bash
# Call the vault deposit function with a specified amount of CSPR.
#
# Required env vars (or set in .livenet.env):
#   CSPR_CLOUD_AUTH_TOKEN          - API token from cspr.cloud
#   ODRA_CASPER_LIVENET_SECRET_KEY_PATH - path to secret_key.pem
#
# Usage:
#   export CSPR_CLOUD_AUTH_TOKEN=your_token
#   export ODRA_CASPER_LIVENET_SECRET_KEY_PATH=/path/to/secret_key.pem
#   bash scripts/deposit.sh 200          # 200 CSPR
#   bash scripts/deposit.sh 500          # 500 CSPR
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# ── load optional .livenet.env ────────────────────────────────────────────────
LIVENET_ENV="${PROJECT_DIR}/scripts/.livenet.env"
if [ -f "$LIVENET_ENV" ]; then
  echo "[deposit] Loading $LIVENET_ENV"
  set -o allexport
  source "$LIVENET_ENV"
  set +o allexport
fi

# ── validate required vars ────────────────────────────────────────────────────
if [ -z "${CSPR_CLOUD_AUTH_TOKEN:-}" ]; then
  echo "ERROR: CSPR_CLOUD_AUTH_TOKEN is not set."
  echo "  export CSPR_CLOUD_AUTH_TOKEN=your_token_here"
  exit 1
fi

if [ -z "${ODRA_CASPER_LIVENET_SECRET_KEY_PATH:-}" ]; then
  echo "ERROR: ODRA_CASPER_LIVENET_SECRET_KEY_PATH is not set."
  echo "  export ODRA_CASPER_LIVENET_SECRET_KEY_PATH=/path/to/secret_key.pem"
  exit 1
fi

if [ ! -f "$ODRA_CASPER_LIVENET_SECRET_KEY_PATH" ]; then
  echo "ERROR: secret key not found at $ODRA_CASPER_LIVENET_SECRET_KEY_PATH"
  exit 1
fi

# ── parse amount ──────────────────────────────────────────────────────────────
CSPR_AMOUNT="${1:-200}"
AMOUNT_MOTES=$(python3 -c "print(int(${CSPR_AMOUNT}) * 1_000_000_000)")
echo "[deposit] Amount: ${CSPR_AMOUNT} CSPR = ${AMOUNT_MOTES} motes"

# ── Odra livenet config ───────────────────────────────────────────────────────
export ODRA_CASPER_LIVENET_NODE_ADDRESS="${ODRA_CASPER_LIVENET_NODE_ADDRESS:-http://127.0.0.1:7777/rpc}"
export ODRA_CASPER_LIVENET_EVENTS_URL="${ODRA_CASPER_LIVENET_EVENTS_URL:-http://127.0.0.1:9999/events/main}"
export ODRA_CASPER_LIVENET_CHAIN_NAME="${ODRA_CASPER_LIVENET_CHAIN_NAME:-casper-test}"

# ── start proxy ───────────────────────────────────────────────────────────────
echo "[deposit] Starting auth proxy..."
python3 scripts/cspr_proxy.py &
PROXY_PID=$!
trap 'kill $PROXY_PID 2>/dev/null || true' EXIT

for i in {1..10}; do
  if curl -s --connect-timeout 1 http://127.0.0.1:7777/ >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done
echo "[deposit] Proxy ready."

# ── build CLI if needed ───────────────────────────────────────────────────────
CLI="./target/debug/yield_vault_cli"
if [ ! -f "$CLI" ]; then
  echo "[deposit] Building CLI..."
  cargo build --bin yield_vault_cli 2>&1 | grep -E "^error|Compiling yield_vault|Finished" || true
fi

if [ ! -f "$CLI" ]; then
  echo "ERROR: CLI binary not found."
  exit 1
fi

# ── execute deposit ───────────────────────────────────────────────────────────
echo "[deposit] Calling deposit on contract..."
"$CLI" run deposit --amount_motes "$AMOUNT_MOTES"

echo ""
echo "[deposit] Done. Check explorer:"
echo "  https://testnet.cspr.live/contract-package/$(grep CONTRACT_PACKAGE_HASH deploy-info.env | cut -d= -f2)"
