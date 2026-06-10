import asyncio
from datetime import datetime

from .models import AgentState, Decision, DecisionHistoryEntry, MarketData


class StateStore:
    def __init__(self):
        self._state = AgentState()
        self._lock = asyncio.Lock()

    async def get(self) -> AgentState:
        async with self._lock:
            return self._state.model_copy()

    async def update_status(self, status: str) -> None:
        async with self._lock:
            self._state.status = status
            self._state.last_updated = datetime.utcnow()

    async def update_market_data(self, data: MarketData) -> None:
        async with self._lock:
            self._state.last_market_data = data
            self._state.balance_cspr = data.balance_cspr
            self._state.last_updated = datetime.utcnow()

    async def record_decision(self, decision: Decision, tx_hash: str | None = None) -> None:
        async with self._lock:
            self._state.last_decision = decision
            if tx_hash:
                self._state.last_tx_hash = tx_hash
                self._state.actions_taken += 1

            entry = DecisionHistoryEntry(
                timestamp=datetime.utcnow(),
                action=decision.action,
                reasoning=decision.reasoning,
                deploy_hash=tx_hash,
            )
            self._state.decision_history.append(entry)
            # Mantener solo las últimas 10 decisiones (FIFO)
            self._state.decision_history = self._state.decision_history[-10:]

            self._state.last_updated = datetime.utcnow()

    async def record_error(self, error: str) -> None:
        async with self._lock:
            self._state.errors.append(error)
            # Mantener solo los últimos 20 errores
            self._state.errors = self._state.errors[-20:]
            self._state.last_updated = datetime.utcnow()


# Singleton compartido entre el loop y la API
state_store = StateStore()
