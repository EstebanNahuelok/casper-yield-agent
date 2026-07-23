from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Action(str, Enum):
    SWAP = "SWAP"
    SWAP_BACK = "SWAP_BACK"
    HOLD = "HOLD"


class Decision(BaseModel):
    action: Action
    reasoning: str
    amount: Optional[float] = None
    amount_out: Optional[float] = None
    token_in: Optional[str] = None
    token_out: Optional[str] = None


class AgentVote(BaseModel):
    agent_name: str
    action: Action
    reasoning: str


class SwarmResult(BaseModel):
    votes: list["AgentVote"]
    final_action: Action
    vote_tally: dict[str, int]


class DecisionHistoryEntry(BaseModel):
    timestamp: datetime
    action: Action
    reasoning: str
    deploy_hash: Optional[str] = None
    swarm_votes: Optional[list["AgentVote"]] = None


class MarketData(BaseModel):
    balance_cspr: float
    current_apy: float
    pool_apy: float
    estimated_slippage: float
    cspr_price_usd: float
    timestamp: datetime = datetime.now(timezone.utc)


class AgentState(BaseModel):
    status: str = "idle"
    last_decision: Optional[Decision] = None
    last_market_data: Optional[MarketData] = None
    decision_history: list[DecisionHistoryEntry] = []
    balance_cspr: float = 0.0
    scspr_balance_cspr: float = 0.0
    actions_taken: int = 0
    last_tx_hash: Optional[str] = None
    last_updated: datetime = datetime.now(timezone.utc)
    errors: list[str] = []
    last_swarm_result: Optional[SwarmResult] = None
