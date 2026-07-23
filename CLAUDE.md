# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Casper Yield Agent** — a Casper Agentic Buildathon 2026 submission. Three components:

1. **Smart contract** (repo root) — `YieldVault` written in Rust with the Odra framework, deployed to Casper Testnet.
2. **Agent** (`agent/`) — Python autonomous agent that runs the observe→decide→execute loop and exposes a FastAPI HTTP API.
3. **Frontend** (`frontend/`) — React/TypeScript dashboard that displays agent status.

## Smart Contract (Rust / Odra)

```bash
# Run tests (in-process, no WASM)
cargo odra test

# Build WASM for Casper
cargo odra build -b casper

# Run tests against Casper WASM backend
cargo odra test -b casper
```

Source layout: `src/vault.rs` (entry points), `src/errors.rs`, `src/events.rs`, `src/types.rs`, `src/tests/`.

## Agent (Python)

The venv lives at the **repo root** (`venv/`), shared by all Python code.

```powershell
# Setup (first time)
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r agent\requirements.txt

# Run agent (from agent/ directory, with venv active or using venv Python)
cd agent
py main.py
```

```bash
# Run tests
cd agent
pytest

# Run a single test file
pytest tests/test_decision.py
```

Linter: `ruff` (line-length 100, target py312). Tests use `pytest-asyncio` with `asyncio_mode = "auto"`.

The `.env` file must be placed inside `agent/` (next to `main.py`). Required vars: `GROQ_API_KEY`, `CSPR_CLOUD_API_KEY`, `VAULT_PUBLIC_KEY`, `VAULT_OWNER_SECRET_KEY`, `SCSPR_CONTRACT_HASH`. See `agent/README.md` for the full table.

**Agent startup dependency**: The agent loop will not start until the Casper MCP Server is reachable at `CASPER_MCP_URL` (default `http://localhost:3001/mcp`). Start that first:

```powershell
CasperMcp.exe --transport http --network testnet --port 3001
```

**One-command stack**: `.\start-all.bat` at the repo root launches the MCP server, agent, and an ngrok tunnel in separate windows.

## Agent Architecture

`agent/src/agent_loop.py` runs `agent_loop()` which coordinates:
- `CasperMCPClient` — reads vault balance via Casper MCP Server (local .NET process on `:3001`)
- `CSPRTradeRestClient` — fetches APY/slippage from `api.cspr.trade` (remote REST, stateless)
- `GroqDecisionEngine` — sends market summary to Groq LLM (`llama-3.3-70b-versatile`), returns `SWAP` or `HOLD`
- `ChainExecutor` — executes swaps and logs every decision on-chain for auditability

State is held in `state_store` (in-memory) and exposed via FastAPI at `GET /status` and `GET /health`.

## Frontend (React / TypeScript)

```bash
cd frontend
npm install     # first time
npm run dev     # dev server (Vite)
npm run build   # production build
npm run lint    # ESLint
```

Stack: React 19, TanStack Router, TanStack Query, Tailwind CSS v4, shadcn/ui (Radix), `casper-js-sdk` for wallet integration.

The frontend polls `GET /status` from the agent API (default `http://localhost:8000`). The agent URL is configured via `agentApi.ts`.

## Key Contract Addresses (Testnet)

- **Contract Hash**: `hash-0bcc5c99c90390e2f8c2259f097a860e93f14edd7c24047451986d44b99d3011`
- **Contract Package Hash**: `hash-d21679ac36362ccd8e3504d6a18c1386d5e1455ca7f948ee843be182ee8d2e38`
- **Owner Wallet**: `01c3acc1af3faa221073e5928bf74d58ad9ad9e58be2bdc39218a25e5ddff72309`
