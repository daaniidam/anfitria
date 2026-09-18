# AnfitrIA — Especificación de diseño

## Problema
Los alojamientos turísticos (Airbnb) sin recepción atienden a los huéspedes por
llamada/WhatsApp. Las preguntas son repetitivas y llegan a cualquier hora, lo que
consume tiempo del anfitrión y empeora la experiencia. Objetivo: **automatizar la
atención al huésped sin renunciar al control humano**.

## Usuarios
- **Anfitrión / gestor de pisos**: administra sus pisos y su información, revisa y
  aprueba respuestas, ve métricas.
- **Huésped**: escribe por WhatsApp; recibe respuestas útiles en su idioma.

## Alcance del MVP
- Gestión de **pisos** y su **ficha de conocimiento** (check-in/out, wifi, dirección,
  normas, FAQs, recomendaciones locales).
- **Conversaciones** por piso/huésped; mensajes entrantes y salientes.
- **Generación de respuesta con IA** anclada al conocimiento del piso (RAG), con
  **detección de idioma** (ES/EN) y respuesta en el idioma del huésped.
- **Supervisión**: cola de **borradores**; el anfitrión aprueba / edita / envía.
  Modo opcional de **auto-envío** cuando la confianza supera un umbral.
- **Trazabilidad**: `AuditLog` de cada decisión (borrador generado, editado, enviado,
  auto-enviado) con modelo y confianza.
- **Métricas**: nº de mensajes, % auto-resueltos, tiempo estimado ahorrado.

## Fuera de alcance (por ahora)
- Voz/llamadas telefónicas.
- Integración con motores de reserva (Airbnb/Booking) — se puede añadir después.
- Facturación / pagos.

## Arquitectura
- **API** (FastAPI async) expone panel + webhook del canal.
- **Worker** (ARQ) procesa mensajes entrantes y llamadas a la IA (no bloquea el webhook).
- **PostgreSQL + pgvector** guarda datos y embeddings del conocimiento.
- **Adaptadores** tras interfaz:
  - IA: `mock` | `anthropic` (Claude).
  - Canal: `sim` (WhatsApp simulado) | `whatsapp_cloud` (Meta Cloud API).

Flujo: mensaje entrante → persistir → encolar → recuperar conocimiento del piso →
IA genera borrador + confianza → aprobación (o auto-envío) → envío → `AuditLog`.

## Modelo de datos (borrador)
- `User(anfitrión)`: credenciales, pisos.
- `Property`: nombre, dirección, idioma por defecto, ajustes (umbral de auto-envío).
- `KnowledgeChunk`: `property_id`, texto, `embedding vector`, categoría.
- `Conversation`: `property_id`, identificador del huésped, canal, estado.
- `Message`: `conversation_id`, dirección (in/out), texto, idioma, timestamp.
- `Draft`: `message_id`, texto propuesto, estado (pendiente/aprobado/editado/enviado),
  confianza, modelo.
- `AuditLog`: actor (IA/anfitrión), acción, datos, timestamp.
- `WhatsAppConfig`: credenciales por anfitrión (fase 5).

## Decisiones
- **Python/FastAPI** (no Laravel) por robustez async, ecosistema de IA y RAG con
  pgvector; elección guiada por el problema, no por costumbre.
- **IA supervisada** como principio: siempre hay revisión posible y registro.
- **Adaptadores** para poder demostrar sin claves (`mock`/`sim`) y pasar a real
  (`anthropic`/`whatsapp_cloud`) sin tocar la lógica de negocio.

## Seguridad
- Webhook de WhatsApp: verificación de `hub.verify_token` y validación de firma
  **HMAC-SHA256** (`X-Hub-Signature-256`) con el `app_secret`.
- Secretos solo por entorno (`.env`), nunca en el repo.
