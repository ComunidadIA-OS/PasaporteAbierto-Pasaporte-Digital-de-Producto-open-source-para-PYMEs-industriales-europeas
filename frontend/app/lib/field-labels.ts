// Utilidades compartidas para resolver labels legibles de campos de plugin.
//
// Extraído de Step3Bom para reutilizar en Step5Extract y Step6Verify.
// El plugin YAML puede declarar un `label` por campo; si no existe,
// `humanizeId` convierte el id snake_case a texto capitalizado.

import { useEffect, useState } from "react";

import { api, type PluginFieldDefinition } from "./api";

/** Convierte un id snake_case en texto legible: battery_mass_kg → Battery mass kg */
export function humanizeId(id: string): string {
  const words = id.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** Resuelve el label de un campo dado su field_id y un mapa de definiciones. */
export function resolveLabel(
  fieldId: string,
  fieldsMap: Map<string, PluginFieldDefinition>,
): string {
  const def = fieldsMap.get(fieldId);
  return def?.label ?? humanizeId(fieldId);
}

/**
 * Hook que carga la definición del plugin y devuelve un mapa field_id → PluginFieldDefinition.
 * Devuelve `null` mientras carga.
 */
export function usePluginFields(
  pluginName: string | null,
): Map<string, PluginFieldDefinition> | null {
  const [fieldsMap, setFieldsMap] = useState<Map<string, PluginFieldDefinition> | null>(null);

  useEffect(() => {
    if (!pluginName) return;
    let cancelled = false;
    api
      .getPluginDetail(pluginName)
      .then((detail) => {
        if (cancelled) return;
        const map = new Map<string, PluginFieldDefinition>();
        for (const f of detail.fields) map.set(f.id, f);
        setFieldsMap(map);
      })
      .catch(() => {
        // Si falla, dejamos null — los componentes usarán humanizeId como fallback.
      });
    return () => {
      cancelled = true;
    };
  }, [pluginName]);

  return fieldsMap;
}
