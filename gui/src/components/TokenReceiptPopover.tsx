/**
 * Token Receipt Popover component.
 *
 * Shows mini receipt for a single token when clicked.
 * Part of progressive disclosure - full ledger stays in Receipts tab.
 */

import type { TokenLedger } from "../api/types";
import { computeTokenRisk, getRiskLevel } from "../utils/heatmapUtils";

interface TokenReceiptPopoverProps {
  token: TokenLedger;
  anchorEl: HTMLElement | null;
  onClose: () => void;
  onViewFullLedger?: () => void;
}

// Styles
const popoverStyle: React.CSSProperties = {
  position: "absolute",
  backgroundColor: "var(--rl-bg-card)",
  border: "1px solid var(--rl-border-strong)",
  borderRadius: "8px",
  padding: "16px",
  minWidth: "280px",
  maxWidth: "360px",
  boxShadow: "0 4px 20px rgba(0, 0, 0, 0.4)",
  zIndex: 1000,
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  marginBottom: "12px",
  borderBottom: "1px solid var(--rl-border-strong)",
  paddingBottom: "12px",
};

const surfaceStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-lg)",
  fontFamily: "'SBL Greek', 'Cardo', 'Gentium Plus', serif",
  color: "#60a5fa",
  fontWeight: 500,
};

const closeButtonStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  color: "var(--rl-text-dim)",
  cursor: "pointer",
  fontSize: "var(--rl-fs-lg)",
  padding: "0",
  lineHeight: 1,
};

const rowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "8px",
};

const labelStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xs)",
  color: "var(--rl-text-muted)",
  textTransform: "uppercase",
};

const valueStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-base)",
  color: "var(--rl-text)",
};

const glossStyle: React.CSSProperties = {
  ...valueStyle,
  fontWeight: 500,
  color: "var(--rl-success)",
};

const morphStyle: React.CSSProperties = {
  fontFamily: "var(--rl-font-mono)",
  fontSize: "var(--rl-fs-sm)",
  color: "var(--rl-text-muted)",
  backgroundColor: "var(--rl-bg-app)",
  padding: "2px 6px",
  borderRadius: "3px",
};

const confidenceGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "8px",
  marginTop: "12px",
  padding: "12px",
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "4px",
};

const confidenceItemStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
};

const confidenceBarStyle: React.CSSProperties = {
  flex: 1,
  height: "6px",
  backgroundColor: "var(--rl-border-strong)",
  borderRadius: "3px",
  overflow: "hidden",
};

const sourceStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xs)",
  color: "var(--rl-text-dim)",
  marginTop: "8px",
};

const linkStyle: React.CSSProperties = {
  display: "block",
  marginTop: "12px",
  padding: "8px",
  backgroundColor: "var(--rl-primary)",
  color: "white",
  textAlign: "center",
  borderRadius: "4px",
  cursor: "pointer",
  fontSize: "var(--rl-fs-sm)",
  border: "none",
  width: "100%",
};

const notesStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xs)",
  color: "var(--rl-text-muted)",
  fontStyle: "italic",
  marginTop: "8px",
  padding: "8px",
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "4px",
};

function getConfidenceColor(score: number): string {
  if (score >= 0.8) return "var(--rl-success)";
  if (score >= 0.6) return "var(--rl-warning)";
  return "var(--rl-error)";
}

function ConfidenceBar({ label, score }: { label: string; score: number }) {
  return (
    <div style={confidenceItemStyle}>
      <span style={{ fontSize: "var(--rl-fs-xs)", color: "var(--rl-text-muted)", width: "12px" }}>
        {label}
      </span>
      <div style={confidenceBarStyle}>
        <div
          style={{
            width: `${score * 100}%`,
            height: "100%",
            backgroundColor: getConfidenceColor(score),
          }}
        />
      </div>
      <span style={{ fontSize: "var(--rl-fs-xs)", color: "var(--rl-text-muted)", width: "28px" }}>
        {(score * 100).toFixed(0)}%
      </span>
    </div>
  );
}

export function TokenReceiptPopover({
  token,
  anchorEl,
  onClose,
  onViewFullLedger,
}: TokenReceiptPopoverProps) {
  if (!anchorEl) return null;

  // Position the popover below the anchor
  const rect = anchorEl.getBoundingClientRect();
  const scrollTop = window.scrollY || document.documentElement.scrollTop;
  const scrollLeft = window.scrollX || document.documentElement.scrollLeft;

  const popoverPosition: React.CSSProperties = {
    ...popoverStyle,
    top: rect.bottom + scrollTop + 8,
    left: Math.max(8, rect.left + scrollLeft - 100),
  };

  const risk = computeTokenRisk(token.confidence);
  const riskLevel = getRiskLevel(risk);

  return (
    <>
      {/* Backdrop */}
      <div
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 999,
        }}
        onClick={onClose}
      />

      {/* Popover */}
      <div style={popoverPosition}>
        {/* Header */}
        <div style={headerStyle}>
          <div>
            <div style={surfaceStyle}>{token.surface}</div>
            {token.lemma && (
              <div
                style={{ fontSize: "var(--rl-fs-sm)", color: "var(--rl-text-muted)", marginTop: "4px" }}
              >
                Lemma: <span style={{ color: "#60a5fa" }}>{token.lemma}</span>
              </div>
            )}
          </div>
          <button style={closeButtonStyle} onClick={onClose}>
            ×
          </button>
        </div>

        {/* Morphology */}
        {token.morph && (
          <div style={rowStyle}>
            <span style={labelStyle}>Morphology</span>
            <span style={morphStyle}>{token.morph}</span>
          </div>
        )}

        {/* Gloss */}
        <div style={rowStyle}>
          <span style={labelStyle}>Gloss</span>
          <span style={glossStyle}>{token.gloss}</span>
        </div>

        {/* Source */}
        <div style={sourceStyle}>Source: {token.gloss_source}</div>

        {/* Confidence Grid */}
        <div style={confidenceGridStyle}>
          <ConfidenceBar label="T" score={token.confidence.textual} />
          <ConfidenceBar label="G" score={token.confidence.grammatical} />
          <ConfidenceBar label="L" score={token.confidence.lexical} />
          <ConfidenceBar label="I" score={token.confidence.interpretive} />
        </div>

        {/* Risk indicator */}
        <div
          style={{
            marginTop: "8px",
            fontSize: "var(--rl-fs-xs)",
            color:
              riskLevel === "critical"
                ? "var(--rl-error)"
                : riskLevel === "high"
                  ? "var(--rl-warning)"
                  : riskLevel === "medium"
                    ? "#fde68a"
                    : "var(--rl-success)",
          }}
        >
          Risk: {(risk * 100).toFixed(0)}% ({riskLevel})
        </div>

        {/* Notes */}
        {token.notes.length > 0 && (
          <div style={notesStyle}>{token.notes.join("; ")}</div>
        )}

        {/* View full ledger link */}
        {onViewFullLedger && (
          <button style={linkStyle} onClick={onViewFullLedger}>
            View Full Ledger
          </button>
        )}
      </div>
    </>
  );
}

export default TokenReceiptPopover;
