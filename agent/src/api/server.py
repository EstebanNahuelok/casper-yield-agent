from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..chain.executor import ChainExecutor
from ..config import settings
from ..state.models import AgentState
from ..state.store import state_store

app = FastAPI(title="Casper Yield Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en prod restringir al dominio del frontend
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    ok: bool
    timestamp: datetime
    agent_status: str


class ConfigResponse(BaseModel):
    check_interval_seconds: int
    min_apy_delta: float
    max_slippage_pct: float
    min_balance_cspr: float
    swarm_vote_threshold: int
    casper_network: str
    vault_public_key: str


@app.get("/status", response_model=AgentState)
async def get_status() -> AgentState:
    """
    Estado completo del agente.
    Consumido por el dashboard React cada pocos segundos.
    """
    return await state_store.get()


@app.get("/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    """
    Parámetros de configuración del agente (read-only).
    Consumido por la página Agent.tsx del dashboard.
    """
    return ConfigResponse(
        check_interval_seconds=settings.check_interval_seconds,
        min_apy_delta=settings.min_apy_delta,
        max_slippage_pct=settings.max_slippage_pct,
        min_balance_cspr=settings.min_balance_cspr,
        swarm_vote_threshold=settings.swarm_vote_threshold,
        casper_network=settings.casper_network,
        vault_public_key=settings.vault_public_key,
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    state = await state_store.get()
    return HealthResponse(
        ok=True,
        timestamp=datetime.now(timezone.utc),
        agent_status=state.status,
    )


class DepositRequest(BaseModel):
    amount_cspr: float


class DepositResponse(BaseModel):
    ok: bool
    deploy_hash: str | None = None
    error: str | None = None


@app.post("/deposit", response_model=DepositResponse)
async def deposit_funds(req: DepositRequest) -> DepositResponse:
    """
    Deposita CSPR en el vault. Llama al entry point payable deposit()
    vía pycspr + proxy WASM (soporta transferred_value que el SDK JS no soporta).
    """
    if req.amount_cspr <= 0:
        return DepositResponse(ok=False, error="El monto debe ser mayor a 0")
    try:
        executor = ChainExecutor()
        deploy_hash = await executor.deposit(req.amount_cspr)
        return DepositResponse(ok=True, deploy_hash=deploy_hash)
    except Exception as exc:
        return DepositResponse(ok=False, error=str(exc))
