"""
Tests del enjambre de agentes especialistas.
Sigue el mismo patrón que test_decision.py: sin conftest, mock via AsyncMock,
inyección directa en engine._client y specialist._client.
"""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.state.models import Action, Decision


def _make_groq_response(action: str, reasoning: str) -> MagicMock:
    """Construye un mock de respuesta Groq con el JSON esperado."""
    content = json.dumps({"action": action, "reasoning": reasoning})
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _inject_mock(engine, responses: list) -> None:
    """Inyecta un AsyncMock compartido en el engine y todos sus specialists."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=responses)
    engine._client = mock_client
    for specialist in engine._specialists:
        specialist._client = mock_client


@pytest.mark.asyncio
async def test_swarm_majority_swap():
    """2 votos SWAP + 1 HOLD → decisión final SWAP."""
    from src.llm.swarm import SwarmDecisionEngine

    engine = SwarmDecisionEngine()
    _inject_mock(engine, [
        _make_groq_response("SWAP", "slippage aceptable, riesgo bajo"),
        _make_groq_response("SWAP", "APY delta suficiente para ejecutar"),
        _make_groq_response("HOLD", "liquidez insuficiente en el pool"),
    ])

    decision, votes = await engine.decide_with_votes(
        '{"balance_cspr": 500, "current_apy": 5.0, "pool_apy": 8.5, "estimated_slippage": 0.5}'
    )

    assert decision.action == Action.SWAP
    assert len(votes) == 3
    assert sum(1 for v in votes if v.action == Action.SWAP) == 2
    assert decision.amount == 250.0
    assert decision.token_in == "CSPR"
    assert decision.token_out == "sCSPR"


@pytest.mark.asyncio
async def test_swarm_majority_hold():
    """1 voto SWAP + 2 HOLD → decisión final HOLD."""
    from src.llm.swarm import SwarmDecisionEngine

    engine = SwarmDecisionEngine()
    _inject_mock(engine, [
        _make_groq_response("HOLD", "slippage demasiado alto"),
        _make_groq_response("SWAP", "APY delta es positivo"),
        _make_groq_response("HOLD", "pool con baja profundidad"),
    ])

    decision, votes = await engine.decide_with_votes(
        '{"balance_cspr": 500, "current_apy": 5.0, "pool_apy": 7.0, "estimated_slippage": 1.2}'
    )

    assert decision.action == Action.HOLD
    assert len(votes) == 3
    assert decision.amount is None


@pytest.mark.asyncio
async def test_swarm_one_specialist_fails():
    """Si 1 especialista falla, el enjambre continúa con los 2 restantes."""
    from src.llm.swarm import SwarmDecisionEngine

    engine = SwarmDecisionEngine()

    call_count = 0

    async def side_effect_with_failure(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise Exception("Groq API timeout")
        return _make_groq_response("SWAP", "decisión correcta")

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=side_effect_with_failure)
    engine._client = mock_client
    for specialist in engine._specialists:
        specialist._client = mock_client

    decision, votes = await engine.decide_with_votes(
        '{"balance_cspr": 500, "current_apy": 5.0, "pool_apy": 9.0, "estimated_slippage": 0.3}'
    )

    assert len(votes) == 2


@pytest.mark.asyncio
async def test_swarm_all_fail_returns_hold():
    """Si todos los especialistas fallan, la decisión es HOLD conservador."""
    from src.llm.swarm import SwarmDecisionEngine

    engine = SwarmDecisionEngine()
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=Exception("API no disponible")
    )
    engine._client = mock_client
    for specialist in engine._specialists:
        specialist._client = mock_client

    decision, votes = await engine.decide_with_votes('{"balance_cspr": 500}')

    assert decision.action == Action.HOLD
    assert len(votes) == 0


@pytest.mark.asyncio
async def test_swarm_decide_backward_compat():
    """decide() sin votos es compatible con la API de GroqDecisionEngine."""
    from src.llm.swarm import SwarmDecisionEngine

    engine = SwarmDecisionEngine()
    _inject_mock(engine, [
        _make_groq_response("HOLD", "condiciones no favorables"),
        _make_groq_response("HOLD", "APY delta insuficiente"),
        _make_groq_response("HOLD", "liquidez baja"),
    ])

    result = await engine.decide('{"balance_cspr": 50}')

    assert isinstance(result, Decision)
    assert result.action in (Action.SWAP, Action.HOLD)


@pytest.mark.asyncio
async def test_swarm_vote_tally_correctness():
    """last_swarm_result.vote_tally refleja los votos correctamente después de record_decision."""
    from src.llm.swarm import SwarmDecisionEngine
    from src.state.store import StateStore

    engine = SwarmDecisionEngine()
    _inject_mock(engine, [
        _make_groq_response("SWAP", "riesgo ok"),
        _make_groq_response("SWAP", "APY delta ok"),
        _make_groq_response("HOLD", "liquidez baja"),
    ])

    decision, votes = await engine.decide_with_votes(
        '{"balance_cspr": 500, "current_apy": 5.0, "pool_apy": 8.5, "estimated_slippage": 0.4}'
    )

    store = StateStore()
    await store.record_decision(decision, tx_hash=None, swarm_votes=votes)
    state = await store.get()

    assert state.last_swarm_result is not None
    assert state.last_swarm_result.vote_tally["SWAP"] == 2
    assert state.last_swarm_result.vote_tally["HOLD"] == 1
    assert state.last_swarm_result.final_action == Action.SWAP
    assert len(state.last_swarm_result.votes) == 3


@pytest.mark.asyncio
async def test_swarm_unanimous_swap():
    """3 votos SWAP → SWAP, reasoning sintetiza los 3 agentes."""
    from src.llm.swarm import SwarmDecisionEngine

    engine = SwarmDecisionEngine()
    _inject_mock(engine, [
        _make_groq_response("SWAP", "slippage bajo"),
        _make_groq_response("SWAP", "APY delta alto"),
        _make_groq_response("SWAP", "pool con liquidez suficiente"),
    ])

    decision, votes = await engine.decide_with_votes(
        '{"balance_cspr": 1000, "current_apy": 3.0, "pool_apy": 12.0, "estimated_slippage": 0.2}'
    )

    assert decision.action == Action.SWAP
    assert all(v.action == Action.SWAP for v in votes)
    assert "3/3" in decision.reasoning
