import asyncio
from datetime import datetime, timezone

from .models import AgentState, AgentVote, Decision, DecisionHistoryEntry, MarketData, SwarmResult


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
            self._state.last_updated = datetime.now(timezone.utc)

    async def update_market_data(self, data: MarketData) -> None:
        async with self._lock:
            self._state.last_market_data = data
            self._state.balance_cspr = data.balance_cspr
            self._state.last_updated = datetime.now(timezone.utc)

    async def record_decision(
        self,
        decision: Decision,
        tx_hash: str | None = None,
        swarm_votes: list[AgentVote] | None = None,
    ) -> None:
        async with self._lock:
            self._state.last_decision = decision
            if tx_hash:
                self._state.last_tx_hash = tx_hash
                self._state.actions_taken += 1
                if decision.amount_out:
                    self._state.scspr_balance_cspr += decision.amount_out
                if decision.amount:
                    self._state.balance_cspr = max(0.0, self._state.balance_cspr - decision.amount)

            entry = DecisionHistoryEntry(
                timestamp=datetime.now(timezone.utc),
                action=decision.action,
                reasoning=decision.reasoning,
                deploy_hash=tx_hash,
                swarm_votes=swarm_votes,
            )
            self._state.decision_history.append(entry)
            # Mantener solo las últimas 10 decisiones (FIFO)
            self._state.decision_history = self._state.decision_history[-10:]

            if swarm_votes is not None:
                tally: dict[str, int] = {"SWAP": 0, "HOLD": 0}
                for v in swarm_votes:
                    tally[v.action.value] = tally.get(v.action.value, 0) + 1
                self._state.last_swarm_result = SwarmResult(
                    votes=swarm_votes,
                    final_action=decision.action,
                    vote_tally=tally,
                )

            self._state.last_updated = datetime.now(timezone.utc)

    async def record_error(self, error: str) -> None:
        async with self._lock:
            self._state.errors.append(error)
            # Mantener solo los últimos 20 errores
            self._state.errors = self._state.errors[-20:]
            self._state.last_updated = datetime.now(timezone.utc)


# Singleton compartido entre el loop y la API
state_store = StateStore()
