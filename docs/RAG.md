# Cómo funciona la IA de AnfitrIA (RAG + IA supervisada)

AnfitrIA no "le pasa la pregunta a un modelo y reza". Ancla cada respuesta en la
**ficha de conocimiento del piso** (RAG), mide su **confianza**, y deja siempre al
anfitrión el control. Este documento explica el pipeline y las decisiones.

## Principio

**Responder sola cuando tiene información que la ancle; escalar al anfitrión
cuando no la tiene; aprender de cada respuesta del anfitrión** para escalar cada
vez menos. Nunca inventa: si no hay conocimiento relevante, escala en vez de
arriesgar una respuesta incorrecta. Es *IA supervisada, no caja negra*.

## El pipeline

```mermaid
flowchart TD
    A[Mensaje del huésped] --> B[Detección de idioma]
    B --> C[Embedding de la consulta]
    C --> D[Recuperación por similitud<br/>coseno sobre la ficha del piso + edificio]
    D -->|score ≥ umbral| E[Fragmentos relevantes (citas)]
    D -->|nada supera el umbral| F[Sin anclaje]
    E --> G[IA genera respuesta<br/>mock | Claude]
    F --> G
    G --> H[Confianza<br/>modelo × recuperación]
    H -->|≥ umbral del piso| I[Responde sola]
    H -->|< umbral| J[Escala: mensaje de espera<br/>+ borrador para el anfitrión]
    I --> K[AuditLog + citas guardadas]
    J --> K
    J --> L[El anfitrión responde]
    L --> M{¿Guardar en la ficha?}
    M -->|sí, y no es relleno| N[Aprende: pregunta + respuesta]
    N --> D
```

## Componentes (y dónde están)

- **Embeddings** (`adapters/embeddings/`): convierten texto en vectores
  normalizados. Dos adaptadores conmutables por `EMBED_PROVIDER`:
  - `mock`: bolsa de palabras con hashing, sin dependencias ni descargas (tests/CI).
  - `local`: transformer multilingüe `paraphrase-multilingual-MiniLM-L12-v2` vía
    fastembed (ONNX, **sin clave y sin torch**), con semántica real. Cada proveedor
    define su propio umbral de recuperación (la escala de coseno depende del modelo).
- **Recuperación** (`services/retrieval.py`): similitud coseno entre la consulta y
  cada fragmento del piso **+ el conocimiento compartido de su edificio**. Devuelve
  los `k` mejores por encima de un umbral, con su `score` (para las citas).
- **IA** (`adapters/ai/`): `mock` (determinista, responde con el fragmento
  recuperado) o `anthropic` (Claude razona sobre la ficha y devuelve un JSON con
  `can_answer`, `confidence` y la respuesta). Prompt endurecido contra inyección.
- **Orquestación** (`services/conversation.py`): une todo, decide auto-responder vs
  escalar, persiste el borrador, **las citas** (`DraftCitation`) y la auditoría.
- **Aprendizaje** (`services/drafts.py`): al aprobar una escalada, guarda
  pregunta + respuesta como nuevo conocimiento (si no es un mensaje de espera).

## Decisiones y trade-offs

- **Coseno en Python, no el operador de pgvector.** El cálculo se hace en Python
  para funcionar igual en Postgres y en SQLite (tests). En producción, con muchos
  fragmentos, se cambia por el operador indexado `embedding <=> :q` de pgvector sin
  tocar el resto de la lógica. (Decisión consciente: simplicidad y portabilidad
  ahora; escalabilidad cuando haga falta.)
- **Umbral de recuperación = 0.40.** Por debajo, compartir una sola palabra común
  (p. ej. "piso") colaría conocimiento irrelevante y la IA respondería con
  seguridad algo equivocado. 0.40 separa los aciertos reales (comparten 2+
  palabras) de los espurios.
- **Confianza graduada.** Con Claude: `0.6 · confianza_del_modelo + 0.4 ·
  similitud_de_recuperación`. Combina la auto-evaluación del modelo con la señal
  objetiva del RAG, en vez de un valor fijo. El umbral de auto-respuesta es
  **por piso** (sensibilidad ajustable, 0.30–0.95).
- **Aprender con contexto, sin relleno.** Se guarda *pregunta → respuesta* (para
  que una respuesta corta siga teniendo sentido) y **nunca** los mensajes de
  espera ("lo confirmo y te respondo"), que no son respuestas.
- **Embeddings mock vs locales.** El `mock` (bolsa de palabras) arranca sin
  descargas y vale para tests/CI, pero solo capta coincidencias léxicas: un huésped
  que parafrasea ("¿cómo me conecto a internet?" en vez de "wifi") no encuentra
  nada. El proveedor `local` (MiniLM multilingüe) entiende el significado, sigue sin
  necesitar clave, y la mejora está **medida** (ver abajo). Un proveedor de API
  (OpenAI/Voyage) se añadiría igual, tras la misma interfaz.

## Evaluación (medir, no suponer)

`eval/` contiene un harness que mide la calidad de recuperación sobre un dataset
con preguntas **parafraseadas** a propósito. Mide la decisión (responder vs
escalar) y si recupera el fragmento correcto. Ejecuta `uv run python -m eval.run`.
Resultado (mejora del léxico al semántico):

| Proveedor | Decisión | Recuperación |
|---|---|---|
| mock (bolsa de palabras) | 46 % | 30 % |
| local (MiniLM, semántico) | 92 % | 100 % |

## Qué se ve (RAG visible)

Cada respuesta guarda las **citas** (fragmento + categoría + % de similitud), que
se muestran en el **Simulador**, en la **Bandeja** (antes de aprobar) y en la
**Auditoría**. El anfitrión —y quien evalúe el producto— ve *en qué se ancló* la
IA y *con qué confianza*. No es una caja negra.
