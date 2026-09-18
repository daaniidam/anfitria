# AnfitrIA 🏨🤖

**Conserje con IA supervisada para alquiler vacacional (Airbnb).** Atiende a los
huéspedes por WhatsApp con respuestas ancladas a la información de cada piso;
el anfitrión **aprueba, edita o envía** desde un panel, con registro de todo.

> Estado: **Fase 1 — andamiaje** (esqueleto que arranca). Ver el roadmap abajo.

## Por qué
Los pisos turísticos sin recepción reciben las mismas preguntas una y otra vez
(check-in, wifi, cómo llegar, normas, recomendaciones), hoy por llamada/WhatsApp
del anfitrión. AnfitrIA automatiza esa atención **sin perder el control**: IA
supervisada, multi-idioma (ES/EN) y trazable.

## Stack
- **Backend:** Python 3.12 · FastAPI (async) · SQLAlchemy 2 async · Alembic · Redis + ARQ · uv
- **BD:** PostgreSQL 16 + pgvector (RAG)
- **IA:** adaptador `mock` (sin clave) | `anthropic` (Claude)
- **Canal:** adaptador `sim` (WhatsApp simulado) | `whatsapp_cloud` (Meta Cloud API)
- **Frontend:** React + TypeScript + Vite + TailwindCSS
- **Infra:** Docker Compose (`db`, `redis`, `api`, `worker`, `web`)

## Arranque rápido
```bash
cp .env.example .env          # opcional en fase 1 (los valores por defecto ya sirven)
docker compose up --build
```
- API: http://localhost:8000  ·  Health: http://localhost:8000/health  ·  Docs: http://localhost:8000/docs
- Web: http://localhost:5173

### Sin Docker (solo backend)
```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload    # necesita Postgres/Redis para las fases 2+
uv run pytest                           # tests
uv run ruff check .                     # lint
```

## Estructura
```
anfitria/
├── backend/            # FastAPI + worker ARQ (uv, pyproject.toml)
│   └── app/            # config, main, worker (rutas/modelos/servicios/adaptadores en fases 2+)
├── frontend/           # React + TS (Vite)
├── docker-compose.yml  # db (pgvector), redis, api, worker, web
├── .devcontainer/      # entorno reproducible (VS Code / Codespaces)
├── .cursor/rules/      # contexto del proyecto para Cursor (AI)
└── docs/spec.md        # diseño y decisiones
```

## Roadmap
1. **Andamiaje** — repo, compose, `/health`, React shell, Postgres/Redis. ✅
2. **Núcleo** — auth, pisos, conocimiento, conversaciones, canal `sim`, IA `mock`, aprobación + auditoría.
3. **RAG** — pgvector + embeddings; respuestas ancladas al piso.
4. **Claude real** — adaptador `anthropic`.
5. **WhatsApp real** — Meta Cloud API (número de test) + firma HMAC del webhook.
6. **Métricas + pulido** — panel de métricas, capturas, seed de demo.

## Continuar en Cursor
Este repo trae **reglas de proyecto en `.cursor/rules/`** para que el agente de
Cursor continúe con todo el contexto (stack, arquitectura, convenciones y fases).
Abre la carpeta en Cursor y pídele, por ejemplo: *"implementa la Fase 2 siguiendo
las reglas del proyecto"*. Empieza por `docs/spec.md`.

## Créditos
Proyecto personal de **Daniel López** ([@daaniidam](https://github.com/daaniidam)).
