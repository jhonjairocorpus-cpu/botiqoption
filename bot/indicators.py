from typing import Iterable, List, Optional, Tuple


MaybeFloat = Optional[float]


def sma(values: List[float], period: int) -> List[MaybeFloat]:
    result: List[MaybeFloat] = [None] * len(values)
    if period <= 0:
        raise ValueError("El periodo debe ser positivo.")

    rolling_sum = 0.0
    for index, value in enumerate(values):
        rolling_sum += value
        if index >= period:
            rolling_sum -= values[index - period]
        if index >= period - 1:
            result[index] = rolling_sum / period
    return result


def ema(values: List[float], period: int) -> List[MaybeFloat]:
    result: List[MaybeFloat] = [None] * len(values)
    if period <= 0:
        raise ValueError("El periodo debe ser positivo.")
    if len(values) < period:
        return result

    multiplier = 2.0 / (period + 1)
    current = sum(values[:period]) / period
    result[period - 1] = current

    for index in range(period, len(values)):
        current = (values[index] - current) * multiplier + current
        result[index] = current
    return result


def rolling_std(values: List[float], period: int) -> List[MaybeFloat]:
    averages = sma(values, period)
    result: List[MaybeFloat] = [None] * len(values)
    for index in range(period - 1, len(values)):
        mean = averages[index]
        if mean is None:
            continue
        window = values[index - period + 1 : index + 1]
        variance = sum((value - mean) ** 2 for value in window) / period
        result[index] = variance ** 0.5
    return result


def bollinger_bands(values: List[float], period: int = 20, deviations: float = 2.0) -> Tuple[List[MaybeFloat], List[MaybeFloat], List[MaybeFloat]]:
    middle = sma(values, period)
    std = rolling_std(values, period)
    upper: List[MaybeFloat] = [None] * len(values)
    lower: List[MaybeFloat] = [None] * len(values)

    for index, mean in enumerate(middle):
        if mean is None or std[index] is None:
            continue
        upper[index] = mean + deviations * std[index]
        lower[index] = mean - deviations * std[index]

    return upper, middle, lower


def macd(values: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[List[MaybeFloat], List[MaybeFloat], List[MaybeFloat]]:
    fast_ema = ema(values, fast)
    slow_ema = ema(values, slow)
    macd_line: List[MaybeFloat] = [None] * len(values)

    for index, (fast_value, slow_value) in enumerate(zip(fast_ema, slow_ema)):
        if fast_value is not None and slow_value is not None:
            macd_line[index] = fast_value - slow_value

    compact = [value for value in macd_line if value is not None]
    compact_signal = ema(compact, signal)
    signal_line: List[MaybeFloat] = [None] * len(values)
    first_valid = next((index for index, value in enumerate(macd_line) if value is not None), None)
    if first_valid is not None:
        for offset, value in enumerate(compact_signal):
            target = first_valid + offset
            if target < len(signal_line):
                signal_line[target] = value

    histogram: List[MaybeFloat] = [None] * len(values)
    for index in range(len(values)):
        if macd_line[index] is not None and signal_line[index] is not None:
            histogram[index] = macd_line[index] - signal_line[index]

    return macd_line, signal_line, histogram


def crossed_above(previous_left: MaybeFloat, previous_right: MaybeFloat, left: MaybeFloat, right: MaybeFloat) -> bool:
    return previous_left is not None and previous_right is not None and left is not None and right is not None and previous_left <= previous_right and left > right


def crossed_below(previous_left: MaybeFloat, previous_right: MaybeFloat, left: MaybeFloat, right: MaybeFloat) -> bool:
    return previous_left is not None and previous_right is not None and left is not None and right is not None and previous_left >= previous_right and left < right
