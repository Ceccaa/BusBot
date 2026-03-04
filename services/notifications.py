"""Formattazione dei messaggi Telegram per BusBot v2.0."""

import logging
import os

from telegram import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from db import database as db

logger = logging.getLogger(__name__)

ADSTERRA_WEBAPP_URL = os.getenv("ADSTERRA_WEBAPP_URL", "")


def get_ad_markup(chat_id: int) -> ReplyKeyboardMarkup | None:
    """Crea il bottone KeyboardButton web_app per lo spot pubblicitario.

    Mostrato solo se:
    - ADSTERRA_WEBAPP_URL è configurato
    - L'utente non è già sbloccato oggi
    - L'utente non è un supporter permanente
    """
    if not ADSTERRA_WEBAPP_URL:
        return None

    if db.is_permanent_supporter(chat_id):
        return None

    if db.is_unlocked(chat_id):
        return None  # già sbloccato oggi — niente bottone

    button = KeyboardButton(
        "📢 Sblocca orari (guarda uno spot)",
        web_app=WebAppInfo(url=ADSTERRA_WEBAPP_URL),
    )
    return ReplyKeyboardMarkup(
        [[button]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# ── Bollettino multi-linea (soppressioni periodiche) ─────────────────────────


def format_multiline_bulletin(
    linee_status: dict[str, list[dict]], is_unlocked: bool = False
) -> str:
    """Genera il bollettino soppressioni per più linee.

    Args:
        linee_status: {"8": [...routes], "92": [], "1A": [...]}
        is_unlocked: Se False (default), mostra messaggio generico FOMO.

    Returns:
        Testo HTML Telegram.
    """
    if not linee_status:
        return "⚠️ Nessuna linea configurata. Usa /start."

    if not is_unlocked:
        linee_str = " · ".join(sorted(linee_status.keys()))
        return (
            "🟠 <b>Potrebbero esserci variazioni</b>\n"
            f"sulle tue linee: <b>{linee_str}</b>\n\n"
            "Sblocca il bollettino guardando\n"
            "un breve spot dal bottone 👇\n\n"
            "<i>Oppure usa /donate per sbloccarli per sempre!</i>"
        )

    lines = ["📊 <b>Situazione Attuale:</b>\n"]
    for linea, routes in sorted(linee_status.items()):
        if routes:
            lines.append(f"🚆 Linea <b>{linea}</b>: ❌ {len(routes)} corsa/e non garantita/e")
            for r in routes:
                lines.append(
                    f"   • {r['inizio']} → {r['fine']} "
                    f"| {r['dalle']} — {r['alle']}"
                )
        else:
            lines.append(f"🚆 Linea <b>{linea}</b>: ✅ Tutto regolare")

    return "\n".join(lines)


# ── Bollettino programmato (alarm digest) ────────────────────────────────────


def format_alarm_bulletin(
    orario: str, linee_status: dict[str, list[dict]], is_unlocked: bool = False
) -> str:
    """Genera il bollettino per la sveglia del pendolare."""
    if not is_unlocked:
        linee_str = " · ".join(sorted(linee_status.keys()))
        return (
            f"⏰ <b>Sveglia delle {orario}</b>\n\n"
            "🟠 <b>Potrebbero esserci variazioni</b>\n"
            f"sulle tue linee: <b>{linee_str}</b>\n\n"
            "Sblocca il bollettino guardando\n"
            "un breve spot dal bottone 👇\n\n"
            "Buona fortuna 🍀"
        )

    lines = [f"⏰ <b>Bollettino delle {orario}</b>\n"]
    for linea, routes in sorted(linee_status.items()):
        if routes:
            lines.append(f"🚆 Linea <b>{linea}</b>: ❌ {len(routes)} corsa/e non garantita/e")
            for r in routes:
                lines.append(
                    f"   • {r['inizio']} → {r['fine']} "
                    f"| {r['dalle']} — {r['alle']}"
                )
        else:
            lines.append(f"🚆 Linea <b>{linea}</b>: ✅ Tutto regolare")

    lines.append("\nBuona fortuna 🍀")
    return "\n".join(lines)


