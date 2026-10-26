# AnfitrIA — RAG visible + remate técnico — Diseño

Fecha: 2026-10-22
Autor: Daniel López
Estado: implementado

## Objetivo

Dejar Anfitria **presentable para enviar a empresas**, con el foco en lo que
una empresa mira: **el RAG y la implementación de IA**. Hoy el RAG funciona pero
es **invisible** (se recuperan fragmentos y se calcula su similitud, pero no se
guardan ni se muestran). El trabajo hace el RAG **visible y explicable** en el
producto, refuerza la parte técnica y arregla dos bugs reales detectados al
arrancar la app.

No se añaden features de negocio nuevas: se trata de pulir y lucir lo existente.

## Alcance

Dentro:
1. Cerrar y commitear el **refactor UX** ya empezado (sin commitear).
2. **Bug 1** — "la IA aprende" guarda basura como conocimiento.
3. **Bug 2** — el umbral de auto-respuesta admite valores inalcanzables.
4. **Feature A** — RAG visible: persistir las citas (fragmentos + similitud) de
   cada respuesta y mostrarlas en Simulador, Bandeja y Auditoría.
5. **Feature B** — confianza graduada real de Claude (no 0.9/0.2 fijo).
6. **Docs** — `docs/RAG.md` con el pipeline y las decisiones, enlazado del README.

Fuera: WhatsApp real, pagos, embeddings reales en producción (se deja el
adaptador conmutable ya existente), despliegue online, presentación/deck.

## Contexto del código (estado actual)

- `services/retrieval.py` — `retrieve()` devuelve `list[(content, score)]`; score
  es coseno (embeddings L2-normalizados). Umbral de recuperación 0.25.
- `services/conversation.py::handle_inbound()` — calcula `hits` (los fragmentos
  recuperados con score), genera el borrador vía el adaptador de IA, decide
  auto-respuesta vs escalada por umbral, y **descarta los hits**.
- `adapters/ai/mock.py` — confianza = `min(0.6 + 0.4·score, 0.97)` si hay
  conocimiento; responde con el primer fragmento.
- `adapters/ai/anthropic_ai.py` — confianza **fija** 0.9 (can_answer) / 0.2.
- `services/drafts.py::approve_draft()` — al aprobar una escalada con
  `save_to_knowledge`, guarda el texto como `KnowledgeItem` categoría "aprendido"
  **sin filtrar**.
- `models.py` — `Draft` no guarda las fuentes; `KnowledgeItem` tiene id, scope
  (property/building), category, content, embedding.
- `schemas.py` — `auto_answer_threshold: float | None` con `ge=0.0, le=1.0`.
- Frontend: `pages/BandejaPage.tsx` (ApprovalBox, `save` por defecto `true`),
  `pages/GuestSimPage.tsx` (simulador), `pages/AuditPage.tsx`,
  `pages/PropertiesPage.tsx` (sensibilidad por piso), `components/ConfidenceMeter.tsx`.

## Principio acordado (dirección del producto)

El valor de la app es el **bucle de aprendizaje**: responder sola siempre que
tenga conocimiento, escalar **solo cuando no tiene info**, y **aprender cada
respuesta** del anfitrión para escalar cada vez menos. No se fuerza a responder
sin anclaje (eso rompería la "IA supervisada" y haría que inventara). Aprender es
por defecto, pero **con contexto** (pregunta + respuesta) y **sin aprender
relleno** (mensajes de espera).

## Bug 1 — "la IA aprende" guarda basura  ✅ HECHO

Síntoma real (datos de demo): la categoría "aprendido" contenía mensajes de
espera ("Thanks for reaching out… I'll check this") y respuestas sueltas sin
contexto ("no", "el 26").

Causa: `approve_draft` guardaba el texto **sin validar** y, además, un borrador de
escalada trae como texto el propio mensaje de espera; aprobarlo sin editar lo
aprendía.

Arreglo implementado (`services/drafts.py` + `tests/test_learning.py`):
1. **Guardar pregunta + respuesta juntas**: `content = f"{question} → {text}"`,
   para que una respuesta corta ("el 26") siga teniendo sentido en la ficha y al
   recuperarse. El `mock` recorta el "pregunta →" al responder al huésped.
2. **No aprender mensajes de espera**: `_is_learnable(text)` descarta los textos
   que coinciden con las plantillas `conversation.HOLDING` / `mock._WAIT`
   (firmas derivadas de las propias plantillas, en todos los idiomas). Si se pidió
   guardar pero no es aprendible, se registra `AuditLog action="learn_skipped"`.
3. **Guardado activado por defecto** (se mantiene): el bucle de aprendizaje es el
   valor de la app. (Se descartó mi propuesta inicial de desactivarlo y de filtrar
   por longitud: iba en contra del objetivo.)

## Bug 2 — umbral de auto-respuesta inalcanzable  ✅ HECHO

Síntoma: un piso con `auto_answer_threshold = 0.99` nunca auto-responde (el `mock`
da como máximo 0.97).

Arreglo implementado (`schemas.py`): acotar a `ge=0.3, le=0.95` en
`PropertyCreate` y `PropertyUpdate` (0.95 deja margen bajo el máximo real).
Pendiente (frontend, en el plan): control de sensibilidad acotado/etiquetado en
`PropertiesPage`, nunca texto libre.

## Bug 3 — recuperación con falsos positivos  ✅ HECHO

Síntoma (descubierto en vivo): a "¿el piso tiene piscina?" la IA respondía sola
con la info del **parking** (compartían solo la palabra "piso", score 0.298).
Respuesta segura pero equivocada → rompe "escalar solo sin info".

Arreglo implementado (`services/retrieval.py`): subir `RETRIEVAL_THRESHOLD` de
0.25 a 0.40, que separa los aciertos reales (comparten 2+ palabras, ~0.5+) de los
espurios de una sola palabra común. Suite completa (65 tests) en verde.

## Feature A — RAG visible (citas)

### Modelo de datos

Nueva tabla `DraftCitation` (una fila por fragmento que ancló la respuesta):

| campo               | tipo                                   | nota |
|---------------------|----------------------------------------|------|
| id                  | PK                                     | |
| draft_id            | FK → drafts.id, index                  | |
| knowledge_item_id   | FK → knowledge_items.id, nullable      | origen (puede borrarse después) |
| content             | Text                                   | **snapshot** del fragmento |
| category            | String(64)                             | para el chip |
| score               | Float                                  | similitud coseno 0–1 |

`Draft` gana `citations: relationship(order_by score desc)`.
Snapshot + FK: el snapshot evita que la cita "mienta" si el conocimiento cambia;
la FK conserva el origen. Una migración Alembic nueva.
(Alternativa descartada: columna JSON en `Draft` — más simple, pero sin
integridad relacional ni demostración de modelado; el snapshot ya resuelve la
robustez, así que preferimos la tabla.)

### Recuperación y persistencia

- `retrieval.retrieve()` pasa a devolver también `id` y `category` del fragmento
  (hoy solo `content, score`). Se ajustan sus llamadas y tests.
- `conversation.handle_inbound()`: tras crear el `Draft`, crea las
  `DraftCitation` a partir de los `hits` (ya calculados). No cambia el flujo de
  decisión; solo persiste lo que ya se computaba.

### API

- Nuevo `CitationOut { content, category, score }`.
- `DraftOut` gana `citations: list[CitationOut] = []`.
- Se sirve donde ya se devuelve el draft: `/inbox` (Bandeja),
  `/channels/sim/inbound` (Simulador) y en la Auditoría del borrador.

### Frontend (dónde se ve)

- Nuevo componente `SourceList` (reutiliza `ConfidenceMeter` para las barras).
- **Simulador** (`GuestSimPage`): bajo la respuesta de la IA, bloque
  "Me he basado en…" con cada fragmento (chip de categoría + texto) y su % de
  similitud.
- **Bandeja** (`BandejaPage::ApprovalBox`): mismo bloque, plegable, para que el
  anfitrión vea el anclaje antes de aprobar.
- **Auditoría** (`AuditPage`): en las entradas `draft_generated`, mostrar las
  fuentes y la confianza.

## Feature B — confianza graduada

- `anthropic_ai.py`: el JSON de Claude incluye `confidence` (0–1) auto-evaluada.
  La confianza final combina modelo y recuperación:
  `final = round(0.6·conf_modelo + 0.4·score_top, 2)` cuando `can_answer`;
  si no, baja (p. ej. 0.15). Degradación segura intacta.
- `mock.py`: mantiene su confianza ya derivada del score (coherente con la
  fórmula); sin cambios de comportamiento.
- Documentar la fórmula en `docs/RAG.md`.

## Docs

`docs/RAG.md`: diagrama mermaid del pipeline (embed → recuperar → anclar →
confianza → supervisión), y decisiones/trade-offs: coseno en Python vs operador
indexado de pgvector, embeddings mock vs reales, fórmula de confianza, y por qué
IA supervisada. Enlazado desde el README en una sección "Cómo funciona la IA".

## Pruebas

Backend (pytest):
- `retrieve()` devuelve id + category + score.
- `handle_inbound` persiste `DraftCitation` con el score correcto.
- Borrar un `KnowledgeItem` no rompe la cita (snapshot sobrevive).
- Fórmula de confianza combinada (Claude) con un cliente simulado.
- `approve_draft` no aprende holding/triviales; sí aprende una respuesta real.
- Validación de umbral fuera de rango (422).

Frontend (vitest):
- `SourceList` renderiza chips + % correctamente.
- ApprovalBox: el check "Guardar" nace desmarcado.

CI existente (`ruff` + `pytest`, `oxlint` + build + `vitest`) debe seguir verde.

## Orden de trabajo

1. Cerrar/commitear el **refactor UX** (revisar que arranca y compila).
2. **Bug 2** (acotar umbral) — pequeño, aislado.
3. **Bug 1** (filtro de aprendizaje + check por defecto) — aislado.
4. **Feature A backend**: modelo + migración + retrieval + persistencia + tests.
5. **Feature A API**: schemas + endpoints.
6. **Feature B**: confianza graduada + tests.
7. **Feature A frontend**: `SourceList` en simulador, bandeja y auditoría + tests.
8. **Docs**: `docs/RAG.md` + sección en README.

## Riesgos / notas

- Migración Alembic: verificar que corre sobre la BD de demo existente sin
  pérdida (la tabla nueva es aditiva).
- `retrieve()` cambia de firma de retorno: revisar todas sus llamadas.
- Mantener la degradación segura de Claude (nunca romper el chat).
