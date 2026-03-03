"""Test suite — Database layer (SQLite) per BusBot v2.0."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from db import database as db


def _tmp_db():
    """Crea un DB temporaneo e patcha DB_PATH."""
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    return Path(f.name)


class TestDatabase(unittest.TestCase):

    def setUp(self):
        self.db_path = _tmp_db()
        self.patcher = patch.object(db, "DB_PATH", self.db_path)
        self.patcher.start()
        db.init_db()

    def tearDown(self):
        self.patcher.stop()
        self.db_path.unlink(missing_ok=True)

    # ── save / get user ──────────────────────────────────────────────────────

    def test_save_and_get_user(self):
        db.save_user(111, "Forli-Cesena", ["8"])
        user = db.get_user(111)
        self.assertIsNotNone(user)
        self.assertEqual(user["bacino"], "Forli-Cesena")
        self.assertTrue(user["is_active"])

    def test_multiline_save(self):
        db.save_user(111, "Forli-Cesena", ["8", "92", "1A"])
        user = db.get_user(111)
        self.assertIn("8", user["linee"])
        self.assertIn("92", user["linee"])
        self.assertIn("1A", user["linee"])
        self.assertEqual(len(user["linee"]), 3)

    def test_linea_normalizzata_maiuscola(self):
        db.save_user(111, "Rimini", ["1a", "s1"])
        user = db.get_user(111)
        self.assertIn("1A", user["linee"])
        self.assertIn("S1", user["linee"])

    def test_upsert_aggiorna_utente(self):
        db.save_user(111, "Rimini", ["92"])
        db.save_user(111, "Ravenna", ["5", "8"])
        user = db.get_user(111)
        self.assertEqual(user["bacino"], "Ravenna")
        self.assertEqual(len(user["linee"]), 2)

    def test_utente_inesistente(self):
        self.assertIsNone(db.get_user(999))

    # ── deactivate ───────────────────────────────────────────────────────────

    def test_deactivate_user(self):
        db.save_user(111, "Rimini", ["92"])
        result = db.deactivate_user(111)
        self.assertTrue(result)
        self.assertFalse(db.get_user(111)["is_active"])

    def test_deactivate_inesistente(self):
        self.assertFalse(db.deactivate_user(999))

    def test_get_all_active_filters_inactive(self):
        db.save_user(111, "Rimini", ["92"])
        db.save_user(222, "Ravenna", ["1A"])
        db.deactivate_user(222)
        active = db.get_all_active_users()
        ids = [u["user_id"] for u in active]
        self.assertIn(111, ids)
        self.assertNotIn(222, ids)

    # ── alarms ───────────────────────────────────────────────────────────────

    def test_save_and_query_alarms(self):
        db.save_user(111, "Forli-Cesena", ["8"])
        db.save_alarms(111, ["07:10", "13:30"])
        users = db.get_users_with_alarm("07:10")
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["user_id"], 111)

    def test_alarm_wrong_time_no_match(self):
        db.save_user(111, "Forli-Cesena", ["8"])
        db.save_alarms(111, ["07:10"])
        self.assertEqual(db.get_users_with_alarm("08:00"), [])

    def test_save_alarms_replaces_previous(self):
        db.save_user(111, "Forli-Cesena", ["8"])
        db.save_alarms(111, ["07:10", "13:30"])
        db.save_alarms(111, ["18:45"])
        user = db.get_user(111)
        self.assertEqual(user["alarms"], ["18:45"])

    def test_remove_all_alarms(self):
        db.save_user(111, "Forli-Cesena", ["8"])
        db.save_alarms(111, ["07:10"])
        db.save_alarms(111, [])
        self.assertEqual(db.get_users_with_alarm("07:10"), [])

    # ── realtime ─────────────────────────────────────────────────────────────

    def test_realtime_toggle(self):
        db.save_user(111, "Rimini", ["92"])
        result = db.set_realtime(111, True)
        self.assertTrue(result)
        self.assertTrue(db.get_user(111)["notifiche_realtime"])

    def test_realtime_toggle_off(self):
        db.save_user(111, "Rimini", ["92"])
        db.set_realtime(111, True)
        db.set_realtime(111, False)
        self.assertFalse(db.get_user(111)["notifiche_realtime"])

    def test_realtime_inesistente(self):
        result = db.set_realtime(999, True)
        self.assertFalse(result)

    # ── ad impressions ────────────────────────────────────────────────────────

    def test_increment_ad_impression(self):
        db.save_user(111, "Rimini", ["92"])
        db.increment_ad_impression(111)
        db.increment_ad_impression(111)
        user = db.get_user(111)
        self.assertEqual(user["ad_impressions"], 2)
        self.assertIsNotNone(user.get("last_ad_date"))

    def test_is_unlocked(self):
        db.save_user(111, "Rimini", ["92"])
        self.assertFalse(db.is_unlocked(111))  # Inizialmente False
        db.increment_ad_impression(111)
        self.assertTrue(db.is_unlocked(111))  # Dopo impression è True


# ════════════════════════════════════════════════════════════════════════════
#  Test migrazione JSON → SQLite
# ════════════════════════════════════════════════════════════════════════════


class TestMigrate(unittest.TestCase):

    def setUp(self):
        self.db_path = _tmp_db()
        self.db_patcher = patch.object(db, "DB_PATH", self.db_path)
        self.db_patcher.start()
        db.init_db()

    def tearDown(self):
        self.db_patcher.stop()
        self.db_path.unlink(missing_ok=True)

    def test_migrate_basic(self):
        from db import migrate

        json_data = {
            "111": {"bacino": "Forli-Cesena", "linea": "8", "active": True},
            "222": {"bacino": "Rimini", "linea": "92", "active": False},
        }
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as f:
            json.dump(json_data, f)
            json_path = Path(f.name)

        try:
            migrate.migrate(json_path)

            u1 = db.get_user(111)
            self.assertIsNotNone(u1)
            self.assertEqual(u1["bacino"], "Forli-Cesena")
            self.assertIn("8", u1["linee"])
            self.assertTrue(u1["is_active"])

            u2 = db.get_user(222)
            self.assertIsNotNone(u2)
            self.assertFalse(u2["is_active"])

        finally:
            json_path.unlink(missing_ok=True)

    def test_migrate_idempotente(self):
        from db import migrate

        json_data = {"111": {"bacino": "Rimini", "linea": "3", "active": True}}
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as f:
            json.dump(json_data, f)
            json_path = Path(f.name)

        try:
            migrate.migrate(json_path)
            migrate.migrate(json_path)  # seconda esecuzione — nessun errore

            # Solo un record nel DB
            users = db.get_all_active_users()
            self.assertEqual(len(users), 1)
        finally:
            json_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
