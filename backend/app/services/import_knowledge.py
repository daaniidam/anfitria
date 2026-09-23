"""Importación de conocimiento desde ficheros (CSV / PDF).

Un gestor con muchos pisos no teclea la ficha a mano: sube un CSV (categoría,
contenido) o el PDF del manual del piso y se trocea en fragmentos de conocimiento.
Cada fragmento se indexa con su embedding para el RAG, igual que si se hubiera
escrito en el panel.
"""
from __future__ import annotations

import csv
import io

# Topes defensivos: evitan importaciones gigantes (coste de embeddings/almacenamiento).
MAX_ITEMS = 200
MAX_CONTENT = 4000
MIN_CHUNK = 25
MAX_CHUNK = 700


def parse_csv(data: bytes) -> list[tuple[str, str]]:
    """Devuelve [(categoría, contenido)]. Acepta 1 columna (contenido) o 2 (categoría, contenido).

    Ignora una posible fila de cabecera (category/categoría, content/contenido).
    """
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    items: list[tuple[str, str]] = []
    for i, row in enumerate(reader):
        cells = [c.strip() for c in row if c is not None]
        cells = [c for c in cells if c != ""]
        if not cells:
            continue
        if len(cells) >= 2:
            category, content = cells[0], cells[1]
        else:
            category, content = "general", cells[0]
        # Saltar cabecera típica.
        if i == 0 and category.lower() in {"category", "categoría", "categoria"}:
            continue
        content = content[:MAX_CONTENT].strip()
        if content:
            items.append((category[:64] or "general", content))
        if len(items) >= MAX_ITEMS:
            break
    return items


def chunk_text(text: str) -> list[str]:
    """Trocea texto plano (p. ej. de un PDF) en fragmentos de conocimiento.

    Divide por líneas en blanco; une líneas cortas; parte los bloques muy largos.
    """
    blocks = [b.strip() for b in text.replace("\r\n", "\n").split("\n\n")]
    chunks: list[str] = []
    for block in blocks:
        block = " ".join(block.split())  # normaliza espacios
        if len(block) < MIN_CHUNK:
            continue
        while len(block) > MAX_CHUNK:
            cut = block.rfind(" ", 0, MAX_CHUNK)
            cut = cut if cut > MIN_CHUNK else MAX_CHUNK
            chunks.append(block[:cut].strip())
            block = block[cut:].strip()
            if len(chunks) >= MAX_ITEMS:
                return chunks[:MAX_ITEMS]
        if len(block) >= MIN_CHUNK:
            chunks.append(block[:MAX_CONTENT])
        if len(chunks) >= MAX_ITEMS:
            break
    return chunks[:MAX_ITEMS]


def extract_pdf_text(data: bytes) -> str:
    """Extrae el texto de un PDF. Lazy import para no cargar pypdf si no hace falta."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def parse_upload(filename: str, content_type: str | None, data: bytes) -> list[tuple[str, str]]:
    """Enruta por tipo de fichero y devuelve [(categoría, contenido)] listo para indexar."""
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    if name.endswith(".csv") or "csv" in ctype:
        return parse_csv(data)
    if name.endswith(".pdf") or "pdf" in ctype:
        return [("general", chunk) for chunk in chunk_text(extract_pdf_text(data))]
    raise ValueError("Formato no soportado: usa CSV o PDF")
