"""Planes de suscripción (SaaS por nº de pisos).

El pago está simulado en esta demo; la estructura (planes, límites, estado de la
cuenta) es real y el límite de pisos se aplica de verdad.
"""

PLANS = [
    {"id": "free", "name": "Prueba", "price_eur": 0, "max_properties": 3},
    {"id": "starter", "name": "Starter", "price_eur": 29, "max_properties": 10},
    {"id": "pro", "name": "Pro", "price_eur": 79, "max_properties": 30},
    {"id": "business", "name": "Business", "price_eur": 199, "max_properties": 200},
]
_BY_ID = {p["id"]: p for p in PLANS}


def get_plan(plan_id: str) -> dict:
    return _BY_ID.get(plan_id, PLANS[0])


def max_properties(plan_id: str) -> int:
    return get_plan(plan_id)["max_properties"]
