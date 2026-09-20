"""Tests del endpoint de métricas."""
from tests.conftest import register_and_login


async def test_metrics_aggregate(client):
    headers = await register_and_login(client, email="metrics@test.com")
    resp = await client.post(
        "/properties", json={"name": "Piso Métricas", "default_language": "es"}, headers=headers
    )
    prop_id = resp.json()["id"]
    await client.post(
        f"/properties/{prop_id}/knowledge",
        json={"category": "wifi", "content": "La contraseña del wifi es METRIC-1."},
        headers=headers,
    )

    # respondida sola (coincide con el wifi)
    await client.post(
        "/channels/sim/inbound",
        json={"property_id": prop_id, "guest_ref": "g1", "text": "contraseña del wifi?"},
        headers=headers,
    )
    # escalada (no lo sabe)
    await client.post(
        "/channels/sim/inbound",
        json={"property_id": prop_id, "guest_ref": "g2", "text": "¿hay piscina climatizada?"},
        headers=headers,
    )

    m = (await client.get("/metrics", headers=headers)).json()
    assert m["properties"] == 1
    assert m["conversations"] == 2
    assert m["auto_answered"] >= 1
    assert m["escalated"] >= 1
    assert m["pending"] >= 1
    assert 0.0 < m["auto_rate"] <= 1.0
    assert m["minutes_saved"] >= 3


async def test_metrics_empty(client):
    headers = await register_and_login(client, email="empty@test.com")
    m = (await client.get("/metrics", headers=headers)).json()
    assert m["properties"] == 0
    assert m["auto_rate"] == 0.0
    assert m["minutes_saved"] == 0
