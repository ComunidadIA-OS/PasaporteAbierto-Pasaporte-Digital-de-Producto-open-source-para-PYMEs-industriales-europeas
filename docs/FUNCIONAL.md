# Especificación funcional · PasaporteAbierto

Versión 1.0 · Última actualización: 22 mayo 2026

Documento funcional del sistema PasaporteAbierto. Acompaña al documento de [arquitectura](./ARCHITECTURE%20%281%29.md) y a los tickets del [board Trello](./tickets/) (carpeta `tickets/`). El documento describe **qué hace** el sistema desde el punto de vista del usuario y **cómo se comporta** desde el punto de vista del equipo dev. Para decisiones técnicas (stack, patrones, descartes), ver `ARCHITECTURE.md`.

---

## 1. Objetivo y alcance

PasaporteAbierto es una **aplicación web auto-hospedable** que ayuda a fabricantes PYME a generar el **Pasaporte Digital de Producto (DPP)** exigido por el Reglamento UE 2024/1781 (ESPR), sin depender de SaaS propietario.

El alcance del hackathon (1 semana, 6 fases) cubre:

- Wizard guiado de 7 pasos para registrar un producto y generar su DPP.
- Pipeline IA con dos componentes acotados (Clasificador y Recolector) y todo lo demás determinista.
- Chat lateral normativo con cita obligatoria.
- Generación del DPP en JSON-LD CIRPASS-2 Core, QR resoluble vía GS1 Digital Link, endpoint público con content negotiation.
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
- **Código QR** descargable (PNG y SVG).
- **URL pública** del DPP (basada en GS1 Digital Link).
- Confirmación de **firma Ed25519** (si se activó).

**Qué hace el sistema:**
1. Ensambla el DPP en **JSON-LD CIRPASS-2 Core** (marzo 2025).
2. Genera el identificador **GS1 Digital Link** canónico.
3. Genera el QR con `segno`.
4. Opcionalmente firma con Ed25519 (PyNaCl), persistiendo la clave pública.
5. Persiste en `published_dpps`.
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

**Qué hace el sistema:** ensambla prompt con (a) contexto del wizard, (b) top-k del retrieval, (c) pregunta. Loguea la conversación completa en Langfuse.

---

## 5. DPP público

El DPP generado es accesible vía URL canónica (GS1 Digital Link). El endpoint `GET /dpp/{gs1_uri}` aplica **content negotiation**:

| Header `Accept` | Respuesta |
|---|---|
| `application/ld+json` | JSON-LD CIRPASS-2 Core válido (consumido por máquinas, auditores, agregadores). |
| `text/html` (default navegador) | Página HTML legible en móvil, con campos verificados destacados visualmente. |

La página HTML diferencia visualmente **verified vs self_declared** para que el consumidor entienda la calidad del dato.

---

## 6. Plugins (contrato funcional)

Cada plugin es un **YAML** en `plugins/`. Define:
- **Identidad del plugin**: nombre del sector, reglamento aplicable, versión.
- **Campos del DPP**: nombre, tipo, obligatoriedad, cita normativa, regla de validación opcional.
- **Documentos requeridos**: tipo (datasheet, certificado, LCA, SDS, declaración CE) y condición de obligatoriedad.
- **Reglas adicionales**: validaciones cruzadas entre campos (ej. SoC mínimo, vida útil mínima).

El sistema valida cada plugin contra `plugins/_schema.yaml` al arrancar. **Un plugin que no cumpla el schema no se carga**.

**Cobertura del hackathon:**
- `plugins/batteries.yaml` (F1-03) — Reglamento UE 2023/1542.
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
| chat | POST | `/sessions/{id}/chat` | IA | respuesta con cita |
| público | GET | `/dpp/{gs1_uri}` | det | JSON-LD o HTML según `Accept` |
| audit | GET | `/audit/verify` | det | `{ ok, broken_at? }` |
| health | GET | `/health` | det | `{ version, model, backend }` |

---

## 9. Estados funcionales de los campos

Definición canónica de los tres estados que aparecen en la UI y en `extracted_fields.provenance`:

| Estado | UI | Cuándo se asigna |
|---|---|---|
| `verified` | 🟢 verde | El campo aparece tanto en el BOM del paso 3 **como** en un PDF subido, y el Recolector ha podido cruzar ambas fuentes con éxito. |
| `self_declared` | 🟠 naranja | El campo aparece **solo** en el BOM, **o solo** en un PDF, sin verificación cruzada. |
| `required_pending` | 🔴 rojo | Campo declarado obligatorio por el plugin del sector, sin dato disponible ni en BOM ni en PDFs. **Bloquea publicación**. |

---

## 10. Definición de "hecho" (criterios globales de aceptación)

Al cierre del hackathon, el sistema debe cumplir simultáneamente:

1. `docker compose up` levanta toda la solución en una máquina nueva en ≤30 minutos siguiendo solo el README.
2. Un fabricante PYME completa el wizard de 7 pasos con datos demo de un producto del sector baterías y obtiene su DPP publicado en ≤15 minutos.
3. El DPP resultante es accesible vía URL pública y vía QR, y pasa la validación de schema CIRPASS-2 Core.
4. El chat responde con cita normativa al 100 % de las preguntas del set de referencia, y se niega correctamente fuera de dominio.
5. Existen al menos dos plugins funcionales (`batteries.yaml`, `textile.yaml`) cargados desde YAML sin tocar el núcleo.
6. La integridad del audit log es verificable end-to-end.
7. Los tests E2E del flujo completo pasan en CI.
8. README, guía de contribución de plugins y documentación DPGA están publicados.

---

## 11. Fuera de alcance (explícito)

Los siguientes elementos **no** están cubiertos por este documento ni por los tickets actuales:

- Multi-tenant (una instancia = un fabricante).
- OAuth y SSO (basic auth si se necesita exponer en red local).
- Federación entre instancias o registro central de DPPs.
- Marketplace de plugins (los plugins se contribuyen vía PR al repo).
- Integración con sistemas ERP / MES del fabricante.
- HRIA (evaluación de impacto en derechos humanos) — evaluado pero descartado para el alcance de la semana.
- PostgreSQL y Redis — descartados explícitamente (ver `ARCHITECTURE.md` §"Decisiones técnicas explícitas").
- LangGraph / LangChain — descartados explícitamente.

---

## 12. Referencias cruzadas

- Arquitectura técnica: [`ARCHITECTURE (1).md`](./ARCHITECTURE%20%281%29.md)
- Tickets por fase: [`tickets/F1.md`](./tickets/F1.md) … [`tickets/F6.md`](./tickets/F6.md)
- Generador de tickets Trello: [`crear_tickets_trello.js`](./crear_tickets_trello.js)
- Reglamentos de referencia:
  - Reglamento UE 2024/1781 (ESPR)
  - Reglamento UE 2023/1542 (baterías)
  - CIRPASS-2 Core Ontology (marzo 2025)
  - GS1 Digital Link specification
