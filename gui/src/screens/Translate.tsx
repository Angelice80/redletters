/**
 * Translation screen for Red Letters GUI.
 *
 * Sprint 5: Main translation interface with:
 * - Reference input
 * - Mode selector (readable/traceable)
 * - Translator dropdown (literal/fluent)
 * - Result display with Greek/translation/confidence
 * - Variants expander
 * - Provenance info
 */

import { useState, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAppStore, selectSettings } from "../store";
import { ApiError, detectBackendMismatch } from "../api/client";
import type { ApiClient } from "../api/client";
import type {
  TranslateResponse,
  TranslationMode,
  TranslatorType,
  ConfidenceResult,
  ClaimResult,
  VariantDisplay,
  BackendMismatchInfo,
} from "../api/types";
import { isGateResponse } from "../api/types";
import { LedgerList } from "../components/LedgerPanel";
import { BackendMismatchPanel } from "../components/BackendMismatchPanel";

interface TranslateProps {
  client: ApiClient | null;
}

// Styles
const containerStyle: React.CSSProperties = {
  padding: "24px",
  maxWidth: "900px",
};

const headerStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xl)",
  fontWeight: 600,
  marginBottom: "24px",
  color: "var(--rl-text)",
};

const formRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "12px",
  marginBottom: "16px",
  alignItems: "flex-end",
};

const inputGroupStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "4px",
};

const labelStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-sm)",
  color: "var(--rl-text-muted)",
  textTransform: "uppercase",
};

const inputStyle: React.CSSProperties = {
  padding: "10px 14px",
  fontSize: "var(--rl-fs-md)",
  backgroundColor: "var(--rl-bg-card)",
  border: "1px solid var(--rl-border-strong)",
  borderRadius: "4px",
  color: "var(--rl-text)",
  width: "300px",
};

const selectStyle: React.CSSProperties = {
  ...inputStyle,
  width: "140px",
  cursor: "pointer",
};

const buttonStyle: React.CSSProperties = {
  padding: "10px 20px",
  fontSize: "var(--rl-fs-base)",
  fontWeight: 500,
  backgroundColor: "var(--rl-primary)",
  color: "white",
  border: "none",
  borderRadius: "4px",
  cursor: "pointer",
};

const buttonDisabledStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "var(--rl-border-strong)",
  cursor: "not-allowed",
};

const resultPanelStyle: React.CSSProperties = {
  marginTop: "24px",
  backgroundColor: "var(--rl-bg-card)",
  borderRadius: "8px",
  padding: "20px",
};

const sectionHeaderStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-base)",
  fontWeight: 600,
  color: "var(--rl-text-muted)",
  marginBottom: "8px",
  textTransform: "uppercase",
};

const greekTextStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-lg)",
  fontFamily: "'SBL Greek', 'Cardo', 'Gentium Plus', serif",
  color: "#60a5fa",
  marginBottom: "16px",
  lineHeight: 1.6,
};

const translationTextStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-lg)",
  color: "var(--rl-text)",
  marginBottom: "24px",
  lineHeight: 1.6,
};

const confidenceBarStyle: React.CSSProperties = {
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "4px",
  padding: "16px",
  marginBottom: "16px",
};

const layerRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "12px",
  marginBottom: "8px",
};

const layerLabelStyle: React.CSSProperties = {
  width: "100px",
  fontSize: "var(--rl-fs-base)",
  color: "var(--rl-text-muted)",
};

const barContainerStyle: React.CSSProperties = {
  flex: 1,
  height: "8px",
  backgroundColor: "var(--rl-border-strong)",
  borderRadius: "4px",
  overflow: "hidden",
};

const scoreStyle: React.CSSProperties = {
  width: "50px",
  fontSize: "var(--rl-fs-base)",
  color: "var(--rl-text)",
  textAlign: "right",
};

const expanderStyle: React.CSSProperties = {
  marginTop: "16px",
  borderTop: "1px solid var(--rl-border-strong)",
  paddingTop: "16px",
};

const expanderHeaderStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  cursor: "pointer",
  padding: "8px 0",
};

const claimStyle: React.CSSProperties = {
  padding: "12px",
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "4px",
  marginBottom: "8px",
  fontSize: "var(--rl-fs-base)",
};

const claimTypeStyle: React.CSSProperties = {
  display: "inline-block",
  padding: "2px 6px",
  borderRadius: "3px",
  fontSize: "var(--rl-fs-xs)",
  fontWeight: 600,
  marginRight: "8px",
};

const variantStyle: React.CSSProperties = {
  padding: "12px",
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "4px",
  marginBottom: "8px",
};

const statusStripStyle: React.CSSProperties = {
  display: "flex",
  gap: "16px",
  marginTop: "16px",
  padding: "12px",
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "4px",
  fontSize: "var(--rl-fs-sm)",
  color: "var(--rl-text-dim)",
};

function ConfidenceBar({ confidence }: { confidence: ConfidenceResult }) {
  const getBarColor = (score: number) => {
    if (score >= 0.8) return "var(--rl-success)";
    if (score >= 0.6) return "var(--rl-warning)";
    return "var(--rl-error)";
  };

  return (
    <div style={confidenceBarStyle}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: "12px",
        }}
      >
        <span style={{ color: "var(--rl-text)", fontWeight: 500 }}>
          Confidence: {(confidence.composite * 100).toFixed(0)}%
        </span>
        <span style={{ color: "var(--rl-text-muted)", fontSize: "var(--rl-fs-sm)" }}>
          Weakest: {confidence.weakest_layer}
        </span>
      </div>

      {(["textual", "grammatical", "lexical", "interpretive"] as const).map(
        (layer) => (
          <div key={layer} style={layerRowStyle}>
            <span style={layerLabelStyle}>
              {layer.charAt(0).toUpperCase() + layer.slice(1)}:
            </span>
            <div style={barContainerStyle}>
              <div
                style={{
                  width: `${confidence.layers[layer].score * 100}%`,
                  height: "100%",
                  backgroundColor: getBarColor(confidence.layers[layer].score),
                  borderRadius: "4px",
                  transition: "width 0.3s ease",
                }}
              />
            </div>
            <span style={scoreStyle}>
              {(confidence.layers[layer].score * 100).toFixed(0)}%
            </span>
          </div>
        ),
      )}
    </div>
  );
}

function ClaimsList({ claims }: { claims: ClaimResult[] }) {
  const getTypeColor = (claimType: number) => {
    if (claimType <= 1) return "var(--rl-success)"; // TYPE0-1: Green
    if (claimType <= 3) return "var(--rl-warning)"; // TYPE2-3: Yellow
    return "var(--rl-error)"; // TYPE4+: Red
  };

  return (
    <div>
      {claims.map((claim, i) => (
        <div key={i} style={claimStyle}>
          <span
            style={{
              ...claimTypeStyle,
              backgroundColor: getTypeColor(claim.claim_type),
              color: "var(--rl-bg-app)",
            }}
          >
            {claim.claim_type_label}
          </span>
          <span
            style={{ color: claim.enforcement_allowed ? "var(--rl-text)" : "var(--rl-error)" }}
          >
            {claim.content}
          </span>
          {claim.warnings.length > 0 && (
            <div
              style={{ marginTop: "6px", color: "var(--rl-warning)", fontSize: "var(--rl-fs-sm)" }}
            >
              {claim.warnings.join("; ")}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function VariantsList({ variants }: { variants: VariantDisplay[] }) {
  if (variants.length === 0) {
    return (
      <div style={{ color: "var(--rl-text-dim)", fontSize: "var(--rl-fs-base)" }}>
        No variants at this passage.
      </div>
    );
  }

  return (
    <div>
      {variants.map((v) => (
        <div key={v.ref} style={variantStyle}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: "8px",
            }}
          >
            <span style={{ color: "#60a5fa", fontWeight: 500 }}>{v.ref}</span>
            <span
              style={{
                fontSize: "var(--rl-fs-xs)",
                padding: "2px 6px",
                borderRadius: "3px",
                backgroundColor:
                  v.significance === "major"
                    ? "var(--rl-error)"
                    : v.significance === "significant"
                      ? "var(--rl-warning)"
                      : "var(--rl-border-strong)",
                color: "white",
              }}
            >
              {v.significance}
            </span>
          </div>
          <div style={{ marginBottom: "8px" }}>
            <span style={{ color: "var(--rl-success)", fontWeight: 500 }}>SBLGNT: </span>
            <span
              style={{ fontFamily: "'SBL Greek', serif", color: "var(--rl-text)" }}
            >
              {v.sblgnt_reading}
            </span>
            <span
              style={{ color: "var(--rl-text-dim)", fontSize: "var(--rl-fs-sm)", marginLeft: "8px" }}
            >
              ({v.sblgnt_witnesses})
            </span>
          </div>
          {v.alternate_readings.map((alt) => (
            <div
              key={alt.index}
              style={{ marginLeft: "16px", marginBottom: "4px" }}
            >
              <span style={{ color: "var(--rl-warning)" }}>Alt: </span>
              <span
                style={{ fontFamily: "'SBL Greek', serif", color: "var(--rl-text-muted)" }}
              >
                {alt.surface_text}
              </span>
              <span
                style={{
                  color: "var(--rl-text-dim)",
                  fontSize: "var(--rl-fs-sm)",
                  marginLeft: "8px",
                }}
              >
                ({alt.witnesses})
              </span>
            </div>
          ))}
          {v.acknowledged && (
            <div
              style={{ color: "var(--rl-success)", fontSize: "var(--rl-fs-sm)", marginTop: "8px" }}
            >
              Acknowledged
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export function Translate({ client }: TranslateProps) {
  const navigate = useNavigate();
  const settings = useAppStore(selectSettings);

  const [reference, setReference] = useState("");
  const [mode, setMode] = useState<TranslationMode>("readable");
  const [translator, setTranslator] = useState<TranslatorType>("literal");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TranslateResponse | null>(null);

  // Sprint 19: Backend mismatch detection
  const [mismatch, setMismatch] = useState<BackendMismatchInfo | null>(null);

  const [showClaims, setShowClaims] = useState(false);
  const [showVariants, setShowVariants] = useState(false);
  const [showLedger, setShowLedger] = useState(false);

  const handleTranslate = useCallback(async () => {
    if (!client || !reference.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setMismatch(null);

    try {
      const response = await client.translate({
        reference: reference.trim(),
        mode,
        session_id: settings.sessionId,
        translator,
      });

      if (isGateResponse(response)) {
        // Navigate to gate screen with gate data
        navigate("/gate", {
          state: { gate: response, originalReference: reference.trim() },
        });
      } else {
        setResult(response);
      }
    } catch (err) {
      // Sprint 19: Check for backend mismatch on 404
      if (err instanceof ApiError && err.status === 404) {
        const mismatchInfo = await detectBackendMismatch(
          client.baseUrl,
          client.token,
          "/translate",
        );
        if (mismatchInfo.detected) {
          setMismatch(mismatchInfo);
          return;
        }
      }
      setError(err instanceof Error ? err.message : "Translation failed");
    } finally {
      setLoading(false);
    }
  }, [client, reference, mode, translator, settings.sessionId, navigate]);

  const handleKeyPress = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !loading && reference.trim()) {
        handleTranslate();
      }
    },
    [handleTranslate, loading, reference],
  );

  return (
    <div style={containerStyle}>
      <h1 style={headerStyle}>Explore</h1>

      {/* Input form */}
      <div style={formRowStyle}>
        <div style={inputGroupStyle}>
          <label style={labelStyle}>Reference</label>
          <input
            type="text"
            style={inputStyle}
            placeholder="e.g., John 1:18 or John 1:18-19"
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            onKeyPress={handleKeyPress}
          />
        </div>

        <div style={inputGroupStyle}>
          <label style={labelStyle}>Mode</label>
          <select
            style={selectStyle}
            value={mode}
            onChange={(e) => setMode(e.target.value as TranslationMode)}
          >
            <option value="readable">Readable</option>
            <option value="traceable">Traceable</option>
          </select>
        </div>

        <div style={inputGroupStyle}>
          <label style={labelStyle}>Translator</label>
          <select
            style={selectStyle}
            value={translator}
            onChange={(e) => setTranslator(e.target.value as TranslatorType)}
          >
            <option value="literal">Literal</option>
            <option value="fluent">Fluent</option>
            <option value="traceable">Traceable</option>
            <option value="fake">Test Data</option>
          </select>
        </div>

        <button
          style={
            !client || loading || !reference.trim()
              ? buttonDisabledStyle
              : buttonStyle
          }
          onClick={handleTranslate}
          disabled={!client || loading || !reference.trim()}
        >
          {loading ? "Translating..." : "Translate"}
        </button>
      </div>

      {/* Sprint 19: Backend mismatch display */}
      {mismatch && (
        <BackendMismatchPanel
          mismatchInfo={mismatch}
          onRetry={handleTranslate}
          onDismiss={() => setMismatch(null)}
        />
      )}

      {/* Error display */}
      {error && !mismatch && (
        <div
          style={{
            padding: "12px",
            backgroundColor: "#7f1d1d",
            color: "#fca5a5",
            borderRadius: "4px",
            marginBottom: "16px",
          }}
        >
          <div>{error}</div>
          {/* CTA for spine-missing error */}
          {(error.toLowerCase().includes("spine") ||
            error.toLowerCase().includes("morphgnt-sblgnt") ||
            error.toLowerCase().includes("no tokens found")) && (
            <div style={{ marginTop: "12px" }}>
              <span style={{ fontSize: "var(--rl-fs-base)" }}>
                The canonical spine source may not be installed.{" "}
              </span>
              <Link
                to="/sources"
                style={{
                  color: "#60a5fa",
                  textDecoration: "underline",
                  fontSize: "var(--rl-fs-base)",
                }}
              >
                Go to Sources to install it
              </Link>
            </div>
          )}
        </div>
      )}

      {/* Result display */}
      {result && (
        <div style={resultPanelStyle}>
          {/* Greek text */}
          <div>
            <div style={sectionHeaderStyle}>Greek (SBLGNT)</div>
            <div style={greekTextStyle}>{result.sblgnt_text}</div>
          </div>

          {/* Translation */}
          <div>
            <div style={sectionHeaderStyle}>Translation</div>
            <div style={translationTextStyle}>{result.translation_text}</div>
          </div>

          {/* Confidence */}
          {result.confidence && (
            <ConfidenceBar confidence={result.confidence} />
          )}

          {/* Claims expander */}
          <div style={expanderStyle}>
            <div
              style={expanderHeaderStyle}
              onClick={() => setShowClaims(!showClaims)}
            >
              <span style={{ color: "var(--rl-text-muted)", fontSize: "var(--rl-fs-base)" }}>
                Claims ({result.claims.length})
              </span>
              <span style={{ color: "var(--rl-text-dim)" }}>{showClaims ? "−" : "+"}</span>
            </div>
            {showClaims && <ClaimsList claims={result.claims} />}
          </div>

          {/* Variants expander */}
          <div style={expanderStyle}>
            <div
              style={expanderHeaderStyle}
              onClick={() => setShowVariants(!showVariants)}
            >
              <span style={{ color: "var(--rl-text-muted)", fontSize: "var(--rl-fs-base)" }}>
                Variants ({result.variants.length})
              </span>
              <span style={{ color: "var(--rl-text-dim)" }}>
                {showVariants ? "−" : "+"}
              </span>
            </div>
            {showVariants && <VariantsList variants={result.variants} />}
          </div>

          {/* Ledger expander (traceable mode only) */}
          {result.mode === "traceable" &&
            result.ledger &&
            result.ledger.length > 0 && (
              <div style={expanderStyle}>
                <div
                  style={expanderHeaderStyle}
                  onClick={() => setShowLedger(!showLedger)}
                >
                  <span
                    style={{
                      color: "#60a5fa",
                      fontSize: "var(--rl-fs-base)",
                      fontWeight: 500,
                    }}
                  >
                    Token Ledger (
                    {result.ledger.reduce((sum, v) => sum + v.tokens.length, 0)}{" "}
                    tokens)
                  </span>
                  <span style={{ color: "var(--rl-text-dim)" }}>
                    {showLedger ? "−" : "+"}
                  </span>
                </div>
                {showLedger && <LedgerList ledgers={result.ledger} />}
              </div>
            )}

          {/* Provenance */}
          <div
            style={{ ...expanderStyle, borderTop: "none", paddingTop: "8px" }}
          >
            <div style={{ fontSize: "var(--rl-fs-sm)", color: "var(--rl-text-dim)" }}>
              Provenance: {result.provenance.spine_source} | Sources:{" "}
              {result.provenance.sources_used.join(", ")}
            </div>
          </div>

          {/* Status strip */}
          <div style={statusStripStyle}>
            <span>Session: {result.session_id.substring(0, 8)}...</span>
            <span>Translator: {result.translator_type}</span>
            <span>Mode: {result.mode}</span>
            <span>Verses: {result.verse_ids.join(", ")}</span>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!result && !error && !loading && (
        <div
          style={{
            textAlign: "center",
            padding: "48px",
            color: "var(--rl-text-dim)",
          }}
        >
          Enter a scripture reference above to translate.
        </div>
      )}
    </div>
  );
}
