from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Action(str, Enum):
    SWAP = "SWAP"
    HOLD = "HOLD"


class Decision(BaseModel):
    action: Action
    reasoning: str
    amount: Optional[float] = None
    token_in: Optional[str] = None
    token_out: Optional[str] = None


class MarketData(BaseModel):
    balance_cspr: float
    current_apy: float
    pool_apy: float
    estimated_slippage: float
    cspr_price_usd: float
    timestamp: datetime = datetime.utcnow()


class AgentState(BaseModel):
    status: str = "idle"
    last_decision: Optional[Decision] = None
    last_market_data: Optional[MarketData] = None
    balance_cspr: float = 0.0
    actions_taken: int = 0
    last_tx_hash: Optional[str] = None
    last_updated: datetime = datetime.utcnow()
    errors: list[str] = []
