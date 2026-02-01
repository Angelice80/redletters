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
import type { GateResponse, VariantDisplay, RequiredAck } from "../api/types";
import { isGateResponse } from "../api/types";

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
  fontSize: "24px",
};

const titleStyle: React.CSSProperties = {
  fontSize: "20px",
  fontWeight: 600,
  color: "#fef9c3",
};

const subtitleStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#fde68a",
  marginTop: "4px",
};

const sectionStyle: React.CSSProperties = {
  backgroundColor: "#2d2d44",
  borderRadius: "8px",
  padding: "20px",
  marginBottom: "16px",
};

const sectionHeaderStyle: React.CSSProperties = {
  fontSize: "14px",
  fontWeight: 600,
  color: "#9ca3af",
  marginBottom: "16px",
  textTransform: "uppercase",
};

const variantCardStyle: React.CSSProperties = {
  backgroundColor: "#1a1a2e",
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
  border: "2px solid #3b82f6",
};

const readingUnselectedStyle: React.CSSProperties = {
  ...readingCardStyle,
  backgroundColor: "#1a1a2e",
  border: "2px solid #4b5563",
};

const readingLabelStyle: React.CSSProperties = {
  fontSize: "11px",
  fontWeight: 600,
  textTransform: "uppercase",
  marginBottom: "8px",
};

const greekTextStyle: React.CSSProperties = {
  fontSize: "18px",
  fontFamily: "'SBL Greek', 'Cardo', 'Gentium Plus', serif",
  marginBottom: "8px",
};

const witnessTextStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#6b7280",
};

const buttonRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "center",
  gap: "16px",
  marginTop: "24px",
};

const primaryButtonStyle: React.CSSProperties = {
  padding: "12px 32px",
  fontSize: "16px",
  fontWeight: 500,
  backgroundColor: "#22c55e",
  color: "white",
  border: "none",
  borderRadius: "6px",
  cursor: "pointer",
};

const secondaryButtonStyle: React.CSSProperties = {
  padding: "12px 24px",
  fontSize: "14px",
  fontWeight: 500,
  backgroundColor: "#4b5563",
  color: "#eaeaea",
  border: "none",
  borderRadius: "6px",
  cursor: "pointer",
};

const disabledButtonStyle: React.CSSProperties = {
  ...primaryButtonStyle,
  backgroundColor: "#374151",
  cursor: "not-allowed",
};

const statusStripStyle: React.CSSProperties = {
  display: "flex",
  gap: "16px",
  marginTop: "24px",
  padding: "12px",
  backgroundColor: "#1a1a2e",
  borderRadius: "4px",
  fontSize: "12px",
  color: "#6b7280",
};

const requiredAckStyle: React.CSSProperties = {
  padding: "8px 12px",
  backgroundColor: "#1a1a2e",
  borderRadius: "4px",
  marginBottom: "8px",
  fontSize: "13px",
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
        <span style={{ color: "#60a5fa", fontWeight: 500, fontSize: "16px" }}>
          {variant.ref}
        </span>
        <span
          style={{
            fontSize: "11px",
            padding: "4px 8px",
            borderRadius: "4px",
            backgroundColor:
              variant.significance === "major"
                ? "#ef4444"
                : variant.significance === "significant"
                  ? "#f59e0b"
                  : "#4b5563",
            color: "white",
          }}
        >
          {variant.significance}
        </span>
      </div>

      <div style={{ color: "#9ca3af", fontSize: "13px", marginBottom: "12px" }}>
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
          <div style={{ ...readingLabelStyle, color: "#22c55e" }}>
            SBLGNT [default]
          </div>
          <div style={{ ...greekTextStyle, color: "#eaeaea" }}>
            {variant.sblgnt_reading}
          </div>
          <div style={witnessTextStyle}>{variant.sblgnt_witnesses}</div>
          <div style={{ marginTop: "8px" }}>
            {selectedIndex === 0 ? (
              <span style={{ color: "#22c55e", fontSize: "12px" }}>
                Selected
              </span>
            ) : (
              <span style={{ color: "#6b7280", fontSize: "12px" }}>
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
            <div style={{ ...readingLabelStyle, color: "#f59e0b" }}>
              Alternate
            </div>
            <div style={{ ...greekTextStyle, color: "#9ca3af" }}>
              {alt.surface_text}
            </div>
            <div style={witnessTextStyle}>{alt.witnesses}</div>
            <div style={{ marginTop: "8px" }}>
              {selectedIndex === alt.index ? (
                <span style={{ color: "#22c55e", fontSize: "12px" }}>
                  Selected
                </span>
              ) : (
                <span style={{ color: "#6b7280", fontSize: "12px" }}>
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
        <div style={{ color: "#ef4444", padding: "24px" }}>
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
            <span style={{ color: "#9ca3af", fontSize: "13px" }}>
              Reference:{" "}
            </span>
            <span
              style={{ color: "#eaeaea", fontSize: "16px", fontWeight: 500 }}
            >
              {gate.reference}
            </span>
          </div>
          <div>
            <span style={{ color: "#9ca3af", fontSize: "13px" }}>
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
          <div style={sectionHeaderStyle}>Required Acknowledgements</div>
          {gate.required_acks.map((ack) => (
            <div key={ack.variant_ref} style={requiredAckStyle}>
              <span style={{ color: "#f59e0b" }}>{ack.variant_ref}</span>
              <span style={{ color: "#6b7280", marginLeft: "12px" }}>
                {ack.message}
              </span>
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
          color: "#9ca3af",
          fontSize: "14px",
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
        <button
          style={!client || loading ? disabledButtonStyle : primaryButtonStyle}
          onClick={handleAcknowledge}
          disabled={!client || loading}
        >
          {loading ? "Processing..." : "Acknowledge & Continue"}
        </button>
      </div>

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
