"""Test del handoff en vivo: el anfitrión toma el control, responde, y devuelve a la IA."""
import pytest

from tests.conftest import register_and_login


async def _inbound(client, headers, pid, text, guest="+34600"):
    return await client.post(
        "/channels/sim/inbound",
        json={"property_id": pid, "guest_ref": guest, "text": text},
        headers=headers,
    )


@pytest.mark.asyncio
async def test_live_handoff_flow(client):
    headers = await register_and_login(client, email="handoff@test.com")
    pid = (
        await client.post("/properties", json={"name": "Piso", "auto_answer": True}, headers=headers)
    ).json()["id"]
    await client.post(
        f"/properties/{pid}/knowledge",
        json={"category": "wifi", "content": "La contraseña del wifi es CASA-1234"},
        headers=headers,
    )

    # 1) La IA responde sola.
    r = await _inbound(client, headers, pid, "cual es la contraseña del wifi?")
    body = r.json()
    assert body["answered"] is True
    conv_id = body["conversation"]["id"]

    # 2) El anfitrión toma el control.
    tk = await client.post(f"/conversations/{conv_id}/takeover", headers=headers)
    assert tk.status_code == 200
    assert tk.json()["handoff"] is True

    # 3) Nuevo mensaje del huésped: la IA se aparta (no responde, sin borrador).
    r = await _inbound(client, headers, pid, "otra duda mas")
    body = r.json()
    assert body["answered"] is False
    assert body["draft"] is None

    # 4) El anfitrión responde en vivo.
    reply = await client.post(
        f"/conversations/{conv_id}/reply", json={"text": "¡Claro! te ayudo ahora mismo."},
        headers=headers,
    )
    assert reply.status_code == 201
    assert reply.json()["direction"] == "out"

    # 5) Devuelve el control a la IA: vuelve a responder sola.
    rel = await client.post(f"/conversations/{conv_id}/release", headers=headers)
    assert rel.json()["handoff"] is False
    r = await _inbound(client, headers, pid, "y la contraseña del wifi?")
    assert r.json()["answered"] is True
