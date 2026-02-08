/**
 * CompatibilityModal - Blocking modal for version/endpoint mismatch.
 *
 * Sprint 17: Shows when GUI and backend are incompatible.
 * Blocks core actions until resolved. Shows exact mismatch + fix steps.
 */

import { useState, useCallback } from "react";
import type { CapabilitiesValidation } from "../api/types";

interface CompatibilityModalProps {
  validation: CapabilitiesValidation;
  backendVersion?: string;
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
  maxWidth: "500px",
  width: "90%",
  boxShadow: "0 20px 60px rgba(0, 0, 0, 0.5)",
  border: "1px solid var(--rl-error)",
};

const iconStyle: React.CSSProperties = {
  fontSize: "48px",
  textAlign: "center",
  marginBottom: "16px",
};

const headerStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-lg)",
  fontWeight: 600,
  color: "#fca5a5",
  textAlign: "center",
  marginBottom: "8px",
};

const subHeaderStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-base)",
  color: "var(--rl-text-muted)",
  textAlign: "center",
  marginBottom: "24px",
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

const fixSectionStyle: React.CSSProperties = {
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "8px",
  padding: "16px",
  marginBottom: "20px",
  borderLeft: "3px solid var(--rl-warning)",
};

const fixTitleStyle: React.CSSProperties = {
  color: "var(--rl-warning)",
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
};

const codeStyle: React.CSSProperties = {
  backgroundColor: "var(--rl-border-strong)",
  padding: "2px 6px",
  borderRadius: "3px",
  fontFamily: "var(--rl-font-mono)",
  fontSize: "var(--rl-fs-sm)",
  color: "var(--rl-warning)",
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

const copiedStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "var(--rl-success)",
  color: "white",
};

export function CompatibilityModal({
  validation,
  backendVersion,
  onRetry,
  onDismiss,
}: CompatibilityModalProps) {
  const [copied, setCopied] = useState(false);

  const handleCopyDiagnostics = useCallback(() => {
    const diagnostics = `Red Letters Compatibility Check
===============================
Status: FAILED

${
  validation.versionMismatch
    ? `Version Mismatch:
  Required GUI Version: ${validation.versionMismatch.required}
  Current GUI Version: ${validation.versionMismatch.current}
  Backend Version: ${backendVersion || "unknown"}`
    : ""
}

${
  validation.missingEndpoints && validation.missingEndpoints.length > 0
    ? `Missing Endpoints:
${validation.missingEndpoints.map((e) => `  - ${e}`).join("\n")}`
    : ""
}

Error: ${validation.error || "Unknown compatibility issue"}

Fix Steps:
1. Update your GUI to match the required version
2. Or upgrade/downgrade your backend to match
3. Ensure all required services are running
`;
    navigator.clipboard.writeText(diagnostics);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [validation, backendVersion]);

  const isVersionMismatch = !!validation.versionMismatch;
  const isMissingEndpoints =
    validation.missingEndpoints && validation.missingEndpoints.length > 0;

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <div style={iconStyle}>⚠️</div>
        <div style={headerStyle}>Compatibility Issue Detected</div>
        <div style={subHeaderStyle}>
          The GUI and backend are not compatible. Core features are disabled
          until this is resolved.
        </div>

        {/* Details Card */}
        <div style={detailsCardStyle}>
          {isVersionMismatch && (
            <>
              <div style={detailRowStyle}>
                <span style={labelStyle}>Backend requires GUI version:</span>
                <span style={errorValueStyle}>
                  {validation.versionMismatch!.required}+
                </span>
              </div>
              <div style={detailRowStyle}>
                <span style={labelStyle}>Your GUI version:</span>
                <span style={errorValueStyle}>
                  {validation.versionMismatch!.current}
                </span>
              </div>
              {backendVersion && (
                <div style={detailRowStyle}>
                  <span style={labelStyle}>Backend version:</span>
                  <span style={valueStyle}>{backendVersion}</span>
                </div>
              )}
            </>
          )}

          {isMissingEndpoints && (
            <div>
              <div style={{ ...detailRowStyle, marginBottom: "12px" }}>
                <span style={labelStyle}>Missing required endpoints:</span>
              </div>
              {validation.missingEndpoints!.map((endpoint) => (
                <div
                  key={endpoint}
                  style={{ marginLeft: "16px", marginBottom: "4px" }}
                >
                  <span style={errorValueStyle}>✗ {endpoint}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Fix Steps */}
        <div style={fixSectionStyle}>
          <div style={fixTitleStyle}>How to Fix</div>
          <ol style={fixListStyle}>
            {isVersionMismatch && (
              <>
                <li style={fixItemStyle}>
                  Update your GUI to version{" "}
                  <code style={codeStyle}>
                    {validation.versionMismatch!.required}
                  </code>{" "}
                  or newer
                </li>
                <li style={fixItemStyle}>
                  Or downgrade your backend:{" "}
                  <code style={codeStyle}>
                    pip install redletters=={`<older_version>`}
                  </code>
                </li>
              </>
            )}
            {isMissingEndpoints && (
              <>
                <li style={fixItemStyle}>
                  Upgrade your backend:{" "}
                  <code style={codeStyle}>pip install -U redletters</code>
                </li>
                <li style={fixItemStyle}>
                  Ensure you are running backend v0.16.0 or newer
                </li>
              </>
            )}
            <li style={fixItemStyle}>
              Restart the backend and click "Check Again"
            </li>
          </ol>
        </div>

        {/* Actions */}
        <div style={buttonContainerStyle}>
          <button style={primaryButtonStyle} onClick={onRetry}>
            Check Again
          </button>
          <button
            style={copied ? copiedStyle : secondaryButtonStyle}
            onClick={handleCopyDiagnostics}
          >
            {copied ? "Copied!" : "Copy Diagnostics"}
          </button>
          {onDismiss && (
            <button style={secondaryButtonStyle} onClick={onDismiss}>
              Continue Anyway
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default CompatibilityModal;
