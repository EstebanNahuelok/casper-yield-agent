# Casper Yield Agent

Autonomous yield farming agent on Casper Network Testnet — Casper Agentic Buildathon 2026.

## Architecture

```
casper-yield-agent/
├── agent/                  # Python agent (Persona 2)
│   ├── main.py             # Entry point: agent loop + API server
│   ├── src/
│   │   ├── config.py       # Settings via pydantic-settings + .env
│   │   ├── agent_loop.py   # Core loop: observe → decide → execute → log
│   │   ├── mcp_clients/
│   │   │   ├── casper_client.py   # Casper MCP Server (balance, rates, contract calls)
│   │   │   └── trade_client.py    # CSPR.trade MCP (swap quotes, pool APY)
│   │   ├── llm/
│   │   │   └── gemini.py          # Google Gemini decision engine
│   │   ├── chain/
│   │   │   └── executor.py        # On-chain execution via YieldVault contract
│   │   ├── api/
│   │   │   └── server.py          # FastAPI: GET /status for the frontend
│   │   └── state/
│   │       ├── models.py          # Pydantic models (Decision, MarketData, AgentState)
│   │       └── store.py           # In-memory async state store
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── contracts/              # Odra/Rust YieldVault contract (Persona 1)
└── frontend/               # React dashboard (Persona 3)
```

## Agent loop (every 5 minutes)

1. **Observe** — fetch balance via Casper MCP, pool APY via CSPR.trade MCP
2. **Decide** — send market data to Gemini 1.5 Pro; receive SWAP or HOLD + reasoning
3. **Execute** — if SWAP: call `execute_swap` on YieldVault contract
4. **Log** — always call `log_action` on YieldVault (auditable on-chain)
5. **Expose** — FastAPI `/status` endpoint updated for the React dashboard

Swap rules enforced in the LLM prompt:
- Pool APY > current APY + 2% → SWAP
- Slippage > 1.5% → HOLD
- Balance < 100 CSPR → HOLD

## Setup

```bash
cd agent
cp .env.example .env
# fill in .env with your keys

pip install -r requirements.txt
python main.py
```

The agent exposes:
- `GET http://localhost:8000/status` — current agent state (for the frontend)
- `GET http://localhost:8000/health`

## Prerequisites

```bash
# Casper MCP Server (local)
dotnet tool install -g CasperMcp
casper-mcp --api-key YOUR_KEY --network testnet --transport sse --port 3001
```

Get your CSPR.cloud API key at https://cspr.cloud (free for testnet).

## Running tests

```bash
cd agent
pip install pytest pytest-asyncio
pytest
```
