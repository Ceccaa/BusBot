"""BusBot v2.0 — Entry point.

Avvia in parallelo:
  1. Bot Telegram (polling)
  2. Job queue: suppression_check ogni 30 minuti
  3. Job queue: alarm_digest ogni 60 secondi
"""

import logging
import os

from dotenv import load_dotenv
from telegram.ext import Application

from bot.conversations import register_conversation_handlers
from bot.handlers import register_command_handlers
from bot.stars import register_stars_handlers
from db import database as db
from scheduler.alarm_digest import alarm_digest_job
from scheduler.suppression_check import suppression_check_job

# ── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise SystemExit("TELEGRAM_BOT_TOKEN non trovato in .env")

CHECK_INTERVAL = 30 * 60   # 30 minuti
ALARM_INTERVAL = 60        # 1 minuto



# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    """Avvia il bot e tutti i servizi."""
    # Inizializza il DB (crea tabelle se non esistono)
    db.init_db()
    logger.info("DB inizializzato.")

    app = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    register_conversation_handlers(app)
    register_command_handlers(app)
    register_stars_handlers(app)

    app.job_queue.run_repeating(suppression_check_job, interval=CHECK_INTERVAL, first=10)
    app.job_queue.run_repeating(alarm_digest_job, interval=ALARM_INTERVAL, first=5)

    logger.info(
        "BusBot v2.0 avviato — check ogni %d min, alarm digest ogni %d sec",
        CHECK_INTERVAL // 60,
        ALARM_INTERVAL,
    )

    app.run_polling()


if __name__ == "__main__":
    main()
