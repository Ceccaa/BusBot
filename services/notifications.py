"""Formattazione dei messaggi Telegram per BusBot v2.0."""

import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from db import database as db

logger = logging.getLogger(__name__)

MONETAG_WEBAPP_URL = os.getenv("MONETAG_WEBAPP_URL", "")


def get_ad_markup(chat_id: int) -> ReplyKeyboardMarkup | None:
    """Crea il bottone KeyboardButton web_app per Monetag Rewarded Interstitial.

    Apre la pagina GitHub Pages con il Monetag SDK come Telegram Mini App,
    che al completamento invia sendData('ad_reward') per sbloccare gli orari.
    Non mostrato ai supporter permanenti (Stars ≥ 150).
    """
    if not MONETAG_WEBAPP_URL:
        return None

    if db.is_permanent_supporter(chat_id):
        return None

    button = KeyboardButton(
        "📢 Sblocca orari (guarda uno spot)",
        web_app=WebAppInfo(url=MONETAG_WEBAPP_URL),
    )
    return ReplyKeyboardMarkup(
        [[button]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# ── Metodi di utilità ────────────────────────────────────────────────────────

def _obfuscate(time_str: str) -> str:
    """Trasforma un orario HH:MM in HH:XX (es: 13:14 -> 13:XX)."""
    if not isinstance(time_str, str) or len(time_str) < 5:
        return str(time_str)
    return str(time_str)[:3] + "XX"


# ── Bollettino multi-linea (soppressioni periodiche) ─────────────────────────


def format_multiline_bulletin(
    linee_status: dict[str, list[dict]], is_unlocked: bool = True
) -> str:
    """Genera il bollettino soppressioni per più linee.

    Args:
        linee_status: {"8": [...routes], "92": [], "1A": [...]}
        is_unlocked: Se False, nasconde i minuti esatti delle soppressioni.

    Returns:
        Testo HTML Telegram.
    """
    if not linee_status:
        return "⚠️ Nessuna linea configurata. Usa /start."

    lines = ["📊 <b>Situazione Attuale:</b>\n"]
    for linea, routes in sorted(linee_status.items()):
        if routes:
            lines.append(f"🚆 Linea <b>{linea}</b>: ❌ {len(routes)} corsa/e non garantita/e")
            for r in routes:
                dalle = r["dalle"] if is_unlocked else _obfuscate(r["dalle"])
                alle = r["alle"] if is_unlocked else _obfuscate(r["alle"])
                lines.append(
                    f"   • Da: {r['inizio']} → {r['fine']} "
                    f"| {dalle} — {alle}"
                )
        else:
            lines.append(f"🚆 Linea <b>{linea}</b>: ✅ Nessuna corsa soppressa")

    if not is_unlocked:
        lines.append(
            "\n🔒 <b>Orari nascosti.</b>\n"
            "Guarda uno spot veloce dal bottone rosso 👇 per sbloccare l'esattezza del minuto per oggi!"
        )

    return "\n".join(lines)


# ── Bollettino programmato (alarm digest) ────────────────────────────────────


def format_alarm_bulletin(
    orario: str, linee_status: dict[str, list[dict]], is_unlocked: bool = True
) -> str:
    """Genera il bollettino per la sveglia del pendolare.

    Inviato sempre, anche se tutto è regolare.
    """
    lines = [f"⏰ <b>Bollettino delle {orario}</b>\n"]

    for linea, routes in sorted(linee_status.items()):
        if routes:
            lines.append(f"🚆 Linea <b>{linea}</b>: ❌ {len(routes)} corsa/e non garantita/e")
            for r in routes:
                dalle = r["dalle"] if is_unlocked else _obfuscate(r["dalle"])
                alle = r["alle"] if is_unlocked else _obfuscate(r["alle"])
                lines.append(
                    f"   • Da: {r['inizio']} → {r['fine']} "
                    f"| {dalle} — {alle}"
                )
        else:
            lines.append(f"🚆 Linea <b>{linea}</b>: ✅ Tutto regolare")

    if not is_unlocked:
        lines.append(
            "\n🔒 <b>Minuto oscurato.</b>\n"
            "Usa il bottone Ads 👇 per sbloccare gli orari di oggi."
        )

    lines.append("\nBuona fortuna 🍀")
    return "\n".join(lines)


# ── Alert real-time (nuova soppressione) ─────────────────────────────────────


def format_realtime_alert(linea: str, routes: list[dict], is_unlocked: bool = True) -> str:
    """Notifica immediata per nuova soppressione."""
    lines = [
        "⚠️ <b>NUOVA CORSA SOPPRESSA</b>\n",
        f"🚆 Linea <b>{linea}</b>",
    ]

    for r in routes:
        dalle = r["dalle"] if is_unlocked else _obfuscate(r["dalle"])
        alle = r["alle"] if is_unlocked else _obfuscate(r["alle"])
        lines.append(
            f"   {dalle} — {alle} "
            f"| {r['inizio']} → {r['fine']}"
        )

    lines.append("\n🤬 Il bus ti ha mollato a piedi?")
    if not is_unlocked:
        lines.append(
            "\n(PS: Guarda un Ad dal bottone qui sotto per sbloccare l'orario effettivo 👇)"
        )

    return "\n".join(lines)
