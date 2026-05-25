# Reglas del Hackathon — "IA Responsable y Abierta en Industria" (Mayo'26)

Documento de referencia para **todo el equipo y para Claude Code**. Cada vez
que se propongan cambios al repo, hay que respetar estas reglas. Fuente:
Términos y condiciones publicados por SEDIA + AESIA (ver
`docs/hackathon/terminos_y_condiciones.pdf` si lo adjuntáis al repo).

> **Para Claude:** antes de implementar, refactorizar o documentar, comprueba
> que el cambio cumple las invariantes de la sección "Reglas duras". Si una
> propuesta entra en conflicto con ellas, **la regla del hackathon gana** —
> avisa antes de proseguir.

---

## Calendario crítico

| Fecha | Hito | Implicación práctica |
|---|---|---|
| **22 may 2026 12:00** | Apertura oficial de la fase online | A efectos de evaluación, **solo cuenta el código a partir de esta fecha**. Lo anterior es "software preexistente" y hay que declararlo (ver §Reglas duras). |
| **27 may 2026 23:59** | Entrega del **repositorio + README.md** | Repo público con licencia OSS, README completo. |
| **29 may 2026 23:59** | Entrega del **vídeo demo + evaluación HRIA** | Demo real ejecutable + autoevaluación impacto DD.HH. (UNDP). |
| **2 jun 2026** | Presentación final presencial en Zaragoza | 10 min presentación + demo + preguntas del jurado. |

**Faltar a un plazo = exclusión automática.** Sin excepciones.

---

## Reglas duras (invariantes del hackathon)

1. **Open source obligatorio.** Licencia reconocida por [OSI](https://opensource.org/licenses) o [FSF](https://www.gnu.org/licenses/license-list.html). El proyecto tiene `LICENSE` con **Apache 2.0** — no cambiar sin discusión.
2. **Repo 100% público.** Nada de carpetas, ramas o submódulos privados. Sin secretos en el código (revisar `.env.example` vs `.env`).
3. **IA como elemento relevante.** En este repo los dos pasos IA son el Clasificador (paso 2) y el Recolector (paso 5). Si en algún momento alguien propone hacerlos deterministas, lo bloqueamos: rompería el requisito.
4. **Aplicabilidad industrial / PYMES.** Cualquier feature nueva debe seguir orientada a fabricantes PYME europeos generando su DPP. Refactors que se alejen del caso de uso → rechazar.
5. **TRL al cierre: ≥3.** "Función crítica analítica y experimental + prueba de concepto ejecutable". En la práctica: el pipeline de 7 pasos tiene que ejecutar end-to-end sobre **al menos un sector real (baterías)** y emitir un DPP firmado. Documentación sola = exclusión.
6. **Demo ejecutable, no maqueta.** El vídeo del 29-may tiene que enseñar el sistema real corriendo (`docker compose up` → wizard → DPP publicado). Mockups, screenshots animados o "lo que haría si funcionara" → exclusión.
7. **Reproducible por terceros.** `git clone` + seguir el README → el sistema arranca. Esto ya lo cubre el README de F1; **no romperlo** en fases posteriores.
8. **Software preexistente declarado.** Cualquier dependencia o snippet adoptado *antes del 22-may-2026* debe:
   - Aparecer en `pyproject.toml`/`package.json` (no copiar/pegar código).
   - Ser licencia compatible con Apache 2.0 (evitar GPL/AGPL en deps directas).
   - Quedar identificado en el README si es un componente nuclear.
9. **Sin confidencialidad.** Todo lo que se haga aquí es público. No anotar datos sensibles ni nombres de clientes reales en docs, commits o issues.
10. **Lenguaje inclusivo y código de conducta.** Aplica a commits, issues, PRs, docs y comentarios de Claude. Sin lenguaje despectivo ni excluyente.

---

## Cómo se nos evalúa (peso de cada criterio)

| Criterio | Peso | Qué significa para nuestras decisiones de código |
|---|---|---|
| **Impacto** | 30% | Justificar utilidad real para PYMEs industriales. El README y la demo tienen que contar la historia "antes vs. después" desde la perspectiva de un fabricante. |
| **Innovación** | 30% | Diferenciarnos de soluciones existentes (consultoras de DPP, plataformas SaaS cerradas). Argumentos: auto-hospedable, plugin-based extensible, sin vendor lock-in, RAG con cita normativa. |
| **Alineamiento OSS** | 25% | Devolver contribuciones, security by design (audit log, firma Ed25519, OWASP en LLM router), participación inclusiva, diseño reutilizable (sistema de plugins). |
| **Comunicación** | 15% | Claridad del README, del vídeo y de la presentación. |

**Implicación práctica:** cuando elijas entre dos diseños similares, prioriza el que mejor encaje en estos cuatro ejes. No basta con que "funcione".

---

## Entregables — checklist al cierre de cada fase

Al terminar F2, F3, F4… revisar que el repo sigue cumpliendo:

- [ ] `README.md` actualizado: descripción, instalación, uso, **hoja de ruta**.
- [ ] `docker compose up` arranca limpio (verificado, no declarativo).
- [ ] `LICENSE` (Apache 2.0) presente y referenciado.
- [ ] Sin secretos commiteados (`grep -r "sk-" .` y similares).
- [ ] CI verde (lint + tests).
- [ ] Demo del pipeline end-to-end ejecutable en local.

Antes del 27-may: verificar también que el repo es **público en GitHub** y que cualquier persona con la URL puede clonarlo, instalarlo y ejecutarlo.

Antes del 29-may: grabar vídeo demo + completar [evaluación HRIA del UNDP](https://hria.eu/#use-cases).

---

## Reconocimientos (motivación)

- **1º lugar:** hasta 3 personas viajan al hackathon de la ONU "UN Tech Over" en Nueva York (jun'26). Vuelo desde Madrid + alojamiento cubiertos. Visados / ESTA / seguros = a nuestra cuenta.
- **1º-3º lugar:** participación en el South Summit Madrid en el stand de SEDIA.

---

## Datos del equipo (rellenar antes del 19-may)

> Estos datos los pide el formulario de inscripción. Tenerlos preparados.

- Nombre del equipo: _pendiente_
- Persona de contacto: _pendiente_
- Tipo de entidad: _pendiente_
- Sector de actividad: Industria y manufactura
- TRL inicial declarado: **TRL 2** (Concepto formulado — al inscribir)
- TRL objetivo al cierre: **TRL 4** (Validación de componente en entorno de laboratorio)
- ¿Han desarrollado OSS antes?: _pendiente_

---

## Contacto oficial del hackathon

`comunidad.ia.os@digital.gob.es` — sólo la persona de contacto del equipo debería escribir.
