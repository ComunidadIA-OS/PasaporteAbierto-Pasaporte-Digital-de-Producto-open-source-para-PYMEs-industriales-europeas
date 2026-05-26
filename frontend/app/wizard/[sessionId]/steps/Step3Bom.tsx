// Paso 3 del wizard: BOM dinámico generado desde el plugin YAML (F4-03).
//
// - Carga GET /plugins/{name} para tener la definición completa de campos.
// - Genera inputs según `type` (string/number/integer/boolean/enum/repeater).
// - Cada campo con asterisco si required + icono "i" con la cita normativa.
// - Submit → PUT /bom; los errores devueltos por el backend se pintan por
//   campo. Continuar al paso 4 se habilita si la respuesta es `accepted`.
//
// Criterio de F4-03 §1: cambiar el plugin re-renderiza el formulario sin
// modificación de código. Aquí se cumple porque el render depende del
// `plugin.fields` cargado, no de hardcoded.

"use client";

import { useEffect, useMemo, useRef, useState, useTransition } from "react";
import { useForm } from "react-hook-form";

import {
  ApiError,
  api,
  type BomValidationError,
  type PluginDetail,
  type PluginFieldDefinition,
  type SessionState,
} from "@/app/lib/api";

type FormValues = Record<string, unknown>;

export function Step3Bom({
  session,
  onSessionChange,
}: {
  session: SessionState;
  onSessionChange: (s: SessionState) => void;
}) {
  const [plugin, setPlugin] = useState<PluginDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [serverErrors, setServerErrors] = useState<BomValidationError[]>([]);
  const [pending, startTransition] = useTransition();

  const { register, handleSubmit, reset } = useForm<FormValues>({
    defaultValues: session.bom as FormValues,
  });

  // Mantener el último BOM visto en una ref evita meter `session.bom` en las
  // deps del useEffect: cada PATCH cambia la referencia del objeto y haría
  // `reset(defaults)` cada vez, sobreescribiendo los edits no guardados del
  // usuario. Sólo re-sembramos al montar o cuando cambia el plugin.
  const bomRef = useRef(session.bom);
  bomRef.current = session.bom;

  useEffect(() => {
    if (!session.plugin) return;
    let cancelled = false;
    api
      .getPluginDetail(session.plugin)
      .then((detail) => {
        if (cancelled) return;
        setPlugin(detail);
        const defaults: FormValues = {};
        for (const f of detail.fields) {
          defaults[f.id] = (bomRef.current as FormValues)[f.id] ?? defaultFor(f);
        }
        reset(defaults);
      })
      .catch((err) => {
        if (cancelled) return;
        setLoadError(
          err instanceof ApiError
            ? `Error ${err.status} cargando plugin ${session.plugin}`
            : "No se pudo cargar la definición del plugin",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [session.plugin, reset]);

  const errorByField = useMemo(() => {
    const m = new Map<string, string>();
    for (const e of serverErrors) m.set(e.field_id, e.message);
    return m;
  }, [serverErrors]);

  function onSubmit(values: FormValues) {
    if (!plugin) return;
    const coerced = coerceForBackend(values, plugin.fields);
    setServerErrors([]);
    startTransition(async () => {
      try {
        const r = await api.putBom(session.session_id, { fields: coerced });
        setServerErrors(r.errors);
        if (r.accepted) {
          const updated = await api.updateProgress(session.session_id, { step: 4 });
          onSessionChange(updated);
        }
      } catch (err) {
        setServerErrors([
          {
            field_id: "__global__",
            message: err instanceof ApiError ? `Error ${err.status}` : "Save falló",
          },
        ]);
      }
    });
  }

  if (!session.plugin) {
    return (
      <p className="status-panel is-warn">
        Necesitas clasificar el sector en el paso 2 antes de rellenar el BOM.
      </p>
    );
  }
  if (loadError) {
    return <p className="status-panel is-danger">{loadError}</p>;
  }
  if (!plugin) {
    return <p className="muted">Cargando definición del plugin…</p>;
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      style={{ display: "flex", flexDirection: "column", gap: 24 }}
    >
      <header>
        <h2 className="typ-3" style={{ margin: 0 }}>
          BOM · {plugin.name}{" "}
          <span className="muted" style={{ fontWeight: 400 }}>
            ({plugin.regulation})
          </span>
        </h2>
        <p className="muted" style={{ margin: "6px 0 0", fontSize: 12 }}>
          {plugin.fields.length} campos · marcados con{" "}
          <span style={{ color: "var(--danger)" }}>*</span> son obligatorios. Los datos se guardan
          con <code className="mono">provenance=self_declared</code>.
        </p>
      </header>

      <div
        style={{
          display: "grid",
          gap: 16,
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
        }}
      >
        {plugin.fields.map((field) => (
          <FieldRow
            key={field.id}
            field={field}
            register={register}
            error={errorByField.get(field.id)}
          />
        ))}
      </div>

      {serverErrors.length > 0 && (
        <div className="status-panel is-warn" style={{ padding: 12, fontSize: 12 }}>
          {serverErrors.length} aviso{serverErrors.length === 1 ? "" : "s"} del backend. Los campos
          marcados en rojo necesitan revisión.
        </div>
      )}

      <div>
        <button type="submit" disabled={pending} className="btn btn-primary btn-lg">
          {pending ? "Guardando…" : "Guardar y continuar al paso 4 →"}
        </button>
      </div>
    </form>
  );
}

/** Convierte un id snake_case en texto legible: battery_mass_kg → Battery mass kg */
function humanizeId(id: string): string {
  const words = id.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function FieldRow({
  field,
  register,
  error,
}: {
  field: PluginFieldDefinition;
  register: ReturnType<typeof useForm<FormValues>>["register"];
  error: string | undefined;
}) {
  const displayLabel = field.label ?? humanizeId(field.id);
  const citation = `${field.citation.regulation}, ${field.citation.article}`;
  const labelStyle: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: 6,
    fontSize: 12,
    fontWeight: 500,
    color: error ? "var(--danger)" : "var(--text)",
    marginBottom: 6,
  };
  const inputClass = `input${error ? " input-error" : ""}`;
  const inputStyle: React.CSSProperties = error ? { borderColor: "var(--danger)" } : {};

  return (
    <label htmlFor={field.id} style={{ display: "block" }}>
      <span style={labelStyle}>
        <span>
          {displayLabel}
          {field.required && <span style={{ marginLeft: 2, color: "var(--danger)" }}>*</span>}
        </span>
        <span
          role="img"
          title={citation}
          aria-label={`Cita: ${citation}`}
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 18,
            height: 18,
            borderRadius: "50%",
            border: "1px solid var(--border-strong)",
            fontSize: 10,
            color: "var(--accent)",
            cursor: "help",
            fontFamily: "var(--font-head)",
            fontStyle: "italic",
          }}
        >
          i
        </span>
      </span>

      {field.type === "boolean" ? (
        <input id={field.id} type="checkbox" {...register(field.id)} />
      ) : field.type === "enum" ? (
        <select id={field.id} {...register(field.id)} className="select" style={inputStyle}>
          <option value="">— seleccionar —</option>
          {(field.enum_values ?? []).map((v) => (
            <option key={v} value={v}>
              {v}
            </option>
          ))}
        </select>
      ) : field.type === "repeater" ? (
        <textarea
          id={field.id}
          {...register(field.id)}
          rows={2}
          placeholder='["item1", "item2"]'
          className="textarea mono"
          style={{ ...inputStyle, fontSize: 12, minHeight: 64 }}
        />
      ) : (
        <input
          id={field.id}
          type={field.type === "string" ? "text" : "number"}
          step={field.type === "integer" ? 1 : "any"}
          {...register(field.id)}
          className={inputClass}
          style={inputStyle}
        />
      )}

      {error && (
        <span style={{ display: "block", marginTop: 4, fontSize: 11, color: "var(--danger)" }}>
          {error}
        </span>
      )}
    </label>
  );
}

function defaultFor(field: PluginFieldDefinition): unknown {
  switch (field.type) {
    case "boolean":
      return false;
    case "repeater":
      return "";
    default:
      return "";
  }
}

function coerceForBackend(
  values: FormValues,
  fields: PluginFieldDefinition[],
): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of fields) {
    const v = values[f.id];
    if (v === undefined || v === "" || v === null) continue;
    if (f.type === "number") {
      const n = Number(v);
      if (!Number.isNaN(n)) out[f.id] = n;
    } else if (f.type === "integer") {
      const n = Number.parseInt(String(v), 10);
      if (!Number.isNaN(n)) out[f.id] = n;
    } else if (f.type === "boolean") {
      out[f.id] = Boolean(v);
    } else if (f.type === "repeater") {
      try {
        const parsed = JSON.parse(String(v));
        if (Array.isArray(parsed)) out[f.id] = parsed;
      } catch {
        // valor sin parsear; se queda fuera y el backend pedirá required si aplica
      }
    } else {
      out[f.id] = v;
    }
  }
  return out;
}
