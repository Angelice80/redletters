/**
 * Gate screen for variant acknowledgement.
 *
 * Sprint 5: Shows side-by-side variants with witness info,
 * SBLGNT default highlighted, and acknowledge button that
 * auto-retries translation.
 */

import { useState, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAppStore, selectSettings } from "../store";
import type { ApiClient } from "../api/client";
import type { GateResponse, VariantDisplay } from "../api/types";
import { isGateResponse } from "../api/types";
import { DossierPanel } from "../components/DossierPanel";

interface GateProps {
  client: ApiClient | null;
}

// Styles
const containerStyle: React.CSSProperties = {
  padding: "24px",
  maxWidth: "900px",
};

const warningBannerStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "12px",
  padding: "16px 20px",
  backgroundColor: "#854d0e",
  borderRadius: "8px",
  marginBottom: "24px",
};

const warningIconStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xl)",
};

const titleStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-lg)",
  fontWeight: 600,
  color: "#fef9c3",
};

const subtitleStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-base)",
  color: "#fde68a",
  marginTop: "4px",
};

const sectionStyle: React.CSSProperties = {
  backgroundColor: "var(--rl-bg-card)",
  borderRadius: "8px",
  padding: "20px",
  marginBottom: "16px",
};

const sectionHeaderStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-base)",
  fontWeight: 600,
  color: "var(--rl-text-muted)",
  marginBottom: "16px",
  textTransform: "uppercase",
};

const variantCardStyle: React.CSSProperties = {
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "8px",
  padding: "16px",
  marginBottom: "12px",
};

const variantHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "12px",
};

const readingRowStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "16px",
  marginTop: "12px",
};

const readingCardStyle: React.CSSProperties = {
  padding: "12px",
  borderRadius: "6px",
  border: "2px solid transparent",
};

const readingSelectedStyle: React.CSSProperties = {
  ...readingCardStyle,
  backgroundColor: "#1e3a5f",
  border: "2px solid var(--rl-primary)",
};

const readingUnselectedStyle: React.CSSProperties = {
  ...readingCardStyle,
  backgroundColor: "var(--rl-bg-app)",
  border: "2px solid var(--rl-border-strong)",
};

const readingLabelStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xs)",
  fontWeight: 600,
  textTransform: "uppercase",
  marginBottom: "8px",
};

const greekTextStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-lg)",
  fontFamily: "'SBL Greek', 'Cardo', 'Gentium Plus', serif",
  marginBottom: "8px",
};

const witnessTextStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-sm)",
  color: "var(--rl-text-dim)",
};

const buttonRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "center",
  gap: "16px",
  marginTop: "24px",
};

const primaryButtonStyle: React.CSSProperties = {
  padding: "12px 32px",
  fontSize: "var(--rl-fs-md)",
  fontWeight: 500,
  backgroundColor: "var(--rl-success)",
  color: "white",
  border: "none",
  borderRadius: "6px",
  cursor: "pointer",
};

const secondaryButtonStyle: React.CSSProperties = {
  padding: "12px 24px",
  fontSize: "var(--rl-fs-base)",
  fontWeight: 500,
  backgroundColor: "var(--rl-border-strong)",
  color: "var(--rl-text)",
  border: "none",
  borderRadius: "6px",
  cursor: "pointer",
};

const disabledButtonStyle: React.CSSProperties = {
  ...primaryButtonStyle,
  backgroundColor: "var(--rl-border-strong)",
  cursor: "not-allowed",
};

const statusStripStyle: React.CSSProperties = {
  display: "flex",
  gap: "16px",
  marginTop: "24px",
  padding: "12px",
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "4px",
  fontSize: "var(--rl-fs-sm)",
  color: "var(--rl-text-dim)",
};

const requiredAckStyle: React.CSSProperties = {
  padding: "8px 12px",
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "4px",
  marginBottom: "8px",
  fontSize: "var(--rl-fs-base)",
};

// Sprint 7: Styles for multi-ack button
const multiAckButtonStyle: React.CSSProperties = {
  padding: "12px 24px",
  fontSize: "var(--rl-fs-base)",
  fontWeight: 500,
  backgroundColor: "var(--rl-warning)",
  color: "white",
  border: "none",
  borderRadius: "6px",
  cursor: "pointer",
};

const reasonBadgeStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xs)",
  padding: "2px 6px",
  borderRadius: "3px",
  backgroundColor: "var(--rl-border-strong)",
  color: "var(--rl-text-muted)",
  marginLeft: "8px",
};

interface VariantSelectionState {
  [variantRef: string]: number; // variant_ref -> selected reading index
}

function VariantCard({
  variant,
  selectedIndex,
  onSelect,
}: {
  variant: VariantDisplay;
  selectedIndex: number;
  onSelect: (index: number) => void;
}) {
  return (
    <div style={variantCardStyle}>
      <div style={variantHeaderStyle}>
        <span style={{ color: "#60a5fa", fontWeight: 500, fontSize: "var(--rl-fs-md)" }}>
          {variant.ref}
        </span>
        <span
          style={{
            fontSize: "var(--rl-fs-xs)",
            padding: "4px 8px",
            borderRadius: "4px",
            backgroundColor:
              variant.significance === "major"
                ? "var(--rl-error)"
                : variant.significance === "significant"
                  ? "var(--rl-warning)"
                  : "var(--rl-border-strong)",
            color: "white",
          }}
        >
          {variant.significance}
        </span>
      </div>

      <div style={{ color: "var(--rl-text-muted)", fontSize: "var(--rl-fs-base)", marginBottom: "12px" }}>
        Position {variant.position} in verse
      </div>

      <div style={readingRowStyle}>
        {/* SBLGNT Reading (always index 0) */}
        <div
          style={
            selectedIndex === 0 ? readingSelectedStyle : readingUnselectedStyle
          }
          onClick={() => onSelect(0)}
        >
          <div style={{ ...readingLabelStyle, color: "var(--rl-success)" }}>
            SBLGNT [default]
          </div>
          <div style={{ ...greekTextStyle, color: "var(--rl-text)" }}>
            {variant.sblgnt_reading}
          </div>
          <div style={witnessTextStyle}>{variant.sblgnt_witnesses}</div>
          <div style={{ marginTop: "8px" }}>
            {selectedIndex === 0 ? (
              <span style={{ color: "var(--rl-success)", fontSize: "var(--rl-fs-sm)" }}>
                Selected
              </span>
            ) : (
              <span style={{ color: "var(--rl-text-dim)", fontSize: "var(--rl-fs-sm)" }}>
                Click to select
              </span>
            )}
          </div>
        </div>

        {/* Alternate readings */}
        {variant.alternate_readings.map((alt) => (
          <div
            key={alt.index}
            style={
              selectedIndex === alt.index
                ? readingSelectedStyle
                : readingUnselectedStyle
            }
            onClick={() => onSelect(alt.index)}
          >
            <div style={{ ...readingLabelStyle, color: "var(--rl-warning)" }}>
              Alternate
            </div>
            <div style={{ ...greekTextStyle, color: "var(--rl-text-muted)" }}>
              {alt.surface_text}
            </div>
            <div style={witnessTextStyle}>{alt.witnesses}</div>
            <div style={{ marginTop: "8px" }}>
              {selectedIndex === alt.index ? (
                <span style={{ color: "var(--rl-success)", fontSize: "var(--rl-fs-sm)" }}>
                  Selected
                </span>
              ) : (
                <span style={{ color: "var(--rl-text-dim)", fontSize: "var(--rl-fs-sm)" }}>
                  Click to select
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function Gate({ client }: GateProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const settings = useAppStore(selectSettings);

  // Get gate data from navigation state
  const { gate, originalReference } = (location.state || {}) as {
    gate?: GateResponse;
    originalReference?: string;
  };

  const [selections, setSelections] = useState<VariantSelectionState>(() => {
    // Initialize with default SBLGNT readings (index 0)
    const initial: VariantSelectionState = {};
    if (gate?.variants_side_by_side) {
      for (const v of gate.variants_side_by_side) {
        initial[v.ref] = 0;
      }
    }
    return initial;
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSelect = useCallback((variantRef: string, index: number) => {
    setSelections((prev) => ({
      ...prev,
      [variantRef]: index,
    }));
  }, []);

  // Sprint 7: Multi-ack handler for acknowledging all passage variants at once
  const handleAcknowledgeAll = useCallback(async () => {
    if (!client || !gate) return;

    setLoading(true);
    setError(null);

    try {
      // Build acks list from selections
      const acks = (
        gate.required_acks.length > 0
          ? gate.required_acks
          : gate.variants_side_by_side.filter((v) => v.requires_acknowledgement)
      ).map((item) => {
        const variantRef = "variant_ref" in item ? item.variant_ref : item.ref;
        return {
          variant_ref: variantRef,
          reading_index: selections[variantRef] ?? 0,
        };
      });

      // Use multi-ack endpoint
      await client.acknowledgeMulti({
        session_id: settings.sessionId,
        acks,
        scope: "passage",
      });

      // Re-translate
      const response = await client.translate({
        reference: originalReference || gate.reference,
        mode: "readable",
        session_id: settings.sessionId,
        translator: "literal",
      });

      if (isGateResponse(response)) {
        navigate("/gate", {
          state: {
            gate: response,
            originalReference: originalReference || gate.reference,
          },
          replace: true,
        });
      } else {
        navigate("/translate", { state: { result: response } });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Acknowledgement failed");
    } finally {
      setLoading(false);
    }
  }, [
    client,
    gate,
    selections,
    settings.sessionId,
    originalReference,
    navigate,
  ]);

  const handleAcknowledge = useCallback(async () => {
    if (!client || !gate) return;

    setLoading(true);
    setError(null);

    try {
      // Acknowledge all required variants
      const toAck =
        gate.required_acks.length > 0
          ? gate.required_acks
          : gate.variants_side_by_side.filter(
              (v) => v.requires_acknowledgement,
            );

      for (const item of toAck) {
        const variantRef = "variant_ref" in item ? item.variant_ref : item.ref;
        const readingIndex = selections[variantRef] ?? 0;

        await client.acknowledge({
          session_id: settings.sessionId,
          variant_ref: variantRef,
          reading_index: readingIndex,
        });
      }

      // Re-translate
      const response = await client.translate({
        reference: originalReference || gate.reference,
        mode: "readable",
        session_id: settings.sessionId,
        translator: "literal",
      });

      if (isGateResponse(response)) {
        // Another gate - stay here with new gate data
        navigate("/gate", {
          state: {
            gate: response,
            originalReference: originalReference || gate.reference,
          },
          replace: true,
        });
      } else {
        // Success - go back to translate with result
        navigate("/translate", { state: { result: response } });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Acknowledgement failed");
    } finally {
      setLoading(false);
    }
  }, [
    client,
    gate,
    selections,
    settings.sessionId,
    originalReference,
    navigate,
  ]);

  const handleCancel = useCallback(() => {
    navigate("/translate");
  }, [navigate]);

  // No gate data
  if (!gate) {
    return (
      <div style={containerStyle}>
        <div style={{ color: "var(--rl-error)", padding: "24px" }}>
          No gate data available. Please start a translation first.
        </div>
        <button style={secondaryButtonStyle} onClick={handleCancel}>
          Back to Translate
        </button>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      {/* Warning banner */}
      <div style={warningBannerStyle}>
        <span style={warningIconStyle}>!</span>
        <div>
          <div style={titleStyle}>{gate.title}</div>
          <div style={subtitleStyle}>{gate.message}</div>
        </div>
      </div>

      {/* Reference info */}
      <div style={sectionStyle}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <span style={{ color: "var(--rl-text-muted)", fontSize: "var(--rl-fs-base)" }}>
              Reference:{" "}
            </span>
            <span
              style={{ color: "var(--rl-text)", fontSize: "var(--rl-fs-md)", fontWeight: 500 }}
            >
              {gate.reference}
            </span>
          </div>
          <div>
            <span style={{ color: "var(--rl-text-muted)", fontSize: "var(--rl-fs-base)" }}>
              Variants requiring attention:{" "}
              {gate.required_acks.length ||
                gate.variants_side_by_side.filter(
                  (v) => v.requires_acknowledgement,
                ).length}
            </span>
          </div>
        </div>
      </div>

      {/* Required acknowledgements list */}
      {gate.required_acks.length > 1 && (
        <div style={sectionStyle}>
          <div style={sectionHeaderStyle}>
            Required Acknowledgements ({gate.required_acks.length})
          </div>
          {gate.required_acks.map((ack) => (
            <div key={ack.variant_ref} style={requiredAckStyle}>
              <span style={{ color: "var(--rl-warning)" }}>{ack.variant_ref}</span>
              <span
                style={{
                  fontSize: "var(--rl-fs-xs)",
                  padding: "2px 6px",
                  borderRadius: "3px",
                  backgroundColor:
                    ack.significance === "major"
                      ? "var(--rl-error)"
                      : ack.significance === "significant"
                        ? "var(--rl-warning)"
                        : "var(--rl-border-strong)",
                  color: "white",
                  marginLeft: "8px",
                }}
              >
                {ack.significance}
              </span>
              {/* Sprint 7: Show reason if available */}
              {ack.reason && <span style={reasonBadgeStyle}>{ack.reason}</span>}
              <div
                style={{ color: "var(--rl-text-dim)", marginTop: "4px", fontSize: "var(--rl-fs-sm)" }}
              >
                {ack.message}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Variants side-by-side */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle}>Side-by-Side Variants</div>
        {gate.variants_side_by_side.map((variant) => (
          <VariantCard
            key={variant.ref}
            variant={variant}
            selectedIndex={selections[variant.ref] ?? 0}
            onSelect={(index) => handleSelect(variant.ref, index)}
          />
        ))}
      </div>

      {/* Prompt */}
      <div
        style={{
          color: "var(--rl-text-muted)",
          fontSize: "var(--rl-fs-base)",
          textAlign: "center",
          marginBottom: "16px",
        }}
      >
        {gate.prompt}
      </div>

      {/* Error display */}
      {error && (
        <div
          style={{
            padding: "12px",
            backgroundColor: "#7f1d1d",
            color: "#fca5a5",
            borderRadius: "4px",
            marginBottom: "16px",
            textAlign: "center",
          }}
        >
          {error}
        </div>
      )}

      {/* Action buttons */}
      <div style={buttonRowStyle}>
        <button
          style={secondaryButtonStyle}
          onClick={handleCancel}
          disabled={loading}
        >
          Cancel
        </button>
        {/* Sprint 7: Multi-ack button for passages with multiple variants */}
        {gate.required_acks.length > 1 && (
          <button
            style={
              !client || loading ? disabledButtonStyle : multiAckButtonStyle
            }
            onClick={handleAcknowledgeAll}
            disabled={!client || loading}
            title="Acknowledge all variants for this passage at once"
          >
            {loading
              ? "Processing..."
              : `Ack All (${gate.required_acks.length})`}
          </button>
        )}
        <button
          style={!client || loading ? disabledButtonStyle : primaryButtonStyle}
          onClick={handleAcknowledge}
          disabled={!client || loading}
        >
          {loading ? "Processing..." : "Acknowledge & Continue"}
        </button>
      </div>

      {/* Sprint 8: Dossier Panel for full variant traceability */}
      <DossierPanel
        client={client}
        reference={gate.reference}
        scope="verse"
        sessionId={settings.sessionId}
      />

      {/* Status strip */}
      <div style={statusStripStyle}>
        <span>
          Session:{" "}
          {gate.session_id?.substring(0, 8) ||
            settings.sessionId.substring(0, 8)}
          ...
        </span>
        <span>Gate Type: {gate.gate_type}</span>
        <span>Verses: {gate.verse_ids?.join(", ") || gate.reference}</span>
      </div>
    </div>
  );
}
