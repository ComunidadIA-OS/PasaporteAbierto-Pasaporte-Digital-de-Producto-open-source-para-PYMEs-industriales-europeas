import type { Metadata } from "next";
import { DM_Mono, IBM_Plex_Sans, Newsreader } from "next/font/google";

import "./globals.css";

// Tema Quiet (D): Newsreader (serif italic) para títulos, IBM Plex Sans para body,
// DM Mono para mono. Los pesos vienen de los specs del bundle de diseño.
const newsreader = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  style: ["normal", "italic"],
  display: "swap",
});

const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  display: "swap",
});

const dmMono = DM_Mono({
  variable: "--font-dm-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
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
    <html
      lang="es"
      className={`${newsreader.variable} ${plexSans.variable} ${dmMono.variable}`}
    >
      <body>
        <div className="app-root">
          <div className="app-content">{children}</div>
        </div>
      </body>
    </html>
  );
}
