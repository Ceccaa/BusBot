"""Scraper per le corse non garantite di Start Romagna."""

import logging
from datetime import date

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://servizi.startromagna.it/corsesoppresse/corsesopp"
TIMEOUT = 20


# ── Funzioni pubbliche ──────────────────────────────────────────────────────


def get_cancelled_routes(bacino: str, linea: str | None = None) -> list[dict]:
    """Scarica le corse soppresse dal sito Start Romagna.

    Args:
        bacino: "Forli-Cesena", "Rimini" o "Ravenna".
        linea:  Numero della linea (es. "3", "92"). None = tutte.

    Returns:
        Lista di dict con: linea, inizio, dalle, fine, alle, data.
    """
    params = {"param1": bacino, "param2": date.today().isoformat()}

    try:
        response = requests.get(BASE_URL, params=params, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Errore HTTP per %s: %s", bacino, exc)
        return []

    return parse_html(response.text, linea)


def parse_html(html: str, linea: str | None = None) -> list[dict]:
    """Parsa la tabella HTML delle corse soppresse.

    La pagina ha due <table>:
      - Filtri (contiene <input>)
      - Dati  (colonne: LINEA · INIZIO · DALLE · FINE · ALLE · DATA)

    Il campo LINEA ha formato "NUMERO CITTÀ" (es. "8 Forlì").
    """
    soup = BeautifulSoup(html, "html.parser")
    table = _find_data_table(soup)
    if not table:
        return []

    results = []
    for row in table.find_all("tr"):
        cells = row.find_all("td")

        if len(cells) < 5 or _is_filter_row(cells):
            continue

        row_linea = cells[0].get_text(strip=True)
        if not row_linea:
            continue

        if linea and not linea_matches(row_linea, linea):
            continue

        results.append({
            "linea":  row_linea,
            "inizio": cells[1].get_text(strip=True),
            "dalle":  cells[2].get_text(strip=True),
            "fine":   cells[3].get_text(strip=True),
            "alle":   cells[4].get_text(strip=True),
            "data":   cells[5].get_text(strip=True) if len(cells) > 5 else "",
        })

    logger.info("Trovate %d corse soppresse (linea=%s)", len(results), linea)
    return results


def linea_matches(row_linea: str, target: str) -> bool:
    """Verifica se il primo token di row_linea corrisponde a target.

    "8 Forlì" → target "8"  → True
    "S1 Forlì" → target "s1" → True
    "80 Forlì" → target "8"  → False
    """
    parts = row_linea.strip().split()
    return bool(parts) and parts[0].upper() == target.strip().upper()


def format_routes(routes: list[dict]) -> str:
    """Formatta le corse soppresse in un messaggio HTML per Telegram."""
    if not routes:
        return "✅ Nessuna corsa soppressa trovata per la tua linea oggi."

    lines = ["🚍 <b>Corse non garantite oggi:</b>\n"]
    for r in routes:
        lines.append(
            f"❌ <b>Linea {r['linea']}</b>\n"
            f"   Da: {r['inizio']} → {r['fine']}\n"
            f"   Orario: {r['dalle']} — {r['alle']}\n"
        )
    return "\n".join(lines)


# ── Funzioni interne ────────────────────────────────────────────────────────


def _find_data_table(soup: BeautifulSoup):
    """Trova la tabella dati ignorando quella dei filtri."""
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 5 and not _is_filter_row(cells):
                return table
    return None


def _is_filter_row(cells) -> bool:
    """True se la riga contiene campi <input> (riga dei filtri)."""
    return any(cell.find("input") for cell in cells)
