"""Siembra datos de demo reproducibles: un anfitrión y tres pisos con su ficha.

Idempotente: si el usuario de demo ya existe, no hace nada. El conocimiento se
embebe con el proveedor activo (define EMBED_PROVIDER). Uso:

    EMBED_PROVIDER=local uv run python -m scripts.seed
"""
import asyncio

from sqlalchemy import select

from app.adapters.embeddings.factory import get_embedding_provider
from app.db import SessionLocal
from app.models import KnowledgeItem, Organization, Property, User
from app.security import hash_password

DEMO_EMAIL = "demo@anfitria.com"
DEMO_PASSWORD = "Demo12345!"  # noqa: S105 (credencial de demo, no secreto real)

PROPERTIES = [
    {
        "name": "Ático Malasaña",
        "auto_answer_threshold": 0.70,
        "knowledge": {
            "wifi": "La red wifi se llama Atico_Malasana y la contraseña es MALASANA-2024.",
            "check-in": "El check-in es a partir de las 15:00. Las llaves están en la caja de "
            "seguridad junto al portal; el código te llega el día de llegada.",
            "direccion": "La dirección es Calle de la Palma 28, 3º izquierda, 28004 Madrid "
            "(Malasaña). El metro más cercano es Tribunal (líneas 1 y 10).",
            "parking": "Hay un parking público en la calle Mayor 4, a unos 150 m, por unos 18 € "
            "al día.",
            "normas": "No se permite fumar dentro ni hacer fiestas; respeta el descanso de los "
            "vecinos a partir de las 22:00.",
        },
    },
    {
        "name": "Loft Gran Vía",
        "auto_answer_threshold": None,
        "knowledge": {
            "cómo llegar": "Desde el aeropuerto, metro línea 8 a Nuevos Ministerios y luego la 10 "
            "hasta Gran Vía.",
            "aire": "El aire acondicionado se enciende con el mando blanco de la pared del salón.",
            "basura": "La basura se saca al contenedor de la esquina después de las 20:00.",
            "check-out": "El check-out es antes de las 11:00; deja las llaves sobre la mesa.",
        },
    },
    {
        "name": "Estudio Sol",
        "auto_answer_threshold": None,
        "knowledge": {
            "wifi": "La red wifi se llama Sol_Estudio y la contraseña es SOL-2024.",
            "check-in": "El check-in es a partir de las 16:00, con caja de llaves en la entrada.",
            "recomendaciones": "A 5 minutos tienes la Plaza Mayor y el Mercado de San Miguel para "
            "tapear.",
        },
    },
]


async def main() -> None:
    provider = get_embedding_provider()
    async with SessionLocal() as session:
        exists = await session.execute(select(User).where(User.email == DEMO_EMAIL))
        if exists.scalar_one_or_none() is not None:
            print(f"La demo ya existe ({DEMO_EMAIL}); nada que sembrar.")
            return

        org = Organization(name="Demo AnfitrIA")
        session.add(org)
        await session.flush()
        user = User(
            email=DEMO_EMAIL,
            name="Daniel (demo)",
            password_hash=hash_password(DEMO_PASSWORD),
            org_id=org.id,
            role="owner",
        )
        session.add(user)
        await session.flush()

        chunks = 0
        for spec in PROPERTIES:
            prop = Property(
                name=spec["name"],
                owner_id=user.id,
                org_id=org.id,
                default_language="es",
                auto_answer=True,
                auto_answer_threshold=spec["auto_answer_threshold"],
            )
            session.add(prop)
            await session.flush()
            categories = list(spec["knowledge"].keys())
            contents = list(spec["knowledge"].values())
            vectors = provider.embed(contents)
            for category, content, vector in zip(categories, contents, vectors, strict=True):
                session.add(
                    KnowledgeItem(
                        property_id=prop.id, category=category, content=content, embedding=vector
                    )
                )
                chunks += 1

        await session.commit()
        print(
            f"Demo creada: {len(PROPERTIES)} pisos, {chunks} fragmentos.\n"
            f"Acceso: {DEMO_EMAIL} / {DEMO_PASSWORD}"
        )


if __name__ == "__main__":
    asyncio.run(main())
