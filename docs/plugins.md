# Guía de contribución de plugins

## Qué es un plugin

Un plugin es un YAML en `plugins/` que modela un sector ESPR (baterías, textil, electrónica…) sin tocar el núcleo del sistema. El loader valida cada plugin contra el contrato canónico al arrancar; uno que no cumpla el schema no se carga. Añadir un sector es dropear un YAML, no modificar Python.

## Anatomía del YAML

Cada plugin declara estos bloques (contrato completo en `plugins/_schema.yaml`):

- `name`, `regulation`, `version` (semver), `description` opcional.
- `identifier_scheme`: `iso_iec_15459` o `gs1_digital_link`.
- `fields`: lista de campos del DPP.
- `required_documents`: PDFs que el Recolector necesita.
- `cross_validations`: reglas que cruzan varios campos.

## Cada campo

| Clave | Valores | Notas |
|---|---|---|
| `id` | string único | identificador estable, usado por el wizard |
| `type` | `string` `number` `integer` `boolean` `enum` `repeater` | tipo del input |
| `required` | bool | obligatorio para emitir el DPP |
| `citation` | `{regulation, article}` | **obligatorio**, no vacío |
| `access_level` | `public` `legitimate_interest` `authorities_only` `individual` | Annex XIII Reg. UE 2023/1542 |
| `enum_values` | lista | requerido si `type=enum` |
| `validation` | expresión | opcional |

## identifier_scheme

`iso_iec_15459` es obligatorio para baterías por Art. 77.3 del Reglamento UE 2023/1542. `gs1_digital_link` es el default para sectores sin acto delegado específico (textil, electrónica, mobiliario). Ver [ADR 0001](./adr/0001-identificador-dpp-plugin-declared.md) para el razonamiento.

## Ejemplo paso a paso

Añadir un nuevo campo opcional al plugin de baterías (color del envoltorio):

```yaml
# plugins/batteries.yaml (fragmento)
fields:
  - id: enclosure_color
    type: string
    required: false
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Anexo VI Parte A(6)"
```

Validar que carga:

```bash
cd backend
PYTHONPATH=src uv run python -c \
  "from app.plugins.loader import load_all_plugins; \
   from pathlib import Path; \
   load_all_plugins(Path('../plugins'))"
```

El campo aparece automáticamente en el wizard: `Step3Bom` genera el formulario dinámico a partir del YAML usando React Hook Form. Sin cambios en frontend ni backend.

## Test de contrato

Cualquier plugin debe pasar `backend/tests/plugins/test_contract.py` antes de ser aceptado. El test auto-descubre los `plugins/*.yaml` y verifica 13 invariantes (semver válido, citation no vacía por campo, enum coherente con `enum_values`, sintaxis Python válida en `when` y `rule`, scheme correcto por sector, etc.). Ejecútalo localmente:

```bash
cd backend
PYTHONPATH=src uv run pytest tests/plugins/test_contract.py -v
```

## Cómo enviar el plugin

1. Crea `plugins/<sector>.yaml` siguiendo el schema y el estilo de `batteries.yaml` o `textile.yaml`.
2. **Cita normativa concreta por campo** (`regulation` + `article`). Sin cita, el campo no entra. Si el sector no tiene acto delegado, ancla al Art. 7 del ESPR.
3. Ejecuta el test de contrato y los tests del loader (`pytest tests/test_plugin_loader.py`).
4. Abre un PR contra `main` con título `feat(plugins): añade <sector>.yaml`. Incluye en el cuerpo: reglamento de referencia, número de campos required/opcionales, justificación del `identifier_scheme` elegido.

No hace falta más infraestructura: ni migración de base de datos, ni cambios en el frontend, ni nuevas dependencias.
