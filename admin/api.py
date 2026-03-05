"""Admin API — FastAPI REST per gestione utenti BusBot.

Espone endpoint CRUD per il pannello di amministrazione locale.
Serve anche il frontend React come file statici.
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from db import database as db

logger = logging.getLogger(__name__)

app = FastAPI(title="BusBot Admin", docs_url="/api/docs", redoc_url=None)

# CORS per sviluppo locale (Vite dev server su porta diversa)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pydantic models ─────────────────────────────────────────────────────────


class UserUpdate(BaseModel):
    bacino: Optional[str] = None
    is_active: Optional[bool] = None
    notifiche_realtime: Optional[bool] = None
    is_permanent_supporter: Optional[bool] = None
    linee: Optional[list[str]] = None
    alarms: Optional[list[str]] = None


# ── API Routes ───────────────────────────────────────────────────────────────


@app.get("/api/stats")
def get_stats():
    """Statistiche globali per la dashboard."""
    return db.get_stats()


@app.get("/api/users")
def get_users():
    """Lista completa di tutti gli utenti."""
    return db.get_all_users()


@app.get("/api/users/{user_id}")
def get_user(user_id: int):
    """Dettaglio singolo utente."""
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    return user


@app.put("/api/users/{user_id}")
def update_user(user_id: int, data: UserUpdate):
    """Aggiorna la configurazione di un utente."""
    kwargs = data.model_dump(exclude_none=True)
    if not kwargs:
        raise HTTPException(status_code=400, detail="Nessun campo da aggiornare")
    ok = db.update_user(user_id, **kwargs)
    if not ok:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    return db.get_user(user_id)


@app.delete("/api/users/{user_id}")
def delete_user(user_id: int):
    """Elimina un utente e tutti i suoi dati."""
    ok = db.delete_user(user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    return {"ok": True, "deleted": user_id}


# ── Static files (SPA frontend) ──────────────────────────────────────────────

FRONTEND_DIR = Path(__file__).parent / "frontend"


def mount_static():
    """Monta i file statici del frontend, se presenti."""
    if FRONTEND_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

        @app.get("/")
        async def serve_index():
            return FileResponse(FRONTEND_DIR / "index.html")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """Fallback: serve index.html per tutte le route non-API."""
            file_path = FRONTEND_DIR / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(FRONTEND_DIR / "index.html")
    else:
        logger.warning("Frontend non trovato in %s", FRONTEND_DIR)


mount_static()
