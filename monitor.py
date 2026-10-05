import json
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests


GOOGLE_MAPS_URL = "https://maps.app.goo.gl/3HY2zevoNAjenXM87"
RESTAURANT_NAME = "HOT POT 逍遥烫"
STATE_FILE = Path("state.json")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def get_google_maps_page():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/140.0 Safari/537.36"
        ),
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    response = requests.get(
        GOOGLE_MAPS_URL,
        headers=headers,
        timeout=30,
        allow_redirects=True,
    )
    response.raise_for_status()

    return response.text, response.url


def detect_status(html):
    text = re.sub(r"\s+", " ", html).lower()

    permanent_patterns = [
        "permanently closed",
        "chiuso definitivamente",
        "chiusa definitivamente",
        "chiuso per sempre",
        "chiusa per sempre",
    ]

    if any(pattern in text for pattern in permanent_patterns):
        return "PERMANENTLY_CLOSED"

    temporary_patterns = [
        "temporarily closed",
        "temporarily unavailable",
        "chiuso temporaneamente",
        "chiusa temporaneamente",
    ]

    if any(pattern in text for pattern in temporary_patterns):
        return "TEMPORARILY_CLOSED"

    open_patterns = [
        '"open"',
        "open now",
        "aperto ora",
        "aperta ora",
        "aperto",
        "aperta",
    ]

    if any(pattern in text for pattern in open_patterns):
        return "OPEN"

    return "UNKNOWN"


def status_text(status):
    return {
        "OPEN": "🟢 OPERATIVO / APERTO",
        "TEMPORARILY_CLOSED": "🟠 CHIUSO TEMPORANEAMENTE",
        "PERMANENTLY_CLOSED": "🔴 CHIUSO DEFINITIVAMENTE",
        "UNKNOWN": "⚪ STATO NON DETERMINABILE",
    }.get(status, "⚪ STATO NON DETERMINABILE")


def load_previous_status():
    if not STATE_FILE.exists():
        return None

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data.get("status")
    except Exception:
        return None


def save_status(status):
    data = {
        "status": status,
        "checked_at": datetime.now(
            ZoneInfo("Europe/Rome")
        ).isoformat(),
    }

    STATE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("Manca TELEGRAM_BOT_TOKEN.")

    if not TELEGRAM_CHAT_ID:
        raise RuntimeError("Manca TELEGRAM_CHAT_ID.")

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    response = requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
        },
        timeout=30,
    )
    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result}")


def main():
    print("====================================")
    print("HOT POT 逍遥烫 - controllo")
    print("====================================")

    previous_status = load_previous_status()
    print("Stato precedente:", previous_status)

    html, final_url = get_google_maps_page()

    print("URL finale Google Maps:")
    print(final_url)

    current_status = detect_status(html)
    print("Stato attuale:", current_status)

    if current_status == "UNKNOWN":
        print("ATTENZIONE: stato non riconosciuto.")
        print("Nessun messaggio Telegram inviato.")
        return

    if previous_status is None:
        save_status(current_status)

        now = datetime.now(ZoneInfo("Europe/Rome"))
        message = (
            f"📍 {RESTAURANT_NAME}\n\n"
            f"Stato rilevato:\n"
            f"{status_text(current_status)}\n\n"
            f"Controllo iniziale effettuato il "
            f"{now.strftime('%d/%m/%Y alle %H:%M')}."
        )

        send_telegram(message)

        print("Prima esecuzione: stato salvato.")
        print("Notifica Telegram inviata.")
        return

    if current_status == previous_status:
        print("Nessun cambiamento.")
        return

    save_status(current_status)

    now = datetime.now(ZoneInfo("Europe/Rome"))
    message = (
        f"🔔 CAMBIAMENTO STATO\n\n"
        f"📍 {RESTAURANT_NAME}\n\n"
        f"Prima:\n"
        f"{status_text(previous_status)}\n\n"
        f"Ora:\n"
        f"{status_text(current_status)}\n\n"
        f"Controllato il {now.strftime('%d/%m/%Y alle %H:%M')}\n\n"
        f"🗺️ Google Maps:\n"
        f"{GOOGLE_MAPS_URL}"
    )

    send_telegram(message)

    print("CAMBIAMENTO RILEVATO!")
    print("Notifica Telegram inviata.")


if __name__ == "__main__":
    main()
