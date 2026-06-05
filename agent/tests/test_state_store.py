import pytest

from src.state.models import Action, Decision
from src.state.store import StateStore


@pytest.mark.asyncio
async def test_initial_state_is_idle():
    store = StateStore()
    state = await store.get()
    assert state.status == "idle"
    assert state.actions_taken == 0


@pytest.mark.asyncio
async def test_record_swap_increments_actions():
    store = StateStore()
    decision = Decision(action=Action.SWAP, reasoning="test", amount=100.0, token_in="CSPR", token_out="sCSPR")
    await store.record_decision(decision, tx_hash="deploy-abc123")

    state = await store.get()
    assert state.actions_taken == 1
    assert state.last_tx_hash == "deploy-abc123"


@pytest.mark.asyncio
async def test_hold_does_not_increment_actions():
    store = StateStore()
    decision = Decision(action=Action.HOLD, reasoning="slippage too high")
    await store.record_decision(decision, tx_hash=None)

    state = await store.get()
    assert state.actions_taken == 0
