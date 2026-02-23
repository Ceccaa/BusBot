"""Bot Telegram — handler per comandi e conversazione di setup."""

import logging

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

from config import BACINI, get_user, remove_user, save_user
from scraper import format_routes, get_cancelled_routes

logger = logging.getLogger(__name__)

SCEGLI_BACINO, SCEGLI_LINEA = range(2)


# ── Conversazione di configurazione ─────────────────────────────────────────


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mostra la scelta del bacino."""
    keyboard = [
        [InlineKeyboardButton("🟢 Forlì-Cesena", callback_data="Forli-Cesena")],
        [InlineKeyboardButton("🔵 Rimini",        callback_data="Rimini")],
        [InlineKeyboardButton("🟡 Ravenna",       callback_data="Ravenna")],
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
    """Salva il bacino scelto e chiede la linea."""
    query = update.callback_query
    await query.answer()

    bacino = query.data
    if bacino not in BACINI.values():
        await query.edit_message_text("❌ Bacino non valido. Usa /start per riprovare.")
        return ConversationHandler.END

    context.user_data["bacino"] = bacino
    await query.edit_message_text(
        f"📍 Bacino selezionato: <b>{bacino}</b>\n\n"
        "🔢 Inserisci il <b>numero della linea</b> da monitorare "
        "(es. <code>3</code>, <code>92</code>, <code>1A</code>):",
        parse_mode="HTML",
    )
    return SCEGLI_LINEA


async def scegli_linea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva la linea, conferma e fa un check immediato."""
    linea = update.message.text.strip()
    if not linea:
        await update.message.reply_text("❌ Inserisci un numero di linea valido.")
        return SCEGLI_LINEA

    bacino = context.user_data["bacino"]
    save_user(update.effective_chat.id, bacino, linea)

    await update.message.reply_html(
        f"✅ <b>Configurazione completata!</b>\n\n"
        f"📍 Bacino: <b>{bacino}</b>\n"
        f"🚍 Linea: <b>{linea.upper()}</b>\n\n"
        "Riceverai notifiche automatiche per le corse soppresse.\n\n"
        "📋 <b>Comandi:</b>\n"
        "/check — Controlla subito\n"
        "/status — Configurazione attuale\n"
        "/stop — Disattiva monitoraggio\n"
        "/start — Riconfigura",
    )

    # Check immediato dopo configurazione
    routes = get_cancelled_routes(bacino, linea)
    await update.message.reply_html(format_routes(routes))

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Annulla la configurazione in corso."""
    await update.message.reply_text("❌ Configurazione annullata.")
    return ConversationHandler.END


# ── Comandi ──────────────────────────────────────────────────────────────────


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Controlla subito le corse soppresse."""
    cfg = get_user(update.effective_chat.id)
    if not cfg or not cfg.get("active"):
        await update.message.reply_html("⚠️ Non sei configurato. Usa /start.")
        return

    await update.message.reply_text("🔄 Controllo in corso...")
    routes = get_cancelled_routes(cfg["bacino"], cfg["linea"])
    await update.message.reply_html(format_routes(routes))


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra la configurazione corrente."""
    cfg = get_user(update.effective_chat.id)
    if not cfg:
        await update.message.reply_html("⚠️ Non sei configurato. Usa /start.")
        return

    stato = "🟢 Attivo" if cfg.get("active") else "🔴 Disattivato"
    await update.message.reply_html(
        f"📋 <b>Configurazione:</b>\n\n"
        f"📍 Bacino: <b>{cfg['bacino']}</b>\n"
        f"🚍 Linea: <b>{cfg['linea']}</b>\n"
        f"📡 Stato: {stato}",
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disattiva il monitoraggio."""
    if remove_user(update.effective_chat.id):
        await update.message.reply_html(
            "🔴 Monitoraggio <b>disattivato</b>.\nUsa /start per riattivare."
        )
    else:
        await update.message.reply_html("⚠️ Non sei configurato. Usa /start.")


# ── Registrazione ────────────────────────────────────────────────────────────


def register_handlers(app: Application) -> None:
    """Registra tutti gli handler sull'applicazione."""
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SCEGLI_BACINO: [CallbackQueryHandler(scegli_bacino)],
            SCEGLI_LINEA:  [MessageHandler(filters.TEXT & ~filters.COMMAND, scegli_linea)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    ))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("stop", stop))
