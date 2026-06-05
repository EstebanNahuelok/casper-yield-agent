from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..state.models import AgentState
from ..state.store import state_store

app = FastAPI(title="Casper Yield Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en prod restringir al dominio del frontend
    allow_methods=["GET"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    ok: bool
    timestamp: datetime
    agent_status: str


@app.get("/status", response_model=AgentState)
async def get_status() -> AgentState:
    """
    Estado completo del agente.
    Consumido por el dashboard React cada pocos segundos.
    """
    return await state_store.get()


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    state = await state_store.get()
    return HealthResponse(
        ok=True,
        timestamp=datetime.utcnow(),
        agent_status=state.status,
    )
