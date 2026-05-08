from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Candle:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(frozen=True)
class Signal:
    index: int
    timestamp: str
    side: str
    price: float
    reason: str
    probability: Optional[float] = None
    score: Optional[int] = None
    strength: Optional[str] = None
    context: Optional[str] = None


@dataclass(frozen=True)
class Trade:
    entry_index: int
    exit_index: int
    side: str
    entry_price: float
    exit_price: float
    payout: float
    won: bool
    reason: str
