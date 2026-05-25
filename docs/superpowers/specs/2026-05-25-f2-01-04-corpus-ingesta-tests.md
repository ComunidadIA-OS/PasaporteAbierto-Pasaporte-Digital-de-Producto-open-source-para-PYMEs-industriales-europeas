# F2-01 + F2-04 · Ingesta del corpus normativo y suite de calidad RAG · Diseño

> **Alcance de este spec:** tickets `F2-01` (pipeline de ingesta) y `F2-04` (dataset de queries + tests RAG) de la Fase 2. Los tickets `F2-02` (chunking + embeddings + ChromaDB) y `F2-03` (servicio de retrieval) se trabajan en paralelo en otra rama sobre el mismo contrato compartido.

**Rama de trabajo:** `f2_01_04` (ya existe, parte de `e74011f`).

**Contrato compartido (ya commiteado en `e74011f`):** `backend/src/app/rag/schema.py` define `Fragment`, `Filters`, `Result`, `Language`, la función pura `format_citation()` y el stub `search_corpus()` que lanza `NotImplementedError` hasta que F2-03 aterrice.

---

## Objetivo

1. **F2-01:** un comando reproducible `python -m app.rag.ingest` que descarga, parsea y persiste el corpus regulatorio europeo como ficheros JSONL de `Fragment`s, listos para que F2-02 los indexe en ChromaDB.
2. **F2-04:** un dataset fijo de 20–30 queries con su cita esperada y una suite pytest que detectará regresiones del RAG cuando F2-02/F2-03 aterricen. Los tests se escriben hoy contra la firma del stub `search_corpus()`, marcados `xfail(strict=False)`, y se vuelven verdes automáticamente cuando F2-03 mergee.

Ambos tickets cubren sus criterios de aceptación tal como están en `docs/tickets/F2.md`.

---

## Alcance del corpus (decisión: completa, según ticket)

| Fuente | Idiomas | Cómo se obtiene |
|---|---|---|
| Reg. UE 2024/1781 (ESPR) | es, en | Descarga HTML EUR-Lex en runtime |
| Reg. UE 2023/1542 (baterías) — incluye Art. 77 y Annex XIII explícitos | es, en | Descarga HTML EUR-Lex en runtime |
| Actos delegados publicados a fecha | es, en | Lista declarativa de CELEX IDs, descarga HTML EUR-Lex |
| CIRPASS-2 Core Ontology (mar 2025) | en (no hay versión es oficial) | Descarga JSON-LD desde repo público CIRPASS-2 |
| GS1 Digital Link spec | en | Descarga HTML público GS1 |
| ISO/IEC 15459-1/2/3/4/5/6 | es, en | **Fragmentos-stub** con abstract público + `fuente_url` a ISO OBP. No se redistribuye texto bajo licencia ISO. |

**Por qué fragmentos-stub para ISO:** el Art. 77.3 del Reg. UE 2023/1542 exige que el identificador único de batería cumpla ISO/IEC 15459. El RAG debe poder citar la norma cuando el chat lo necesite, aunque no contenga el texto completo. Un fragmento con `texto` = abstract público (≤200 palabras de uso legítimo) + `fuente_url` = página oficial ISO OBP cumple esa función sin infringir licencia.

---

## Arquitectura

### Estructura de módulos (F2-01)

```
backend/src/app/rag/
├── schema.py                # ya existe (e74011f) — no se toca
├── __init__.py              # ya existe (e74011f) — re-exports
└── ingest/
    ├── __init__.py
    ├── __main__.py          # CLI: `python -m app.rag.ingest`
    ├── writer.py            # escritura atómica JSONL
    ├── http_cache.py        # cache HTTP en data/corpus/_raw/
    └── sources/
        ├── __init__.py      # registry de sources
        ├── eurlex.py        # Reg. 2024/1781 + Reg. 2023/1542 + actos delegados
        ├── cirpass.py       # CIRPASS-2 Core Ontology
        ├── gs1.py           # GS1 Digital Link
        └── iso_15459.py     # fragmentos-stub
```

**Principio:** cada source es independiente, devuelve `Iterable[Fragment]`, y se testea aislada con HTML fixture. Añadir un sector nuevo en F3+ = un fichero nuevo en `sources/`. Coherente con la invariante del proyecto "extensibilidad por configuración" (CLAUDE.md §"Invariantes arquitectónicas").

### Estructura de tests (F2-01 + F2-04)

```
backend/tests/rag/
├── __init__.py
├── conftest.py                       # fixtures comunes
├── fixtures/
│   ├── eurlex_ue-2024-1781_es.html   # snippet real recortado (~30 KB)
│   ├── eurlex_ue-2024-1781_en.html
│   ├── eurlex_ue-2023-1542_es.html   # incluye Art. 77 + Annex XIII (críticos)
│   ├── eurlex_ue-2023-1542_en.html
│   ├── cirpass_core.jsonld
│   └── gs1_digital_link.html
├── queries.yaml                       # dataset F2-04 (20–30 queries)
├── test_ingest_eurlex.py             # F2-01
├── test_ingest_cirpass.py            # F2-01
├── test_ingest_gs1.py                # F2-01
├── test_ingest_iso_15459.py          # F2-01
├── test_ingest_writer.py             # F2-01
├── test_query_dataset.py             # F2-04, no xfail (valida el YAML)
└── test_retrieval_quality.py         # F2-04, xfail strict=False hasta F2-03
```

### Persistencia (output de F2-01)

```
backend/data/corpus/
├── _raw/                              # cache HTTP, NO commitado (en .gitignore)
│   ├── ue-2024-1781.es.html
│   ├── ue-2024-1781.en.html
│   ├── ue-2023-1542.es.html
│   ├── ue-2023-1542.en.html
│   ├── cirpass-2-core.jsonld
│   └── gs1-digital-link.html
├── ue-2024-1781.es.jsonl              # un Fragment por línea (model_dump_json)
├── ue-2024-1781.en.jsonl
├── ue-2023-1542.es.jsonl
├── ue-2023-1542.en.jsonl
├── actos-delegados-<celex>.{es,en}.jsonl
├── cirpass-2-core.en.jsonl
├── gs1-digital-link.en.jsonl
└── iso-15459.{es,en}.jsonl
```

`data/corpus/_raw/` y `data/corpus/*.jsonl` van al `.gitignore` del backend — el corpus es regenerable, no es código fuente.

---

## Data flow

### Pipeline end-to-end de `python -m app.rag.ingest`

```
1. CLI parsea flags: --force-refresh, --only=<slug>, --lang={es,en}
2. Para cada source seleccionada en [eurlex, cirpass, gs1, iso_15459]:
   a. source.fetch()       → bytes raw (HTML/JSON-LD), cacheados en data/corpus/_raw/
   b. source.parse(bytes)  → Iterable[Fragment] (lazy)
   c. writer.write(fragments, slug, lang)
      → data/corpus/{slug}.{lang}.jsonl  (escritura atómica: tmp + os.replace)
3. Imprime resumen: por reglamento × idioma, nº de fragments escritos
4. Exit 0 si todo OK; exit 1 si alguna source falló transitoriamente
   (red); exit 2 si hay parser bug (regresión bloqueante)
```

### Cómo cada source produce `Fragment`s

| Source | Estrategia |
|---|---|
| `eurlex.py` | Descarga HTML de `https://eur-lex.europa.eu/legal-content/{ES,EN}/TXT/HTML/?uri=CELEX:<id>`. Parsea con `lxml`+`beautifulsoup4` usando selectores semánticos de EUR-Lex (`p.ti-art` marca artículo, `p.normal` apartado, divs con clase `ti-section-1` para anexos). Un `Fragment` por (artículo, apartado). Anexos modelados como `articulo="Annex XIII"`. `sector="batteries"` para Reg. 2023/1542; `None` para Reg. 2024/1781 (transversal). |
| `actos_delegados.py` (parte de `eurlex.py`) | Lista hardcoded de CELEX IDs **publicados a fecha 2026-05-25** (los IDs concretos se determinan en el primer paso del plan consultando EUR-Lex; en caso de no haber actos delegados ESPR publicados todavía, se omite el grupo y se documenta). Reutiliza el parser de `eurlex.py`. `sector` se etiqueta según ámbito del acto. |
| `cirpass.py` | Descarga JSON-LD desde repo público CIRPASS-2. Cada clase/propiedad (Product, Material, ConformityDocument, etc.) → un `Fragment` con `articulo` = nombre de la clase, `texto` = label + comment. `reglamento="CIRPASS-2 Core"`, `apartado=None`, `sector=None`. |
| `gs1.py` | Descarga HTML público GS1 Digital Link. Secciones numeradas → `Fragment` con `articulo="sección N"`. `reglamento="GS1 Digital Link 1.3.0"`. |
| `iso_15459.py` | Sin red. Lista declarativa en código con 6 entradas (una por parte). `texto` = abstract público del ISO OBP (≤200 palabras) + nota "Texto completo bajo licencia ISO". `fuente_url` apunta a la página oficial de esa parte. Una pasada `idioma="es"` y otra `"en"`. |

### Slug + idioma → fichero

| Reglamento | Slug | Ficheros producidos |
|---|---|---|
| Reg. UE 2024/1781 (ESPR) | `ue-2024-1781` | `ue-2024-1781.{es,en}.jsonl` |
| Reg. UE 2023/1542 (baterías) | `ue-2023-1542` | `ue-2023-1542.{es,en}.jsonl` |
| Acto delegado (cada uno) | `actos-delegados-<celex-en-minúsculas>` | uno por acto × idioma |
| CIRPASS-2 Core | `cirpass-2-core` | `cirpass-2-core.en.jsonl` |
| GS1 Digital Link | `gs1-digital-link` | `gs1-digital-link.en.jsonl` |
| ISO/IEC 15459-1..6 | `iso-15459` | `iso-15459.{es,en}.jsonl` |

### Formato JSONL

Una línea = un `Fragment` serializado con `Fragment.model_dump_json()`. Sin envelope ni header. F2-02 lo lee con `for line in file: Fragment.model_validate_json(line)`.

### Idempotencia

- Re-ejecutar el comando **siempre reescribe** los JSONL (escritura atómica con `os.replace`). No hay detección incremental — la regeneración completa es barata (HTML cacheado, parsing en segundos).
- Cache HTTP en `data/corpus/_raw/{slug}.{lang}.html` evita re-descargar. `--force-refresh` invalida la cache.
- IDs deterministas en F2-02 saldrán de `(slug, articulo, apartado)`, garantizando "reindexar dos veces no duplica vectores" (criterio 2 del F2-02).

---

## Manejo de errores

| Tipo de error | Comportamiento | Exit code |
|---|---|---|
| Red caída / timeout EUR-Lex | Reintento `httpx` con backoff exponencial (3 intentos: 1s/2s/4s). Si falla, source loguea WARNING y se salta; el CLI continúa | 1 |
| HTTP 4xx/5xx persistente | Misma política | 1 |
| HTML cambió y parser no encuentra artículos (0 artículos en doc >10 KB) | `IngestParseError` con URL — regresión bloqueante | 2 |
| `Fragment` falla validación Pydantic | Bug de parser, excepción con contexto | 2 |
| Cache HTML corrupta (truncada) | Validador del cache la descarta y re-descarga | 0 (transparente) |
| Disco lleno al escribir JSONL | `os.replace` falla, el JSONL anterior sigue intacto, excepción se propaga | distinto de 0 |

### Logging

`logging` estándar de Python. INFO en happy path (`✓ ue-2024-1781.es: 412 fragments`), WARNING en skips de red, ERROR en bugs de parser.

### Observabilidad Langfuse

**F2-01 NO emite spans Langfuse.** Es un comando one-shot offline, no parte de una sesión de usuario. Langfuse se reserva para Clasificador/Recolector/Chat (coherente con F1-05). F2-03 sí emitirá spans cuando `search_corpus()` se invoque desde un agente IA.

---

## CLI

```
usage: python -m app.rag.ingest [--force-refresh] [--only SLUG] [--lang {es,en}]

Sin flags: descarga (o usa cache) + parsea + escribe todos los sources × es+en.

  --force-refresh    Invalida cache HTTP, re-descarga todo
  --only SLUG        Limita a una source (ej. --only ue-2024-1781). Repetible.
  --lang {es,en}     Limita a un idioma. Sin flag = ambos.

Exit codes:
  0  todo OK
  1  alguna source falló transitoriamente (red), el resto se completó
  2  parser bug: regresión bloqueante (HTML cambió, validación Pydantic)
```

---

## Dependencias nuevas (`backend/pyproject.toml`)

```
"beautifulsoup4==4.12.*",   # parsear HTML EUR-Lex
"lxml==5.*",                # parser rápido para BS4
```

`httpx` ya está. `pyyaml` ya está (lo usa F2-04 para el dataset). `chromadb` y `sentence-transformers` quedan para F2-02 — no se añaden aquí.

En dev:

```
"pytest-json-report==1.5.*",  # para generar el badge de calidad
```

---

## Testing

### F2-01 — tests unitarios por source

Cada test trabaja sobre fixtures HTML reales recortados (~30 KB cada uno). Sin red.

| Test | Garantía |
|---|---|
| `test_ingest_eurlex.py::test_parse_espr_produces_articles` | Sobre fixture Reg. 2024/1781 (~30 KB recortado del HTML real), extrae el número exacto de artículos contenidos en el fixture (valor concreto se fija en el plan, al crear el fixture). Cada `Fragment` valida contra el contrato |
| `test_ingest_eurlex.py::test_parse_baterias_art77_present` | Captura específicamente Art. 77 + Annex XIII (críticos para batteries); cita formateada con `format_citation()` |
| `test_ingest_eurlex.py::test_sector_tagged_correctly` | Reg. 2023/1542 → `sector="batteries"`; Reg. 2024/1781 → `sector=None` |
| `test_ingest_eurlex.py::test_fuente_url_canonical` | `fuente_url` apunta al CELEX correcto en EUR-Lex |
| `test_ingest_cirpass.py::test_classes_become_fragments` | Cada clase/propiedad del JSON-LD → un `Fragment` válido |
| `test_ingest_gs1.py::test_sections_extracted` | Secciones numeradas pasan a `Fragment` con `articulo="sección N"` |
| `test_ingest_iso_15459.py::test_six_parts_present` | 6 fragments en es + 6 en en, sin red |
| `test_ingest_writer.py::test_atomic_write_idempotent` | Escribir dos veces el mismo input produce el mismo fichero byte a byte |
| `test_ingest_writer.py::test_atomic_write_does_not_corrupt_on_crash` | Si la escritura falla a medias, el fichero previo sobrevive |

**Lo que NO se testea:** la descarga real desde EUR-Lex (red flaky en CI). Eso se cubre con un smoke test manual documentado en el README del backend, no en pytest.

### F2-04 — dataset

#### `backend/tests/rag/queries.yaml`

20–30 queries con este schema:

```yaml
- id: <kebab>                # único, estable
  query: <texto de la query>
  expected_citation:
    reglamento: "UE 2024/1781"
    articulo: "7"
    apartado: "3"            # opcional
  idioma: es                  # idioma de la query
  tags: [espr, public]        # opcional, para análisis posterior
```

**Distribución mínima:**
- ≥8 queries sobre ESPR (Reg. UE 2024/1781)
- ≥8 queries sobre baterías (Reg. UE 2023/1542) — al menos 3 sobre Art. 77 / Annex XIII
- ≥2 queries sobre CIRPASS-2
- ≥2 queries sobre GS1 Digital Link
- ≥2 queries sobre ISO 15459 (verifica que la cita aparece aunque el texto sea stub)
- ≥40% en castellano, ≥40% en inglés

#### `backend/tests/rag/test_query_dataset.py` (NO xfail — corren siempre)

| Test | Garantía |
|---|---|
| `test_dataset_valid_schema` | Cada entrada cumple el schema (pydantic model interno) |
| `test_dataset_no_duplicate_ids` | IDs únicos |
| `test_dataset_min_size` | ≥20 entradas, ≤30 |
| `test_dataset_distribution` | Cobertura mínima por reglamento e idioma |

#### `backend/tests/rag/test_retrieval_quality.py` (xfail strict=False)

```python
@pytest.mark.xfail(
    reason="Requiere F2-03 (search_corpus implementado). Retirar marca al mergear F2-03 a develop.",
    strict=False,
)
@pytest.mark.parametrize("entry", load_queries(), ids=lambda e: e.id)
def test_expected_citation_in_top3(entry):
    results = search_corpus(entry.query, top_k=3, filters=Filters(idioma=entry.idioma))
    citations = [r.cita for r in results]
    expected = render_expected_citation(entry.expected_citation)
    assert any(expected in c for c in citations), (
        f"Esperado '{expected}' en top-3, obtenido: {citations}"
    )


@pytest.mark.xfail(reason="Requiere F2-03", strict=False)
def test_top3_accuracy_over_80_percent():
    results = run_full_eval(load_queries())
    assert results.top3_accuracy >= 0.80
```

**Por qué `xfail(strict=False)`:** mientras F2-03 no exista, `search_corpus()` lanza `NotImplementedError` → `xfail` → CI verde. Cuando F2-03 mergee a `develop`, los tests pasarán → `XPASS` → CI sigue verde y el equipo retira la marca en un PR puente.

### Badge de calidad RAG en README

`scripts/rag_quality_badge.py`:

1. Corre `pytest backend/tests/rag/test_retrieval_quality.py --json-report --json-report-file=/tmp/rag.json`
2. Lee el JSON, cuenta `passed`/`xfailed`/`failed`
3. Si todos `xfailed` → badge "RAG quality: pendiente (F2-03)" en gris
4. Si hay `passed` → badge "RAG quality: X% top-3" en verde si ≥80%, ámbar 60–80%, rojo <60%
5. Inserta el badge entre dos comentarios HTML marcadores en `README.md`

CI corre este script y commitea README solo si el badge cambia. **En esta rama, el badge inicialmente dice "pendiente (F2-03)"** — esperado y correcto.

### Restricción de tiempo (criterio 2 de F2-04)

`pytest backend/tests/rag/` corre en <60s. Mientras `test_retrieval_quality.py` está xfail, corre en milisegundos (cada test salta al primer `NotImplementedError`).

---

## Mapeo de criterios de aceptación

### F2-01

| Criterio del ticket | Cómo se cumple |
|---|---|
| `python -m ingest` se ejecuta desde cero sin requerir datos previos | El comando descarga HTML, cachea en `data/corpus/_raw/`, escribe JSONL. Sin estado previo necesario. (Nota: el módulo está bajo `app.rag.ingest` para evitar colisión de nombres y respetar la convención del proyecto; documentado en README) |
| Cada fragmento expone su referencia "Reglamento X, Art. Y" lista para citar | `format_citation()` del contrato compartido se aplica al persistir; los campos crudos quedan en el `Fragment` por si F2-03 los necesita |
| El corpus contiene fragmentos en castellano e inglés | Cada source itera sobre `["es", "en"]` salvo CIRPASS-2 y GS1 (solo `en` por no existir versión oficial es) |

### F2-04

| Criterio del ticket | Cómo se cumple |
|---|---|
| ≥80% de queries devuelven cita correcta en top-3 | `test_top3_accuracy_over_80_percent` mide y asserta. Validable solo cuando F2-03 aterrice |
| `pytest tests/rag/` corre en <60s en local | Tests unitarios usan fixtures locales (sin red); la suite de calidad mientras xfail corre en ms. Cuando F2-03 aterrice, retrieval real es <500ms por query (criterio F2-02) × 30 queries < 15s |
| Badge de calidad RAG en README, actualizado por CI | `scripts/rag_quality_badge.py` + paso de CI |

---

## Coordinación con F2-02 y F2-03 (otra rama)

- El contrato compartido en `backend/src/app/rag/schema.py` es la frontera. **No se modifica** en esta rama salvo bug crítico (y entonces en PR aparte, coordinado).
- F2-01 produce JSONLs en `backend/data/corpus/{slug}.{idioma}.jsonl`. F2-02 los consume desde ese path. El path es contrato de facto entre las ramas — documentado aquí.
- F2-04 importa `search_corpus()` y `Filters` desde `app.rag` (stub hoy). Cuando F2-03 mergee a `develop` y luego entre a esta rama vía rebase/merge, los tests pasarán automáticamente.
- Orden de merge sugerido: F2-01 → develop, F2-02 → develop (depende de JSONLs), F2-03 → develop (depende de Chroma poblado), F2-04 → develop (depende de search_corpus real). Las dos ramas (`f2_01_04` y la de F2-02/03) sincronizan por `develop`.

---

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| EUR-Lex cambia el HTML y rompe el parser | Tests sobre fixtures fijos detectan regresión en CI. Si el parser falla en runtime (0 artículos), exit code 2 obliga a intervenir en lugar de continuar silenciosamente |
| CIRPASS-2 mueve el JSON-LD de URL | URL en una constante en `cirpass.py` — actualización trivial. Cache HTTP cubre cortes puntuales |
| GS1 Digital Link spec migra a otra estructura | Fixture local mantiene tests verdes; el smoke manual del README captura el problema antes del próximo merge |
| ISO 15459 no devuelve nada útil en RAG porque el texto es muy corto | Aceptado conscientemente: la función del fragmento es que la cita aparezca, no que el contenido sea rico. Documentado |
| F2-03 retrasa y los `xfail` se ignoran indefinidamente | El badge "pendiente (F2-03)" en el README es presión visible. El criterio 3 de F2-04 (badge actualizado) no se cumple hasta que F2-03 cierre |

---

## Lo que este spec NO cubre

- Chunking semántico, embeddings, indexado en ChromaDB → **F2-02**.
- Servicio `search_corpus()` con ranking, filtros, span Langfuse → **F2-03**.
- Modificaciones al contrato `backend/src/app/rag/schema.py` → fuera de alcance, PR aparte si fuera necesario.
- Refresco automático del corpus (cron) → fuera del hackathon. Hoy: comando manual.
