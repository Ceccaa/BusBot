"""Migration script: user_config.json → SQLite (BusBot v1 → v2).

Usage:
    python -m db.migrate [--json-path PATH]

Features:
- Idempotent: safe to run multiple times (INSERT OR IGNORE)
- Preserves original JSON (read-only)
- Logs every processed user
"""

import argparse
import json
import logging
from pathlib import Path

from db import database as db

logging.basicConfig(
    format="%(asctime)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

DEFAULT_JSON = Path(__file__).parent.parent / "user_config.json"


def migrate(json_path: Path) -> None:
    if not json_path.exists():
        logger.error("File non trovato: %s", json_path)
        raise SystemExit(1)

    try:
        data: dict = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Errore lettura JSON: %s", exc)
        raise SystemExit(1) from exc

    if not data:
        logger.info("JSON vuoto — nulla da migrare.")
        return

    db.init_db()

    ok = skipped = errors = 0

    for chat_id_str, cfg in data.items():
        chat_id = int(chat_id_str)
        bacino: str = cfg.get("bacino", "")
        linea: str = cfg.get("linea", "")
        is_active: bool = cfg.get("active", True)

        if not bacino or not linea:
            logger.warning("Utente %s ignorato (bacino/linea mancanti)", chat_id)
            skipped += 1
            continue

        try:
            # Check if user already exists in DB
            existing = db.get_user(chat_id)
            if existing:
                logger.info("Utente %s già presente nel DB — salto.", chat_id)
                skipped += 1
                continue

            # Save user with single line (v1 schema)
            db.save_user(chat_id, bacino, [linea])

            # Respect is_active flag
            if not is_active:
                db.deactivate_user(chat_id)

            logger.info(
                "Migrato utente %s | bacino=%s | linea=%s | active=%s",
                chat_id, bacino, linea, is_active,
            )
            ok += 1

        except Exception as exc:
            logger.error("Errore migrazione utente %s: %s", chat_id, exc)
            errors += 1

    logger.info(
        "Migrazione completata — OK: %d | Skipati: %d | Errori: %d",
        ok, skipped, errors,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Migra user_config.json → SQLite")
    parser.add_argument(
        "--json-path",
        type=Path,
        default=DEFAULT_JSON,
        help=f"Percorso del JSON (default: {DEFAULT_JSON})",
    )
    args = parser.parse_args()
    migrate(args.json_path)


if __name__ == "__main__":
    main()
