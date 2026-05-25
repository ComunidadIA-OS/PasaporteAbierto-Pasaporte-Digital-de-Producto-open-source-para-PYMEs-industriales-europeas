# ADR 0002 — Vocabulario JSON-LD local hasta CIRPASS-2 Core estable

## Estado

**Aceptada** — 2026-05-25

## Contexto

El paso 7 del wizard (`POST /sessions/{id}/dpp`) serializa el estado validado de la sesión como un documento JSON-LD que se persiste en `published_dpps.jsonld` y se sirve por content negotiation en `GET /dpp/{slug}` con `Accept: application/ld+json`. El CA #1 de `docs/tickets/F5.md` (F5-01) pide que ese output **"pase la validación de schema CIRPASS-2 Core sin errores"**.

La realidad de **CIRPASS-2 Core Ontology** (marzo 2025) al cierre de F5 es:

- El consorcio CIRPASS-2 ha publicado el modelo conceptual y la lista de atributos núcleo del DPP, pero **no publica todavía un `@context` JSON-LD HTTP-resolvable estable** ni un schema (SHACL o JSON Schema) de validación canónico.
- Las publicaciones disponibles son documentos PDF y notas técnicas; no hay un endpoint del estilo `https://cirpass2.eu/context/v1.jsonld` resoluble por un procesador JSON-LD estándar.
- Apuntar el `@context` a una URL externa que no resuelve (o que cambiará sin aviso cuando el consorcio publique) rompe la propiedad fundamental de un documento JSON-LD: que un consumidor pueda dereferenciar el contexto para interpretar los términos sin canales fuera de banda.

La versión inicial del documento funcional y del ticket F5-01 hablaban de "JSON-LD CIRPASS-2 Core" como si el `@context` ya existiera. Eso era aspiracional; cumplirlo materialmente no era posible al implementar F5-01.

## Decisión

**El `@context` del DPP usa un namespace URN local: `urn:pasaporte-abierto:dpp:v1#`.**

Concretamente:

- El generador `app.dpp.build_jsonld` declara un `@context` con prefijo `dpp:` apuntando al URN `urn:pasaporte-abierto:dpp:v1#`, y emite los términos del DPP (`DigitalProductPassport`, `sector`, `regulation`, `identifier_scheme`, `fields`, `value`, `provenance`) como CURIEs dentro de ese vocabulario.
- Los URN son identificadores JSON-LD válidos: la especificación JSON-LD 1.1 admite cualquier IRI absoluto como término de un `@context`, sin requerir resolución HTTP. Un consumidor que reciba el documento sabe que dos campos con el mismo URN denotan el mismo concepto, aunque no pueda dereferenciar el namespace.
- El campo `provenance` por campo (`{"value": ..., "provenance": "verified"|"self_declared"}`) sigue siendo nativo del documento — F5-01 CA #2 se cumple sin depender de CIRPASS.
- La estructura interna del DPP queda alineada con el modelo conceptual de CIRPASS-2 (sectores, regulación aplicable, identificador, campos con su procedencia), de forma que cuando el consorcio publique el `@context` HTTP-resolvable la migración consista en swap del namespace, no en rediseño del documento.

## Alternativas consideradas

- **A) Apuntar `@context` a una URL HTTP de CIRPASS-2 anticipándonos a su publicación.** Descartada: prometer una URL que no resuelve es peor que un URN local. Un procesador JSON-LD que intente dereferenciar fallará y un auditor que valide formalmente reportará el documento como roto. Cuando CIRPASS publique, la URL final puede ser distinta de la que adivinamos hoy.

- **B) Embeber el `@context` literal en cada DPP (sin namespace, definiendo todos los términos inline).** Descartada: viable técnicamente, pero infla cada documento publicado con metadatos repetidos y dificulta la migración futura. Un URN como prefijo es más limpio y mantiene la opción de swap a una URL HTTP cuando exista.

- **C) Omitir `@context` y emitir JSON plano.** Descartada: rompe la promesa de FUNCIONAL.md §5 de que `application/ld+json` devuelve **JSON-LD válido** consumible por máquinas. Sin `@context`, el documento no es JSON-LD; es JSON con shape decorativo.

- **D) Esperar a que CIRPASS-2 publique antes de cerrar F5.** Descartada: el alcance del hackathon es una semana, y el calendario del consorcio CIRPASS-2 está fuera de nuestro control. Bloquear F5 hasta entonces deja todo el pipeline sin entregable. Mejor entregar un DPP estructuralmente coherente con vocabulario propio y documentar la deuda regulatoria que prometer interoperabilidad nominal con un schema inexistente.

## Consecuencias

**Positivas:**

- El DPP emitido es un **JSON-LD válido** según JSON-LD 1.1: cualquier procesador estándar puede consumirlo sin errores de resolución de contexto.
- F5-01 CA #2 (`provenance` por campo) se cumple sin depender de CIRPASS.
- La estructura del documento queda lista para migrar a CIRPASS-2 Core cuando exista: la decisión es **reversible** con cambio acotado al `@context` (no a la lógica de generación).
- Entrega honesta: no prometemos validar contra un schema que no existe. La doc lo dice explícitamente (FUNCIONAL.md §10 criterio 3, §12 referencias).

**Neutras:**

- Trade-off entre **interoperabilidad nominal** (poder decir "JSON-LD CIRPASS-2 Core" en marketing) y **entrega material** (un documento que un consumidor puede consumir hoy). Aceptamos el trade-off mientras esté documentado.

**Negativas:**

- Un consumidor que espere CIRPASS-2 Core literal en el `@context` debe leer este ADR para entender por qué nuestro DPP usa un URN propio. Mitigado: el ADR está enlazado desde FUNCIONAL.md §3 paso 7 y §10 criterio 3.
- La validación formal contra un schema CIRPASS oficial queda pendiente; no se puede ejecutar hoy. F5-01 CA #1 queda parcialmente cumplido (estructura interna validada, alineación CIRPASS pendiente del `@context` oficial). Documentado como tal.

## Reversión

Cuando CIRPASS-2 publique un `@context` HTTP-resolvable estable (o un schema SHACL/JSON Schema oficial):

1. Sustituir el valor de `_DPP_NAMESPACE` en `backend/src/app/dpp/__init__.py` por la URL oficial.
2. Re-mapear los términos del `@context` si el vocabulario CIRPASS difiere en nombres (`DigitalProductPassport` → término oficial, etc.).
3. Añadir un paso de validación SHACL/JSON Schema en el generador, materializando F5-01 CA #1 al 100 %.
4. Marcar este ADR como **Superado** y crear un ADR sucesor con la decisión migratoria.

El cambio es acotado: no toca la lógica de filtrado por `access_level`, ni la firma Ed25519, ni el endpoint público. Solo el `@context` y el paso de validación.

## Referencias

- **CIRPASS-2 Core Ontology** (marzo 2025) — modelo conceptual del DPP publicado por el consorcio CIRPASS-2 financiado por la Comisión Europea.
- **JSON-LD 1.1** (W3C Recommendation, 16 julio 2020), §3.1 "The Context" — admite URN como IRI absoluto en términos de `@context` sin requerir resolución HTTP.
- `backend/src/app/dpp/__init__.py:43` — definición del namespace `_DPP_NAMESPACE`.
- `backend/src/app/dpp/__init__.py:100-146` — `build_jsonld` con el `@context` local.
- `docs/tickets/F5.md` §F5-01 CA #1 — criterio de aceptación cuyo cumplimiento queda condicionado por este ADR.
- `docs/FUNCIONAL.md` §3 paso 7, §10 criterio 3, §12 referencias.
- `docs/ARCHITECTURE.md` §"Pipeline del wizard" paso 7, §"Capa de datos y conocimiento".

---

*ADR siguiendo la convención del proyecto establecida en `docs/adr/0001-identificador-dpp-plugin-declared.md`.*
