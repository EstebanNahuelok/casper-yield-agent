import json
from unittest.mock import AsyncMock, patch

import pytest

from src.state.models import Action, Decision


@pytest.mark.asyncio
async def test_decision_swap_when_apy_delta_sufficient():
    mock_response_text = json.dumps({
        "action": "SWAP",
        "reasoning": "Pool APY is 3% above current, slippage within limits.",
        "amount": 500.0,
        "token_in": "CSPR",
        "token_out": "sCSPR",
    })

    with patch("google.generativeai.GenerativeModel") as MockModel:
        mock_model = MockModel.return_value
        mock_model.generate_content_async = AsyncMock(
            return_value=type("R", (), {"text": mock_response_text})()
        )

        from src.llm.gemini import GeminiDecisionEngine
        engine = GeminiDecisionEngine()
        engine._model = mock_model

        decision = await engine.decide('{"balance_cspr": 1000, "current_apy": 5.0, "pool_apy": 8.5}')

    assert decision.action == Action.SWAP
    assert decision.amount == 500.0


@pytest.mark.asyncio
async def test_decision_hold_when_slippage_high():
    mock_response_text = json.dumps({
        "action": "HOLD",
        "reasoning": "Slippage 2.1% exceeds maximum allowed 1.5%.",
        "amount": None,
        "token_in": None,
        "token_out": None,
    })

    with patch("google.generativeai.GenerativeModel") as MockModel:
        mock_model = MockModel.return_value
        mock_model.generate_content_async = AsyncMock(
            return_value=type("R", (), {"text": mock_response_text})()
        )

        from src.llm.gemini import GeminiDecisionEngine
        engine = GeminiDecisionEngine()
        engine._model = mock_model

        decision = await engine.decide('{"balance_cspr": 1000, "estimated_slippage": 2.1}')

    assert decision.action == Action.HOLD
    assert decision.amount is None
