<!--
Gracias por contribuir. Recuerda: los PRs van contra `develop`, no contra `main`.
Lee CONTRIBUTING.md si es tu primera contribución.
-->

## Qué hace

<!-- Resumen breve del cambio. -->

## Motivación

<!-- Qué problema resuelve o qué requisito cubre. Enlaza el issue/ticket: Closes #..., F3-02… -->

## Decisiones no obvias

<!-- Alternativas descartadas, tradeoffs, invariantes respetadas. Borra si no aplica. -->

## Impacto

<!-- Cambios de contrato (API, schema YAML, formato del DPP), migraciones, breaking changes. -->

## Tipo de cambio

- [ ] `feat` — funcionalidad nueva
- [ ] `fix` — corrección de error
- [ ] `refactor` / `perf`
- [ ] `docs`
- [ ] `test`
- [ ] `chore` / `build` / `ci`
- [ ] Plugin sectorial nuevo

## Checklist

- [ ] El PR apunta a `develop`.
- [ ] `uv run pytest` y `uv run ruff check .` pasan en el backend (si aplica).
- [ ] `pnpm test` y `pnpm lint` pasan en el frontend (si aplica).
- [ ] Los cambios de comportamiento llegan con tests.
- [ ] Commits siguen Conventional Commits en castellano, sin trailers de IA (`Co-Authored-By:`).
- [ ] Documentación actualizada si cambia un contrato o el comportamiento visible.
- [ ] Respeta las invariantes de `docs/ARCHITECTURE.md` (solo 2 pasos IA, chat fuera del estado del wizard, cita normativa obligatoria, no DPP parcial conforme, extensibilidad por YAML, audit hash chain).
- [ ] Sin secretos ni datos sensibles en el código, commits o capturas.
