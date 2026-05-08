from typing import List, Tuple

from .strategy import StrategyConfig, build_features_at
from .types import Candle


def build_training_samples(candles: List[Candle], config: StrategyConfig, horizon: int = 1) -> List[Tuple[List[float], int]]:
    samples: List[Tuple[List[float], int]] = []
    start = max(config.ema_trend_period, config.bollinger_period, config.macd_slow + config.macd_signal)
    for index in range(start, len(candles) - horizon):
        features = build_features_at(candles, index, config)
        if features is None:
            continue
        label = 1 if candles[index + horizon].close > candles[index].close else 0
        samples.append((features, label))
    return samples
