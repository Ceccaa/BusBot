"""Test suite — Endpoint Adsgram reward — BusBot v2.0."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aiohttp.test_utils import AioHTTPTestCase

from db import database as db
from services.ads import create_app


def _tmp_db():
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    return Path(f.name)


class TestAdsEndpoint(AioHTTPTestCase):

    async def get_application(self):
        self.db_path = _tmp_db()
        self.db_patcher = patch.object(db, "DB_PATH", self.db_path)
        self.db_patcher.start()
        db.init_db()
        db.save_user(123456789, "Rimini", ["92"])
        return create_app()

    async def tearDownAsync(self):
        self.db_patcher.stop()
        self.db_path.unlink(missing_ok=True)

    async def test_reward_ok(self):
        resp = await self.client.get("/reward?userid=123456789")
        self.assertEqual(resp.status, 200)
        text = await resp.text()
        self.assertEqual(text, "OK")

    async def test_reward_missing_userid(self):
        resp = await self.client.get("/reward")
        self.assertEqual(resp.status, 400)

    async def test_reward_invalid_userid(self):
        resp = await self.client.get("/reward?userid=abc")
        self.assertEqual(resp.status, 400)

    async def test_reward_increments_db(self):
        await self.client.get("/reward?userid=123456789")
        await self.client.get("/reward?userid=123456789")
        user = db.get_user(123456789)
        self.assertEqual(user["ad_impressions"], 2)

    async def test_reward_unknown_user_no_error(self):
        """Utente non nel DB: increment silenzioso (no crash)."""
        resp = await self.client.get("/reward?userid=999999")
        self.assertEqual(resp.status, 200)


if __name__ == "__main__":
    unittest.main()
