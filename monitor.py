import json
import os
import re
from pathlib import Path
from urllib.parse import urljoin

import requests


GOOGLE_MAPS_URL = "https://maps.app.goo.gl/3HY2zevoNAjenXM87"
STATE_FILE = Path("state.json")

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def get_google_maps_page():
    response = requests.get(
        GOOGLE_MAPS_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0 Safari/537.36"
            )
        },
        timeout=30,
        allow_redirects=True,
    )

    response.raise_for_status()

    return response.url, response.text


def detect_status(html):
    text = re.sub(r"\s+", " ", html.lower())

    permanent_patterns = [
        "permanently closed",
        "permanentlyclose",
        "chiuso definitivamente",
        "chiusa definitivamente",
        "definitivamente chiuso",
        "definitivamente chiusa",
    ]

    temporary_patterns = [
        "temporarily closed",
        "temporarilyclose",
        "chiuso temporaneamente",
        "chiusa temporaneamente",
        "temporaneamente chiuso",
        "temporaneamente chiusa",
    ]

    open_patterns = [
        "open now",
        "open",
        "aperto",
        "aperta",
    ]

    if any(pattern in text for pattern in permanent_patterns):
        return "DEFINITIVAMENTE CHIUSO"

    if any(pattern in text for pattern in temporary_patterns):
        return "TEMPORANEAMENTE CHIUSO"

    if any(pattern in text for pattern in open_patterns):
        return "APERTO/OPERATIVO"

    return "NON DETERMINATO"


def load_previous_status():
    if not STATE_FILE.exists():
        return None

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data.get("status")

    except Exception:
        return None


def save_status(status):
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(
            {"status": status},
            file,
            ensure_ascii=False,
            indent=2,
        )


def send_telegram(message):
    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    response = requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
        },
        timeout=30,
    )

    response.raise_for_status()


def main():
    print("Controllo HOT POT 逍遥烫...")

    final_url, html = get_google_maps_page()

    status = detect_status(html)
    previous_status = load_previous_status()

    print(f"Stato precedente: {previous_status}")
    print(f"Stato attuale: {status}")

    if status == "NON DETERMINATO":
        print("Non è possibile determinare lo stato con sufficiente affidabilità.")
        return

    if previous_status is None:
        message = (
            "🍲 HOT POT 逍遥烫\n\n"
            f"Stato rilevato: {status}\n\n"
            f"Google Maps:\n{GOOGLE_MAPS_URL}"
        )

        send_telegram(message)
        save_status(status)

        print("Primo controllo completato.")
        return

    if status != previous_status:
        message = (
            "🔔 CAMBIAMENTO STATO HOT POT 逍遥烫\n\n"
            f"Prima: {previous_status}\n"
            f"Adesso: {status}\n\n"
            f"Google Maps:\n{GOOGLE_MAPS_URL}"
        )

        send_telegram(message)
        save_status(status)

        print("Cambiamento rilevato e inviato su Telegram.")
        return

    print("Nessun cambiamento. Nessun messaggio inviato.")


if __name__ == "__main__":
    main()
