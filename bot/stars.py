"""Handler Telegram Stars — donazioni/supporto — BusBot v2.0.

Flusso:
  1. Utente invia /donate
  2. Bot risponde con invoice Stars
  3. Utente conferma il pagamento in Telegram
  4. Telegram invia PreCheckoutQuery → bot risponde ok entro 10s
  5. Telegram conferma il pagamento → SuccessfulPayment
  6. Bot registra l'impressione nel DB e ringrazia l'utente
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from db import database as db

logger = logging.getLogger(__name__)

# Opzioni di donazione (in Stars). 1 Star ≈ 0,013 $ (prezzo indicativo Telegram).
DONATION_OPTIONS = [
    (50,  "☕ Caffè — 50 ⭐"),
    (150, "🍕 Pizza — 150 ⭐"),
    (500, "🚌 Abbonamento — 500 ⭐"),
]


async def donate_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra le opzioni di donazione con bottoni inline."""
    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"donate_{stars}")]
        for stars, label in DONATION_OPTIONS
    ]
    await update.message.reply_html(
        "⭐ <b>Supporta BusBot!</b>\n\n"
        "BusBot è gratuito. Se ti è utile, offrimi qualcosa:\n\n"
        "Scegli un'opzione:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def donate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Invia l'invoice Stars quando l'utente clicca un bottone di donazione."""
    query = update.callback_query
    await query.answer()

    try:
        stars = int(query.data.split("_")[1])
    except (IndexError, ValueError):
        return

    label = next((lbl for s, lbl in DONATION_OPTIONS if s == stars), f"{stars} ⭐")

    await context.bot.send_invoice(
        chat_id=query.from_user.id,
        title="Supporto a BusBot",
        description=f"{label} — grazie mille! 🙏",
        payload=f"donation_{stars}",
        currency="XTR",           # Telegram Stars (nessun provider esterno)
        prices=[LabeledPrice(label, stars)],
    )


async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Risponde alla PreCheckoutQuery entro 10 secondi (obbligatorio).

    Telegram annulla automaticamente il pagamento se non rispondiamo in tempo.
    """
    query = update.pre_checkout_query
    await query.answer(ok=True)


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confermato il pagamento: registra nel DB e ringrazia l'utente."""
    payment = update.message.successful_payment
    chat_id = update.effective_chat.id
    stars = payment.total_amount   # amount in Stars

    db.increment_ad_impression(chat_id)  # riutilizziamo il contatore esistente
    logger.info("Stars ricevute: chat_id=%s stars=%d", chat_id, stars)

    await update.message.reply_html(
        f"🙏 <b>Grazie mille per le {stars} ⭐!</b>\n\n"
        "Il tuo supporto mantiene BusBot in vita. "
        "Continuerò ad aggiornarti sulle corse soppresse 🚍"
    )


def register_stars_handlers(app: Application) -> None:
    """Registra tutti gli handler per Telegram Stars."""
    from telegram.ext import CallbackQueryHandler

    app.add_handler(CommandHandler("donate", donate_start))
    app.add_handler(CallbackQueryHandler(donate_callback, pattern=r"^donate_\d+$"))
    app.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    app.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler)
    )
