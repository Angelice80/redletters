/**
 * Ledger Panel for Traceable Mode display.
 *
 * Sprint 10: Shows token-level analysis with:
 * - Token table (surface, lemma, morph, gloss)
 * - Per-token confidence bars (reusing ADR-010 presentation style)
 * - Provenance badges (spine + comparative pack IDs)
 */

import { useState } from "react";
import type {
  VerseLedger,
  TokenLedger,
  TokenConfidence,
  LedgerProvenance,
  EvidenceClassSummary,
} from "../api/types";

// Styles
const panelStyle: React.CSSProperties = {
  marginTop: "16px",
  backgroundColor: "#1a1a2e",
  borderRadius: "8px",
  overflow: "hidden",
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "12px 16px",
  backgroundColor: "#2d2d44",
  cursor: "pointer",
  userSelect: "none",
};

const headerTextStyle: React.CSSProperties = {
  fontSize: "14px",
  fontWeight: 500,
  color: "#60a5fa",
};

const toggleStyle: React.CSSProperties = {
  fontSize: "16px",
  color: "#6b7280",
};

const contentStyle: React.CSSProperties = {
  padding: "16px",
};

const tableContainerStyle: React.CSSProperties = {
  overflowX: "auto",
};

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "13px",
};

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "8px 12px",
  borderBottom: "1px solid #4b5563",
  color: "#9ca3af",
  fontWeight: 500,
  fontSize: "11px",
  textTransform: "uppercase",
};

const tdStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderBottom: "1px solid #2d2d44",
  color: "#eaeaea",
  verticalAlign: "top",
};

const greekCellStyle: React.CSSProperties = {
  ...tdStyle,
  fontFamily: "'SBL Greek', 'Cardo', 'Gentium Plus', serif",
  fontSize: "15px",
  color: "#60a5fa",
};

const morphCellStyle: React.CSSProperties = {
  ...tdStyle,
  fontFamily: "monospace",
  fontSize: "11px",
  color: "#9ca3af",
};

const glossSourceStyle: React.CSSProperties = {
  fontSize: "10px",
  color: "#6b7280",
  marginTop: "2px",
};

const noteStyle: React.CSSProperties = {
  fontSize: "10px",
  color: "#9ca3af",
  fontStyle: "italic",
};

const confidenceContainerStyle: React.CSSProperties = {
  display: "flex",
  gap: "4px",
  alignItems: "center",
};

const confidenceBarStyle: React.CSSProperties = {
  width: "30px",
  height: "6px",
  backgroundColor: "#374151",
  borderRadius: "3px",
  overflow: "hidden",
};

const provenanceStyle: React.CSSProperties = {
  marginTop: "16px",
  padding: "12px",
  backgroundColor: "#2d2d44",
  borderRadius: "4px",
};

const badgeStyle: React.CSSProperties = {
  display: "inline-block",
  padding: "2px 8px",
  borderRadius: "3px",
  fontSize: "11px",
  fontWeight: 500,
  marginRight: "6px",
  marginBottom: "4px",
};

const spineBadgeStyle: React.CSSProperties = {
  ...badgeStyle,
  backgroundColor: "#22c55e",
  color: "#1a1a2e",
};

const comparativeBadgeStyle: React.CSSProperties = {
  ...badgeStyle,
  backgroundColor: "#3b82f6",
  color: "white",
};

const evidenceBadgeStyle: React.CSSProperties = {
  ...badgeStyle,
  backgroundColor: "#6b7280",
  color: "white",
};

// Helper to get confidence bar color
function getConfidenceColor(score: number): string {
  if (score >= 0.8) return "#22c55e";
  if (score >= 0.6) return "#f59e0b";
  return "#ef4444";
}

// Mini confidence bars component
function MiniConfidenceBars({ confidence }: { confidence: TokenConfidence }) {
  const layers = [
    { key: "T", value: confidence.textual },
    { key: "G", value: confidence.grammatical },
    { key: "L", value: confidence.lexical },
    { key: "I", value: confidence.interpretive },
  ];

  return (
    <div style={confidenceContainerStyle} title="T/G/L/I confidence">
      {layers.map(({ key, value }) => (
        <div
          key={key}
          style={{ display: "flex", alignItems: "center", gap: "2px" }}
        >
          <span style={{ fontSize: "9px", color: "#6b7280" }}>{key}</span>
          <div style={confidenceBarStyle}>
            <div
              style={{
                width: `${value * 100}%`,
                height: "100%",
                backgroundColor: getConfidenceColor(value),
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

// Provenance badges component
function ProvenanceBadges({ provenance }: { provenance: LedgerProvenance }) {
  const { evidence_class_summary: ecs } = provenance;
  const total =
    ecs.manuscript_count +
    ecs.edition_count +
    ecs.tradition_count +
    ecs.other_count;

  return (
    <div style={provenanceStyle}>
      <div style={{ fontSize: "11px", color: "#9ca3af", marginBottom: "8px" }}>
        PROVENANCE
      </div>
      <div>
        <span style={spineBadgeStyle}>Spine: {provenance.spine_source_id}</span>
        {provenance.comparative_sources_used.map((id) => (
          <span key={id} style={comparativeBadgeStyle}>
            {id}
          </span>
        ))}
      </div>
      <div style={{ marginTop: "8px" }}>
        <span
          style={{ fontSize: "11px", color: "#9ca3af", marginRight: "8px" }}
        >
          Evidence:
        </span>
        {ecs.manuscript_count > 0 && (
          <span style={evidenceBadgeStyle}>{ecs.manuscript_count} MSS</span>
        )}
        {ecs.edition_count > 0 && (
          <span style={evidenceBadgeStyle}>{ecs.edition_count} Ed</span>
        )}
        {ecs.tradition_count > 0 && (
          <span style={evidenceBadgeStyle}>{ecs.tradition_count} Trad</span>
        )}
        {ecs.other_count > 0 && (
          <span style={evidenceBadgeStyle}>{ecs.other_count} Other</span>
        )}
        {total === 0 && (
          <span style={{ color: "#6b7280", fontSize: "11px" }}>
            No recorded support
          </span>
        )}
      </div>
    </div>
  );
}

// Token table component
function TokenTable({ tokens }: { tokens: TokenLedger[] }) {
  return (
    <div style={tableContainerStyle}>
      <table style={tableStyle}>
        <thead>
          <tr>
            <th style={thStyle}>#</th>
            <th style={thStyle}>Surface</th>
            <th style={thStyle}>Lemma</th>
            <th style={thStyle}>Morph</th>
            <th style={thStyle}>Gloss</th>
            <th style={thStyle}>Confidence</th>
          </tr>
        </thead>
        <tbody>
          {tokens.map((token, idx) => (
            <tr key={idx}>
              <td style={{ ...tdStyle, color: "#6b7280", width: "40px" }}>
                {token.position + 1}
              </td>
              <td style={greekCellStyle}>
                {token.surface}
                {token.notes.length > 0 && (
                  <div style={noteStyle}>{token.notes.join(", ")}</div>
                )}
              </td>
              <td style={greekCellStyle}>{token.lemma || "—"}</td>
              <td style={morphCellStyle}>{token.morph || "—"}</td>
              <td style={tdStyle}>
                {token.gloss}
                <div style={glossSourceStyle}>via {token.gloss_source}</div>
              </td>
              <td style={tdStyle}>
                <MiniConfidenceBars confidence={token.confidence} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Main LedgerPanel component
interface LedgerPanelProps {
  ledger: VerseLedger;
  defaultExpanded?: boolean;
}

export function LedgerPanel({
  ledger,
  defaultExpanded = false,
}: LedgerPanelProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div style={panelStyle}>
      <div style={headerStyle} onClick={() => setExpanded(!expanded)}>
        <span style={headerTextStyle}>
          Ledger: {ledger.normalized_ref} ({ledger.tokens.length} tokens)
        </span>
        <span style={toggleStyle}>{expanded ? "−" : "+"}</span>
      </div>
      {expanded && (
        <div style={contentStyle}>
          <TokenTable tokens={ledger.tokens} />
          <ProvenanceBadges provenance={ledger.provenance} />
        </div>
      )}
    </div>
  );
}

// Multi-verse ledger list
interface LedgerListProps {
  ledgers: VerseLedger[];
}

export function LedgerList({ ledgers }: LedgerListProps) {
  if (ledgers.length === 0) {
    return (
      <div style={{ color: "#6b7280", fontSize: "13px", padding: "16px" }}>
        No ledger data available. Ledger is only populated in traceable mode.
      </div>
    );
  }

  return (
    <div>
      {ledgers.map((ledger, idx) => (
        <LedgerPanel
          key={ledger.verse_id}
          ledger={ledger}
          defaultExpanded={idx === 0}
        />
      ))}
    </div>
  );
}

export default LedgerPanel;
