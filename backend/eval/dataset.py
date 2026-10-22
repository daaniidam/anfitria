"""Dataset de evaluación del RAG de AnfitrIA.

Cada caso tiene la ficha de un piso y preguntas de huésped con lo que se espera:
- `expected_category`: el fragmento que DEBERÍA recuperar (None = debe escalar).
Muchas preguntas están **parafraseadas** a propósito (no comparten palabras con
la ficha) para distinguir una recuperación semántica real de la coincidencia
léxica (bolsa de palabras).
"""
from dataclasses import dataclass, field


@dataclass
class Case:
    question: str
    expected_category: str | None  # None => debe escalar (no hay info)
    note: str = ""


@dataclass
class EvalProperty:
    name: str
    knowledge: dict[str, str]  # categoría -> contenido
    cases: list[Case] = field(default_factory=list)


DATASET: list[EvalProperty] = [
    EvalProperty(
        name="Ático Malasaña",
        knowledge={
            "wifi": "La contraseña del wifi es MALASANA-2024.",
            "check-in": "El check-in es a partir de las 15:00; llaves en la caja del portal.",
            "parking": "Hay un parking público en la calle Mayor 4, a 150 m, por unos 18 € al día.",
            "mascotas": "No se admiten mascotas en el apartamento.",
            "normas": "No se puede fumar dentro ni hacer fiestas; silencio a partir de las 22:00.",
        },
        cases=[
            # Léxicas (comparten palabras): el mock también debería acertar.
            Case("¿cuál es la contraseña del wifi?", "wifi", "léxica directa"),
            Case("¿a qué hora es el check-in?", "check-in", "léxica directa"),
            # Parafraseadas (sin palabras compartidas): aquí la bolsa de palabras falla.
            Case("¿cómo me conecto a internet?", "wifi", "paráfrasis: internet≈wifi"),
            Case("¿a qué hora puedo entrar al piso?", "check-in", "paráfrasis: entrar≈check-in"),
            Case("¿dónde puedo dejar el coche?", "parking", "paráfrasis: dejar el coche≈parking"),
            Case("¿puedo traer a mi perro?", "mascotas", "paráfrasis: perro≈mascotas"),
            Case("¿se puede fumar en el balcón?", "normas", "paráfrasis: fumar≈normas"),
            # Debe escalar: no hay información.
            Case("¿hay piscina en el edificio?", None, "sin info -> escala"),
            Case("¿tenéis cuna para bebés?", None, "sin info -> escala"),
        ],
    ),
    EvalProperty(
        name="Loft Gran Vía",
        knowledge={
            "cómo llegar": "Desde el aeropuerto, metro línea 8 a Nuevos Ministerios y la 10.",
            "aire": "El aire acondicionado se enciende con el mando blanco de la pared del salón.",
            "basura": "La basura se saca al contenedor de la esquina después de las 20:00.",
        },
        cases=[
            Case("¿cómo llego desde el aeropuerto?", "cómo llegar", "léxica"),
            # Parafraseadas.
            Case("hace mucho calor, ¿cómo pongo el clima?", "aire", "paráfrasis: calor/clima≈aire"),
            Case("¿dónde tiro la basura?", "basura", "paráfrasis: tirar≈sacar"),
            Case("where is the nearest supermarket?", None, "sin info (y en inglés) -> escala"),
        ],
    ),
]
