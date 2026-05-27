// Icono Material Symbols (Outlined) self-hosted.
//
// La fuente se carga una sola vez en app/layout.tsx
// (`import "material-symbols/outlined.css"`). Aquí solo envolvemos el
// `<span>` con ligadura para exponer una API tipada y accesible.
//
// Uso:
//   <Icon name="verified" />                 decorativo (aria-hidden)
//   <Icon name="close" label="Cerrar" />     semántico (role=img + aria-label)

import type { CSSProperties } from "react";

type IconProps = {
  /** Nombre de la ligadura Material Symbols, p. ej. "verified", "gavel". */
  name: string;
  /** Tamaño en px (también ajusta el eje óptico `opsz`). */
  size?: number;
  /** Variante rellena (eje `FILL`). */
  fill?: boolean;
  /** Grosor del trazo (eje `wght`). */
  weight?: 300 | 400 | 500 | 600 | 700;
  /** Etiqueta accesible. Si se omite, el icono es decorativo. */
  label?: string;
  className?: string;
  style?: CSSProperties;
};

export function Icon({
  name,
  size = 20,
  fill = false,
  weight = 400,
  label,
  className,
  style,
}: IconProps) {
  // `aria-label` solo es válido junto a un role explícito (aquí "img"); si el
  // icono es decorativo lo ocultamos del árbol de accesibilidad con aria-hidden.
  const a11y = label
    ? ({ role: "img", "aria-label": label } as const)
    : ({ "aria-hidden": true } as const);
  return (
    <span
      className={`material-symbols-outlined${className ? ` ${className}` : ""}`}
      style={{
        fontSize: size,
        fontVariationSettings: `'FILL' ${fill ? 1 : 0}, 'wght' ${weight}, 'GRAD' 0, 'opsz' ${size}`,
        ...style,
      }}
      {...a11y}
    >
      {name}
    </span>
  );
}
