/**
 * Rendering diff utilities for comparing translations.
 *
 * Provides token alignment and change classification for
 * visual comparison between renderings.
 */

import type { TokenLedger } from "../api/types";

// Change types for visual classification
export type ChangeType = "none" | "lexical" | "syntactic" | "interpretive";

export interface AlignedToken {
  position: number;
  baseToken: TokenLedger | null;
  otherToken: TokenLedger | null;
  changeType: ChangeType;
  reason?: string;
}

export interface DiffResult {
  alignedTokens: AlignedToken[];
  summary: {
    lexicalChanges: number;
    syntacticChanges: number;
    interpretiveChanges: number;
    unchanged: number;
  };
}

/**
 * Align tokens from two renderings by position or lemma.
 *
 * Uses position-first matching (simpler and more robust for
 * same-verse comparisons). Falls back to lemma matching for
 * edge cases.
 */
export function alignTokens(
  baseTokens: TokenLedger[],
  otherTokens: TokenLedger[],
): AlignedToken[] {
  const aligned: AlignedToken[] = [];

  // Create lookup by position for other tokens
  const otherByPosition = new Map<number, TokenLedger>();
  const otherByLemma = new Map<string, TokenLedger[]>();

  for (const token of otherTokens) {
    otherByPosition.set(token.position, token);
    if (token.lemma) {
      const existing = otherByLemma.get(token.lemma) || [];
      existing.push(token);
      otherByLemma.set(token.lemma, existing);
    }
  }

  // Track which other tokens have been matched
  const matchedOtherPositions = new Set<number>();

  // First pass: position-based alignment
  for (const baseToken of baseTokens) {
    const otherToken = otherByPosition.get(baseToken.position);

    if (otherToken) {
      matchedOtherPositions.add(otherToken.position);
      aligned.push({
        position: baseToken.position,
        baseToken,
        otherToken,
        changeType: classifyChange(baseToken, otherToken),
        reason: getChangeReason(baseToken, otherToken),
      });
    } else {
      // No position match - try lemma match
      const lemmaMatches = baseToken.lemma
        ? otherByLemma.get(baseToken.lemma)
        : undefined;
      const unmatchedLemma = lemmaMatches?.find(
        (t) => !matchedOtherPositions.has(t.position),
      );

      if (unmatchedLemma) {
        matchedOtherPositions.add(unmatchedLemma.position);
        aligned.push({
          position: baseToken.position,
          baseToken,
          otherToken: unmatchedLemma,
          changeType: "syntactic", // Position differs = syntactic change
          reason: "Token reordered",
        });
      } else {
        // No match at all - base-only token
        aligned.push({
          position: baseToken.position,
          baseToken,
          otherToken: null,
          changeType: "lexical",
          reason: "Token not in other rendering",
        });
      }
    }
  }

  // Add any other tokens that weren't matched (additions)
  for (const otherToken of otherTokens) {
    if (!matchedOtherPositions.has(otherToken.position)) {
      aligned.push({
        position: otherToken.position,
        baseToken: null,
        otherToken,
        changeType: "lexical",
        reason: "Token added in other rendering",
      });
    }
  }

  // Sort by position
  aligned.sort((a, b) => a.position - b.position);

  return aligned;
}

/**
 * Classify the type of change between two aligned tokens.
 *
 * Classification rules:
 * - Lexical: Different gloss or sense_source
 * - Syntactic: Same lemma but different morph or position
 * - Interpretive: Rationale contains interpretive markers
 */
export function classifyChange(
  baseToken: TokenLedger,
  otherToken: TokenLedger,
): ChangeType {
  // Check if tokens are identical
  if (
    baseToken.gloss === otherToken.gloss &&
    baseToken.gloss_source === otherToken.gloss_source &&
    baseToken.morph === otherToken.morph
  ) {
    return "none";
  }

  // Check for interpretive markers in notes or explanations
  const interpretiveMarkers = [
    "contextual",
    "theological",
    "discourse",
    "rhetorical",
    "pragmatic",
    "implied",
  ];

  const baseNotes = baseToken.notes.join(" ").toLowerCase();
  const otherNotes = otherToken.notes.join(" ").toLowerCase();
  const baseExplanations = Object.values(
    baseToken.confidence.explanations,
  ).join(" ");
  const otherExplanations = Object.values(
    otherToken.confidence.explanations,
  ).join(" ");

  const hasInterpretiveMarker =
    interpretiveMarkers.some(
      (marker) => baseNotes.includes(marker) || otherNotes.includes(marker),
    ) ||
    interpretiveMarkers.some(
      (marker) =>
        baseExplanations.toLowerCase().includes(marker) ||
        otherExplanations.toLowerCase().includes(marker),
    );

  if (hasInterpretiveMarker) {
    return "interpretive";
  }

  // Check for lexical changes (different gloss)
  if (
    baseToken.gloss !== otherToken.gloss ||
    baseToken.gloss_source !== otherToken.gloss_source
  ) {
    return "lexical";
  }

  // Check for syntactic changes (same content, different structure)
  if (baseToken.morph !== otherToken.morph) {
    return "syntactic";
  }

  // Default to lexical for any other differences
  return "lexical";
}

/**
 * Get human-readable reason for a change.
 */
function getChangeReason(
  baseToken: TokenLedger,
  otherToken: TokenLedger,
): string | undefined {
  if (baseToken.gloss !== otherToken.gloss) {
    return `Gloss: "${baseToken.gloss}" → "${otherToken.gloss}"`;
  }
  if (baseToken.gloss_source !== otherToken.gloss_source) {
    return `Source: ${baseToken.gloss_source} → ${otherToken.gloss_source}`;
  }
  if (baseToken.morph !== otherToken.morph) {
    return `Morphology: ${baseToken.morph} → ${otherToken.morph}`;
  }
  return undefined;
}

/**
 * Compute full diff between two renderings.
 */
export function computeDiff(
  baseTokens: TokenLedger[],
  otherTokens: TokenLedger[],
): DiffResult {
  const alignedTokens = alignTokens(baseTokens, otherTokens);

  const summary = {
    lexicalChanges: 0,
    syntacticChanges: 0,
    interpretiveChanges: 0,
    unchanged: 0,
  };

  for (const aligned of alignedTokens) {
    switch (aligned.changeType) {
      case "lexical":
        summary.lexicalChanges++;
        break;
      case "syntactic":
        summary.syntacticChanges++;
        break;
      case "interpretive":
        summary.interpretiveChanges++;
        break;
      case "none":
        summary.unchanged++;
        break;
    }
  }

  return { alignedTokens, summary };
}

/**
 * Get CSS color for a change type.
 */
export function getChangeTypeColor(changeType: ChangeType): string {
  switch (changeType) {
    case "lexical":
      return "#3b82f6"; // Blue
    case "syntactic":
      return "#8b5cf6"; // Purple
    case "interpretive":
      return "#f59e0b"; // Orange
    case "none":
    default:
      return "transparent";
  }
}

/**
 * Get background color with opacity for highlighting.
 */
export function getChangeTypeHighlight(
  changeType: ChangeType,
  intensity: number = 0.2,
): string {
  switch (changeType) {
    case "lexical":
      return `rgba(59, 130, 246, ${intensity})`; // Blue
    case "syntactic":
      return `rgba(139, 92, 246, ${intensity})`; // Purple
    case "interpretive":
      return `rgba(245, 158, 11, ${intensity})`; // Orange
    case "none":
    default:
      return "transparent";
  }
}
