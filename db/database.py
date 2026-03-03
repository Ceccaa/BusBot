"""Database layer — SQLite persistence for BusBot v2.0.

Replace the old config.py JSON layer with a proper relational DB.
All functions use short-lived connections (thread-safe single-writer SQLite).
"""

import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(os.getenv("DB_PATH", Path(__file__).parent.parent / "busbot.db"))


# ── Connection helper ────────────────────────────────────────────────────────


@contextmanager
def _conn():
    """Yield a short-lived SQLite connection with WAL mode for concurrency."""
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


# ── Schema init ──────────────────────────────────────────────────────────────


def init_db() -> None:
    """Create tables and indexes if they do not exist."""
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id            INTEGER PRIMARY KEY,
                chat_id            INTEGER NOT NULL,
                bacino             TEXT    NOT NULL,
                notifiche_realtime BOOLEAN DEFAULT 0,
                is_active          BOOLEAN DEFAULT 1,
                ad_impressions     INTEGER DEFAULT 0,
                last_ad_date       TEXT    DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS user_lines (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                linea   TEXT    NOT NULL,
                UNIQUE (user_id, linea)
            );

            CREATE TABLE IF NOT EXISTS user_alarms (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                orario  TEXT    NOT NULL,  -- HH:MM
                UNIQUE (user_id, orario)
            );

            CREATE INDEX IF NOT EXISTS idx_user_lines_user  ON user_lines(user_id);
            CREATE INDEX IF NOT EXISTS idx_user_alarms_user ON user_alarms(user_id);
            CREATE INDEX IF NOT EXISTS idx_user_alarms_time ON user_alarms(orario);
        """)
        
        # Retrocompatibilità: aggiungo la colonna se non esiste nei db vecchi
        try:
            con.execute("ALTER TABLE users ADD COLUMN last_ad_date TEXT DEFAULT NULL")
            logger.info("Migrazione schema DB: colonna last_ad_date aggiunta.")
        except sqlite3.OperationalError:
            pass  # Colonna già esistente
            
    logger.info("DB initialized at %s", DB_PATH)


# ── User CRUD ────────────────────────────────────────────────────────────────


def save_user(chat_id: int, bacino: str, linee: list[str]) -> None:
    """Upsert user, then replace their monitored lines."""
    normalized = [linea.strip().upper() for linea in linee if linea.strip()]
    if not normalized:
        raise ValueError("Almeno una linea è richiesta.")

    with _conn() as con:
        con.execute("""
            INSERT INTO users (user_id, chat_id, bacino, is_active)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                chat_id   = excluded.chat_id,
                bacino    = excluded.bacino,
                is_active = 1
        """, (chat_id, chat_id, bacino))

        # Replace lines atomically
        con.execute("DELETE FROM user_lines WHERE user_id = ?", (chat_id,))
        con.executemany(
            "INSERT OR IGNORE INTO user_lines (user_id, linea) VALUES (?, ?)",
            [(chat_id, linea) for linea in normalized],
        )


def get_user(chat_id: int) -> dict | None:
    """Return user config dict with lines and alarms, or None."""
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM users WHERE user_id = ?", (chat_id,)
        ).fetchone()
        if not row:
            return None
        user: dict[str, Any] = dict(row)
        user["linee"] = _get_lines(con, chat_id)
        user["alarms"] = _get_alarms(con, chat_id)
        return user


def deactivate_user(chat_id: int) -> bool:
    """Set is_active=0. Returns True if user existed."""
    with _conn() as con:
        cur = con.execute(
            "UPDATE users SET is_active = 0 WHERE user_id = ? AND is_active = 1",
            (chat_id,),
        )
        return cur.rowcount > 0
    return False


def get_all_active_users() -> list[dict]:
    """Return all active users with their lines and alarms."""
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM users WHERE is_active = 1"
        ).fetchall()
        result = []
        for row in rows:
            user: dict[str, Any] = dict(row)
            user["linee"] = _get_lines(con, user["user_id"])
            user["alarms"] = _get_alarms(con, user["user_id"])
            result.append(user)
        return result


# ── Alarms CRUD ──────────────────────────────────────────────────────────────


def save_alarms(chat_id: int, orari: list[str]) -> None:
    """Replace all alarms for a user."""
    with _conn() as con:
        con.execute("DELETE FROM user_alarms WHERE user_id = ?", (chat_id,))
        con.executemany(
            "INSERT OR IGNORE INTO user_alarms (user_id, orario) VALUES (?, ?)",
            [(chat_id, o.strip()) for o in orari if o.strip()],
        )


def get_users_with_alarm(orario: str) -> list[dict]:
    """Return active users who have an alarm set at the given HH:MM."""
    with _conn() as con:
        rows = con.execute("""
            SELECT DISTINCT u.*
            FROM users u
            JOIN user_alarms a ON a.user_id = u.user_id
            WHERE u.is_active = 1 AND a.orario = ?
        """, (orario,)).fetchall()
        result = []
        for row in rows:
            user: dict[str, Any] = dict(row)
            user["linee"] = _get_lines(con, user["user_id"])
            user["alarms"] = _get_alarms(con, user["user_id"])
            result.append(user)
        return result


# ── Real-time ────────────────────────────────────────────────────────────────


def set_realtime(chat_id: int, enabled: bool) -> bool:
    """Toggle realtime notifications. Returns True if user existed."""
    with _conn() as con:
        cur = con.execute(
            "UPDATE users SET notifiche_realtime = ? WHERE user_id = ?",
            (1 if enabled else 0, chat_id),
        )
        return cur.rowcount > 0
    return False


# ── Ads ──────────────────────────────────────────────────────────────────────


def increment_ad_impression(user_id: int) -> None:
    """Increment ad_impressions counter for a user and record today's date."""
    today_iso = datetime.now().date().isoformat()
    with _conn() as con:
        con.execute(
            """UPDATE users 
               SET ad_impressions = ad_impressions + 1,
                   last_ad_date = ?
               WHERE user_id = ?""",
            (today_iso, user_id),
        )


def is_unlocked(chat_id: int) -> bool:
    """Return True if the user has watched an ad today."""
    today_iso = datetime.now().date().isoformat()
    with _conn() as con:
        row = con.execute(
            "SELECT last_ad_date FROM users WHERE user_id = ?", (chat_id,)
        ).fetchone()
        if not row or not row["last_ad_date"]:
            return False
        return row["last_ad_date"] == today_iso


# ── Internal helpers ─────────────────────────────────────────────────────────


def _get_lines(con: sqlite3.Connection, user_id: int) -> list[str]:
    rows = con.execute(
        "SELECT linea FROM user_lines WHERE user_id = ? ORDER BY linea",
        (user_id,),
    ).fetchall()
    return [row["linea"] for row in rows]


def _get_alarms(con: sqlite3.Connection, user_id: int) -> list[str]:
    rows = con.execute(
        "SELECT orario FROM user_alarms WHERE user_id = ? ORDER BY orario",
        (user_id,),
    ).fetchall()
    return [row["orario"] for row in rows]
