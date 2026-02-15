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
  ONBOARDING_DISMISSED_KEY,
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
import { validateRef, nextRef, prevRef } from "../utils/referenceNav";
import { Tooltip } from "../components/Tooltip";
import { ReferenceBar } from "../components/ReferenceBar";
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
  border: "1px solid var(--rl-border)",
  borderRadius: "var(--rl-radius-md)",
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
  backgroundColor: "var(--rl-primary)",
  color: "white",
  border: "none",
  borderRadius: "var(--rl-radius-md)",
  cursor: "pointer",
  letterSpacing: "0.02em",
};

const toggleButtonStyle: React.CSSProperties = {
  padding: "6px 12px",
  fontSize: "var(--rl-fs-sm)",
  backgroundColor: "var(--rl-border-strong)",
  color: "var(--rl-text-muted)",
  border: "1px solid var(--rl-border-strong)",
  borderRadius: "var(--rl-radius-md)",
  cursor: "pointer",
};

const toggleActiveStyle: React.CSSProperties = {
  ...toggleButtonStyle,
  backgroundColor: "transparent",
  color: "var(--rl-link)",
  borderColor: "var(--rl-link)",
};

// UX3.2: workspaceStyle is now computed inside the component for responsive layout.
// See getWorkspaceStyle() below.

type LayoutMode = "mobile" | "tablet" | "desktop";

const panelStyle: React.CSSProperties = {
  backgroundColor: "var(--rl-bg-card)",
  border: "1px solid var(--rl-border)",
  borderRadius: "var(--rl-radius-lg)",
  overflow: "hidden",
  display: "flex",
  flexDirection: "column",
};

const panelHeaderStyle: React.CSSProperties = {
  padding: "12px 16px",
  borderBottom: "1px solid var(--rl-border)",
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
  borderRadius: "var(--rl-radius-md)",
  padding: "16px",
  marginBottom: "12px",
};

const styleChipStyle: React.CSSProperties = {
  display: "inline-block",
  padding: "2px 8px",
  borderRadius: "var(--rl-radius-sm)",
  fontSize: "var(--rl-fs-xs)",
  fontWeight: 600,
  backgroundColor: "var(--rl-border-strong)",
  color: "var(--rl-text-muted)",
  marginRight: "8px",
};

const tabBarStyle: React.CSSProperties = {
  display: "flex",
  borderBottom: "1px solid var(--rl-border)",
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
  color: "var(--rl-link)",
  borderBottom: "2px solid var(--rl-link)",
};

const legendStyle: React.CSSProperties = {
  display: "flex",
  gap: "16px",
  padding: "8px 16px",
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "var(--rl-radius-md)",
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

const recentItemStyle: React.CSSProperties = {
  padding: "8px 12px",
  fontSize: "var(--rl-fs-base)",
  color: "var(--rl-text)",
  cursor: "pointer",
  borderBottom: "1px solid var(--rl-border)",
};

const disabledToggleStyle: React.CSSProperties = {
  padding: "6px 12px",
  fontSize: "var(--rl-fs-sm)",
  backgroundColor: "var(--rl-bg-card)",
  color: "var(--rl-border-strong)",
  border: "1px solid var(--rl-border-strong)",
  borderRadius: "var(--rl-radius-md)",
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
    mode: TranslationMode;
    translator: TranslatorType;
    label: string;
    description: string;
  }
> = {
  reader: {
    viewMode: "readable",
    density: "comfortable",
    evidenceTab: "confidence",
    mode: "readable",
    translator: "literal",
    label: "Reader",
    description: "Clean English for reading",
  },
  translator: {
    viewMode: "traceable",
    density: "comfortable",
    evidenceTab: "receipts",
    mode: "traceable",
    translator: "traceable",
    label: "Translator",
    description: "Token-level mapping and receipts",
  },
  "text-critic": {
    viewMode: "traceable",
    density: "compact",
    evidenceTab: "variants",
    mode: "traceable",
    translator: "traceable",
    label: "Text Critic",
    description: "Variant analysis and apparatus",
  },
};

// A.2: Panel microcopy keyed to study mode
const PANEL_MICROCOPY: Record<StudyMode, { greek: string; rendering: string }> =
  {
    reader: {
      greek: "The original Greek from the SBLGNT critical text.",
      rendering:
        "English translation for reading. Switch to Traceable for word-level detail.",
    },
    translator: {
      greek:
        "Source text with morphological data. Click tokens to see alignment.",
      rendering:
        "Token-mapped English. Click words for receipts and alignment evidence.",
    },
    "text-critic": {
      greek:
        "Base text (SBLGNT). Compare against manuscript variants in Evidence.",
      rendering:
        "Rendered translation. Use the Evidence panel for variant analysis.",
    },
    "": {
      greek: "Greek text from the SBLGNT critical edition.",
      rendering: "English rendering from the selected translator.",
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
    borderRadius: "var(--rl-radius-sm)",
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
        ? "var(--rl-warning-text)"
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

  const handleStudyModeChange = useCallback((sm: StudyMode) => {
    setStudyMode(sm);
    try {
      localStorage.setItem(STUDY_MODE_KEY, sm);
    } catch {
      // Ignore storage errors
    }
    if (sm && sm in STUDY_MODE_PRESETS) {
      const preset = STUDY_MODE_PRESETS[sm as Exclude<StudyMode, "">];
      setViewMode(preset.viewMode);
      setTokenDensity(preset.density);
      setMode(preset.mode);
      setTranslator(preset.translator);
      try {
        localStorage.setItem(TOKEN_DENSITY_KEY, preset.density);
      } catch {
        // Ignore
      }
      setActiveTab(preset.evidenceTab);
    }
  }, []);

  // A.1: When user manually changes mode or translator, switch to Custom
  const handleManualModeChange = useCallback(
    (newMode: TranslationMode) => {
      setMode(newMode);
      if (studyMode) {
        setStudyMode("");
        try {
          localStorage.setItem(STUDY_MODE_KEY, "");
        } catch {
          /* */
        }
      }
    },
    [studyMode],
  );

  const handleManualTranslatorChange = useCallback(
    (newTr: TranslatorType) => {
      setTranslator(newTr);
      if (studyMode) {
        setStudyMode("");
        try {
          localStorage.setItem(STUDY_MODE_KEY, "");
        } catch {
          /* */
        }
      }
    },
    [studyMode],
  );

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

  // A.4: Onboarding dismissed state
  const [onboardingDismissed, setOnboardingDismissed] = useState(() => {
    try {
      return localStorage.getItem(ONBOARDING_DISMISSED_KEY) === "true";
    } catch {
      return false;
    }
  });

  const handleDismissOnboarding = useCallback(() => {
    setOnboardingDismissed(true);
    try {
      localStorage.setItem(ONBOARDING_DISMISSED_KEY, "true");
    } catch {
      // Ignore
    }
  }, []);

  // Sprint 17: Recent references
  const [recentRefs, setRecentRefs] = useState<string[]>([]);
  // UX4.1: Orientation strip recent refs dropdown
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

  // A.3: Compute ambiguous tokens (lexical confidence < 0.70)
  const ambiguousTokens = useMemo(() => {
    if (!result?.ledger) return [];
    const allTokens = result.ledger.flatMap((v) => v.tokens);
    return allTokens
      .filter((t) => t.confidence && t.confidence.lexical < 0.7)
      .sort((a, b) => a.confidence.lexical - b.confidence.lexical)
      .slice(0, 5);
  }, [result?.ledger]);

  // A.3: Click handler for ambiguity pill
  const handleAmbiguityPillClick = useCallback((token: TokenLedger) => {
    setSelectedTokenPosition(token.position);
    setSelectedToken(token);
    setPopoverAnchor(null);
    setActiveTab("confidence");
  }, []);

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
  const handleTranslate = useCallback(
    async (refOverride?: string) => {
      const ref = (refOverride || reference).trim();
      if (!client || !ref) return;

      setLoading(true);
      setError(null);
      setResult(null);
      // S5/S6: Clear selection states on new translate
      setSelectedTokenPosition(null);
      setSelectedToken(null);
      setPopoverAnchor(null);
      setConfidenceDetailLayer(null);
      setIsDemoResult(false);

      try {
        const response = await client.translate({
          reference: ref,
          mode,
          session_id: settings.sessionId,
          translator,
        });

        if (isGateResponse(response)) {
          navigate("/gate", {
            state: { gate: response, originalReference: ref },
          });
        } else {
          setResult(response);
          // Sprint 26 (UX1): Sync viewMode to the result's actual mode
          // so users see traceable view when they requested traceable
          setViewMode(response.mode === "traceable" ? "traceable" : "readable");
          // Sprint 17: Save successful translation to recent refs
          saveToRecent(ref);
          // Sync URL with translated state
          updateUrlParams(ref, mode, translator);
        }
      } catch (err) {
        setError(createApiErrorDetail("POST", "/translate", err));
      } finally {
        setLoading(false);
      }
    },
    [
      client,
      reference,
      mode,
      translator,
      settings.sessionId,
      navigate,
      saveToRecent,
      updateUrlParams,
    ],
  );

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
      const tagName = (e.target as HTMLElement)?.tagName;
      const isInInput = ["INPUT", "SELECT", "TEXTAREA"].includes(tagName);
      const isRefInput =
        (e.target as HTMLElement)?.dataset?.testid === "ref-input";

      // `/` focuses ref input (when not in an input/select/textarea)
      if (e.key === "/" && !isInInput) {
        e.preventDefault();
        (
          document.querySelector('[data-testid="ref-input"]') as HTMLElement
        )?.focus();
      }

      // Cmd/Ctrl+L focuses ref input and selects all text
      const isMac = navigator.platform.toUpperCase().indexOf("MAC") >= 0;
      const modKey = isMac ? e.metaKey : e.ctrlKey;
      if (modKey && e.key === "l" && (!isInInput || isRefInput)) {
        e.preventDefault();
        const input = document.querySelector(
          '[data-testid="ref-input"]',
        ) as HTMLInputElement;
        input?.focus();
        input?.select();
      }

      // Alt+Left -> Previous verse (not when in input/textarea, except ref-input)
      if (e.altKey && e.key === "ArrowLeft" && (!isInInput || isRefInput)) {
        e.preventDefault();
        const prev = prevRef(reference);
        if (prev) {
          setReference(prev);
          handleTranslate(prev);
        }
      }

      // Alt+Right -> Next verse (not when in input/textarea, except ref-input)
      if (e.altKey && e.key === "ArrowRight" && (!isInInput || isRefInput)) {
        e.preventDefault();
        const next = nextRef(reference);
        if (next) {
          setReference(next);
          handleTranslate(next);
        }
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
  }, [
    showCompareModal,
    selectedToken,
    handleClosePopover,
    reference,
    handleTranslate,
  ]);

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
        if (!result.ledger || result.ledger.length === 0) {
          const reasons: string[] = [];
          if (result.mode !== "traceable")
            reasons.push("mode was " + result.mode);
          if (result.translator_type !== "traceable")
            reasons.push(
              result.translator_type + " translator lacks per-token data",
            );
          const explanation =
            reasons.length > 0
              ? reasons.join("; ") + "."
              : "No per-token data returned.";
          return {
            text:
              explanation +
              " Re-translate with Traceable mode + translator for receipts.",
            action: () => {
              setMode("traceable");
              setTranslator("traceable");
              setTimeout(() => handleTranslate(), 50);
            },
            label: "Re-translate as Traceable",
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
      <div
        style={{
          position: "relative",
          zIndex: 1,
          display: "flex",
          flexDirection: "column" as const,
          flex: 1,
          overflow: "hidden",
        }}
      >
        {/* Toolbar */}
        <div style={toolbarStyle}>
          {/* Reference input with recent refs dropdown + nav buttons */}
          <div
            style={{
              ...inputGroupStyle,
              position: "relative",
              minWidth: "280px",
            }}
          >
            <label style={labelStyle}>Reference</label>
            <ReferenceBar
              reference={reference}
              onReferenceChange={setReference}
              onNavigate={(ref) => handleTranslate(ref)}
              loading={loading}
              recentRefs={recentRefs}
            />
          </div>

          {/* A.1: Study Mode chips — primary control */}
          <div style={inputGroupStyle} data-testid="study-mode-chips">
            <label style={labelStyle}>Study Mode</label>
            <div style={{ display: "flex", gap: "2px" }}>
              {(
                Object.entries(STUDY_MODE_PRESETS) as [
                  Exclude<StudyMode, "">,
                  (typeof STUDY_MODE_PRESETS)[Exclude<StudyMode, "">],
                ][]
              ).map(([key, preset]) => (
                <Tooltip
                  key={key}
                  content={preset.description}
                  position="bottom"
                >
                  <button
                    data-testid={`study-chip-${key}`}
                    aria-label={`${preset.label} study mode`}
                    aria-pressed={studyMode === key}
                    style={{
                      padding: "6px 14px",
                      fontSize: "var(--rl-fs-sm)",
                      fontWeight: 500,
                      border: "1px solid",
                      cursor: "pointer",
                      borderColor:
                        studyMode === key
                          ? "var(--rl-link)"
                          : "var(--rl-border-strong)",
                      backgroundColor:
                        studyMode === key
                          ? "var(--rl-link)"
                          : "var(--rl-border-strong)",
                      color:
                        studyMode === key ? "white" : "var(--rl-text-muted)",
                      borderRadius:
                        key === "reader"
                          ? "var(--rl-radius-sm) 0 0 var(--rl-radius-sm)"
                          : key === "text-critic"
                            ? "0"
                            : "0",
                      transition:
                        "background-color var(--rl-transition-fast), border-color var(--rl-transition-fast)",
                    }}
                    onClick={() => handleStudyModeChange(key)}
                  >
                    {preset.label}
                  </button>
                </Tooltip>
              ))}
              <Tooltip
                content="Manual control over request mode and translator."
                position="bottom"
              >
                <button
                  data-testid="study-chip-custom"
                  aria-label="Custom study mode"
                  aria-pressed={studyMode === ""}
                  style={{
                    padding: "6px 14px",
                    fontSize: "var(--rl-fs-sm)",
                    fontWeight: 500,
                    border: "1px solid",
                    cursor: "pointer",
                    borderColor:
                      studyMode === ""
                        ? "var(--rl-link)"
                        : "var(--rl-border-strong)",
                    backgroundColor:
                      studyMode === ""
                        ? "var(--rl-link)"
                        : "var(--rl-border-strong)",
                    color: studyMode === "" ? "white" : "var(--rl-text-muted)",
                    borderRadius: "0 var(--rl-radius-sm) var(--rl-radius-sm) 0",
                    transition:
                      "background-color var(--rl-transition-fast), border-color var(--rl-transition-fast)",
                  }}
                  onClick={() => handleStudyModeChange("")}
                >
                  Custom
                </button>
              </Tooltip>
            </div>
          </div>

          {/* A.1: Request Mode + Translator dropdowns — only visible in Custom mode */}
          {studyMode === "" && (
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
                    onChange={(e) =>
                      handleManualModeChange(e.target.value as TranslationMode)
                    }
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
                      handleManualTranslatorChange(
                        e.target.value as TranslatorType,
                      )
                    }
                    aria-label="Translator type"
                  >
                    <option value="literal">Literal</option>
                    <option value="fluent">Fluent</option>
                    <option value="traceable">Traceable</option>
                  </select>
                </Tooltip>
              </div>
            </div>
          )}

          <Tooltip
            content="Translate the selected reference using the current settings."
            position="bottom"
            wrapFocus={!client || loading || !reference.trim()}
          >
            <button
              data-testid="primary-cta"
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
              onClick={() => handleTranslate()}
              disabled={!client || loading || !reference.trim()}
            >
              {loading ? "Translating..." : "Translate"}
            </button>
          </Tooltip>

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
              borderRadius: "var(--rl-radius-md)",
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
                    : "var(--rl-link)",
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
                      border: "1px solid var(--rl-border)",
                      borderRadius: "var(--rl-radius-md)",
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

        {/* A.3: Ambiguities strip — tokens with low lexical confidence */}
        {result && ambiguousTokens.length > 0 && studyMode !== "reader" && (
          <div
            data-testid="ambiguities-strip"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "6px 12px",
              marginBottom: "8px",
              backgroundColor: "rgba(251, 191, 36, 0.06)",
              border: "1px solid rgba(251, 191, 36, 0.2)",
              borderRadius: "var(--rl-radius-md)",
              fontSize: "var(--rl-fs-xs)",
              flexWrap: "wrap",
            }}
          >
            <span
              style={{
                color: "var(--rl-warning-text)",
                fontWeight: 600,
                whiteSpace: "nowrap",
              }}
            >
              Ambiguities
            </span>
            {ambiguousTokens.map((token) => (
              <button
                key={token.position}
                data-testid={`ambiguity-pill-${token.position}`}
                onClick={() => handleAmbiguityPillClick(token)}
                style={{
                  padding: "3px 10px",
                  fontSize: "var(--rl-fs-xs)",
                  backgroundColor: "rgba(251, 191, 36, 0.12)",
                  color: "var(--rl-text)",
                  border: "1px solid rgba(251, 191, 36, 0.3)",
                  borderRadius: "var(--rl-radius-full)",
                  cursor: "pointer",
                  transition: "background-color var(--rl-transition-fast)",
                  whiteSpace: "nowrap",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor =
                    "rgba(251, 191, 36, 0.25)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor =
                    "rgba(251, 191, 36, 0.12)";
                }}
              >
                <span style={{ fontWeight: 500 }}>
                  {token.gloss.replace(/^\[|\]$/g, "")}
                </span>
                <span
                  style={{
                    marginLeft: "4px",
                    color: "var(--rl-text-dim)",
                  }}
                >
                  {token.lemma || token.surface}
                </span>
                <span
                  style={{
                    marginLeft: "4px",
                    color: "var(--rl-warning)",
                    fontWeight: 600,
                  }}
                >
                  {(token.confidence.lexical * 100).toFixed(0)}%
                </span>
              </button>
            ))}
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
                              ? "var(--rl-confidence-high)"
                              : item.risk < 0.6
                                ? "var(--rl-confidence-mid)"
                                : "var(--rl-confidence-low)",
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
              <div style={panelHeaderStyle}>
                <span>Greek Source</span>
                <div
                  style={{
                    fontSize: "var(--rl-fs-xs)",
                    fontWeight: 400,
                    color: "var(--rl-text-dim)",
                    textTransform: "none",
                    marginTop: "2px",
                  }}
                >
                  {PANEL_MICROCOPY[studyMode].greek}
                </div>
              </div>
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
                  <div>
                    <span>Rendering</span>
                    <div
                      style={{
                        fontSize: "var(--rl-fs-xs)",
                        fontWeight: 400,
                        color: "var(--rl-text-dim)",
                        textTransform: "none",
                        marginTop: "2px",
                      }}
                    >
                      {PANEL_MICROCOPY[studyMode].rendering}
                    </div>
                  </div>
                  {/* UX2.1: Density toggle + View toggle */}
                  <div
                    style={{
                      display: "flex",
                      gap: "8px",
                      alignItems: "center",
                    }}
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
                              borderRadius:
                                "var(--rl-radius-sm) 0 0 var(--rl-radius-sm)",
                              cursor: "pointer",
                              backgroundColor:
                                tokenDensity === "compact"
                                  ? "var(--rl-link)"
                                  : "var(--rl-border-strong)",
                              color:
                                tokenDensity === "compact"
                                  ? "white"
                                  : "var(--rl-text-muted)",
                              borderColor:
                                tokenDensity === "compact"
                                  ? "var(--rl-link)"
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
                              borderRadius:
                                "0 var(--rl-radius-sm) var(--rl-radius-sm) 0",
                              cursor: "pointer",
                              backgroundColor:
                                tokenDensity === "comfortable"
                                  ? "var(--rl-link)"
                                  : "var(--rl-border-strong)",
                              color:
                                tokenDensity === "comfortable"
                                  ? "white"
                                  : "var(--rl-text-muted)",
                              borderColor:
                                tokenDensity === "comfortable"
                                  ? "var(--rl-link)"
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
                            borderRadius:
                              "var(--rl-radius-sm) 0 0 var(--rl-radius-sm)",
                            cursor: "pointer",
                            backgroundColor:
                              viewMode === "readable"
                                ? "var(--rl-link)"
                                : "var(--rl-border-strong)",
                            color:
                              viewMode === "readable"
                                ? "white"
                                : "var(--rl-text-muted)",
                            borderColor:
                              viewMode === "readable"
                                ? "var(--rl-link)"
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
                            borderRadius:
                              "0 var(--rl-radius-sm) var(--rl-radius-sm) 0",
                            cursor: "pointer",
                            backgroundColor:
                              viewMode === "traceable"
                                ? "var(--rl-link)"
                                : "var(--rl-border-strong)",
                            color:
                              viewMode === "traceable"
                                ? "white"
                                : "var(--rl-text-muted)",
                            borderColor:
                              viewMode === "traceable"
                                ? "var(--rl-link)"
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
                      <span style={styleChipStyle}>
                        {result.translator_type}
                      </span>
                      {viewMode !== result.mode ? (
                        <Tooltip
                          content={
                            viewMode === "traceable" &&
                            result.mode === "readable"
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
                            backgroundColor: "var(--rl-warning-bg)",
                            borderRadius: "var(--rl-radius-md)",
                            border: "1px solid var(--rl-warning)",
                          }}
                        >
                          No token data available. These results were generated
                          in Readable mode.{" "}
                          <span
                            style={{
                              color: "var(--rl-link)",
                              cursor: "pointer",
                              textDecoration: "underline",
                            }}
                            onClick={() => {
                              setMode("traceable");
                              setTranslator("traceable");
                              setTimeout(() => handleTranslate(), 50);
                            }}
                          >
                            Re-translate as Traceable
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
                              color: "var(--rl-link)",
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
                          color: "var(--rl-link)",
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
                    style={
                      activeTab === "confidence" ? tabActiveStyle : tabStyle
                    }
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
                  content="Manuscript/readings differences (apparatus), not alternate interpretations."
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
                    Textual Variants ({result.variants.length})
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
                            borderRadius: "var(--rl-radius-md)",
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
                                {(result.confidence.composite * 100).toFixed(0)}
                                %
                              </span>
                            </div>
                            <div
                              data-testid="confidence-composite-bar"
                              style={{
                                height: "6px",
                                backgroundColor: "var(--rl-border-strong)",
                                borderRadius: "var(--rl-radius-sm)",
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
                                  borderRadius: "var(--rl-radius-sm)",
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
                                    borderRadius: "var(--rl-radius-sm)",
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
                                      backgroundColor:
                                        "var(--rl-border-strong)",
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
                                borderRadius: "var(--rl-radius-md)",
                              }}
                            >
                              {result.mode === "traceable" &&
                              result.translator_type !== "traceable" ? (
                                <>
                                  The {result.translator_type} translator does
                                  not provide per-token data.{" "}
                                  <span
                                    style={{
                                      color: "var(--rl-link)",
                                      cursor: "pointer",
                                      textDecoration: "underline",
                                      fontStyle: "normal",
                                    }}
                                    onClick={() => {
                                      setTranslator("traceable");
                                      setTimeout(() => handleTranslate(), 50);
                                    }}
                                  >
                                    Switch to Traceable translator
                                  </span>
                                </>
                              ) : (
                                <>
                                  {result.mode !== "traceable" &&
                                    "This result was generated in " +
                                      result.mode +
                                      " mode. "}
                                  Per-token data requires Traceable mode and
                                  translator.{" "}
                                  <span
                                    style={{
                                      color: "var(--rl-link)",
                                      cursor: "pointer",
                                      textDecoration: "underline",
                                      fontStyle: "normal",
                                    }}
                                    onClick={() => {
                                      setMode("traceable");
                                      setTranslator("traceable");
                                      setTimeout(() => handleTranslate(), 50);
                                    }}
                                  >
                                    Re-translate as Traceable
                                  </span>
                                </>
                              )}
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
                            borderRadius: "var(--rl-radius-md)",
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
                                color: "var(--rl-link)",
                                border: "1px solid var(--rl-link)",
                                borderRadius: "var(--rl-radius-sm)",
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
                            color: "var(--rl-link)",
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
                          Results were generated in Readable mode. Re-translate
                          with Traceable mode and translator for per-token
                          receipts.
                        </div>
                        <button
                          data-testid="receipts-cta-btn"
                          style={{
                            padding: "6px 14px",
                            fontSize: "var(--rl-fs-sm)",
                            backgroundColor: "transparent",
                            color: "var(--rl-link)",
                            border: "1px solid var(--rl-link)",
                            borderRadius: "var(--rl-radius-md)",
                            cursor: "pointer",
                          }}
                          onClick={() => {
                            setMode("traceable");
                            setTranslator("traceable");
                            setTimeout(() => handleTranslate(), 50);
                          }}
                        >
                          Re-translate as Traceable
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
                            color: "var(--rl-link)",
                            border: "1px solid var(--rl-link)",
                            borderRadius: "var(--rl-radius-md)",
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
                            borderRadius: "var(--rl-radius-md)",
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
                                color: "var(--rl-link)",
                                border: "1px solid var(--rl-link)",
                                borderRadius: "var(--rl-radius-sm)",
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
                          borderRadius: "var(--rl-radius-md)",
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
                          source packs. The SBLGNT spine text is the only
                          attested reading
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
                            color: "var(--rl-link)",
                            border: "1px solid var(--rl-link)",
                            borderRadius: "var(--rl-radius-md)",
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
                    style={{
                      color: "var(--rl-link)",
                      fontSize: "var(--rl-fs-base)",
                    }}
                  >
                    {reference}
                  </div>
                </div>
              ) : !client ? (
                <div style={emptyStateStyle}>
                  <div
                    style={{
                      fontSize: "var(--rl-fs-lg)",
                      marginBottom: "12px",
                    }}
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
                <div style={emptyStateStyle} data-testid="empty-state">
                  {/* A.4: 3-step onboarding */}
                  {!onboardingDismissed ? (
                    <>
                      <div
                        aria-hidden="true"
                        style={{
                          fontSize: "24px",
                          marginBottom: "8px",
                          color: "var(--rl-text-muted)",
                          opacity: 0.6,
                        }}
                      >
                        &#x0391;&#x03A9;
                      </div>
                      <div
                        style={{
                          fontSize: "var(--rl-fs-lg)",
                          fontWeight: 600,
                          color: "var(--rl-text)",
                          marginBottom: "16px",
                        }}
                      >
                        Explore Greek New Testament
                      </div>

                      {/* 3-step guide */}
                      <div
                        data-testid="onboarding-steps"
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: "12px",
                          width: "100%",
                          maxWidth: "380px",
                          marginBottom: "20px",
                        }}
                      >
                        {[
                          {
                            step: 1,
                            title: "Type a reference",
                            hint: 'e.g., "John 3:16" or "Rom 8:28"',
                            done: reference.trim().length > 0,
                          },
                          {
                            step: 2,
                            title: "Choose a study mode",
                            hint: "Reader, Translator, or Text Critic",
                            done: studyMode !== "",
                          },
                          {
                            step: 3,
                            title: "Click Translate",
                            hint: "Or press Enter in the reference field",
                            done: false,
                          },
                        ].map((s) => (
                          <div
                            key={s.step}
                            data-testid={`onboarding-step-${s.step}`}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "12px",
                              padding: "10px 14px",
                              backgroundColor: s.done
                                ? "rgba(52, 211, 153, 0.08)"
                                : "var(--rl-bg-card)",
                              border: `1px solid ${s.done ? "var(--rl-success)" : "var(--rl-border)"}`,
                              borderRadius: "var(--rl-radius-md)",
                              textAlign: "left",
                            }}
                          >
                            <div
                              style={{
                                width: "28px",
                                height: "28px",
                                borderRadius: "50%",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                fontSize: "var(--rl-fs-sm)",
                                fontWeight: 600,
                                flexShrink: 0,
                                backgroundColor: s.done
                                  ? "var(--rl-success)"
                                  : "var(--rl-border-strong)",
                                color: s.done
                                  ? "white"
                                  : "var(--rl-text-muted)",
                              }}
                            >
                              {s.done ? "\u2713" : s.step}
                            </div>
                            <div>
                              <div
                                style={{
                                  fontSize: "var(--rl-fs-base)",
                                  fontWeight: 500,
                                  color: "var(--rl-text)",
                                }}
                              >
                                {s.title}
                              </div>
                              <div
                                style={{
                                  fontSize: "var(--rl-fs-xs)",
                                  color: "var(--rl-text-dim)",
                                }}
                              >
                                {s.hint}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Demo + example chips */}
                      <Tooltip
                        content="Load an example passage to see how Explore works."
                        position="bottom"
                      >
                        <button
                          data-testid="demo-btn"
                          style={{
                            ...buttonStyle,
                            marginBottom: "16px",
                          }}
                          onClick={handleDemo}
                        >
                          Try a demo ({DEMO_REF})
                        </button>
                      </Tooltip>

                      <div style={{ marginBottom: "16px" }}>
                        <div
                          style={{
                            fontSize: "var(--rl-fs-xs)",
                            color: "var(--rl-text-dim)",
                            marginBottom: "8px",
                            textTransform: "uppercase",
                          }}
                        >
                          Or try an example
                        </div>
                        <div style={exampleChipsStyle}>
                          {EXAMPLE_REFS.map((ref) => (
                            <button
                              key={ref}
                              style={chipStyle}
                              onClick={() => {
                                setReference(ref);
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
                                e.currentTarget.style.color =
                                  "var(--rl-text-muted)";
                              }}
                            >
                              {ref}
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Recent refs */}
                      {recentRefs.length > 0 && (
                        <div style={{ marginBottom: "12px" }}>
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
                                style={{
                                  ...chipStyle,
                                  borderColor: "var(--rl-link)",
                                }}
                                onClick={() => {
                                  setReference(ref);
                                  setTimeout(() => handleTranslate(), 100);
                                }}
                                onMouseEnter={(e) => {
                                  e.currentTarget.style.backgroundColor =
                                    "var(--rl-link)";
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

                      {/* Don't show again */}
                      <button
                        data-testid="onboarding-dismiss"
                        onClick={handleDismissOnboarding}
                        style={{
                          fontSize: "var(--rl-fs-xs)",
                          color: "var(--rl-text-dim)",
                          backgroundColor: "transparent",
                          border: "none",
                          cursor: "pointer",
                          padding: "4px 8px",
                          textDecoration: "underline",
                        }}
                      >
                        Don&apos;t show this guide again
                      </button>
                    </>
                  ) : (
                    /* Minimal empty state after onboarding dismissed */
                    <>
                      <div
                        style={{
                          fontSize: "var(--rl-fs-lg)",
                          fontWeight: 600,
                          color: "var(--rl-text)",
                          marginBottom: "8px",
                        }}
                      >
                        Enter a reference to begin
                      </div>
                      <Tooltip
                        content="Load an example passage to see how Explore works."
                        position="bottom"
                      >
                        <button
                          data-testid="demo-btn"
                          style={{
                            ...buttonStyle,
                            marginBottom: "16px",
                          }}
                          onClick={handleDemo}
                        >
                          Try a demo ({DEMO_REF})
                        </button>
                      </Tooltip>
                      <div style={exampleChipsStyle}>
                        {EXAMPLE_REFS.map((ref) => (
                          <button
                            key={ref}
                            style={chipStyle}
                            onClick={() => {
                              setReference(ref);
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
                              e.currentTarget.style.color =
                                "var(--rl-text-muted)";
                            }}
                          >
                            {ref}
                          </button>
                        ))}
                      </div>
                    </>
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
                border: "1px solid var(--rl-link)",
                borderRadius: "var(--rl-radius-lg)",
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
                      borderRadius: "var(--rl-radius-md)",
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
                    borderRadius: "var(--rl-radius-md)",
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
    </div>
  );
}

export default PassageWorkspace;
