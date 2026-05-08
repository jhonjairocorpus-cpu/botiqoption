import sys

from bot.main import main


DEFAULT_SIGNAL_ARGS = [
    "signals",
    "--asset",
    "EURUSD-OTC",
    "--model",
    "models\\EURUSD_OTC_1m_5000_model.json",
    "--telegram",
    "--timeframe",
    "60",
    "--confirmation-timeframe",
    "300",
    "--context-timeframe",
    "900",
    "--signal-lookback",
    "15",
    "--expiry-candles",
    "2",
    "--min-model-probability",
    "0.55",
    "--min-score",
    "70",
]


if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.extend(DEFAULT_SIGNAL_ARGS)
    main()
