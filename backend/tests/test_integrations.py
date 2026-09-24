"""Tests de integración con PMS (conectar + sincronizar la cartera)."""
import pytest

from tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_list_shows_demo_available(client):
    headers = await register_and_login(client, email="int1@test.com")
    providers = (await client.get("/integrations", headers=headers)).json()
    demo = next(p for p in providers if p["id"] == "demo")
    assert demo["available"] is True and demo["connected"] is False
    assert any(p["id"] == "guesty" and p["available"] is False for p in providers)


@pytest.mark.asyncio
async def test_connect_and_sync_portfolio(client):
    headers = await register_and_login(client, email="int2@test.com")

    # No se puede sincronizar sin conectar.
    assert (await client.post("/integrations/demo/sync", headers=headers)).status_code == 400
    # Un proveedor no disponible no se conecta.
    assert (await client.post("/integrations/guesty/connect", headers=headers)).status_code == 400

    # Conectar el demo y sincronizar.
    assert (await client.post("/integrations/demo/connect", headers=headers)).status_code == 200
    resp = await client.post("/integrations/demo/sync", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"properties_imported": 2, "reservations_imported": 3}

    # Los pisos y reservas están en la cuenta.
    assert len((await client.get("/properties", headers=headers)).json()) == 2
    assert len((await client.get("/reservations", headers=headers)).json()) == 3

    # Resincronizar no duplica (idempotente).
    resp = await client.post("/integrations/demo/sync", headers=headers)
    assert resp.json() == {"properties_imported": 0, "reservations_imported": 0}


@pytest.mark.asyncio
async def test_member_cannot_connect(client):
    owner = await register_and_login(client, email="int3@test.com")
    await client.post(
        "/org/members",
        json={"email": "m@test.com", "name": "M", "password": "member123"},
        headers=owner,
    )
    login = await client.post("/auth/login", json={"email": "m@test.com", "password": "member123"})
    member = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert (await client.post("/integrations/demo/connect", headers=member)).status_code == 403
