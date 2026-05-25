# Cuestionario DPGA — PasaporteAbierto

Documento de evaluación frente a los **9 indicadores del estándar Digital Public Good Alliance** (DPGA). Cada sección referencia la fuente de evidencia dentro del repositorio.

Fuente del estándar: <https://digitalpublicgoods.net/standard/>.

Cobertura al cierre de la fase **F6** del hackathon (2026-05-25).

---

## 1. Relevance to Sustainable Development Goals (SDGs)

PasaporteAbierto contribuye de forma directa a tres ODS de Naciones Unidas:

- **ODS 12 — Producción y consumo responsables** (núcleo del proyecto). El Pasaporte Digital de Producto exigido por el Reglamento UE 2024/1781 (ESPR) hace explícita la trazabilidad de materiales, durabilidad, reparabilidad y reciclabilidad. PasaporteAbierto es la implementación de referencia que permite a PYMEs industriales europeas publicar esa información sin depender de SaaS propietario.
- **ODS 9 — Industria, innovación e infraestructura**. El proyecto reduce la barrera de entrada al cumplimiento ESPR para fabricantes pequeños y medianos (estructura de costes incompatible con suites cerradas de ERP/PLM extendido). Se distribuye como aplicación auto-hospedable (`docker compose up`) y como ecosistema de plugins sectoriales.
- **ODS 13 — Acción por el clima**. El DPP es habilitador de circularidad: alimenta a recicladores, reparadores y autoridades de vigilancia con datos estructurados que hacen factibles cadenas de reciclaje y reutilización. Sin DPP estandarizado, esos datos siguen viviendo en PDFs aislados.

El alcance regulatorio inicial (baterías por Reg. UE 2023/1542, textil como prueba de extensibilidad) cubre dos sectores con impacto ambiental medible.

---

## 2. Use of Approved Open Source License

Licencia: **Apache License 2.0**, aprobada por la OSI (<https://opensource.org/license/apache-2-0>).

Evidencia: archivo [`LICENSE`](../LICENSE) en la raíz del repositorio, con el texto canónico publicado por la Apache Software Foundation. El año de copyright es 2026 y el holder es `PasaporteAbierto contributors`, fórmula comunitaria habitual para proyectos sin una entidad legal única.

La elección de Apache 2.0 frente a alternativas más permisivas (MIT/BSD) está motivada por la cláusula explícita de licencia de patentes, especialmente relevante en un dominio que toca estándares industriales (ISO/IEC 15459, GS1 Digital Link).

---

## 3. Clear Ownership

El repositorio es **comunitario**: el copyright vive distribuido entre las personas que contribuyen al código, conforme al Apache 2.0 §5 ("Submission of Contributions").

Mantenedores actuales al cierre del hackathon (inferidos del histórico de commits sin merges):

- Malen Aguirre — 36 commits — co-mantenedora principal.
- Mencía González — 14 commits — co-mantenedora.

El proyecto no cuenta todavía con un `MAINTAINERS.md` separado; este apartado actúa como referencia provisional hasta que se formalice. Los issues y PRs en GitHub son el canal oficial de gobernanza durante el hackathon.

---

## 4. Platform Independence

PasaporteAbierto se despliega en cualquier máquina capaz de ejecutar Docker 24+. Stack documentado en [`ARCHITECTURE.md`](./ARCHITECTURE.md):

- Backend: Python 3.11, FastAPI 0.115, Pydantic v2, SQLModel sobre SQLite.
- Frontend: Node 20, Next.js 16 con App Router, TypeScript estricto.
- Persistencia: SQLite local (un fichero `.db` por instancia). No requiere Postgres ni Redis para la aplicación; Postgres aparece únicamente como dependencia interna de Langfuse self-hosted, sin puerto expuesto.
- Orquestación: `docker compose up`.

**Sin dependencias de SaaS propietario.** El backend de modelos de IA es intercambiable vía la variable de entorno `MODEL_BACKEND` mediante LiteLLM como router universal: la misma instancia puede correr `ollama:qwen2.5:14b` localmente (sin internet, sin coste por token) o `anthropic:claude-...`, `openai:gpt-...`, `groq:...`, etc. Ningún proveedor concreto es obligatorio.

La observabilidad (Langfuse) también es self-hosted dentro del mismo `docker-compose.yml`.

---

## 5. Documentation

Documentación principal del proyecto, toda dentro del repositorio:

- [`README.md`](../README.md) — visión general, quickstart en ≤30 min, comandos de desarrollo.
- [`docs/FUNCIONAL.md`](./FUNCIONAL.md) — especificación funcional completa, UX paso a paso, reglas duras del producto.
- [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md) — arquitectura técnica, contratos entre componentes, decisiones de stack y descartes razonados.
- [`docs/plugins.md`](./plugins.md) — guía de contribución de plugins sectoriales.
- [`docs/adr/`](./adr/) — Architecture Decision Records (identificador del DPP por plugin, vocabulario JSON-LD local, URL pública con slug opaco).
- [`docs/tickets/`](./tickets/) — tickets de las 6 fases del hackathon con criterios de aceptación.
- `CLAUDE.md` — convenciones del proyecto (commits, idioma, invariantes arquitectónicas).

Toda la documentación funcional y los mensajes de UI están en castellano; las citas normativas conservan el idioma original del reglamento (mayoritariamente español/inglés). El código y los commits siguen Conventional Commits en castellano.

---

## 6. Mechanism for Extracting Data

El proyecto está diseñado para que los datos sean **exportables y portables** desde el primer día:

- **DPP publicado**: el endpoint público `GET /dpp/{slug}` aplica content negotiation (RFC 7231 §5.3.2). Con `Accept: application/ld+json` devuelve el DPP en JSON-LD con vocabulario local (`urn:pasaporte-abierto:dpp:v1#`) alineado con CIRPASS-2 Core; con `Accept: text/html` devuelve la página renderizada para el consumidor.
- **Audit log**: `GET /api/v1/audit/verify` recorre la cadena hash del log y reporta integridad; las filas individuales son consultables por API.
- **Datos del fabricante**: SQLite es un único fichero (`backend/data/pasaporteabierto.db`) trivialmente exportable, copiable y migrable. Sin lock-in de schema.
- **Corpus normativo**: los fragmentos RAG se almacenan como JSONL en `backend/data/corpus/{slug}.{lang}.jsonl`, formato estándar inspeccionable con cualquier editor.

No hay formatos propietarios. Todo lo serializable es JSON-LD, JSONL, SQLite o Markdown.

---

## 7. Adherence to Privacy and Applicable Laws

**Sin recopilación de PII por defecto.** El DPP cubre datos del **producto** del fabricante (composición, durabilidad, reciclabilidad, proveedores aguas arriba), no datos del consumidor final.

Garantías de privacidad por diseño:

- El endpoint público `GET /dpp/{slug}` expone únicamente campos con `access_level: public` (Sección 1 del Annex XIII del Reg. UE 2023/1542). Los otros tres niveles (`legitimate_interest`, `authorities_only`, `individual`) quedan fuera del HTML público. Ver [`FUNCIONAL.md` §9.2](./FUNCIONAL.md).
- No hay multi-tenant ni OAuth: una instancia = un fabricante; los datos viven en su propia instancia bajo su control.
- La aplicación no integra trackers de terceros ni telemetría hacia servidores externos.

Cumplimiento regulatorio:

- **GDPR-friendly** por ausencia de PII en el dato canónico publicado.
- **ESPR (Reg. UE 2024/1781)**: el DPP generado sigue la estructura del acto delegado aplicable; cuando no exista acto delegado, el plugin sectorial declara `access_level` por campo e `identifier_scheme` por defecto (GS1 Digital Link).

El fabricante es responsable de la veracidad de los datos. PasaporteAbierto marca explícitamente la diferencia entre `provenance: verified` (con PDF de respaldo y hash SHA-256) y `provenance: self_declared` (sin soporte documental); no oculta esa distinción al consumidor.

---

## 8. Adherence to Standards & Best Practices

Estándares y prácticas adoptados, todos documentados en el repositorio:

- **Licencia**: Apache 2.0 (OSI-approved).
- **Versionado de plugins**: SemVer; un test de contrato (`tests/plugins/test_contract.py`) lo enforza al cargar cada YAML.
- **Identificador único del DPP**:
  - **ISO/IEC 15459** para baterías (Art. 77.3 del Reg. UE 2023/1542).
  - **GS1 Digital Link 1.3.0** como fallback genérico para sectores sin acto delegado específico. Ver [ADR 0001](./adr/0001-identificador-dpp-plugin-declared.md).
- **Serialización del DPP**: JSON-LD alineado con el modelo conceptual de CIRPASS-2 Core (marzo 2025), con vocabulario local hasta que el consorcio publique `@context` HTTP-resolvable estable. Ver [ADR 0002](./adr/0002-jsonld-vocabulario-local.md).
- **Firma criptográfica**: Ed25519 (PyNaCl) sobre el JSON-LD canónico del DPP; clave pública por fabricante persistida en `published_dpps`.
- **Integridad del audit log**: hash chain con SHA-256, verificable vía `GET /api/v1/audit/verify`.
- **Convenciones de código**: Conventional Commits en castellano (ver `CLAUDE.md`), Ruff (lint + format) en backend, Biome en frontend.
- **Content negotiation**: RFC 7231 §5.3.2 para el endpoint público del DPP (ADR pendiente sobre tratamiento de q-values).
- **Observabilidad**: Langfuse self-hosted con `@observe` en cada decisión IA (Clasificador, Recolector, Chat); `litellm.completion()` emite spans `generation` automáticamente.

---

## 9. Do No Harm

Riesgos identificados y mitigaciones:

- **Privacidad**: ausencia de PII por diseño (ver §7). El `access_level` por campo evita exponer en el HTML público datos clasificados como `legitimate_interest`, `authorities_only` o `individual`.
- **Mala fe del fabricante**: el sistema **no verifica los datos contra fuentes externas**; lo señala honestamente con `provenance: self_declared`. El audit log con hash chain permite detectar manipulación posterior por la autoridad de vigilancia: cada operación significativa (clasificación, publicación, firma) deja entrada con `prev_hash`.
- **Sesgo y errores de IA**: solo dos pasos del pipeline son IA (Clasificador y Recolector). Cada decisión IA emite traza Langfuse (`@trace_classifier`, `@trace_collector`, `@trace_chat`) y el override manual queda en `audit_log`. **Toda respuesta del Chat exige cita normativa concreta** (`[Reglamento X, Art. Y]`); si el RAG no devuelve fragmentos, la respuesta canónica es "No tengo información suficiente para responder con base normativa". El chat **nunca escribe en el estado del wizard** (§9 `FUNCIONAL.md`).
- **Huella energética**: el operador puede elegir modelo local (Ollama, Qwen 2.5 14B) para reducir huella vs APIs comerciales.
- **Cadena de suministro**: dependencias gestionadas con `uv` y `pnpm`, con lock files commiteados.

El proyecto no procesa contenido generado por consumidores finales ni maneja sus datos personales; no se identifican riesgos materiales fuera de lo cubierto.
