"""Tests de importación de conocimiento (CSV/PDF)."""
import pytest

from app.services.import_knowledge import chunk_text, parse_csv
from tests.conftest import register_and_login


def test_parse_csv_two_columns_and_header():
    data = b"categoria,contenido\nwifi,La clave es CASA-1234\ncheck-in,Entrada a las 15:00\n"
    items = parse_csv(data)
    assert items == [("wifi", "La clave es CASA-1234"), ("check-in", "Entrada a las 15:00")]


def test_parse_csv_single_column():
    data = "El parking está en la planta -1\nSe admiten mascotas pequeñas\n".encode()
    items = parse_csv(data)
    assert [c for _, c in items] == ["El parking está en la planta -1", "Se admiten mascotas pequeñas"]
    assert all(cat == "general" for cat, _ in items)


def test_chunk_text_splits_and_filters():
    text = "Bienvenido al piso. El wifi es CASA-1234.\n\nx\n\n" + ("palabra " * 200)
    chunks = chunk_text(text)
    assert any("CASA-1234" in c for c in chunks)
    assert all(len(c) <= 700 for c in chunks)  # bloque largo troceado
    assert "x" not in chunks  # descarta lo demasiado corto


@pytest.mark.asyncio
async def test_import_csv_endpoint(client):
    headers = await register_and_login(client, email="import@test.com")
    pid = (
        await client.post("/properties", json={"name": "Piso"}, headers=headers)
    ).json()["id"]

    csv_bytes = b"categoria,contenido\nwifi,La clave del wifi es SOL-99\nnormas,No se puede fumar\n"
    resp = await client.post(
        f"/properties/{pid}/knowledge/import",
        files={"file": ("ficha.csv", csv_bytes, "text/csv")},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["imported"] == 2

    items = (await client.get(f"/properties/{pid}/knowledge", headers=headers)).json()
    contents = {i["content"] for i in items}
    assert "La clave del wifi es SOL-99" in contents
    assert "No se puede fumar" in contents


@pytest.mark.asyncio
async def test_import_rejects_unknown_format(client):
    headers = await register_and_login(client, email="badfmt@test.com")
    pid = (await client.post("/properties", json={"name": "P"}, headers=headers)).json()["id"]
    resp = await client.post(
        f"/properties/{pid}/knowledge/import",
        files={"file": ("nota.txt", b"hola", "text/plain")},
        headers=headers,
    )
    assert resp.status_code == 400
