/**
 * ApiErrorPanel - Structured error display with diagnostics.
 *
 * Sprint 16: Replaces generic error banners with actionable diagnostics.
 * Sprint 17: Enhanced with error categories, multiple suggestions, copy payload.
 *
 * Shows request method+URL, status code, response snippet, and fix hints.
 */

import { useState, useCallback } from "react";
import type { ApiErrorDetail, ErrorCategory } from "../api/types";
import { normalizeApiError } from "../api/client";

interface ApiErrorPanelProps {
  error: ApiErrorDetail;
  onDismiss?: () => void;
  onRetry?: () => void;
  compact?: boolean;
}

const containerStyle: React.CSSProperties = {
  backgroundColor: "#7f1d1d",
  borderRadius: "8px",
  padding: "16px",
  marginBottom: "16px",
  border: "1px solid #ef4444",
};

const compactContainerStyle: React.CSSProperties = {
  ...containerStyle,
  padding: "12px",
  marginBottom: "12px",
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  marginBottom: "12px",
};

const titleStyle: React.CSSProperties = {
  color: "#fca5a5",
  fontSize: "14px",
  fontWeight: 600,
  display: "flex",
  alignItems: "center",
  gap: "8px",
};

const detailsContainerStyle: React.CSSProperties = {
  backgroundColor: "#450a0a",
  borderRadius: "4px",
  padding: "12px",
  marginBottom: "12px",
  fontFamily: "monospace",
  fontSize: "12px",
  lineHeight: 1.5,
};

const labelStyle: React.CSSProperties = {
  color: "#9ca3af",
  marginRight: "8px",
};

const valueStyle: React.CSSProperties = {
  color: "#fca5a5",
};

const codeStyle: React.CSSProperties = {
  backgroundColor: "#374151",
  padding: "2px 6px",
  borderRadius: "3px",
  color: "#f87171",
};

const fixHintStyle: React.CSSProperties = {
  backgroundColor: "#1a1a2e",
  borderRadius: "4px",
  padding: "12px",
  marginBottom: "12px",
  borderLeft: "3px solid #f59e0b",
};

const fixHintTitleStyle: React.CSSProperties = {
  color: "#f59e0b",
  fontSize: "12px",
  fontWeight: 600,
  marginBottom: "8px",
};

const suggestionListStyle: React.CSSProperties = {
  margin: 0,
  paddingLeft: "16px",
  color: "#9ca3af",
  fontSize: "13px",
};

const suggestionItemStyle: React.CSSProperties = {
  marginBottom: "4px",
};

const buttonContainerStyle: React.CSSProperties = {
  display: "flex",
  gap: "8px",
  marginTop: "12px",
};

const buttonStyle: React.CSSProperties = {
  padding: "6px 12px",
  fontSize: "12px",
  fontWeight: 500,
  border: "none",
  borderRadius: "4px",
  cursor: "pointer",
};

const primaryButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "#3b82f6",
  color: "white",
};

const secondaryButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "#4b5563",
  color: "#eaeaea",
};

const copyButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "#374151",
  color: "#9ca3af",
};

const dismissButtonStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  color: "#9ca3af",
  cursor: "pointer",
  fontSize: "18px",
  padding: "4px",
};

const causeStyle: React.CSSProperties = {
  color: "#fca5a5",
  fontSize: "13px",
  marginBottom: "8px",
};

// Category-specific icons and labels
const CATEGORY_CONFIG: Record<
  ErrorCategory,
  { icon: string; label: string; color: string }
> = {
  network: { icon: "⚡", label: "Network Error", color: "#f59e0b" },
  auth: { icon: "🔒", label: "Authentication Error", color: "#ef4444" },
  not_found: { icon: "🔍", label: "Endpoint Not Found", color: "#6366f1" },
  backend_mismatch: {
    icon: "🔀",
    label: "Backend Mismatch",
    color: "#f59e0b",
  },
  gate_blocked: { icon: "🚧", label: "Gate Blocked", color: "#f59e0b" },
  service_unavailable: {
    icon: "⏳",
    label: "Service Unavailable",
    color: "#f59e0b",
  },
  server: { icon: "🔧", label: "Server Error", color: "#ef4444" },
  unknown: { icon: "⚠️", label: "Request Failed", color: "#9ca3af" },
};

export function ApiErrorPanel({
  error,
  onDismiss,
  onRetry,
  compact = false,
}: ApiErrorPanelProps) {
  const [copied, setCopied] = useState(false);
  const [showDetails, setShowDetails] = useState(!compact);

  const handleCopyDiagnostics = useCallback(() => {
    // Sprint 17: Include contract diagnostics in copy payload
    const contractSection = error.contractDiagnostics
      ? `
Contract State
--------------
Base URL: ${error.contractDiagnostics.baseUrl}
Has Capabilities: ${error.contractDiagnostics.hasCapabilities}
${
  error.contractDiagnostics.capabilities
    ? `Backend Version: ${error.contractDiagnostics.capabilities.version}
API Version: ${error.contractDiagnostics.capabilities.api_version}
Min GUI Version: ${error.contractDiagnostics.capabilities.min_gui_version}
Features: ${error.contractDiagnostics.capabilities.features.join(", ")}
Initialized: ${error.contractDiagnostics.capabilities.initialized}`
    : "Capabilities not loaded"
}
${
  error.contractDiagnostics.resolvedEndpoints
    ? `
Resolved Endpoints:
${Object.entries(error.contractDiagnostics.resolvedEndpoints)
  .map(([k, v]) => `  ${k}: ${v}`)
  .join("\n")}`
    : ""
}
`
      : "";

    const diagnostics = `API Error Diagnostics
=====================
Timestamp: ${error.timestamp}
Category: ${error.category || "unknown"}

Request
-------
Method: ${error.method}
URL: ${error.url}

Response
--------
Status: ${error.status ?? "N/A"} ${error.statusText}
Body: ${error.responseSnippet || "No response body"}
${contractSection}
Analysis
--------
Likely Cause: ${error.likelyCause || "Unknown"}

Suggested Fixes:
${(error.suggestions || [error.suggestedFix]).map((s, i) => `${i + 1}. ${s}`).join("\n")}

${error.raw ? `\nRaw Error:\n${JSON.stringify(error.raw, null, 2)}` : ""}
`;
    navigator.clipboard.writeText(diagnostics);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [error]);

  // Get category config (with fallback for legacy errors without category)
  const category = error.category || getCategoryFromStatus(error.status);
  const config = CATEGORY_CONFIG[category];
  const suggestions = error.suggestions || [error.suggestedFix];

  return (
    <div style={compact ? compactContainerStyle : containerStyle}>
      <div style={headerStyle}>
        <div style={titleStyle}>
          <span>{config.icon}</span>
          <span style={{ color: config.color }}>{config.label}</span>
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          {compact && (
            <button
              style={{ ...dismissButtonStyle, fontSize: "12px" }}
              onClick={() => setShowDetails(!showDetails)}
            >
              {showDetails ? "▼" : "▶"} Details
            </button>
          )}
          {onDismiss && (
            <button
              style={dismissButtonStyle}
              onClick={onDismiss}
              title="Dismiss"
            >
              ×
            </button>
          )}
        </div>
      </div>

      {/* Likely cause (always visible) */}
      <div style={causeStyle}>{error.likelyCause || error.suggestedFix}</div>

      {/* Detailed info (collapsible in compact mode) */}
      {showDetails && (
        <>
          {/* Request details */}
          <div style={detailsContainerStyle}>
            <div>
              <span style={labelStyle}>Request:</span>
              <code style={codeStyle}>{error.method}</code>{" "}
              <span style={valueStyle}>{error.url}</span>
            </div>
            <div style={{ marginTop: "4px" }}>
              <span style={labelStyle}>Status:</span>
              <span style={valueStyle}>
                {error.status !== null
                  ? `${error.status} ${error.statusText}`
                  : "No response (network error)"}
              </span>
            </div>
            {error.responseSnippet && (
              <div style={{ marginTop: "8px" }}>
                <span style={labelStyle}>Response:</span>
                <div
                  style={{
                    marginTop: "4px",
                    color: "#9ca3af",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    maxHeight: "100px",
                    overflow: "auto",
                  }}
                >
                  {error.responseSnippet.slice(0, 500)}
                  {error.responseSnippet.length > 500 && "..."}
                </div>
              </div>
            )}
            {/* Sprint 17: Show resolved base URL and capabilities */}
            {error.contractDiagnostics && (
              <div
                style={{
                  marginTop: "12px",
                  paddingTop: "8px",
                  borderTop: "1px solid #374151",
                }}
              >
                <span style={labelStyle}>Contract:</span>
                <div
                  style={{
                    marginTop: "4px",
                    color: "#9ca3af",
                    fontSize: "11px",
                  }}
                >
                  <div>
                    Base URL:{" "}
                    <span style={{ color: "#fca5a5" }}>
                      {error.contractDiagnostics.baseUrl}
                    </span>
                  </div>
                  {error.contractDiagnostics.capabilities && (
                    <div style={{ marginTop: "2px" }}>
                      Backend: v{error.contractDiagnostics.capabilities.version}
                      {" | "}
                      {error.contractDiagnostics.capabilities.initialized
                        ? "Initialized"
                        : "Not initialized"}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Suggestions */}
          {suggestions.length > 0 && (
            <div style={fixHintStyle}>
              <div style={fixHintTitleStyle}>
                {suggestions.length === 1 ? "Suggested Fix" : "Try These Steps"}
              </div>
              {suggestions.length === 1 ? (
                <div style={{ color: "#9ca3af", fontSize: "13px" }}>
                  {suggestions[0]}
                </div>
              ) : (
                <ol style={suggestionListStyle}>
                  {suggestions.map((suggestion, i) => (
                    <li key={i} style={suggestionItemStyle}>
                      {suggestion}
                    </li>
                  ))}
                </ol>
              )}
            </div>
          )}
        </>
      )}

      {/* Actions */}
      <div style={buttonContainerStyle}>
        {onRetry && (
          <button style={primaryButtonStyle} onClick={onRetry}>
            Retry
          </button>
        )}
        <button style={copyButtonStyle} onClick={handleCopyDiagnostics}>
          {copied ? "Copied!" : "Copy Diagnostics"}
        </button>
        {onDismiss && !compact && (
          <button style={secondaryButtonStyle} onClick={onDismiss}>
            Dismiss
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * Get category from status code (for legacy ApiErrorDetail without category).
 */
function getCategoryFromStatus(status: number | null): ErrorCategory {
  if (status === null) return "network";
  if (status === 401) return "auth";
  if (status === 404) return "not_found";
  if (status === 409) return "gate_blocked";
  if (status === 503) return "service_unavailable";
  if (status >= 500) return "server";
  return "unknown";
}

/**
 * Helper to create ApiErrorDetail from various error sources.
 * Sprint 17: Now delegates to normalizeApiError for consistent handling.
 * Accepts optional contract diagnostics for debugging endpoint resolution.
 */
export function createApiErrorDetail(
  method: string,
  url: string,
  error: unknown,
  contractDiagnostics?: ApiErrorDetail["contractDiagnostics"],
): ApiErrorDetail {
  return normalizeApiError(method, url, error, contractDiagnostics);
}

export default ApiErrorPanel;
