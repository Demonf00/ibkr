from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SignalAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Signal:
    strategy_name: str
    symbol: str
    action: SignalAction
    quantity: int = 0
    confidence: float = 0.0
    reason: str = ""
    expected_edge_bps: float = 0.0
    source_strategies: list[str] = field(default_factory=list)


@dataclass
class OrderRequest:
    symbol: str
    side: SignalAction
    quantity: int
    strategy_name: str
    reason: str = ""
    limit_price: Optional[float] = None
    source_strategies: list[str] = field(default_factory=list)