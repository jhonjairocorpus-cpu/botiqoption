from dataclasses import dataclass
from typing import List, Optional

from .strategy import StrategyConfig, generate_signals
from .model import LogisticModel
from .types import Candle, Trade


@dataclass(frozen=True)
class BacktestResult:
    trades: List[Trade]
    wins: int
    losses: int
    win_rate: float
    profit: float


def run_backtest(
    candles: List[Candle],
    config: StrategyConfig,
    model: Optional[LogisticModel] = None,
    expiry_candles: int = 1,
    stake: float = 1.0,
    payout_rate: float = 0.82,
) -> BacktestResult:
    signals = generate_signals(candles, config, model)
    trades: List[Trade] = []

    for signal in signals:
        exit_index = signal.index + expiry_candles
        if exit_index >= len(candles):
            continue

        entry = signal.price
        exit_price = candles[exit_index].close
        won = exit_price > entry if signal.side == "CALL" else exit_price < entry
        payout = stake * payout_rate if won else -stake
        trades.append(
            Trade(
                entry_index=signal.index,
                exit_index=exit_index,
                side=signal.side,
                entry_price=entry,
                exit_price=exit_price,
                payout=payout,
                won=won,
                reason=signal.reason,
            )
        )

    wins = sum(1 for trade in trades if trade.won)
    losses = len(trades) - wins
    win_rate = wins / len(trades) if trades else 0.0
    profit = sum(trade.payout for trade in trades)
    return BacktestResult(trades=trades, wins=wins, losses=losses, win_rate=win_rate, profit=profit)
