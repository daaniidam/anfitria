"""Integración con PMS / Channel Manager (Guesty, Avantio, Lodgify, Smoobu…).

En lugar de que el gestor recree su cartera a mano, conecta su PMS y se importan
pisos y reservas. Aquí hay un adaptador `demo` funcional (datos de ejemplo); los
reales se enchufarían con sus credenciales sin tocar el resto de la lógica.
"""
from __future__ import annotations

from datetime import date, timedelta

# Proveedores que la UI muestra; solo `demo` está implementado en este entorno.
PROVIDERS = [
    {"id": "demo", "name": "PMS demo", "available": True},
    {"id": "guesty", "name": "Guesty", "available": False},
    {"id": "avantio", "name": "Avantio", "available": False},
    {"id": "lodgify", "name": "Lodgify", "available": False},
    {"id": "smoobu", "name": "Smoobu", "available": False},
]
_AVAILABLE = {p["id"] for p in PROVIDERS if p["available"]}


def is_available(provider: str) -> bool:
    return provider in _AVAILABLE


def fetch_portfolio(provider: str, today: date | None = None) -> tuple[list[dict], list[dict]]:
    """Devuelve (pisos, reservas) del PMS. Solo `demo` trae datos aquí."""
    if provider != "demo":
        raise ValueError("Proveedor no disponible en este entorno")
    today = today or date.today()

    properties = [
        {"external_ref": "pms-loft-granvia", "name": "Loft Gran Vía", "default_language": "es"},
        {"external_ref": "pms-estudio-sol", "name": "Estudio Sol", "default_language": "es"},
    ]
    reservations = [
        {
            "property_ref": "pms-loft-granvia", "guest_name": "Sophie Martin",
            "guest_ref": "+33612345678", "check_in": today, "check_out": today + timedelta(days=3),
            "source": "airbnb", "code": "PMS-AB-1001",
        },
        {
            "property_ref": "pms-loft-granvia", "guest_name": "James Wilson",
            "guest_ref": "+447700900123", "check_in": today + timedelta(days=5),
            "check_out": today + timedelta(days=8), "source": "booking", "code": "PMS-BK-2002",
        },
        {
            "property_ref": "pms-estudio-sol", "guest_name": "Laura Gómez",
            "guest_ref": "+34655123456", "check_in": today + timedelta(days=1),
            "check_out": today + timedelta(days=4), "source": "direct", "code": "PMS-DR-3003",
        },
    ]
    return properties, reservations
