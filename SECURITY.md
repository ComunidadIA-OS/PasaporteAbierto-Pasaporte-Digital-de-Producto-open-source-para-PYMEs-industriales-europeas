# Política de seguridad

PasaporteAbierto trata datos de producto que pueden alimentar decisiones regulatorias (DPP
conforme al Reglamento UE 2024/1781). Nos tomamos la seguridad en serio y agradecemos el
reporte responsable de vulnerabilidades.

## Versiones soportadas

El proyecto está en desarrollo inicial (`0.x`). Solo la última versión publicada recibe
parches de seguridad.

| Versión | Soporte |
|---|---|
| `0.1.x` | ✅ |
| < `0.1` | ❌ |

## Cómo reportar una vulnerabilidad

**No abras un issue público** para reportar una vulnerabilidad. Usa la divulgación coordinada
privada:

1. Ve a la pestaña **Security** del repositorio →
   [**Report a vulnerability**](https://github.com/ComunidadIA-OS/PasaporteAbierto-Pasaporte-Digital-de-Producto-open-source-para-PYMEs-industriales-europeas/security/advisories/new)
   (GitHub Private Vulnerability Reporting).
2. Describe el problema, su impacto y, si puedes, una prueba de concepto y los pasos para
   reproducirlo.

Si no puedes usar el canal de GitHub, escribe a
**luis.bravo@logixsdigital.com**.

### Qué esperar

- **Acuse de recibo** en un plazo de 72 horas.
- **Evaluación inicial** (severidad, alcance) en un plazo de 7 días.
- Te mantendremos al tanto del progreso del parche y coordinaremos contigo la fecha de
  divulgación pública. Reconoceremos tu aporte salvo que prefieras permanecer anónima.

Te pedimos un plazo razonable para publicar el parche antes de divulgar el detalle públicamente.

## Alcance y modelo de amenaza

PasaporteAbierto está diseñado como instancia **auto-hospedable y single-tenant** (una
instancia = un fabricante). Esto condiciona el modelo de amenaza:

- **Sin multi-tenant ni OAuth** en el alcance actual. La protección de red (red local, VPN,
  proxy inverso con TLS, basic auth) es responsabilidad de quien despliega.
- **Sin secretos en el código.** Las claves van en `.env` (no versionado); compara contra
  [`.env.example`](./.env.example).
- **El endpoint público del DPP** (`GET /dpp/{slug}`) expone **solo** los campos con
  `access_level = public`. El resto de niveles de acceso del Anexo XIII no se sirven por esa vía.

### Controles de seguridad ya integrados

- **Firma Ed25519 (PyNaCl)** de cada DPP publicado: integridad y autenticidad verificables.
- **Audit log con hash chain** en SQLite: cada operación significativa encadena `prev_hash`;
  `GET /api/v1/audit/verify` recorre la cadena y detecta manipulación.
- **Citas normativas obligatorias** en el chat: mitiga alucinaciones del LLM con base
  documental verificable.

Reportes sobre el endurecimiento de despliegue (cabeceras HTTP, rate limiting, hardening del
contenedor) también son bienvenidos aunque queden fuera del alcance single-tenant por defecto.
