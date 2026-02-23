"""Test suite per BusBot — scraper, matching linee e configurazione utenti."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config
from scraper import parse_html, linea_matches, format_routes


# ════════════════════════════════════════════════════════════════════════════
#  HTML di test — riproduce fedelmente la struttura di Start Romagna
# ════════════════════════════════════════════════════════════════════════════

PAGE_WITH_DATA = """
<html><body>
<table class="table">
  <tr>
    <td><input id="Text1" placeholder="Filtra per Linea" type="text"/></td>
    <td><input id="Text2" placeholder="Filtra per Inizio" type="text"/></td>
    <td><input id="Text3" placeholder="Filtra per Dalle" type="text"/></td>
    <td><input id="Text4" placeholder="Filtra per Fine" type="text"/></td>
    <td><input id="Text5" placeholder="Filtra per Alle" type="text"/></td>
    <td><button id="clearBtn">Azzera Filtri</button></td>
  </tr>
</table>
<table class="table table-bordered">
  <tr><th>LINEA</th><th>INIZIO</th><th>DALLE</th><th>FINE</th><th>ALLE</th><th>DATA</th></tr>
  <tr><td>8 Forlì</td><td>Schio (Lunga)</td><td>15:57</td><td>V.Federico Ii</td><td>16:24</td><td>23-02-2026</td></tr>
  <tr><td>8 Forlì</td><td>V.Federico Ii</td><td>16:25</td><td>Schio (Lunga)</td><td>16:52</td><td>23-02-2026</td></tr>
  <tr><td>S1 Forlì</td><td>Centro Studi (Moro)</td><td>14:05</td><td>Pievequinta</td><td>14:35</td><td>23-02-2026</td></tr>
  <tr><td>3 Cesena</td><td>Stazione FS</td><td>07:00</td><td>Ospedale</td><td>07:30</td><td>23-02-2026</td></tr>
  <tr><td>92 Rimini</td><td>Stazione</td><td>08:10</td><td>Riccione</td><td>08:45</td><td>23-02-2026</td></tr>
  <tr><td>1A Ravenna</td><td>P.zza Caduti</td><td>09:00</td><td>Marina</td><td>09:25</td><td>23-02-2026</td></tr>
</table>
</body></html>
"""

PAGE_EMPTY = """
<html><body>
<table class="table">
  <tr>
    <td><input id="Text1" type="text"/></td>
    <td><input id="Text2" type="text"/></td>
    <td><input id="Text3" type="text"/></td>
    <td><input id="Text4" type="text"/></td>
    <td><input id="Text5" type="text"/></td>
    <td><button>Azzera Filtri</button></td>
  </tr>
</table>
</body></html>
"""

PAGE_NO_TABLE = "<html><body><p>Pagina vuota</p></body></html>"


# ════════════════════════════════════════════════════════════════════════════
#  Test parsing HTML
# ════════════════════════════════════════════════════════════════════════════


class TestParseHtml(unittest.TestCase):

    def test_trova_tutte_le_corse(self):
        result = parse_html(PAGE_WITH_DATA)
        self.assertEqual(len(result), 6)

    def test_campi_prima_riga(self):
        result = parse_html(PAGE_WITH_DATA)
        primo = result[0]
        self.assertEqual(primo["linea"],  "8 Forlì")
        self.assertEqual(primo["inizio"], "Schio (Lunga)")
        self.assertEqual(primo["dalle"],  "15:57")
        self.assertEqual(primo["fine"],   "V.Federico Ii")
        self.assertEqual(primo["alle"],   "16:24")
        self.assertEqual(primo["data"],   "23-02-2026")

    def test_ignora_riga_filtri(self):
        """La riga con <input> non deve apparire nei risultati."""
        result = parse_html(PAGE_WITH_DATA)
        for r in result:
            self.assertNotIn("Filtra", r["linea"])

    def test_pagina_vuota_restituisce_lista_vuota(self):
        self.assertEqual(parse_html(PAGE_EMPTY), [])

    def test_pagina_senza_tabella(self):
        self.assertEqual(parse_html(PAGE_NO_TABLE), [])


# ════════════════════════════════════════════════════════════════════════════
#  Test filtro per linea
# ════════════════════════════════════════════════════════════════════════════


class TestFiltroLinea(unittest.TestCase):

    def test_filtra_linea_8(self):
        result = parse_html(PAGE_WITH_DATA, linea="8")
        self.assertEqual(len(result), 2)
        self.assertTrue(all("8" in r["linea"] for r in result))

    def test_filtra_linea_s1(self):
        result = parse_html(PAGE_WITH_DATA, linea="S1")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["linea"], "S1 Forlì")

    def test_filtra_linea_3(self):
        result = parse_html(PAGE_WITH_DATA, linea="3")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["inizio"], "Stazione FS")

    def test_filtra_linea_92(self):
        result = parse_html(PAGE_WITH_DATA, linea="92")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["fine"], "Riccione")

    def test_filtra_linea_alfanumerica_1a(self):
        result = parse_html(PAGE_WITH_DATA, linea="1A")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["linea"], "1A Ravenna")

    def test_filtra_case_insensitive(self):
        """'s1' deve funzionare come 'S1'."""
        self.assertEqual(
            parse_html(PAGE_WITH_DATA, linea="s1"),
            parse_html(PAGE_WITH_DATA, linea="S1"),
        )

    def test_linea_inesistente(self):
        self.assertEqual(parse_html(PAGE_WITH_DATA, linea="999"), [])

    def test_nessun_filtro_restituisce_tutto(self):
        self.assertEqual(len(parse_html(PAGE_WITH_DATA, linea=None)), 6)


# ════════════════════════════════════════════════════════════════════════════
#  Test linea_matches — matching "NUMERO CITTÀ" → "NUMERO"
# ════════════════════════════════════════════════════════════════════════════


class TestLineaMatches(unittest.TestCase):

    def test_numero_semplice(self):
        self.assertTrue(linea_matches("8 Forlì", "8"))

    def test_numero_con_lettera(self):
        self.assertTrue(linea_matches("S1 Forlì", "S1"))

    def test_alfanumerico(self):
        self.assertTrue(linea_matches("1A Ravenna", "1A"))

    def test_case_insensitive_target(self):
        self.assertTrue(linea_matches("S1 Forlì", "s1"))

    def test_case_insensitive_row(self):
        self.assertTrue(linea_matches("s1 forlì", "S1"))

    def test_non_matcha_numero_diverso(self):
        self.assertFalse(linea_matches("8 Forlì", "3"))

    def test_non_matcha_prefisso_parziale(self):
        """'8' non deve matchare '80', solo match esatto sul primo token."""
        self.assertFalse(linea_matches("80 Forlì", "8"))

    def test_non_matcha_suffisso(self):
        """'1' non deve matchare '1A'."""
        self.assertFalse(linea_matches("1A Ravenna", "1"))

    def test_stringa_vuota(self):
        self.assertFalse(linea_matches("", "8"))

    def test_solo_spazi(self):
        self.assertFalse(linea_matches("   ", "8"))

    def test_target_con_spazi(self):
        """Spazi nel target devono essere ignorati."""
        self.assertTrue(linea_matches("8 Forlì", " 8 "))

    def test_linea_senza_citta(self):
        """Caso ipotetico: solo il numero senza città."""
        self.assertTrue(linea_matches("92", "92"))


# ════════════════════════════════════════════════════════════════════════════
#  Test formattazione messaggi
# ════════════════════════════════════════════════════════════════════════════


class TestFormatRoutes(unittest.TestCase):

    def test_nessuna_corsa(self):
        msg = format_routes([])
        self.assertIn("✅", msg)
        self.assertIn("Nessuna", msg)

    def test_formattazione_con_dati(self):
        routes = [{
            "linea": "8 Forlì", "inizio": "Schio (Lunga)",
            "dalle": "15:57", "fine": "V.Federico Ii",
            "alle": "16:24", "data": "23-02-2026",
        }]
        msg = format_routes(routes)
        self.assertIn("❌", msg)
        self.assertIn("Linea 8 Forlì", msg)
        self.assertIn("Schio (Lunga)", msg)
        self.assertIn("15:57", msg)
        self.assertIn("V.Federico Ii", msg)

    def test_piu_corse(self):
        routes = parse_html(PAGE_WITH_DATA, linea="8")
        msg = format_routes(routes)
        self.assertEqual(msg.count("❌"), 2)


# ════════════════════════════════════════════════════════════════════════════
#  Test fetch dal sito reale (integration)
# ════════════════════════════════════════════════════════════════════════════


class TestFetchReale(unittest.TestCase):
    """Verifica che il sito sia raggiungibile e il parsing funzioni."""

    def test_fetch_forli_cesena(self):
        from scraper import get_cancelled_routes
        result = get_cancelled_routes("Forli-Cesena")
        self.assertIsInstance(result, list)

    def test_fetch_rimini(self):
        from scraper import get_cancelled_routes
        result = get_cancelled_routes("Rimini")
        self.assertIsInstance(result, list)

    def test_fetch_ravenna(self):
        from scraper import get_cancelled_routes
        result = get_cancelled_routes("Ravenna")
        self.assertIsInstance(result, list)


# ════════════════════════════════════════════════════════════════════════════
#  Test configurazione utenti
# ════════════════════════════════════════════════════════════════════════════


class TestConfig(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8")
        self.tmp.write("{}")
        self.tmp.close()
        self.patcher = patch.object(config, "CONFIG_FILE", Path(self.tmp.name))
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        Path(self.tmp.name).unlink(missing_ok=True)

    def test_salva_e_leggi(self):
        config.save_user(111, "Forli-Cesena", "8")
        user = config.get_user(111)
        self.assertEqual(user["bacino"], "Forli-Cesena")
        self.assertEqual(user["linea"], "8")
        self.assertTrue(user["active"])

    def test_linea_maiuscola(self):
        config.save_user(111, "Rimini", "1a")
        self.assertEqual(config.get_user(111)["linea"], "1A")

    def test_aggiorna_utente(self):
        config.save_user(111, "Rimini", "92")
        config.save_user(111, "Ravenna", "5")
        self.assertEqual(config.get_user(111)["bacino"], "Ravenna")

    def test_disattiva(self):
        config.save_user(111, "Rimini", "92")
        self.assertTrue(config.remove_user(111))
        self.assertFalse(config.get_user(111)["active"])

    def test_disattiva_inesistente(self):
        self.assertFalse(config.remove_user(999))

    def test_utente_inesistente(self):
        self.assertIsNone(config.get_user(999))

    def test_utenti_attivi(self):
        config.save_user(111, "Rimini", "92")
        config.save_user(222, "Ravenna", "1A")
        config.remove_user(222)
        active = config.get_all_active_users()
        self.assertIn("111", active)
        self.assertNotIn("222", active)

    def test_file_corrotto(self):
        Path(self.tmp.name).write_text("{{broken", encoding="utf-8")
        self.assertIsNone(config.get_user(111))


if __name__ == "__main__":
    unittest.main()
