# ADR 0005 — Licencia Apache 2.0

## Estado

**Aceptada** — 2026-05-27

## Contexto

El proyecto debe publicarse con una licencia de código abierto, y esa elección
no es libre del todo: viene acotada por dos requisitos externos y por el perfil
del producto.

1. **Regla del hackathon** (`.claude/HACKATHON.md`): *"Open source obligatorio.
   Licencia reconocida por OSI o FSF."* Y exige además que las dependencias
   directas sean **compatibles con Apache 2.0** (evitar GPL/AGPL en deps
   directas). El ticket **F6-05** lo fija como criterio de aceptación:
   "repositorio público con licencia OSI aprobada (Apache 2.0)".
2. **Estándar DPGA** (Digital Public Good Alliance): el indicador #2 —*"Use of
   Approved Open Source License"*— exige una licencia de su lista aprobada. El
   proyecto aspira a ser reconocido como Bien Público Digital (`docs/dpga.md`).
3. **Perfil del producto.** El público objetivo son **fabricantes PYME** que
   despliegan la app auto-hospedada y, a menudo, la integrarán en sus propios
   sistemas (posiblemente cerrados). Además el dominio toca **estándares
   industriales patentables** (ISO/IEC 15459 para baterías, GS1 Digital Link),
   donde la exposición a patentes es un riesgo real.

La decisión, por tanto, no es "¿OSS sí o no?" (es obligatorio), sino **qué
licencia OSS aprobada** encaja mejor con un proyecto permisivo, integrable por
PYMEs y anclado a estándares.

## Decisión

**El proyecto se publica bajo la Licencia Apache 2.0** (identificador SPDX
`Apache-2.0`). El texto íntegro y canónico de la Apache Software Foundation está
en [`LICENSE`](../../LICENSE); el aviso de copyright es
`Copyright 2026 PasaporteAbierto contributors` (fórmula comunitaria, sin entidad
legal única).

Razones concretas de elegir Apache 2.0 frente a otras licencias aprobadas:

- **Permisiva → adopción sin fricción por PYMEs.** Permite uso comercial,
  modificación, distribución, sublicencia e **integración en productos
  cerrados**, sin obligar a abrir el derivado.
- **Concesión expresa de patentes (§3) — el diferencial frente a MIT/BSD.** Cada
  contribuidor cede los derechos de patente que cubre su código, y la licencia
  incluye una **cláusula de retorsión**: quien inicie un litigio de patentes
  contra el proyecto pierde la licencia. En un dominio anclado a estándares
  industriales, esa protección importa de verdad.
- **Cumple OSI/FSF y la lista DPGA**, satisfaciendo los dos requisitos externos.
- **Sin garantía ni responsabilidad** ("tal cual"), apropiado para software
  auto-hospedable que cada fabricante opera bajo su control.

## Alternativas consideradas

- **A) MIT / BSD.** Igual de permisivas, pero **no conceden patentes de forma
  expresa**. Para un proyecto que toca estándares patentables, esa laguna es el
  motivo de descarte. Apache 2.0 = "MIT + concesión de patentes".
- **B) GPL / AGPL (copyleft).** Descartadas: imponen *share-alike*, lo que crea
  fricción legal para que una PYME integre el software en un producto cerrado, y
  la AGPL extendería esa obligación al uso en red. Contradice el objetivo de
  adopción amplia; además el hackathon pide evitar GPL/AGPL incluso en
  dependencias directas.
- **C) Propietaria / sin licencia.** Descartada: incumple el requisito de OSS
  del hackathon y del estándar DPGA; "sin licencia" además implica "todos los
  derechos reservados" por defecto, lo contrario de lo buscado.
- **D) CC0 / dominio público.** Descartada: las licencias Creative Commons no
  están pensadas para software (no cubren patentes ni el descargo de garantía de
  forma adecuada) y la propia Creative Commons lo desaconseja para código.

## Consecuencias

**Positivas:**

- Máxima adopción por PYMEs: pueden usar, modificar e integrar el software
  —incluido en productos comerciales/cerrados— sin pedir permiso ni pagar.
- Protección de patentes explícita para usuarios y contribuidores, relevante en
  el contexto normativo/estándares del proyecto.
- Cumple de un plumazo los requisitos OSI del hackathon y el indicador #2 de
  DPGA (evidencia en `docs/dpga.md`).
- Fija una restricción útil aguas abajo: las **dependencias directas deben ser
  compatibles con Apache 2.0** (sin GPL/AGPL), manteniendo el conjunto
  redistribuible.

**Negativas / costes:**

- Obliga a quien redistribuye a **conservar el aviso de copyright y la
  licencia**, **indicar los cambios** en los archivos modificados y mantener el
  `NOTICE` si existe. Coste bajo y estándar.
- El texto **jurídicamente vinculante es el inglés** (la ASF no reconoce
  traducciones); las explicaciones en castellano del `README` son orientativas.
- Los manifiestos de paquete (`frontend/package.json`, `backend/pyproject.toml`)
  **no declaran** aún `license = "Apache-2.0"`; conviene añadirlo para que las
  herramientas (npm/PyPI, SBOM, escáneres) lo reflejen. Es coherencia, no un
  cambio de la decisión.

## Documentación relacionada

- [`LICENSE`](../../LICENSE) — texto canónico de Apache 2.0.
- [`README.md`](../../README.md) §Licencia — qué permite/exige y "por qué Apache".
- [`docs/dpga.md`](../dpga.md) §2 — evidencia para el indicador DPGA.
- `CITATION.cff` — `license: Apache-2.0`.
