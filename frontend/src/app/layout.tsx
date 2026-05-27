import type { Metadata } from "next";
import { JetBrains_Mono, Space_Grotesk } from "next/font/google";

import "./globals.css";

// Tema Compliance OS: Space Grotesk (head + body) y JetBrains Mono (mono).
// Pesos según specs del bundle de diseño.
const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
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
    <html lang="es" className={`${spaceGrotesk.variable} ${jetbrainsMono.variable}`}>
      <body>
        <div className="app-root">
          <div className="app-content">{children}</div>
        </div>
      </body>
    </html>
  );
}
