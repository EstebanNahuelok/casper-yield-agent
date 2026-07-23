# Casper Yield Agent

> Autonomous yield farming agent on Casper Network — Casper Agentic Buildathon 2026 submission.

An AI-powered system that observes on-chain market conditions, decides whether to swap CSPR → sCSPR to maximize yield, and executes the decision autonomously. Every decision is recorded on-chain for full auditability.

**Live links**

| Resource | URL |
|----------|-----|
| Frontend (Vercel) | https://casper-yield-agent.vercel.app |
| Contract on Testnet | https://testnet.cspr.live/contract/0bcc5c99c90390e2f8c2259f097a860e93f14edd7c24047451986d44b99d3011 |
| Deploy transaction | https://testnet.cspr.live/deploy/87d049e49874173ce5ee3eb6e7333baeebd6e3be938e65aa6cae82bb7ba31ecb |

---

## What it does

1. **Observe** — reads the vault balance from the `YieldVault` contract via Casper MCP Server and fetches live APY and slippage from `api.cspr.trade`.
2. **Decide** — a swarm of 3 specialized LLM agents (Risk, Yield, Liquidity) each cast a vote in parallel using Groq `llama-3.3-70b-versatile`. Majority wins.
3. **Execute** — if the swarm votes SWAP, the agent sends a `execute_swap` transaction to the vault contract. Either way, the decision (action + full LLM reasoning) is written on-chain via `log_action`.
4. **Expose** — a FastAPI HTTP API publishes the agent state; the React dashboard polls it in real time.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend (React)                   │
│  Vercel · casper-yield-agent.vercel.app                 │
│  TanStack Router · TanStack Query · Tailwind v4         │
└──────────────────────┬──────────────────────────────────┘
                       │ GET /status  POST /deposit
┌──────────────────────▼──────────────────────────────────┐
│                  Agent (Python / FastAPI)                │
│  agent/  ·  localhost:8000  ·  ngrok tunnel for demos   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Observe → Decide → Execute          │   │
│  │                                                 │   │
│  │  CasperMCPClient ──► Casper MCP Server :3001    │   │
│  │  CSPRTradeRestClient ──► api.cspr.trade (REST)  │   │
│  │                                                 │   │
│  │  SwarmDecisionEngine (Groq)                     │   │
│  │    ├── risk_agent                               │   │
│  │    ├── yield_agent           3× llama-3.3-70b  │   │
│  │    └── liquidity_agent  (parallel, majority)    │   │
│  │                                                 │   │
│  │  ChainExecutor ──► YieldVault contract          │   │
│  └─────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │ TransactionV1 / Deploy
┌──────────────────────▼──────────────────────────────────┐
│              YieldVault Smart Contract (Rust / Odra)    │
│  Casper Testnet                                         │
│  deposit · withdraw · execute_swap · log_action         │
└─────────────────────────────────────────────────────────┘
```

### Components

| Component | Stack | Where it runs |
|-----------|-------|---------------|
| Smart contract | Rust · Odra 2.7.2 | Casper Testnet (always on) |
| Casper MCP Server | .NET 10 | Local · `:3001` |
| Agent + API | Python 3.12 · FastAPI · Groq | Local · `:8000` · ngrok for remote access |
| Frontend | React 19 · Vite · Tailwind v4 | Vercel (static) |

---

## Contract addresses (Testnet)

| Key | Value |
|-----|-------|
| Contract Hash | `hash-0bcc5c99c90390e2f8c2259f097a860e93f14edd7c24047451986d44b99d3011` |
| Contract Package Hash | `hash-d21679ac36362ccd8e3504d6a18c1386d5e1455ca7f948ee843be182ee8d2e38` |
| Owner Wallet | `01c3acc1af3faa221073e5928bf74d58ad9ad9e58be2bdc39218a25e5ddff72309` |
| Deploy Hash | `87d049e49874173ce5ee3eb6e7333baeebd6e3be938e65aa6cae82bb7ba31ecb` |

---

## Quick start

### Prerequisites

- Windows 10/11
- Python 3.12
- Node.js 20+
- Rust + `cargo-odra` (only if you want to rebuild the contract)
- [CasperMcp.exe](https://github.com/casper-ecosystem/casper-mcp) — .NET 10 binary
- [ngrok](https://ngrok.com) account with a static domain (for remote dashboard access)

### 1. Clone and set up the Python venv

```powershell
git clone https://github.com/EstebanNahuelok/casper-yield-agent.git
cd casper-yield-agent

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r agent\requirements.txt
```

### 2. Configure environment variables

Create `agent\.env` (next to `agent\main.py`):

```dotenv
GROQ_API_KEY=gsk_...
CSPR_CLOUD_API_KEY=019e...
VAULT_PUBLIC_KEY=01c3acc1...
VAULT_OWNER_SECRET_KEY=MC4CAQAwBQYDK2VwBCIEIL...
SCSPR_CONTRACT_HASH=a4f6d5e6...
CASPER_NETWORK=testnet
CHECK_INTERVAL_SECONDS=300
```

Full variable reference: [`agent/README.md`](agent/README.md#1-configurar-el-env)

### 3. Launch the full stack

```powershell
.\start-all.bat
```

This opens three terminal windows:

1. **Casper MCP Server** — `.NET` process on `:3001` (blockchain reads via MCP protocol)
2. **Agent** — Python loop + FastAPI on `:8000`
3. **ngrok tunnel** — exposes `:8000` publicly so the Vercel frontend can reach the local agent

Wait ~5 seconds for the MCP server to initialize, then the agent will connect automatically.

### 4. Open the dashboard

- **Local:** http://localhost:8000/status (raw JSON)
- **Remote:** https://casper-yield-agent.vercel.app (set `VITE_AGENT_API_URL` in Vercel to your ngrok URL)

---

## Running components individually

```powershell
# Casper MCP Server
CasperMcp.exe --transport http --network testnet --port 3001

# Agent (separate terminal, with venv active or using venv Python)
cd agent
..\venv\Scripts\python.exe main.py

# ngrok tunnel (separate terminal)
ngrok http --domain=<your-static-domain>.ngrok-free.app 8000
```

---

## Smart contract

The `YieldVault` contract is written in Rust using the [Odra framework](https://odra.dev) (v2.7.2).

```bash
cd smart-contract

# Run in-process tests (fast, no WASM)
cargo odra test

# Build WASM for Casper
cargo odra build -b casper

# Run tests against Casper WASM backend
cargo odra test -b casper
```

Entry points:

| Function | Caller | Description |
|----------|--------|-------------|
| `deposit()` | Anyone | Payable — deposits CSPR into the vault |
| `withdraw(amount)` | Depositor | Withdraws caller's own CSPR |
| `execute_swap(...)` | Agent only | Executes real CSPR → sCSPR swap via SimplePool AMM (cross-contract call) |
| `log_action(action_type, params)` | Agent only | Records every decision on-chain with full LLM reasoning |

---

## Frontend

```bash
cd frontend
npm install
npm run dev      # dev server at localhost:5173
npm run build    # production build
```

Set `VITE_AGENT_API_URL` to your agent URL (local or ngrok) in `.env.local` or in the Vercel dashboard.

---

## How the swarm works

Instead of a single LLM call, the agent runs three specialist agents **in parallel**, each focused on a different risk dimension:

| Agent | Evaluates | SWAP condition |
|-------|-----------|----------------|
| `risk_agent` | Slippage, balance floor | slippage < 1.5% AND balance ≥ 100 CSPR |
| `yield_agent` | APY delta | pool APY − current APY ≥ 2% |
| `liquidity_agent` | Pool depth | slippage < 0.8% |

All three call Groq `llama-3.3-70b-versatile` concurrently. The majority vote (≥ 2 of 3) determines the final action. The full reasoning from each agent is serialized as JSON and written on-chain via `log_action`.

---

## Roadmap

### Q2 2026 (current — Buildathon)
- [x] YieldVault contract deployed on Casper Testnet (Odra 2.7.2)
- [x] Autonomous observe → decide → execute loop with swarm LLM
- [x] On-chain audit log for every decision
- [x] Live dashboard on Vercel
- [x] Deposit via agent API (payable entry point via pycspr + proxy WASM)

### Q3 2026
- [x] SimplePool AMM integration — live CSPR/sCSPR swaps with real fund movement (deployed on testnet, `set_pool` configured)
- [ ] Mainnet deployment after security audit
- [ ] x402 protocol integration for trustless agent payments
- [ ] Multi-strategy support (staking, LP positions, lending)
- [ ] Withdraw button in dashboard with wallet signing

### Q4 2026
- [ ] Token-gated vault access (whitelist / deposit caps)
- [ ] Performance fee mechanism (protocol revenue)
- [ ] Mobile-friendly dashboard
- [ ] Governance module — community voting on strategy parameters
- [ ] Public API for third-party integrations

---

## Socials

| Platform | Link |
|----------|------|
| GitHub | https://github.com/EstebanNahuelok/casper-yield-agent |
| Twitter / X | @CasperYieldAgent *(coming soon)* |
| Discord | *(coming soon)* |
| Telegram | *(coming soon)* |

---

## License

MIT

---

*Built for the [Casper Agentic Buildathon 2026](https://casper.network/buildathon). Powered by [Odra](https://odra.dev), [Groq](https://groq.com), and [Casper MCP](https://github.com/casper-ecosystem/casper-mcp).*
