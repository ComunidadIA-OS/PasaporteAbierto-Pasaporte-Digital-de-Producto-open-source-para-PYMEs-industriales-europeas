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

import { useEffect, useMemo, useState, useTransition } from "react";
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

  useEffect(() => {
    if (!session.plugin) return;
    api
      .getPluginDetail(session.plugin)
      .then((detail) => {
        setPlugin(detail);
        // Re-sembrar defaults con los nombres de campos del plugin.
        const defaults: FormValues = {};
        for (const f of detail.fields) {
          defaults[f.id] = (session.bom as FormValues)[f.id] ?? defaultFor(f);
        }
        reset(defaults);
      })
      .catch((err) =>
        setLoadError(
          err instanceof ApiError
            ? `Error ${err.status} cargando plugin ${session.plugin}`
            : "No se pudo cargar la definición del plugin",
        ),
      );
  }, [session.plugin, session.bom, reset]);

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
      <p className="rounded-xl bg-amber-50 p-4 text-sm text-amber-900 shadow">
        Necesitas clasificar el sector en el paso 2 antes de rellenar el BOM.
      </p>
    );
  }
  if (loadError) {
    return <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700 shadow">{loadError}</p>;
  }
  if (!plugin) {
    return <p className="text-sm text-gray-500">Cargando definición del plugin…</p>;
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="animate-fade-in space-y-6">
      <header>
        <h2 className="text-lg font-semibold">
          BOM · {plugin.name}{" "}
          <span className="font-normal text-gray-500">({plugin.regulation})</span>
        </h2>
        <p className="text-xs text-gray-500">
          {plugin.fields.length} campos · marcados con <span className="text-red-600">*</span> son
          obligatorios. Los datos se guardan con <code>provenance=self_declared</code>.
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
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
        <div className="rounded-xl bg-amber-50 p-3 text-xs text-amber-900 shadow">
          {serverErrors.length} aviso{serverErrors.length === 1 ? "" : "s"} del backend. Los campos
          marcados en rojo necesitan revisión.
        </div>
      )}

      <button
        type="submit"
        disabled={pending}
        className="rounded-xl bg-gradient-to-r from-teal-600 to-teal-500 px-6 py-2 text-sm font-semibold text-white shadow disabled:bg-none disabled:bg-gray-300"
      >
        {pending ? "Guardando…" : "Guardar y continuar al paso 4 →"}
      </button>
    </form>
  );
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
  const citation = `${field.citation.regulation}, ${field.citation.article}`;
  const labelClass = `flex items-center gap-1 text-xs font-semibold ${
    error ? "text-red-700" : "text-gray-700"
  }`;
  const inputClass = `mt-1 w-full rounded-xl border p-2 text-sm shadow-sm focus:border-teal-500 focus:ring-1 focus:ring-teal-500 ${
    error ? "border-red-400" : "border-gray-300"
  }`;

  return (
    <label htmlFor={field.id} className="block">
      <span className={labelClass}>
        <span>
          {field.id}
          {field.required && <span className="ml-0.5 text-red-600">*</span>}
        </span>
        {/* biome-ignore lint/a11y/useAriaPropsSupportedByRole: decorative tooltip */}
        <span
          title={citation}
          className="inline-flex h-4 w-4 cursor-help items-center justify-center rounded-full border border-gray-300 text-[10px] text-gray-500"
          aria-label={`Cita: ${citation}`}
        >
          i
        </span>
      </span>

      {field.type === "boolean" ? (
        <input id={field.id} type="checkbox" {...register(field.id)} className="mt-1" />
      ) : field.type === "enum" ? (
        <select id={field.id} {...register(field.id)} className={inputClass}>
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
          className={`${inputClass} font-mono text-xs`}
        />
      ) : (
        <input
          id={field.id}
          type={field.type === "string" ? "text" : "number"}
          step={field.type === "integer" ? 1 : "any"}
          {...register(field.id)}
          className={inputClass}
        />
      )}

      {error && <span className="mt-1 block text-xs text-red-700">{error}</span>}
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
