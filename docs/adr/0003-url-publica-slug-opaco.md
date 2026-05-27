# ADR 0003 — URL pública del DPP con slug opaco; `gs1_uri` en el cuerpo

## Estado

**Aceptada** — 2026-05-25

## Contexto

La versión inicial de `docs/FUNCIONAL.md` §8 y `docs/ARCHITECTURE.md` §API documentaba el endpoint público del DPP como `GET /dpp/{gs1_uri}`, sugiriendo que el identificador canónico del DPP era a la vez el segmento de URL público. La idea era que el QR del producto codificara directamente `https://<host>/dpp/<gs1_uri>` y el cliente que escanease llegase al pasaporte sin redirectores externos.

El problema es que el `gs1_uri` que cada plugin produce, según la decisión documentada en `docs/adr/0001-identificador-dpp-plugin-declared.md`, no es siempre una URL navegable:

- Para baterías (`identifier_scheme: iso_iec_15459`), el URI generado por `app.dpp.build_gs1_uri` es del tipo `urn:iso15459:batteries:abcd1234`. Los URN no se resuelven por HTTP por definición.
- Para el fallback `gs1_digital_link`, el URI es `https://id.gs1.org/01/<gtin>/21/<serial>` — una URL externa que el operador de PasaporteAbierto **no controla** y que no apuntará a su instancia.

Servir el DPP en una ruta cuyo segmento sea literal el `gs1_uri` significaría:

- O bien que la ruta solo funciona con `gs1_digital_link`, sacrificando el sector más importante del hackathon (baterías).
- O bien percent-encodear el URN ISO/IEC 15459 en la URL pública (`/dpp/urn%3Aiso15459%3Abatteries%3Aabcd1234`), produciendo URLs feas y frágiles que ningún QR scanner de móvil maneja bien.
- O bien levantar un resolver oficial ISO/IEC 15459 (infraestructura externa fuera del alcance del hackathon) para que la URL del QR redirija a la instancia.

Implementar cualquiera de las tres opciones rompe el objetivo de servir el DPP de forma directa desde el propio backend del fabricante, en una URL navegable que entre en un QR estándar.

## Decisión

**La URL pública canónica es `GET /dpp/{slug}` donde `slug` es un identificador opaco derivado del `session_id` (primeros 8 caracteres del UUID4). El `gs1_uri` canónico vive en el cuerpo del DPP, no en la URL.**

Concretamente:

- `backend/src/app/api/public_dpp.py:34-47` resuelve el slug con `WHERE session_id LIKE '<slug>%'`, validando que tenga exactamente 8 caracteres alfanuméricos.
- El `gs1_uri` canónico —ISO/IEC 15459 para baterías, GS1 Digital Link como fallback genérico— se persiste en `published_dpps.gs1_uri` y aparece dentro del documento JSON-LD en el campo `@id` (ver `backend/src/app/dpp/__init__.py:141`). También se muestra explícitamente en la página HTML pública (`backend/src/app/api/public_dpp.py:119`) como "Identificador" para que el auditor humano lo lea.
- El QR del producto codifica la URL opaca completa (`https://<host>/dpp/<slug>`), generada por `app.dpp.public_dpp_url`. Así el QR es navegable directamente desde cualquier móvil sin depender de redirectores externos.
- Las rutas internas del wizard (`POST /sessions/{id}/dpp`, `GET /sessions/{id}/dpp/qr.png`, etc.) siguen usando el `session_id` completo; el slug solo aparece en la URL pública.

## Alternativas consideradas

- **A) Mantener `GET /dpp/{gs1_uri}` con percent-encoding del URN.** Descartada: URLs frágiles, mal soporte en QR scanners de móvil que aplican normalizaciones agresivas a la URL escaneada (lowercasing, drop de fragmentos, etc.). Además rompe la analogía con el `gs1_digital_link`, donde el URI es **externo** y nunca apuntaría al backend del fabricante.

- **B) Servir el DPP directamente bajo `https://id.gs1.org/...` (cuando `identifier_scheme=gs1_digital_link`).** Descartada: el operador no controla `id.gs1.org`. Forzaría un acuerdo con GS1 para resolver al DPP del fabricante, fuera del alcance del hackathon y no replicable por una PYME.

- **C) Levantar un resolver `urn:iso15459:` propio bajo `/resolve/{urn}` que redirija al slug.** Descartada: añade superficie sin valor durante el hackathon. Cuando exista un resolver oficial ISO/IEC 15459 (o cuando la Comisión publique el acto de ejecución del Art. 77.9 del Reg. UE 2023/1542 que la prevé), se puede añadir un endpoint `/dpp-by-id/{gs1_uri}` que redirija al slug — sin romper nada de lo existente.

- **D) Usar el `session_id` completo en la URL (sin slug truncado).** Descartada: el UUID completo es largo (36 chars con guiones) y aparece percent-encoded en el QR, ocupando densidad innecesaria. Ocho caracteres tienen suficiente espacio de colisión para una instancia PYME (1 fabricante, decenas de DPPs publicados); el endpoint valida `LIKE` con prefijo exacto y devuelve 404 si hay ambigüedad.

## Consecuencias

**Positivas:**

- El QR del producto es **directamente navegable**: un cliente que lo escanea llega al DPP sin depender de redirectores externos ni acuerdos con autoridades terceras.
- La instancia del fabricante sirve el DPP con sus propios dominio + certificado TLS — control operativo total.
- El `gs1_uri` canónico se preserva en el cuerpo del DPP (`@id` del JSON-LD y página HTML), así que un consumidor que necesite el identificador conforme a ISO/IEC 15459 o GS1 Digital Link lo encuentra ahí.
- La columna `published_dpps.gs1_uri` mantiene su rol de **clave de búsqueda inversa**: dado un URN ISO/IEC 15459, se puede localizar la fila correspondiente sin depender del slug.

**Neutras:**

- Para obtener el `gs1_uri` canónico, el consumidor debe leer el cuerpo del DPP (no la URL). Aceptable: cualquier procesador de DPP que valide identidad regulatoria leerá el JSON-LD completo de todas formas.

**Negativas:**

- La URL pública no es "self-describing" respecto al identificador regulatorio del producto. Un humano que vea la URL no sabe a qué batería corresponde sin abrirla. Mitigado: el contenido renderizado en HTML muestra el `gs1_uri` claramente.
- La doc original (FUNCIONAL.md §5/§8 y ARCHITECTURE.md §API) prometía `GET /dpp/{gs1_uri}`; este ADR materializa el cambio a `/dpp/{slug}` y la doc se actualiza en el mismo commit que lo introduce.

## Reversión

Cuando exista un resolver oficial para ISO/IEC 15459 (esperable cuando la Comisión adopte el acto de ejecución del Art. 77.9 del Reg. UE 2023/1542 a más tardar el 18 de agosto de 2026), o cuando GS1 publique un mecanismo de redirección estandarizado, se puede:

1. Mantener `GET /dpp/{slug}` como ruta canónica (compatibilidad con QRs ya emitidos).
2. Añadir `GET /dpp-by-id/{gs1_uri}` (o un nombre similar) que resuelva el `gs1_uri` contra `published_dpps.gs1_uri` y redirija (HTTP 301) al slug.
3. Documentar la nueva ruta en `ARCHITECTURE.md` §API y en este ADR como evolución.

El cambio es aditivo: no rompe QRs ya impresos.

## Referencias

- **Reglamento UE 2023/1542**, Art. 77.3 y Art. 77.9 (DOUE L 191/28.7.2023).
- **ISO/IEC 15459-1:2014 a -6:2014** — normas del identificador único para baterías.
- **GS1 Digital Link 1.3.0** — esquema de identificador por defecto para sectores sin acto delegado específico.
- `backend/src/app/api/public_dpp.py:34-47` — resolver del slug en el endpoint público.
- `backend/src/app/dpp/__init__.py:81-91` — `build_gs1_uri` (genera URN ISO/IEC 15459 o URL GS1 Digital Link según el plugin).
- `backend/src/app/dpp/__init__.py:189-199` — `public_dpp_url` (construye la URL opaca para el QR).
- `backend/src/app/api/v1/wizard.py:845-846` — derivación del slug desde `session_id` al publicar.
- `docs/adr/0001-identificador-dpp-plugin-declared.md` — decisión que llevó a tener URI no-navegables como identificador canónico.
- `docs/FUNCIONAL.md` §5, §8.
- `docs/ARCHITECTURE.md` §API, §Persistencia.

---

*ADR siguiendo la convención del proyecto establecida en `docs/adr/0001-identificador-dpp-plugin-declared.md`.*
