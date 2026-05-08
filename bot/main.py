import argparse

from .backtest import run_backtest
from .data import fetch_iqoption_candles, generate_sample_candles, read_candles_csv, write_candles_csv
from .live import LiveConfig, connect_iqoption, list_open_assets, run_live_trader
from .model import LogisticModel, train_logistic_regression
from .signals import SignalBotConfig, run_signal_bot
from .strategy import StrategyConfig
from .telegram import load_telegram_config, send_telegram_message
from .training import build_training_samples


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bot cuantitativo con Bollinger, MACD y EMA200.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sample = subparsers.add_parser("generate-sample", help="Genera velas sinteticas para probar.")
    sample.add_argument("--output", required=True)
    sample.add_argument("--rows", type=int, default=600)

    fetch = subparsers.add_parser("fetch-iq", help="Descarga velas historicas desde IQ Option.")
    fetch.add_argument("--asset", required=True)
    fetch.add_argument("--timeframe", type=int, default=60, help="Timeframe en segundos.")
    fetch.add_argument("--count", type=int, default=1000)
    fetch.add_argument("--balance", default="PRACTICE", choices=("PRACTICE", "REAL"))
    fetch.add_argument("--output", required=True)

    backtest = subparsers.add_parser("backtest", help="Ejecuta backtest sobre un CSV.")
    backtest.add_argument("--csv", required=True)
    backtest.add_argument("--model")
    backtest.add_argument("--expiry-candles", type=int, default=1)
    backtest.add_argument("--stake", type=float, default=1.0)
    backtest.add_argument("--payout-rate", type=float, default=0.82)
    backtest.add_argument("--min-model-probability", type=float, default=0.56)
    backtest.add_argument("--signal-lookback", type=int, default=5)

    optimize = subparsers.add_parser("optimize", help="Busca parametros rentables por fuerza bruta simple.")
    optimize.add_argument("--csv", required=True)
    optimize.add_argument("--model")
    optimize.add_argument("--payout-rate", type=float, default=0.82)
    optimize.add_argument("--stake", type=float, default=1.0)
    optimize.add_argument("--min-trades", type=int, default=10)

    train = subparsers.add_parser("train", help="Entrena un modelo simple con historico.")
    train.add_argument("--csv", required=True)
    train.add_argument("--model", required=True)
    train.add_argument("--horizon", type=int, default=1)
    train.add_argument("--epochs", type=int, default=600)
    train.add_argument("--signal-lookback", type=int, default=5)

    live = subparsers.add_parser("live", help="Ejecuta el bot en vivo. Por defecto no envia ordenes.")
    live.add_argument("--asset", required=True)
    live.add_argument("--model")
    live.add_argument("--timeframe", type=int, default=60)
    live.add_argument("--candle-count", type=int, default=300)
    live.add_argument("--expiry-candles", type=int, default=5)
    live.add_argument("--amount", type=float, default=1.0)
    live.add_argument("--balance", default="PRACTICE", choices=("PRACTICE", "REAL"))
    live.add_argument("--execute", action="store_true", help="Envia ordenes reales a IQ Option.")
    live.add_argument("--poll-seconds", type=int, default=10)
    live.add_argument("--max-trades", type=int, default=3)
    live.add_argument("--stop-loss", type=float, default=5.0)
    live.add_argument("--stop-win", type=float, default=5.0)
    live.add_argument("--option-type", default="turbo", choices=("turbo", "binary"))
    live.add_argument("--result-timeout-seconds", type=int, default=180)
    live.add_argument("--signal-lookback", type=int, default=20)
    live.add_argument("--min-model-probability", type=float, default=0.55)

    markets = subparsers.add_parser("markets", help="Lista activos abiertos en IQ Option.")
    markets.add_argument("--balance", default="PRACTICE", choices=("PRACTICE", "REAL"))
    markets.add_argument("--option-type", default="turbo", choices=("turbo", "binary"))

    signals = subparsers.add_parser("signals", help="Envia senales a consola, CSV y Telegram.")
    signals.add_argument("--asset", required=True)
    signals.add_argument("--model")
    signals.add_argument("--timeframe", type=int, default=60)
    signals.add_argument("--confirmation-timeframe", type=int, default=300)
    signals.add_argument("--context-timeframe", type=int, default=900)
    signals.add_argument("--candle-count", type=int, default=300)
    signals.add_argument("--expiry-candles", type=int, default=2)
    signals.add_argument("--balance", default="PRACTICE", choices=("PRACTICE", "REAL"))
    signals.add_argument("--poll-seconds", type=int, default=10)
    signals.add_argument("--max-signals", type=int, default=10)
    signals.add_argument("--output-csv", default="logs/signals.csv")
    signals.add_argument("--telegram", action="store_true")
    signals.add_argument("--signal-lookback", type=int, default=15)
    signals.add_argument("--min-model-probability", type=float, default=0.55)
    signals.add_argument("--min-score", type=int, default=70)

    telegram_test = subparsers.add_parser("telegram-test", help="Envia un mensaje de prueba a Telegram.")
    telegram_test.add_argument("--message", default="Bot de senales conectado correctamente.")

    return parser


def make_config(args: argparse.Namespace) -> StrategyConfig:
    return StrategyConfig(
        signal_lookback=getattr(args, "signal_lookback", 5),
        min_model_probability=getattr(args, "min_model_probability", 0.56),
    )


def command_generate_sample(args: argparse.Namespace) -> None:
    candles = generate_sample_candles(rows=args.rows)
    write_candles_csv(args.output, candles)
    print(f"CSV generado: {args.output} ({len(candles)} velas)")


def command_fetch_iq(args: argparse.Namespace) -> None:
    candles = fetch_iqoption_candles(args.asset, args.timeframe, args.count, args.balance)
    write_candles_csv(args.output, candles)
    print(f"CSV descargado: {args.output} ({len(candles)} velas)")


def command_backtest(args: argparse.Namespace) -> None:
    candles = read_candles_csv(args.csv)
    model = LogisticModel.load(args.model) if args.model else None
    result = run_backtest(
        candles=candles,
        config=make_config(args),
        model=model,
        expiry_candles=args.expiry_candles,
        stake=args.stake,
        payout_rate=args.payout_rate,
    )

    print(f"Velas: {len(candles)}")
    print(f"Operaciones: {len(result.trades)}")
    print(f"Ganadas: {result.wins}")
    print(f"Perdidas: {result.losses}")
    print(f"Win rate: {result.win_rate:.2%}")
    print(f"Win rate equilibrio: {(1 / (1 + args.payout_rate)):.2%}")
    print(f"Profit simulado: {result.profit:.2f}")

    for trade in result.trades[-10:]:
        status = "WIN" if trade.won else "LOSS"
        print(
            f"{status} {trade.side} entry={trade.entry_price:.6f} "
            f"exit={trade.exit_price:.6f} payout={trade.payout:.2f}"
        )


def command_train(args: argparse.Namespace) -> None:
    candles = read_candles_csv(args.csv)
    config = make_config(args)
    samples = build_training_samples(candles, config, horizon=args.horizon)
    model = train_logistic_regression(samples, epochs=args.epochs)
    model.save(args.model)
    print(f"Modelo guardado: {args.model}")
    print(f"Muestras de entrenamiento: {len(samples)}")


def command_optimize(args: argparse.Namespace) -> None:
    candles = read_candles_csv(args.csv)
    model = LogisticModel.load(args.model) if args.model else None
    results = []

    lookbacks = [3, 5, 8, 10, 15, 20]
    expiries = [1, 2, 3, 5]
    probabilities = [0.50, 0.52, 0.54, 0.55, 0.56, 0.58, 0.60] if model else [0.0]

    for lookback in lookbacks:
        for expiry in expiries:
            for probability in probabilities:
                config = StrategyConfig(signal_lookback=lookback, min_model_probability=probability)
                result = run_backtest(
                    candles=candles,
                    config=config,
                    model=model,
                    expiry_candles=expiry,
                    stake=args.stake,
                    payout_rate=args.payout_rate,
                )
                if len(result.trades) < args.min_trades:
                    continue
                results.append((result.profit, result.win_rate, len(result.trades), lookback, expiry, probability))

    results.sort(reverse=True)
    print(f"Velas: {len(candles)}")
    print(f"Win rate equilibrio: {(1 / (1 + args.payout_rate)):.2%}")
    print("Top resultados:")
    for profit, win_rate, trades, lookback, expiry, probability in results[:10]:
        model_filter = f" min_prob={probability:.2f}" if model else ""
        print(
            f"profit={profit:.2f} win_rate={win_rate:.2%} trades={trades} "
            f"lookback={lookback} expiry={expiry}{model_filter}"
        )


def command_live(args: argparse.Namespace) -> None:
    model = LogisticModel.load(args.model) if args.model else None
    live_config = LiveConfig(
        asset=args.asset,
        timeframe=args.timeframe,
        candle_count=args.candle_count,
        expiry_candles=args.expiry_candles,
        amount=args.amount,
        balance=args.balance,
        execute=args.execute,
        poll_seconds=args.poll_seconds,
        max_trades=args.max_trades,
        stop_loss=args.stop_loss,
        stop_win=args.stop_win,
        option_type=args.option_type,
        result_timeout_seconds=args.result_timeout_seconds,
    )
    run_live_trader(live_config, make_config(args), model)


def command_markets(args: argparse.Namespace) -> None:
    api = connect_iqoption(args.balance)
    assets = list_open_assets(api, args.option_type)
    print(f"Activos abiertos ({args.option_type}): {len(assets)}")
    for asset in assets:
        print(asset)


def command_signals(args: argparse.Namespace) -> None:
    model = LogisticModel.load(args.model) if args.model else None
    signal_config = SignalBotConfig(
        asset=args.asset,
        timeframe=args.timeframe,
        confirmation_timeframe=args.confirmation_timeframe,
        context_timeframe=args.context_timeframe,
        candle_count=args.candle_count,
        expiry_candles=args.expiry_candles,
        balance=args.balance,
        poll_seconds=args.poll_seconds,
        max_signals=args.max_signals,
        output_csv=args.output_csv,
        send_telegram=args.telegram,
        min_score=args.min_score,
    )
    run_signal_bot(signal_config, make_config(args), model)


def command_telegram_test(args: argparse.Namespace) -> None:
    telegram = load_telegram_config()
    if telegram is None:
        raise RuntimeError("Configura TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en .env.")
    send_telegram_message(telegram, args.message)
    print("Mensaje de prueba enviado a Telegram.")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "generate-sample":
        command_generate_sample(args)
    elif args.command == "fetch-iq":
        command_fetch_iq(args)
    elif args.command == "backtest":
        command_backtest(args)
    elif args.command == "train":
        command_train(args)
    elif args.command == "optimize":
        command_optimize(args)
    elif args.command == "live":
        command_live(args)
    elif args.command == "markets":
        command_markets(args)
    elif args.command == "signals":
        command_signals(args)
    elif args.command == "telegram-test":
        command_telegram_test(args)
    else:
        parser.error(f"Comando no soportado: {args.command}")
