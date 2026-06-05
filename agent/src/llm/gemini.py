import json

import structlog
from google import genai
from google.genai import types

from ..config import settings
from ..state.models import Decision

log = structlog.get_logger()

SYSTEM_PROMPT = """Sos un agente de yield farming autónomo en Casper Network Testnet.

Reglas estrictas:
- Si el APY del pool sCSPR está más de {min_apy_delta}% por encima del APY actual → acción SWAP
- Si el slippage estimado es mayor a {max_slippage_pct}% → acción HOLD (no ejecutar)
- Si el balance es menor a {min_balance_cspr} CSPR → acción HOLD (no ejecutar)
- SIEMPRE justificá tu decisión antes de actuar

Respondé ÚNICAMENTE con un JSON válido, sin texto adicional, sin markdown:
{{"action": "SWAP" | "HOLD", "reasoning": "explicación breve", "amount": number | null, "token_in": "string | null", "token_out": "string | null"}}
"""


class GeminiDecisionEngine:
    def __init__(self):
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._generate_config = types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=512,
        )
        self._system = SYSTEM_PROMPT.format(
            min_apy_delta=settings.min_apy_delta,
            max_slippage_pct=settings.max_slippage_pct,
            min_balance_cspr=settings.min_balance_cspr,
        )

    async def decide(self, market_data_str: str) -> Decision:
        prompt = f"{self._system}\n\nDatos de mercado actuales:\n{market_data_str}"

        response = await self._client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=self._generate_config,
        )

        raw = response.text.strip()

        # Limpiar posibles bloques markdown que Gemini pueda devolver
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        log.debug("gemini.response", raw=raw)

        data = json.loads(raw)
        decision = Decision(**data)
        log.info("gemini.decision", action=decision.action, reasoning=decision.reasoning)
        return decision
