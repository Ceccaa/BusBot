"""Adsgram reward endpoint — aiohttp server (non-blocking).

Adsgram invia una GET request a:
    https://<tunnel>/reward?userid=[userId]

quando l'utente completa la visione dell'ad (evento REWARD).
[userId] viene sostituito automaticamente da Adsgram con il Telegram ID.

Endpoint:
    GET /reward?userid=<chat_id>
    → 200 OK  (incrementa ad_impressions nel DB)
    → 400     (userid mancante o non intero)
"""

import logging
import os

from aiohttp import web

from db import database as db

logger = logging.getLogger(__name__)

ADS_SERVER_PORT = int(os.getenv("ADS_SERVER_PORT", "5000"))


async def handle_reward(request: web.Request) -> web.Response:
    """Handle GET /reward?userid=<id> (chiamato da Adsgram server-side)."""
    user_id_str = request.rel_url.query.get("userid", "").strip()

    if not user_id_str:
        logger.warning("Ads reward: userid mancante")
        return web.Response(status=400, text="Missing userId")

    try:
        user_id = int(user_id_str)
    except ValueError:
        logger.warning("Ads reward: userid non valido: %s", user_id_str)
        return web.Response(status=400, text="Invalid userId")

    db.increment_ad_impression(user_id)
    logger.info("Ads reward registrato per user_id=%d", user_id)
    return web.Response(text="OK")


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/reward", handle_reward)
    return app


async def run_ads_server(port: int = ADS_SERVER_PORT) -> None:
    """Start the aiohttp server as an async task."""
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Ads server avviato su http://0.0.0.0:%d — endpoint: /reward", port)
