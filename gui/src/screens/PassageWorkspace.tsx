/**
 * Passage Workspace - the main exploration hub.
 *
 * Sprint 15 (B6): 3-column layout with:
 * - Left: Greek text panel
 * - Center: Rendering cards with interactive tokens
 * - Right: Inspector tabs (Receipts | Variants)
 *
 * Features:
 * - Progressive disclosure receipts (B7)
 * - Compare toggle for diff highlighting (B9)
 * - Confidence heatmap toggle (B10)
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAppStore, selectSettings } from "../store";

// Sprint 17: Example references for quick access
const EXAMPLE_REFS = ["John 1:1", "Matt 5:3-12", "Mark 1:15", "Rom 8:28"];
const RECENT_REFS_KEY = "redletters_recent_refs";
const MAX_RECENT_REFS = 5;
import type { ApiClient } from "../api/client";
import type {
  TranslateResponse,
  TranslationMode,
  TranslatorType,
  TokenLedger,
  VerseLedger,
  ApiErrorDetail,
} from "../api/types";
import { isGateResponse } from "../api/types";
import {
  ApiErrorPanel,
  createApiErrorDetail,
} from "../components/ApiErrorPanel";
import { LedgerList } from "../components/LedgerPanel";
import { DossierPanel } from "../components/DossierPanel";
import { TokenReceiptPopover } from "../components/TokenReceiptPopover";
import {
  computeDiff,
  getChangeTypeHighlight,
  getChangeTypeColor,
  type ChangeType,
} from "../utils/renderingDiff";
import {
  getHeatmapStyles,
  HEATMAP_LEGEND,
  computeTokenRisk,
} from "../utils/heatmapUtils";

interface PassageWorkspaceProps {
  client: ApiClient | null;
}

// Styles
const containerStyle: React.CSSProperties = {
  padding: "16px",
  height: "100%",
  display: "flex",
  flexDirection: "column",
  overflow: "hidden",
};

const toolbarStyle: React.CSSProperties = {
  display: "flex",
  gap: "12px",
  alignItems: "center",
  marginBottom: "16px",
  flexWrap: "wrap",
};

const inputGroupStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "4px",
};

const labelStyle: React.CSSProperties = {
  fontSize: "11px",
  color: "#9ca3af",
  textTransform: "uppercase",
};

const inputStyle: React.CSSProperties = {
  padding: "8px 12px",
  fontSize: "14px",
  backgroundColor: "#2d2d44",
  border: "1px solid #4b5563",
  borderRadius: "4px",
  color: "#eaeaea",
  width: "220px",
};

const selectStyle: React.CSSProperties = {
  ...inputStyle,
  width: "120px",
  cursor: "pointer",
};

const buttonStyle: React.CSSProperties = {
  padding: "8px 16px",
  fontSize: "13px",
  fontWeight: 500,
  backgroundColor: "#3b82f6",
  color: "white",
  border: "none",
  borderRadius: "4px",
  cursor: "pointer",
};

const toggleButtonStyle: React.CSSProperties = {
  padding: "6px 12px",
  fontSize: "12px",
  backgroundColor: "#374151",
  color: "#9ca3af",
  border: "1px solid #4b5563",
  borderRadius: "4px",
  cursor: "pointer",
};

const toggleActiveStyle: React.CSSProperties = {
  ...toggleButtonStyle,
  backgroundColor: "#3b82f6",
  color: "white",
  borderColor: "#3b82f6",
};

const workspaceStyle: React.CSSProperties = {
  flex: 1,
  display: "grid",
  gridTemplateColumns: "1fr 2fr 1fr",
  gap: "16px",
  overflow: "hidden",
  minHeight: 0,
};

const panelStyle: React.CSSProperties = {
  backgroundColor: "#2d2d44",
  borderRadius: "8px",
  overflow: "hidden",
  display: "flex",
  flexDirection: "column",
};

const panelHeaderStyle: React.CSSProperties = {
  padding: "12px 16px",
  borderBottom: "1px solid #4b5563",
  fontSize: "12px",
  fontWeight: 600,
  color: "#9ca3af",
  textTransform: "uppercase",
};

const panelContentStyle: React.CSSProperties = {
  flex: 1,
  overflow: "auto",
  padding: "16px",
};

const greekTextStyle: React.CSSProperties = {
  fontSize: "18px",
  fontFamily: "'SBL Greek', 'Cardo', 'Gentium Plus', serif",
  color: "#60a5fa",
  lineHeight: 1.8,
};

const renderingCardStyle: React.CSSProperties = {
  backgroundColor: "#1a1a2e",
  borderRadius: "6px",
  padding: "16px",
  marginBottom: "12px",
};

const styleChipStyle: React.CSSProperties = {
  display: "inline-block",
  padding: "2px 8px",
  borderRadius: "3px",
  fontSize: "10px",
  fontWeight: 600,
  backgroundColor: "#374151",
  color: "#9ca3af",
  marginRight: "8px",
};

const tabBarStyle: React.CSSProperties = {
  display: "flex",
  borderBottom: "1px solid #4b5563",
};

const tabStyle: React.CSSProperties = {
  padding: "12px 16px",
  fontSize: "12px",
  fontWeight: 500,
  color: "#9ca3af",
  cursor: "pointer",
  borderBottom: "2px solid transparent",
  marginBottom: "-1px",
};

const tabActiveStyle: React.CSSProperties = {
  ...tabStyle,
  color: "#60a5fa",
  borderBottomColor: "#60a5fa",
};

const legendStyle: React.CSSProperties = {
  display: "flex",
  gap: "16px",
  padding: "8px 16px",
  backgroundColor: "#1a1a2e",
  borderRadius: "4px",
  fontSize: "11px",
  color: "#9ca3af",
};

const legendItemStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "6px",
};

const errorStyle: React.CSSProperties = {
  padding: "12px",
  backgroundColor: "#7f1d1d",
  color: "#fca5a5",
  borderRadius: "4px",
  marginBottom: "12px",
};

const emptyStateStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  height: "100%",
  color: "#6b7280",
  textAlign: "center",
  padding: "24px",
};

// Sprint 17: Additional styles for usability improvements
const exampleChipsStyle: React.CSSProperties = {
  display: "flex",
  gap: "8px",
  flexWrap: "wrap",
  marginTop: "16px",
};

const chipStyle: React.CSSProperties = {
  padding: "6px 12px",
  backgroundColor: "#374151",
  color: "#9ca3af",
  borderRadius: "16px",
  fontSize: "12px",
  cursor: "pointer",
  border: "1px solid #4b5563",
  transition: "all 0.15s",
};

const recentDropdownStyle: React.CSSProperties = {
  position: "absolute",
  top: "100%",
  left: 0,
  right: 0,
  backgroundColor: "#2d2d44",
  border: "1px solid #4b5563",
  borderRadius: "4px",
  marginTop: "4px",
  zIndex: 10,
  maxHeight: "200px",
  overflow: "auto",
};

const recentItemStyle: React.CSSProperties = {
  padding: "8px 12px",
  fontSize: "13px",
  color: "#eaeaea",
  cursor: "pointer",
  borderBottom: "1px solid #374151",
};

const loadingOverlayStyle: React.CSSProperties = {
  position: "absolute",
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: "rgba(26, 26, 46, 0.8)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  borderRadius: "8px",
};

const disabledToggleStyle: React.CSSProperties = {
  padding: "6px 12px",
  fontSize: "12px",
  backgroundColor: "#2d2d44",
  color: "#4b5563",
  border: "1px solid #374151",
  borderRadius: "4px",
  cursor: "not-allowed",
  opacity: 0.5,
};

// Interactive token component
interface InteractiveTokenProps {
  token: TokenLedger;
  isCompareMode: boolean;
  changeType?: ChangeType;
  isHeatmapMode: boolean;
  onClick: (token: TokenLedger, element: HTMLElement) => void;
}

function InteractiveToken({
  token,
  isCompareMode,
  changeType,
  isHeatmapMode,
  onClick,
}: InteractiveTokenProps) {
  const ref = useRef<HTMLSpanElement>(null);

  let style: React.CSSProperties = {
    cursor: "pointer",
    padding: "2px 4px",
    borderRadius: "3px",
    transition: "background-color 0.15s",
  };

  // Apply compare highlighting
  if (isCompareMode && changeType && changeType !== "none") {
    style.backgroundColor = getChangeTypeHighlight(changeType, 0.3);
  }

  // Apply heatmap highlighting (can combine with compare)
  if (isHeatmapMode) {
    const heatmapStyles = getHeatmapStyles(token.confidence, "underline");
    style = { ...style, ...heatmapStyles };
  }

  const handleClick = () => {
    if (ref.current) {
      onClick(token, ref.current);
    }
  };

  return (
    <span
      ref={ref}
      style={style}
      onClick={handleClick}
      title={`${token.gloss} (click for details)`}
    >
      {token.gloss}
    </span>
  );
}

// Confidence summary component
function ConfidenceSummary({ tokens }: { tokens: TokenLedger[] }) {
  if (tokens.length === 0) return null;

  const avgRisk =
    tokens.reduce((sum, t) => sum + computeTokenRisk(t.confidence), 0) /
    tokens.length;

  const riskColor =
    avgRisk < 0.2
      ? "#22c55e"
      : avgRisk < 0.4
        ? "#fde68a"
        : avgRisk < 0.6
          ? "#f59e0b"
          : "#ef4444";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        marginTop: "8px",
        fontSize: "11px",
        color: "#9ca3af",
      }}
    >
      <span>Avg Risk:</span>
      <span style={{ color: riskColor, fontWeight: 500 }}>
        {(avgRisk * 100).toFixed(0)}%
      </span>
      <span>({tokens.length} tokens)</span>
    </div>
  );
}

export function PassageWorkspace({ client }: PassageWorkspaceProps) {
  const navigate = useNavigate();
  const settings = useAppStore(selectSettings);

  // Form state
  const [reference, setReference] = useState("");
  const [mode, setMode] = useState<TranslationMode>("traceable");
  const [translator, setTranslator] = useState<TranslatorType>("literal");

  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiErrorDetail | null>(null);
  const [result, setResult] = useState<TranslateResponse | null>(null);

  // Feature toggles
  const [compareMode, setCompareMode] = useState(false);
  const [heatmapMode, setHeatmapMode] = useState(false);
  const [baseRenderingIndex] = useState(0);

  // Sprint 17: Recent references
  const [recentRefs, setRecentRefs] = useState<string[]>([]);
  const [showRecentDropdown, setShowRecentDropdown] = useState(false);

  // Load recent refs from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(RECENT_REFS_KEY);
      if (stored) {
        setRecentRefs(JSON.parse(stored));
      }
    } catch {
      // Ignore parse errors
    }
  }, []);

  // Save a reference to recent history
  const saveToRecent = useCallback((ref: string) => {
    setRecentRefs((prev) => {
      const filtered = prev.filter((r) => r !== ref);
      const updated = [ref, ...filtered].slice(0, MAX_RECENT_REFS);
      localStorage.setItem(RECENT_REFS_KEY, JSON.stringify(updated));
      return updated;
    });
  }, []);

  // Inspector state
  const [activeTab, setActiveTab] = useState<"receipts" | "variants">(
    "receipts",
  );

  // Popover state
  const [selectedToken, setSelectedToken] = useState<TokenLedger | null>(null);
  const [popoverAnchor, setPopoverAnchor] = useState<HTMLElement | null>(null);

  // Handle translation
  const handleTranslate = useCallback(async () => {
    if (!client || !reference.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setShowRecentDropdown(false);

    try {
      const response = await client.translate({
        reference: reference.trim(),
        mode,
        session_id: settings.sessionId,
        translator,
      });

      if (isGateResponse(response)) {
        navigate("/gate", {
          state: { gate: response, originalReference: reference.trim() },
        });
      } else {
        setResult(response);
        // Sprint 17: Save successful translation to recent refs
        saveToRecent(reference.trim());
      }
    } catch (err) {
      setError(createApiErrorDetail("POST", "/translate", err));
    } finally {
      setLoading(false);
    }
  }, [
    client,
    reference,
    mode,
    translator,
    settings.sessionId,
    navigate,
    saveToRecent,
  ]);

  const handleKeyPress = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !loading && reference.trim()) {
        handleTranslate();
      }
    },
    [handleTranslate, loading, reference],
  );

  // Sprint 17: Select from recent or example refs
  const handleSelectRef = useCallback((ref: string) => {
    setReference(ref);
    setShowRecentDropdown(false);
  }, []);

  // Token click handler
  const handleTokenClick = useCallback(
    (token: TokenLedger, element: HTMLElement) => {
      setSelectedToken(token);
      setPopoverAnchor(element);
    },
    [],
  );

  const handleClosePopover = useCallback(() => {
    setSelectedToken(null);
    setPopoverAnchor(null);
  }, []);

  const handleViewFullLedger = useCallback(() => {
    setActiveTab("receipts");
    handleClosePopover();
  }, [handleClosePopover]);

  // Get tokens for rendering
  const getTokensForVerse = (verseId: string): TokenLedger[] => {
    if (!result?.ledger) return [];
    const verseLedger = result.ledger.find((l) => l.verse_id === verseId);
    return verseLedger?.tokens || [];
  };

  // Render interactive translation text
  const renderInteractiveTranslation = (tokens: TokenLedger[]) => {
    if (tokens.length === 0) {
      return <span>{result?.translation_text}</span>;
    }

    return (
      <span>
        {tokens.map((token, idx) => (
          <span key={idx}>
            <InteractiveToken
              token={token}
              isCompareMode={compareMode}
              isHeatmapMode={heatmapMode}
              onClick={handleTokenClick}
            />
            {idx < tokens.length - 1 && " "}
          </span>
        ))}
      </span>
    );
  };

  return (
    <div style={containerStyle}>
      {/* Toolbar */}
      <div style={toolbarStyle}>
        {/* Sprint 17: Reference input with recent refs dropdown */}
        <div style={{ ...inputGroupStyle, position: "relative" }}>
          <label style={labelStyle}>Reference</label>
          <input
            type="text"
            style={inputStyle}
            placeholder="e.g., John 1:1 (press Enter)"
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !loading && reference.trim()) {
                handleTranslate();
              }
            }}
            onFocus={() => recentRefs.length > 0 && setShowRecentDropdown(true)}
            onBlur={() => setTimeout(() => setShowRecentDropdown(false), 200)}
          />
          {/* Recent refs dropdown */}
          {showRecentDropdown && recentRefs.length > 0 && (
            <div style={recentDropdownStyle}>
              <div
                style={{
                  padding: "6px 12px",
                  fontSize: "10px",
                  color: "#6b7280",
                  textTransform: "uppercase",
                  borderBottom: "1px solid #374151",
                }}
              >
                Recent
              </div>
              {recentRefs.map((ref) => (
                <div
                  key={ref}
                  style={recentItemStyle}
                  onMouseDown={() => handleSelectRef(ref)}
                >
                  {ref}
                </div>
              ))}
            </div>
          )}
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
          </select>
        </div>

        <button
          style={{
            ...buttonStyle,
            ...(loading || !reference.trim()
              ? { backgroundColor: "#4b5563", cursor: "not-allowed" }
              : {}),
          }}
          onClick={handleTranslate}
          disabled={!client || loading || !reference.trim()}
        >
          {loading ? "Translating..." : "Translate"}
        </button>

        {/* Sprint 17: Disable toggles until result exists */}
        <div style={{ marginLeft: "auto", display: "flex", gap: "8px" }}>
          <button
            style={
              !result
                ? disabledToggleStyle
                : compareMode
                  ? toggleActiveStyle
                  : toggleButtonStyle
            }
            onClick={() => result && setCompareMode(!compareMode)}
            title={
              result
                ? "Toggle compare mode"
                : "Translate a passage first to enable compare"
            }
            disabled={!result}
          >
            Compare
          </button>
          <button
            style={
              !result
                ? disabledToggleStyle
                : heatmapMode
                  ? toggleActiveStyle
                  : toggleButtonStyle
            }
            onClick={() => result && setHeatmapMode(!heatmapMode)}
            title={
              result
                ? "Toggle confidence heatmap"
                : "Translate a passage first to enable heatmap"
            }
            disabled={!result}
          >
            Heatmap
          </button>
        </div>
      </div>

      {/* Error display */}
      {error && (
        <ApiErrorPanel
          error={error}
          onRetry={handleTranslate}
          onDismiss={() => setError(null)}
        />
      )}

      {/* Legends */}
      {(compareMode || heatmapMode) && result && (
        <div style={{ marginBottom: "12px", display: "flex", gap: "16px" }}>
          {compareMode && (
            <div style={legendStyle}>
              <span>Diff:</span>
              <div style={legendItemStyle}>
                <span
                  style={{
                    width: "12px",
                    height: "12px",
                    backgroundColor: getChangeTypeColor("lexical"),
                    borderRadius: "2px",
                  }}
                />
                <span>Lexical</span>
              </div>
              <div style={legendItemStyle}>
                <span
                  style={{
                    width: "12px",
                    height: "12px",
                    backgroundColor: getChangeTypeColor("syntactic"),
                    borderRadius: "2px",
                  }}
                />
                <span>Syntactic</span>
              </div>
              <div style={legendItemStyle}>
                <span
                  style={{
                    width: "12px",
                    height: "12px",
                    backgroundColor: getChangeTypeColor("interpretive"),
                    borderRadius: "2px",
                  }}
                />
                <span>Interpretive</span>
              </div>
            </div>
          )}
          {heatmapMode && (
            <div style={legendStyle}>
              <span>Risk:</span>
              {HEATMAP_LEGEND.map((item) => (
                <div key={item.label} style={legendItemStyle}>
                  <span
                    style={{
                      width: "12px",
                      height: "4px",
                      backgroundColor:
                        item.risk < 0.2
                          ? "transparent"
                          : item.risk < 0.4
                            ? "#facc15"
                            : item.risk < 0.6
                              ? "#fb923c"
                              : "#f87171",
                      border: item.risk < 0.2 ? "1px solid #4b5563" : "none",
                    }}
                  />
                  <span>{item.label}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Main workspace */}
      {result ? (
        <div style={workspaceStyle}>
          {/* Left: Greek Panel */}
          <div style={panelStyle}>
            <div style={panelHeaderStyle}>Greek (SBLGNT)</div>
            <div style={panelContentStyle}>
              <div style={greekTextStyle}>{result.sblgnt_text}</div>
            </div>
          </div>

          {/* Center: Renderings */}
          <div style={panelStyle}>
            <div style={panelHeaderStyle}>
              Rendering ({result.translator_type})
            </div>
            <div style={panelContentStyle}>
              {/* Primary rendering card */}
              <div style={renderingCardStyle}>
                <div style={{ marginBottom: "8px" }}>
                  <span style={styleChipStyle}>{result.translator_type}</span>
                  <span
                    style={{ ...styleChipStyle, backgroundColor: "#22c55e" }}
                  >
                    {result.mode}
                  </span>
                </div>

                <div
                  style={{
                    fontSize: "16px",
                    color: "#eaeaea",
                    lineHeight: 1.8,
                  }}
                >
                  {result.ledger && result.ledger.length > 0
                    ? result.ledger.map((vl) => (
                        <div key={vl.verse_id} style={{ marginBottom: "12px" }}>
                          {renderInteractiveTranslation(vl.tokens)}
                        </div>
                      ))
                    : result.translation_text}
                </div>

                {result.ledger && result.ledger.length > 0 && (
                  <ConfidenceSummary
                    tokens={result.ledger.flatMap((l) => l.tokens)}
                  />
                )}
              </div>

              {/* Confidence summary */}
              {result.confidence && (
                <div
                  style={{
                    ...renderingCardStyle,
                    backgroundColor: "#1a1a2e",
                    padding: "12px",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <span style={{ color: "#9ca3af", fontSize: "12px" }}>
                      Composite Confidence
                    </span>
                    <span style={{ color: "#eaeaea", fontWeight: 500 }}>
                      {(result.confidence.composite * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div
                    style={{
                      fontSize: "11px",
                      color: "#6b7280",
                      marginTop: "4px",
                    }}
                  >
                    Weakest: {result.confidence.weakest_layer}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right: Inspector */}
          <div style={panelStyle}>
            <div style={tabBarStyle}>
              <div
                style={activeTab === "receipts" ? tabActiveStyle : tabStyle}
                onClick={() => setActiveTab("receipts")}
              >
                Receipts
              </div>
              <div
                style={activeTab === "variants" ? tabActiveStyle : tabStyle}
                onClick={() => setActiveTab("variants")}
              >
                Variants ({result.variants.length})
              </div>
            </div>
            <div style={{ ...panelContentStyle, padding: 0 }}>
              {activeTab === "receipts" && (
                <div style={{ padding: "16px" }}>
                  {result.ledger && result.ledger.length > 0 ? (
                    <LedgerList ledgers={result.ledger} />
                  ) : (
                    <div
                      style={{
                        color: "#6b7280",
                        fontSize: "13px",
                        padding: "16px",
                      }}
                    >
                      Token ledger available in Traceable mode only.
                    </div>
                  )}
                </div>
              )}
              {activeTab === "variants" && (
                <div style={{ padding: "16px" }}>
                  <DossierPanel
                    client={client}
                    reference={result.reference}
                    sessionId={settings.sessionId}
                    defaultExpanded={true}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* Sprint 17: Enhanced empty state with example chips and loading */
        <div style={workspaceStyle}>
          <div
            style={{
              ...panelStyle,
              gridColumn: "span 3",
              position: "relative",
            }}
          >
            {loading ? (
              <div style={emptyStateStyle}>
                <div
                  style={{
                    fontSize: "24px",
                    marginBottom: "16px",
                    animation: "pulse 1.5s ease-in-out infinite",
                  }}
                >
                  Translating...
                </div>
                <div style={{ color: "#60a5fa", fontSize: "14px" }}>
                  {reference}
                </div>
              </div>
            ) : !client ? (
              <div style={emptyStateStyle}>
                <div style={{ fontSize: "18px", marginBottom: "12px" }}>
                  Not Connected
                </div>
                <div style={{ marginBottom: "16px" }}>
                  Connect to the backend to start exploring Greek texts.
                </div>
                <Link
                  to="/settings"
                  style={{
                    ...buttonStyle,
                    textDecoration: "none",
                    display: "inline-block",
                  }}
                >
                  Check Connection
                </Link>
              </div>
            ) : (
              <div style={emptyStateStyle}>
                <div style={{ fontSize: "18px", marginBottom: "8px" }}>
                  Explore Greek New Testament
                </div>
                <div style={{ marginBottom: "16px" }}>
                  Enter a scripture reference above and press Enter to
                  translate.
                </div>

                {/* Example chips */}
                <div style={{ marginBottom: "16px" }}>
                  <div
                    style={{
                      fontSize: "11px",
                      color: "#6b7280",
                      marginBottom: "8px",
                      textTransform: "uppercase",
                    }}
                  >
                    Try an example
                  </div>
                  <div style={exampleChipsStyle}>
                    {EXAMPLE_REFS.map((ref) => (
                      <button
                        key={ref}
                        style={chipStyle}
                        onClick={() => {
                          setReference(ref);
                          // Auto-translate after selecting
                          setTimeout(() => handleTranslate(), 100);
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = "#4b5563";
                          e.currentTarget.style.color = "#eaeaea";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = "#374151";
                          e.currentTarget.style.color = "#9ca3af";
                        }}
                      >
                        {ref}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Recent refs if available */}
                {recentRefs.length > 0 && (
                  <div>
                    <div
                      style={{
                        fontSize: "11px",
                        color: "#6b7280",
                        marginBottom: "8px",
                        textTransform: "uppercase",
                      }}
                    >
                      Recent
                    </div>
                    <div style={exampleChipsStyle}>
                      {recentRefs.slice(0, 3).map((ref) => (
                        <button
                          key={ref}
                          style={{ ...chipStyle, borderColor: "#60a5fa" }}
                          onClick={() => {
                            setReference(ref);
                            setTimeout(() => handleTranslate(), 100);
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.backgroundColor = "#3b82f6";
                            e.currentTarget.style.color = "white";
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.backgroundColor = "#374151";
                            e.currentTarget.style.color = "#9ca3af";
                          }}
                        >
                          {ref}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Token Receipt Popover */}
      {selectedToken && (
        <TokenReceiptPopover
          token={selectedToken}
          anchorEl={popoverAnchor}
          onClose={handleClosePopover}
          onViewFullLedger={handleViewFullLedger}
        />
      )}
    </div>
  );
}

export default PassageWorkspace;
