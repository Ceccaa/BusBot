"""ConversationHandler per il setup multi-linea e multi-orario — BusBot v2.0."""

import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from db import database as db
from services import scraper
from services.notifications import format_multiline_bulletin, get_adsgram_markup

logger = logging.getLogger(__name__)

# ── Stati ConversationHandler ─────────────────────────────────────────────────

SCEGLI_BACINO, SCEGLI_LINEE = range(2)
INSERISCI_ALARMS = 10

BACINI = {
    "Forli-Cesena": "🟢 Forlì-Cesena",
    "Rimini": "🔵 Rimini",
    "Ravenna": "🟡 Ravenna",
}

_TIME_RE = re.compile(r"^\d{2}:\d{2}$")


# ── /start — Setup iniziale ───────────────────────────────────────────────────


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mostra la scelta del bacino."""
    keyboard = [
        [InlineKeyboardButton(label, callback_data=bacino)]
        for bacino, label in BACINI.items()
    ]
    await update.message.reply_html(
        "👋 <b>Benvenuto su BusBot!</b>\n\n"
        "Monitoro le corse non garantite di Start Romagna "
        "e ti avviso quando il tuo autobus è soppresso.\n\n"
        "📍 <b>Scegli il tuo bacino:</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return SCEGLI_BACINO


async def scegli_bacino(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva il bacino e chiede le linee."""
    query = update.callback_query
    await query.answer()

    bacino = query.data
    if bacino not in BACINI:
        await query.edit_message_text("❌ Bacino non valido. Usa /start per riprovare.")
        return ConversationHandler.END

    context.user_data["bacino"] = bacino
    await query.edit_message_text(
        f"📍 Bacino selezionato: <b>{bacino}</b>\n\n"
        "🔢 Inserisci le <b>linee da monitorare</b>, separate da spazio:\n"
        "<i>Esempio: <code>8 92 1A</code></i>",
        parse_mode="HTML",
    )
    return SCEGLI_LINEE


async def scegli_linee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parsa le linee, salva utente, fa check immediato."""
    raw = update.message.text.strip()
    linee = [t.upper() for t in raw.split() if t.strip()]

    if not linee:
        await update.message.reply_text("❌ Inserisci almeno un numero di linea.")
        return SCEGLI_LINEE

    bacino = context.user_data["bacino"]
    chat_id = update.effective_chat.id
    db.save_user(chat_id, bacino, linee)

    linee_str = " · ".join(linee)
    await update.message.reply_html(
        f"✅ <b>Configurazione completata!</b>\n\n"
        f"📍 Bacino: <b>{bacino}</b>\n"
        f"🚍 Linee: <b>{linee_str}</b>\n\n"
        "Riceverai notifiche automatiche per le corse soppresse.\n\n"
        "📋 <b>Comandi:</b>\n"
        "/check — Controlla subito\n"
        "/alarms — Imposta sveglia pendolare\n"
        "/realtime — Toggle notifiche istantanee\n"
        "/status — Configurazione attuale\n"
        "/donate — ⭐ Supporta BusBot\n"
        "/stop — Disattiva monitoraggio\n"
        "/start — Riconfigura",
    )

    # Check immediato su tutte le linee
    linee_status = {
        linea: await scraper.get_cancelled_routes(bacino, linea) for linea in linee
    }
    
    is_unlocked = db.is_unlocked(chat_id)
    reply_markup = get_adsgram_markup(chat_id)
    await update.message.reply_html(
        format_multiline_bulletin(linee_status, is_unlocked=is_unlocked),
        reply_markup=reply_markup
    )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Configurazione annullata.")
    return ConversationHandler.END


# ── /alarms — Imposta sveglia pendolare ──────────────────────────────────────


async def alarms_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Chiede gli orari da impostare."""
    cfg = db.get_user(update.effective_chat.id)
    if not cfg or not cfg.get("is_active"):
        await update.message.reply_html("⚠️ Non sei configurato. Usa /start.")
        return ConversationHandler.END

    current = cfg.get("alarms", [])
    current_str = " · ".join(current) if current else "nessuno"
    await update.message.reply_html(
        f"⏰ <b>Sveglia del Pendolare</b>\n\n"
        f"Orari attuali: <b>{current_str}</b>\n\n"
        "Inserisci i nuovi orari in formato <code>HH:MM</code>, separati da spazio.\n"
        "<i>Esempio: <code>07:10 13:30 18:45</code></i>\n\n"
        "Invia <code>0</code> per rimuovere tutti gli allarmi.",
    )
    return INSERISCI_ALARMS


async def salva_alarms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Valida e salva gli orari."""
    raw = update.message.text.strip()
    chat_id = update.effective_chat.id

    if raw == "0":
        db.save_alarms(chat_id, [])
        await update.message.reply_text("🔕 Tutti gli allarmi rimossi.")
        return ConversationHandler.END

    tokens = raw.split()
    valid = [t for t in tokens if _TIME_RE.match(t)]
    invalid = [t for t in tokens if not _TIME_RE.match(t)]

    if invalid:
        await update.message.reply_html(
            f"❌ Formato non valido per: <code>{' '.join(invalid)}</code>\n"
            "Usa il formato <code>HH:MM</code>."
        )
        return INSERISCI_ALARMS

    db.save_alarms(chat_id, valid)
    orari_str = " · ".join(valid)
    
    reply_markup = get_adsgram_markup(chat_id)
    await update.message.reply_html(
        f"✅ Allarmi impostati: <b>{orari_str}</b>\n\n"
        "Riceverai un bollettino automatico ad ogni orario impostato.",
        reply_markup=reply_markup
    )
    return ConversationHandler.END


# ── Registrazione ─────────────────────────────────────────────────────────────


def register_conversation_handlers(app: Application) -> None:
    """Registra i ConversationHandler sull'applicazione."""
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SCEGLI_BACINO: [CallbackQueryHandler(scegli_bacino)],
            SCEGLI_LINEE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, scegli_linee)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
        allow_reentry=True,
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("alarms", alarms_start)],
        states={
            INSERISCI_ALARMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, salva_alarms)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
        allow_reentry=True,
    ))
