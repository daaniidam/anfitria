"""Importación de reservas desde un calendario iCal (.ics).

Es la forma en que los gestores conectan Booking.com y Airbnb: cada anuncio expone
una URL de calendario iCal; al importarla, las reservas entran con su origen (de
dónde vienen). Aquí parseamos el fichero .ics y deducimos el origen del PRODID.
"""
from __future__ import annotations

from datetime import date

MAX_EVENTS = 500


def detect_source(text: str) -> str:
    low = text.lower()
    if "booking.com" in low or "booking" in low:
        return "booking"
    if "airbnb" in low:
        return "airbnb"
    return "other"


def _unfold(data: str) -> list[str]:
    """Une las líneas plegadas del iCal (las que empiezan por espacio/tab continúan)."""
    lines: list[str] = []
    for raw in data.replace("\r\n", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _parse_date(value: str) -> date | None:
    digits = "".join(ch for ch in value if ch.isdigit())[:8]
    if len(digits) != 8:
        return None
    try:
        return date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))
    except ValueError:
        return None


def parse_ics(data: bytes) -> tuple[str, list[dict]]:
    """Devuelve (origen, [reservas]) con guest_name, check_in, check_out, code."""
    text = data.decode("utf-8-sig", errors="replace")
    source = detect_source(text)
    reservations: list[dict] = []
    current: dict | None = None
    for line in _unfold(text):
        if line.startswith("BEGIN:VEVENT"):
            current = {}
        elif line.startswith("END:VEVENT"):
            if current and current.get("check_in") and current.get("check_out"):
                reservations.append(current)
            current = None
        elif current is not None:
            key, _, value = line.partition(":")
            name = key.split(";")[0].upper()
            if name == "DTSTART":
                current["check_in"] = _parse_date(value)
            elif name == "DTEND":
                # En iCal el DTEND es exclusivo; el check-out es ese mismo día.
                current["check_out"] = _parse_date(value)
            elif name == "SUMMARY":
                current["guest_name"] = value.strip()[:160]
            elif name == "UID":
                current["code"] = value.strip()[:32]
        if len(reservations) >= MAX_EVENTS:
            break

    fallback = {"booking": "Reserva Booking", "airbnb": "Reserva Airbnb"}.get(
        source, "Reserva"
    )
    blocks = ("closed", "not available", "reserved", "blocked")
    for r in reservations:
        name = r.get("guest_name") or ""
        # Los bloqueos genéricos ("CLOSED", "Not available", "Reserved") no son nombres.
        if not name or any(w in name.lower() for w in blocks):
            r["guest_name"] = fallback
    return source, reservations
