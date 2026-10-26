"""Tests del aprendizaje (guardar respuestas) y del edificio compartido."""
from tests.conftest import register_and_login


async def test_host_answer_can_be_learned(client):
    headers = await register_and_login(client, email="learn@test.com")
    prop_id = (
        await client.post("/properties", json={"name": "Piso", "default_language": "es"}, headers=headers)
    ).json()["id"]

    # sin conocimiento sobre mascotas -> escala
    resp = await client.post(
        "/channels/sim/inbound",
        json={"property_id": prop_id, "guest_ref": "g1", "text": "¿se admiten mascotas?"},
        headers=headers,
    )
    body = resp.json()
    assert body["answered"] is False
    draft_id = body["draft"]["id"]

    # el anfitrión responde y guarda en la ficha
    resp = await client.post(
        f"/drafts/{draft_id}/approve",
        json={"edited_text": "Sí, se admiten mascotas pequeñas.", "save_to_knowledge": True},
        headers=headers,
    )
    assert resp.status_code == 201

    # la misma pregunta ahora se responde sola (aprendida)
    resp2 = await client.post(
        "/channels/sim/inbound",
        json={"property_id": prop_id, "guest_ref": "g2", "text": "¿se admiten mascotas?"},
        headers=headers,
    )
    body2 = resp2.json()
    assert body2["answered"] is True
    assert "mascotas" in body2["draft"]["text"].lower()


async def test_not_saving_does_not_learn(client):
    headers = await register_and_login(client, email="nolearn@test.com")
    prop_id = (
        await client.post("/properties", json={"name": "Piso", "default_language": "es"}, headers=headers)
    ).json()["id"]
    resp = await client.post(
        "/channels/sim/inbound",
        json={"property_id": prop_id, "guest_ref": "g1", "text": "¿se admiten mascotas?"},
        headers=headers,
    )
    draft_id = resp.json()["draft"]["id"]
    # responde SIN guardar
    await client.post(
        f"/drafts/{draft_id}/approve",
        json={"edited_text": "Sí, se admiten.", "save_to_knowledge": False},
        headers=headers,
    )
    # vuelve a escalar
    resp2 = await client.post(
        "/channels/sim/inbound",
        json={"property_id": prop_id, "guest_ref": "g2", "text": "¿se admiten mascotas?"},
        headers=headers,
    )
    assert resp2.json()["answered"] is False


async def test_holding_message_is_not_learned(client):
    """Si el anfitrión aprueba sin editar un borrador de espera, NO se aprende:
    los mensajes de 'lo confirmo y te respondo' no son respuestas útiles."""
    headers = await register_and_login(client, email="holding@test.com")
    prop_id = (
        await client.post("/properties", json={"name": "Piso", "default_language": "es"}, headers=headers)
    ).json()["id"]

    # sin conocimiento -> escala; el borrador trae el mensaje de espera
    resp = await client.post(
        "/channels/sim/inbound",
        json={"property_id": prop_id, "guest_ref": "g1", "text": "¿se admiten mascotas?"},
        headers=headers,
    )
    body = resp.json()
    assert body["answered"] is False
    draft_id = body["draft"]["id"]

    # aprueba SIN editar (acepta el mensaje de espera) pero marcando guardar
    resp = await client.post(
        f"/drafts/{draft_id}/approve",
        json={"save_to_knowledge": True},
        headers=headers,
    )
    assert resp.status_code == 201

    # la misma pregunta sigue escalando: no se aprendió el mensaje de espera
    resp2 = await client.post(
        "/channels/sim/inbound",
        json={"property_id": prop_id, "guest_ref": "g2", "text": "¿se admiten mascotas?"},
        headers=headers,
    )
    assert resp2.json()["answered"] is False


async def test_learned_knowledge_keeps_the_question(client):
    """Una respuesta corta se guarda junto a la pregunta, para que siga teniendo sentido."""
    headers = await register_and_login(client, email="qa@test.com")
    prop_id = (
        await client.post("/properties", json={"name": "Piso", "default_language": "es"}, headers=headers)
    ).json()["id"]
    resp = await client.post(
        "/channels/sim/inbound",
        json={"property_id": prop_id, "guest_ref": "g1", "text": "¿qué día es el check-in?"},
        headers=headers,
    )
    draft_id = resp.json()["draft"]["id"]
    await client.post(
        f"/drafts/{draft_id}/approve",
        json={"edited_text": "el 26", "save_to_knowledge": True},
        headers=headers,
    )
    items = (await client.get(f"/properties/{prop_id}/knowledge", headers=headers)).json()
    learned = [it for it in items if it["category"] == "aprendido"]
    assert len(learned) == 1
    # la ficha guarda pregunta + respuesta, no solo "el 26"
    assert "check-in" in learned[0]["content"].lower()
    assert "el 26" in learned[0]["content"].lower()


async def test_auto_answer_threshold_out_of_range_is_rejected(client):
    """Un umbral inalcanzable (p. ej. 0.99 > confianza máxima del mock) se rechaza."""
    headers = await register_and_login(client, email="thr@test.com")
    resp = await client.post(
        "/properties",
        json={"name": "Piso", "default_language": "es", "auto_answer_threshold": 0.99},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_building_knowledge_is_shared_with_its_properties(client):
    headers = await register_and_login(client, email="bld@test.com")
    building_id = (
        await client.post("/buildings", json={"name": "Edificio Centro"}, headers=headers)
    ).json()["id"]
    await client.post(
        f"/buildings/{building_id}/knowledge",
        json={"category": "cómo llegar", "content": "El portal del edificio tiene código 2580."},
        headers=headers,
    )

    # piso dentro del edificio, sin conocimiento propio del tema
    prop = await client.post(
        "/properties",
        json={"name": "3ºA", "default_language": "es", "building_id": building_id},
        headers=headers,
    )
    assert prop.json()["building_id"] == building_id
    prop_id = prop.json()["id"]

    resp = await client.post(
        "/channels/sim/inbound",
        json={"property_id": prop_id, "guest_ref": "g", "text": "¿cuál es el código del portal?"},
        headers=headers,
    )
    assert "2580" in resp.json()["draft"]["text"]  # respondió con conocimiento del edificio


async def test_cannot_use_another_users_building(client):
    a = await register_and_login(client, email="a@test.com")
    building_id = (await client.post("/buildings", json={"name": "Mío"}, headers=a)).json()["id"]
    b = await register_and_login(client, email="b@test.com")
    resp = await client.post(
        "/properties",
        json={"name": "Intruso", "default_language": "es", "building_id": building_id},
        headers=b,
    )
    assert resp.status_code == 404
