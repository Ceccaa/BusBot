"""Formattazione dei messaggi Telegram per BusBot v2.0."""

import logging

logger = logging.getLogger(__name__)


# ── Bollettino multi-linea (soppressioni periodiche) ─────────────────────────


def format_multiline_bulletin(linee_status: dict[str, list[dict]]) -> str:
    """Genera il bollettino soppressioni per più linee.

    Args:
        linee_status: {"8": [...routes], "92": [], "1A": [...]}

    Returns:
        Testo HTML Telegram.
    """
    if not linee_status:
        return "⚠️ Nessuna linea configurata. Usa /start."

    lines = ["📊 <b>Situazione Attuale:</b>\n"]
    for linea, routes in sorted(linee_status.items()):
        if routes:
            lines.append(f"🚆 Linea <b>{linea}</b>: ❌ {len(routes)} corsa/e non garantita/e")
            for r in routes:
                lines.append(
                    f"   • Da: {r['inizio']} → {r['fine']} "
                    f"| {r['dalle']} — {r['alle']}"
                )
        else:
            lines.append(f"🚆 Linea <b>{linea}</b>: ✅ Nessuna corsa soppressa")

    return "\n".join(lines)


# ── Bollettino programmato (alarm digest) ────────────────────────────────────


def format_alarm_bulletin(orario: str, linee_status: dict[str, list[dict]]) -> str:
    """Genera il bollettino per la sveglia del pendolare.

    Inviato sempre, anche se tutto è regolare.
    """
    lines = [f"⏰ <b>Bollettino delle {orario}</b>\n"]

    for linea, routes in sorted(linee_status.items()):
        if routes:
            lines.append(f"🚆 Linea <b>{linea}</b>: ❌ {len(routes)} corsa/e non garantita/e")
            for r in routes:
                lines.append(
                    f"   • Da: {r['inizio']} → {r['fine']} "
                    f"| {r['dalle']} — {r['alle']}"
                )
        else:
            lines.append(f"🚆 Linea <b>{linea}</b>: ✅ Tutto regolare")

    lines.append("\nBuona fortuna 🍀")
    return "\n".join(lines)


# ── Alert real-time (nuova soppressione) ─────────────────────────────────────


def format_realtime_alert(linea: str, routes: list[dict]) -> str:
    """Notifica immediata per nuova soppressione."""
    lines = [
        f"⚠️ <b>NUOVA CORSA SOPPRESSA</b>\n",
        f"🚆 Linea <b>{linea}</b>",
    ]

    for r in routes:
        lines.append(
            f"   {r['dalle']} — {r['alle']} "
            f"| {r['inizio']} → {r['fine']}"
        )

    lines.append("\n🤬 Il bus ti ha mollato a piedi?")

    return "\n".join(lines)
