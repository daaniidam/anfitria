# Conectar WhatsApp real (Meta Cloud API)

AnfitrIA trae un canal `whatsapp_cloud` listo para usar la **WhatsApp Cloud API**
de Meta. Por defecto el proyecto funciona con el canal **simulado** (sin cuenta ni
número); esta guía es para cuando quieras enchufar WhatsApp de verdad.

## Qué necesitas (gratis para pruebas)
1. Una app en [Meta for Developers](https://developers.facebook.com/) con el
   producto **WhatsApp** añadido.
2. El **número de test** que Meta te da (envía a hasta 5 números verificados sin
   verificación de negocio). Anota su **Phone number ID** y el **Access token**
   temporal.
3. El **App secret** (Configuración → Básica) para validar la firma del webhook.
4. Un **verify token** que inventas tú (una cadena cualquiera).
5. Una **URL pública HTTPS** para el webhook. En local, usa un túnel:
   ```bash
   ngrok http 8000
   ```

## Configuración
Crea un `.env` en la raíz del proyecto:
```
CHANNEL_PROVIDER=whatsapp_cloud
WHATSAPP_VERIFY_TOKEN=el-token-que-inventaste
WHATSAPP_ACCESS_TOKEN=EAAG...token-de-meta
WHATSAPP_PHONE_NUMBER_ID=1234567890
WHATSAPP_APP_SECRET=abcd1234appsecret
```
Y en la app, asigna ese número al piso: al crear el piso, pon su
`whatsapp_phone_number_id` (el mismo `WHATSAPP_PHONE_NUMBER_ID`). Así el webhook
sabe a qué piso enrutar cada mensaje entrante.

Reinicia el backend: `docker compose up -d`.

## Registrar el webhook en Meta
En la app de Meta → WhatsApp → Configuración → **Webhook**:
- **Callback URL**: `https://<tu-tunel>.ngrok.app/channels/whatsapp/webhook`
- **Verify token**: el mismo `WHATSAPP_VERIFY_TOKEN`.
- Suscríbete al campo **messages**.

Meta hará un `GET` de verificación (AnfitrIA responde el `hub.challenge`) y a
partir de ahí enviará los mensajes entrantes por `POST`, firmados con
`X-Hub-Signature-256` (que AnfitrIA valida con el `WHATSAPP_APP_SECRET`).

## Cómo funciona por dentro
- **Salida**: `WhatsAppCloudChannel` publica en la Graph API
  `POST /{phone_number_id}/messages`.
- **Entrada**: `POST /channels/whatsapp/webhook` valida la **firma HMAC-SHA256**,
  localiza el piso por su `phone_number_id` y lanza el flujo de conserje
  (responder solo o escalar).
- **Seguridad**: sin firma válida, el webhook responde `403`. El verify token
  protege el alta del webhook.

## Nota de producción
El procesamiento de la IA se hace en línea para simplificar. En producción se
movería al worker (ARQ, ya incluido) para responder al webhook al instante y
evitar reintentos de Meta.
