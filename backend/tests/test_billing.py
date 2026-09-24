"""Tests de facturación: planes, uso y límite de pisos (paywall)."""
import pytest

from tests.conftest import register_and_login


async def _add_property(client, headers, name="Piso"):
    return await client.post("/properties", json={"name": name}, headers=headers)


@pytest.mark.asyncio
async def test_plan_limit_and_upgrade(client):
    headers = await register_and_login(client, email="bill@test.com")

    st = (await client.get("/billing", headers=headers)).json()
    assert st["plan"] == "free" and st["max_properties"] == 3 and st["properties_used"] == 0

    # Hasta el límite del plan Prueba (3).
    for i in range(3):
        assert (await _add_property(client, headers, f"Piso {i}")).status_code == 201
    # El cuarto choca con el paywall.
    resp = await _add_property(client, headers, "Piso 4")
    assert resp.status_code == 402

    # Subir a Starter (pago simulado) y ahora sí entra.
    up = await client.post("/billing/plan", json={"plan": "starter"}, headers=headers)
    assert up.status_code == 200 and up.json()["plan"] == "starter"
    assert (await _add_property(client, headers, "Piso 4")).status_code == 201

    # No se puede bajar a un plan que no cubre los pisos actuales (4 > 3).
    down = await client.post("/billing/plan", json={"plan": "free"}, headers=headers)
    assert down.status_code == 400


@pytest.mark.asyncio
async def test_member_cannot_change_plan(client):
    owner = await register_and_login(client, email="billowner@test.com")
    await client.post(
        "/org/members",
        json={"email": "billm@test.com", "name": "M", "password": "member123"},
        headers=owner,
    )
    login = await client.post("/auth/login", json={"email": "billm@test.com", "password": "member123"})
    member = {"Authorization": f"Bearer {login.json()['access_token']}"}
    resp = await client.post("/billing/plan", json={"plan": "pro"}, headers=member)
    assert resp.status_code == 403
