"""Test del asistente de conexión de WhatsApp Business (conectar → plantillas → asignar)."""
import pytest

from tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_whatsapp_setup_flow(client):
    headers = await register_and_login(client, email="wa@test.com")
    pid = (await client.post("/properties", json={"name": "Piso"}, headers=headers)).json()["id"]

    st = (await client.get("/integrations/whatsapp", headers=headers)).json()
    assert st["connected"] is False and st["total_pisos"] == 1

    # No se puede asignar sin conectar.
    assert (
        await client.post("/integrations/whatsapp/assign", json={"property_id": pid}, headers=headers)
    ).status_code == 400

    # Conectar el número.
    resp = await client.post(
        "/integrations/whatsapp/connect",
        json={"business_name": "Mi Alojamiento", "phone": "+34600112233"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["connected"] is True
    assert resp.json()["phone"] == "+34600112233"

    # Sin plantillas aprobadas no se asigna.
    assert (
        await client.post("/integrations/whatsapp/assign", json={"property_id": pid}, headers=headers)
    ).status_code == 400

    # Aprobar plantillas y asignar a un piso.
    assert (await client.post("/integrations/whatsapp/templates", headers=headers)).json()[
        "templates_approved"
    ] is True
    st = (
        await client.post("/integrations/whatsapp/assign", json={"property_id": pid}, headers=headers)
    ).json()
    assert st["pisos_assigned"] == 1


@pytest.mark.asyncio
async def test_member_cannot_connect_whatsapp(client):
    owner = await register_and_login(client, email="waowner@test.com")
    await client.post(
        "/org/members",
        json={"email": "wam@test.com", "name": "M", "password": "member123"},
        headers=owner,
    )
    login = await client.post("/auth/login", json={"email": "wam@test.com", "password": "member123"})
    member = {"Authorization": f"Bearer {login.json()['access_token']}"}
    resp = await client.post(
        "/integrations/whatsapp/connect",
        json={"business_name": "X", "phone": "+34600000000"},
        headers=member,
    )
    assert resp.status_code == 403
