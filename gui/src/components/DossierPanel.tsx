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
  backgroundColor: "#1a1a2e",
  borderRadius: "8px",
  overflow: "hidden",
  marginTop: "16px",
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "12px 16px",
  backgroundColor: "#2d2d44",
  cursor: "pointer",
  userSelect: "none",
};

const headerTextStyle: React.CSSProperties = {
  fontSize: "14px",
  fontWeight: 600,
  color: "#9ca3af",
  textTransform: "uppercase",
};

const contentStyle: React.CSSProperties = {
  padding: "16px",
};

const variantSectionStyle: React.CSSProperties = {
  marginBottom: "16px",
  paddingBottom: "16px",
  borderBottom: "1px solid #374151",
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
  fontSize: "10px",
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
  backgroundColor: "#2d2d44",
  borderRadius: "4px",
};

const witnessTypeLabelStyle: React.CSSProperties = {
  fontSize: "10px",
  color: "#6b7280",
  textTransform: "uppercase",
  marginBottom: "4px",
};

const witnessListStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#eaeaea",
};

const readingCardStyle: React.CSSProperties = {
  padding: "10px",
  backgroundColor: "#2d2d44",
  borderRadius: "4px",
  marginBottom: "8px",
};

const readingLabelStyle: React.CSSProperties = {
  fontSize: "10px",
  fontWeight: 600,
  textTransform: "uppercase",
  marginBottom: "6px",
};

const readingTextStyle: React.CSSProperties = {
  fontSize: "16px",
  fontFamily: "'SBL Greek', 'Cardo', 'Gentium Plus', serif",
  color: "#eaeaea",
  marginBottom: "4px",
};

const provenanceStyle: React.CSSProperties = {
  marginTop: "16px",
  padding: "12px",
  backgroundColor: "#2d2d44",
  borderRadius: "4px",
};

const provenanceLabelStyle: React.CSSProperties = {
  fontSize: "11px",
  color: "#6b7280",
  textTransform: "uppercase",
  marginBottom: "8px",
};

const provenanceTextStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#9ca3af",
};

const loadingStyle: React.CSSProperties = {
  padding: "16px",
  textAlign: "center",
  color: "#6b7280",
};

const errorStyle: React.CSSProperties = {
  padding: "12px",
  backgroundColor: "#7f1d1d",
  color: "#fca5a5",
  borderRadius: "4px",
  fontSize: "13px",
};

function getSignificanceBadgeStyle(significance: string): React.CSSProperties {
  const bgColor =
    significance === "major"
      ? "#ef4444"
      : significance === "significant"
        ? "#f59e0b"
        : "#4b5563";
  return { ...badgeStyle, backgroundColor: bgColor, color: "white" };
}

function getGatingBadgeStyle(gating: string): React.CSSProperties {
  return {
    ...badgeStyle,
    backgroundColor:
      gating === "requires_acknowledgement" ? "#854d0e" : "#374151",
    color: gating === "requires_acknowledgement" ? "#fde68a" : "#9ca3af",
  };
}

function WitnessSummaryDisplay({
  summary,
}: {
  summary: DossierWitnessSummary;
}) {
  const groups = [
    { label: "Papyri", witnesses: summary.papyri, color: "#22c55e" },
    { label: "Uncials", witnesses: summary.uncials, color: "#3b82f6" },
    { label: "Minuscules", witnesses: summary.minuscules, color: "#8b5cf6" },
    { label: "Versions", witnesses: summary.versions, color: "#f59e0b" },
    { label: "Fathers", witnesses: summary.fathers, color: "#ec4899" },
    { label: "Editions", witnesses: summary.editions, color: "#6b7280" },
  ].filter((g) => g.witnesses.length > 0);

  if (groups.length === 0) {
    return (
      <div style={{ color: "#6b7280", fontSize: "12px" }}>
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
                backgroundColor: "#22c55e",
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
            color: "#6b7280",
            cursor: "pointer",
            fontSize: "12px",
          }}
        >
          {expanded ? "Hide details" : "Show details"}
        </button>
      </div>

      {/* Reason summary */}
      <div style={{ marginBottom: "12px" }}>
        <span style={{ color: "#9ca3af", fontSize: "13px" }}>
          {variant.reason.summary}
        </span>
        {variant.reason.detail && (
          <span
            style={{ color: "#6b7280", fontSize: "12px", marginLeft: "8px" }}
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
              color: reading.is_spine ? "#22c55e" : "#f59e0b",
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
                    fontSize: "11px",
                    color: "#6b7280",
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
        <span style={{ color: "#6b7280" }}>{expanded ? "−" : "+"}</span>
      </div>

      {expanded && (
        <div style={contentStyle}>
          {loading && <div style={loadingStyle}>Loading dossier...</div>}

          {error && <div style={errorStyle}>{error}</div>}

          {dossier && (
            <>
              {/* Spine info */}
              <div style={{ marginBottom: "16px" }}>
                <span style={{ color: "#6b7280", fontSize: "12px" }}>
                  Spine: {dossier.spine.source_id}
                </span>
                {dossier.spine.text && (
                  <div
                    style={{
                      ...readingTextStyle,
                      marginTop: "4px",
                      color: "#22c55e",
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
                    fontSize: "12px",
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
                    color: "#6b7280",
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
                      fontSize: "11px",
                      color: "#6b7280",
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
