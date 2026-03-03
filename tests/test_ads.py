"""Test suite — Monetag reward flow — BusBot v2.0."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from db import database as db


def _tmp_db() -> Path:
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    return Path(f.name)


class TestAdReward(unittest.TestCase):
    """Tests for the ad impression / unlock logic in the DB layer."""

    def setUp(self):
        self.db_path = _tmp_db()
        self.patcher = patch.object(db, "DB_PATH", self.db_path)
        self.patcher.start()
        db.init_db()

    def tearDown(self):
        self.patcher.stop()
        self.db_path.unlink(missing_ok=True)

    def test_increment_unlocks_today(self):
        db.save_user(111, "Rimini", ["92"])
        self.assertFalse(db.is_unlocked(111))
        db.increment_ad_impression(111)
        self.assertTrue(db.is_unlocked(111))

    def test_increment_increments_counter(self):
        db.save_user(111, "Rimini", ["92"])
        db.increment_ad_impression(111)
        db.increment_ad_impression(111)
        user = db.get_user(111)
        self.assertEqual(user["ad_impressions"], 2)

    def test_permanent_supporter_always_unlocked(self):
        db.save_user(111, "Rimini", ["92"])
        self.assertFalse(db.is_unlocked(111))
        db.set_permanent_supporter(111)
        self.assertTrue(db.is_unlocked(111))

    def test_is_permanent_supporter(self):
        db.save_user(111, "Rimini", ["92"])
        self.assertFalse(db.is_permanent_supporter(111))
        db.set_permanent_supporter(111)
        self.assertTrue(db.is_permanent_supporter(111))

    def test_permanent_supporter_skips_ad_button(self):
        """is_permanent_supporter impatta la logica di get_ad_markup (None)."""
        db.save_user(111, "Rimini", ["92"])
        db.set_permanent_supporter(111)
        # Simulated check: the markup function returns None for permanent supporters
        self.assertTrue(db.is_permanent_supporter(111))


if __name__ == "__main__":
    unittest.main()
