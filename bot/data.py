import csv
import math
import os
import random
import time
from pathlib import Path
from typing import Iterable, List

from .types import Candle


REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close")


def load_env_file(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def read_candles_csv(path: str) -> List[Candle]:
    with open(path, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            raise ValueError("El CSV no tiene encabezados.")

        missing = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
        if missing:
            raise ValueError(f"Faltan columnas requeridas: {', '.join(missing)}")

        candles: List[Candle] = []
        for row in reader:
            candles.append(
                Candle(
                    timestamp=str(row["timestamp"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume") or 0.0),
                )
            )
    return candles


def write_candles_csv(path: str, candles: Iterable[Candle]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=("timestamp", "open", "high", "low", "close", "volume"))
        writer.writeheader()
        for candle in candles:
            writer.writerow(
                {
                    "timestamp": candle.timestamp,
                    "open": f"{candle.open:.6f}",
                    "high": f"{candle.high:.6f}",
                    "low": f"{candle.low:.6f}",
                    "close": f"{candle.close:.6f}",
                    "volume": f"{candle.volume:.2f}",
                }
            )


def generate_sample_candles(rows: int = 600, seed: int = 7) -> List[Candle]:
    random.seed(seed)
    candles: List[Candle] = []
    price = 1.1000
    start = int(time.time()) - rows * 60

    for index in range(rows):
        trend = math.sin(index / 70.0) * 0.00012
        noise = random.gauss(0, 0.00035)
        open_price = price
        close_price = max(0.0001, open_price + trend + noise)
        spread = abs(random.gauss(0.00025, 0.00009))
        high = max(open_price, close_price) + spread
        low = min(open_price, close_price) - spread
        volume = random.randint(100, 1000)
        candles.append(
            Candle(
                timestamp=str(start + index * 60),
                open=open_price,
                high=high,
                low=low,
                close=close_price,
                volume=float(volume),
            )
        )
        price = close_price

    return candles


def fetch_iqoption_candles(asset: str, timeframe: int, count: int, balance: str = "PRACTICE") -> List[Candle]:
    load_env_file()
    email = os.getenv("IQOPTION_EMAIL")
    password = os.getenv("IQOPTION_PASSWORD")
    if not email or not password:
        raise RuntimeError("Configura IQOPTION_EMAIL y IQOPTION_PASSWORD antes de descargar datos.")

    try:
        from iqoptionapi.stable_api import IQ_Option
    except ImportError as exc:
        raise RuntimeError("Instala iqoptionapi con: pip install -r requirements.txt") from exc

    api = IQ_Option(email, password)
    connected, reason = api.connect()
    if not connected:
        raise RuntimeError(f"No se pudo conectar a IQ Option: {reason}")

    api.change_balance(balance)
    raw = []
    end_time = time.time()
    remaining = count
    batch_size = 1000

    while remaining > 0:
        batch_count = min(batch_size, remaining)
        batch = api.get_candles(asset, timeframe, batch_count, end_time)
        if not batch:
            break

        raw.extend(batch)
        oldest_timestamp = min(item["from"] for item in batch)
        end_time = oldest_timestamp - 1
        remaining -= len(batch)

        if len(batch) < batch_count:
            break

        time.sleep(0.2)

    deduplicated = {item["from"]: item for item in raw}
    raw = sorted(deduplicated.values(), key=lambda item: item["from"])

    return [
        Candle(
            timestamp=str(item["from"]),
            open=float(item["open"]),
            high=float(item["max"]),
            low=float(item["min"]),
            close=float(item["close"]),
            volume=float(item.get("volume") or 0.0),
        )
        for item in raw
    ]
