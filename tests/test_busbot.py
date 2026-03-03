"""Test suite BusBot v2.0 — scraper, matching linee e formattazione.

Test esistenti adattati ai nuovi path di import (services.scraper).
"""

import unittest

from services.scraper import parse_html, linea_matches
from services.notifications import (
    format_multiline_bulletin,
    format_alarm_bulletin,
    format_realtime_alert,
)


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
        self.assertEqual(
            parse_html(PAGE_WITH_DATA, linea="s1"),
            parse_html(PAGE_WITH_DATA, linea="S1"),
        )

    def test_linea_inesistente(self):
        self.assertEqual(parse_html(PAGE_WITH_DATA, linea="999"), [])

    def test_nessun_filtro_restituisce_tutto(self):
        self.assertEqual(len(parse_html(PAGE_WITH_DATA, linea=None)), 6)


# ════════════════════════════════════════════════════════════════════════════
#  Test linea_matches
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
        self.assertFalse(linea_matches("80 Forlì", "8"))

    def test_non_matcha_suffisso(self):
        self.assertFalse(linea_matches("1A Ravenna", "1"))

    def test_stringa_vuota(self):
        self.assertFalse(linea_matches("", "8"))

    def test_solo_spazi(self):
        self.assertFalse(linea_matches("   ", "8"))

    def test_target_con_spazi(self):
        self.assertTrue(linea_matches("8 Forlì", " 8 "))

    def test_linea_senza_citta(self):
        self.assertTrue(linea_matches("92", "92"))


# ════════════════════════════════════════════════════════════════════════════
#  Test formattazione messaggi
# ════════════════════════════════════════════════════════════════════════════


class TestFormatMultilineBulletin(unittest.TestCase):

    def test_nessuna_corsa(self):
        msg = format_multiline_bulletin({"8": [], "92": []})
        self.assertIn("✅", msg)
        self.assertIn("Nessuna corsa soppressa", msg)

    def test_linea_con_soppressione(self):
        routes = parse_html(PAGE_WITH_DATA, linea="8")
        msg = format_multiline_bulletin({"8": routes, "92": []})
        self.assertIn("❌", msg)
        self.assertIn("Linea <b>8</b>", msg)
        self.assertIn("✅", msg)
        self.assertIn("Linea <b>92</b>", msg)

    def test_dizionario_vuoto(self):
        msg = format_multiline_bulletin({})
        self.assertIn("⚠️", msg)

    def test_piu_linee_con_soppressioni(self):
        routes_8 = parse_html(PAGE_WITH_DATA, linea="8")
        routes_s1 = parse_html(PAGE_WITH_DATA, linea="S1")
        msg = format_multiline_bulletin({"8": routes_8, "S1": routes_s1})
        self.assertEqual(msg.count("❌"), 2)


class TestFormatAlarmBulletin(unittest.TestCase):

    def test_include_orario(self):
        msg = format_alarm_bulletin("07:10", {"8": []})
        self.assertIn("07:10", msg)

    def test_include_buona_fortuna(self):
        msg = format_alarm_bulletin("07:10", {"8": []})
        self.assertIn("Buona fortuna", msg)

    def test_linea_soppressa(self):
        routes = parse_html(PAGE_WITH_DATA, linea="8")
        msg = format_alarm_bulletin("15:57", {"8": routes})
        self.assertIn("❌", msg)


class TestFormatRealtimeAlert(unittest.TestCase):

    SAMPLE_ROUTE = {
        "linea": "8 Forlì", "inizio": "Schio",
        "dalle": "07:10", "fine": "Centro",
        "alle": "07:40", "data": "03-03-2026",
    }

    def test_include_linea(self):
        msg = format_realtime_alert("8", [self.SAMPLE_ROUTE])
        self.assertIn("Linea <b>8</b>", msg)

    def test_include_orario(self):
        msg = format_realtime_alert("8", [self.SAMPLE_ROUTE])
        self.assertIn("07:10", msg)


# ════════════════════════════════════════════════════════════════════════════
#  Test fetch dal sito reale (integration)
# ════════════════════════════════════════════════════════════════════════════


class TestFetchReale(unittest.IsolatedAsyncioTestCase):
    """Verifica che il sito sia raggiungibile e il parsing funzioni."""

    async def test_fetch_forli_cesena(self):
        from services.scraper import get_cancelled_routes
        result = await get_cancelled_routes("Forli-Cesena")
        self.assertIsInstance(result, list)

    async def test_fetch_rimini(self):
        from services.scraper import get_cancelled_routes
        result = await get_cancelled_routes("Rimini")
        self.assertIsInstance(result, list)

    async def test_fetch_ravenna(self):
        from services.scraper import get_cancelled_routes
        result = await get_cancelled_routes("Ravenna")
        self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()
