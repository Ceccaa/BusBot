"""Reward logic per gli annunci pubblicitari — BusBot v2.0.

Gestisce lo sblocco degli orari dopo che l'utente ha visualizzato
un annuncio Monetag (Rewarded Interstitial) tramite Telegram Mini App.

Il reward arriva via Telegram.WebApp.sendData('ad_reward') dalla pagina
GitHub Pages, senza necessità di alcun server HTTPS esposto.
"""

import logging

from telegram import Bot
from telegram.error import TelegramError

from db import database as db
from services.scraper import get_cancelled_routes
from services.notifications import format_multiline_bulletin

logger = logging.getLogger(__name__)


async def unlock_message_for_user(bot: Bot, chat_id: int) -> None:
    """Rigenera il bollettino in chiaro e aggiorna l'ultimo messaggio nel DB."""
    user = db.get_user(chat_id)
    if not user:
        return

    last_msg_id = user.get("last_message_id")
    if not last_msg_id:
        return

    linee = user.get("linee", [])
    if not linee:
        return

    linee_status = {
        linea: await get_cancelled_routes(user["bacino"], linea)
        for linea in linee
    }
    testo = format_multiline_bulletin(linee_status, is_unlocked=True)

    try:
        await bot.edit_message_text(
            text=testo,
            chat_id=chat_id,
            message_id=last_msg_id,
            parse_mode="HTML",
            reply_markup=None,  # Rimuove il bottone Ads
        )
        logger.info("Messaggio %s sbloccato per chat_id=%s", last_msg_id, chat_id)
    except TelegramError as e:
        logger.warning(
            "Impossibile sbloccare il messaggio %s per chat_id=%s: %s",
            last_msg_id, chat_id, e,
        )
