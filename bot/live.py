import time
from dataclasses import dataclass
from typing import Optional

from .data import load_env_file
from .model import LogisticModel
from .strategy import StrategyConfig, generate_signals
from .types import Candle


@dataclass(frozen=True)
class LiveConfig:
    asset: str
    timeframe: int
    candle_count: int
    expiry_candles: int
    amount: float
    balance: str
    execute: bool
    poll_seconds: int
    max_trades: int
    stop_loss: float
    stop_win: float
    option_type: str = "turbo"
    result_timeout_seconds: int = 180


def connect_iqoption(balance: str):
    import os

    load_env_file()
    email = os.getenv("IQOPTION_EMAIL")
    password = os.getenv("IQOPTION_PASSWORD")
    if not email or not password:
        raise RuntimeError("Configura IQOPTION_EMAIL y IQOPTION_PASSWORD en .env antes de operar.")

    try:
        from iqoptionapi.stable_api import IQ_Option
    except ImportError as exc:
        raise RuntimeError("Instala iqoptionapi con: pip install -r requirements.txt") from exc

    api = IQ_Option(email, password)
    connected, reason = api.connect()
    if not connected:
        raise RuntimeError(f"No se pudo conectar a IQ Option: {reason}")

    api.change_balance(balance)
    return api


def fetch_recent_candles(api, asset: str, timeframe: int, count: int) -> list[Candle]:
    raw = api.get_candles(asset, timeframe, count, time.time())
    raw = sorted(raw, key=lambda item: item["from"])
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


def is_asset_open(api, asset: str, option_type: str = "turbo") -> bool:
    try:
        return asset in list_open_assets(api, option_type)
    except Exception as exc:
        print(f"No se pudo verificar mercado abierto: {exc}")
        return False


def list_open_assets(api, option_type: str = "turbo") -> list[str]:
    if option_type not in ("turbo", "binary"):
        raise ValueError("option_type debe ser turbo o binary.")

    binary_data = api.get_all_init_v2()
    market = binary_data.get(option_type, {}).get("actives", {})
    assets = []
    for active in market.values():
        name = str(active.get("name", "")).split(".")[-1]
        enabled = bool(active.get("enabled", False))
        suspended = bool(active.get("is_suspended", True))
        if name and enabled and not suspended:
            assets.append(name)
    return sorted(set(assets))


def wait_binary_result(api, order_id: int, timeout_seconds: int, polling_seconds: int = 2) -> Optional[float]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            order = api.get_async_order(order_id)
            closed = order.get("option-closed", {}) if order else {}
            message = closed.get("msg", {}) if closed else {}
            if message:
                return float(message["profit_amount"]) - float(message["amount"])
        except Exception:
            try:
                api.connect()
            except Exception:
                pass
        time.sleep(polling_seconds)
    return None


def confirm_order(api, order_id: int, timeout_seconds: int = 10) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            ok, order = api.get_order(order_id)
            if ok:
                status = order.get("status") or order.get("raw_event", {}).get("status")
                instrument = order.get("instrument_type") or order.get("raw_event", {}).get("instrument_type")
                print(f"Orden confirmada por IQ: id={order_id} status={status} instrument={instrument}")
                return True
        except Exception:
            pass
        time.sleep(1)
    print(f"IQ no confirmo la orden dentro del timeout. id={order_id}")
    return False


def run_live_trader(config: LiveConfig, strategy: StrategyConfig, model: Optional[LogisticModel] = None) -> None:
    api = connect_iqoption(config.balance)
    mode = "EJECUCION REAL" if config.execute else "SIMULACION"
    account_balance = api.get_balance()
    print(
        f"Bot iniciado: {mode} balance={config.balance} amount={account_balance} "
        f"asset={config.asset} option_type={config.option_type}"
    )

    last_signal_timestamp: Optional[str] = None
    trades = 0
    profit = 0.0

    while trades < config.max_trades and profit > -abs(config.stop_loss) and profit < abs(config.stop_win):
        candles = fetch_recent_candles(api, config.asset, config.timeframe, config.candle_count)
        signals = generate_signals(candles, strategy, model)
        latest = signals[-1] if signals else None

        if latest is None or latest.timestamp == last_signal_timestamp:
            time.sleep(config.poll_seconds)
            continue

        if config.execute and not is_asset_open(api, config.asset, config.option_type):
            print(f"Activo cerrado o suspendido: {config.asset} ({config.option_type}). Esperando...")
            time.sleep(config.poll_seconds)
            continue

        last_signal_timestamp = latest.timestamp
        action = "call" if latest.side == "CALL" else "put"
        expiration_minutes = max(1, round((config.expiry_candles * config.timeframe) / 60))
        probability = f" prob={latest.probability:.2%}" if latest.probability is not None else ""
        print(
            f"Senal {latest.side} timestamp={latest.timestamp} price={latest.price:.6f}"
            f" expiry={expiration_minutes}m{probability}"
        )

        if not config.execute:
            trades += 1
            print("DRY RUN: no se envio orden.")
            time.sleep(config.poll_seconds)
            continue

        ok, order_id = api.buy(config.amount, config.asset, action, expiration_minutes)
        if not ok:
            print(f"Orden rechazada: {order_id}")
            time.sleep(config.poll_seconds)
            continue

        trades += 1
        print(f"Orden enviada id={order_id} amount={config.amount:.2f} action={action}")
        confirm_order(api, order_id)
        timeout = max(config.result_timeout_seconds, expiration_minutes * 60 + 60)
        result = wait_binary_result(api, order_id, timeout_seconds=timeout)
        if result is None:
            print(f"No se pudo confirmar resultado antes del timeout. id={order_id}")
            time.sleep(config.poll_seconds)
            continue

        profit += float(result)
        status = "WIN" if result > 0 else "LOSS" if result < 0 else "EQUAL"
        print(f"Resultado {status}: pnl={result:.2f} profit_total={profit:.2f}")

    print(f"Bot detenido. trades={trades} profit_total={profit:.2f}")
