"""
Motor de decisión por enjambre (colmena).
Tres agentes especialistas corren en paralelo y votan por mayoría.
"""
import asyncio
import json
from typing import Optional

import structlog
from groq import AsyncGroq

from ..config import settings
from ..state.models import Action, AgentVote, Decision, SwarmResult

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# System prompts — uno por especialista
# ---------------------------------------------------------------------------

RISK_AGENT_PROMPT = """Sos el Agente de Riesgo de un sistema de yield farming autónomo en Casper Network Testnet.

Tu ÚNICA responsabilidad es evaluar el riesgo de ejecutar un swap en este momento.
Analizás exclusivamente:
- estimated_slippage: si supera {max_slippage_pct}% → HOLD obligatorio
- balance_cspr: si está por debajo de {min_balance_cspr} CSPR → HOLD obligatorio
- Riesgo de pérdida por precio de impacto y condiciones adversas del mercado

Reglas estrictas:
- Si el slippage estimado supera {max_slippage_pct}% → votá HOLD sin importar nada más
- Si el balance es menor a {min_balance_cspr} CSPR → votá HOLD sin importar nada más
- Si ambas condiciones son aceptables → podés votar SWAP si el riesgo es bajo

Respondé ÚNICAMENTE con un JSON válido, sin texto adicional, sin markdown:
{{"action": "SWAP" | "HOLD", "reasoning": "justificación breve enfocada en riesgo"}}
"""

YIELD_AGENT_PROMPT = """Sos el Agente de Rendimiento de un sistema de yield farming autónomo en Casper Network Testnet.

Tu ÚNICA responsabilidad es evaluar la oportunidad de rendimiento.
Analizás exclusivamente:
- pool_apy vs current_apy: la diferencia (delta APY) justifica el swap
- Si pool_apy es más de {min_apy_delta}% superior a current_apy → oportunidad real de SWAP
- Potencial de auto-compounding y rentabilidad proyectada

Reglas estrictas:
- Si pool_apy - current_apy < {min_apy_delta}% → votá HOLD (no vale la pena el costo del swap)
- Si el delta APY es suficiente → votá SWAP
- No te preocupés por el riesgo: eso es tarea del Agente de Riesgo

Respondé ÚNICAMENTE con un JSON válido, sin texto adicional, sin markdown:
{{"action": "SWAP" | "HOLD", "reasoning": "justificación breve enfocada en rendimiento"}}
"""

LIQUIDITY_AGENT_PROMPT = """Sos el Agente de Liquidez de un sistema de yield farming autónomo en Casper Network Testnet.

Tu ÚNICA responsabilidad es evaluar las condiciones de liquidez del pool.
Analizás exclusivamente:
- Profundidad del pool estimada por el slippage (slippage alto = pool poco profundo)
- Ratio implícito de reservas y precio de impacto para el volumen del swap
- Si las condiciones de liquidez son suficientes para ejecutar sin distorsionar el precio

Reglas estrictas:
- Si estimated_slippage > 0.8% → el pool tiene liquidez insuficiente → votá HOLD
- Si la liquidez es adecuada para el volumen a operar → votá SWAP

Respondé ÚNICAMENTE con un JSON válido, sin texto adicional, sin markdown:
{{"action": "SWAP" | "HOLD", "reasoning": "justificación breve enfocada en liquidez"}}
"""


# ---------------------------------------------------------------------------
# SpecialistAgent
# ---------------------------------------------------------------------------

class SpecialistAgent:
    """Agente especialista: emite un voto binario sobre los datos de mercado."""

    def __init__(self, name: str, system_prompt: str, client: AsyncGroq):
        self.name = name
        self._system = system_prompt
        self._client = client

    async def vote(self, market_data_str: str) -> AgentVote:
        response = await self._client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": self._system},
                {"role": "user", "content": f"Datos de mercado actuales:\n{market_data_str}"},
            ],
            temperature=0.1,
            max_tokens=256,
        )

        raw = response.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        log.debug("swarm.specialist.response", agent=self.name, raw=raw)

        data = json.loads(raw)
        vote = AgentVote(
            agent_name=self.name,
            action=Action(data["action"]),
            reasoning=data["reasoning"],
        )
        log.info("swarm.specialist.vote", agent=self.name, action=vote.action)
        return vote


# ---------------------------------------------------------------------------
# SwarmDecisionEngine
# ---------------------------------------------------------------------------

class SwarmDecisionEngine:
    """
    Motor de decisión por enjambre.
    Corre 3 especialistas en paralelo y aplica votación mayoritaria.

    API compatible con GroqDecisionEngine: decide() acepta market_data_str y devuelve Decision.
    decide_with_votes() devuelve la tupla (Decision, list[AgentVote]) para el loop principal.
    """

    def __init__(self):
        self._client = AsyncGroq(api_key=settings.groq_api_key)

        risk_prompt = RISK_AGENT_PROMPT.format(
            max_slippage_pct=settings.max_slippage_pct,
            min_balance_cspr=settings.min_balance_cspr,
        )
        yield_prompt = YIELD_AGENT_PROMPT.format(
            min_apy_delta=settings.min_apy_delta,
        )
        liquidity_prompt = LIQUIDITY_AGENT_PROMPT.format(
            max_slippage_pct=settings.max_slippage_pct,
        )

        self._specialists = [
            SpecialistAgent("risk_agent", risk_prompt, self._client),
            SpecialistAgent("yield_agent", yield_prompt, self._client),
            SpecialistAgent("liquidity_agent", liquidity_prompt, self._client),
        ]

    async def decide_with_votes(
        self, market_data_str: str
    ) -> tuple[Decision, list[AgentVote]]:
        """
        Ejecuta los 3 especialistas en paralelo y agrega sus votos.

        Política de fallos:
          - 1 falla → 2 votos restantes, threshold=2 exige ambos SWAP para ejecutar.
          - 2+ fallan → HOLD conservador.
          - Nunca propaga excepción al ciclo principal.
        """
        tasks = [
            asyncio.create_task(agent.vote(market_data_str))
            for agent in self._specialists
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        votes: list[AgentVote] = []
        for agent, result in zip(self._specialists, results):
            if isinstance(result, Exception):
                log.error("swarm.specialist.failed", agent=agent.name, error=str(result))
            else:
                votes.append(result)

        tally: dict[str, int] = {Action.SWAP.value: 0, Action.HOLD.value: 0}
        for v in votes:
            tally[v.action.value] += 1

        swap_votes = tally[Action.SWAP.value]
        total_valid = len(votes)

        if total_valid == 0:
            log.error("swarm.all_failed", fallback="HOLD")
            final_action = Action.HOLD
            reasoning = "Todos los agentes del enjambre fallaron. Acción conservadora: HOLD."
        elif swap_votes >= settings.swarm_vote_threshold:
            final_action = Action.SWAP
            swap_reasons = [v.reasoning for v in votes if v.action == Action.SWAP]
            hold_reasons = [v.reasoning for v in votes if v.action == Action.HOLD]
            reasoning = f"Enjambre SWAP ({swap_votes}/{total_valid} votos): " + "; ".join(swap_reasons)
            if hold_reasons:
                reasoning += ". Disidencia: " + "; ".join(hold_reasons)
        else:
            final_action = Action.HOLD
            hold_reasons = [v.reasoning for v in votes if v.action == Action.HOLD]
            swap_reasons = [v.reasoning for v in votes if v.action == Action.SWAP]
            reasoning = f"Enjambre HOLD ({total_valid - swap_votes}/{total_valid} votos): " + "; ".join(hold_reasons)
            if swap_reasons:
                reasoning += ". A favor: " + "; ".join(swap_reasons)

        amount: Optional[float] = None
        token_in: Optional[str] = None
        token_out: Optional[str] = None
        if final_action == Action.SWAP:
            try:
                mkt = json.loads(market_data_str)
                amount = max(1.0, mkt.get("balance_cspr", 0.0) * 0.5)
                token_in = "CSPR"
                token_out = "sCSPR"
            except (json.JSONDecodeError, KeyError):
                pass

        decision = Decision(
            action=final_action,
            reasoning=reasoning,
            amount=amount,
            token_in=token_in,
            token_out=token_out,
        )

        log.info(
            "swarm.decision",
            action=final_action,
            swap_votes=swap_votes,
            total_valid=total_valid,
        )

        return decision, votes

    async def decide(self, market_data_str: str) -> Decision:
        """API compatible con GroqDecisionEngine.decide()."""
        decision, _ = await self.decide_with_votes(market_data_str)
        return decision
