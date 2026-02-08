/**
 * Token Inspector Dock — persistent panel for selected token details.
 *
 * Replaces the transient popover as the primary "details" surface.
 * Shows Greek surface, lemma, English gloss, and confidence breakdown.
 *
 * UX3.1: Pin details, don't chase popovers.
 */

import type { TokenLedger } from "../api/types";

interface TokenInspectorDockProps {
  token: TokenLedger | null;
  onClear: () => void;
}

const dockStyle: React.CSSProperties = {
  backgroundColor: "#2d2d44",
  borderRadius: "6px",
  border: "1px solid #4b5563",
  padding: "12px 16px",
  marginTop: "8px",
  minHeight: "56px",
};

const emptyStyle: React.CSSProperties = {
  color: "#6b7280",
  fontSize: "13px",
  textAlign: "center",
  padding: "8px 0",
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "8px",
};

const positionBadgeStyle: React.CSSProperties = {
  fontSize: "10px",
  color: "#9ca3af",
  backgroundColor: "#374151",
  padding: "2px 6px",
  borderRadius: "3px",
  fontFamily: "monospace",
};

const clearBtnStyle: React.CSSProperties = {
  fontSize: "11px",
  color: "#9ca3af",
  backgroundColor: "transparent",
  border: "1px solid #4b5563",
  borderRadius: "3px",
  padding: "2px 8px",
  cursor: "pointer",
};

const greekStyle: React.CSSProperties = {
  fontSize: "18px",
  color: "#60a5fa",
  fontFamily: "serif",
  marginBottom: "4px",
};

const lemmaStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#9ca3af",
  fontStyle: "italic",
  marginBottom: "8px",
};

const glossStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#eaeaea",
  marginBottom: "8px",
};

const confRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "12px",
  fontSize: "11px",
  color: "#9ca3af",
  flexWrap: "wrap",
};

function confidenceColor(score: number): string {
  if (score >= 0.9) return "#22c55e";
  if (score >= 0.7) return "#facc15";
  if (score >= 0.5) return "#fb923c";
  return "#f87171";
}

export function TokenInspectorDock({
  token,
  onClear,
}: TokenInspectorDockProps) {
  if (!token) {
    return (
      <div
        style={dockStyle}
        data-testid="token-dock"
        role="region"
        aria-label="Token Inspector"
      >
        <div style={emptyStyle}>Select a token to inspect.</div>
      </div>
    );
  }

  const { position, surface, lemma, gloss, confidence } = token;
  const composite = Math.round(
    ((confidence.textual +
      confidence.grammatical +
      confidence.lexical +
      confidence.interpretive) /
      4) *
      100,
  );

  return (
    <div
      style={dockStyle}
      data-testid="token-dock"
      role="region"
      aria-label="Token Inspector"
    >
      <div style={headerStyle}>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <span style={positionBadgeStyle}>#{position + 1}</span>
          <span style={greekStyle}>{surface}</span>
        </div>
        <button
          style={clearBtnStyle}
          onClick={onClear}
          aria-label="Clear token selection"
          data-testid="dock-clear-btn"
        >
          Clear
        </button>
      </div>
      {lemma && <div style={lemmaStyle}>Lemma: {lemma}</div>}
      <div style={glossStyle}>{gloss}</div>
      <div style={confRowStyle}>
        <span>
          Composite:{" "}
          <strong style={{ color: confidenceColor(composite / 100) }}>
            {composite}%
          </strong>
        </span>
        <span>
          Textual:{" "}
          <span style={{ color: confidenceColor(confidence.textual) }}>
            {Math.round(confidence.textual * 100)}%
          </span>
        </span>
        <span>
          Grammatical:{" "}
          <span style={{ color: confidenceColor(confidence.grammatical) }}>
            {Math.round(confidence.grammatical * 100)}%
          </span>
        </span>
        <span>
          Lexical:{" "}
          <span style={{ color: confidenceColor(confidence.lexical) }}>
            {Math.round(confidence.lexical * 100)}%
          </span>
        </span>
        <span>
          Interpretive:{" "}
          <span style={{ color: confidenceColor(confidence.interpretive) }}>
            {Math.round(confidence.interpretive * 100)}%
          </span>
        </span>
      </div>
    </div>
  );
}
