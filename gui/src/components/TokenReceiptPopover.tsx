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
  backgroundColor: "#2d2d44",
  border: "1px solid #4b5563",
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
  borderBottom: "1px solid #4b5563",
  paddingBottom: "12px",
};

const surfaceStyle: React.CSSProperties = {
  fontSize: "20px",
  fontFamily: "'SBL Greek', 'Cardo', 'Gentium Plus', serif",
  color: "#60a5fa",
  fontWeight: 500,
};

const closeButtonStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  color: "#6b7280",
  cursor: "pointer",
  fontSize: "18px",
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
  fontSize: "11px",
  color: "#9ca3af",
  textTransform: "uppercase",
};

const valueStyle: React.CSSProperties = {
  fontSize: "13px",
  color: "#eaeaea",
};

const glossStyle: React.CSSProperties = {
  ...valueStyle,
  fontWeight: 500,
  color: "#22c55e",
};

const morphStyle: React.CSSProperties = {
  fontFamily: "monospace",
  fontSize: "12px",
  color: "#9ca3af",
  backgroundColor: "#1a1a2e",
  padding: "2px 6px",
  borderRadius: "3px",
};

const confidenceGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "8px",
  marginTop: "12px",
  padding: "12px",
  backgroundColor: "#1a1a2e",
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
  backgroundColor: "#374151",
  borderRadius: "3px",
  overflow: "hidden",
};

const sourceStyle: React.CSSProperties = {
  fontSize: "11px",
  color: "#6b7280",
  marginTop: "8px",
};

const linkStyle: React.CSSProperties = {
  display: "block",
  marginTop: "12px",
  padding: "8px",
  backgroundColor: "#3b82f6",
  color: "white",
  textAlign: "center",
  borderRadius: "4px",
  cursor: "pointer",
  fontSize: "12px",
  border: "none",
  width: "100%",
};

const notesStyle: React.CSSProperties = {
  fontSize: "11px",
  color: "#9ca3af",
  fontStyle: "italic",
  marginTop: "8px",
  padding: "8px",
  backgroundColor: "#1a1a2e",
  borderRadius: "4px",
};

function getConfidenceColor(score: number): string {
  if (score >= 0.8) return "#22c55e";
  if (score >= 0.6) return "#f59e0b";
  return "#ef4444";
}

function ConfidenceBar({ label, score }: { label: string; score: number }) {
  return (
    <div style={confidenceItemStyle}>
      <span style={{ fontSize: "10px", color: "#9ca3af", width: "12px" }}>
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
      <span style={{ fontSize: "10px", color: "#9ca3af", width: "28px" }}>
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
                style={{ fontSize: "12px", color: "#9ca3af", marginTop: "4px" }}
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
            fontSize: "11px",
            color:
              riskLevel === "critical"
                ? "#ef4444"
                : riskLevel === "high"
                  ? "#f59e0b"
                  : riskLevel === "medium"
                    ? "#fde68a"
                    : "#22c55e",
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
