/**
 * BackendMismatchPanel - Blocking panel for backend mode mismatch.
 *
 * Sprint 19: Shows when backend is running in engine-only mode but GUI
 * requires full mode with /translate and /sources routes.
 * Displays the exact correct start command.
 */

import { useState, useCallback } from "react";
import type { BackendMismatchInfo } from "../api/types";

interface BackendMismatchPanelProps {
  mismatchInfo: BackendMismatchInfo;
  onRetry: () => void;
  onDismiss?: () => void;
}

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: "rgba(0, 0, 0, 0.85)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 2000,
};

const modalStyle: React.CSSProperties = {
  backgroundColor: "var(--rl-bg-card)",
  borderRadius: "12px",
  padding: "32px",
  maxWidth: "520px",
  width: "90%",
  boxShadow: "0 20px 60px rgba(0, 0, 0, 0.5)",
  border: "1px solid var(--rl-warning)",
};

const iconStyle: React.CSSProperties = {
  fontSize: "48px",
  textAlign: "center",
  marginBottom: "16px",
};

const headerStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-lg)",
  fontWeight: 600,
  color: "#fbbf24",
  textAlign: "center",
  marginBottom: "8px",
};

const subHeaderStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-base)",
  color: "var(--rl-text-muted)",
  textAlign: "center",
  marginBottom: "24px",
  lineHeight: 1.5,
};

const detailsCardStyle: React.CSSProperties = {
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "8px",
  padding: "16px",
  marginBottom: "20px",
};

const detailRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  marginBottom: "8px",
  fontSize: "var(--rl-fs-base)",
};

const labelStyle: React.CSSProperties = {
  color: "var(--rl-text-muted)",
};

const valueStyle: React.CSSProperties = {
  color: "var(--rl-text)",
  fontFamily: "var(--rl-font-mono)",
};

const errorValueStyle: React.CSSProperties = {
  ...valueStyle,
  color: "#fca5a5",
};

const warningValueStyle: React.CSSProperties = {
  ...valueStyle,
  color: "#fbbf24",
};

const commandBoxStyle: React.CSSProperties = {
  backgroundColor: "#1e1e30",
  borderRadius: "8px",
  padding: "16px",
  marginBottom: "20px",
  border: "2px solid var(--rl-success)",
};

const commandLabelStyle: React.CSSProperties = {
  color: "var(--rl-success)",
  fontSize: "var(--rl-fs-sm)",
  fontWeight: 600,
  marginBottom: "8px",
  textTransform: "uppercase",
  letterSpacing: "0.5px",
};

const commandStyle: React.CSSProperties = {
  fontFamily: "var(--rl-font-mono)",
  fontSize: "var(--rl-fs-base)",
  color: "#f0fdf4",
  backgroundColor: "#052e16",
  padding: "12px",
  borderRadius: "4px",
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: "12px",
};

const copyButtonStyle: React.CSSProperties = {
  backgroundColor: "transparent",
  border: "1px solid var(--rl-success)",
  color: "var(--rl-success)",
  padding: "4px 8px",
  borderRadius: "4px",
  cursor: "pointer",
  fontSize: "var(--rl-fs-xs)",
  fontWeight: 500,
  whiteSpace: "nowrap",
};

const copiedButtonStyle: React.CSSProperties = {
  ...copyButtonStyle,
  backgroundColor: "var(--rl-success)",
  color: "#052e16",
};

const fixSectionStyle: React.CSSProperties = {
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "8px",
  padding: "16px",
  marginBottom: "20px",
  borderLeft: "3px solid var(--rl-primary)",
};

const fixTitleStyle: React.CSSProperties = {
  color: "var(--rl-primary)",
  fontSize: "var(--rl-fs-base)",
  fontWeight: 600,
  marginBottom: "12px",
};

const fixListStyle: React.CSSProperties = {
  margin: 0,
  paddingLeft: "16px",
  color: "var(--rl-text-muted)",
  fontSize: "var(--rl-fs-base)",
};

const fixItemStyle: React.CSSProperties = {
  marginBottom: "8px",
  lineHeight: 1.5,
};

const buttonContainerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "center",
  gap: "12px",
};

const buttonStyle: React.CSSProperties = {
  padding: "12px 24px",
  fontSize: "var(--rl-fs-base)",
  fontWeight: 500,
  border: "none",
  borderRadius: "6px",
  cursor: "pointer",
};

const primaryButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "var(--rl-primary)",
  color: "white",
};

const secondaryButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "var(--rl-border-strong)",
  color: "var(--rl-text)",
};

export function BackendMismatchPanel({
  mismatchInfo,
  onRetry,
  onDismiss,
}: BackendMismatchPanelProps) {
  const [copied, setCopied] = useState(false);
  const [diagCopied, setDiagCopied] = useState(false);

  const handleCopyCommand = useCallback(() => {
    navigator.clipboard.writeText(mismatchInfo.correctStartCommand);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [mismatchInfo.correctStartCommand]);

  const handleCopyDiagnostics = useCallback(() => {
    const diagnostics = `Red Letters Backend Mismatch
==============================
Status: MISMATCH DETECTED

Backend Mode: ${mismatchInfo.backendMode || "unknown"}
Expected Mode: full

Missing Routes:
${mismatchInfo.missingRoutes.map((r) => `  - ${r}`).join("\n") || "  (none detected)"}

Correct Start Command:
  ${mismatchInfo.correctStartCommand}

Fix Steps:
1. Stop the current backend process
2. Start backend with the correct command shown above
3. Verify all routes are available
`;
    navigator.clipboard.writeText(diagnostics);
    setDiagCopied(true);
    setTimeout(() => setDiagCopied(false), 2000);
  }, [mismatchInfo]);

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <div style={iconStyle}>🔧</div>
        <div style={headerStyle}>Backend Mode Mismatch</div>
        <div style={subHeaderStyle}>
          The backend is running in <strong>engine-only</strong> mode, but the
          GUI requires <strong>full</strong> mode with translation and source
          management routes.
        </div>

        {/* Details Card */}
        <div style={detailsCardStyle}>
          <div style={detailRowStyle}>
            <span style={labelStyle}>Detected backend mode:</span>
            <span style={warningValueStyle}>
              {mismatchInfo.backendMode || "engine_only"}
            </span>
          </div>
          <div style={detailRowStyle}>
            <span style={labelStyle}>Required mode:</span>
            <span style={valueStyle}>full</span>
          </div>
          {mismatchInfo.missingRoutes.length > 0 && (
            <div style={{ marginTop: "12px" }}>
              <div style={labelStyle}>Missing routes:</div>
              <div style={{ marginTop: "8px" }}>
                {mismatchInfo.missingRoutes.map((route) => (
                  <div
                    key={route}
                    style={{ marginLeft: "12px", marginBottom: "4px" }}
                  >
                    <span style={errorValueStyle}>✗ {route}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Correct Command */}
        <div style={commandBoxStyle}>
          <div style={commandLabelStyle}>Correct Start Command</div>
          <div style={commandStyle}>
            <code>{mismatchInfo.correctStartCommand}</code>
            <button
              style={copied ? copiedButtonStyle : copyButtonStyle}
              onClick={handleCopyCommand}
            >
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
        </div>

        {/* Fix Steps */}
        <div style={fixSectionStyle}>
          <div style={fixTitleStyle}>How to Fix</div>
          <ol style={fixListStyle}>
            <li style={fixItemStyle}>
              Stop the currently running backend process (Ctrl+C or kill the
              terminal)
            </li>
            <li style={fixItemStyle}>
              Start the backend using the correct command shown above
            </li>
            <li style={fixItemStyle}>
              Click "Retry Connection" below once the backend is running
            </li>
          </ol>
        </div>

        {/* Actions */}
        <div style={buttonContainerStyle}>
          <button style={primaryButtonStyle} onClick={onRetry}>
            Retry Connection
          </button>
          <button
            style={
              diagCopied
                ? { ...secondaryButtonStyle, backgroundColor: "var(--rl-success)" }
                : secondaryButtonStyle
            }
            onClick={handleCopyDiagnostics}
          >
            {diagCopied ? "Copied!" : "Copy Diagnostics"}
          </button>
          {onDismiss && (
            <button style={secondaryButtonStyle} onClick={onDismiss}>
              Dismiss
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default BackendMismatchPanel;
