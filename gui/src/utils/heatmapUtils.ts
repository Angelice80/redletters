/**
 * Heatmap utilities for confidence visualization.
 *
 * Computes "risk" scores from confidence layers and
 * provides color mapping for visual highlighting.
 */

import type { TokenConfidence } from "../api/types";

/**
 * Compute token risk score from confidence layers.
 *
 * Risk = 1 - min(T, G, L, I)
 *
 * This highlights tokens where any single layer is weak,
 * which often indicates areas needing attention.
 */
export function computeTokenRisk(confidence: TokenConfidence): number {
  const minConfidence = Math.min(
    confidence.textual,
    confidence.grammatical,
    confidence.lexical,
    confidence.interpretive,
  );
  return 1 - minConfidence;
}

/**
 * Compute weighted risk using layer importance.
 *
 * Default weights prioritize textual and lexical confidence
 * as these most directly affect translation accuracy.
 */
export function computeWeightedRisk(
  confidence: TokenConfidence,
  weights: {
    textual: number;
    grammatical: number;
    lexical: number;
    interpretive: number;
  } = {
    textual: 0.35,
    grammatical: 0.15,
    lexical: 0.35,
    interpretive: 0.15,
  },
): number {
  const weighted =
    confidence.textual * weights.textual +
    confidence.grammatical * weights.grammatical +
    confidence.lexical * weights.lexical +
    confidence.interpretive * weights.interpretive;
  return 1 - weighted;
}

/**
 * Get the weakest confidence layer.
 */
export function getWeakestLayer(
  confidence: TokenConfidence,
): keyof TokenConfidence {
  const layers: [keyof TokenConfidence, number][] = [
    ["textual", confidence.textual],
    ["grammatical", confidence.grammatical],
    ["lexical", confidence.lexical],
    ["interpretive", confidence.interpretive],
  ];

  layers.sort((a, b) => a[1] - b[1]);
  return layers[0][0];
}

/**
 * Risk level thresholds for visual classification.
 */
export type RiskLevel = "low" | "medium" | "high" | "critical";

export function getRiskLevel(risk: number): RiskLevel {
  if (risk < 0.2) return "low";
  if (risk < 0.4) return "medium";
  if (risk < 0.6) return "high";
  return "critical";
}

/**
 * Convert risk to underline color (subtle highlighting).
 *
 * Uses a gradient from green (low risk) through yellow
 * to red (high risk).
 */
export function riskToUnderlineColor(risk: number): string {
  // Clamp risk to [0, 1]
  const r = Math.max(0, Math.min(1, risk));

  if (r < 0.2) {
    // Very low risk - transparent
    return "transparent";
  } else if (r < 0.4) {
    // Low-medium risk - subtle yellow
    return `rgba(250, 204, 21, ${0.3 + r * 0.5})`; // Yellow-400
  } else if (r < 0.6) {
    // Medium-high risk - orange
    return `rgba(251, 146, 60, ${0.4 + r * 0.4})`; // Orange-400
  } else {
    // High risk - red
    return `rgba(248, 113, 113, ${0.5 + r * 0.5})`; // Red-400
  }
}

/**
 * Convert risk to background tint (very subtle highlighting).
 *
 * Intensity parameter controls how strong the highlight is.
 */
export function riskToBackgroundTint(
  risk: number,
  maxIntensity: number = 0.15,
): string {
  // Clamp risk to [0, 1]
  const r = Math.max(0, Math.min(1, risk));

  if (r < 0.2) {
    return "transparent";
  }

  // Scale intensity by risk
  const intensity = (r - 0.2) * (maxIntensity / 0.8);

  if (r < 0.5) {
    // Low-medium: warm yellow
    return `rgba(250, 204, 21, ${intensity})`;
  } else {
    // High: warm red
    return `rgba(248, 113, 113, ${intensity})`;
  }
}

/**
 * Get CSS styles for heatmap highlighting.
 */
export function getHeatmapStyles(
  confidence: TokenConfidence,
  mode: "underline" | "background" | "both" = "underline",
): React.CSSProperties {
  const risk = computeTokenRisk(confidence);

  const styles: React.CSSProperties = {};

  if (mode === "underline" || mode === "both") {
    const underlineColor = riskToUnderlineColor(risk);
    if (underlineColor !== "transparent") {
      styles.textDecoration = "underline";
      styles.textDecorationColor = underlineColor;
      styles.textDecorationThickness = risk > 0.6 ? "3px" : "2px";
      styles.textUnderlineOffset = "3px";
    }
  }

  if (mode === "background" || mode === "both") {
    const bgColor = riskToBackgroundTint(risk);
    if (bgColor !== "transparent") {
      styles.backgroundColor = bgColor;
      styles.borderRadius = "2px";
      styles.padding = "0 2px";
    }
  }

  return styles;
}

/**
 * Legend data for heatmap display.
 */
export const HEATMAP_LEGEND = [
  { label: "High confidence", risk: 0.1, description: "No highlighting" },
  { label: "Medium", risk: 0.35, description: "Subtle yellow" },
  { label: "Low confidence", risk: 0.55, description: "Orange highlight" },
  { label: "Very low", risk: 0.75, description: "Red highlight" },
];

/**
 * Get tooltip text explaining confidence for a token.
 */
export function getConfidenceTooltip(confidence: TokenConfidence): string {
  const risk = computeTokenRisk(confidence);
  const weakest = getWeakestLayer(confidence);
  const level = getRiskLevel(risk);

  const layerNames: Record<keyof TokenConfidence, string> = {
    textual: "Textual",
    grammatical: "Grammatical",
    lexical: "Lexical",
    interpretive: "Interpretive",
    explanations: "", // Not a confidence layer
  };

  const lines = [
    `Risk: ${(risk * 100).toFixed(0)}% (${level})`,
    `Weakest: ${layerNames[weakest]} (${(confidence[weakest as "textual"] * 100).toFixed(0)}%)`,
    "",
    `T: ${(confidence.textual * 100).toFixed(0)}%  G: ${(confidence.grammatical * 100).toFixed(0)}%`,
    `L: ${(confidence.lexical * 100).toFixed(0)}%  I: ${(confidence.interpretive * 100).toFixed(0)}%`,
  ];

  return lines.join("\n");
}
