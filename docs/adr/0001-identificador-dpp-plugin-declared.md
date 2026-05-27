# ADR 0001 — Identificador único del DPP declarado por el plugin sectorial

## Estado

**Aceptado** — 2026-05-24

## Contexto

El Pasaporte Digital de Producto (DPP) necesita un **identificador único canónico** que se incrusta en el QR del producto y resuelve a la URL pública del DPP (`GET /dpp/{...}`). La especificación de ese identificador difiere entre actos delegados sectoriales:

- El **Reglamento UE 2023/1542** (baterías), **Art. 77.3** —que aplica a baterías LMT, industriales >2 kWh y de vehículos eléctricos desde el 18 de febrero de 2027— obliga literalmente a que *"el código QR y el identificador único deberán cumplir las normas **ISO/IEC 15459-1:2014, 15459-2:2015, 15459-3:2014, 15459-4:2014, 15459-5:2014 y 15459-6:2014** o sus equivalentes"*.
- El **Reglamento UE 2024/1781** (ESPR), marco general, **no fija** un esquema de identificador único: lo delega a cada acto delegado sectorial. Hasta que cada sector publique su acto delegado específico, **GS1 Digital Link** es el esquema de facto en la industria (recomendado por CIRPASS-2 y adoptado por los pilotos europeos).

La versión inicial de `docs/ARCHITECTURE.md` (mayo 2026) describía "GS1 Digital Link" como esquema único del proyecto. Eso contradice directamente el Art. 77.3 para el sector más importante de la fase 1 del hackathon (baterías).

La inconsistencia se detectó al validar `plugins/batteries.yaml` contra el texto oficial del Reglamento UE 2023/1542 en sesión 2026-05-24, junto con otras 5 citas erróneas en el plan F1 y la ausencia del modelo de niveles de acceso del Anexo XIII (esta última cubierta en T5.1, no es objeto de este ADR).

## Decisión

**El esquema del identificador único del DPP lo declara cada plugin sectorial, no el núcleo del sistema.**

Concretamente:

- Cada `plugins/<sector>.yaml` incluye un campo `identifier_scheme` con valor en el enum `{gs1_digital_link, iso_iec_15459}`.
- El plugin de baterías (`plugins/batteries.yaml`) declara `identifier_scheme: "iso_iec_15459"` por mandato del Art. 77.3.
- Plugins de sectores cuyo acto delegado todavía no fije un esquema específico mantienen el valor por defecto `gs1_digital_link`.
- La fábrica determinista del paso 7 del wizard (generación del DPP) delega la construcción del URI canónico en la lógica asociada al `identifier_scheme` declarado.
- La columna `gs1_uri` en la tabla `published_dpps` y la ruta pública `GET /dpp/{gs1_uri}` se **conservan como nombres históricos** (origen de la primera iteración del proyecto). Su contenido es ya agnóstico al esquema: la columna almacena cualquier URI emitido por la fábrica, sea conforme ISO/IEC 15459, GS1 Digital Link u otro esquema registrado en el futuro.

## Alternativas consideradas

- **A) GS1 Digital Link único para todo el proyecto.** Descartada: contradice literalmente el Art. 77.3 del Reglamento UE 2023/1542 para baterías. Un DPP de batería conforme con GS1 Digital Link pero no con ISO/IEC 15459 incumple la regulación.

- **B) ISO/IEC 15459 único para todo el proyecto.** Descartada: sobrecarga para sectores cuyo acto delegado no exige específicamente ese esquema (textil, electrónica, mobiliario, etc.). GS1 Digital Link es la base de identidad de producto más extendida en la industria europea y forzar ISO/IEC 15459 sin mandato regulatorio rompe interoperabilidad con sistemas existentes.

- **C) `identifier_scheme` hardcoded en el núcleo del sistema, con `if/else` por sector.** Descartada: viola la invariante de **"extensibilidad por configuración"** establecida en `docs/ARCHITECTURE.md` §"Principios de diseño". Añadir un sector ESPR debe consistir en dropear un YAML en `plugins/`, no en modificar el núcleo. Acoplarse a un identifier scheme concreto en el núcleo obliga a redeploys y rompe la promesa de contribución comunitaria documentada en F6-04.

- **D) Renombrar la columna `gs1_uri` y la ruta pública.** Descartada: rompería compatibilidad con clientes ya existentes (QRs ya emitidos en la fase de prototipado, tests E2E de F6-02, ejemplos del README) sin aportar valor técnico. El campo es un string; su nombre histórico no condiciona su contenido. Una migración de renombre puede plantearse post-hackathon si surge necesidad real.

## Consecuencias

**Positivas:**

- El proyecto cumple Art. 77.3 del Reg. UE 2023/1542 para baterías sin recompilar nada — basta con que `plugins/batteries.yaml` declare `identifier_scheme: "iso_iec_15459"`.
- Cumple el principio de "extensibilidad por configuración": añadir un sector con su propio esquema (CEN/CENELEC publicará variantes en los actos delegados específicos de cada sector hasta 2030) consiste en un nuevo `identifier_scheme` en el enum y la lógica de su fábrica, sin tocar lógica de negocio.
- La responsabilidad regulatoria del identificador queda **en el plugin**, donde vive la cita normativa concreta. El núcleo no necesita conocer regulaciones sectoriales.
- Sienta precedente para futuras dimensiones plugin-declared (formato de firma Ed25519 vs alternativas, tipos de documentos sectoriales adicionales, validaciones cruzadas específicas, etc.).

**Neutras:**

- El nombre `gs1_uri` queda como artefacto histórico en BD y API. Documentado explícitamente en `docs/ARCHITECTURE.md` §"Identificador único y niveles de acceso del DPP" y en `docs/FUNCIONAL.md` §5. Aceptable mientras esté documentado.

**Negativas:**

- Cada nuevo `identifier_scheme` en el enum requiere añadir su lógica de generación al núcleo (la fábrica del paso 7). No es extensión pura por YAML; el sector con esquema completamente nuevo necesita PR al núcleo. Mitigado por (a) los esquemas mandatorios conocidos son pocos (~3-5 horizonte 2030), (b) cada adición es ~30 LoC bien encapsuladas, (c) los tests del schema (T5.1) ya rechazan esquemas desconocidos con mensaje en castellano.
- Validar `identifier_scheme: "iso_iec_15459"` solo verifica que el plugin **declara** el esquema correcto; no verifica que el URI generado **cumpla** las 6 normas ISO/IEC 15459-N citadas. Esa verificación material (formato del prefijo, código de país, sintaxis del serial) queda pendiente para la fábrica del paso 7 cuando se implemente en F5.

## Referencias

- **Reglamento UE 2023/1542**, Art. 77.3 (texto oficial DOUE L 191/28.7.2023, pág. 72-73). Descargable desde [EUR-Lex CELEX:32023R1542](https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32023R1542).
- **Reglamento UE 2024/1781** (ESPR), marco general que delega el identificador a actos delegados sectoriales.
- **GS1 Digital Link specification**, esquema de identificador por defecto para sectores sin acto delegado específico (https://www.gs1.org/standards/gs1-digital-link).
- **ISO/IEC 15459-1:2014 a -6:2014**, normas citadas literalmente en Art. 77.3 para baterías.
- `docs/ARCHITECTURE.md` §"Identificador único y niveles de acceso del DPP".
- `docs/FUNCIONAL.md` §1, §3 paso 7, §5, §6.
- `docs/tickets/F1.md` F1-03 acceptance criterion #4.
- `docs/research/battery-pass-v1.3-mandatory-attrs.md` §"Hallazgos nuevos detectados solo con el texto oficial" punto 1.
- Commits que materializan la decisión:
  - `8918d94` — `docs: alinea F1 con Art. 77 y Annex XIII del Reg. UE 2023/1542` (alineación de toda la documentación con el texto oficial).
  - `043cd76` — `feat(plugins): añade access_level + identifier_scheme al schema (F1-03)` (introducción del `IdentifierScheme` Literal en el loader).
  - `09f6b54` — `feat(plugins): plugin baterías conforme Anexo XIII (F1-03)` (primer uso de `identifier_scheme: iso_iec_15459`).

---

*Este ADR sigue el formato propuesto por Michael Nygard ("Documenting Architecture Decisions", 2011). Es el primero del proyecto y sienta la convención: archivos numerados `0001-`, `0002-`… en `docs/adr/`, una decisión por archivo, formato Estado / Contexto / Decisión / Alternativas / Consecuencias / Referencias.*
