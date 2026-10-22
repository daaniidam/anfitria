"""Tests del RAG visible: las citas (fragmentos que anclaron la respuesta)."""
from tests.conftest import register_and_login


async def _prop_with_wifi(client, headers):
    pid = (
        await client.post(
            "/properties", json={"name": "Piso", "default_language": "es"}, headers=headers
        )
    ).json()["id"]
    await client.post(
        f"/properties/{pid}/knowledge",
        json={"category": "wifi", "content": "La contraseña del wifi es CASA-1234."},
        headers=headers,
    )
    return pid


async def test_answer_includes_citations_with_score(client):
    headers = await register_and_login(client, email="cit@test.com")
    pid = await _prop_with_wifi(client, headers)

    resp = await client.post(
        "/channels/sim/inbound",
        json={"property_id": pid, "guest_ref": "g1", "text": "¿cuál es la contraseña del wifi?"},
        headers=headers,
    )
    draft = resp.json()["draft"]
    assert resp.json()["answered"] is True
    assert len(draft["citations"]) >= 1
    cite = draft["citations"][0]
    assert cite["category"] == "wifi"
    assert "CASA-1234" in cite["content"]
    assert 0.0 < cite["score"] <= 1.0


async def test_escalation_without_knowledge_has_no_citations(client):
    headers = await register_and_login(client, email="cit2@test.com")
    pid = (
        await client.post(
            "/properties", json={"name": "Piso", "default_language": "es"}, headers=headers
        )
    ).json()["id"]
    resp = await client.post(
        "/channels/sim/inbound",
        json={"property_id": pid, "guest_ref": "g1", "text": "¿hay piscina?"},
        headers=headers,
    )
    assert resp.json()["answered"] is False
    assert resp.json()["draft"]["citations"] == []


async def test_citation_snapshot_survives_knowledge_deletion(client):
    """La cita guarda un snapshot: si luego se borra el conocimiento, no desaparece."""
    headers = await register_and_login(client, email="cit3@test.com")
    pid = await _prop_with_wifi(client, headers)
    item_id = (await client.get(f"/properties/{pid}/knowledge", headers=headers)).json()[0]["id"]

    await client.post(
        "/channels/sim/inbound",
        json={"property_id": pid, "guest_ref": "g1", "text": "¿contraseña del wifi?"},
        headers=headers,
    )
    # se borra el conocimiento de origen
    del_resp = await client.delete(f"/properties/{pid}/knowledge/{item_id}", headers=headers)
    assert del_resp.status_code == 204

    # el wifi se auto-respondió, así que no está en /inbox; se consulta vía /drafts
    drafts = (await client.get("/drafts?status=sent", headers=headers)).json()
    with_cites = [d for d in drafts if d["citations"]]
    assert with_cites, "la cita debe sobrevivir al borrado del conocimiento"
    assert "CASA-1234" in with_cites[0]["citations"][0]["content"]
