import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional

from .data import load_env_file


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    chat_id: str


def load_telegram_config() -> Optional[TelegramConfig]:
    load_env_file()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return None
    return TelegramConfig(bot_token=bot_token, chat_id=chat_id)


def send_telegram_message(config: TelegramConfig, text: str) -> None:
    url = f"https://api.telegram.org/bot{config.bot_token}/sendMessage"
    payload = urllib.parse.urlencode(
        {
            "chat_id": config.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method="POST")
    with urllib.request.urlopen(request, timeout=15) as response:
        body = response.read().decode("utf-8")
        data = json.loads(body)
        if not data.get("ok"):
            raise RuntimeError(f"Telegram rechazo el mensaje: {body}")
