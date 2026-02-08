/**
 * ConfidenceDetailPanel — drill-down view for a specific confidence layer.
 *
 * Sprint 24 (S6): Click a confidence layer to see weak tokens + reasons.
 * Lists tokens sorted by that layer's score (weakest first).
 * Honestly says "not provided" when explanations are missing.
 */

import type { TokenLedger, VerseLedger } from "../api/types";
import { Tooltip } from "./Tooltip";

interface ConfidenceDetailPanelProps {
  /** Which layer is being inspected */
  layer: "textual" | "grammatical" | "lexical" | "interpretive";
  /** Verse ledger data */
  ledger: VerseLedger[];
  /** Called when a token in the list is clicked */
  onTokenSelect: (position: number) => void;
  /** Called to close the panel */
  onClose: () => void;
}

const panelStyle: React.CSSProperties = {
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "6px",
  padding: "12px",
  marginTop: "8px",
  border: "1px solid var(--rl-border-strong)",
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "10px",
};

const titleStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-sm)",
  fontWeight: 600,
  color: "var(--rl-text-muted)",
  textTransform: "capitalize" as const,
};

const closeStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  color: "var(--rl-text-dim)",
  cursor: "pointer",
  fontSize: "var(--rl-fs-base)",
  padding: "2px 6px",
};

const tokenRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
  padding: "6px 8px",
  borderRadius: "4px",
  cursor: "pointer",
  transition: "background-color 0.1s",
  marginBottom: "2px",
};

const scoreStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xs)",
  fontFamily: "var(--rl-font-mono)",
  width: "36px",
  textAlign: "right" as const,
};

const surfaceStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-base)",
  fontFamily: "'SBL Greek', 'Cardo', 'Gentium Plus', serif",
  color: "#60a5fa",
};

const glossStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-sm)",
  color: "var(--rl-text-muted)",
};

const reasonStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xs)",
  color: "var(--rl-text-dim)",
  fontStyle: "italic",
  marginLeft: "auto",
  maxWidth: "200px",
  textAlign: "right" as const,
};

const noReasonsStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-sm)",
  color: "var(--rl-text-dim)",
  fontStyle: "italic",
  padding: "12px 8px",
  textAlign: "center" as const,
};

function getScoreColor(score: number): string {
  if (score >= 0.8) return "var(--rl-success)";
  if (score >= 0.6) return "var(--rl-warning)";
  return "var(--rl-error)";
}

const LAYER_LABELS: Record<string, string> = {
  textual: "Textual",
  grammatical: "Grammatical",
  lexical: "Lexical",
  interpretive: "Interpretive",
};

export function ConfidenceDetailPanel({
  layer,
  ledger,
  onTokenSelect,
  onClose,
}: ConfidenceDetailPanelProps) {
  // Flatten all tokens from all verses
  const allTokens: TokenLedger[] = ledger.flatMap((v) => v.tokens);

  // Sort by the selected layer's score (weakest first)
  const sorted = [...allTokens].sort(
    (a, b) => a.confidence[layer] - b.confidence[layer],
  );

  // Check if any token has explanations for this layer
  const hasAnyExplanation = allTokens.some(
    (t) =>
      t.confidence.explanations &&
      typeof t.confidence.explanations[layer] === "string" &&
      t.confidence.explanations[layer].length > 0,
  );

  // Show top weak tokens (score < 0.8) or all if none are weak
  const weakTokens = sorted.filter((t) => t.confidence[layer] < 0.8);
  const displayTokens = weakTokens.length > 0 ? weakTokens : sorted.slice(0, 5);

  return (
    <div style={panelStyle} data-testid="confidence-detail-panel">
      <div style={headerStyle}>
        <Tooltip
          content={`Tokens sorted by ${LAYER_LABELS[layer]} confidence (weakest first). Click a token to highlight it.`}
          position="bottom"
        >
          <span style={titleStyle}>
            {LAYER_LABELS[layer]} Layer — {weakTokens.length} weak token
            {weakTokens.length !== 1 ? "s" : ""}
          </span>
        </Tooltip>
        <button
          style={closeStyle}
          onClick={onClose}
          aria-label="Close detail panel"
        >
          x
        </button>
      </div>

      {displayTokens.length === 0 ? (
        <div style={noReasonsStyle}>No tokens available for this layer.</div>
      ) : (
        <>
          {displayTokens.map((token) => {
            const score = token.confidence[layer];
            const explanation = token.confidence.explanations?.[layer] || null;

            return (
              <div
                key={token.position}
                data-testid={`confidence-token-${token.position}`}
                style={tokenRowStyle}
                onClick={() => onTokenSelect(token.position)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor =
                    "rgba(96, 165, 250, 0.1)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = "transparent";
                }}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onTokenSelect(token.position);
                  }
                }}
              >
                <span style={{ ...scoreStyle, color: getScoreColor(score) }}>
                  {(score * 100).toFixed(0)}%
                </span>
                <span style={surfaceStyle}>{token.surface}</span>
                <span style={glossStyle}>{token.gloss}</span>
                {explanation && <span style={reasonStyle}>{explanation}</span>}
              </div>
            );
          })}

          {!hasAnyExplanation && (
            <div style={noReasonsStyle} data-testid="no-reasons-msg">
              Token-level reasons not provided by backend.
            </div>
          )}
        </>
      )}
    </div>
  );
}
