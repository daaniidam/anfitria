"""Tests de organización, roles y aislamiento entre cuentas."""
import pytest

from tests.conftest import register_and_login


async def _login(client, email: str, password: str = "member123") -> dict:
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.asyncio
async def test_org_isolation_between_accounts(client):
    a = await register_and_login(client, email="a@test.com")
    pid = (await client.post("/properties", json={"name": "Piso A"}, headers=a)).json()["id"]

    b = await register_and_login(client, email="b@test.com")
    # B no ve los pisos de A y no puede acceder a su ficha.
    assert (await client.get("/properties", headers=b)).json() == []
    assert (await client.get(f"/properties/{pid}/knowledge", headers=b)).status_code == 404


@pytest.mark.asyncio
async def test_member_operates_but_cannot_delete_or_invite(client):
    owner = await register_and_login(client, email="owner@test.com")
    pid = (await client.post("/properties", json={"name": "Piso"}, headers=owner)).json()["id"]

    # El owner invita a un miembro.
    resp = await client.post(
        "/org/members",
        json={"email": "member@test.com", "name": "Empleado", "password": "member123",
              "role": "member"},
        headers=owner,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["role"] == "member"

    member = await _login(client, "member@test.com")
    # El miembro ve los pisos de la org y puede operar (añadir conocimiento).
    assert len((await client.get("/properties", headers=member)).json()) == 1
    add = await client.post(
        f"/properties/{pid}/knowledge",
        json={"category": "wifi", "content": "Clave WIFI-1"},
        headers=member,
    )
    assert add.status_code == 201
    # Pero no puede borrar pisos ni invitar (solo el owner).
    assert (await client.delete(f"/properties/{pid}", headers=member)).status_code == 403
    invite = await client.post(
        "/org/members",
        json={"email": "x@test.com", "name": "X", "password": "member123"},
        headers=member,
    )
    assert invite.status_code == 403

    # El owner sí puede borrar.
    assert (await client.delete(f"/properties/{pid}", headers=owner)).status_code == 204


@pytest.mark.asyncio
async def test_members_list_and_role_change(client):
    owner = await register_and_login(client, email="team@test.com")
    await client.post(
        "/org/members",
        json={"email": "m2@test.com", "name": "M2", "password": "member123"},
        headers=owner,
    )
    members = (await client.get("/org/members", headers=owner)).json()
    assert len(members) == 2
    roles = {m["email"]: m["role"] for m in members}
    assert roles["team@test.com"] == "owner"
    assert roles["m2@test.com"] == "member"

    # No se puede dejar la org sin ningún propietario.
    owner_id = next(m["id"] for m in members if m["role"] == "owner")
    resp = await client.patch(
        f"/org/members/{owner_id}", json={"role": "member"}, headers=owner
    )
    assert resp.status_code == 400
