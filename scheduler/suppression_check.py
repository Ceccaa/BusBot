"""Scheduler: controllo soppressioni ogni 30 minuti — BusBot v2.0.

- Supporto multi-linea per utente
- Deduplicazione per (chat_id, linea, hash_corse)
- Gestione Telegram Forbidden: deattiva utenti che hanno bloccato il bot
"""

import logging
import os
from datetime import datetime, time as dt_time

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from db import database as db
from services import scraper
from services.notifications import format_multiline_bulletin

logger = logging.getLogger(__name__)

ACTIVE_START = dt_time(5, 30)
ACTIVE_END = dt_time(22, 0)
ADSGRAM_BLOCK_ID = os.getenv("ADSGRAM_BLOCK_ID", "")
ADSGRAM_BOT_URL = os.getenv("ADSGRAM_BOT_URL", "")


async def suppression_check_job(context) -> None:
    """Job periodico: controlla soppressioni per tutti gli utenti attivi."""
    now = datetime.now().time()
    if not (ACTIVE_START <= now <= ACTIVE_END):
        return

    users = db.get_all_active_users()
    if not users:
        return

    logger.info("Controllo soppressioni — %d utenti attivi", len(users))

    notified: dict = context.bot_data.setdefault("notified", {})

    # Raggruppa per bacino → 1 richiesta HTTP per bacino
    by_bacino: dict[str, list[dict]] = {}
    for user in users:
        by_bacino.setdefault(user["bacino"], []).append(user)

    for bacino, user_list in by_bacino.items():
        all_routes = scraper.get_cancelled_routes(bacino)

        for user in user_list:
            chat_id = user["chat_id"]
            linee = user.get("linee", [])

            if not linee:
                continue

            linee_status: dict[str, list[dict]] = {}
            has_any_change = False

            for linea in linee:
                routes = [r for r in all_routes if scraper.linea_matches(r["linea"], linea)]
                key = f"{chat_id}:{linea}:{_hash(routes)}"

                if key not in notified:
                    has_any_change = True
                    notified[key] = True

                linee_status[linea] = routes

            # Notifica solo se c'è qualcosa di nuovo E ci sono soppressioni
            any_suppressed = any(routes for routes in linee_status.values())
            if not has_any_change or not any_suppressed:
                continue

            await _send_bulletin(context.bot, chat_id, linee_status, linee)


async def _send_bulletin(bot, chat_id: int, linee_status: dict, linee: list[str]) -> None:
    """Invia il bollettino soppressioni, gestendo Forbidden (bot bloccato)."""
    try:
        reply_markup = _build_adsgram_markup(chat_id)
        await bot.send_message(
            chat_id=chat_id,
            text=format_multiline_bulletin(linee_status),
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
        logger.info("Notifica → chat_id=%s (linee: %s)", chat_id, ", ".join(linee))
    except telegram.error.Forbidden:
        logger.warning("Bot bloccato da chat_id=%s — disattivo l'utente.", chat_id)
        db.deactivate_user(chat_id)
    except Exception as exc:
        logger.error("Errore notifica → chat_id=%s: %s", chat_id, exc)


def _build_adsgram_markup(chat_id: int) -> InlineKeyboardMarkup | None:
    """Crea inline keyboard con banner Adsgram se configurato properly."""
    if not ADSGRAM_BLOCK_ID or not ADSGRAM_BOT_URL:
        return None

    # Esempio URL: https://t.me/CesenaBusBot/ads?startapp=bot-24237_123456
    url = f"{ADSGRAM_BOT_URL}?startapp={ADSGRAM_BLOCK_ID}_{chat_id}"
    button = InlineKeyboardButton("📢 Supporta BusBot (Ads)", url=url)
    return InlineKeyboardMarkup([[button]])


def _hash(routes: list[dict]) -> str:
    """Hash deterministico di un set di corse per deduplicazione."""
    return "|".join(sorted(f"{r['linea']}-{r['dalle']}" for r in routes))
