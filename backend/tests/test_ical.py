"""Tests del origen de reservas, iCal (Booking/Airbnb), vista global y enlace."""
from datetime import date, timedelta

import pytest

from app.services.ical import detect_source, parse_ics
from tests.conftest import register_and_login

BOOKING_ICS = b"""BEGIN:VCALENDAR
PRODID:-//Booking.com//Calendar//EN
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260610
DTEND;VALUE=DATE:20260614
SUMMARY:CLOSED - Not available
UID:evt-1
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260620
DTEND;VALUE=DATE:20260622
SUMMARY:Ana Lopez
UID:evt-2
END:VEVENT
END:VCALENDAR
"""


def test_detect_source():
    assert detect_source("PRODID:-//Booking.com//EN") == "booking"
    assert detect_source("PRODID:-//Airbnb Inc//EN") == "airbnb"
    assert detect_source("PRODID:-//Otro//EN") == "other"


def test_parse_ics():
    source, events = parse_ics(BOOKING_ICS)
    assert source == "booking"
    assert len(events) == 2
    assert events[0]["check_in"] == date(2026, 6, 10)
    assert events[0]["guest_name"] == "Reserva Booking"  # bloqueo genérico → nombre por defecto
    assert events[1]["guest_name"] == "Ana Lopez"


@pytest.mark.asyncio
async def test_import_ics_and_global_view(client):
    headers = await register_and_login(client, email="ics@test.com")
    pid = (await client.post("/properties", json={"name": "Ático"}, headers=headers)).json()["id"]

    resp = await client.post(
        f"/properties/{pid}/reservations/import-ics",
        files={"file": ("booking.ics", BOOKING_ICS, "text/calendar")},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json() == {"imported": 2, "source": "booking"}

    # Vista global: todas las reservas con el nombre del piso y su origen.
    reservations = (await client.get("/reservations", headers=headers)).json()
    assert len(reservations) == 2
    assert all(r["source"] == "booking" for r in reservations)
    assert all(r["property_name"] == "Ático" for r in reservations)


@pytest.mark.asyncio
async def test_source_on_create_and_conversation_link(client):
    headers = await register_and_login(client, email="src@test.com")
    pid = (
        await client.post("/properties", json={"name": "Piso", "auto_answer": True}, headers=headers)
    ).json()["id"]
    ci = date.today() + timedelta(days=1)
    res = await client.post(
        f"/properties/{pid}/reservations",
        json={
            "guest_name": "Ana",
            "guest_ref": "+34600",
            "check_in": ci.isoformat(),
            "check_out": (ci + timedelta(days=2)).isoformat(),
            "source": "airbnb",
        },
        headers=headers,
    )
    rid = res.json()["id"]
    assert res.json()["source"] == "airbnb"

    # Al escribir el huésped, su conversación queda ligada a esa reserva.
    await client.post(
        "/channels/sim/inbound",
        json={"property_id": pid, "guest_ref": "+34600", "text": "hola"},
        headers=headers,
    )
    conv = (await client.get("/conversations", headers=headers)).json()[0]
    assert conv["reservation_id"] == rid
