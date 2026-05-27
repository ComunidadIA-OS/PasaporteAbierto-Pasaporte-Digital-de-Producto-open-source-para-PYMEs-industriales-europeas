// Puerta de UX para rutas que exigen sesión iniciada (ADR-0004).
//
// Next 16 renombró el "middleware" a "proxy"; misma semántica (corre en el
// servidor antes de servir la ruta). Solo comprueba la PRESENCIA de la cookie
// de sesión, no su validez: la autorización real la hace el backend en cada
// endpoint. Una cookie caducada pasa el proxy pero el Server Component recibe
// 401 y redirige a /login. La cookie es httpOnly, pero el proxy corre en el
// servidor y sí puede leerla de la request.

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

const COOKIE_NAME = process.env.NEXT_PUBLIC_AUTH_COOKIE_NAME ?? "pa_session";

export function proxy(request: NextRequest): NextResponse {
  if (request.cookies.has(COOKIE_NAME)) {
    return NextResponse.next();
  }
  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", request.nextUrl.pathname);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  // Protege el wizard y el panel; el resto (landing, login, DPP público) es libre.
  matcher: ["/wizard", "/wizard/:path*", "/panel", "/panel/:path*"],
};
