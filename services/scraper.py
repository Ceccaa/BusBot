"""Scraper per le corse non garantite di Start Romagna.

Logica invariata rispetto a v1. Spostato in services/ per la nuova struttura.
Aggiunto retry HTTP (max 3 tentativi, backoff esponenziale).
"""

import logging
import asyncio
from datetime import date

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://servizi.startromagna.it/corsesoppresse/corsesopp"
TIMEOUT = 20
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # secondi


# ── Funzioni pubbliche ──────────────────────────────────────────────────────


async def get_cancelled_routes(bacino: str, linea: str | None = None) -> list[dict]:
    """Scarica le corse soppresse dal sito Start Romagna (asincrono).

    Args:
        bacino: "Forli-Cesena", "Rimini" o "Ravenna".
        linea:  Numero della linea (es. "3", "92"). None = tutte.

    Returns:
        Lista di dict con: linea, inizio, dalle, fine, alle, data.
    """
    params = {"param1": bacino, "param2": date.today().isoformat()}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            timeout_ctrl = aiohttp.ClientTimeout(total=TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout_ctrl) as session:
                async with session.get(BASE_URL, params=params) as response:
                    response.raise_for_status()
                    html_text = await response.text()
                    return parse_html(html_text, linea)
        except Exception as exc:
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF ** attempt
                logger.warning(
                    "Tentativo %d/%d fallito per %s: %s — retry in %ds",
                    attempt, MAX_RETRIES, bacino, exc, wait,
                )
                await asyncio.sleep(wait)
            else:
                logger.error("Errore HTTP definitivo per %s: %s", bacino, exc)
                return []


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


# ── Funzioni interne ────────────────────────────────────────────────────────


def _find_data_table(soup: BeautifulSoup):
    """Trova la tabella dati ignorando quella dei filtri.

    Strategia: la prima tabella con una riga di almeno 5 <td> non-filtro
    è la tabella dati.
    """
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            data_cells = row.find_all("td")
            if len(data_cells) >= 5 and not _is_filter_row(data_cells):
                return table
    return None


def _is_filter_row(cells) -> bool:
    """True se la riga contiene campi <input> (riga dei filtri)."""
    return any(cell.find("input") for cell in cells)
