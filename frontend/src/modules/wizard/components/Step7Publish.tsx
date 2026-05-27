// Paso 7 del wizard: Publicar DPP (F4-06).
//
// - Si aún no se ha publicado: muestra botón "Publicar DPP" → POST /dpp.
// - Si ya está publicado: muestra QR (imagen PNG inline) + descargas
//   PNG/SVG + URL pública copiable.
//
// 409 cannot_publish vuelve al paso 6.

"use client";

import { useEffect, useState, useTransition } from "react";

import { Icon } from "@/core/ui/Icon";
import {
  ApiError,
  api,
  type DppResponse,
  type SessionState,
} from "@/modules/wizard/lib/wizard-api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function Step7Publish({
  session,
  initialDpp,
  onPublished,
}: {
  session: SessionState;
  initialDpp?: DppResponse | null;
  onPublished?: (dpp: DppResponse) => void;
}) {
  const [dpp, setDpp] = useState<DppResponse | null>(initialDpp ?? null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [confirmOpen, setConfirmOpen] = useState(false);

  // initialDpp llega de forma asíncrona (rehidratación del DPP ya publicado al
  // reentrar desde la lista de finalizados): cuando aparece, sincroniza el
  // estado local para mostrar el QR sin necesidad de re-publicar.
  useEffect(() => {
    if (initialDpp) setDpp(initialDpp);
  }, [initialDpp]);

  function publish() {
    setConfirmOpen(false);
    setError(null);
    startTransition(async () => {
      try {
        const r = await api.generateDpp(session.session_id);
        setDpp(r);
        onPublished?.(r);
      } catch (err) {
        if (err instanceof ApiError && err.status === 409) {
          setError("No se puede publicar: rellena los campos pendientes en el paso 6.");
        } else if (err instanceof ApiError) {
          setError(`Error ${err.status} al publicar`);
        } else {
          setError("Publicación falló");
        }
      }
    });
  }

  if (!dpp) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div className="status-panel is-success">
          <h2 className="typ-3" style={{ margin: 0 }}>
            Listo para publicar
          </h2>
          <p className="muted" style={{ marginTop: 8, marginBottom: 0 }}>
            El paso 6 ha verificado que el DPP está completo. Al publicar se firma con Ed25519, se
            persiste en la BD y se genera el QR + URL pública.
          </p>
        </div>

        {error && (
          <p className="status-panel is-danger" style={{ margin: 0, padding: 14 }}>
            {error}
          </p>
        )}

        {!confirmOpen ? (
          <div>
            <button
              type="button"
              onClick={() => setConfirmOpen(true)}
              disabled={pending}
              className="btn btn-primary btn-lg"
            >
              <Icon name="lock" size={18} />
              {pending ? "Publicando…" : "Publicar DPP"}
            </button>
          </div>
        ) : (
          <div
            className="card"
            style={{
              border: "2px solid var(--accent)",
              display: "flex",
              flexDirection: "column",
              gap: 12,
            }}
          >
            <h3 className="typ-3" style={{ margin: 0 }}>
              ¿Confirmar publicación?
            </h3>
            <p className="muted" style={{ margin: 0, fontSize: 13 }}>
              Se firmará el DPP con Ed25519, se persistirá en la BD y se generará el QR + URL
              pública. Esta acción no se puede deshacer.
            </p>
            <div style={{ display: "flex", gap: 12 }}>
              <button
                type="button"
                onClick={publish}
                disabled={pending}
                className="btn btn-primary"
              >
                {pending ? "Publicando…" : "Sí, publicar"}
              </button>
              <button
                type="button"
                onClick={() => setConfirmOpen(false)}
                disabled={pending}
                className="btn btn-secondary"
              >
                Cancelar
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  // public_url ya es absoluta (backend la construye con DPP_PUBLIC_BASE_URL):
  // no anteponer API_BASE o saldría duplicado (http://...http://.../dpp/...).
  const fullPublicUrl = dpp.public_url;
  // qr_*_url sí son relativas (/api/v1/...): necesitan el host del backend.
  const qrPngUrl = `${API_BASE || ""}${dpp.qr_png_url}`;
  const qrSvgUrl = `${API_BASE || ""}${dpp.qr_svg_url}`;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div className="status-panel is-success">
        <h2
          className="typ-2"
          style={{ margin: 0, display: "inline-flex", alignItems: "center", gap: 8 }}
        >
          <Icon name="verified" size={26} fill style={{ color: "var(--success)" }} />
          DPP <em>publicado</em>
        </h2>
        <p className="muted" style={{ marginTop: 8, marginBottom: 0 }}>
          Firmado con Ed25519. Identificador conforme a{" "}
          {dpp.gs1_uri.startsWith("urn:iso15459")
            ? "ISO/IEC 15459 (Art. 77.3 Reg. UE 2023/1542)"
            : "GS1 Digital Link"}
          .
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gap: 24,
          gridTemplateColumns: "1fr",
        }}
      >
        <div className="qr-card">
          <h3 className="eyebrow">QR del producto</h3>
          <div className="qr-frame" style={{ marginTop: 16 }}>
            {/* biome-ignore lint/performance/noImgElement: el QR lo sirve el backend (dpp.qr_png_url); pasarlo por next/image lo re-codificaría perdiendo nitidez y exigiría configurar remotePatterns para el host del API. */}
            <img src={qrPngUrl} alt="QR del DPP" width={192} height={192} />
          </div>
          <div
            style={{
              marginTop: 16,
              display: "flex",
              justifyContent: "center",
              gap: 12,
              fontSize: 12,
            }}
          >
            <a
              href={qrPngUrl}
              download
              style={{ color: "var(--accent)", textDecoration: "underline" }}
            >
              descargar PNG
            </a>
            <span className="faint">·</span>
            <a
              href={qrSvgUrl}
              download
              style={{ color: "var(--accent)", textDecoration: "underline" }}
            >
              descargar SVG
            </a>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <p className="eyebrow">Identificador</p>
            <code
              className="mono"
              style={{
                display: "block",
                marginTop: 6,
                padding: 12,
                background: "var(--panel-2)",
                borderRadius: "var(--radius)",
                fontSize: 12,
                wordBreak: "break-all",
              }}
            >
              {dpp.gs1_uri}
            </code>
          </div>
          <div>
            <p className="eyebrow">URL pública</p>
            <a
              href={fullPublicUrl}
              target="_blank"
              rel="noreferrer"
              className="mono"
              style={{
                display: "block",
                marginTop: 6,
                padding: 12,
                background: "var(--panel-2)",
                borderRadius: "var(--radius)",
                fontSize: 12,
                color: "var(--accent)",
                textDecoration: "underline",
                wordBreak: "break-all",
              }}
            >
              {fullPublicUrl}
            </a>
            <p className="muted" style={{ marginTop: 6, fontSize: 11 }}>
              Devuelve JSON-LD por defecto; HTML cuando el cliente envía{" "}
              <code>Accept: text/html</code>.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
