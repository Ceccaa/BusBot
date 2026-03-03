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
import asyncio

from aiohttp import web
from telegram import Bot
from telegram.error import TelegramError

from db import database as db
from services.scraper import get_cancelled_routes
from services.notifications import format_multiline_bulletin

logger = logging.getLogger(__name__)

ADS_SERVER_PORT = int(os.getenv("ADS_SERVER_PORT", "5000"))
bot_instance: Bot | None = None


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
    
    if bot_instance:
        asyncio.create_task(unlock_message_for_user(bot_instance, user_id))
        
    return web.Response(text="OK")


async def handle_ad_view(request: web.Request) -> web.Response:
    """Serve the HTML interface for Telegram Mini App Ads."""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Sblocca Orari - Adsgram</title>
    <!-- 1. Importa SDK Ufficiale di Telegram -->
    <script src="https://telegram.org/js/telegram-web-app.js"></script>

    <!-- 2. Importa SDK Ufficiale di Adsgram (Url aggiornato) -->
    <script src="https://sad.adsgram.ai/js/sad.min.js"></script>

    <style>
        body { background-color: #121212; color: #ffffff; text-align: center; font-family: sans-serif; padding-top: 50px; }
    </style>
</head>
<body>
    <h2>Attendere...</h2>
    <p>Caricamento annuncio pubblicitario in corso...</p>
    <script>
        // Gestione errori globale
        window.onerror = function(msg, url, lineNo, columnNo, error) {
            document.body.innerHTML = "<h2>Errore JS</h2><p>" + msg + "</p><button onclick='Telegram.WebApp.close()'>Chiudi</button>";
            return false;
        };

        // Inizializza l'ambiente Telegram
        Telegram.WebApp.ready();

        // Recupera l'utente ID di Telegram e il Block ID dal T.me Link (?startapp=BLOCKID_USERID)
        const initDataUnsafe = Telegram.WebApp.initDataUnsafe;
        const startParam = initDataUnsafe.start_param || "";
        const parts = startParam.split("_");
        
        const blockId = parts[0]; 
        const userId = parts[1];

        if (!blockId) {
            document.body.innerHTML = "<h2>Errore: Costanti mancanti</h2><p>Nessun start_param rilevato (Block ID mancante).</p>";
        } else if (typeof window.Adsgram === 'undefined') {
            document.body.innerHTML = "<h2>Errore caricamento Adsgram</h2><p>Script non caricato. Disattiva eventuale AdBlock, oppure la connessione è limitata.</p>";
        } else {
            try {
                // Inizializza l'interfaccia di Adsgram
                const AdController = window.Adsgram.init({ blockId: blockId });

                // Ordina di mostrare subito l'annuncio in formato Reward
                AdController.show().then((result) => {
                    // L'UTENTE HA COMPLETATO LA VISIONE
                    if (userId) {
                        // Notifichiamo BusBot usando path relativo, così Cloudflare lo risolve
                        fetch(`/reward?userid=${userId}`)
                        .then(() => {
                            // Chiudi il popup riattivando la chat di Telegram
                            Telegram.WebApp.close();
                        });
                    } else {
                         Telegram.WebApp.close();
                    }
                }).catch((err) => {
                    // L'utente ha chiuso il video in anticipo o errore
                    console.error("AdController err:", err);
                    Telegram.WebApp.showAlert("Pubblicità non guardata, errore o AdBlock attivo.");
                    Telegram.WebApp.close();
                });
            } catch (err) {
                document.body.innerHTML = "<h2>Errore Runtime</h2><p>" + err.message + "</p>";
            }
        }
    </script>
</body>
</html>
"""
    return web.Response(text=html_content, content_type="text/html")

def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/reward", handle_reward)
    app.router.add_get("/ads/view", handle_ad_view)
    return app



async def run_ads_server(bot: Bot | None = None, port: int = ADS_SERVER_PORT) -> None:
    """Start the aiohttp server as an async task."""
    global bot_instance
    bot_instance = bot
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Ads server avviato su http://0.0.0.0:%d — endpoint: /reward", port)

async def unlock_message_for_user(bot: Bot, chat_id: int) -> None:
    """Rigenera il bollettino in chiaro e aggiorna il messaggio se presente in DB."""
    user = db.get_user(chat_id)
    if not user:
        return
        
    last_msg_id = user.get("last_message_id")
    if not last_msg_id:
        return
        
    linee = user.get("linee", [])
    if not linee:
        return
        
    # Rigenerazione status
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
            reply_markup=None  # Rimuove il bottone Adsgram!
        )
        logger.info("Messaggio %s sbloccato per chat_id=%s via webhook", last_msg_id, chat_id)
    except TelegramError as e:
        logger.warning("Impossibile sbloccare il messaggio %s per chat_id=%s: %s", last_msg_id, chat_id, e)
