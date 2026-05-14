from dataclasses import dataclass
from typing import List, Optional

from .indicators import bollinger_bands, ema, macd
from .strategy import StrategyConfig
from .types import Candle, Signal


@dataclass(frozen=True)
class TimeframeContext:
    label: str
    bias: str
    close: float
    ema: Optional[float]
    macd_above_signal: Optional[bool]
    band_width: Optional[float]


def timeframe_label(seconds: int) -> str:
    if seconds % 60 == 0:
        minutes = seconds // 60
        return f"{minutes}m"
    return f"{seconds}s"


def analyze_timeframe(candles: List[Candle], config: StrategyConfig, label: str) -> TimeframeContext:
    closes = [candle.close for candle in candles]
    if not candles:
        return TimeframeContext(label=label, bias="sin datos", close=0.0, ema=None, macd_above_signal=None, band_width=None)

    trend = ema(closes, config.ema_trend_period)
    macd_line, signal_line, _ = macd(closes, config.macd_fast, config.macd_slow, config.macd_signal)
    upper, _, lower = bollinger_bands(closes, config.bollinger_period, config.bollinger_deviations)
    index = len(candles) - 1
    close = closes[index]

    ema_value = trend[index]
    macd_value = macd_line[index]
    signal_value = signal_line[index]
    macd_above_signal = None
    if macd_value is not None and signal_value is not None:
        macd_above_signal = macd_value > signal_value

    band_width = None
    if close != 0 and upper[index] is not None and lower[index] is not None:
        band_width = (upper[index] - lower[index]) / close  # type: ignore[operator]

    if ema_value is None or macd_above_signal is None:
        bias = "neutral"
    elif close > ema_value and macd_above_signal:
        bias = "alcista"
    elif close < ema_value and not macd_above_signal:
        bias = "bajista"
    else:
        bias = "neutral"

    return TimeframeContext(
        label=label,
        bias=bias,
        close=close,
        ema=ema_value,
        macd_above_signal=macd_above_signal,
        band_width=band_width,
    )


def is_aligned(side: str, bias: str) -> bool:
    return (side == "CALL" and bias == "alcista") or (side == "PUT" and bias == "bajista")


def is_opposite(side: str, bias: str) -> bool:
    return (side == "CALL" and bias == "bajista") or (side == "PUT" and bias == "alcista")


def probability_points(probability: Optional[float]) -> int:
    if probability is None:
        return 0
    if probability >= 0.62:
        return 20
    if probability >= 0.58:
        return 15
    if probability >= 0.55:
        return 10
    return 0


def strength_from_score(score: int) -> str:
    if score >= 85:
        return "FUERTE"
    if score >= 70:
        return "MODERADA"
    return "DEBIL"


def score_signal(signal: Signal, context_5m: TimeframeContext, context_15m: TimeframeContext) -> Signal:
    score = 40 + probability_points(signal.probability)
    notes = []

    if is_aligned(signal.side, context_5m.bias):
        score += 25
        notes.append(f"{context_5m.label} alineado {context_5m.bias}")
    elif is_opposite(signal.side, context_5m.bias):
        score -= 25
        notes.append(f"{context_5m.label} en contra {context_5m.bias}")
    else:
        score += 10
        notes.append(f"{context_5m.label} neutral")

    if is_aligned(signal.side, context_15m.bias):
        score += 20
        notes.append(f"{context_15m.label} alineado {context_15m.bias}")
    elif is_opposite(signal.side, context_15m.bias):
        score -= 20
        notes.append(f"{context_15m.label} en contra {context_15m.bias}")
    else:
        score += 8
        notes.append(f"{context_15m.label} neutral")

    context = " | ".join(notes)
    return Signal(
        index=signal.index,
        timestamp=signal.timestamp,
        side=signal.side,
        price=signal.price,
        reason=signal.reason,
        probability=signal.probability,
        score=max(0, min(100, score)),
        strength=strength_from_score(max(0, min(100, score))),
        context=context,
    )
