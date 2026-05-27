// Navegador de productos del dashboard: un desplegable filtra entre todos /
// en curso / finalizados, y debajo se listan las tarjetas de cada DPP.
//
// Client Component: el filtro y el desplegable necesitan estado e interacción.
// Recibe las sesiones ya cargadas por el Server Component (DashboardPage).

"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";

import type { SessionSummary } from "@/core/responses";
import { Icon } from "@/core/ui/Icon";

type Filter = "all" | "in_progress" | "done";

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "Todos" },
  { id: "in_progress", label: "En curso" },
  { id: "done", label: "Finalizados" },
];

const TOTAL_STEPS = 7;

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

function ProductCard({ s }: { s: SessionSummary }) {
  const done = s.published;
  const pct = Math.round((Math.min(s.current_step, TOTAL_STEPS) / TOTAL_STEPS) * 100);
  return (
    <li>
      <Link href={`/wizard/${s.session_id}`} className={`product-card${done ? " is-done" : ""}`}>
        <span className="pc-mark">
          <Icon name={done ? "verified" : "edit_document"} size={20} fill={done} />
        </span>
        <div className="pc-body">
          <p className="pc-title">{s.description?.trim() || "Sin descripción todavía"}</p>
          <p className="pc-meta">
            {s.sector ? `${s.sector} · ` : ""}
            {done ? "Publicado" : `Paso ${s.current_step} de ${TOTAL_STEPS}`} · actualizado{" "}
            {formatDate(s.updated_at)}
          </p>
          {!done && (
            <div
              className="product-progress"
              role="progressbar"
              aria-valuenow={pct}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <span style={{ width: `${pct}%` }} />
            </div>
          )}
        </div>
        <div className="pc-tags">
          <span className={`badge ${done ? "badge-success" : "badge-warn"}`}>
            {done ? "publicado" : "en curso"}
          </span>
          {s.has_chat && <span className="badge badge-neutral">con chat</span>}
        </div>
        <span className="pc-cta">
          {done ? "Ver DPP" : "Continuar"}
          <Icon name="chevron_right" size={15} />
        </span>
      </Link>
    </li>
  );
}

export function ProductBrowser({ sessions }: { sessions: SessionSummary[] }) {
  const [filter, setFilter] = useState<Filter>("all");
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  // Cerrar el desplegable al hacer clic fuera o pulsar Escape.
  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const counts = {
    all: sessions.length,
    in_progress: sessions.filter((s) => !s.published).length,
    done: sessions.filter((s) => s.published).length,
  };
  const visible = sessions.filter((s) =>
    filter === "all" ? true : filter === "done" ? s.published : !s.published,
  );
  const activeLabel = FILTERS.find((f) => f.id === filter)?.label ?? "Todos";

  return (
    <section>
      <div className="dash-toolbar">
        <div className="eyebrow">Mis productos</div>
        <div className="dropdown" ref={wrapRef}>
          <button
            type="button"
            className="dropdown-trigger"
            aria-haspopup="menu"
            aria-expanded={open}
            aria-controls={menuId}
            onClick={() => setOpen((v) => !v)}
          >
            <Icon name="filter_list" size={18} />
            {activeLabel}
            <Icon name="expand_more" size={18} className="chev" />
          </button>
          {open && (
            <div className="dropdown-menu" id={menuId} role="menu">
              {FILTERS.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  role="menuitemradio"
                  aria-checked={filter === f.id}
                  className={`dropdown-item${filter === f.id ? " is-active" : ""}`}
                  onClick={() => {
                    setFilter(f.id);
                    setOpen(false);
                  }}
                >
                  {f.label}
                  <span className="count">{counts[f.id]}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {visible.length === 0 ? (
        <div className="dash-empty">
          {sessions.length === 0 ? (
            <p style={{ margin: 0 }}>
              Todavía no has empezado ningún pasaporte. Pulsa <strong>Nuevo DPP</strong> para
              comenzar.
            </p>
          ) : (
            <p style={{ margin: 0 }}>
              No tienes productos {filter === "done" ? "finalizados" : "en curso"} ahora mismo.
            </p>
          )}
        </div>
      ) : (
        <ul className="product-list">
          {visible.map((s) => (
            <ProductCard key={s.session_id} s={s} />
          ))}
        </ul>
      )}
    </section>
  );
}
