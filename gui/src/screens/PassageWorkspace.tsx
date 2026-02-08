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

import { useState, useCallback, useMemo, useRef, useEffect } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useAppStore, selectSettings } from "../store";
import { useMediaQuery } from "../hooks/useMediaQuery";

// Sprint 17: Example references for quick access
const EXAMPLE_REFS = ["John 1:1", "Matt 5:3-12", "Mark 1:15", "Rom 8:28"];
import {
  RECENT_REFS_KEY,
  DEMO_NUDGE_DISMISSED_KEY,
  TOKEN_DENSITY_KEY,
  STUDY_MODE_KEY,
} from "../constants/storageKeys";

const MAX_RECENT_REFS = 5;
// Sprint 24 (S8): Demo + nudge constants
const DEMO_REF = "John 3:16";
import type { ApiClient } from "../api/client";
import type {
  TranslateResponse,
  TranslationMode,
  TranslatorType,
  TokenLedger,
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
// Sprint 24: New components
import { GreekTokenDisplay } from "../components/GreekTokenDisplay";
import { ConfidenceDetailPanel } from "../components/ConfidenceDetailPanel";
import { CompareModal } from "../components/CompareModal";
import {
  getChangeTypeHighlight,
  getChangeTypeColor,
  type ChangeType,
} from "../utils/renderingDiff";
import {
  nextRef,
  prevRef,
  validateRef,
  isAtChapterEnd,
  isAtChapterStart,
} from "../utils/referenceNav";
import { Tooltip } from "../components/Tooltip";
import { TokenInspectorDock } from "../components/TokenInspectorDock";
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
  alignItems: "flex-end",
  marginBottom: "16px",
  flexWrap: "wrap",
};

const inputGroupStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "4px",
};

const labelStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xs)",
  color: "var(--rl-text-muted)",
  textTransform: "uppercase",
};

const inputStyle: React.CSSProperties = {
  padding: "8px 12px",
  fontSize: "var(--rl-fs-base)",
  backgroundColor: "var(--rl-bg-card)",
  border: "1px solid var(--rl-border-strong)",
  borderRadius: "4px",
  color: "var(--rl-text)",
  width: "220px",
};

const selectStyle: React.CSSProperties = {
  ...inputStyle,
  width: "120px",
  cursor: "pointer",
};

const buttonStyle: React.CSSProperties = {
  padding: "10px 24px",
  fontSize: "var(--rl-fs-base)",
  fontWeight: 600,
  backgroundColor: "var(--rl-accent)",
  color: "white",
  border: "none",
  borderRadius: "var(--rl-radius-md)",
  cursor: "pointer",
  boxShadow: "0 0 12px rgba(212, 81, 59, 0.3)",
  letterSpacing: "0.02em",
};

const toggleButtonStyle: React.CSSProperties = {
  padding: "6px 12px",
  fontSize: "var(--rl-fs-sm)",
  backgroundColor: "var(--rl-border-strong)",
  color: "var(--rl-text-muted)",
  border: "1px solid var(--rl-border-strong)",
  borderRadius: "4px",
  cursor: "pointer",
};

const toggleActiveStyle: React.CSSProperties = {
  ...toggleButtonStyle,
  backgroundColor: "var(--rl-primary)",
  color: "white",
  borderColor: "var(--rl-primary)",
};

// UX3.2: workspaceStyle is now computed inside the component for responsive layout.
// See getWorkspaceStyle() below.

type LayoutMode = "mobile" | "tablet" | "desktop";

const panelStyle: React.CSSProperties = {
  backgroundColor: "var(--rl-bg-card)",
  borderRadius: "8px",
  overflow: "hidden",
  display: "flex",
  flexDirection: "column",
};

const panelHeaderStyle: React.CSSProperties = {
  padding: "12px 16px",
  borderBottom: "1px solid var(--rl-border-strong)",
  fontSize: "var(--rl-fs-sm)",
  fontWeight: 600,
  color: "var(--rl-text-muted)",
  textTransform: "uppercase",
};

const panelContentStyle: React.CSSProperties = {
  flex: 1,
  overflow: "auto",
  padding: "16px",
};

const renderingCardStyle: React.CSSProperties = {
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "6px",
  padding: "16px",
  marginBottom: "12px",
};

const styleChipStyle: React.CSSProperties = {
  display: "inline-block",
  padding: "2px 8px",
  borderRadius: "3px",
  fontSize: "var(--rl-fs-xs)",
  fontWeight: 600,
  backgroundColor: "var(--rl-border-strong)",
  color: "var(--rl-text-muted)",
  marginRight: "8px",
};

const tabBarStyle: React.CSSProperties = {
  display: "flex",
  borderBottom: "1px solid var(--rl-border-strong)",
  overflowX: "auto",
  scrollbarWidth: "none",
};

const tabStyle: React.CSSProperties = {
  padding: "10px 10px",
  fontSize: "var(--rl-fs-sm)",
  fontWeight: 500,
  color: "var(--rl-text-muted)",
  cursor: "pointer",
  borderBottom: "2px solid transparent",
  marginBottom: "-1px",
  whiteSpace: "nowrap",
};

const tabActiveStyle: React.CSSProperties = {
  ...tabStyle,
  color: "var(--rl-primary)",
  borderBottom: "2px solid var(--rl-primary)",
};

const legendStyle: React.CSSProperties = {
  display: "flex",
  gap: "16px",
  padding: "8px 16px",
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "4px",
  fontSize: "var(--rl-fs-xs)",
  color: "var(--rl-text-muted)",
};

const legendItemStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "6px",
};

const emptyStateStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  height: "100%",
  color: "var(--rl-text-dim)",
  textAlign: "center",
  padding: "32px 24px",
  maxWidth: "480px",
  margin: "0 auto",
};

// Sprint 17: Additional styles for usability improvements
const exampleChipsStyle: React.CSSProperties = {
  display: "flex",
  gap: "8px",
  flexWrap: "wrap",
  justifyContent: "center",
  marginTop: "8px",
};

const chipStyle: React.CSSProperties = {
  padding: "8px 16px",
  backgroundColor: "var(--rl-bg-card)",
  color: "var(--rl-text-muted)",
  borderRadius: "var(--rl-radius-md)",
  fontSize: "var(--rl-fs-sm)",
  cursor: "pointer",
  border: "1px solid var(--rl-border)",
  transition:
    "background-color var(--rl-transition-fast), border-color var(--rl-transition-fast)",
  boxShadow: "var(--rl-shadow-sm)",
};

const recentDropdownStyle: React.CSSProperties = {
  position: "absolute",
  top: "100%",
  left: 0,
  right: 0,
  backgroundColor: "var(--rl-bg-card)",
  border: "1px solid var(--rl-border-strong)",
  borderRadius: "4px",
  marginTop: "4px",
  zIndex: 10,
  maxHeight: "200px",
  overflow: "auto",
};

const recentItemStyle: React.CSSProperties = {
  padding: "8px 12px",
  fontSize: "var(--rl-fs-base)",
  color: "var(--rl-text)",
  cursor: "pointer",
  borderBottom: "1px solid var(--rl-border-strong)",
};

const disabledToggleStyle: React.CSSProperties = {
  padding: "6px 12px",
  fontSize: "var(--rl-fs-sm)",
  backgroundColor: "var(--rl-bg-card)",
  color: "var(--rl-border-strong)",
  border: "1px solid var(--rl-border-strong)",
  borderRadius: "4px",
  cursor: "not-allowed",
  opacity: 0.5,
};

// UX2.1: Token density type
type TokenDensity = "compact" | "comfortable";

// UX4.5: Study mode presets
type StudyMode = "reader" | "translator" | "text-critic" | "";

const STUDY_MODE_PRESETS: Record<
  Exclude<StudyMode, "">,
  {
    viewMode: "readable" | "traceable";
    density: TokenDensity;
    evidenceTab: "confidence" | "receipts" | "variants";
    label: string;
  }
> = {
  reader: {
    viewMode: "readable",
    density: "comfortable",
    evidenceTab: "confidence",
    label: "Reader",
  },
  translator: {
    viewMode: "traceable",
    density: "comfortable",
    evidenceTab: "receipts",
    label: "Translator",
  },
  "text-critic": {
    viewMode: "traceable",
    density: "compact",
    evidenceTab: "variants",
    label: "Text Critic",
  },
};

// Interactive token component
interface InteractiveTokenProps {
  token: TokenLedger;
  isCompareMode: boolean;
  changeType?: ChangeType;
  isHeatmapMode: boolean;
  /** S5: Whether this token is alignment-selected */
  isAlignmentSelected: boolean;
  /** S5: Whether this token is alignment-highlighted (in same segment) */
  isAlignmentHighlighted: boolean;
  /** UX2.1: Token display density */
  density: TokenDensity;
  onClick: (token: TokenLedger, element: HTMLElement) => void;
}

function InteractiveToken({
  token,
  isCompareMode,
  changeType,
  isHeatmapMode,
  isAlignmentSelected,
  isAlignmentHighlighted,
  density,
  onClick,
}: InteractiveTokenProps) {
  const ref = useRef<HTMLSpanElement>(null);

  const isCompact = density === "compact";
  let style: React.CSSProperties = {
    cursor: "pointer",
    padding: isCompact ? "1px 2px" : "2px 6px",
    borderRadius: "3px",
    fontSize: isCompact ? "14px" : "16px",
    transition: "background-color 0.15s, outline 0.15s",
  };

  // S5: Apply alignment highlighting
  if (isAlignmentSelected) {
    style.backgroundColor = "rgba(96, 165, 250, 0.25)";
    style.outline = "1px solid rgba(96, 165, 250, 0.5)";
  } else if (isAlignmentHighlighted) {
    style.backgroundColor = "rgba(96, 165, 250, 0.12)";
  }

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
    <Tooltip
      content="Select to highlight aligned Greek token(s)."
      position="bottom"
    >
      <span
        ref={ref}
        data-testid={`render-token-${token.position}`}
        style={style}
        onClick={handleClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            handleClick();
          }
        }}
        aria-selected={isAlignmentSelected || undefined}
      >
        {token.gloss.replace(/^\[|\]$/g, "")}
      </span>
    </Tooltip>
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
      ? "var(--rl-success)"
      : avgRisk < 0.4
        ? "#fde68a"
        : avgRisk < 0.6
          ? "var(--rl-warning)"
          : "var(--rl-error)";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        marginTop: "8px",
        fontSize: "var(--rl-fs-xs)",
        color: "var(--rl-text-muted)",
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
  const [searchParams, setSearchParams] = useSearchParams();
  const settings = useAppStore(selectSettings);

  // Initialize form state from URL search params
  const initialRef = searchParams.get("ref") || "";
  const initialMode =
    (searchParams.get("mode") as TranslationMode) || "traceable";
  const initialTranslator =
    (searchParams.get("tr") as TranslatorType) || "literal";

  // Form state
  const [reference, setReference] = useState(initialRef);
  const [mode, setMode] = useState<TranslationMode>(
    initialMode === "readable" || initialMode === "traceable"
      ? initialMode
      : "traceable",
  );
  const [translator, setTranslator] = useState<TranslatorType>(
    (["fake", "literal", "fluent", "traceable"] as TranslatorType[]).includes(
      initialTranslator,
    )
      ? initialTranslator
      : "literal",
  );

  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiErrorDetail | null>(null);
  const [result, setResult] = useState<TranslateResponse | null>(null);

  // View mode: controls rendering without re-fetching
  // "readable" = clean paragraph text; "traceable" = interactive tokens + receipts
  const [viewMode, setViewMode] = useState<"readable" | "traceable">(
    "readable",
  );

  // Feature toggles
  const [compareMode] = useState(false);
  const [heatmapMode, setHeatmapMode] = useState(false);

  // Sprint 24 (S5): Alignment selection state
  const [selectedTokenPosition, setSelectedTokenPosition] = useState<
    number | null
  >(null);

  // Sprint 24 (S6): Confidence layer detail state
  const [confidenceDetailLayer, setConfidenceDetailLayer] = useState<
    "textual" | "grammatical" | "lexical" | "interpretive" | null
  >(null);

  // UX2.1: Token density state
  const [tokenDensity, setTokenDensity] = useState<TokenDensity>(() => {
    try {
      const stored = localStorage.getItem(TOKEN_DENSITY_KEY);
      return stored === "compact" ? "compact" : "comfortable";
    } catch {
      return "comfortable";
    }
  });

  const handleDensityChange = useCallback((d: TokenDensity) => {
    setTokenDensity(d);
    try {
      localStorage.setItem(TOKEN_DENSITY_KEY, d);
    } catch {
      // Ignore storage errors
    }
  }, []);

  // UX4.5: Study mode preset state
  const [studyMode, setStudyMode] = useState<StudyMode>(() => {
    try {
      const stored = localStorage.getItem(STUDY_MODE_KEY);
      if (
        stored === "reader" ||
        stored === "translator" ||
        stored === "text-critic"
      )
        return stored;
    } catch {
      // Ignore
    }
    return "";
  });

  const handleStudyModeChange = useCallback((mode: StudyMode) => {
    setStudyMode(mode);
    try {
      localStorage.setItem(STUDY_MODE_KEY, mode);
    } catch {
      // Ignore storage errors
    }
    if (mode && mode in STUDY_MODE_PRESETS) {
      const preset = STUDY_MODE_PRESETS[mode as Exclude<StudyMode, "">];
      setViewMode(preset.viewMode);
      setTokenDensity(preset.density);
      try {
        localStorage.setItem(TOKEN_DENSITY_KEY, preset.density);
      } catch {
        // Ignore
      }
      setActiveTab(preset.evidenceTab);
    }
  }, []);

  // UX3.2: Responsive layout breakpoints
  const isMobile = useMediaQuery("(max-width: 640px)");
  const isTablet = useMediaQuery("(max-width: 900px)");
  const layoutMode: LayoutMode = isMobile
    ? "mobile"
    : isTablet
      ? "tablet"
      : "desktop";

  const workspaceStyle: React.CSSProperties = useMemo(
    () => ({
      flex: 1,
      display: "grid",
      gridTemplateColumns:
        layoutMode === "mobile"
          ? "1fr"
          : layoutMode === "tablet"
            ? "1fr 1fr"
            : "1fr 2fr 1fr",
      gap: layoutMode === "mobile" ? "8px" : "16px",
      overflow: layoutMode === "mobile" ? "auto" : "hidden",
      minHeight: 0,
    }),
    [layoutMode],
  );

  // Sprint 24 (S7): Compare modal state
  const [showCompareModal, setShowCompareModal] = useState(false);

  // Sprint 24 (S8): Demo nudge state
  const [demoNudgeDismissed, setDemoNudgeDismissed] = useState(() => {
    try {
      return localStorage.getItem(DEMO_NUDGE_DISMISSED_KEY) === "true";
    } catch {
      return false;
    }
  });
  const [isDemoResult, setIsDemoResult] = useState(false);

  // Sprint 17: Recent references
  const [recentRefs, setRecentRefs] = useState<string[]>([]);
  const [showRecentDropdown, setShowRecentDropdown] = useState(false);
  // UX4.1: Orientation strip recent refs dropdown (separate from input dropdown)
  const [showStripRecent, setShowStripRecent] = useState(false);
  const stripRecentRef = useRef<HTMLDivElement>(null);

  // Sync state to URL search params (without page reload)
  const updateUrlParams = useCallback(
    (ref: string, m: TranslationMode, tr: TranslatorType) => {
      const params = new URLSearchParams();
      if (ref) params.set("ref", ref);
      if (m !== "traceable") params.set("mode", m);
      if (tr !== "literal") params.set("tr", tr);
      setSearchParams(params, { replace: true });
    },
    [setSearchParams],
  );

  // Auto-translate from URL params on first mount (S2.1: guarded)
  const [autoTranslated, setAutoTranslated] = useState(false);
  useEffect(() => {
    if (!autoTranslated && initialRef && client) {
      setAutoTranslated(true);
      // S2.1: Validate ref before auto-translate to avoid firing bad requests
      const refError = validateRef(initialRef);
      if (refError) {
        setError(
          createApiErrorDetail("GET", "/explore", {
            message: `Invalid reference in URL: ${refError}`,
          }),
        );
        return;
      }
      // Defer to avoid calling during render
      const timer = setTimeout(() => {
        handleTranslate();
      }, 0);
      return () => clearTimeout(timer);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client, autoTranslated]);

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

  // UX4.1: Close strip recent dropdown on outside click
  useEffect(() => {
    if (!showStripRecent) return;
    const handler = (e: MouseEvent) => {
      if (
        stripRecentRef.current &&
        !stripRecentRef.current.contains(e.target as Node)
      ) {
        setShowStripRecent(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showStripRecent]);

  // UX2.5: Ref for the input element (keyboard focus target)
  const refInputRef = useRef<HTMLInputElement>(null);
  // UX3.5: Focus-return refs
  const compareBtnRef = useRef<HTMLButtonElement>(null);

  // Save a reference to recent history
  const saveToRecent = useCallback((ref: string) => {
    setRecentRefs((prev) => {
      const filtered = prev.filter((r) => r !== ref);
      const updated = [ref, ...filtered].slice(0, MAX_RECENT_REFS);
      localStorage.setItem(RECENT_REFS_KEY, JSON.stringify(updated));
      return updated;
    });
  }, []);

  // Sprint 24 (S5): Compute highlighted positions from segment alignment
  const highlightedPositions = useMemo(() => {
    const positions = new Set<number>();
    if (selectedTokenPosition === null || !result?.ledger) return positions;

    // Find all segments that contain the selected position
    for (const verse of result.ledger) {
      for (const seg of verse.translation_segments) {
        const [start, end] = seg.token_range;
        if (selectedTokenPosition >= start && selectedTokenPosition <= end) {
          // Add all positions in this segment
          for (let i = start; i <= end; i++) {
            if (i !== selectedTokenPosition) {
              positions.add(i);
            }
          }
        }
      }
    }
    return positions;
  }, [selectedTokenPosition, result?.ledger]);

  // Sprint 24 (S5): Greek token click handler
  const handleGreekTokenClick = useCallback(
    (token: TokenLedger, _verseIdx: number, element: HTMLElement) => {
      // Toggle selection
      if (selectedTokenPosition === token.position) {
        setSelectedTokenPosition(null);
        setPopoverAnchor(null);
        setSelectedToken(null);
      } else {
        setSelectedTokenPosition(token.position);
        setSelectedToken(token);
        setPopoverAnchor(element);
      }
    },
    [selectedTokenPosition],
  );

  // Sprint 24 (S8): Demo handler
  const handleDemo = useCallback(async () => {
    if (!client) return;
    setReference(DEMO_REF);
    setMode("readable");
    setTranslator("literal");
    setIsDemoResult(true);

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await client.translate({
        reference: DEMO_REF,
        mode: "readable",
        session_id: settings.sessionId,
        translator: "literal",
      });

      if (isGateResponse(response)) {
        navigate("/gate", {
          state: { gate: response, originalReference: DEMO_REF },
        });
      } else {
        setResult(response);
        // Sprint 26 (UX1): Sync viewMode to result's actual mode
        setViewMode(response.mode === "traceable" ? "traceable" : "readable");
        saveToRecent(DEMO_REF);
        updateUrlParams(DEMO_REF, "readable", "literal");
      }
    } catch (err) {
      setError(createApiErrorDetail("POST", "/translate", err));
    } finally {
      setLoading(false);
    }
  }, [client, settings.sessionId, navigate, saveToRecent, updateUrlParams]);

  // Sprint 24 (S8): Dismiss nudge
  const handleDismissNudge = useCallback(() => {
    setDemoNudgeDismissed(true);
    try {
      localStorage.setItem(DEMO_NUDGE_DISMISSED_KEY, "true");
    } catch {
      // Ignore storage errors
    }
  }, []);

  // Sprint 24 (S8): Accept nudge — just switches view mode (re-translate handled below)
  const [nudgeAccepted, setNudgeAccepted] = useState(false);
  const handleAcceptNudge = useCallback(() => {
    handleDismissNudge();
    setViewMode("traceable");
    setNudgeAccepted(true);
  }, [handleDismissNudge]);

  // UX4.3: Evidence panel state (unified: confidence + receipts + variants)
  const [activeTab, setActiveTab] = useState<
    "confidence" | "receipts" | "variants"
  >("confidence");

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
    // S5/S6: Clear selection states on new translate
    setSelectedTokenPosition(null);
    setSelectedToken(null);
    setPopoverAnchor(null);
    setConfidenceDetailLayer(null);
    setIsDemoResult(false);

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
        // Sprint 26 (UX1): Sync viewMode to the result's actual mode
        // so users see traceable view when they requested traceable
        setViewMode(response.mode === "traceable" ? "traceable" : "readable");
        // Sprint 17: Save successful translation to recent refs
        saveToRecent(reference.trim());
        // Sync URL with translated state
        updateUrlParams(reference.trim(), mode, translator);
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
    updateUrlParams,
  ]);

  // S8: Effect to re-translate after nudge acceptance
  useEffect(() => {
    if (nudgeAccepted && result?.mode === "readable") {
      setNudgeAccepted(false);
      setMode("traceable");
      setTimeout(() => handleTranslate(), 50);
    } else if (nudgeAccepted) {
      setNudgeAccepted(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nudgeAccepted]);

  // Sprint 17: Select from recent or example refs
  const handleSelectRef = useCallback((ref: string) => {
    setReference(ref);
    setShowRecentDropdown(false);
  }, []);

  // Token click handler (rendering tokens)
  const handleTokenClick = useCallback(
    (token: TokenLedger, element: HTMLElement) => {
      // S5: Toggle alignment selection
      if (selectedTokenPosition === token.position) {
        setSelectedTokenPosition(null);
        setSelectedToken(null);
        setPopoverAnchor(null);
      } else {
        setSelectedTokenPosition(token.position);
        setSelectedToken(token);
        setPopoverAnchor(element);
      }
    },
    [selectedTokenPosition],
  );

  const handleClosePopover = useCallback(() => {
    setSelectedToken(null);
    setPopoverAnchor(null);
    setSelectedTokenPosition(null);
  }, []);

  const handleViewFullLedger = useCallback(() => {
    setActiveTab("receipts");
    handleClosePopover();
  }, [handleClosePopover]);

  // UX2.5: Global keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // `/` focuses ref input (when not in an input/select/textarea)
      if (
        e.key === "/" &&
        !["INPUT", "SELECT", "TEXTAREA"].includes(
          (e.target as HTMLElement)?.tagName,
        )
      ) {
        e.preventDefault();
        refInputRef.current?.focus();
      }
      // Esc closes compare modal or token popover
      if (e.key === "Escape") {
        if (showCompareModal) {
          setShowCompareModal(false);
        } else if (selectedToken) {
          handleClosePopover();
        }
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [showCompareModal, selectedToken, handleClosePopover]);

  // UX4.4: Compute next-action guidance for each evidence tab
  const getNextAction = useCallback(
    (tab: "confidence" | "receipts" | "variants") => {
      if (!result) return null;

      if (tab === "confidence") {
        if (!result.confidence) {
          return {
            text: "Confidence data requires a successful translation.",
            action: null,
          };
        }
        return null; // Confidence has data — no action needed
      }

      if (tab === "receipts") {
        if (
          result.mode === "readable" &&
          (!result.ledger || result.ledger.length === 0)
        ) {
          return {
            text: "Re-translate in Traceable mode for per-token receipts.",
            action: () => {
              setMode("traceable");
              setTimeout(() => handleTranslate(), 50);
            },
            label: "Re-translate in Traceable",
          };
        }
        if (
          viewMode === "readable" &&
          result.ledger &&
          result.ledger.length > 0
        ) {
          return {
            text: "Switch to Traceable view to see receipts.",
            action: () => setViewMode("traceable"),
            label: "Switch to Traceable",
          };
        }
        return null;
      }

      if (tab === "variants") {
        if (result.variants.length === 0) {
          return {
            text: "No variants at this reference. Check installed source packs.",
            action: null,
            link: "/sources",
            label: "Go to Sources",
          };
        }
        return null;
      }

      return null;
    },
    [result, viewMode, handleTranslate],
  );

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
              isAlignmentSelected={selectedTokenPosition === token.position}
              isAlignmentHighlighted={highlightedPositions.has(token.position)}
              density={tokenDensity}
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
        {/* Reference input with recent refs dropdown + nav buttons */}
        <div style={{ ...inputGroupStyle, position: "relative" }}>
          <label style={labelStyle}>Reference</label>
          <div style={{ display: "flex", gap: "4px", alignItems: "center" }}>
            <Tooltip
              content={(() => {
                const prev = prevRef(reference);
                if (!prev) {
                  return isAtChapterStart(reference) === true
                    ? "At verse 1. Chapter boundary navigation not yet supported."
                    : "No previous verse available.";
                }
                return `Previous: ${prev}`;
              })()}
              position="bottom"
              wrapFocus={!prevRef(reference)}
            >
              <button
                data-testid="prev-btn"
                aria-label={`Previous verse${prevRef(reference) ? `: ${prevRef(reference)}` : ""}`}
                style={{
                  ...toggleButtonStyle,
                  padding: "8px 10px",
                  fontSize: "var(--rl-fs-base)",
                  opacity: prevRef(reference) ? 1 : 0.3,
                }}
                onClick={() => {
                  const prev = prevRef(reference);
                  if (prev) setReference(prev);
                }}
                disabled={!prevRef(reference)}
              >
                &#8592;
              </button>
            </Tooltip>
            <Tooltip
              content="Enter a passage like 'John 3:16' or a range like 'John 3:16-19'. Press Enter to translate."
              position="bottom"
            >
              <input
                ref={refInputRef}
                data-testid="ref-input"
                type="text"
                style={{
                  ...inputStyle,
                  borderColor:
                    reference.trim() && validateRef(reference)
                      ? "var(--rl-error)"
                      : "var(--rl-border-strong)",
                }}
                placeholder="e.g., John 1:1 (press Enter)"
                aria-label="Scripture reference"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !loading && reference.trim()) {
                    handleTranslate();
                  }
                }}
                onFocus={() =>
                  recentRefs.length > 0 && setShowRecentDropdown(true)
                }
                onBlur={() =>
                  setTimeout(() => setShowRecentDropdown(false), 200)
                }
              />
            </Tooltip>
            <Tooltip
              content={(() => {
                const next = nextRef(reference);
                if (!next) {
                  return isAtChapterEnd(reference) === true
                    ? "At last verse of chapter. Chapter boundary navigation not yet supported."
                    : "No next verse available.";
                }
                return `Next: ${next}`;
              })()}
              position="bottom"
              wrapFocus={!nextRef(reference)}
            >
              <button
                style={{
                  ...toggleButtonStyle,
                  padding: "8px 10px",
                  fontSize: "var(--rl-fs-base)",
                  opacity: nextRef(reference) ? 1 : 0.3,
                }}
                onClick={() => {
                  const next = nextRef(reference);
                  if (next) setReference(next);
                }}
                data-testid="next-btn"
                aria-label={`Next verse${nextRef(reference) ? `: ${nextRef(reference)}` : ""}`}
                disabled={!nextRef(reference)}
              >
                &#8594;
              </button>
            </Tooltip>
          </div>
          {/* Validation hint */}
          {reference.trim() && validateRef(reference) && (
            <div
              style={{
                fontSize: "var(--rl-fs-xs)",
                color: "var(--rl-error)",
                marginTop: "2px",
              }}
            >
              {validateRef(reference)}
            </div>
          )}
          {/* Recent refs dropdown */}
          {showRecentDropdown && recentRefs.length > 0 && (
            <div style={recentDropdownStyle}>
              <div
                style={{
                  padding: "6px 12px",
                  fontSize: "var(--rl-fs-xs)",
                  color: "var(--rl-text-dim)",
                  textTransform: "uppercase",
                  borderBottom: "1px solid var(--rl-border-strong)",
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

        {/* Sprint 26 (UX3): Controls group — wraps together at narrow widths */}
        <div
          style={{
            display: "flex",
            gap: "12px",
            alignItems: "flex-end",
            flexWrap: "wrap",
          }}
          data-testid="toolbar-controls-group"
        >
          <div style={inputGroupStyle}>
            <label style={labelStyle}>Request Mode</label>
            <Tooltip
              content="Controls what the backend generates. Traceable includes token ledger and receipts but may be slower."
              position="bottom"
            >
              <select
                data-testid="request-mode-select"
                style={selectStyle}
                value={mode}
                onChange={(e) => setMode(e.target.value as TranslationMode)}
                aria-label="Request mode"
              >
                <option value="readable">Readable</option>
                <option value="traceable">Traceable</option>
              </select>
            </Tooltip>
          </div>

          <div style={inputGroupStyle}>
            <label style={labelStyle}>Translator</label>
            <Tooltip
              content="Select the translator profile. Literal preserves word order; Fluent prioritizes natural English."
              position="bottom"
            >
              <select
                data-testid="translator-select"
                style={selectStyle}
                value={translator}
                onChange={(e) =>
                  setTranslator(e.target.value as TranslatorType)
                }
                aria-label="Translator type"
              >
                <option value="literal">Literal</option>
                <option value="fluent">Fluent</option>
                <option value="traceable">Traceable</option>
              </select>
            </Tooltip>
          </div>

          <Tooltip
            content="Translate the selected reference using the current settings."
            position="bottom"
            wrapFocus={!client || loading || !reference.trim()}
          >
            <button
              data-testid="translate-btn"
              aria-label="Translate"
              style={{
                ...buttonStyle,
                alignSelf: "flex-end",
                ...(loading || !reference.trim()
                  ? {
                      backgroundColor: "var(--rl-border-strong)",
                      cursor: "not-allowed",
                      boxShadow: "none",
                    }
                  : {}),
              }}
              onClick={handleTranslate}
              disabled={!client || loading || !reference.trim()}
            >
              {loading ? "Translating..." : "Translate"}
            </button>
          </Tooltip>
        </div>
        {/* end toolbar-controls-group */}

        {/* UX4.5: Study Mode Presets */}
        <div style={inputGroupStyle}>
          <label style={labelStyle}>Study Mode</label>
          <Tooltip
            content="Preset configurations for different study workflows. Reader for reading, Translator for token work, Text Critic for variant analysis."
            position="bottom"
          >
            <select
              data-testid="study-mode-select"
              style={{ ...selectStyle, width: "130px" }}
              value={studyMode}
              onChange={(e) =>
                handleStudyModeChange(e.target.value as StudyMode)
              }
              aria-label="Study mode preset"
            >
              <option value="">Manual</option>
              <option value="reader" data-testid="study-mode-reader">
                Reader
              </option>
              <option value="translator" data-testid="study-mode-translator">
                Translator
              </option>
              <option value="text-critic" data-testid="study-mode-text-critic">
                Text Critic
              </option>
            </select>
          </Tooltip>
        </div>

        <div style={{ marginLeft: "auto", display: "flex", gap: "8px" }}>
          <Tooltip
            content={
              result
                ? "Compare two renderings side-by-side (e.g., different translators)."
                : "Translate a passage first to enable compare."
            }
            position="bottom"
            wrapFocus={!result}
          >
            <button
              ref={compareBtnRef}
              data-testid="compare-btn"
              aria-label="Compare translations"
              style={
                !result
                  ? disabledToggleStyle
                  : showCompareModal
                    ? toggleActiveStyle
                    : toggleButtonStyle
              }
              onClick={() => result && setShowCompareModal(true)}
              disabled={!result}
            >
              Compare
            </button>
          </Tooltip>
          <Tooltip
            content={
              result
                ? "Highlight tokens by confidence risk. Red = low confidence."
                : "Translate a passage first to enable heatmap."
            }
            position="bottom"
            wrapFocus={!result}
          >
            <button
              data-testid="heatmap-btn"
              aria-label="Toggle confidence heatmap"
              aria-pressed={heatmapMode}
              style={
                !result
                  ? disabledToggleStyle
                  : heatmapMode
                    ? toggleActiveStyle
                    : toggleButtonStyle
              }
              onClick={() => result && setHeatmapMode(!heatmapMode)}
              disabled={!result}
            >
              Heatmap
            </button>
          </Tooltip>
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

      {/* UX4.1: Orientation Strip — always-visible ref + mode context */}
      {result && (
        <div
          data-testid="orientation-strip"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            padding: "8px 16px",
            marginBottom: "8px",
            backgroundColor: "var(--rl-bg-card)",
            borderRadius: "6px",
            fontSize: "var(--rl-fs-base)",
            flexWrap: "wrap",
          }}
        >
          <span
            data-testid="orientation-ref"
            style={{
              color: "var(--rl-text)",
              fontWeight: 600,
              fontSize: "15px",
              letterSpacing: "0.01em",
            }}
          >
            {result.reference}
          </span>
          <span
            data-testid="orientation-mode"
            style={{
              ...styleChipStyle,
              backgroundColor:
                result.mode === "traceable"
                  ? "var(--rl-success)"
                  : "var(--rl-primary)",
            }}
          >
            {result.mode}
          </span>
          <span style={styleChipStyle}>{result.translator_type}</span>
          {/* Spacer */}
          <div style={{ flex: 1 }} />
          {/* Recent refs button */}
          {recentRefs.length > 0 && (
            <div ref={stripRecentRef} style={{ position: "relative" }}>
              <button
                data-testid="recent-refs-btn"
                aria-label="Recent references"
                aria-expanded={showStripRecent}
                style={{
                  ...toggleButtonStyle,
                  padding: "4px 10px",
                  fontSize: "var(--rl-fs-xs)",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                }}
                onClick={() => setShowStripRecent(!showStripRecent)}
                onKeyDown={(e) => {
                  if (e.key === "Escape") setShowStripRecent(false);
                }}
              >
                Recent
                <span style={{ fontSize: "9px" }}>
                  {showStripRecent ? "\u25B2" : "\u25BC"}
                </span>
              </button>
              {showStripRecent && (
                <div
                  data-testid="recent-refs-menu"
                  role="menu"
                  style={{
                    position: "absolute",
                    top: "100%",
                    right: 0,
                    backgroundColor: "var(--rl-bg-card)",
                    border: "1px solid var(--rl-border-strong)",
                    borderRadius: "4px",
                    marginTop: "4px",
                    zIndex: 20,
                    minWidth: "180px",
                    maxHeight: "200px",
                    overflow: "auto",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
                  }}
                >
                  {recentRefs.map((ref, i) => (
                    <div
                      key={ref}
                      data-testid={`recent-refs-item-${i}`}
                      role="menuitem"
                      tabIndex={0}
                      style={{
                        ...recentItemStyle,
                        backgroundColor:
                          ref === result.reference
                            ? "rgba(96, 165, 250, 0.15)"
                            : "transparent",
                      }}
                      onClick={() => {
                        setReference(ref);
                        setShowStripRecent(false);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          setReference(ref);
                          setShowStripRecent(false);
                        }
                      }}
                    >
                      {ref}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
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
                      border:
                        item.risk < 0.2
                          ? "1px solid var(--rl-border-strong)"
                          : "none",
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
        <div style={workspaceStyle} data-testid="explore-ready">
          {/* Left: Greek Panel */}
          <div style={panelStyle} role="region" aria-label="Greek text">
            <div style={panelHeaderStyle}>Greek (SBLGNT)</div>
            <div style={panelContentStyle}>
              <GreekTokenDisplay
                sblgntText={result.sblgnt_text}
                ledger={result.ledger}
                selectedPosition={selectedTokenPosition}
                highlightedPositions={highlightedPositions}
                onTokenClick={handleGreekTokenClick}
                requestMode={result.mode}
                translatorType={result.translator_type}
              />
            </div>
          </div>

          {/* Center: Renderings + Token Dock */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
              minHeight: 0,
            }}
          >
            <div
              style={{ ...panelStyle, flex: 1, minHeight: 0 }}
              role="region"
              aria-label="Translation rendering"
            >
              <div
                style={{
                  ...panelHeaderStyle,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span>Rendering ({result.translator_type})</span>
                {/* UX2.1: Density toggle + View toggle */}
                <div
                  style={{ display: "flex", gap: "8px", alignItems: "center" }}
                >
                  {viewMode === "traceable" && (
                    <div
                      data-testid="density-toggle"
                      style={{ display: "flex", gap: "2px" }}
                    >
                      <Tooltip
                        content="Compact token spacing for faster scanning."
                        position="bottom"
                      >
                        <button
                          data-testid="density-compact-btn"
                          aria-label="Compact density"
                          aria-pressed={tokenDensity === "compact"}
                          style={{
                            padding: "3px 8px",
                            fontSize: "var(--rl-fs-xs)",
                            border: "1px solid var(--rl-border-strong)",
                            borderRadius: "3px 0 0 3px",
                            cursor: "pointer",
                            backgroundColor:
                              tokenDensity === "compact"
                                ? "var(--rl-primary)"
                                : "var(--rl-border-strong)",
                            color:
                              tokenDensity === "compact"
                                ? "white"
                                : "var(--rl-text-muted)",
                            borderColor:
                              tokenDensity === "compact"
                                ? "var(--rl-primary)"
                                : "var(--rl-border-strong)",
                          }}
                          onClick={() => handleDensityChange("compact")}
                        >
                          Compact
                        </button>
                      </Tooltip>
                      <Tooltip
                        content="Comfortable token spacing with more whitespace."
                        position="bottom"
                      >
                        <button
                          data-testid="density-comfortable-btn"
                          aria-label="Comfortable density"
                          aria-pressed={tokenDensity === "comfortable"}
                          style={{
                            padding: "3px 8px",
                            fontSize: "var(--rl-fs-xs)",
                            border: "1px solid var(--rl-border-strong)",
                            borderRadius: "0 3px 3px 0",
                            cursor: "pointer",
                            backgroundColor:
                              tokenDensity === "comfortable"
                                ? "var(--rl-primary)"
                                : "var(--rl-border-strong)",
                            color:
                              tokenDensity === "comfortable"
                                ? "white"
                                : "var(--rl-text-muted)",
                            borderColor:
                              tokenDensity === "comfortable"
                                ? "var(--rl-primary)"
                                : "var(--rl-border-strong)",
                          }}
                          onClick={() => handleDensityChange("comfortable")}
                        >
                          Comfortable
                        </button>
                      </Tooltip>
                    </div>
                  )}
                  <Tooltip
                    content="Switch how results are displayed. Traceable shows token-by-token mapping and receipts."
                    position="bottom"
                  >
                    <div style={{ display: "flex", gap: "4px" }}>
                      <button
                        style={{
                          padding: "3px 10px",
                          fontSize: "var(--rl-fs-xs)",
                          border: "1px solid var(--rl-border-strong)",
                          borderRadius: "3px 0 0 3px",
                          cursor: "pointer",
                          backgroundColor:
                            viewMode === "readable"
                              ? "var(--rl-primary)"
                              : "var(--rl-border-strong)",
                          color:
                            viewMode === "readable"
                              ? "white"
                              : "var(--rl-text-muted)",
                          borderColor:
                            viewMode === "readable"
                              ? "var(--rl-primary)"
                              : "var(--rl-border-strong)",
                        }}
                        data-testid="view-readable-btn"
                        aria-label="Readable view"
                        aria-pressed={viewMode === "readable"}
                        onClick={() => setViewMode("readable")}
                      >
                        Readable
                      </button>
                      <button
                        style={{
                          padding: "3px 10px",
                          fontSize: "var(--rl-fs-xs)",
                          border: "1px solid var(--rl-border-strong)",
                          borderRadius: "0 3px 3px 0",
                          cursor: "pointer",
                          backgroundColor:
                            viewMode === "traceable"
                              ? "var(--rl-primary)"
                              : "var(--rl-border-strong)",
                          color:
                            viewMode === "traceable"
                              ? "white"
                              : "var(--rl-text-muted)",
                          borderColor:
                            viewMode === "traceable"
                              ? "var(--rl-primary)"
                              : "var(--rl-border-strong)",
                        }}
                        data-testid="view-traceable-btn"
                        aria-label="Traceable view"
                        aria-pressed={viewMode === "traceable"}
                        onClick={() => setViewMode("traceable")}
                      >
                        Traceable
                      </button>
                    </div>
                  </Tooltip>
                </div>
              </div>
              <div style={panelContentStyle}>
                {/* Primary rendering card */}
                <div style={renderingCardStyle}>
                  {/* Sprint 26 (UX1): Simplified chip display — max 2 chips */}
                  <div
                    style={{ marginBottom: "8px" }}
                    data-testid="rendering-chips"
                  >
                    <span style={styleChipStyle}>{result.translator_type}</span>
                    {viewMode !== result.mode ? (
                      <Tooltip
                        content={
                          viewMode === "traceable" && result.mode === "readable"
                            ? "Viewing as Traceable, but data was generated as Readable. Token evidence may be missing. Re-translate in Traceable mode for full data."
                            : `Viewing as ${viewMode}, but data was generated as ${result.mode}.`
                        }
                        position="bottom"
                      >
                        <span
                          style={{
                            ...styleChipStyle,
                            backgroundColor: "var(--rl-warning)",
                            color: "var(--rl-bg-app)",
                          }}
                        >
                          viewing as: {viewMode}
                        </span>
                      </Tooltip>
                    ) : (
                      <span
                        style={{
                          ...styleChipStyle,
                          backgroundColor: "var(--rl-success)",
                        }}
                      >
                        {result.mode}
                      </span>
                    )}
                  </div>
                  {/* S4.1: Stale-result CTA when viewing traceable but generated readable */}
                  {viewMode === "traceable" &&
                    result.mode === "readable" &&
                    (!result.ledger || result.ledger.length === 0) && (
                      <div
                        style={{
                          fontSize: "var(--rl-fs-xs)",
                          color: "var(--rl-warning)",
                          marginBottom: "8px",
                          padding: "6px 10px",
                          backgroundColor: "rgba(245, 158, 11, 0.1)",
                          borderRadius: "4px",
                          border: "1px solid rgba(245, 158, 11, 0.2)",
                        }}
                      >
                        No token data available. These results were generated in
                        Readable mode.{" "}
                        <span
                          style={{
                            color: "var(--rl-primary)",
                            cursor: "pointer",
                            textDecoration: "underline",
                          }}
                          onClick={() => {
                            setMode("traceable");
                            setTimeout(() => handleTranslate(), 50);
                          }}
                        >
                          Re-translate in Traceable
                        </span>
                      </div>
                    )}

                  <div
                    style={{
                      fontSize: "var(--rl-fs-md)",
                      color: "var(--rl-text)",
                      lineHeight: 1.8,
                    }}
                  >
                    {viewMode === "traceable" &&
                    result.ledger &&
                    result.ledger.length > 0
                      ? result.ledger.map((vl) => (
                          <div
                            key={vl.verse_id}
                            style={{ marginBottom: "12px" }}
                          >
                            {renderInteractiveTranslation(vl.tokens)}
                          </div>
                        ))
                      : result.translation_text}
                  </div>

                  {viewMode === "traceable" &&
                    result.ledger &&
                    result.ledger.length > 0 && (
                      <ConfidenceSummary
                        tokens={result.ledger.flatMap((l) => l.tokens)}
                      />
                    )}

                  {/* Readable mode hint when traceable data available */}
                  {viewMode === "readable" &&
                    result.ledger &&
                    result.ledger.length > 0 && (
                      <div
                        style={{
                          marginTop: "12px",
                          fontSize: "var(--rl-fs-xs)",
                          color: "var(--rl-text-dim)",
                        }}
                      >
                        Token-level evidence available.{" "}
                        <span
                          style={{
                            color: "var(--rl-primary)",
                            cursor: "pointer",
                            textDecoration: "underline",
                          }}
                          onClick={() => setViewMode("traceable")}
                        >
                          Switch to Traceable view
                        </span>{" "}
                        to see per-token receipts and confidence.
                      </div>
                    )}
                </div>

                {/* UX4.3: Compact confidence indicator — full details in Evidence panel */}
                {result.confidence && (
                  <div
                    style={{
                      ...renderingCardStyle,
                      backgroundColor: "var(--rl-bg-app)",
                      padding: "8px 12px",
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                      cursor: "pointer",
                    }}
                    onClick={() => setActiveTab("confidence")}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        setActiveTab("confidence");
                      }
                    }}
                  >
                    <span
                      style={{
                        color: "var(--rl-text-muted)",
                        fontSize: "var(--rl-fs-xs)",
                        fontWeight: 500,
                      }}
                    >
                      Confidence
                    </span>
                    <div
                      style={{
                        flex: 1,
                        height: "4px",
                        backgroundColor: "var(--rl-border-strong)",
                        borderRadius: "2px",
                        overflow: "hidden",
                        maxWidth: "120px",
                      }}
                    >
                      <div
                        style={{
                          width: `${(result.confidence.composite * 100).toFixed(0)}%`,
                          height: "100%",
                          backgroundColor:
                            result.confidence.composite >= 0.8
                              ? "var(--rl-success)"
                              : result.confidence.composite >= 0.6
                                ? "var(--rl-warning)"
                                : "var(--rl-error)",
                          borderRadius: "2px",
                        }}
                      />
                    </div>
                    <span
                      style={{
                        color: "var(--rl-text)",
                        fontWeight: 600,
                        fontSize: "var(--rl-fs-base)",
                      }}
                    >
                      {(result.confidence.composite * 100).toFixed(0)}%
                    </span>
                    <span
                      style={{
                        color: "var(--rl-primary)",
                        fontSize: "var(--rl-fs-xs)",
                        marginLeft: "auto",
                      }}
                    >
                      Details &rarr;
                    </span>
                  </div>
                )}
              </div>
            </div>
            {/* UX3.1: Token Inspector Dock */}
            {viewMode === "traceable" && (
              <TokenInspectorDock
                token={selectedToken}
                onClear={handleClosePopover}
              />
            )}
          </div>

          {/* Right: Evidence Panel (UX4.3: unified Confidence + Receipts + Variants) */}
          <div
            style={panelStyle}
            role="region"
            aria-label="Evidence"
            data-testid="evidence-panel"
          >
            <div style={tabBarStyle}>
              <Tooltip
                content="Overall translation confidence with layer breakdown."
                position="bottom"
              >
                <div
                  data-testid="evidence-tab-confidence"
                  style={activeTab === "confidence" ? tabActiveStyle : tabStyle}
                  onClick={() => setActiveTab("confidence")}
                  role="tab"
                  tabIndex={0}
                  onKeyDown={(e) =>
                    e.key === "Enter" && setActiveTab("confidence")
                  }
                >
                  Confidence
                </div>
              </Tooltip>
              <Tooltip
                content="Evidence for how the rendering was produced: sources, rules, and token decisions."
                position="bottom"
              >
                <div
                  data-testid="evidence-tab-receipts"
                  style={activeTab === "receipts" ? tabActiveStyle : tabStyle}
                  onClick={() => setActiveTab("receipts")}
                  role="tab"
                  tabIndex={0}
                  onKeyDown={(e) =>
                    e.key === "Enter" && setActiveTab("receipts")
                  }
                >
                  Receipts
                </div>
              </Tooltip>
              <Tooltip
                content="Textual variants from selected witnesses (when available)."
                position="bottom"
              >
                <div
                  data-testid="evidence-tab-variants"
                  style={activeTab === "variants" ? tabActiveStyle : tabStyle}
                  onClick={() => setActiveTab("variants")}
                  role="tab"
                  tabIndex={0}
                  onKeyDown={(e) =>
                    e.key === "Enter" && setActiveTab("variants")
                  }
                >
                  Variants ({result.variants.length})
                </div>
              </Tooltip>
            </div>
            <div style={{ ...panelContentStyle, padding: 0 }}>
              {/* Confidence tab */}
              {activeTab === "confidence" && (
                <div style={{ padding: "16px" }}>
                  {(() => {
                    const na = getNextAction("confidence");
                    if (!na) return null;
                    return (
                      <div
                        data-testid="evidence-next-action"
                        style={{
                          padding: "8px 12px",
                          marginBottom: "12px",
                          backgroundColor: "rgba(96, 165, 250, 0.08)",
                          border: "1px solid rgba(96, 165, 250, 0.2)",
                          borderRadius: "4px",
                          fontSize: "var(--rl-fs-sm)",
                          color: "var(--rl-text-muted)",
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          flexWrap: "wrap",
                        }}
                      >
                        <span>{na.text}</span>
                      </div>
                    );
                  })()}
                  {result.confidence ? (
                    <div>
                      {/* Composite confidence with progress bar */}
                      <Tooltip
                        content="Overall confidence based on available evidence. Higher = more certain."
                        position="bottom"
                      >
                        <div
                          data-testid="confidence-composite"
                          style={{ marginBottom: "10px", cursor: "default" }}
                        >
                          <div
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                              marginBottom: "6px",
                            }}
                          >
                            <span
                              style={{
                                color: "var(--rl-text-muted)",
                                fontSize: "var(--rl-fs-sm)",
                                fontWeight: 500,
                              }}
                            >
                              Composite Confidence
                            </span>
                            <span
                              style={{
                                color: "var(--rl-text)",
                                fontWeight: 600,
                                fontSize: "15px",
                              }}
                            >
                              {(result.confidence.composite * 100).toFixed(0)}%
                            </span>
                          </div>
                          <div
                            data-testid="confidence-composite-bar"
                            style={{
                              height: "6px",
                              backgroundColor: "var(--rl-border-strong)",
                              borderRadius: "3px",
                              overflow: "hidden",
                            }}
                          >
                            <div
                              style={{
                                width: `${(result.confidence.composite * 100).toFixed(0)}%`,
                                height: "100%",
                                backgroundColor:
                                  result.confidence.composite >= 0.8
                                    ? "var(--rl-success)"
                                    : result.confidence.composite >= 0.6
                                      ? "var(--rl-warning)"
                                      : "var(--rl-error)",
                                transition: "width 0.3s",
                                borderRadius: "3px",
                              }}
                            />
                          </div>
                        </div>
                      </Tooltip>

                      {/* Layer breakdown */}
                      {result.confidence.layers &&
                      Object.values(result.confidence.layers).some(
                        (s) => s && typeof s.score === "number",
                      ) ? (
                        <div
                          style={{
                            display: "flex",
                            flexDirection: "column",
                            gap: "4px",
                          }}
                        >
                          {(
                            [
                              "textual",
                              "grammatical",
                              "lexical",
                              "interpretive",
                            ] as const
                          ).map((layer) => {
                            const score = result.confidence!.layers[layer];
                            if (!score || typeof score.score !== "number")
                              return null;
                            const pct = (score.score * 100).toFixed(0);
                            const isWeakest =
                              result.confidence!.weakest_layer === layer;
                            const barColor =
                              score.score >= 0.8
                                ? "var(--rl-success)"
                                : score.score >= 0.6
                                  ? "var(--rl-warning)"
                                  : "var(--rl-error)";

                            return (
                              <div
                                key={layer}
                                data-testid={`confidence-layer-${layer}`}
                                style={{
                                  display: "flex",
                                  alignItems: "center",
                                  gap: "8px",
                                  cursor: "pointer",
                                  padding: "2px 0",
                                  borderRadius: "3px",
                                  backgroundColor:
                                    confidenceDetailLayer === layer
                                      ? "rgba(96, 165, 250, 0.1)"
                                      : "transparent",
                                }}
                                onClick={() =>
                                  setConfidenceDetailLayer(
                                    confidenceDetailLayer === layer
                                      ? null
                                      : layer,
                                  )
                                }
                                role="button"
                                tabIndex={0}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter" || e.key === " ") {
                                    e.preventDefault();
                                    setConfidenceDetailLayer(
                                      confidenceDetailLayer === layer
                                        ? null
                                        : layer,
                                    );
                                  }
                                }}
                              >
                                <span
                                  style={{
                                    fontSize: "var(--rl-fs-xs)",
                                    color: isWeakest
                                      ? "var(--rl-warning)"
                                      : "var(--rl-text-dim)",
                                    width: "80px",
                                    textTransform: "capitalize",
                                    fontWeight: isWeakest ? 600 : 400,
                                  }}
                                >
                                  {layer}
                                  {isWeakest ? " *" : ""}
                                </span>
                                <div
                                  style={{
                                    flex: 1,
                                    height: "4px",
                                    backgroundColor: "var(--rl-border-strong)",
                                    borderRadius: "2px",
                                    overflow: "hidden",
                                  }}
                                >
                                  <div
                                    style={{
                                      width: `${pct}%`,
                                      height: "100%",
                                      backgroundColor: barColor,
                                      transition: "width 0.3s",
                                    }}
                                  />
                                </div>
                                <span
                                  style={{
                                    fontSize: "var(--rl-fs-xs)",
                                    color: isWeakest
                                      ? "var(--rl-warning)"
                                      : "var(--rl-text-muted)",
                                    width: "32px",
                                    textAlign: "right",
                                    fontWeight: isWeakest ? 600 : 400,
                                  }}
                                >
                                  {pct}%
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <div
                          style={{
                            fontSize: "var(--rl-fs-xs)",
                            color: "var(--rl-text-dim)",
                            fontStyle: "italic",
                            marginTop: "4px",
                          }}
                        >
                          Layer scores not provided by backend.
                        </div>
                      )}

                      {result.confidence.weakest_layer && (
                        <div
                          style={{
                            fontSize: "var(--rl-fs-xs)",
                            color: "var(--rl-warning)",
                            marginTop: "6px",
                          }}
                        >
                          Weakest: {result.confidence.weakest_layer}
                        </div>
                      )}

                      {/* Confidence detail panel */}
                      {confidenceDetailLayer &&
                        result.ledger &&
                        result.ledger.length > 0 && (
                          <ConfidenceDetailPanel
                            layer={confidenceDetailLayer}
                            ledger={result.ledger}
                            onTokenSelect={(pos) => {
                              setSelectedTokenPosition(pos);
                              for (const v of result.ledger!) {
                                const t = v.tokens.find(
                                  (tk) => tk.position === pos,
                                );
                                if (t) {
                                  setSelectedToken(t);
                                  break;
                                }
                              }
                            }}
                            onClose={() => setConfidenceDetailLayer(null)}
                          />
                        )}
                      {confidenceDetailLayer &&
                        (!result.ledger || result.ledger.length === 0) && (
                          <div
                            data-testid="confidence-detail-panel"
                            style={{
                              fontSize: "var(--rl-fs-sm)",
                              color: "var(--rl-text-dim)",
                              fontStyle: "italic",
                              padding: "12px 8px",
                              textAlign: "center",
                              marginTop: "8px",
                              backgroundColor: "var(--rl-bg-app)",
                              borderRadius: "6px",
                            }}
                          >
                            Token data requires Traceable mode. Re-translate in
                            Traceable to see per-token confidence.
                          </div>
                        )}
                    </div>
                  ) : (
                    <div
                      style={{
                        color: "var(--rl-text-dim)",
                        fontSize: "var(--rl-fs-base)",
                        textAlign: "center",
                        padding: "24px",
                      }}
                    >
                      No confidence data available for this translation.
                    </div>
                  )}
                </div>
              )}

              {/* Receipts tab */}
              {activeTab === "receipts" && (
                <div style={{ padding: "16px" }}>
                  {(() => {
                    const na = getNextAction("receipts");
                    if (!na) return null;
                    return (
                      <div
                        data-testid="evidence-next-action"
                        style={{
                          padding: "8px 12px",
                          marginBottom: "12px",
                          backgroundColor: "rgba(96, 165, 250, 0.08)",
                          border: "1px solid rgba(96, 165, 250, 0.2)",
                          borderRadius: "4px",
                          fontSize: "var(--rl-fs-sm)",
                          color: "var(--rl-text-muted)",
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          flexWrap: "wrap",
                        }}
                      >
                        <span>{na.text}</span>
                        {na.action && (
                          <button
                            data-testid="evidence-next-action-btn"
                            style={{
                              padding: "3px 10px",
                              fontSize: "var(--rl-fs-xs)",
                              backgroundColor: "transparent",
                              color: "var(--rl-primary)",
                              border: "1px solid var(--rl-primary)",
                              borderRadius: "3px",
                              cursor: "pointer",
                              whiteSpace: "nowrap",
                            }}
                            onClick={na.action}
                          >
                            {na.label}
                          </button>
                        )}
                      </div>
                    );
                  })()}
                  {viewMode === "readable" &&
                  result.ledger &&
                  result.ledger.length > 0 ? (
                    <div
                      style={{
                        color: "var(--rl-text-dim)",
                        fontSize: "var(--rl-fs-base)",
                        padding: "16px",
                      }}
                    >
                      <div style={{ marginBottom: "8px" }}>
                        Receipts are visible in Traceable view.
                      </div>
                      <span
                        style={{
                          color: "var(--rl-primary)",
                          cursor: "pointer",
                          textDecoration: "underline",
                          fontSize: "var(--rl-fs-sm)",
                        }}
                        onClick={() => {
                          setViewMode("traceable");
                        }}
                      >
                        Switch to Traceable view
                      </span>
                    </div>
                  ) : result.ledger && result.ledger.length > 0 ? (
                    <LedgerList ledgers={result.ledger} />
                  ) : result.mode === "readable" ? (
                    <div
                      style={{
                        color: "var(--rl-text-dim)",
                        fontSize: "var(--rl-fs-base)",
                        padding: "16px",
                      }}
                    >
                      <div style={{ marginBottom: "8px" }}>
                        Token ledger is available in Traceable mode.
                      </div>
                      <div
                        style={{
                          fontSize: "var(--rl-fs-sm)",
                          color: "var(--rl-border-strong)",
                          marginBottom: "12px",
                        }}
                      >
                        Results were generated in Readable mode. Re-translate in
                        Traceable to see per-token receipts.
                      </div>
                      <button
                        data-testid="receipts-cta-btn"
                        style={{
                          padding: "6px 14px",
                          fontSize: "var(--rl-fs-sm)",
                          backgroundColor: "transparent",
                          color: "var(--rl-primary)",
                          border: "1px solid var(--rl-primary)",
                          borderRadius: "4px",
                          cursor: "pointer",
                        }}
                        onClick={() => {
                          setMode("traceable");
                          setTimeout(() => handleTranslate(), 50);
                        }}
                      >
                        Re-translate in Traceable
                      </button>
                    </div>
                  ) : (
                    <div
                      style={{
                        color: "var(--rl-text-dim)",
                        fontSize: "var(--rl-fs-base)",
                        padding: "16px",
                      }}
                    >
                      <div style={{ marginBottom: "8px" }}>
                        No token ledger returned for this translation.
                      </div>
                      <div
                        style={{
                          fontSize: "var(--rl-fs-sm)",
                          color: "var(--rl-border-strong)",
                          marginBottom: "12px",
                        }}
                      >
                        The translator type may not support token-level
                        evidence. Try the traceable translator for per-token
                        receipts.
                      </div>
                      <button
                        data-testid="receipts-cta-btn"
                        style={{
                          padding: "6px 14px",
                          fontSize: "var(--rl-fs-sm)",
                          backgroundColor: "transparent",
                          color: "var(--rl-primary)",
                          border: "1px solid var(--rl-primary)",
                          borderRadius: "4px",
                          cursor: "pointer",
                        }}
                        onClick={() => {
                          setTranslator("traceable");
                          setMode("traceable");
                          setTimeout(() => handleTranslate(), 50);
                        }}
                      >
                        Try traceable translator
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Variants tab */}
              {activeTab === "variants" && (
                <div style={{ padding: "16px" }}>
                  {(() => {
                    const na = getNextAction("variants");
                    if (!na) return null;
                    return (
                      <div
                        data-testid="evidence-next-action"
                        style={{
                          padding: "8px 12px",
                          marginBottom: "12px",
                          backgroundColor: "rgba(96, 165, 250, 0.08)",
                          border: "1px solid rgba(96, 165, 250, 0.2)",
                          borderRadius: "4px",
                          fontSize: "var(--rl-fs-sm)",
                          color: "var(--rl-text-muted)",
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          flexWrap: "wrap",
                        }}
                      >
                        <span>{na.text}</span>
                        {na.link && (
                          <Link
                            to={na.link}
                            data-testid="evidence-next-action-btn"
                            style={{
                              padding: "3px 10px",
                              fontSize: "var(--rl-fs-xs)",
                              backgroundColor: "transparent",
                              color: "var(--rl-primary)",
                              border: "1px solid var(--rl-primary)",
                              borderRadius: "3px",
                              textDecoration: "none",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {na.label}
                          </Link>
                        )}
                      </div>
                    );
                  })()}
                  {result.variants.length === 0 && (
                    <div
                      style={{
                        color: "var(--rl-text-dim)",
                        fontSize: "var(--rl-fs-base)",
                        padding: "12px",
                        backgroundColor: "var(--rl-bg-app)",
                        borderRadius: "6px",
                        marginBottom: "12px",
                      }}
                    >
                      <div
                        style={{
                          marginBottom: "6px",
                          fontWeight: 500,
                          color: "var(--rl-text-muted)",
                        }}
                      >
                        No textual variants at this reference
                      </div>
                      <div
                        style={{
                          fontSize: "var(--rl-fs-sm)",
                          marginBottom: "12px",
                        }}
                      >
                        This passage has no variant readings in the installed
                        source packs. The SBLGNT spine text is the only attested
                        reading
                        {result.provenance?.sources_used?.length > 0
                          ? ` across ${result.provenance.sources_used.length} source(s): ${result.provenance.sources_used.join(", ")}.`
                          : "."}
                      </div>
                      <Link
                        to="/sources"
                        data-testid="variants-cta-btn"
                        style={{
                          display: "inline-block",
                          padding: "6px 14px",
                          fontSize: "var(--rl-fs-sm)",
                          backgroundColor: "transparent",
                          color: "var(--rl-primary)",
                          border: "1px solid var(--rl-primary)",
                          borderRadius: "4px",
                          textDecoration: "none",
                          cursor: "pointer",
                        }}
                      >
                        Manage Sources
                      </Link>
                    </div>
                  )}
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
              gridColumn:
                layoutMode === "mobile"
                  ? "span 1"
                  : layoutMode === "tablet"
                    ? "span 2"
                    : "span 3",
              position: "relative",
            }}
          >
            {loading ? (
              <div style={emptyStateStyle}>
                <div
                  style={{
                    fontSize: "var(--rl-fs-xl)",
                    marginBottom: "16px",
                    animation: "pulse 1.5s ease-in-out infinite",
                  }}
                >
                  Translating...
                </div>
                <div
                  style={{ color: "var(--rl-primary)", fontSize: "var(--rl-fs-base)" }}
                >
                  {reference}
                </div>
              </div>
            ) : !client ? (
              <div style={emptyStateStyle}>
                <div
                  style={{ fontSize: "var(--rl-fs-lg)", marginBottom: "12px" }}
                >
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
                <div
                  style={{
                    fontSize: "32px",
                    marginBottom: "12px",
                    opacity: 0.5,
                  }}
                >
                  {/* Greek alpha-omega glyph */}
                  &#x0391;&#x03A9;
                </div>
                <div
                  style={{
                    fontSize: "var(--rl-fs-lg)",
                    fontWeight: 600,
                    color: "var(--rl-text)",
                    marginBottom: "8px",
                  }}
                >
                  Explore Greek New Testament
                </div>
                <div
                  style={{
                    color: "var(--rl-text-muted)",
                    fontSize: "var(--rl-fs-base)",
                    marginBottom: "20px",
                    lineHeight: 1.5,
                  }}
                >
                  Enter a scripture reference above and press Enter to
                  translate.
                </div>

                {/* S8: Try a demo button */}
                <Tooltip
                  content="Load an example passage to see how Explore works."
                  position="bottom"
                >
                  <button
                    data-testid="demo-btn"
                    style={{
                      ...buttonStyle,
                      marginBottom: "24px",
                    }}
                    onClick={handleDemo}
                  >
                    Try a demo ({DEMO_REF})
                  </button>
                </Tooltip>

                {/* Example chips */}
                <div style={{ marginBottom: "16px" }}>
                  <div
                    style={{
                      fontSize: "var(--rl-fs-xs)",
                      color: "var(--rl-text-dim)",
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
                          e.currentTarget.style.backgroundColor =
                            "var(--rl-border-strong)";
                          e.currentTarget.style.color = "var(--rl-text)";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor =
                            "var(--rl-border-strong)";
                          e.currentTarget.style.color = "var(--rl-text-muted)";
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
                        fontSize: "var(--rl-fs-xs)",
                        color: "var(--rl-text-dim)",
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
                          style={{ ...chipStyle, borderColor: "var(--rl-primary)" }}
                          onClick={() => {
                            setReference(ref);
                            setTimeout(() => handleTranslate(), 100);
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.backgroundColor =
                              "var(--rl-primary)";
                            e.currentTarget.style.color = "white";
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.backgroundColor =
                              "var(--rl-border-strong)";
                            e.currentTarget.style.color =
                              "var(--rl-text-muted)";
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
        <div data-testid="token-popover">
          <TokenReceiptPopover
            token={selectedToken}
            anchorEl={popoverAnchor}
            onClose={handleClosePopover}
            onViewFullLedger={handleViewFullLedger}
          />
        </div>
      )}

      {/* S8: Demo nudge — appears once after demo, suggests Traceable */}
      {result &&
        isDemoResult &&
        !demoNudgeDismissed &&
        viewMode === "readable" && (
          <div
            data-testid="demo-nudge"
            style={{
              position: "fixed",
              bottom: "24px",
              right: "24px",
              backgroundColor: "var(--rl-bg-card)",
              border: "1px solid var(--rl-primary)",
              borderRadius: "8px",
              padding: "16px 20px",
              boxShadow: "0 4px 20px rgba(0, 0, 0, 0.4)",
              zIndex: 1500,
              maxWidth: "340px",
            }}
          >
            <div
              style={{
                fontSize: "var(--rl-fs-base)",
                color: "var(--rl-text)",
                marginBottom: "12px",
              }}
            >
              Want to see how each word was translated? Switch to{" "}
              <strong>Traceable</strong> to see token mapping and receipts.
            </div>
            <div style={{ display: "flex", gap: "8px" }}>
              <Tooltip
                content="Switch to Traceable to see token mapping and receipts."
                position="top"
              >
                <button
                  data-testid="demo-nudge-accept"
                  style={{
                    padding: "6px 14px",
                    fontSize: "var(--rl-fs-sm)",
                    backgroundColor: "var(--rl-primary)",
                    color: "white",
                    border: "none",
                    borderRadius: "4px",
                    cursor: "pointer",
                  }}
                  onClick={handleAcceptNudge}
                >
                  Switch to Traceable
                </button>
              </Tooltip>
              <button
                data-testid="demo-nudge-dismiss"
                style={{
                  padding: "6px 14px",
                  fontSize: "var(--rl-fs-sm)",
                  backgroundColor: "transparent",
                  color: "var(--rl-text-muted)",
                  border: "1px solid var(--rl-border-strong)",
                  borderRadius: "4px",
                  cursor: "pointer",
                }}
                onClick={handleDismissNudge}
              >
                Maybe later
              </button>
            </div>
          </div>
        )}

      {/* S7: Compare Modal */}
      {showCompareModal && result && client && (
        <CompareModal
          client={client}
          reference={result.reference}
          sessionId={settings.sessionId}
          resultA={result}
          onClose={() => {
            setShowCompareModal(false);
            // UX3.5: Return focus to Compare button
            requestAnimationFrame(() => compareBtnRef.current?.focus());
          }}
        />
      )}
    </div>
  );
}

export default PassageWorkspace;
