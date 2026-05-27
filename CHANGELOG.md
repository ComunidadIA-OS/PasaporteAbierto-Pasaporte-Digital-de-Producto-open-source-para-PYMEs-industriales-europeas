# Registro de cambios

Todos los cambios notables de PasaporteAbierto se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el
proyecto sigue [Versionado Semántico](https://semver.org/lang/es/).

## [Sin publicar]

### Añadido
- Documentación de comunidad para alinear el repo con las buenas prácticas open source:
  `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1, en castellano),
  `SECURITY.md`, plantillas de issue (bug, mejora, plugin sectorial) y de pull request.
- `CHANGELOG.md`, `CITATION.cff` y configuración de Dependabot.
- Badges y tabla de contenidos en el README.

## [0.1.0] - 2026-05-27

Primera versión pública, entregada en el hackathon. El pipeline de 7 pasos ejecuta
end-to-end sobre el sector de baterías y emite un DPP firmado.

### Añadido
- **Wizard de 7 pasos**: descripción → clasificación (IA) → BOM → documentos →
  extracción (IA, vía SSE) → verificación → generación del DPP.
- **Pasos de IA acotados** a Clasificador (paso 2) y Recolector (paso 5), enrutados por
  LiteLLM (Ollama local o APIs comerciales según `MODEL_BACKEND`). El resto del pipeline es
  código determinista cubierto por tests.
- **Corpus normativo (RAG)** con ChromaDB embebido + embeddings `bge-m3`: ESPR (Reg. UE
  2024/1781), baterías (Reg. UE 2023/1542), actos delegados ESPR, CIRPASS-2 Core, GS1
  Digital Link 1.3.0 e ISO/IEC 15459.
- **Chat normativo lateral** con cita obligatoria (`[Reglamento X, Art. Y]`), independiente
  del estado del wizard.
- **Generación y publicación del DPP**: JSON-LD CIRPASS-2 Core, firma Ed25519 (PyNaCl),
  código QR (segno) y endpoint público con content negotiation
  (`application/ld+json` / `text/html`).
- **Sistema de plugins sectoriales** por YAML validado contra `plugins/_schema.yaml`:
  `batteries.yaml` (Reg. UE 2023/1542) y `textile.yaml` (prueba de extensibilidad).
- **Cuatro niveles de acceso** del DPP conforme al Anexo XIII del Reg. UE 2023/1542
  (`public`, `legitimate_interest`, `authorities_only`, `individual`).
- **Audit log con hash chain** en SQLite y endpoint `GET /api/v1/audit/verify`.
- **Observabilidad** con Langfuse self-hosted (`@observe`).
- Despliegue reproducible con **Docker Compose**, migraciones con **Alembic** y **CI**
  (lint + tests) con GitHub Actions.

[Sin publicar]: https://github.com/ComunidadIA-OS/PasaporteAbierto-Pasaporte-Digital-de-Producto-open-source-para-PYMEs-industriales-europeas/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ComunidadIA-OS/PasaporteAbierto-Pasaporte-Digital-de-Producto-open-source-para-PYMEs-industriales-europeas/releases/tag/v0.1.0
