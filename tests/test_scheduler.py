"""Test suite — Scheduler deduplicazione multi-linea — BusBot v2.0."""

import unittest

from scheduler.suppression_check import _hash


# Corse di test
ROUTE_A = {"linea": "8 Forlì", "dalle": "07:10", "alle": "07:40",
           "inizio": "Schio", "fine": "Centro", "data": "03-03-2026"}
ROUTE_B = {"linea": "8 Forlì", "dalle": "08:00", "alle": "08:30",
           "inizio": "Centro", "fine": "Schio", "data": "03-03-2026"}
ROUTE_C = {"linea": "92 Rimini", "dalle": "09:00", "alle": "09:30",
           "inizio": "Stazione", "fine": "Riccione", "data": "03-03-2026"}


class TestSuppressionHash(unittest.TestCase):

    def test_hash_deterministico(self):
        """Lo stesso set di corse produce sempre lo stesso hash."""
        self.assertEqual(_hash([ROUTE_A, ROUTE_B]), _hash([ROUTE_A, ROUTE_B]))

    def test_hash_ordine_indipendente(self):
        """L'ordine delle corse non deve influire sull'hash."""
        self.assertEqual(_hash([ROUTE_A, ROUTE_B]), _hash([ROUTE_B, ROUTE_A]))

    def test_hash_diverso_per_corse_diverse(self):
        self.assertNotEqual(_hash([ROUTE_A]), _hash([ROUTE_B]))

    def test_hash_lista_vuota(self):
        self.assertEqual(_hash([]), "")

    def test_hash_unica_corsa(self):
        h = _hash([ROUTE_A])
        self.assertIsInstance(h, str)
        self.assertGreater(len(h), 0)

    def test_deduplicazione_stessa_chiave_no_notifica(self):
        """Simula il meccanismo di notified dict: stessa chiave = skip."""
        notified = {}
        chat_id = 111
        linea = "8"
        routes = [ROUTE_A, ROUTE_B]

        key = f"{chat_id}:{linea}:{_hash(routes)}"

        # Prima volta: non c'è → notifica
        self.assertNotIn(key, notified)
        notified[key] = True

        # Seconda volta: c'è → skip
        self.assertIn(key, notified)

    def test_deduplicazione_hash_diverso_notifica(self):
        """Hash diverso per la stessa linea → nuova notifica."""
        notified = {}
        chat_id = 111
        linea = "8"

        key1 = f"{chat_id}:{linea}:{_hash([ROUTE_A])}"
        notified[key1] = True

        key2 = f"{chat_id}:{linea}:{_hash([ROUTE_A, ROUTE_B])}"
        self.assertNotIn(key2, notified)

    def test_deduplicazione_per_linea_indipendente(self):
        """Due linee hanno chiavi indipendenti."""
        notified = {}
        chat_id = 111

        key_8 = f"{chat_id}:8:{_hash([ROUTE_A])}"
        key_92 = f"{chat_id}:92:{_hash([ROUTE_C])}"

        notified[key_8] = True
        self.assertNotIn(key_92, notified)

    def test_deduplicazione_per_utenti_diversi(self):
        """Stessa corsa ma utenti diversi → chiavi diverse."""
        routes = [ROUTE_A]
        linea = "8"

        key_111 = f"111:{linea}:{_hash(routes)}"
        key_222 = f"222:{linea}:{_hash(routes)}"

        self.assertNotEqual(key_111, key_222)


if __name__ == "__main__":
    unittest.main()
