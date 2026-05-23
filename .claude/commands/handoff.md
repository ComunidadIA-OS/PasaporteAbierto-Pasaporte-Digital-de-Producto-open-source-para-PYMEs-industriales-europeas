---
description: Cierra el TODO en curso y escribe un handoff en docs/handoffs/ para retomar la sesión más tarde.
---

# /handoff — protocolo de cierre de sesión

El usuario ha disparado este comando porque la cuota del plan de Anthropic está a punto de agotarse (típicamente al ~10% restante). Tu misión es **parar de forma segura** y dejar un documento de handoff suficiente para retomar el trabajo en una sesión nueva.

Sigue este protocolo al pie. No improvises, no añadas pasos, no commitees nada.

## Paso 1 — Para de aceptar trabajo nuevo

- No abras TODOs nuevos en `TodoWrite`.
- No lances subagentes nuevos vía el tool `Agent`.
- Si hay subagentes corriendo en background, espera a su próximo `TaskOutput` natural; no lances ninguno más.

## Paso 2 — Cierra el TODO en curso (solo ese)

Mira tu lista de TODOs. Identifica el que está marcado como `in_progress`. Ciérralo según su naturaleza:

- **Edición de archivo a medias:** déjalo en estado coherente (no a mitad de un bloque ni con sintaxis rota *si puedes evitarlo con un edit puntual*). Si requiere arreglar de más para que compile, **NO lo arregles**: déjalo como esté y documéntalo en el handoff.
- **Comando largo en ejecución:** espera a que termine. No lo mates.
- **Investigación / lectura:** márcalo como completado si tienes ya la conclusión; si no, márcalo parcial y documenta lo encontrado en el handoff.

**No abras el siguiente TODO de la lista**, aunque sea trivial. Tampoco lances `Agent` para "dejar avanzado" nada.

## Paso 3 — Escribe el handoff

### Ruta y nombre

- Carpeta: `docs/handoffs/` (créala si no existe).
- Nombre: `YYYY-MM-DD-HHMM.md` con fecha y hora locales del momento en que escribes el archivo.
- Si ya existe un archivo con ese mismo minuto, añade sufijo `-2`, `-3`, etc. **No sobrescribas.**

### Datos a recoger ANTES de escribir

Ejecuta en paralelo, son lecturas baratas:

- `git branch --show-current` — rama actual.
- `git status --short` — estado del working tree.

Si no estás en un repo git, los dos comandos fallarán; en ese caso las líneas correspondientes del handoff van vacías.

### Estructura exacta del archivo

```markdown
# Handoff — <YYYY-MM-DD HH:MM>

## Estado actual

- **Ticket / fase:** <p. ej. F1-02 — scaffolding backend; si no sabes, "sin ticket identificado">
- **Rama git:** <output de `git branch --show-current`>
- **Último TODO cerrado:** <descripción + estado: completo / parcial / revertido / roto-a-propósito>
- **TODOs pendientes (de la lista de la sesión):**
  - [ ] …
  - [ ] …
- **Working tree:** <resumen 1-2 líneas de `git status --short`; menciona explícitamente si hay archivos que quedan a medias o con build/tests rotos>

## Decisiones tomadas

Decisiones técnicas no obvias hechas en esta sesión, con su porqué.
Solo las que NO son obvias del commit/diff ni están ya en CLAUDE.md / ARCHITECTURE.md / FUNCIONAL.md.
Cita el doc cuando una decisión se apoya en él (p. ej. "§9 FUNCIONAL.md").

- **<Decisión 1>:** <qué se eligió y por qué; alternativa descartada si aplica>.
- **<Decisión 2>:** …

(Si no hubo decisiones no obvias en la sesión, escribe literalmente: "Ninguna decisión no obvia en esta sesión.")

## Próximos pasos

Bullets accionables, imperativo. Cada bullet es algo que se pueda empezar a hacer sin re-investigar.
Incluye archivo y/o comando concreto cuando aplique. Nada de "explorar X" sin más.

1. **<Siguiente>:** <acción concreta, archivo/comando si aplica>.
2. **<Después>:** …
3. **<Después>:** …
```

### Reglas de redacción

- **Estado actual:** factual, derivado de `TodoWrite`, `git status` y `git branch`. No interpretes.
- **Decisiones:** solo no obvias (descartes, tradeoffs, invariantes respetadas). Una decisión trivial ("usé el endpoint que pedía el ticket") **no entra**.
- **Próximos pasos:** imperativo + archivo o comando concreto. Si el siguiente paso es genuinamente investigación, el bullet es "investigar X consultando Y", no "ver si Y".
- Idioma: castellano (convención del proyecto, ver CLAUDE.md).

## Paso 4 — Devuelve control

Mensaje final al usuario, **una o dos líneas máximo**. Plantilla:

> Handoff escrito en `docs/handoffs/<archivo>.md`. Working tree sin tocar — decides tú qué commitear.

Nada de resumen largo de la sesión. Nada de "¿quieres que…?". El usuario ya tiene el `.md`.

## Restricciones de git (importante)

En este flujo **NO ejecutes**:

- `git add`, `git commit`, `git stash`, `git restore`, `git reset`, `git checkout <archivos>`, `git clean`.

**Sí puedes** (son lecturas):

- `git status --short`, `git branch --show-current`, `git log` si necesitas contexto del último commit para el handoff.

El usuario decide qué hacer con el working tree después de leer el handoff.

## Casos límite

- **Sin TODOs activos al invocar /handoff:** salta el paso 2. En el handoff escribe `Último TODO cerrado: ninguno (sesión sin lista activa)` y rellena el resto con lo que se haya trabajado.
- **Subagente sigue corriendo:** si decides no esperarlo (porque puede tardar mucho), documéntalo en Estado actual: `subagente <id> seguía corriendo al cierre`. Marca el TODO asociado como parcial.
- **Working tree con build/tests rotos:** **no intentes arreglarlo**. Es la regla explícita del usuario. Documéntalo claramente en Estado actual (qué archivo está roto, qué cambio quedó a medias).
- **No estás en un repo git:** las líneas de rama y working tree van vacías; el resto del handoff se escribe igual.
