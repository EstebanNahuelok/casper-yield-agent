# YieldVault

Smart contract for the **Casper Agentic Buildathon 2026** — a yield farming vault controlled by an autonomous AI agent on Casper Network.

## Overview

YieldVault is an on-chain vault where users deposit CSPR and an authorized AI agent manages yield strategies. All agent decisions are recorded on-chain as immutable, verifiable evidence.

### Roles

| Role | Description |
|------|-------------|
| **Owner** | Deploys and administers the vault. Can pause, unpause, transfer ownership, and rotate the agent. |
| **Agent** | Autonomous AI that logs decisions and executes swaps on behalf of the vault. Cannot withdraw user funds. |
| **Users** | Deposit and withdraw their own CSPR independently. Balances are tracked per address. |

### Features

- Per-user CSPR balance tracking (`Mapping<Address, U512>`)
- Immutable on-chain action log with full history (`Mapping<u64, ActionEntry>`)
- On-chain swap record with full history (`Mapping<u64, SwapRecord>`)
- Vault pause/unpause with idempotency
- Ownership transfer with event emission
- Agent rotation
- Checked arithmetic throughout — no silent overflow
- 8 on-chain events covering all state transitions

## Stack

- **Casper Network** (Testnet)
- **Rust**
- **Odra Framework** `=2.7.2` (pinned)
- **cargo-odra**

## Build

Install [cargo-odra](https://github.com/odradev/cargo-odra) first.

```bash
# Run tests (in-process, no WASM required)
cargo odra test

# Build WASM for Casper
cargo odra build -b casper

# Run tests against the Casper WASM backend
cargo odra test -b casper
```

## Deploy

Set the agent address before deploying:

```bash
export ODRA_AGENT_ADDRESS="account-hash-<hex>"
cargo odra run -b casper --bin yield_vault_cli -- deploy
```

## CLI Scenarios

```bash
# Query a user's balance (in motes and CSPR)
cargo odra run -b casper --bin yield_vault_cli -- scenario get-balance --user account-hash-<hex>
```

## Source Layout

```
src/
  vault.rs      — YieldVault contract (entry points, business logic)
  errors.rs     — VaultError enum
  events.rs     — All on-chain events
  types.rs      — ActionEntry, SwapRecord structs
  tests/
    test_deposit.rs
    test_withdraw.rs
    test_logging.rs
    test_access.rs
    test_accounting.rs
    test_integration.rs
```

## Tests

50 tests covering deposits, withdrawals, access control, action logging, swap execution, accounting invariants, integration flows, and event verification.

```bash
cargo test
```
