"""BusBot — Entry point.

Avvia il bot Telegram e il job periodico per le corse soppresse.
"""

import logging
import os
from datetime import datetime, time as dt_time

from dotenv import load_dotenv
from telegram.ext import Application

from bot import register_handlers
from config import get_all_active_users
from scraper import format_routes, get_cancelled_routes, linea_matches

# ── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ── Configurazione ──────────────────────────────────────────────────────────

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise SystemExit("TELEGRAM_BOT_TOKEN non trovato in .env")

CHECK_INTERVAL = 30 * 60   # secondi (30 minuti)
ACTIVE_START = dt_time(5, 30)
ACTIVE_END = dt_time(22, 0)


# ── Job periodico ───────────────────────────────────────────────────────────


async def periodic_check(context) -> None:
    """Controlla le corse soppresse per tutti gli utenti attivi."""
    now = datetime.now().time()
    if not (ACTIVE_START <= now <= ACTIVE_END):
        return

    users = get_all_active_users()
    if not users:
        return

    logger.info("Controllo periodico — %d utenti attivi", len(users))

    # Raggruppa per bacino → una sola richiesta HTTP per bacino
    by_bacino: dict[str, list[tuple[str, dict]]] = {}
    for chat_id, cfg in users.items():
        by_bacino.setdefault(cfg["bacino"], []).append((chat_id, cfg))

    notified = context.bot_data.setdefault("notified", {})

    for bacino, user_list in by_bacino.items():
        all_routes = get_cancelled_routes(bacino)

        for chat_id, cfg in user_list:
            user_routes = [r for r in all_routes if linea_matches(r["linea"], cfg["linea"])]
            if not user_routes:
                continue

            key = f"{chat_id}:{_hash(user_routes)}"
            if key in notified:
                continue

            try:
                await context.bot.send_message(
                    chat_id=int(chat_id),
                    text=format_routes(user_routes),
                    parse_mode="HTML",
                )
                notified[key] = True
                logger.info("Notifica → %s (linea %s)", chat_id, cfg["linea"])
            except Exception as exc:
                logger.error("Errore notifica → %s: %s", chat_id, exc)


def _hash(routes: list[dict]) -> str:
    """Hash semplice di un set di corse per deduplicazione."""
    return "|".join(sorted(f"{r['linea']}-{r['dalle']}" for r in routes))


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> None:
    """Avvia il bot."""
    logger.info("Avvio BusBot...")

    app = Application.builder().token(TOKEN).build()
    register_handlers(app)

    app.job_queue.run_repeating(periodic_check, interval=CHECK_INTERVAL, first=10)

    logger.info("Bot avviato — check ogni %d min (%s–%s)", CHECK_INTERVAL // 60, ACTIVE_START, ACTIVE_END)
    app.run_polling()


if __name__ == "__main__":
    main()
