/**
 * GreekTokenDisplay — renders Greek tokens individually with selection/alignment.
 *
 * Sprint 24 (S5): Click a Greek token to highlight aligned rendering token(s).
 * Shows surface forms from VerseLedger.tokens[].surface.
 * Falls back to raw sblgnt_text when no ledger is available.
 */

import type { TokenLedger, VerseLedger } from "../api/types";
import { Tooltip } from "./Tooltip";

interface GreekTokenDisplayProps {
  /** Raw SBLGNT text (fallback when no ledger) */
  sblgntText: string;
  /** Verse ledger data (null when no token-level data) */
  ledger: VerseLedger[] | null;
  /** Currently selected token position (null = none) */
  selectedPosition: number | null;
  /** Set of positions highlighted via segment grouping */
  highlightedPositions: Set<number>;
  /** Called when a Greek token is clicked */
  onTokenClick: (
    token: TokenLedger,
    verseIdx: number,
    element: HTMLElement,
  ) => void;
  /** Sprint 26 (UX5): Current request mode for context-aware messages */
  requestMode?: "readable" | "traceable";
  /** Sprint 26 (UX5): Current translator type for context-aware messages */
  translatorType?: string;
}

const greekTextStyle: React.CSSProperties = {
  fontSize: "18px",
  fontFamily: "'SBL Greek', 'Cardo', 'Gentium Plus', serif",
  color: "#60a5fa",
  lineHeight: 1.8,
};

const greekTokenStyle: React.CSSProperties = {
  cursor: "pointer",
  padding: "2px 4px",
  borderRadius: "3px",
  transition: "background-color 0.15s, outline 0.15s",
  display: "inline",
};

const selectedStyle: React.CSSProperties = {
  backgroundColor: "rgba(96, 165, 250, 0.25)",
  outline: "1px solid rgba(96, 165, 250, 0.5)",
};

const highlightedStyle: React.CSSProperties = {
  backgroundColor: "rgba(96, 165, 250, 0.12)",
};

const noDataStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#6b7280",
  fontStyle: "italic",
  marginTop: "12px",
  padding: "8px",
  backgroundColor: "#1a1a2e",
  borderRadius: "4px",
};

export function GreekTokenDisplay({
  sblgntText,
  ledger,
  selectedPosition,
  highlightedPositions,
  onTokenClick,
  requestMode,
  translatorType,
}: GreekTokenDisplayProps) {
  // No ledger: show raw text with context-aware explanation (Sprint 26, UX5)
  if (!ledger || ledger.length === 0) {
    const isTraceable = requestMode === "traceable";
    const noDataMsg = isTraceable
      ? `The ${translatorType || "selected"} translator did not return token alignment for this passage. Try the "traceable" translator for per-token mapping.`
      : "Token alignment requires Traceable request mode. Switch Request Mode to Traceable and re-translate.";

    return (
      <div>
        <div style={greekTextStyle}>{sblgntText}</div>
        <div style={noDataStyle} data-testid="alignment-disabled-msg">
          {noDataMsg}
        </div>
      </div>
    );
  }

  return (
    <div>
      {ledger.map((verse, verseIdx) => (
        <div key={verse.verse_id} style={{ marginBottom: "12px" }}>
          {verse.tokens.map((token) => {
            const isSelected = selectedPosition === token.position;
            const isHighlighted =
              !isSelected && highlightedPositions.has(token.position);

            const tokenTip = token.lemma
              ? `Select to see lemma/morph and highlight aligned English. (${token.lemma})`
              : "Select to see details and highlight aligned English.";

            return (
              <span key={token.position}>
                <Tooltip content={tokenTip} position="bottom">
                  <span
                    data-testid={`greek-token-${token.position}`}
                    role="button"
                    tabIndex={0}
                    style={{
                      ...greekTextStyle,
                      ...greekTokenStyle,
                      ...(isSelected ? selectedStyle : {}),
                      ...(isHighlighted ? highlightedStyle : {}),
                    }}
                    onClick={(e) =>
                      onTokenClick(token, verseIdx, e.currentTarget)
                    }
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onTokenClick(token, verseIdx, e.currentTarget);
                      }
                    }}
                    aria-selected={isSelected || undefined}
                  >
                    {token.surface}
                  </span>
                </Tooltip>{" "}
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
}
