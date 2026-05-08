import csv
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from .live import connect_iqoption, fetch_recent_candles
from .model import LogisticModel
from .multitimeframe import analyze_timeframe, score_signal, timeframe_label
from .strategy import StrategyConfig, generate_signals
from .telegram import TelegramConfig, load_telegram_config, send_telegram_message


@dataclass(frozen=True)
class SignalBotConfig:
    asset: str
    timeframe: int
    confirmation_timeframe: int
    context_timeframe: int
    candle_count: int
    expiry_candles: int
    balance: str
    poll_seconds: int
    max_signals: int
    output_csv: str
    send_telegram: bool
    min_score: int


def signal_strength(probability: Optional[float]) -> str:
    if probability is None:
        return "SIN MODELO"
    if probability >= 0.62:
        return "FUERTE"
    if probability >= 0.55:
        return "MODERADA"
    return "DEBIL"


def display_strength(probability: Optional[float], score: Optional[int], strength: Optional[str]) -> str:
    if strength:
        return strength
    return signal_strength(probability)


def format_signal_time(timestamp: str, timeframe: int) -> tuple[str, str]:
    timezone = ZoneInfo("America/Bogota")
    try:
        candle_open = datetime.fromtimestamp(float(timestamp), timezone)
        entry_time = datetime.fromtimestamp(float(timestamp) + timeframe, timezone)
        return candle_open.strftime("%Y-%m-%d %H:%M:%S"), entry_time.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return timestamp, "proxima vela"


def format_signal_message(
    asset: str,
    side: str,
    price: float,
    signal_timestamp: str,
    expiry_candles: int,
    timeframe: int,
    probability: Optional[float],
    score: Optional[int],
    strength: Optional[str],
    context: Optional[str],
    reason: str,
) -> str:
    expiration_minutes = max(1, round((expiry_candles * timeframe) / 60))
    probability_text = f"{probability:.2%}" if probability is not None else "N/A"
    strength_text = display_strength(probability, score, strength)
    score_text = f"{score}/100" if score is not None else "N/A"
    candle_time, entry_time = format_signal_time(signal_timestamp, timeframe)
    direction = "COMPRA / CALL" if side == "CALL" else "VENTA / PUT"
    direction_icon = "🟢" if side == "CALL" else "🔴"
    strength_icon = "🔥" if strength_text == "FUERTE" else "⚡" if strength_text == "MODERADA" else "⚠️"
    context_text = context or "Sin contexto multi temporalidad"
    return (
        "📊 <b>SENAL IQ OPTION</b>\n\n"
        f"💱 Activo: <b>{asset}</b>\n"
        f"{direction_icon} Direccion: <b>{direction}</b>\n"
        f"{strength_icon} Fuerza: <b>{strength_text}</b>\n"
        f"🧠 Score MTF: <b>{score_text}</b>\n"
        f"🎯 Probabilidad: <b>{probability_text}</b>\n\n"
        f"⏰ Entrada sugerida: <b>{entry_time}</b>\n"
        f"🕯️ Vela analizada: <code>{candle_time}</code>\n"
        f"💵 Precio referencia: <code>{price:.6f}</code>\n"
        f"⌛ Expiracion: <b>{expiration_minutes} min</b>\n\n"
        f"🧭 Contexto: {context_text}\n"
        f"✅ Confirmacion: {reason}"
    )


def append_signal_csv(path: str, row: dict[str, str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    exists = output.exists()
    with output.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=(
                "timestamp",
                "asset",
                "side",
                "price",
                "probability",
                "score",
                "strength",
                "expiry_candles",
                "timeframe",
                "context",
                "reason",
                "manual_result",
            ),
        )
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def run_signal_bot(config: SignalBotConfig, strategy: StrategyConfig, model: Optional[LogisticModel] = None) -> None:
    api = connect_iqoption(config.balance)
    telegram: Optional[TelegramConfig] = load_telegram_config() if config.send_telegram else None
    if config.send_telegram and telegram is None:
        raise RuntimeError("Configura TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en .env para enviar senales.")

    print(
        f"Bot de senales iniciado: asset={config.asset} balance={config.balance} "
        f"tf={timeframe_label(config.timeframe)} confirmacion={timeframe_label(config.confirmation_timeframe)} "
        f"contexto={timeframe_label(config.context_timeframe)} min_score={config.min_score}"
    )
    last_signal_timestamp: Optional[str] = None
    sent = 0

    while sent < config.max_signals:
        candles = fetch_recent_candles(api, config.asset, config.timeframe, config.candle_count)
        signals = generate_signals(candles, strategy, model)
        latest_raw = signals[-1] if signals else None

        if latest_raw is None or latest_raw.timestamp == last_signal_timestamp:
            time.sleep(config.poll_seconds)
            continue

        confirmation_candles = fetch_recent_candles(api, config.asset, config.confirmation_timeframe, config.candle_count)
        context_candles = fetch_recent_candles(api, config.asset, config.context_timeframe, config.candle_count)
        context_5m = analyze_timeframe(confirmation_candles, strategy, timeframe_label(config.confirmation_timeframe))
        context_15m = analyze_timeframe(context_candles, strategy, timeframe_label(config.context_timeframe))
        latest = score_signal(latest_raw, context_5m, context_15m)

        if latest.score is not None and latest.score < config.min_score:
            last_signal_timestamp = latest.timestamp
            print(f"Senal descartada por score bajo: {latest.score}/100 {latest.side} {latest.context}")
            time.sleep(config.poll_seconds)
            continue

        last_signal_timestamp = latest.timestamp
        sent += 1
        message = format_signal_message(
            asset=config.asset,
            side=latest.side,
            price=latest.price,
            signal_timestamp=latest.timestamp,
            expiry_candles=config.expiry_candles,
            timeframe=config.timeframe,
            probability=latest.probability,
            score=latest.score,
            strength=latest.strength,
            context=latest.context,
            reason=latest.reason,
        )
        probability = "" if latest.probability is None else f"{latest.probability:.6f}"
        append_signal_csv(
            config.output_csv,
            {
                "timestamp": latest.timestamp,
                "asset": config.asset,
                "side": latest.side,
                "price": f"{latest.price:.6f}",
                "probability": probability,
                "score": "" if latest.score is None else str(latest.score),
                "strength": latest.strength or "",
                "expiry_candles": str(config.expiry_candles),
                "timeframe": str(config.timeframe),
                "context": latest.context or "",
                "reason": latest.reason,
                "manual_result": "",
            },
        )

        print(message.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", ""))
        if telegram is not None:
            send_telegram_message(telegram, message)
            print("Senal enviada a Telegram.")

        time.sleep(config.poll_seconds)

    print(f"Bot de senales detenido. senales={sent}")
