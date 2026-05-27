# Especificación funcional · PasaporteAbierto

Versión 1.0 · Última actualización: 22 mayo 2026

Documento funcional del sistema PasaporteAbierto. Acompaña al documento de [arquitectura](./ARCHITECTURE.md) y a los tickets del [board Trello](./tickets/) (carpeta `tickets/`). El documento describe **qué hace** el sistema desde el punto de vista del usuario y **cómo se comporta** desde el punto de vista del equipo dev. Para decisiones técnicas (stack, patrones, descartes), ver `ARCHITECTURE.md`.

---

## 1. Objetivo y alcance

PasaporteAbierto es una **aplicación web auto-hospedable** que ayuda a fabricantes PYME a generar el **Pasaporte Digital de Producto (DPP)** exigido por el Reglamento UE 2024/1781 (ESPR), sin depender de SaaS propietario.

El alcance del hackathon (1 semana, 6 fases) cubre:

- Wizard guiado de 7 pasos para registrar un producto y generar su DPP.
- Pipeline IA con dos componentes acotados (Clasificador y Recolector) y todo lo demás determinista.
- Chat lateral normativo con cita obligatoria.
- Generación del DPP en JSON-LD con vocabulario local alineado con el modelo conceptual CIRPASS-2 Core (ver [ADR 0002](./adr/0002-jsonld-vocabulario-local.md)), QR resoluble vía identificador único declarado por el plugin sectorial (ISO/IEC 15459-1/2/3/4/5/6 para baterías por Art. 77.3 del Reglamento UE 2023/1542; GS1 Digital Link como esquema por defecto), endpoint público con content negotiation.
- Plugins YAML para cubrir actos delegados sectoriales por configuración (no por código).
- Observabilidad (Langfuse) y trazabilidad inmutable (audit log con hash chain).

**Fuera de alcance del hackathon:** multi-tenant, OAuth, federación entre instancias, marketplace de plugins, integración con sistemas ERP del fabricante.

---

## 2. Usuarios

| Rol | Perfil | Necesita |
|---|---|---|
| **Fabricante PYME** | No técnico, conoce su producto y sus proveedores. Necesita cumplir ESPR. | Wizard simple, sin jerga regulatoria innecesaria, con ayuda contextual. |
| **Auditor / cliente B2B** | Necesita validar un DPP publicado por un fabricante. | URL pública con DPP legible (HTML) y verificable (JSON-LD + firma). |
| **Consumidor final** | Escanea QR en el producto. | Página HTML legible en móvil con la información clave del DPP. |
| **Desarrollador externo (comunidad)** | Quiere añadir cobertura para un nuevo sector. | Guía clara para contribuir un plugin YAML sin tocar el núcleo. |
| **Equipo dev** | Mantiene y opera la instancia. | Trazas Langfuse, audit log verificable, tests E2E. |

---

## 3. Flujo funcional del wizard (perspectiva del fabricante)

El wizard tiene **7 pasos en cadena**. Cada paso es una ruta del frontend y un endpoint del backend. El **chat lateral** está disponible en todos los pasos.

### Acceso · _determinista (login)_

Antes de usar el wizard el fabricante inicia sesión (email + contraseña). El login es **propio y mínimo** (ver [ADR 0004](./adr/0004-login-sesion-server-side-cookie-httponly.md)): sesión server-side en SQLite, cookie `httpOnly`, sin OAuth ni IdP externo. Su función no es multi-tenant sino **ligar cada sesión del wizard y del chat a un `user_id`**, de modo que los datos sensibles (BOM, PDFs, conversación) no queden accesibles a quien adivine el UUID de la sesión. Una sesión creada sin login queda "sin dueño" y sigue siendo accesible (**propiedad blanda**); en cuanto un usuario autenticado la reclama, solo él la lee —el resto recibe `404`, no `403`, para no filtrar que la sesión existe—. El alta de cuentas puede cerrarse con el flag `allow_registration`. Endpoints: `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`.

### Paso 1 · Descripción del producto · _determinista_

**Lo que ve el fabricante:** un textarea grande con una pista contextual ("describe tu producto en lenguaje natural: para qué sirve, de qué está hecho, a quién se vende").

**Qué hace el sistema:** persiste la descripción en `sessions` con un `session_id` generado. Validación mínima de longitud (≥50 caracteres).

**Salida:** redirección al paso 2.

---

### Paso 2 · Clasificación de sector · _IA (Clasificador)_

**Lo que ve el fabricante:** el sistema muestra **automáticamente**:
- El sector identificado (ej. "Baterías industriales — Reglamento UE 2023/1542").
- Un badge con el **porcentaje de confianza**.
- La **cita normativa concreta** que justifica la clasificación (reglamento + artículo, enlazado a la fuente).
- Un botón para **override manual** si discrepa con la clasificación.

Si la confianza es **<0.7**, aparece un aviso destacado: "Revisa la clasificación antes de continuar".

**Qué hace el sistema:**
1. Recupera fragmentos del corpus regulatorio relacionados con la descripción (RAG, top-k).
2. Envía descripción + fragmentos al LLM con un prompt que exige: `{ sector, plugin, confianza, cita }`.
3. Persiste el resultado en `sessions`.
4. Cualquier override manual queda registrado en `audit_log` con el motivo.

**Salida:** confirmación del sector → carga del plugin YAML correspondiente → paso 3.

---

### Paso 3 · BOM (Bill of Materials) dinámico · _determinista_

**Lo que ve el fabricante:** un formulario adaptado a su sector, generado a partir del plugin YAML. Cada campo:
- Marcado como **obligatorio** o **opcional**.
- Acompañado de un icono "i" con la **cita normativa** que lo justifica.
- Con tipo de input apropiado (texto, número, select, repeater para materiales).

**Qué hace el sistema:** renderiza el formulario dinámicamente vía React Hook Form a partir de `plugins/{sector}.yaml`. Valida con las reglas del schema antes de avanzar. Persiste cada material en `extracted_fields` con `provenance = self_declared`.

**Salida:** BOM validado contra el schema del plugin → paso 4.

---

### Paso 4 · Documentos requeridos · _determinista_

**Lo que ve el fabricante:** una lista personalizada de los PDFs que debe subir (datasheets, certificados, LCAs, SDS, declaración CE…), calculada a partir del plugin **y** del BOM introducido. Cada documento muestra:
- Su tipo y propósito.
- Un dropzone para subir el PDF.
- Estado: `pendiente`, `subido`, `procesando`, `listo`.

**Qué hace el sistema:**
1. A partir del plugin y del BOM, deduce qué tipos de documentos son necesarios.
2. Acepta drag & drop multi-archivo (máx. 10 MB por PDF).
3. Calcula SHA-256 al subir; si el hash ya existe, **no duplica** el documento.
4. Persiste en la tabla `documents`.

**Salida:** todos los documentos requeridos marcados como `subido` → paso 5.

---

### Paso 5 · Extracción de datos · _IA (Recolector)_

**Lo que ve el fabricante:** una vista con **progreso en tiempo real** (SSE) mientras el Recolector procesa los PDFs. Al terminar, una tabla con todos los campos del DPP y, junto a cada uno, un badge de color:

| Badge | Estado | Significado |
|---|---|---|
| 🟢 Verde | `verified` | El PDF confirma un dato del BOM. |
| 🟠 Naranja | `self_declared` | El dato existe en el formulario o en el PDF, pero sin verificación cruzada. |
| 🔴 Rojo | `required_pending` | Campo obligatorio del plugin sin dato disponible. |

Los campos verdes / naranjas enlazan al **fragmento concreto del PDF fuente**. Los rojos quedan como tarea del fabricante: rellenar a mano, subir otro PDF o consultar al chat.

**Qué hace el sistema:**
1. Por cada PDF en `documents`, lanza el Recolector (paraleliza con `asyncio.gather`).
2. Pipeline híbrido: `pdfplumber` para texto estructurado, LLM para texto libre.
3. Por cada campo del plugin, asigna estado y persiste en `extracted_fields`.
4. **No abre diálogo con el usuario**: termina, escribe estado y devuelve el control al wizard.

**Salida:** el fabricante resuelve los pendientes y avanza → paso 6.

---

### Paso 6 · Verificación · _determinista_

**Lo que ve el fabricante:** un resumen de completitud:
- **Score 0–1** de completitud global.
- Lista de campos por estado (verified / self_declared / required_pending).
- Advertencias del plugin (ej. "el SoC declarado está por debajo del mínimo del Reglamento 2023/1542").

Si hay campos críticos vacíos, el botón "Generar DPP" del paso 7 **está deshabilitado** con motivo visible.

**Qué hace el sistema:** el Verificador (componente determinista) valida el estado completo contra el schema del plugin y sus reglas adicionales.

**Regla dura:** no se permite emitir un DPP parcial conforme. Si falta cualquier campo obligatorio, la publicación queda bloqueada.

**Salida:** completitud OK → paso 7.

---

### Paso 7 · Generación y publicación del DPP · _determinista_

**Lo que ve el fabricante:** tras confirmar, el sistema muestra:
- **Código QR** descargable (PNG y SVG) que codifica la URL pública navegable del DPP.
- **URL pública** del DPP en la forma `GET /dpp/{slug}` (slug opaco derivado del `session_id`). El identificador canónico (`gs1_uri`) según el esquema declarado por el plugin (ISO/IEC 15459 para baterías, GS1 Digital Link como fallback genérico) aparece dentro del DPP, no en la URL — ver [ADR 0003](./adr/0003-url-publica-slug-opaco.md).
- Confirmación de **firma Ed25519** (si se activó).

**Qué hace el sistema:**
1. Ensambla el DPP en **JSON-LD** con vocabulario local bajo el namespace URN `urn:pasaporte-abierto:dpp:v1#`, filtrando los campos por su `access_level` (ver §9.2) y emitiendo cada campo como `{value, provenance}` para mantener trazabilidad por dato. La estructura queda alineada con el modelo conceptual de CIRPASS-2 Core (marzo 2025) pero usa namespace propio hasta que el consorcio publique un `@context` HTTP-resolvable estable — ver [ADR 0002](./adr/0002-jsonld-vocabulario-local.md).
2. Genera el identificador único canónico delegando en la fábrica del esquema declarado por el plugin (`identifier_scheme`).
3. Genera el QR con `segno`.
4. Opcionalmente firma con Ed25519 (PyNaCl), persistiendo la clave pública.
5. Persiste en `published_dpps` (columna `gs1_uri`, nombre histórico que ahora soporta cualquier esquema).
6. Registra la publicación en `audit_log` (hash chain).
7. Expone el DPP en el endpoint público (paso siguiente, ver §5).

---

## 4. Chat lateral

Endpoint **independiente** del pipeline. Disponible en cualquier paso del wizard.

**Reglas funcionales duras:**
1. Cada respuesta debe terminar con `[Reglamento X, Art. Y]`. Sin excepciones.
2. Si el retrieval no devuelve fragmentos relevantes, la respuesta es: _"No tengo información suficiente para responder con base normativa."_
3. El chat **nunca escribe en el estado del wizard**. El dato lo introduce siempre el fabricante.
4. Preguntas fuera de dominio (clima, opinión personal, etc.) reciben la negativa estándar.

**Qué ve el fabricante:** panel lateral fijo con historial de la sesión. Cada respuesta incluye la cita normativa como link.

**Qué hace el sistema:** ensambla prompt con (a) contexto del wizard, (b) top-k del retrieval, (c) pregunta. Loguea la conversación completa en Langfuse y **persiste el histórico en la tabla `chat_messages`** —canal independiente del estado del wizard— para poder reanudar la conversación tras un refresh sin violar la invariante de que el chat no escribe en el wizard. El endpoint `POST /chat` recibe el `session_id` en el cuerpo; `GET /sessions/{id}/chat` devuelve el histórico.

---

## 5. DPP público

El DPP generado es accesible vía URL canónica `GET /dpp/{slug}` que aplica **content negotiation**:

| Header `Accept` | Respuesta |
|---|---|
| `application/ld+json` | JSON-LD válido con vocabulario local `urn:pasaporte-abierto:dpp:v1#` (consumido por máquinas, auditores, agregadores). Alineado con el modelo conceptual CIRPASS-2 Core; ver [ADR 0002](./adr/0002-jsonld-vocabulario-local.md). |
| `text/html` (default navegador) | Página HTML legible en móvil, con campos verificados destacados visualmente. |

La respuesta incluye únicamente los campos con `access_level = public` (Sección 1 del Annex XIII del Reg. UE 2023/1542 para baterías; el resto de sectores hereda `public` por defecto hasta que su acto delegado fije otra cosa). La página HTML diferencia visualmente **verified vs self_declared** (ver §9.1) para que el consumidor entienda la calidad del dato.

`slug` es un identificador opaco derivado del `session_id` (primeros 8 caracteres del UUID). El `gs1_uri` canónico —ISO/IEC 15459 para baterías por Art. 77.3 de Reg. UE 2023/1542; GS1 Digital Link como fallback genérico— aparece en el campo `@id` del JSON-LD y se muestra explícitamente en la página HTML como "Identificador". El QR codifica la URL opaca completa para que sea navegable directamente sin depender de resolvers externos. Ver [ADR 0003](./adr/0003-url-publica-slug-opaco.md).

---

## 6. Plugins (contrato funcional)

Cada plugin es un **YAML** en `plugins/`. Define:
- **Identidad del plugin**: nombre del sector, reglamento aplicable, versión.
- **Esquema del identificador único** (`identifier_scheme`): canónico del sector (p. ej. `iso_iec_15459` para baterías; `gs1_digital_link` como fallback).
- **Campos del DPP**: nombre, tipo, obligatoriedad, cita normativa, `access_level` (ver §9.2), regla de validación opcional.
- **Documentos requeridos**: tipo (datasheet, certificado, LCA, SDS, declaración CE) y condición de obligatoriedad.
- **Reglas adicionales**: validaciones cruzadas entre campos (ej. SoC mínimo, vida útil mínima).

El sistema valida cada plugin contra `plugins/_schema.yaml` al arrancar. **Un plugin que no cumpla el schema no se carga**.

**Cobertura del hackathon:**
- `plugins/batteries.yaml` (F1-03) — Reglamento UE 2023/1542, cubriendo las Secciones 1, 2 y 3 estáticas del Annex XIII (~32 campos). La Sección 4 (datos individuales dinámicos) se reconoce en el schema pero queda fuera del alcance del wizard del hackathon: son datos de telemetría que se inyectan en operación.
- `plugins/textile.yaml` (F6-04) — ejemplo de contribución para validar la arquitectura de extensibilidad.

---

## 7. Reglas funcionales transversales

### 7.1. Manejo de errores
- Ninguna pantalla queda en blanco ante un fallo de API.
- Los errores se muestran en lenguaje humano, nunca stack traces.
- Timeouts del LLM: retry automático x3 con backoff exponencial, luego mensaje + botón "Reintentar".

### 7.2. Persistencia de sesión
- Toda interacción del wizard se guarda automáticamente.
- Recargar mantiene el paso y los datos.
- La URL `/wizard/{session_id}` es compartible y reanuda exactamente donde se dejó.

### 7.3. Trazabilidad (audit log)
- Cada operación significativa (clasificación, override, validación, publicación, firma) escribe en `audit_log`.
- Cada fila incluye `prev_hash` apuntando a la anterior. Modificar una fila a mano rompe la cadena de forma detectable.
- Endpoint `GET /audit/verify` recorre la cadena y reporta si es íntegra o dónde se rompe.

### 7.4. Observabilidad (Langfuse)
- Cada decisión de Clasificador, Recolector y Chat se traza con prompt, modelo, tokens, latencia y resultado.
- Trazas separadas por componente para depuración y demo.
- Audit log y Langfuse son canales independientes (no se mezclan).

### 7.5. Internacionalización mínima
- El corpus indexado incluye al menos castellano e inglés.
- La UI del wizard está en castellano (alcance hackathon).
- Las citas normativas conservan el idioma original del reglamento.

---

## 8. Contratos de API (resumen funcional)

Todos los endpoints bajo prefijo `/api/v1`. Detalle de schemas en el código fuente (Pydantic v2).

| Paso | Método | Endpoint | Tipo | Devuelve |
|---|---|---|---|---|
| 1 | POST | `/sessions` | det | `session_id` |
| 2 | POST | `/sessions/{id}/classify` | IA | `{ sector, plugin, confianza, cita }` |
| 3 | PUT | `/sessions/{id}/bom` | det | estado del BOM persistido |
| 4a | GET | `/sessions/{id}/documents` | det | lista de documentos requeridos |
| 4b | POST | `/sessions/{id}/documents` | det | confirmación de subida + hash |
| 5 | POST | `/sessions/{id}/extract` | IA | stream SSE + estado final por campo |
| 6 | GET | `/sessions/{id}/verify` | det | `{ score, faltantes[], advertencias[] }` |
| 7 | POST | `/sessions/{id}/dpp` | det | `{ gs1_uri, qr_url, firma? }` |
| chat | POST | `/chat` | IA | respuesta con cita (recibe `session_id` en el cuerpo, no en la ruta) |
| chat · histórico | GET | `/sessions/{id}/chat` | det | mensajes persistidos de la sesión (tabla `chat_messages`) |
| auth · registro | POST | `/auth/register` | det | alta de cuenta (gated por `allow_registration`) |
| auth · login | POST | `/auth/login` | det | fija cookie `httpOnly` de sesión |
| auth · logout | POST | `/auth/logout` | det | revoca la sesión server-side |
| auth · identidad | GET | `/auth/me` | det | usuario autenticado |
| público | GET | `/dpp/{slug}` | det | JSON-LD o HTML según `Accept` (`slug` opaco derivado del `session_id`; el `gs1_uri` canónico va en el cuerpo — ver [ADR 0003](./adr/0003-url-publica-slug-opaco.md); ruta fuera del prefijo `/api/v1`) |
| audit | GET | `/audit/verify` | det | `{ ok, broken_at? }` |
| health | GET | `/health` | det | `{ version, model, backend }` |

---

## 9. Estados funcionales de los campos

Cada campo del DPP tiene **dos dimensiones ortogonales**: provenance (cómo de fiable es el dato) y access_level (quién puede verlo). Ambas se persisten en `extracted_fields` y se exponen en la UI con badges distintos.

### 9.1. Provenance (fiabilidad del dato)

Definición canónica de los tres estados que aparecen en la UI y en `extracted_fields.provenance`:

| Estado | UI | Cuándo se asigna |
|---|---|---|
| `verified` | 🟢 verde | El campo aparece tanto en el BOM del paso 3 **como** en un PDF subido, y el Recolector ha podido cruzar ambas fuentes con éxito. |
| `self_declared` | 🟠 naranja | El campo aparece **solo** en el BOM, **o solo** en un PDF, sin verificación cruzada. |
| `required_pending` | 🔴 rojo | Campo declarado obligatorio por el plugin del sector, sin dato disponible ni en BOM ni en PDFs. **Bloquea publicación**. |

### 9.2. Access level (visibilidad del dato)

Definición canónica de los cuatro niveles del Annex XIII del Reglamento UE 2023/1542, generalizados a todos los plugins. Cada campo del plugin declara su `access_level`; el plugin loader rechaza valores fuera del enum.

| Estado | A quién se expone | Origen normativo |
|---|---|---|
| `public` | Cualquiera (URL pública del DPP) | Annex XIII Sección 1 (Reg. UE 2023/1542) o equivalente. Default para plugins sin acto delegado específico. |
| `legitimate_interest` | Personas con interés legítimo + Comisión, sobre el **modelo** | Annex XIII Sección 2. Ej. composición detallada de cátodo/ánodo/electrolito, info de desmontaje, medidas de seguridad. |
| `authorities_only` | Organismos notificados + autoridades de vigilancia del mercado + Comisión | Annex XIII Sección 3. Ej. resultados de informes de ensayo de conformidad. |
| `individual` | Personas con interés legítimo sobre **una batería concreta** (no el modelo) | Annex XIII Sección 4. Datos dinámicos de telemetría: SoH actual, ciclos consumidos, accidentes, temperatura operativa, SoC. Fuera del alcance del wizard. |

**Regla dura:** el endpoint público `GET /dpp/{slug}` solo devuelve campos con `access_level = public`. Los demás quedan accesibles vía endpoints específicos planificados para fases posteriores del proyecto (no cubiertos por el hackathon).

La identidad del solicitante (operador notificado, MSA, interés legítimo) se resolverá a través de los actos de ejecución que la Comisión adoptará a más tardar el 18 de agosto de 2026 conforme al Art. 77.9 del Reglamento UE 2023/1542; hasta entonces el sistema solo expone el subconjunto `public`.

---

## 10. Definición de "hecho" (criterios globales de aceptación)

Al cierre del hackathon, el sistema debe cumplir simultáneamente:

1. `docker compose up` levanta toda la solución en una máquina nueva en ≤30 minutos siguiendo solo el README.
2. Un fabricante PYME completa el wizard de 7 pasos con datos demo de un producto del sector baterías y obtiene su DPP publicado en ≤15 minutos.
3. El DPP resultante es accesible vía URL pública y vía QR, valida su estructura interna y emite `provenance` por campo. La alineación formal con CIRPASS-2 Core queda pendiente de que el consorcio publique un `@context` HTTP-resolvable estable — ver [ADR 0002](./adr/0002-jsonld-vocabulario-local.md).
4. El chat responde con cita normativa al 100 % de las preguntas del set de referencia, y se niega correctamente fuera de dominio.
5. Existen al menos dos plugins funcionales (`batteries.yaml`, `textile.yaml`) cargados desde YAML sin tocar el núcleo.
6. La integridad del audit log es verificable end-to-end.
7. Los tests E2E del flujo completo pasan en CI.
8. README, guía de contribución de plugins y documentación DPGA están publicados.

---

## 11. Fuera de alcance (explícito)

Los siguientes elementos **no** están cubiertos por este documento ni por los tickets actuales:

- Multi-tenant (una instancia = un fabricante; el login propio del ADR-0004 liga sesiones a un `user_id` pero **no** aísla por organización).
- OAuth, SSO y federación de identidad con IdP externo. **Sí** existe un login propio mínimo (email + contraseña, sesión server-side en cookie `httpOnly`) descrito en el bloque «Acceso (login)» de §3 — ver [ADR 0004](./adr/0004-login-sesion-server-side-cookie-httponly.md). No sustituye a un sistema de identidad corporativo.
- Federación entre instancias o registro central de DPPs.
- Marketplace de plugins (los plugins se contribuyen vía PR al repo).
- Integración con sistemas ERP / MES del fabricante.
- HRIA (evaluación de impacto en derechos humanos) — evaluado pero descartado para el alcance de la semana.
- PostgreSQL y Redis — descartados explícitamente (ver `ARCHITECTURE.md` §"Decisiones técnicas explícitas").
- LangGraph / LangChain — descartados explícitamente.

---

## 12. Referencias cruzadas

- Arquitectura técnica: [`ARCHITECTURE.md`](./ARCHITECTURE.md)
- Decisiones de arquitectura cerradas: [`adr/`](./adr/) (0001 identificador declarado por el plugin, 0002 vocabulario JSON-LD local, 0003 slug opaco en la URL pública, 0004 login con sesión server-side en cookie httpOnly)
- Tickets por fase: [`tickets/F1.md`](./tickets/F1.md) … [`tickets/F6.md`](./tickets/F6.md)
- Generador de tickets Trello: [`crear_tickets_trello.js`](./crear_tickets_trello.js)
- Reglamentos de referencia:
  - Reglamento UE 2024/1781 (ESPR)
  - Reglamento UE 2023/1542 (baterías) — **Art. 77** establece el pasaporte de batería; **Annex XIII** define las 4 secciones de información con sus niveles de acceso.
  - CIRPASS-2 Core Ontology (marzo 2025) — modelo conceptual de referencia. El sistema usa un vocabulario local interno (`urn:pasaporte-abierto:dpp:v1#`) hasta que el consorcio publique su `@context` HTTP-resolvable; ver [ADR 0002](./adr/0002-jsonld-vocabulario-local.md).
  - GS1 Digital Link specification (esquema de identificador por defecto para sectores sin acto delegado específico)
  - ISO/IEC 15459-1/2/3/4/5/6 (esquema obligatorio para el identificador único de baterías por Art. 77.3 de Reg. UE 2023/1542)
  - Battery Pass Consortium Data Attribute Longlist v1.3 (referencia industrial de implementación; ver `docs/research/battery-pass-v1.3-mandatory-attrs.md`)
