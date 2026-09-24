"""Test del estado de arranque (onboarding): los pasos se marcan con datos reales."""
import pytest

from tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_onboarding_progresses_with_real_data(client):
    headers = await register_and_login(client, email="onb@test.com")

    st = (await client.get("/onboarding", headers=headers)).json()
    assert st == {
        "has_property": False,
        "has_knowledge": False,
        "has_whatsapp": False,
        "has_conversation": False,
    }

    pid = (
        await client.post(
            "/properties",
            json={"name": "Piso", "auto_answer": True, "whatsapp_phone_number_id": "PN1"},
            headers=headers,
        )
    ).json()["id"]
    st = (await client.get("/onboarding", headers=headers)).json()
    assert st["has_property"] is True
    assert st["has_whatsapp"] is True
    assert st["has_knowledge"] is False
    assert st["has_conversation"] is False

    await client.post(
        f"/properties/{pid}/knowledge",
        json={"category": "wifi", "content": "La clave es CASA-1234"},
        headers=headers,
    )
    await client.post(
        "/channels/sim/inbound",
        json={"property_id": pid, "guest_ref": "+34600", "text": "hola"},
        headers=headers,
    )
    st = (await client.get("/onboarding", headers=headers)).json()
    assert st == {
        "has_property": True,
        "has_knowledge": True,
        "has_whatsapp": True,
        "has_conversation": True,
    }
