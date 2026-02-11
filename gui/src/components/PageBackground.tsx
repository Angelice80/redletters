/**
 * PageBackground — decorative, per-route background image layer.
 *
 * Renders with position: absolute to fill its nearest positioned ancestor
 * (the main content shell in App.tsx). No fixed positioning, no magic
 * offsets, no sidebar coupling.
 *
 * Stacking: z-index: 0 behind content (z-index: 1).
 *
 * Opacity policy:
 *   - Production max: 0.3 (hard clamp). Default: 0.15.
 *   - Values > 0.3 are only allowed in DEV mode for debugging.
 *   - This prevents accidental high-opacity shipping.
 */

import { useEffect, useState } from "react";

/** Production ceiling — backgrounds must stay subtle. */
const MAX_OPACITY = 0.3;
const DEFAULT_OPACITY = 0.15;

interface PageBackgroundProps {
  /** Path to image in public/ directory, e.g. "/backgrounds/explore.webp" */
  image: string;
  /** Override opacity for debugging. Clamped to MAX_OPACITY in production. */
  opacity?: number;
}

export function PageBackground({
  image,
  opacity = DEFAULT_OPACITY,
}: PageBackgroundProps) {
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setLoaded(false);
    const img = new Image();
    img.onload = () => setLoaded(true);
    img.src = image;
    return () => {
      img.onload = null;
    };
  }, [image]);

  // Clamp opacity: allow > MAX_OPACITY only in DEV for visual debugging.
  const resolvedOpacity = import.meta.env.DEV
    ? opacity
    : Math.min(opacity, MAX_OPACITY);

  return (
    <div
      className="pageBackground"
      aria-hidden="true"
      style={{
        position: "absolute",
        inset: 0,
        zIndex: 0,
        overflow: "hidden",
        pointerEvents: "none",
      }}
    >
      {/* Background image */}
      <div
        className="pageBackground__image"
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `url(${image})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
          backgroundRepeat: "no-repeat",
          opacity: loaded ? resolvedOpacity : 0,
          filter: "grayscale(0.3)",
          transition: "opacity 800ms ease",
        }}
      />
      {/* Soft vignette for readability */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: [
            "linear-gradient(to bottom,",
            "  rgba(11, 16, 32, 0.5) 0%,",
            "  transparent 20%,",
            "  transparent 80%,",
            "  rgba(11, 16, 32, 0.5) 100%)",
          ].join(" "),
        }}
      />
    </div>
  );
}
