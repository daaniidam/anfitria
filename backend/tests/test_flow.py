"""Tests del flujo núcleo (Fase 2)."""
from tests.conftest import register_and_login


async def _create_property(client, headers, name="Piso Centro", lang="es") -> int:
    resp = await client.post(
        "/properties", json={"name": name, "default_language": lang}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_requires_auth(client):
    resp = await client.get("/auth/me")
    assert resp.status_code in (401, 403)


async def test_manual_approval_flow(client):
    headers = await register_and_login(client)

    prop_id = await _create_property(client, headers)  # sin conocimiento -> confianza baja

    resp = await client.post(
        "/channels/sim/inbound",
        json={"property_id": prop_id, "guest_ref": "+34600111222", "text": "Hola, tengo una duda"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["answered"] is False  # sin conocimiento -> se escala
    draft_id = body["draft"]["id"]
    conversation_id = body["conversation"]["id"]

    # aparece en la cola de pendientes
    resp = await client.get("/drafts?status=pending", headers=headers)
    assert any(d["id"] == draft_id for d in resp.json())

    # y en la bandeja enriquecida (/inbox) con el texto del huésped
    resp = await client.get("/inbox", headers=headers)
    inbox = resp.json()
    assert len(inbox) == 1
    assert inbox[0]["draft"]["id"] == draft_id
    assert inbox[0]["inbound_text"] == "Hola, tengo una duda"
    assert inbox[0]["property_name"] == "Piso Centro"

    # aprobar (con edición)
    resp = await client.post(
        f"/drafts/{draft_id}/approve",
        json={"edited_text": "¡Hola! Claro, dime en qué te ayudo."},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["direction"] == "out"

    # la conversación tiene: entrada + mensaje de espera + respuesta del anfitrión
    resp = await client.get(f"/conversations/{conversation_id}/messages", headers=headers)
    directions = [m["direction"] for m in resp.json()]
    assert directions == ["in", "out", "out"]

    # ya no está pendiente
    resp = await client.get("/drafts?status=pending", headers=headers)
    assert all(d["id"] != draft_id for d in resp.json())


async def test_auto_send_with_matching_knowledge(client):
    headers = await register_and_login(client, email="host2@test.com")
    prop_id = await _create_property(client, headers, name="Piso Playa")

    resp = await client.post(
        f"/properties/{prop_id}/knowledge",
        json={"category": "wifi", "content": "La contraseña del wifi es CASA1234."},
        headers=headers,
    )
    assert resp.status_code == 201

    resp = await client.post(
        "/channels/sim/inbound",
        json={
            "property_id": prop_id,
            "guest_ref": "+34600333444",
            "text": "¿Cuál es la contraseña del wifi?",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["answered"] is True  # con conocimiento relevante -> responde sola
    assert body["draft"]["status"] == "sent"

    conversation_id = body["conversation"]["id"]
    resp = await client.get(f"/conversations/{conversation_id}/messages", headers=headers)
    directions = [m["direction"] for m in resp.json()]
    assert directions == ["in", "out"]


async def test_language_detection_english(client):
    headers = await register_and_login(client, email="host3@test.com")
    prop_id = await _create_property(client, headers, name="City Flat")

    resp = await client.post(
        "/channels/sim/inbound",
        json={"property_id": prop_id, "guest_ref": "guest-en", "text": "What time is the check-in?"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["draft"]["language"] == "en"


async def test_rag_grounds_answer_in_relevant_knowledge(client):
    headers = await register_and_login(client, email="rag1@test.com")
    prop_id = await _create_property(client, headers, name="Loft Sol")
    await client.post(
        f"/properties/{prop_id}/knowledge",
        json={"category": "wifi", "content": "La contraseña del wifi es MALASANA-2024."},
        headers=headers,
    )
    await client.post(
        f"/properties/{prop_id}/knowledge",
        json={"category": "check-in", "content": "El check-in es a partir de las 15:00 con caja de llaves."},
        headers=headers,
    )

    resp = await client.post(
        "/channels/sim/inbound",
        json={"property_id": prop_id, "guest_ref": "g", "text": "¿Me pasas la contraseña del wifi?"},
        headers=headers,
    )
    draft = resp.json()["draft"]
    assert "MALASANA" in draft["text"]  # se ancló en el fragmento de wifi
    assert "15:00" not in draft["text"]  # no mezcló el de check-in


async def test_rag_ignores_irrelevant_question(client):
    headers = await register_and_login(client, email="rag2@test.com")
    prop_id = await _create_property(client, headers, name="Loft Luna")
    await client.post(
        f"/properties/{prop_id}/knowledge",
        json={"category": "wifi", "content": "La contraseña del wifi es MALASANA-2024."},
        headers=headers,
    )

    resp = await client.post(
        "/channels/sim/inbound",
        json={"property_id": prop_id, "guest_ref": "g", "text": "¿Hay algún parking o garaje por la zona?"},
        headers=headers,
    )
    body = resp.json()
    assert "MALASANA" not in body["draft"]["text"]  # no soltó el wifi sin venir a cuento
    assert body["answered"] is False  # no sabía -> escala en vez de inventar


async def test_property_with_auto_answer_off_always_escalates(client):
    headers = await register_and_login(client, email="manual@test.com")
    resp = await client.post(
        "/properties",
        json={"name": "Casa Manual", "default_language": "es", "auto_answer": False},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["auto_answer"] is False
    prop_id = resp.json()["id"]
    await client.post(
        f"/properties/{prop_id}/knowledge",
        json={"category": "wifi", "content": "La contraseña del wifi es MALASANA-2024."},
        headers=headers,
    )

    resp = await client.post(
        "/channels/sim/inbound",
        json={"property_id": prop_id, "guest_ref": "g", "text": "¿Cuál es la contraseña del wifi?"},
        headers=headers,
    )
    # aunque tenga la respuesta, este piso escala siempre
    assert resp.json()["answered"] is False


async def test_ownership_isolation(client):
    owner_headers = await register_and_login(client, email="owner@test.com")
    prop_id = await _create_property(client, owner_headers)

    intruder_headers = await register_and_login(client, email="intruder@test.com")
    resp = await client.post(
        f"/properties/{prop_id}/knowledge",
        json={"content": "no debería poder"},
        headers=intruder_headers,
    )
    assert resp.status_code == 404
