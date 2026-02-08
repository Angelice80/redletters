/**
 * CompareModal — side-by-side translation comparison.
 *
 * Sprint 24 (S7): Choose A/B translator + mode, run compare, show side-by-side.
 * UX2.3: Swap A/B button, sticky result labels.
 */

import { useState, useCallback } from "react";
import type { ApiClient } from "../api/client";
import type {
  TranslateResponse,
  TranslationMode,
  TranslatorType,
} from "../api/types";
import { isGateResponse } from "../api/types";

interface CompareModalProps {
  /** API client for translation requests */
  client: ApiClient;
  /** Current reference being viewed */
  reference: string;
  /** Current session ID */
  sessionId: string;
  /** The "A" result (already loaded) */
  resultA: TranslateResponse;
  /** Close the modal */
  onClose: () => void;
}

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  backgroundColor: "rgba(0, 0, 0, 0.6)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 2000,
};

const modalStyle: React.CSSProperties = {
  backgroundColor: "var(--rl-bg-card)",
  borderRadius: "12px",
  padding: "24px",
  width: "90vw",
  maxWidth: "900px",
  maxHeight: "80vh",
  overflow: "auto",
  boxShadow: "0 8px 32px rgba(0, 0, 0, 0.5)",
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "20px",
};

const titleStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-md)",
  fontWeight: 600,
  color: "var(--rl-text)",
};

const closeBtn: React.CSSProperties = {
  background: "none",
  border: "none",
  color: "var(--rl-text-muted)",
  fontSize: "var(--rl-fs-lg)",
  cursor: "pointer",
  padding: "4px 8px",
};

const configRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "12px",
  marginBottom: "20px",
  alignItems: "center",
};

const configColStyle: React.CSSProperties = {
  flex: 1,
  padding: "12px",
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "8px",
};

const labelStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xs)",
  color: "var(--rl-text-muted)",
  textTransform: "uppercase" as const,
  marginBottom: "6px",
  display: "block",
};

const selectStyle: React.CSSProperties = {
  padding: "6px 10px",
  fontSize: "var(--rl-fs-base)",
  backgroundColor: "var(--rl-bg-card)",
  border: "1px solid var(--rl-border-strong)",
  borderRadius: "4px",
  color: "var(--rl-text)",
  width: "100%",
  marginBottom: "8px",
};

const runBtnStyle: React.CSSProperties = {
  padding: "10px 24px",
  fontSize: "var(--rl-fs-base)",
  fontWeight: 500,
  backgroundColor: "var(--rl-primary)",
  color: "white",
  border: "none",
  borderRadius: "6px",
  cursor: "pointer",
  width: "100%",
  marginBottom: "20px",
};

const disabledBtnStyle: React.CSSProperties = {
  ...runBtnStyle,
  backgroundColor: "var(--rl-border-strong)",
  cursor: "not-allowed",
};

const resultsPaneStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "16px",
};

const resultCardStyle: React.CSSProperties = {
  padding: "16px",
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "8px",
};

const resultLabelStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xs)",
  fontWeight: 600,
  color: "var(--rl-text-muted)",
  textTransform: "uppercase" as const,
  marginBottom: "8px",
  position: "sticky" as const,
  top: 0,
  backgroundColor: "var(--rl-bg-app)",
  padding: "4px 0",
  zIndex: 1,
};

const resultTextStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-base)",
  color: "var(--rl-text)",
  lineHeight: 1.7,
};

const chipStyle: React.CSSProperties = {
  display: "inline-block",
  padding: "2px 8px",
  borderRadius: "3px",
  fontSize: "var(--rl-fs-xs)",
  fontWeight: 600,
  backgroundColor: "var(--rl-border-strong)",
  color: "var(--rl-text-muted)",
  marginRight: "6px",
};

const swapBtnStyle: React.CSSProperties = {
  padding: "6px 10px",
  fontSize: "var(--rl-fs-base)",
  backgroundColor: "var(--rl-border-strong)",
  color: "var(--rl-text-muted)",
  border: "1px solid var(--rl-border-strong)",
  borderRadius: "4px",
  cursor: "pointer",
  flexShrink: 0,
};

const errorStyle: React.CSSProperties = {
  padding: "12px",
  backgroundColor: "#7f1d1d",
  color: "#fca5a5",
  borderRadius: "4px",
  fontSize: "var(--rl-fs-base)",
  marginBottom: "16px",
};

export function CompareModal({
  client,
  reference,
  sessionId,
  resultA,
  onClose,
}: CompareModalProps) {
  const [translatorB, setTranslatorB] = useState<TranslatorType>(
    resultA.translator_type === "literal" ? "fluent" : "literal",
  );
  const [modeB, setModeB] = useState<TranslationMode>(resultA.mode);
  const [resultB, setResultB] = useState<TranslateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // UX2.3: Track whether results have been swapped
  const [swapped, setSwapped] = useState(false);

  const handleRunCompare = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResultB(null);
    setSwapped(false);

    try {
      const response = await client.translate({
        reference,
        mode: modeB,
        session_id: sessionId,
        translator: translatorB,
      });

      if (isGateResponse(response)) {
        setError(
          "Gate triggered: variant acknowledgement required before comparing with these settings.",
        );
      } else {
        setResultB(response);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to run comparison.",
      );
    } finally {
      setLoading(false);
    }
  }, [client, reference, modeB, sessionId, translatorB]);

  // UX2.3: Swap A/B results
  const handleSwap = useCallback(() => {
    setSwapped((prev) => !prev);
  }, []);

  // Determine which result shows on which side
  const displayA = swapped ? resultB : resultA;
  const displayB = swapped ? resultA : resultB;

  return (
    <div style={overlayStyle} onClick={onClose} data-testid="compare-modal">
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <div style={headerStyle}>
          <span style={titleStyle}>Compare Renderings — {reference}</span>
          <button style={closeBtn} onClick={onClose} aria-label="Close compare">
            x
          </button>
        </div>

        {/* Config row with swap button */}
        <div style={configRowStyle}>
          {/* A side (current result) */}
          <div style={configColStyle}>
            <span style={labelStyle}>A — Current</span>
            <div style={{ fontSize: "var(--rl-fs-base)", color: "var(--rl-text)" }}>
              <span style={chipStyle}>{resultA.translator_type}</span>
              <span style={chipStyle}>{resultA.mode}</span>
            </div>
          </div>

          {/* UX2.3: Swap button */}
          {resultB && (
            <button
              data-testid="compare-swap-btn"
              style={swapBtnStyle}
              onClick={handleSwap}
              title="Swap A and B"
            >
              &#8644;
            </button>
          )}

          {/* B side (configurable) */}
          <div style={configColStyle}>
            <span style={labelStyle}>B — Compare with</span>
            <label style={labelStyle}>Translator</label>
            <select
              style={selectStyle}
              value={translatorB}
              onChange={(e) => setTranslatorB(e.target.value as TranslatorType)}
              data-testid="compare-translator-b"
            >
              <option value="literal">Literal</option>
              <option value="fluent">Fluent</option>
              <option value="traceable">Traceable</option>
            </select>
            <label style={labelStyle}>Mode</label>
            <select
              style={selectStyle}
              value={modeB}
              onChange={(e) => setModeB(e.target.value as TranslationMode)}
              data-testid="compare-mode-b"
            >
              <option value="readable">Readable</option>
              <option value="traceable">Traceable</option>
            </select>
          </div>
        </div>

        {/* Run button */}
        <button
          style={loading ? disabledBtnStyle : runBtnStyle}
          onClick={handleRunCompare}
          disabled={loading}
          data-testid="compare-run-btn"
        >
          {loading ? "Translating B..." : "Run Comparison"}
        </button>

        {error && <div style={errorStyle}>{error}</div>}

        {/* Results */}
        {resultB && displayA && displayB && (
          <div style={resultsPaneStyle} data-testid="compare-results">
            <div style={resultCardStyle}>
              <div style={resultLabelStyle} data-testid="compare-label-a">
                A — {displayA.translator_type} / {displayA.mode}
              </div>
              <div style={resultTextStyle}>{displayA.translation_text}</div>
            </div>
            <div style={resultCardStyle}>
              <div style={resultLabelStyle} data-testid="compare-label-b">
                B — {displayB.translator_type} / {displayB.mode}
              </div>
              <div style={resultTextStyle}>{displayB.translation_text}</div>
            </div>
          </div>
        )}

        {!resultB && !loading && !error && (
          <div
            style={{
              textAlign: "center",
              color: "var(--rl-text-dim)",
              fontSize: "var(--rl-fs-base)",
              padding: "24px",
            }}
          >
            Choose settings for B and click "Run Comparison" to see results
            side-by-side.
          </div>
        )}
      </div>
    </div>
  );
}
