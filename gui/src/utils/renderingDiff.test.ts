/**
 * Unit tests for rendering diff utilities.
 */

import { describe, it, expect } from "vitest";
import {
  alignTokens,
  classifyChange,
  computeDiff,
  getChangeTypeColor,
  getChangeTypeHighlight,
} from "./renderingDiff";
import type { TokenLedger, TokenConfidence } from "../api/types";

// Helper to create test tokens
function createToken(
  position: number,
  overrides: Partial<TokenLedger> = {},
): TokenLedger {
  const defaultConfidence: TokenConfidence = {
    textual: 0.9,
    grammatical: 0.85,
    lexical: 0.8,
    interpretive: 0.75,
    explanations: {},
  };

  return {
    position,
    surface: `word${position}`,
    normalized: `word${position}`,
    lemma: `lemma${position}`,
    morph: "V-PAI-3S",
    gloss: `gloss${position}`,
    gloss_source: "lexicon",
    notes: [],
    confidence: defaultConfidence,
    ...overrides,
  };
}

describe("alignTokens", () => {
  it("aligns tokens by position when positions match", () => {
    const base = [createToken(0), createToken(1), createToken(2)];
    const other = [createToken(0), createToken(1), createToken(2)];

    const aligned = alignTokens(base, other);

    expect(aligned).toHaveLength(3);
    expect(aligned[0].position).toBe(0);
    expect(aligned[0].baseToken).toBeTruthy();
    expect(aligned[0].otherToken).toBeTruthy();
  });

  it("marks missing tokens when other has fewer tokens", () => {
    const base = [createToken(0), createToken(1), createToken(2)];
    const other = [createToken(0), createToken(1)];

    const aligned = alignTokens(base, other);

    expect(aligned).toHaveLength(3);
    expect(aligned[2].baseToken).toBeTruthy();
    expect(aligned[2].otherToken).toBeNull();
    expect(aligned[2].changeType).toBe("lexical");
  });

  it("marks added tokens when other has more tokens", () => {
    const base = [createToken(0), createToken(1)];
    const other = [createToken(0), createToken(1), createToken(2)];

    const aligned = alignTokens(base, other);

    expect(aligned).toHaveLength(3);
    expect(aligned[2].baseToken).toBeNull();
    expect(aligned[2].otherToken).toBeTruthy();
    expect(aligned[2].changeType).toBe("lexical");
  });

  it("falls back to lemma matching when positions differ", () => {
    // Base token at position 5 (no matching position in other)
    // should fall back to lemma matching and find position 2
    const base = [createToken(5, { lemma: "unique_lemma" }), createToken(1)];
    const other = [
      createToken(0),
      createToken(2, { lemma: "unique_lemma" }), // Different position, same lemma
    ];

    const aligned = alignTokens(base, other);

    // Should find the lemma match
    const uniqueMatch = aligned.find(
      (a) => a.baseToken?.lemma === "unique_lemma",
    );
    expect(uniqueMatch).toBeTruthy();
    expect(uniqueMatch?.otherToken?.lemma).toBe("unique_lemma");
    expect(uniqueMatch?.changeType).toBe("syntactic"); // Position differs
  });
});

describe("classifyChange", () => {
  it('returns "none" when tokens are identical', () => {
    const base = createToken(0);
    const other = createToken(0);

    expect(classifyChange(base, other)).toBe("none");
  });

  it('returns "lexical" when gloss differs', () => {
    const base = createToken(0, { gloss: "word" });
    const other = createToken(0, { gloss: "term" });

    expect(classifyChange(base, other)).toBe("lexical");
  });

  it('returns "lexical" when gloss_source differs', () => {
    const base = createToken(0, { gloss_source: "bdag" });
    const other = createToken(0, { gloss_source: "louw-nida" });

    expect(classifyChange(base, other)).toBe("lexical");
  });

  it('returns "syntactic" when morph differs but gloss is same', () => {
    const base = createToken(0, { morph: "V-PAI-3S" });
    const other = createToken(0, { morph: "V-AAI-3S" });

    expect(classifyChange(base, other)).toBe("syntactic");
  });

  it('returns "interpretive" when notes contain interpretive markers', () => {
    const base = createToken(0, { notes: ["contextual interpretation"] });
    const other = createToken(0, { gloss: "different" });

    expect(classifyChange(base, other)).toBe("interpretive");
  });

  it('returns "interpretive" when confidence explanations contain markers', () => {
    const base = createToken(0, {
      confidence: {
        textual: 0.9,
        grammatical: 0.85,
        lexical: 0.8,
        interpretive: 0.75,
        explanations: { lexical: "theological context affects meaning" },
      },
    });
    const other = createToken(0, { gloss: "different" });

    expect(classifyChange(base, other)).toBe("interpretive");
  });
});

describe("computeDiff", () => {
  it("computes summary statistics correctly", () => {
    const base = [
      createToken(0),
      createToken(1, { gloss: "base_gloss" }),
      createToken(2, { morph: "V-PAI-3S" }),
    ];
    const other = [
      createToken(0),
      createToken(1, { gloss: "other_gloss" }),
      createToken(2, { morph: "V-AAI-3S" }),
    ];

    const diff = computeDiff(base, other);

    expect(diff.summary.unchanged).toBe(1);
    expect(diff.summary.lexicalChanges).toBe(1);
    expect(diff.summary.syntacticChanges).toBe(1);
  });

  it("handles empty arrays", () => {
    const diff = computeDiff([], []);

    expect(diff.alignedTokens).toHaveLength(0);
    expect(diff.summary.unchanged).toBe(0);
  });

  it("handles one empty array", () => {
    const base = [createToken(0), createToken(1)];
    const diff = computeDiff(base, []);

    expect(diff.summary.lexicalChanges).toBe(2); // Both base tokens are "missing" in other
  });
});

describe("getChangeTypeColor", () => {
  it("returns correct colors for each change type", () => {
    expect(getChangeTypeColor("lexical")).toBe("var(--rl-primary)");
    expect(getChangeTypeColor("syntactic")).toBe("#8b5cf6");
    expect(getChangeTypeColor("interpretive")).toBe("var(--rl-warning)");
    expect(getChangeTypeColor("none")).toBe("transparent");
  });
});

describe("getChangeTypeHighlight", () => {
  it("returns rgba colors with default intensity", () => {
    expect(getChangeTypeHighlight("lexical")).toBe("rgba(59, 130, 246, 0.2)");
    expect(getChangeTypeHighlight("none")).toBe("transparent");
  });

  it("respects custom intensity", () => {
    expect(getChangeTypeHighlight("lexical", 0.5)).toBe(
      "rgba(59, 130, 246, 0.5)",
    );
  });
});
