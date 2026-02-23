"""Gestione configurazione utenti — persistenza JSON."""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_FILE = Path(os.getenv("CONFIG_PATH", Path(__file__).parent / "user_config.json"))

BACINI = {
    "forli_cesena": "Forli-Cesena",
    "rimini":       "Rimini",
    "ravenna":      "Ravenna",
}


# ── Operazioni CRUD ─────────────────────────────────────────────────────────


def save_user(chat_id: int, bacino: str, linea: str) -> None:
    """Salva (o aggiorna) la configurazione di un utente."""
    data = _load()
    data[str(chat_id)] = {"bacino": bacino, "linea": linea.strip().upper(), "active": True}
    _save(data)


def remove_user(chat_id: int) -> bool:
    """Disattiva il monitoraggio. Restituisce True se l'utente esisteva."""
    data = _load()
    key = str(chat_id)
    if key not in data:
        return False
    data[key]["active"] = False
    _save(data)
    return True


def get_user(chat_id: int) -> dict | None:
    """Restituisce la config di un utente, o None."""
    return _load().get(str(chat_id))


def get_all_active_users() -> dict[str, dict]:
    """Restituisce {chat_id: config} per tutti gli utenti attivi."""
    return {cid: cfg for cid, cfg in _load().items() if cfg.get("active")}


# ── I/O file ────────────────────────────────────────────────────────────────


def _load() -> dict:
    """Legge il JSON. Crea il file se non esiste."""
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text("{}", encoding="utf-8")
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Errore lettura config: %s", exc)
        return {}


def _save(data: dict) -> None:
    """Scrive il dizionario nel file JSON."""
    try:
        CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        logger.error("Errore scrittura config: %s", exc)
