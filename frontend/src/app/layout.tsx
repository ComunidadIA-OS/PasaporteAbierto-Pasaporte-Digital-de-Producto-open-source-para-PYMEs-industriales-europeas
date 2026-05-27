import type { Metadata } from "next";
import { Atkinson_Hyperlegible, JetBrains_Mono, Space_Grotesk } from "next/font/google";

import { AccessibilityWidget } from "@/core/ui/AccessibilityWidget";
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

// Atkinson Hyperlegible (Braille Institute): solo se aplica en el modo
// dislexia del widget de accesibilidad, vía la variable --font-dyslexia.
const atkinsonHyperlegible = Atkinson_Hyperlegible({
  variable: "--font-dyslexia",
  subsets: ["latin"],
  weight: ["400", "700"],
  display: "swap",
});

// Reaplica los modos de accesibilidad guardados antes de pintar, evitando el
// parpadeo (FOUC) en modos visuales como texto grande o alto contraste.
const A11Y_BOOT = `(function(){try{var m=JSON.parse(localStorage.getItem('pa-accesibilidad')||'{}');var map={daltonico:'a11y-daltonico',dislexia:'a11y-dislexia',contraste:'a11y-contraste','texto-grande':'a11y-texto-grande',enlaces:'a11y-enlaces','sin-animaciones':'a11y-sin-animaciones'};var c=document.documentElement.classList;for(var k in map){if(m[k])c.add(map[k]);}}catch(e){}})();`;

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
      className={`${spaceGrotesk.variable} ${jetbrainsMono.variable} ${atkinsonHyperlegible.variable}`}
      // El script de arranque añade clases de modo a <html> antes de hidratar
      // (igual que next-themes); evita el aviso de desajuste de hidratación.
      suppressHydrationWarning
    >
      <body>
        {/* biome-ignore lint/security/noDangerouslySetInnerHtml: script de arranque sin datos externos */}
        <script dangerouslySetInnerHTML={{ __html: A11Y_BOOT }} />
        <a href="#main-content" className="skip-link">
          Saltar al contenido principal
        </a>
        <div className="app-root">
          <div className="app-content">{children}</div>
        </div>
        <AccessibilityWidget />
      </body>
    </html>
  );
}
