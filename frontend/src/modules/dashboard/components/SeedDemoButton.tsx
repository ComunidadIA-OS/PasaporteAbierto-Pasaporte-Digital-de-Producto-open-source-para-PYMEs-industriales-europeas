// Botón (solo modo demo) que siembra DPP de ejemplo —en curso y finalizados—
// para el usuario actual, sin pasar por los pasos IA. Permite ver el dashboard
// poblado al instante. Tras sembrar, refresca los datos del Server Component.

"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Icon } from "@/core/ui/Icon";
import { api } from "@/modules/wizard/lib/wizard-api";

export function SeedDemoButton() {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function onSeed() {
    setPending(true);
    try {
      await api.seedDemoDashboard();
      // Refresca los datos del dashboard (Server Component) sin recarga completa.
      router.refresh();
    } catch {
      // best-effort; si falla, el usuario puede reintentar.
    } finally {
      setPending(false);
    }
  }

  return (
    <button
      type="button"
      onClick={onSeed}
      disabled={pending}
      className="btn btn-secondary btn-lg"
      title="Crea DPP de ejemplo (en curso y finalizados) para probar el dashboard"
    >
      <Icon name="auto_awesome" size={18} />
      {pending ? "Generando…" : "Generar ejemplos"}
    </button>
  );
}
