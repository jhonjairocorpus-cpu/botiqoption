from dataclasses import dataclass
from typing import List, Optional

from .indicators import bollinger_bands, crossed_above, crossed_below, ema, macd
from .model import LogisticModel
from .types import Candle, Signal


@dataclass(frozen=True)
class StrategyConfig:
    bollinger_period: int = 20
    bollinger_deviations: float = 2.0
    ema_trend_period: int = 200
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    signal_lookback: int = 5
    min_model_probability: float = 0.56


def build_features_at(candles: List[Candle], index: int, config: StrategyConfig) -> Optional[List[float]]:
    if index <= 0 or index >= len(candles):
        return None

    closes = [candle.close for candle in candles]
    upper, middle, lower = bollinger_bands(closes, config.bollinger_period, config.bollinger_deviations)
    trend = ema(closes, config.ema_trend_period)
    macd_line, signal_line, histogram = macd(closes, config.macd_fast, config.macd_slow, config.macd_signal)

    needed = [upper[index], middle[index], lower[index], trend[index], macd_line[index], signal_line[index], histogram[index]]
    if any(value is None for value in needed):
        return None

    close = closes[index]
    previous_close = closes[index - 1]
    band_range = upper[index] - lower[index]  # type: ignore[operator]
    if close == 0 or previous_close == 0 or band_range == 0:
        return None

    band_width = band_range / close
    band_position = (close - lower[index]) / band_range  # type: ignore[operator]
    ema_distance = (close - trend[index]) / close  # type: ignore[operator]
    macd_distance = (macd_line[index] - signal_line[index]) / close  # type: ignore[operator]
    momentum = (close - previous_close) / previous_close

    return [band_width, band_position, ema_distance, macd_distance, histogram[index] / close, momentum]  # type: ignore[operator]


def generate_signals(candles: List[Candle], config: StrategyConfig, model: Optional[LogisticModel] = None) -> List[Signal]:
    closes = [candle.close for candle in candles]
    upper, _, lower = bollinger_bands(closes, config.bollinger_period, config.bollinger_deviations)
    trend = ema(closes, config.ema_trend_period)
    macd_line, signal_line, _ = macd(closes, config.macd_fast, config.macd_slow, config.macd_signal)
    signals: List[Signal] = []

    start = max(config.ema_trend_period, config.bollinger_period, config.macd_slow + config.macd_signal)
    for index in range(start, len(candles) - 1):
        candle = candles[index]
        previous = index - 1

        if trend[index] is None or upper[index] is None or lower[index] is None:
            continue

        bullish_trend = candle.close > trend[index]  # type: ignore[operator]
        bearish_trend = candle.close < trend[index]  # type: ignore[operator]
        lookback_start = max(start, index - config.signal_lookback + 1)
        bullish_macd = macd_line[index] is not None and signal_line[index] is not None and macd_line[index] > signal_line[index]
        bearish_macd = macd_line[index] is not None and signal_line[index] is not None and macd_line[index] < signal_line[index]
        recent_bullish_cross = any(
            crossed_above(macd_line[cross_index - 1], signal_line[cross_index - 1], macd_line[cross_index], signal_line[cross_index])
            for cross_index in range(lookback_start, index + 1)
        )
        recent_bearish_cross = any(
            crossed_below(macd_line[cross_index - 1], signal_line[cross_index - 1], macd_line[cross_index], signal_line[cross_index])
            for cross_index in range(lookback_start, index + 1)
        )
        recent_lower_touch = any(
            lower[touch_index] is not None and candles[touch_index].low <= lower[touch_index]  # type: ignore[operator]
            for touch_index in range(lookback_start, index + 1)
        )
        recent_upper_touch = any(
            upper[touch_index] is not None and candles[touch_index].high >= upper[touch_index]  # type: ignore[operator]
            for touch_index in range(lookback_start, index + 1)
        )

        side: Optional[str] = None
        reason = ""
        if bullish_trend and bullish_macd and recent_bullish_cross and recent_lower_touch:
            side = "CALL"
            reason = "Tendencia alcista EMA200 + MACD alcista reciente + toque reciente banda inferior"
        elif bearish_trend and bearish_macd and recent_bearish_cross and recent_upper_touch:
            side = "PUT"
            reason = "Tendencia bajista EMA200 + MACD bajista reciente + toque reciente banda superior"

        if side is None:
            continue

        probability = None
        if model is not None:
            features = build_features_at(candles, index, config)
            if features is None:
                continue
            probability_up = model.predict_proba(features)
            probability = probability_up if side == "CALL" else 1.0 - probability_up
            if probability < config.min_model_probability:
                continue

        signals.append(Signal(index=index, timestamp=candle.timestamp, side=side, price=candle.close, reason=reason, probability=probability))

    return signals
