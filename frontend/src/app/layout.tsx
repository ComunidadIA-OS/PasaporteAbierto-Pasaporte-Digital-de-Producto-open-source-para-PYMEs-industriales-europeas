import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";

// Iconografía: Material Symbols (self-hosted vía paquete npm, sin CDN).
import "material-symbols/outlined.css";
import "./globals.css";

// Tipografía institucional: IBM Plex Sans (titulares + cuerpo) e IBM Plex Mono
// (identificadores, citas y código). Familia de ingeniería diseñada por IBM:
// transmite seriedad técnica y encaja con un producto de cumplimiento UE.
const ibmPlexSans = IBM_Plex_Sans({
  variable: "--font-ibm-plex-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-ibm-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "PasaporteAbierto",
  description:
    "Pasaporte Digital de Producto (DPP) auto-hospedable para fabricantes PYME, conforme al Reglamento UE 2024/1781 (ESPR).",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className={`${ibmPlexSans.variable} ${ibmPlexMono.variable}`}>
      <body>
        <div className="app-root">
          <div className="app-content">{children}</div>
        </div>
      </body>
    </html>
  );
}
