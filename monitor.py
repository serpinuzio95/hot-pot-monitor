import html
import json
import os
import re
from pathlib import Path

import requests


# ============================================================
# CONFIGURAZIONE
# ============================================================

GOOGLE_MAPS_URL = "https://maps.app.goo.gl/3HY2zevoNAjenXM87"

STATE_FILE = Path("state.json")

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


# ============================================================
# GOOGLE MAPS
# ============================================================

def get_google_maps_page():
    print("Apro il link Google Maps...")

    response = requests.get(
        GOOGLE_MAPS_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0 Safari/537.36"
            ),
            "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        },
        timeout=30,
        allow_redirects=True,
    )

    response.raise_for_status()

    print(f"URL finale: {response.url}")
    print(f"Dimensione pagina: {len(response.text)} caratteri")

    return response.url, response.text


# ============================================================
# RICONOSCIMENTO STATO
# ============================================================

def normalize_text(text):
    """
    Normalizza il testo della pagina per facilitare la ricerca
    delle frasi di stato.
    """

    text = html.unescape(text)

    # Elimina tag HTML
    text = re.sub(r"<[^>]+>", " ", text)

    # Normalizza spazi
    text = re.sub(r"\s+", " ", text)

    return text.lower()


def detect_status(html_content):
    """
    Cerca prima gli stati di chiusura.
    Solo successivamente cerca segnali molto specifici di apertura.

    IMPORTANTE:
    NON consideriamo più la semplice parola 'open' o 'aperto'
    come prova di apertura.
    """

    text = normalize_text(html_content)

    # --------------------------------------------------------
    # 1. TEMPORANEAMENTE CHIUSO
    # --------------------------------------------------------

    temporary_patterns = [
        r"temporarily\s+closed",
        r"temporarilyclosed",
        r"temporarily[_-]closed",

        r"temporaneamente\s+chius[oa]",
        r"temporaneamentechius[oa]",
        r"temporaneamente[_-]chius[oa]",

        r"chius[oa]\s+temporaneamente",
    ]

    for pattern in temporary_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            print(f"Rilevato stato TEMPORANEAMENTE CHIUSO con: {pattern}")
            return "TEMPORANEAMENTE CHIUSO"

    # --------------------------------------------------------
    # 2. DEFINITIVAMENTE CHIUSO
    # --------------------------------------------------------

    permanent_patterns = [
        r"permanently\s+closed",
        r"permanentlyclosed",
        r"permanently[_-]closed",

        r"chius[oa]\s+definitivamente",
        r"definitivamente\s+chius[oa]",
        r"definitivamentechius[oa]",
    ]

    for pattern in permanent_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            print(f"Rilevato stato DEFINITIVAMENTE CHIUSO con: {pattern}")
            return "DEFINITIVAMENTE CHIUSO"

    # --------------------------------------------------------
    # 3. APERTO
    # --------------------------------------------------------
    #
    # ATTENZIONE:
    # NON cerchiamo semplicemente "open" o "aperto".
    #
    # Cerchiamo frasi che Google Maps usa normalmente per
    # indicare che il locale è aperto ADESSO.
    # --------------------------------------------------------

    open_patterns = [
        # Inglese
        r"\bopen\s+now\b",
        r"\bopen\s*[·•]\s*closes\b",
        r"\bopen\s*[·•]\s*closing\b",

        # Italiano
        r"\baperto\s+ora\b",
        r"\baperta\s+ora\b",
        r"\baperto\s*[·•]\s*chiude\b",
        r"\baperta\s*[·•]\s*chiude\b",
    ]

    for pattern in open_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            print(f"Rilevato stato APERTO con: {pattern}")
            return "APERTO/OPERATIVO"

    # --------------------------------------------------------
    # 4. NON DETERMINATO
    # --------------------------------------------------------

    print("Nessuno stato sufficientemente affidabile trovato.")
    return "NON DETERMINATO"


# ============================================================
# STATO PRECEDENTE
# ============================================================

def load_previous_status():
    if not STATE_FILE.exists():
        print("Nessun stato precedente trovato.")
        return None

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        status = data.get("status")

        print(f"Stato salvato precedentemente: {status}")

        return status

    except Exception as error:
        print(f"Errore leggendo state.json: {error}")
        return None


def save_status(status):
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(
            {
                "status": status
            },
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"Nuovo stato salvato: {status}")


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):
    print("Invio messaggio Telegram...")

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

    print("Messaggio Telegram inviato correttamente.")


# ============================================================
# PROGRAMMA PRINCIPALE
# ============================================================

def main():

    print("=" * 60)
    print("CONTROLLO HOT POT 逍遥烫")
    print("=" * 60)

    # --------------------------------------------------------
    # Scarica pagina Google Maps
    # --------------------------------------------------------

    try:
        final_url, page_html = get_google_maps_page()

    except Exception as error:
        print(f"ERRORE Google Maps: {error}")

        # Non mandiamo notifiche se Google Maps non risponde.
        return

    # --------------------------------------------------------
    # Determina stato
    # --------------------------------------------------------

    current_status = detect_status(page_html)

    previous_status = load_previous_status()

    print()
    print(f"Stato precedente: {previous_status}")
    print(f"Stato attuale:    {current_status}")
    print()

    # --------------------------------------------------------
    # Se non siamo sicuri, NON mandiamo notifiche
    # --------------------------------------------------------

    if current_status == "NON DETERMINATO":

        print(
            "⚠️ Stato non determinato con sufficiente affidabilità."
        )

        print(
            "Nessun messaggio Telegram inviato."
        )

        return

    # --------------------------------------------------------
    # PRIMO CONTROLLO
    # --------------------------------------------------------

    if previous_status is None:

        message = (
            "🍲 HOT POT 逍遥烫\n\n"
            f"Stato rilevato: {current_status}\n\n"
            "Controllo automatico Google Maps.\n\n"
            f"{GOOGLE_MAPS_URL}"
        )

        send_telegram(message)

        save_status(current_status)

        print("Primo controllo completato.")
        return

    # --------------------------------------------------------
    # STATO CAMBIATO
    # --------------------------------------------------------

    if current_status != previous_status:

        message = (
            "🔔 CAMBIAMENTO STATO HOT POT 逍遥烫\n\n"
            f"Prima:  {previous_status}\n"
            f"Adesso: {current_status}\n\n"
            "Controllo automatico Google Maps.\n\n"
            f"{GOOGLE_MAPS_URL}"
        )

        send_telegram(message)

        save_status(current_status)

        print("⚠️ CAMBIAMENTO RILEVATO!")
        return

    # --------------------------------------------------------
    # STATO INVARIATO
    # --------------------------------------------------------

    print("Stato invariato.")
    print("Nessun messaggio Telegram necessario.")


# ============================================================
# AVVIO
# ============================================================

if __name__ == "__main__":
    main()
