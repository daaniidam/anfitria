"""Tests de reservas (contexto de estancia para la IA) y detección de idiomas."""
from datetime import date, timedelta

import pytest

from app.adapters.ai.mock import detect_language
from app.services.reservations import stay_phase
from tests.conftest import register_and_login


def test_stay_phase():
    ci, co = date(2026, 6, 10), date(2026, 6, 14)
    assert stay_phase(ci, co, today=date(2026, 6, 8)) == "pre_llegada"
    assert stay_phase(ci, co, today=date(2026, 6, 12)) == "durante"
    assert stay_phase(ci, co, today=date(2026, 6, 20)) == "pasada"


def test_detect_language_multi():
    assert detect_language("Bonjour, quelle heure est le check-in ?") == "fr"
    assert detect_language("Hallo, wann ist die Ankunft?") == "de"
    assert detect_language("Ciao, a che ora è il check-in?") == "it"
    assert detect_language("Hola, ¿a qué hora es la entrada?") == "es"
    assert detect_language("Hi, what time is check-in please?") == "en"


@pytest.mark.asyncio
async def test_reservation_crud(client):
    headers = await register_and_login(client, email="res@test.com")
    pid = (await client.post("/properties", json={"name": "Piso"}, headers=headers)).json()["id"]
    ci = date.today() + timedelta(days=2)
    co = ci + timedelta(days=3)
    resp = await client.post(
        f"/properties/{pid}/reservations",
        json={
            "guest_name": "Ana López",
            "guest_ref": "+34600",
            "check_in": ci.isoformat(),
            "check_out": co.isoformat(),
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    rid = resp.json()["id"]

    listed = (await client.get(f"/properties/{pid}/reservations", headers=headers)).json()
    assert len(listed) == 1

    # Cancelar (PATCH status) y borrar.
    resp = await client.patch(
        f"/reservations/{rid}", json={"status": "cancelled"}, headers=headers
    )
    assert resp.json()["status"] == "cancelled"
    assert (await client.delete(f"/reservations/{rid}", headers=headers)).status_code == 204


@pytest.mark.asyncio
async def test_reservation_gives_ai_context(client):
    headers = await register_and_login(client, email="ctx@test.com")
    pid = (
        await client.post(
            "/properties", json={"name": "Piso", "auto_answer": True}, headers=headers
        )
    ).json()["id"]
    ci = date.today() + timedelta(days=1)
    co = ci + timedelta(days=2)
    await client.post(
        f"/properties/{pid}/reservations",
        json={
            "guest_name": "Ana López",
            "guest_ref": "+34600",
            "check_in": ci.isoformat(),
            "check_out": co.isoformat(),
        },
        headers=headers,
    )
    # Sin conocimiento, pero con reserva: la IA (mock) responde con el contexto de la estancia.
    resp = await client.post(
        "/channels/sim/inbound",
        json={"property_id": pid, "guest_ref": "+34600", "text": "hola, alguna info?"},
        headers=headers,
    )
    body = resp.json()
    assert body["answered"] is True
    assert "Ana López" in body["draft"]["text"]
    assert "check-in" in body["draft"]["text"].lower()
