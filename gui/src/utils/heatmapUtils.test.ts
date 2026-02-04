/**
 * Unit tests for heatmap utilities.
 */

import { describe, it, expect } from "vitest";
import {
  computeTokenRisk,
  computeWeightedRisk,
  getWeakestLayer,
  getRiskLevel,
  riskToUnderlineColor,
  riskToBackgroundTint,
  getHeatmapStyles,
  getConfidenceTooltip,
} from "./heatmapUtils";
import type { TokenConfidence } from "../api/types";

// Helper to create test confidence
function createConfidence(
  overrides: Partial<Omit<TokenConfidence, "explanations">> = {},
): TokenConfidence {
  return {
    textual: 0.9,
    grammatical: 0.85,
    lexical: 0.8,
    interpretive: 0.75,
    explanations: {},
    ...overrides,
  };
}

describe("computeTokenRisk", () => {
  it("returns 0 when all layers are 1.0", () => {
    const confidence = createConfidence({
      textual: 1.0,
      grammatical: 1.0,
      lexical: 1.0,
      interpretive: 1.0,
    });

    expect(computeTokenRisk(confidence)).toBe(0);
  });

  it("returns 1 when any layer is 0", () => {
    const confidence = createConfidence({
      textual: 0.9,
      grammatical: 0.85,
      lexical: 0, // Zero confidence
      interpretive: 0.75,
    });

    expect(computeTokenRisk(confidence)).toBe(1);
  });

  it("returns risk based on minimum layer", () => {
    const confidence = createConfidence({
      textual: 0.9,
      grammatical: 0.7,
      lexical: 0.6, // Minimum
      interpretive: 0.8,
    });

    // Risk = 1 - min = 1 - 0.6 = 0.4
    expect(computeTokenRisk(confidence)).toBe(0.4);
  });
});

describe("computeWeightedRisk", () => {
  it("applies default weights correctly", () => {
    const confidence = createConfidence({
      textual: 0.8,
      grammatical: 0.7,
      lexical: 0.6,
      interpretive: 0.5,
    });

    // Default weights: T=0.35, G=0.15, L=0.35, I=0.15
    // Weighted = 0.8*0.35 + 0.7*0.15 + 0.6*0.35 + 0.5*0.15
    //          = 0.28 + 0.105 + 0.21 + 0.075 = 0.67
    // Risk = 1 - 0.67 = 0.33
    expect(computeWeightedRisk(confidence)).toBeCloseTo(0.33, 2);
  });

  it("accepts custom weights", () => {
    const confidence = createConfidence({
      textual: 1.0,
      grammatical: 0.0,
      lexical: 0.0,
      interpretive: 0.0,
    });

    // Only textual matters with 100% weight
    const risk = computeWeightedRisk(confidence, {
      textual: 1.0,
      grammatical: 0.0,
      lexical: 0.0,
      interpretive: 0.0,
    });

    expect(risk).toBe(0); // Full confidence in the only weighted layer
  });
});

describe("getWeakestLayer", () => {
  it("identifies the lowest confidence layer", () => {
    expect(
      getWeakestLayer(
        createConfidence({
          textual: 0.9,
          grammatical: 0.85,
          lexical: 0.5, // Lowest
          interpretive: 0.75,
        }),
      ),
    ).toBe("lexical");

    expect(
      getWeakestLayer(
        createConfidence({
          textual: 0.3, // Lowest
          grammatical: 0.85,
          lexical: 0.8,
          interpretive: 0.75,
        }),
      ),
    ).toBe("textual");
  });
});

describe("getRiskLevel", () => {
  it("classifies risk levels correctly", () => {
    expect(getRiskLevel(0.1)).toBe("low");
    expect(getRiskLevel(0.19)).toBe("low");
    expect(getRiskLevel(0.2)).toBe("medium");
    expect(getRiskLevel(0.39)).toBe("medium");
    expect(getRiskLevel(0.4)).toBe("high");
    expect(getRiskLevel(0.59)).toBe("high");
    expect(getRiskLevel(0.6)).toBe("critical");
    expect(getRiskLevel(1.0)).toBe("critical");
  });
});

describe("riskToUnderlineColor", () => {
  it("returns transparent for very low risk", () => {
    expect(riskToUnderlineColor(0.1)).toBe("transparent");
    expect(riskToUnderlineColor(0.19)).toBe("transparent");
  });

  it("returns yellow-ish for low-medium risk", () => {
    const color = riskToUnderlineColor(0.3);
    expect(color).toContain("rgba(250, 204, 21"); // Yellow-400
  });

  it("returns orange for medium-high risk", () => {
    const color = riskToUnderlineColor(0.5);
    expect(color).toContain("rgba(251, 146, 60"); // Orange-400
  });

  it("returns red for high risk", () => {
    const color = riskToUnderlineColor(0.8);
    expect(color).toContain("rgba(248, 113, 113"); // Red-400
  });
});

describe("riskToBackgroundTint", () => {
  it("returns transparent for very low risk", () => {
    expect(riskToBackgroundTint(0.1)).toBe("transparent");
  });

  it("respects maxIntensity parameter", () => {
    // Use 0.4 to stay clearly in the yellow range (r < 0.5)
    const low = riskToBackgroundTint(0.4, 0.1);
    const high = riskToBackgroundTint(0.4, 0.5);

    // Higher maxIntensity should result in higher alpha
    // Both should be the same color family but different intensity
    expect(low).toContain("rgba(250, 204, 21");
    expect(high).toContain("rgba(250, 204, 21");
  });
});

describe("getHeatmapStyles", () => {
  it("returns empty object for high confidence", () => {
    const confidence = createConfidence({
      textual: 0.95,
      grammatical: 0.95,
      lexical: 0.95,
      interpretive: 0.95,
    });

    const styles = getHeatmapStyles(confidence);
    expect(Object.keys(styles)).toHaveLength(0);
  });

  it('includes underline styles in "underline" mode', () => {
    const confidence = createConfidence({
      textual: 0.5,
      grammatical: 0.5,
      lexical: 0.5,
      interpretive: 0.5,
    });

    const styles = getHeatmapStyles(confidence, "underline");
    expect(styles.textDecoration).toBe("underline");
    expect(styles.textDecorationColor).toBeTruthy();
  });

  it('includes background styles in "background" mode', () => {
    const confidence = createConfidence({
      textual: 0.5,
      grammatical: 0.5,
      lexical: 0.5,
      interpretive: 0.5,
    });

    const styles = getHeatmapStyles(confidence, "background");
    expect(styles.backgroundColor).toBeTruthy();
    expect(styles.textDecoration).toBeUndefined();
  });

  it('includes both styles in "both" mode', () => {
    const confidence = createConfidence({
      textual: 0.4,
      grammatical: 0.4,
      lexical: 0.4,
      interpretive: 0.4,
    });

    const styles = getHeatmapStyles(confidence, "both");
    expect(styles.textDecoration).toBe("underline");
    expect(styles.backgroundColor).toBeTruthy();
  });
});

describe("getConfidenceTooltip", () => {
  it("includes risk and weakest layer", () => {
    const confidence = createConfidence({
      textual: 0.9,
      grammatical: 0.85,
      lexical: 0.5, // Weakest
      interpretive: 0.75,
    });

    const tooltip = getConfidenceTooltip(confidence);

    expect(tooltip).toContain("Risk:");
    expect(tooltip).toContain("Weakest: Lexical");
    expect(tooltip).toContain("50%");
  });

  it("includes all layer values", () => {
    const confidence = createConfidence({
      textual: 0.9,
      grammatical: 0.85,
      lexical: 0.8,
      interpretive: 0.75,
    });

    const tooltip = getConfidenceTooltip(confidence);

    expect(tooltip).toContain("T: 90%");
    expect(tooltip).toContain("G: 85%");
    expect(tooltip).toContain("L: 80%");
    expect(tooltip).toContain("I: 75%");
  });
});
