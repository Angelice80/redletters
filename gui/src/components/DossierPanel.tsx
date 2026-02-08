/**
 * Dossier Panel component for variant traceability display.
 *
 * Sprint 8 (B5): Shows witness summaries, provenance,
 * and acknowledgement state for variants.
 */

import { useState, useEffect } from "react";
import type { ApiClient } from "../api/client";
import type {
  DossierResponse,
  DossierVariant,
  DossierWitnessSummary,
  DossierScope,
} from "../api/types";

// Styles
const panelStyle: React.CSSProperties = {
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "8px",
  overflow: "hidden",
  marginTop: "16px",
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "12px 16px",
  backgroundColor: "var(--rl-bg-card)",
  cursor: "pointer",
  userSelect: "none",
};

const headerTextStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-base)",
  fontWeight: 600,
  color: "var(--rl-text-muted)",
  textTransform: "uppercase",
};

const contentStyle: React.CSSProperties = {
  padding: "16px",
};

const variantSectionStyle: React.CSSProperties = {
  marginBottom: "16px",
  paddingBottom: "16px",
  borderBottom: "1px solid var(--rl-border-strong)",
};

const variantHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "12px",
};

const refStyle: React.CSSProperties = {
  color: "#60a5fa",
  fontWeight: 500,
  fontSize: "15px",
};

const badgeStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xs)",
  padding: "2px 6px",
  borderRadius: "3px",
  marginLeft: "8px",
};

const witnessGroupStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(3, 1fr)",
  gap: "8px",
  marginBottom: "12px",
};

const witnessTypeStyle: React.CSSProperties = {
  padding: "8px",
  backgroundColor: "var(--rl-bg-card)",
  borderRadius: "4px",
};

const witnessTypeLabelStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xs)",
  color: "var(--rl-text-dim)",
  textTransform: "uppercase",
  marginBottom: "4px",
};

const witnessListStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-sm)",
  color: "var(--rl-text)",
};

const readingCardStyle: React.CSSProperties = {
  padding: "10px",
  backgroundColor: "var(--rl-bg-card)",
  borderRadius: "4px",
  marginBottom: "8px",
};

const readingLabelStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xs)",
  fontWeight: 600,
  textTransform: "uppercase",
  marginBottom: "6px",
};

const readingTextStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-md)",
  fontFamily: "'SBL Greek', 'Cardo', 'Gentium Plus', serif",
  color: "var(--rl-text)",
  marginBottom: "4px",
};

const provenanceStyle: React.CSSProperties = {
  marginTop: "16px",
  padding: "12px",
  backgroundColor: "var(--rl-bg-card)",
  borderRadius: "4px",
};

const provenanceLabelStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xs)",
  color: "var(--rl-text-dim)",
  textTransform: "uppercase",
  marginBottom: "8px",
};

const provenanceTextStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-sm)",
  color: "var(--rl-text-muted)",
};

const loadingStyle: React.CSSProperties = {
  padding: "16px",
  textAlign: "center",
  color: "var(--rl-text-dim)",
};

const errorStyle: React.CSSProperties = {
  padding: "12px",
  backgroundColor: "#7f1d1d",
  color: "#fca5a5",
  borderRadius: "4px",
  fontSize: "var(--rl-fs-base)",
};

function getSignificanceBadgeStyle(significance: string): React.CSSProperties {
  const bgColor =
    significance === "major"
      ? "var(--rl-error)"
      : significance === "significant"
        ? "var(--rl-warning)"
        : "var(--rl-border-strong)";
  return { ...badgeStyle, backgroundColor: bgColor, color: "white" };
}

function getGatingBadgeStyle(gating: string): React.CSSProperties {
  return {
    ...badgeStyle,
    backgroundColor:
      gating === "requires_acknowledgement" ? "#854d0e" : "var(--rl-border-strong)",
    color: gating === "requires_acknowledgement" ? "#fde68a" : "var(--rl-text-muted)",
  };
}

function WitnessSummaryDisplay({
  summary,
}: {
  summary: DossierWitnessSummary;
}) {
  const groups = [
    { label: "Papyri", witnesses: summary.papyri, color: "var(--rl-success)" },
    { label: "Uncials", witnesses: summary.uncials, color: "var(--rl-primary)" },
    { label: "Minuscules", witnesses: summary.minuscules, color: "#8b5cf6" },
    { label: "Versions", witnesses: summary.versions, color: "var(--rl-warning)" },
    { label: "Fathers", witnesses: summary.fathers, color: "#ec4899" },
    { label: "Editions", witnesses: summary.editions, color: "var(--rl-text-dim)" },
  ].filter((g) => g.witnesses.length > 0);

  if (groups.length === 0) {
    return (
      <div style={{ color: "var(--rl-text-dim)", fontSize: "var(--rl-fs-sm)" }}>
        No witness data available
      </div>
    );
  }

  return (
    <div style={witnessGroupStyle}>
      {groups.map((group) => (
        <div key={group.label} style={witnessTypeStyle}>
          <div style={{ ...witnessTypeLabelStyle, color: group.color }}>
            {group.label} ({group.witnesses.length})
          </div>
          <div style={witnessListStyle}>
            {group.witnesses.slice(0, 5).join(", ")}
            {group.witnesses.length > 5 && ` +${group.witnesses.length - 5}`}
          </div>
        </div>
      ))}
    </div>
  );
}

function VariantDossierCard({ variant }: { variant: DossierVariant }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div style={variantSectionStyle}>
      <div style={variantHeaderStyle}>
        <div>
          <span style={refStyle}>{variant.ref}</span>
          <span style={getSignificanceBadgeStyle(variant.significance)}>
            {variant.significance}
          </span>
          <span style={getGatingBadgeStyle(variant.gating_requirement)}>
            {variant.gating_requirement === "requires_acknowledgement"
              ? "ACK required"
              : "no gate"}
          </span>
          {variant.acknowledgement.acknowledged && (
            <span
              style={{
                ...badgeStyle,
                backgroundColor: "var(--rl-success)",
                color: "white",
              }}
            >
              acknowledged
            </span>
          )}
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            background: "none",
            border: "none",
            color: "var(--rl-text-dim)",
            cursor: "pointer",
            fontSize: "var(--rl-fs-sm)",
          }}
        >
          {expanded ? "Hide details" : "Show details"}
        </button>
      </div>

      {/* Reason summary */}
      <div style={{ marginBottom: "12px" }}>
        <span style={{ color: "var(--rl-text-muted)", fontSize: "var(--rl-fs-base)" }}>
          {variant.reason.summary}
        </span>
        {variant.reason.detail && (
          <span
            style={{ color: "var(--rl-text-dim)", fontSize: "var(--rl-fs-sm)", marginLeft: "8px" }}
          >
            ({variant.reason.detail})
          </span>
        )}
      </div>

      {/* Readings */}
      {variant.readings.map((reading) => (
        <div key={reading.index} style={readingCardStyle}>
          <div
            style={{
              ...readingLabelStyle,
              color: reading.is_spine ? "var(--rl-success)" : "var(--rl-warning)",
            }}
          >
            {reading.is_spine
              ? "SBLGNT [spine]"
              : `Reading ${reading.index + 1}`}
          </div>
          <div style={readingTextStyle}>{reading.text || "(omission)"}</div>

          {expanded && (
            <>
              <WitnessSummaryDisplay summary={reading.witness_summary} />
              {reading.source_packs.length > 0 && (
                <div
                  style={{
                    fontSize: "var(--rl-fs-xs)",
                    color: "var(--rl-text-dim)",
                    marginTop: "8px",
                  }}
                >
                  Source packs: {reading.source_packs.join(", ")}
                </div>
              )}
            </>
          )}
        </div>
      ))}
    </div>
  );
}

interface DossierPanelProps {
  client: ApiClient | null;
  reference: string;
  scope?: DossierScope;
  sessionId?: string;
  defaultExpanded?: boolean;
}

export function DossierPanel({
  client,
  reference,
  scope = "verse",
  sessionId,
  defaultExpanded = false,
}: DossierPanelProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dossier, setDossier] = useState<DossierResponse | null>(null);

  useEffect(() => {
    if (!expanded || !client || !reference) return;

    const fetchDossier = async () => {
      setLoading(true);
      setError(null);

      try {
        const result = await client.getDossier(reference, scope, sessionId);
        setDossier(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load dossier");
      } finally {
        setLoading(false);
      }
    };

    fetchDossier();
  }, [expanded, client, reference, scope, sessionId]);

  return (
    <div style={panelStyle}>
      <div style={headerStyle} onClick={() => setExpanded(!expanded)}>
        <span style={headerTextStyle}>
          Variant Dossier {dossier && `(${dossier.variants.length} variants)`}
        </span>
        <span style={{ color: "var(--rl-text-dim)" }}>{expanded ? "−" : "+"}</span>
      </div>

      {expanded && (
        <div style={contentStyle}>
          {loading && <div style={loadingStyle}>Loading dossier...</div>}

          {error && <div style={errorStyle}>{error}</div>}

          {dossier && (
            <>
              {/* Spine info */}
              <div style={{ marginBottom: "16px" }}>
                <span style={{ color: "var(--rl-text-dim)", fontSize: "var(--rl-fs-sm)" }}>
                  Spine: {dossier.spine.source_id}
                </span>
                {dossier.spine.text && (
                  <div
                    style={{
                      ...readingTextStyle,
                      marginTop: "4px",
                      color: "var(--rl-success)",
                    }}
                  >
                    {dossier.spine.text}
                  </div>
                )}
              </div>

              {/* Witness density note */}
              {dossier.witness_density_note && (
                <div
                  style={{
                    padding: "8px 12px",
                    backgroundColor: "#1e3a5f",
                    borderRadius: "4px",
                    marginBottom: "16px",
                    fontSize: "var(--rl-fs-sm)",
                    color: "#93c5fd",
                  }}
                >
                  {dossier.witness_density_note}
                </div>
              )}

              {/* Variants */}
              {dossier.variants.length === 0 ? (
                <div
                  style={{
                    color: "var(--rl-text-dim)",
                    textAlign: "center",
                    padding: "16px",
                  }}
                >
                  No variants at this reference
                </div>
              ) : (
                dossier.variants.map((variant) => (
                  <VariantDossierCard key={variant.ref} variant={variant} />
                ))
              )}

              {/* Provenance */}
              <div style={provenanceStyle}>
                <div style={provenanceLabelStyle}>Provenance</div>
                <div style={provenanceTextStyle}>
                  <div>Spine: {dossier.provenance.spine_source}</div>
                  {dossier.provenance.comparative_packs.length > 0 && (
                    <div>
                      Comparative packs:{" "}
                      {dossier.provenance.comparative_packs.join(", ")}
                    </div>
                  )}
                  <div
                    style={{
                      marginTop: "4px",
                      fontSize: "var(--rl-fs-xs)",
                      color: "var(--rl-text-dim)",
                    }}
                  >
                    Generated: {new Date(dossier.generated_at).toLocaleString()}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
