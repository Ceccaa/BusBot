"""Handler per i comandi semplici — BusBot v2.0."""

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from db import database as db
from services import scraper
from services.notifications import format_multiline_bulletin, get_adsgram_markup

logger = logging.getLogger(__name__)


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Controlla subito le corse soppresse per tutte le linee configurate."""
    chat_id = update.effective_chat.id
    cfg = db.get_user(chat_id)

    if not cfg or not cfg.get("is_active"):
        await update.message.reply_html("⚠️ Non sei configurato. Usa /start.")
        return

    await update.message.reply_text("🔄 Controllo in corso...")

    linee_status = {
        linea: scraper.get_cancelled_routes(cfg["bacino"], linea)
        for linea in cfg["linee"]
    }
    
    reply_markup = get_adsgram_markup(chat_id)
    await update.message.reply_html(
        format_multiline_bulletin(linee_status),
        reply_markup=reply_markup
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra la configurazione corrente."""
    chat_id = update.effective_chat.id
    cfg = db.get_user(chat_id)

    if not cfg:
        await update.message.reply_html("⚠️ Non sei configurato. Usa /start.")
        return

    stato = "🟢 Attivo" if cfg.get("is_active") else "🔴 Disattivato"
    realtime = "🔔 Attivo" if cfg.get("notifiche_realtime") else "🔕 Disattivato"
    linee_str = " · ".join(cfg.get("linee", [])) or "—"
    alarms_str = " · ".join(cfg.get("alarms", [])) or "nessuno"

    reply_markup = get_adsgram_markup(chat_id)
    await update.message.reply_html(
        f"📋 <b>Configurazione:</b>\n\n"
        f"📍 Bacino: <b>{cfg['bacino']}</b>\n"
        f"🚍 Linee: <b>{linee_str}</b>\n"
        f"⏰ Sveglie: <b>{alarms_str}</b>\n"
        f"🔔 Notifiche realtime: {realtime}\n"
        f"📡 Stato: {stato}\n"
        f"📊 Impressioni ads: {cfg.get('ad_impressions', 0)}",
        reply_markup=reply_markup
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disattiva il monitoraggio."""
    chat_id = update.effective_chat.id
    if db.deactivate_user(chat_id):
        await update.message.reply_html(
            "🔴 Monitoraggio <b>disattivato</b>.\nUsa /start per riattivare."
        )
    else:
        await update.message.reply_html("⚠️ Non sei configurato. Usa /start.")


async def realtime_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle per le notifiche real-time."""
    chat_id = update.effective_chat.id
    cfg = db.get_user(chat_id)

    if not cfg or not cfg.get("is_active"):
        await update.message.reply_html("⚠️ Non sei configurato. Usa /start.")
        return

    current = bool(cfg.get("notifiche_realtime"))
    new_state = not current
    db.set_realtime(chat_id, new_state)

    if new_state:
        await update.message.reply_html(
            "🔔 <b>Notifiche real-time attivate!</b>\n"
            "Riceverai un alert immediato appena una corsa viene soppressa."
        )
    else:
        await update.message.reply_html(
            "🔕 <b>Notifiche real-time disattivate.</b>\n"
            "Riceverai solo i bollettini periodici."
        )


def register_command_handlers(app: Application) -> None:
    """Registra i command handler sull'applicazione."""
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("realtime", realtime_toggle))
