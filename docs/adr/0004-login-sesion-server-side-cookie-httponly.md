# ADR 0004 — Login con sesión server-side y cookie `httpOnly` (sin OAuth ni multi-tenant)

## Estado

**Aceptada** — 2026-05-27

## Contexto

Hasta ahora la aplicación no tenía autenticación. Una `WizardSession` se identificaba por un UUID4 opaco (`POST /sessions`) y **cualquiera que conociera ese id** podía leer, mutar, extraer o publicar el DPP, además de leer y continuar el chat de la sesión (`GET /sessions/{id}`, `PATCH /sessions/{id}`, `POST /chat`, …). El id era el único secreto y viajaba en la URL del wizard.

Esto choca con dos necesidades del producto:

1. **Privacidad de los datos del fabricante.** El BOM, los PDFs subidos (datasheets, certificados, LCA) y las conversaciones del chat son información sensible de la PYME. No deben ser accesibles solo por adivinar/filtrar un UUID.
2. **Reanudación por persona, no por URL.** El fabricante quiere volver a entrar y encontrar "sus conversaciones y los DPP que empezó" sin guardar URLs. Hoy, perder la URL = perder la sesión.

`docs/ARCHITECTURE.md` (§"Decisiones descartadas") y `CLAUDE.md` declaran explícitamente: **"No multi-tenant ni OAuth en el alcance del hackathon. Basic auth si hace falta exponer en red local."** Cualquier login debe respetar el espíritu de ese descarte: nada de proveedores de identidad externos, nada de aislamiento por organización, nada de infraestructura pesada (una instancia = un fabricante PYME, SQLite + FastAPI).

Hay además un requisito de seguridad concreto del ticket: **"que sea seguro y no almacene nada en local"** — el estado de autenticación no debe vivir en `localStorage`/`sessionStorage` del navegador (vector de robo de token vía XSS).

## Decisión

**Se añade un login propio de email + contraseña, con sesión server-side persistida en SQLite y un token transportado en una cookie `httpOnly`. Las sesiones del wizard y el chat se ligan a un `user_id`. No es OAuth ni multi-tenant: solo cuentas de usuario dentro de la misma instancia auto-hospedada.**

Concretamente:

- **Contraseñas:** hash con `hashlib.scrypt` de la stdlib (KDF memory-hard), salt aleatorio por contraseña y parámetros embebidos en el digest (`scrypt$n$r$p$salt$hash`). Cero dependencias nuevas — se descartó argon2/bcrypt para no añadir wheels con build C al lock de `uv`. Ver `backend/src/app/auth/service.py`.
- **Sesión server-side, no JWT:** el token (`secrets.token_urlsafe(32)`) vive en una fila de `auth_sessions`; en BD solo se guarda su **SHA-256**, así una fuga de BD no entrega sesiones reutilizables. Es revocable (logout, expiración a 30 días por defecto).
- **Cookie `httpOnly` + `SameSite=Lax`:** inaccesible desde JS (mitiga XSS); el navegador la adjunta con `credentials: "include"`. `Secure` se controla por `AUTH_COOKIE_SECURE` (False en dev `http://localhost`, **True obligatorio tras HTTPS**). No se guarda nada de auth en `localStorage`.
- **Propiedad de sesiones ("blanda"):** `POST /sessions` exige login y graba `user_id`. La lectura/escritura comprueba propiedad: una sesión con `user_id` poblado solo la ve su dueño (404 ante una ajena, sin confirmar su existencia); una sesión con `user_id` nulo (seed/demo/legacy) sigue siendo accesible. Como toda sesión creada por la API lleva dueño, en la práctica esto aísla los DPP por usuario. Ver `_get_owned_or_404` en `backend/src/app/api/v1/wizard.py` y `_owned_session_or_404` en `chat.py`.
- **Reanudación:** `GET /sessions` devuelve las sesiones del usuario (descripción, sector, paso, flags `has_chat`/`published`) para el panel `/panel`.
- **Endpoints de auth:** `POST /auth/register` (gated por `ALLOW_REGISTRATION`), `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`. Errores genéricos (401 en login, sin distinguir email inexistente de contraseña errónea; trabajo de verificación equivalente cuando el email no existe) para no convertir el login en un oráculo de cuentas.
- **Frontend:** páginas `/login` y `/panel`; `proxy.ts` (el "middleware" de Next 16) redirige a `/login` las rutas `/wizard` y `/panel` si falta la cookie; `serverFetch` reenvía la cookie en Server Components vía `next/headers` y manda `credentials: "include"` en cliente.

## Alternativas consideradas

- **A) Mantener solo el UUID opaco como secreto (sin login).** Descartada: no protege datos sensibles (un id filtrado en logs, historial del navegador o un `Referer` expone el DPP completo) y no permite reanudar "mis sesiones" por persona.
- **B) HTTP Basic auth** (la opción que sugería el descarte original). Descartada: no liga sesiones a un usuario (todos comparten credencial), el navegador cachea la credencial de forma incontrolable y no hay logout limpio ni "mis DPP".
- **C) OAuth / proveedor de identidad externo (Google, etc.).** Descartada explícitamente por el alcance del hackathon (`ARCHITECTURE.md`): añade dependencia de un IdP externo y complejidad sin valor para una instancia auto-hospedada de una PYME.
- **D) JWT en `localStorage`.** Descartada: viola "no almacenar nada en local"; el token en `localStorage` es robable por XSS y no es revocable server-side. La sesión server-side + cookie `httpOnly` es estrictamente mejor en ambos ejes.
- **E) Token de sesión en claro en BD.** Descartada: una fuga de BD entregaría sesiones vivas. Guardar solo el SHA-256 del token cuesta lo mismo y elimina ese riesgo.
- **F) Multi-tenant real (aislamiento por organización).** Descartada: fuera de alcance. El modelo es "una instancia = un fabricante"; basta aislar por usuario dentro de la instancia.

## Consecuencias

**Positivas:**

- Los datos del fabricante (BOM, PDFs, chat, DPP en curso) quedan protegidos por sesión autenticada; un UUID filtrado ya no basta para acceder.
- Reanudación por persona: al volver a entrar, el panel lista las conversaciones y DPP empezados.
- Seguridad sólida sin dependencias nuevas: scrypt + token aleatorio + cookie `httpOnly`, todo con la stdlib y FastAPI.
- Se respeta el espíritu del descarte: ni OAuth, ni IdP externo, ni multi-tenant, ni Postgres/Redis.

**Negativas / costes:**

- Reabre parcialmente una decisión descartada (login): este ADR lo justifica y acota (login propio mínimo ≠ OAuth/multi-tenant). `ARCHITECTURE.md` §"Decisiones descartadas" se actualiza para apuntar aquí.
- Sin Alembic real en el proyecto, la columna `sessions.user_id` se añade a BDs SQLite preexistentes con una migración ligera idempotente en `init_db()` (`ALTER TABLE … ADD COLUMN`). En un futuro con Alembic, formalizar como migración.
- `AUTH_COOKIE_SECURE` **debe** ponerse a `true` en cualquier despliegue tras HTTPS; olvidarlo permitiría enviar la cookie por HTTP. Documentado en `.env.example`.
- Frontend y backend deben compartir el nombre de la cookie (`pa_session` por defecto); si se cambia `AUTH_COOKIE_NAME`, ajustar también `NEXT_PUBLIC_AUTH_COOKIE_NAME`.

## Invariantes que se mantienen

- **El chat sigue sin escribir en el estado del wizard.** El login solo añade una comprobación de propiedad antes de responder/persistir el chat; no toca `progress` ni `extracted_fields`.
- **El endpoint público `GET /dpp/{slug}` sigue siendo público** (sin auth): es el punto de escaneo del QR. La autorización solo aplica a las rutas del fabricante bajo `/sessions` y `/chat`.
- **Pipeline lineal, SQLite única, sin servicios nuevos.** Las tablas `users` y `auth_sessions` nacen del mismo `create_all` que el resto.
