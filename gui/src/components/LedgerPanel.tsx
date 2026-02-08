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
} from "../api/types";

// Styles
const panelStyle: React.CSSProperties = {
  marginTop: "16px",
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "8px",
  overflow: "hidden",
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "12px 16px",
  backgroundColor: "var(--rl-bg-card)",
  cursor: "pointer",
  userSelect: "none",
};

const headerTextStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-base)",
  fontWeight: 500,
  color: "#60a5fa",
};

const toggleStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-md)",
  color: "var(--rl-text-dim)",
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
  fontSize: "var(--rl-fs-base)",
};

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "8px 12px",
  borderBottom: "1px solid var(--rl-border-strong)",
  color: "var(--rl-text-muted)",
  fontWeight: 500,
  fontSize: "var(--rl-fs-xs)",
  textTransform: "uppercase",
};

const tdStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderBottom: "1px solid var(--rl-bg-card)",
  color: "var(--rl-text)",
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
  fontFamily: "var(--rl-font-mono)",
  fontSize: "var(--rl-fs-xs)",
  color: "var(--rl-text-muted)",
};

const glossSourceStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xs)",
  color: "var(--rl-text-dim)",
  marginTop: "2px",
};

const noteStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xs)",
  color: "var(--rl-text-muted)",
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
  backgroundColor: "var(--rl-border-strong)",
  borderRadius: "3px",
  overflow: "hidden",
};

const provenanceStyle: React.CSSProperties = {
  marginTop: "16px",
  padding: "12px",
  backgroundColor: "var(--rl-bg-card)",
  borderRadius: "4px",
};

const badgeStyle: React.CSSProperties = {
  display: "inline-block",
  padding: "2px 8px",
  borderRadius: "3px",
  fontSize: "var(--rl-fs-xs)",
  fontWeight: 500,
  marginRight: "6px",
  marginBottom: "4px",
};

const spineBadgeStyle: React.CSSProperties = {
  ...badgeStyle,
  backgroundColor: "var(--rl-success)",
  color: "var(--rl-bg-app)",
};

const comparativeBadgeStyle: React.CSSProperties = {
  ...badgeStyle,
  backgroundColor: "var(--rl-primary)",
  color: "white",
};

const evidenceBadgeStyle: React.CSSProperties = {
  ...badgeStyle,
  backgroundColor: "var(--rl-text-dim)",
  color: "white",
};

// Helper to get confidence bar color
function getConfidenceColor(score: number): string {
  if (score >= 0.8) return "var(--rl-success)";
  if (score >= 0.6) return "var(--rl-warning)";
  return "var(--rl-error)";
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
          <span style={{ fontSize: "9px", color: "var(--rl-text-dim)" }}>
            {key}
          </span>
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
      <div
        style={{
          fontSize: "var(--rl-fs-xs)",
          color: "var(--rl-text-muted)",
          marginBottom: "8px",
        }}
      >
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
          style={{
            fontSize: "var(--rl-fs-xs)",
            color: "var(--rl-text-muted)",
            marginRight: "8px",
          }}
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
          <span style={{ color: "var(--rl-text-dim)", fontSize: "var(--rl-fs-xs)" }}>
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
              <td
                style={{
                  ...tdStyle,
                  color: "var(--rl-text-dim)",
                  width: "40px",
                }}
              >
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
      <div
        style={{
          color: "var(--rl-text-dim)",
          fontSize: "var(--rl-fs-base)",
          padding: "16px",
        }}
      >
        No ledger data available for this translation.
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
