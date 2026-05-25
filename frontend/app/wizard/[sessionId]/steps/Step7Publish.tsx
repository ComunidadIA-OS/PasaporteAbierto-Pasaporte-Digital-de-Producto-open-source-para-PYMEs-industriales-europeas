// Paso 7 del wizard: Publicar DPP (F4-06).
//
// - Si aún no se ha publicado: muestra botón "Publicar DPP" → POST /dpp.
// - Si ya está publicado: muestra QR (imagen PNG inline) + descargas
//   PNG/SVG + URL pública copiable.
//
// 409 cannot_publish vuelve al paso 6.

"use client";

import { useState, useTransition } from "react";

import { ApiError, api, type DppResponse, type SessionState } from "@/app/lib/api";

const API_BASE = typeof process !== "undefined" ? (process.env.NEXT_PUBLIC_API_URL ?? "") : "";

export function Step7Publish({ session }: { session: SessionState }) {
  const [dpp, setDpp] = useState<DppResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function publish() {
    setError(null);
    startTransition(async () => {
      try {
        const r = await api.generateDpp(session.session_id);
        setDpp(r);
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
      <div className="animate-fade-in space-y-4">
        <div className="rounded-xl border border-green-200 bg-green-50 p-5 shadow">
          <h2 className="text-lg font-semibold text-green-900">Listo para publicar</h2>
          <p className="mt-1 text-sm text-green-800">
            El paso 6 ha verificado que el DPP está completo. Al publicar se firma con Ed25519, se
            persiste en la BD y se genera el QR + URL pública.
          </p>
        </div>

        {error && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700 shadow">{error}</p>}

        <button
          type="button"
          onClick={publish}
          disabled={pending}
          className="rounded-xl bg-gradient-to-r from-teal-600 to-teal-500 px-6 py-2 text-sm font-semibold text-white shadow disabled:bg-none disabled:bg-gray-300"
        >
          {pending ? "Publicando…" : "Publicar DPP"}
        </button>
      </div>
    );
  }

  const fullPublicUrl = `${API_BASE || ""}${dpp.public_url}`;
  const qrPngUrl = `${API_BASE || ""}${dpp.qr_png_url}`;
  const qrSvgUrl = `${API_BASE || ""}${dpp.qr_svg_url}`;

  return (
    <div className="animate-fade-in space-y-6">
      <div className="rounded-xl border border-green-300 bg-green-50 p-5 shadow">
        <h2 className="text-lg font-bold text-green-900">DPP publicado ✓</h2>
        <p className="mt-1 text-sm text-green-800">
          Firmado con Ed25519. Identificador conforme a{" "}
          {dpp.gs1_uri.startsWith("urn:iso15459")
            ? "ISO/IEC 15459 (Art. 77.3 Reg. UE 2023/1542)"
            : "GS1 Digital Link"}
          .
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-5 text-center shadow">
          <h3 className="text-sm font-semibold">QR del producto</h3>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={qrPngUrl} alt="QR del DPP" className="mx-auto mt-3 h-48 w-48" />
          <div className="mt-3 flex justify-center gap-2 text-xs">
            <a href={qrPngUrl} download className="text-teal-700 underline">
              descargar PNG
            </a>
            <span className="text-gray-300">·</span>
            <a href={qrSvgUrl} download className="text-teal-700 underline">
              descargar SVG
            </a>
          </div>
        </div>

        <div className="space-y-3">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Identificador
            </p>
            <code className="mt-1 block break-all rounded-xl bg-gray-100 p-2 text-xs shadow-sm">
              {dpp.gs1_uri}
            </code>
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              URL pública
            </p>
            <a
              href={fullPublicUrl}
              target="_blank"
              rel="noreferrer"
              className="mt-1 block break-all rounded-xl bg-gray-100 p-2 text-xs text-teal-700 underline shadow-sm"
            >
              {fullPublicUrl}
            </a>
            <p className="mt-1 text-xs text-gray-500">
              Devuelve JSON-LD por defecto; HTML cuando el cliente envía{" "}
              <code>Accept: text/html</code>.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
