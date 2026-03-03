"""Scheduler: bollettino programmato (alarm digest) — BusBot v2.0.

Gira ogni minuto. Per ogni utente che ha un allarme all'orario corrente
invia sempre un bollettino, anche se non ci sono soppressioni.
Gestisce Telegram Forbidden: deattiva utenti che hanno bloccato il bot.
"""

import logging
from datetime import datetime

import telegram

from db import database as db
from services import scraper
from services.notifications import format_alarm_bulletin, get_adsgram_markup

logger = logging.getLogger(__name__)


async def alarm_digest_job(context) -> None:
    """Job al minuto: invia bollettino agli utenti con allarme adesso."""
    now = datetime.now().strftime("%H:%M")
    users = db.get_users_with_alarm(now)

    if not users:
        return

    logger.info("Alarm digest %s — %d utenti", now, len(users))

    for user in users:
        chat_id = user["chat_id"]
        bacino = user["bacino"]
        linee = user.get("linee", [])

        if not linee:
            continue

        linee_status = {
            linea: scraper.get_cancelled_routes(bacino, linea)
            for linea in linee
        }

        text = format_alarm_bulletin(now, linee_status)
        reply_markup = get_adsgram_markup(chat_id)

        try:
            msg = await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
            db.update_last_message_id(chat_id, msg.message_id)
            logger.info("Alarm digest inviato → chat_id=%s (%s)", chat_id, now)
        except telegram.error.Forbidden:
            logger.warning("Bot bloccato da chat_id=%s — disattivo l'utente.", chat_id)
            db.deactivate_user(chat_id)
        except Exception as exc:
            logger.error("Errore alarm digest → chat_id=%s: %s", chat_id, exc)

