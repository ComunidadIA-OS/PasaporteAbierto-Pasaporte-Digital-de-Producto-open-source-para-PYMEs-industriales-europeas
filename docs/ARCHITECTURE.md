# Arquitectura de PasaporteAbierto

Versión 1.0 · Última actualización: 18 mayo 2026

PasaporteAbierto es una aplicación web auto-hospedable que ayuda a fabricantes PYME a generar el Pasaporte Digital de Producto (DPP) exigido por el Reglamento UE 2024/1781 (ESPR). Este documento describe la arquitectura del sistema y los contratos entre sus componentes.

## Principios de diseño

La arquitectura se construye sobre tres principios.

Primero, IA donde aporta, código donde basta. Solo dos pasos del pipeline son agénticos: el Clasificador (entiende la descripción en lenguaje natural y la asocia a un sector y acto delegado) y el Recolector (extrae datos no estructurados de fichas técnicas en PDF). Toda la lógica de validación, generación del DPP, firma criptográfica y publicación es código determinista cubierto por tests unitarios. Esto reduce la superficie de fallo a dos puntos bien acotados.

Segundo, el chat ayuda, no suplanta. Hay un asistente conversacional separado del pipeline que el fabricante puede consultar en cualquier momento. Tiene dos límites duros: nunca escribe en el formulario del wizard (el dato siempre lo introduce el fabricante), y nunca responde sin cita normativa concreta (artículo más reglamento). Si no encuentra una cita relevante en el corpus, responde que no tiene información suficiente.

Tercero, extensibilidad por configuración. Cada acto delegado ESPR se modela como un archivo YAML en el directorio `plugins/`. Añadir cobertura de un nuevo sector no requiere modificar el núcleo del sistema: basta con contribuir un nuevo plugin YAML. La Comisión Europea publicará actos delegados sectoriales progresivamente hasta 2030, y la arquitectura está diseñada para que la comunidad open source pueda absorber esa cadencia regulatoria sin intervención del equipo del núcleo.

## Pipeline del wizard

El flujo del usuario consta de siete pasos en cadena. Cada paso es un endpoint del backend y una ruta del frontend, garantizando alineamiento entre la UX y la API.

Paso 1, descripción libre. Determinista. El fabricante escribe en lenguaje natural una descripción del producto que quiere registrar.

Paso 2, clasificación. IA. El agente Clasificador analiza la descripción contra el corpus regulatorio europeo (RAG sobre los reglamentos ESPR y baterías y los actos delegados publicados) y devuelve el sector identificado, el plugin aplicable, los campos requeridos y la cita regulatoria que justifica la clasificación.

Paso 3, formulario BOM. Determinista. El frontend renderiza dinámicamente un formulario adaptado al sector según los campos definidos en el plugin YAML. Los datos se validan con Pydantic y se persisten.

Paso 4, documentos necesarios. Determinista. A partir del BOM introducido y del plugin del sector, el sistema calcula qué fichas técnicas y certificados necesita el Recolector para completar el DPP. Devuelve la lista al usuario, que sube los PDFs correspondientes.

Paso 5, extracción. IA. El agente Recolector lee los PDFs subidos con un pipeline híbrido: pdfplumber para texto estructurado y LLM para campos en lenguaje natural. Marca cada campo extraído con uno de tres estados: verificado (el PDF confirma un dato del BOM, badge verde), auto-declarado (el dato existe en el formulario o en el PDF pero sin verificación cruzada, badge naranja) o pendiente (campo obligatorio del plugin sin dato disponible, badge rojo). El Recolector no inicia diálogo con el usuario: termina su trabajo, actualiza el estado de la sesión y devuelve el control al wizard. El frontend muestra el estado completo de los campos y el fabricante decide cómo resolver los pendientes: rellenar a mano, subir otro PDF que contenga el dato, o consultar al chat lateral. Esta separación de responsabilidades mantiene el control en el fabricante y simplifica el código del Recolector, que no carga con lógica conversacional.

Paso 6, verificación. Determinista. El Verificador valida el DPP completo contra el schema del plugin más las reglas adicionales definidas en el YAML. Devuelve el estado de completitud, la lista de campos faltantes y las advertencias. Si la información obligatoria está incompleta, el sistema bloquea la publicación: no se puede emitir un DPP parcial conforme.

Paso 7, generación del DPP. Determinista. Una vez validados los datos, el sistema ensambla un documento JSON-LD con vocabulario local bajo el namespace URN `urn:pasaporte-abierto:dpp:v1#` —alineado con el modelo conceptual CIRPASS-2 Core (marzo 2025) y emitiendo cada campo como `{value, provenance}`— hasta que el consorcio publique un `@context` HTTP-resolvable estable (ver `docs/adr/0002-jsonld-vocabulario-local.md`); genera el identificador único del DPP conforme al esquema declarado por el plugin sectorial (ISO/IEC 15459-1/2/3/4/5/6 para baterías por el Art. 77.3 del Reglamento UE 2023/1542; GS1 Digital Link como esquema por defecto para sectores sin acto delegado específico de identificador), el código QR resoluble, la página HTML pública con content negotiation, y opcionalmente firma el conjunto con Ed25519 usando la clave del fabricante.

## Identificador único y niveles de acceso del DPP

El identificador único del DPP **lo declara el plugin sectorial**, no el núcleo. La razón es regulatoria: el Art. 77.3 del Reglamento UE 2023/1542 obliga a que el QR y el identificador único de un pasaporte de batería cumplan ISO/IEC 15459-1/2/3/4/5/6 o equivalentes; el Reglamento UE 2024/1781 (ESPR) deja la elección abierta a cada acto delegado sectorial y, hasta que llegue uno específico, GS1 Digital Link es el esquema de facto en la industria. El núcleo del sistema delega la generación del URI en una pequeña fábrica determinista parametrizada por el campo `identifier_scheme` que cada plugin declara. El `gs1_uri` se persiste en la columna del mismo nombre en `published_dpps` y se expone en el cuerpo del DPP (`@id` del JSON-LD, página HTML). La URL pública, en cambio, usa un slug opaco derivado del `session_id` porque ni el URN ISO/IEC 15459 ni la URL externa GS1 Digital Link son adecuados como segmento de ruta servida por el backend; ver `docs/adr/0003-url-publica-slug-opaco.md`.

El Anexo XIII del Reglamento UE 2023/1542 define **cuatro niveles de visibilidad** para los campos del DPP de batería: público general (Sección 1, 19 ítems), accesible solo a personas con interés legítimo y a la Comisión sobre el modelo (Sección 2, 4 ítems), accesible solo a organismos notificados y autoridades de vigilancia del mercado (Sección 3, 1 ítem), y datos accesibles a interés legítimo sobre una batería individual concreta (Sección 4, 4 ítems, dinámicos). Esta dimensión es **ortogonal al estado de provenance** del campo (`verified` / `self_declared` / `required_pending`). Cada campo del plugin declara su `access_level` con uno de los valores `public`, `legitimate_interest`, `authorities_only`, `individual`. Para sectores cuyo acto delegado todavía no fije esta dimensión, el plugin puede mantener el valor por defecto `public`. El endpoint público `GET /dpp/{slug}` filtra los campos según el `access_level` del solicitante: en el alcance del hackathon solo se devuelve el subconjunto `public`; los niveles restringidos quedan habilitados por la columna del campo en `extracted_fields` y por endpoints específicos planificados para fases posteriores.

## Chat lateral

Endpoint independiente del pipeline, accesible en cualquier momento de la sesión. Cada respuesta se construye con tres entradas: el contexto del wizard (paso actual, sector clasificado, campos rellenos y campos pendientes), el contexto RAG (los top-k fragmentos del corpus relevantes a la pregunta) y la pregunta del usuario. Las tres entradas se ensamblan en un prompt que exige al modelo una respuesta corta y una cita normativa concreta.

Si el RAG no devuelve fragmentos relevantes, el chat responde "no tengo información suficiente para responder con base normativa". El chat nunca escribe en el estado del wizard.

## Capa de datos y conocimiento

El corpus RAG es **exclusivamente normativo**: contiene el Reglamento UE 2024/1781 (ESPR), el Reglamento UE 2023/1542 (baterías) y los actos delegados publicados a fecha de despliegue, descargados como texto oficial vía el repositorio Cellar de la Oficina de Publicaciones (`publications.europa.eu/resource/celex/{celex}` con content negotiation; el endpoint `legal-content` de EUR-Lex aplica anti-scraping y responde 202 vacío a clientes no-navegador). El corpus se chunca por estructura legal (artículo y apartado, con el epígrafe del artículo como contexto), se embebe con bge-m3 (modelo multilingüe que permite consulta en castellano, inglés, francés, portugués y alemán) y se indexa en ChromaDB embebido. Su única razón de ser es dar **cita normativa**: cada fragmento es citable como "Reglamento X, Art. Y".

El esquema del identificador único (ISO/IEC 15459, GS1 Digital Link) y el vocabulario del DPP (modelo conceptual CIRPASS-2 Core) **no** forman parte del corpus RAG —no son texto citable como ley—: los declara el plugin sectorial (`identifier_scheme`, campos con su cita) y los consume de forma determinista la generación del DPP (paso 7). El `@context` JSON-LD emitido es local hasta que el consorcio publique uno HTTP-resolvable estable (ver `docs/adr/0002-jsonld-vocabulario-local.md`).

El directorio `plugins/` contiene un archivo YAML por sector. Cada plugin describe los campos del DPP, los documentos requeridos, las validaciones adicionales y las citas regulatorias asociadas. El formato del plugin está documentado en `plugins/_schema.yaml`.

El router de modelos (LiteLLM) abstrae el backend de LLM. Una única variable de entorno `MODEL_BACKEND` permite alternar entre Ollama local (Qwen 2.5 14B o Llama 3.1 8B en Apple Silicon) y APIs comerciales (Claude, GPT, Gemini), sin recompilación ni cambios en el resto del código.

La observabilidad se construye con Langfuse self-hosted. Cada decisión del Clasificador, del Recolector y del chat se registra con traza completa: prompt enviado, modelo utilizado, tokens, latencia y resultado. El audit log adicional escribe cada operación significativa (clasificación, validación, generación de DPP, firma) en SQLite con encadenamiento de hashes: cada entrada contiene un hash de la entrada anterior, lo que permite detectar manipulación posterior.

## API

Casi todas las rutas usan el prefijo `/api/v1`; la excepción es la ruta pública `/dpp/{slug}`, que se monta directamente en la app (es la URL navegable que codifica el QR).

| Paso | Método | Endpoint | Tipo |
|---|---|---|---|
| 1 · descripción | POST | /sessions | det |
| 2 · clasificación | POST | /sessions/{id}/classify | IA |
| 3 · BOM | PUT | /sessions/{id}/bom | det |
| 4a · listar docs | GET | /sessions/{id}/documents | det |
| 4b · subir docs | POST | /sessions/{id}/documents | det |
| 5 · extracción | POST | /sessions/{id}/extract | IA |
| 6 · verificación | GET | /sessions/{id}/verify | det |
| 7 · DPP | POST | /sessions/{id}/dpp | det |
| chat | POST | /chat | IA |
| chat · histórico | GET | /sessions/{id}/chat | det |
| auth · registro | POST | /auth/register | det |
| auth · login | POST | /auth/login | det |
| auth · logout | POST | /auth/logout | det |
| auth · identidad | GET | /auth/me | det |
| audit | GET | /audit/verify | det |
| pública | GET | /dpp/{slug} | det |

El chat lateral recibe el `session_id` en el cuerpo de la petición (no en la ruta), de modo que el endpoint es `POST /chat` y no `POST /sessions/{id}/chat`; el histórico persistido se recupera con `GET /sessions/{id}/chat`. La ruta pública `/dpp/{slug}` queda **fuera** del prefijo `/api/v1` (se monta directamente en la app) porque es la URL navegable que codifica el QR.

El endpoint público de DPP usa content negotiation: si el cliente envía `Accept: application/ld+json` devuelve el JSON-LD, si envía `Accept: text/html` devuelve la página renderizada para humanos. El segmento `{slug}` es un identificador opaco derivado del `session_id` (primeros 8 caracteres del UUID); el `gs1_uri` canónico declarado por el plugin sectorial aparece dentro del cuerpo del DPP (campo `@id` del JSON-LD) y en la página HTML, no en la URL. La motivación —URN ISO/IEC 15459 no resoluble por HTTP, GS1 Digital Link apunta a un dominio externo— está documentada en `docs/adr/0003-url-publica-slug-opaco.md`.

Para operaciones largas (extracción de PDFs grandes, indexado de nuevos documentos) el backend emite progreso vía Server-Sent Events, lo que permite al frontend mostrar las trazas de los agentes en tiempo real durante la demo.

## Persistencia

Una única base SQLite por instancia, con ocho tablas: las cinco del pipeline (`sessions`, `documents`, `extracted_fields`, `audit_log`, `published_dpps`), la del histórico de chat (`chat_messages`) y las dos del login (`users`, `auth_sessions`, añadidas por el ADR-0004).

La tabla `sessions` guarda el estado del wizard: identificador único, JSON con el progreso paso a paso, sector clasificado, plugin aplicable, timestamps de creación y última modificación. Incluye un `user_id` **nullable** (FK a `users`) que implementa la propiedad blanda de sesiones del ADR-0004: una sesión sin dueño es accesible, pero una con dueño solo la lee su propietario.

La tabla `documents` guarda los PDFs subidos: referencia a la sesión, tipo de documento (datasheet, certificado, LCA, SDS, declaración CE), ruta al blob y hash SHA-256 del archivo.

La tabla `extracted_fields` guarda los campos que el Recolector ha extraído: referencia a la sesión, identificador del campo, valor, documento fuente, provenance (verified, self_declared o required_pending) y confianza estimada.

La tabla `audit_log` implementa el hash chain: identificador incremental, hash de la entrada anterior, hash del contenido actual, timestamp, operación y payload JSON. La integridad se verifica recorriendo la cadena desde la primera entrada.

La tabla `published_dpps` guarda los DPPs ya emitidos: la columna `gs1_uri` almacena el URI canónico del pasaporte —cuya forma sigue el esquema declarado por el plugin sectorial (ISO/IEC 15459 para baterías, GS1 Digital Link como fallback genérico, u otro esquema registrado por un plugin futuro)—, blob JSON-LD, firma Ed25519, fecha de publicación y referencia a la clave pública del fabricante. La URL pública del DPP no usa la columna `gs1_uri` como segmento de ruta: deriva un slug opaco del `session_id` (ver `docs/adr/0003-url-publica-slug-opaco.md`). El `gs1_uri` queda disponible para búsqueda inversa (recuperar un DPP dado su identificador canónico) y se expone dentro del cuerpo del JSON-LD.

La tabla `chat_messages` guarda el histórico del chat lateral por sesión (rol `user`/`assistant`, contenido, cita normativa opcional, timestamp). Es un **canal independiente del estado del wizard**: persistir la conversación permite reanudarla tras un refresh sin que el chat escriba nunca en `sessions`, `extracted_fields` ni `documents`.

La tabla `users` guarda las cuentas del login propio (ADR-0004): identificador, email único y hash de contraseña con `scrypt` (parámetros embebidos en el digest). Nunca almacena la contraseña en claro.

La tabla `auth_sessions` guarda las sesiones server-side: identificador, `user_id`, **SHA-256 del token** (no el token en claro), y timestamps de creación, expiración y último acceso. El token viaja al cliente en una cookie `httpOnly`; guardar solo su hash evita que una fuga de la BD entregue sesiones reutilizables, y la fila se puede borrar para revocar (logout, expiración).

## Stack técnico

Backend: FastAPI 0.115 sobre Python 3.11. Validación con Pydantic v2. Persistencia con SQLite vía SQLModel. Vector store con ChromaDB embebido. Embeddings con bge-m3 vía sentence-transformers. Router de modelos con LiteLLM. Modelo local con Ollama (Qwen 2.5 14B como referencia primaria, Llama 3.1 8B como alternativa más ligera). PDF parsing con pdfplumber complementado con LLM. Generación de QR con segno. Firmado Ed25519 con PyNaCl. Observabilidad con Langfuse self-hosted.

Frontend: Next.js 16 con App Router, TypeScript estricto, Tailwind CSS, componentes de shadcn/ui. React Hook Form para los formularios dinámicos generados desde los plugins.

Despliegue: Docker Compose con cuatro servicios (backend, frontend, Langfuse, Ollama opcional si se quiere modelo local en el contenedor). Un solo `docker compose up` arranca el sistema completo en menos de cinco minutos.

Licencia Apache 2.0. Repositorio público en GitHub. CI con GitHub Actions: lint en cada PR, tests unitarios e integración, validación del formato de los plugin YAMLs.

## Decisiones técnicas explícitas

No usamos LangGraph ni LangChain. El pipeline es lineal con dos pasos IA bien acotados. Plain Python con FastAPI endpoints es más simple, más debuggeable, requiere menos dependencias y menos curva de aprendizaje. Para el paralelismo del Recolector (que llama al LLM una vez por PDF de forma independiente) usamos asyncio.gather: consigue el mismo paralelismo que un grafo agentic sin dependencias adicionales ni capa de orquestación. La complejidad de un framework de agentes no se justifica en este caso de uso.

No usamos PostgreSQL ni Redis. El caso de uso objetivo es una instancia por fabricante PYME con uso modesto. SQLite cubre persistencia y FastAPI BackgroundTasks cubre asincronía.

No implementamos multi-tenant ni OAuth en el alcance del hackathon. Una instancia equivale a un fabricante. Sí incorporamos un **login propio mínimo** (email + contraseña, sesión server-side en SQLite, cookie `httpOnly`) que liga las sesiones del wizard y el chat a un `user_id`, de modo que el fabricante recupere sus conversaciones y DPP empezados y que los datos sensibles (BOM, PDFs, chat) no queden accesibles solo por adivinar el UUID de la sesión. Esto **no** es OAuth ni multi-tenant (sin IdP externo, sin aislamiento por organización, sin Postgres/Redis): es la opción acotada que sustituye al "basic auth" que se contemplaba aquí. Decisión, alternativas y reconciliación con este descarte en `docs/adr/0004-login-sesion-server-side-cookie-httponly.md`.

No imponemos un esquema único de identificador del DPP. Cada plugin sectorial declara su `identifier_scheme` (ISO/IEC 15459 para baterías por mandato del Art. 77.3 del Reglamento UE 2023/1542; GS1 Digital Link como esquema por defecto para sectores sin acto delegado específico). La fábrica determinista del paso 7 delega la generación del URI canónico en la lógica del esquema declarado. Esto evita acoplar el núcleo a un estándar concreto que cambia entre actos delegados y deja la responsabilidad regulatoria del identificador en el plugin, que es donde la cita normativa concreta vive.
