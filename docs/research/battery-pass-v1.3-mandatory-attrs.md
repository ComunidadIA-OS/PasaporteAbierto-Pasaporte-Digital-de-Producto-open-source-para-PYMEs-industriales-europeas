# Battery Pass Consortium v1.3 — Atributos mandatorios extract

**Fecha de extracción:** 2026-05-24
**Sesión:** validación de batteries.yaml T6 contra referencia industrial
**Fuente original (XLSX, 459 KB):**
https://thebatterypass.eu/wp-content/uploads/2026_BatteryPass-Ready_DataAttributeLongList_v1.3.xlsx
**Publicación:** Battery Pass Consortium, marzo 2026
**Hoja relevante en el XLSX:** `Data attribute longlist_DR_v1.3` (107 filas × 23 columnas; data en filas 8-107 → 100 atributos)

## Por qué este documento existe

EUR-Lex trunca el HTML del Reglamento UE 2023/1542 en los considerandos cuando se consulta vía WebFetch — no devuelve los artículos ni los anexos. La validación directa contra el texto regulatorio no fue posible en la sesión 2026-05-23.

El Battery Pass Consortium (proyecto financiado por el Ministerio Alemán de Economía, ver disclaimer del XLSX) publica la referencia industrial estándar para la implementación del battery passport del Reg. UE 2023/1542. La v1.3 (marzo 2026) incorpora:
- JTC-24 prEN_18219 / prEN_18222 / prEN_18223 (drafts CEN/CENELEC Q3 2025)
- DIN DKE SPEC 99100
- Implementing/Delegated Acts en preparación bajo el reglamento

Es la **referencia de hecho** que la industria está siguiendo. **No es texto regulatorio**, pero su mapeo a artículos del reglamento es fiel.

## Leyenda

- `x` = mandatorio per BattReg (Reg. UE 2023/1542)
- `(x)` = mandatorio per ESPR / JTC-24 (extiende el BattReg)
- `o` = voluntario

Categorías de batería relevantes: **EV** (vehículo eléctrico) y **Other Industrial >2kWh** son las que aplican desde **febrero 2027**.

## Resumen cuantitativo

| Status | EV o Industrial>2kWh | Notas |
|---|---|---|
| Mandatorio per BattReg | **73 atributos** | Lista completa abajo |
| Mandatorio per ESPR/JTC-24 (extensión) | 6 atributos | Anexo al final |
| Voluntario | 9 atributos | No incluido aquí |
| **Total de la longlist** | 100 atributos | |

## Cobertura del plan original de T6 (batteries.yaml v0.1.0 propuesto)

El plan en `docs/superpowers/plans/2026-05-23-fase-1-fundacion.md` líneas 1393-1554 propone **17 campos** (16 obligatorios + 1 opcional). Eso equivale a **~22% del mínimo regulatorio** según Battery Pass v1.3.

Además, el plan tiene **errores de citación documentados** en al menos 5 campos (citan Anexo VI Parte A cuando la cita canónica para contenidos del DPP es Anexo XIII):

| Campo del plan | Cita en el plan | Cita correcta per Battery Pass v1.3 |
|---|---|---|
| `battery_category` | Art. 3(1) | Anexo XIII (1a) + Anexo VI Part A(2) |
| `chemistry` | Anexo VI Part A(1) | Anexo XIII (1b) + Anexo VI Part A(**7**) |
| `nominal_voltage_v` | Anexo VI Part A(2) | Anexo XIII (1h) |
| `capacity_kwh` | Anexo VI Part A(2) | Anexo XIII (1g) + Anexo IV Part A(1) |
| `mass_kg` | Anexo VI Part A(3) | Anexo XIII (1a) + Anexo VI Part A(**5**) |
| `hazardous_substances` | Anexo VI Part A(7) | Anexo XIII (1b) + Anexo VI Part A(**8**) |
| `expected_lifetime_cycles` | Art. 14(1) | Anexo XIII (1) y (4a) + Anexo IV Part A(5) |
| `carbon_footprint_kgco2e_kwh` | Art. 7 | Anexo XIII (1c) → Art. 7 |
| `recycled_content_*` | Art. 8(1) | Anexo XIII (1e) + Art. 8(1) — debe split pre/post-consumer |
| `ce_marking_present` | Art. 19 | Anexo XIII (1r) + Art. 18 (Art. 19 es etiquetado, no DPP) |

## Vacíos críticos (mandatorio per BattReg, ausente del plan)

### 🔴 Identificadores fundamentales (10 campos)
- **Unique battery passport identifier** (Art. 77(3)(10), Art. 3(66)) — **el ID del propio DPP**
- Unique battery identifier (Art. 77(3))
- Battery serial number (Art. 38(6); Anexo IX)
- Unique manufacturer identifier (Anexo VI Part A(1))
- Economic operator information (Art. 3, 1(22))
- Manufacturing place (Anexo XIII (1a); Anexo VI Part A(3))
- Manufacturing date (Anexo XIII (1a); Anexo VI Part A(4))
- Warranty period of the battery (Anexo XIII (1m))
- Battery status (Anexo XIII 4(c)) — dinámico

### 🟠 Símbolos, etiquetas y conformidad (7 campos)
- Separate collection symbol (Anexo XIII (1s); Art. 13(4))
- Symbols for cadmium and lead (Anexo XIII (1s); Art. 13(5))
- Carbon footprint label (Art. 7(2) via Anexo XIII (1c))
- Extinguishing agent (Anexo VI Part A(9))
- Meaning of labels and symbols (Anexo XIII (1s); Art. 74 1(e))
- EU declaration of conformity (Anexo XIII (1r); Art. 18; Anexo IX)
- Results of test reports proving compliance (Anexo XIII (3); Anexo VIII Part A 2(h))

### 🟠 Huella de carbono (5 sub-campos adicionales al kgCO2e/kWh total)
- Contribution of raw material acquisition lifecycle stage
- Contribution of production lifecycle stage
- Contribution of distribution lifecycle stage
- Contribution of end-of-life lifecycle stage
- Carbon footprint performance class
- Web link to public carbon footprint study

(Todos: Anexo XIII (1c) → Art. 7; CF declaration IA draft)

### 🟠 Supply chain
- Due diligence report info (Art. 52(3))

### 🟠 Materiales (Anexo XIII (1b) y (2a))
- **Critical raw materials** (Anexo XIII (1b); Anexo VI Part A(10))
- **Materials used in cathode, anode and electrolyte** (Anexo XIII (2a))
- Impact of substances on environment, human health, safety, persons (Anexo XIII (1s); Art. 74 1(f))

### 🟠 Circularidad (Anexo XIII (2) + Art. 74)
- **Dismantling information / manuales** (Anexo XIII (2c)) — clave por Art. 11
- Part numbers for components (Anexo XIII (2b))
- Sources of spare parts (Anexo XIII (2b))
- Safety measures (Anexo XIII (2d); Art. 74(2))
- Renewable content share (Anexo XIII (1f))
- Info usuario final: prevención de residuos (Art. 74(1a))
- Info usuario final: recolección separada (Art. 74(1b))
- Info usuario final: recolección + tratamiento fin de vida (Art. 74(1c)) ← parcialmente cubierto por `collection_recycling_info_url`

### 🟠 Contenido reciclado (split pre/post-consumer per material — el plan oversimplifica)
- Pre-consumer recycled nickel share | Post-consumer recycled nickel share
- Pre-consumer recycled cobalt share | Post-consumer recycled cobalt share
- Pre-consumer recycled lithium share | Post-consumer recycled lithium share
- Recycled lead share (un solo split en el caso del plomo)

(Todos: Anexo XIII (1e); Art. 8(1))

### 🟠 Performance & durability — la sección más grande del DPP (Anexo XIII (1g-p) + (4a-d))
- **Capacity fade** (Anexo IV Part A(1); Anexo IV (2))
- **State of Charge (SoC)** (Anexo XIII (4d); Art. 3 1(27)) — dinámico
- **Min voltage** (Anexo XIII (1h))
- **Max voltage** (Anexo XIII (1h))
- **Original power capability** (Anexo XIII (1i); Art. 10; Anexo IV Part B(4))
- **Power fade** (Anexo IV P(4); Anexo IV Part A(2); Anexo IV Part B(4))
- **Max permitted battery power** (Anexo XIII (1i))
- **Initial round-trip energy efficiency** (Anexo XIII (1n); Art. 10; Anexo IV(6); Anexo IV Part A(4))
- **RTEE @ 50% cycle life** (Anexo XIII (1n); Anexo IV(6))
- **Energy round-trip efficiency fade** (Anexo IV Part A(4))
- **Initial internal resistance** cell/pack (Anexo XIII (1o); Art. 10; Anexo IV Part A(3))
- **Internal resistance increase** pack (Anexo IV Part A(3))
- **Expected lifetime in calendar years** (Anexo IV Part A(5); Anexo XIII (1); Anexo XIII (4a))
- **Expected lifetime: charge-discharge cycles** (Anexo IV Part A(5); Anexo XIII (1); Anexo XIII (4a)) ← parcialmente cubierto por `expected_lifetime_cycles`
- **Number of full charging/discharging cycles** (Anexo XIII (4d); Art. 14; Anexo VII Part B(5)) — dinámico
- **Cycle-life reference test** (Anexo XIII (1j))
- **C-rate of relevant cycle-life test** (Anexo XIII (1p))
- **Capacity threshold for exhaustion** (Anexo XIII (1k)) — solo EV
- **Temperature information** (Anexo XIII (4d)) — dinámico
- **Temperature range idle state, lower** (Anexo XIII (1l))
- **Temperature range idle state, upper** (Anexo XIII (1l))
- **Information on accidents** (Anexo XIII (4d)) — dinámico
- **State of certified energy (SOCE)** (Anexo VII Part A) — solo EV, dinámico

## Listado completo de los 73 mandatorios per BattReg

Extracto generado con script openpyxl sobre el XLSX. Para regenerar:
```bash
curl -sSL -o /tmp/longlist.xlsx "https://thebatterypass.eu/wp-content/uploads/2026_BatteryPass-Ready_DataAttributeLongList_v1.3.xlsx"
PATH="$HOME/.local/bin:$PATH" uvx --from openpyxl --with openpyxl python -c "
import openpyxl, json
wb = openpyxl.load_workbook('/tmp/longlist.xlsx', data_only=True)
ws = wb['Data attribute longlist_DR_v1.3']
for r in range(8, ws.max_row + 1):
    row = {ws.cell(row=7, column=c).value: ws.cell(row=r, column=c).value for c in range(2, ws.max_column + 1)}
    if row.get('EV') == 'x' or row.get('Other Industrial >2kWh') == 'x':
        print(f\"#{row['#']:>3} [EV:{row['EV']}, IND:{row['Other Industrial >2kWh']}] {row['Attribute category']} :: {row['Attribute']} — ref: {(row.get('Regulation Reference') or '').strip()[:80]}\")
"
```

## Decisión tomada (2026-05-24): opción A refinada contra texto oficial

Tras descargar el PDF oficial del Reglamento UE 2023/1542 (`/Users/luisbravo/Downloads/CELEX_32023R1542_ES_TXT.pdf`, 117 páginas, DOUE L 191 de 28.07.2023) y extraer **Annex XIII (página 108-109), Anexo VI Parte A (página 93) y Artículo 77 (páginas 72-73)** con `pypdf`, la decisión es:

**Opción A — Tier-1 ampliado**, refinada con el texto oficial en lugar de Battery Pass v1.3.

| Opción original | Resultado |
|---|---|
| A — Tier-1 ampliado (~30 campos) | ✅ **ELEGIDA**, refinada a 48 campos validados contra Annex XIII |
| B — Mantener 17 + corregir citas | ❌ Descartada: con 17 campos solo se cubre el ~28% del Annex XIII expandido — incompatible con la decisión de ser fiel al reglamento |
| C — Cobertura completa (73 campos) | ❌ Descartada: los 73 del Battery Pass v1.3 incluyen desagregaciones JTC-24 (industrial-standard) y la Sección 4 dinámica (telemetría operativa post-registro). Out of scope del wizard |
| D — Diferir T6 hasta F2 | ❌ Descartada: rompe el orden del plan y F1-03 queda abierto |

## Validación final contra texto oficial del Reglamento

Esta sección reemplaza el análisis previo basado únicamente en Battery Pass v1.3. La nueva fuente de verdad es el **texto oficial del Reglamento UE 2023/1542** (DOUE L 191/28.7.2023).

### Estructura canónica del Annex XIII

El Annex XIII tiene **4 secciones** con niveles de acceso diferenciados, formalmente establecidos por el Art. 77.2:

| Sección | Visibilidad | Items oficiales (alto nivel) | Items expandidos (sub-elementos) |
|---|---|---|---|
| **1** | Público general | 19 letras (a-s) | ~40 campos al expandir (1a) → Anexo VI Parte A (10 sub-ítems), (1b) → 3 sub-elementos, (1s) → Art. 74.1.a-f (6 sub-items) |
| **2** | Interés legítimo + Comisión | 4 letras (a-d) | 7 campos |
| **3** | Organismos notificados + MSA + Comisión | 1 | 1 campo |
| **4** | Interés legítimo, batería individual | 4 letras (a-d) | **Fuera de alcance** del plugin — son datos dinámicos de telemetría operativa post-registro |

### Hallazgos validados contra el texto oficial

✅ **Los 73 atributos del Battery Pass v1.3 son una representación razonable** de Annex XIII + JTC-24 (industrial standard) + Sección 4 dinámica. Para nuestro plugin estático cubrimos ~48 campos (Secciones 1+2+3 del texto oficial, sin las desagregaciones JTC-24 ni la Sección 4 dinámica).

✅ **Las 5 citas erróneas del plan original están confirmadas como erróneas** contra el texto oficial:

| Campo | Cita errónea del plan | Cita correcta verificada |
|---|---|---|
| `chemistry` | Anexo VI Parte A(1) | **Annex XIII (1b) + Anexo VI Parte A(7)** |
| `nominal_voltage_v` | Anexo VI Parte A(2) | **Annex XIII (1h)** (Anexo VI no lista voltaje) |
| `capacity_kwh` → `rated_capacity_ah` | Anexo VI Parte A(2) en kWh | **Annex XIII (1g) literal: "amperios-hora"** |
| `mass_kg` | Anexo VI Parte A(3) | **Annex XIII (1a) + Anexo VI Parte A(5)** (el (3) es "lugar de fabricación") |
| `hazardous_substances` | Anexo VI Parte A(7) | **Annex XIII (1b) + Anexo VI Parte A(8)** |
| `ce_marking_present` | Art. 19 (inexistente para CE) | **Annex XIII (1r) + Art. 18** (Declaración UE de conformidad) |

🚨 **Hallazgos nuevos detectados solo con el texto oficial:**

1. **Identificador único contradice ARCHITECTURE.md.** El Art. 77.3 obliga literalmente: *"el código QR y el identificador único deberán cumplir las normas **ISO/IEC 15459-1:2014, 15459-2:2015, 15459-3:2014, 15459-4:2014, 15459-5:2014 y 15459-6:2014** o sus equivalentes"*. La arquitectura decía "GS1 Digital Link" — actualizada para que el esquema lo declare cada plugin (`identifier_scheme`), con ISO/IEC 15459 obligatorio para baterías y GS1 Digital Link como fallback genérico.

2. **Cuatro niveles de visibilidad, no uno.** Art. 77.2 + Annex XIII definen 4 secciones con visibilidad regulada. El schema del plugin no modelaba esto. Se ha añadido `access_level` por campo en T5.1 (`public` / `legitimate_interest` / `authorities_only` / `individual`). Establecido como dimensión ortogonal al `provenance` existente (ver FUNCIONAL.md §9.1 vs §9.2).

3. **El reglamento literal dice "amperios-hora" para la capacidad asignada** (Annex XIII (1g)). El plan tenía `capacity_kwh: number`, que era doblemente erróneo: unidad incorrecta + cita errónea. Renombrado a `rated_capacity_ah` con cita Annex XIII (1g).

4. **Aplicabilidad del pasaporte (Art. 77.1):** desde 18 febrero 2027, aplica a **baterías LMT, industriales >2 kWh y EV**. El plugin v0.1.0 cubre Industrial y EV (las dos categorías más estables del subset). Los actos de ejecución de Art. 77.9 (a más tardar 18 agosto 2026) definirán las "personas con interés legítimo" para el acceso a Sección 2 y 4.

### Reparto final de los 48 campos por sección

Detalle exhaustivo en `docs/superpowers/plans/2026-05-23-fase-1-fundacion.md` Task 6:

| Sección | # campos | Required | Access level |
|---|---|---|---|
| 1 (público) | 38-40 | 39 (todos menos 1k que es solo EV) | `public` |
| 2 (interés legítimo) | 7 | 7 | `legitimate_interest` |
| 3 (autoridades) | 1 | 1 | `authorities_only` |
| **Total** | **~48** | **~47** | mixto |

Por encima del ≥25 obligatorios de F1-03 (acceptance criterion #2 actualizado).

## Referencias para próxima sesión

- **Battery Pass v1.3 XLSX:** https://thebatterypass.eu/wp-content/uploads/2026_BatteryPass-Ready_DataAttributeLongList_v1.3.xlsx
- **Battery Pass publications:** https://thebatterypass.eu/battery-pass-ready/publications/
- **Plan original T6:** `docs/superpowers/plans/2026-05-23-fase-1-fundacion.md` líneas 1393-1554
- **Ticket relacionado:** F1-03 en `docs/tickets/F1.md`
- **Invariante en CLAUDE.md:** "Si una decisión técnica o funcional contradice estos documentos, el documento gana: actualiza el doc antes de implementar, no al revés." → la corrección de citas + ampliación de campos puede requerir actualizar el plan antes de implementar.
