/**
 * ConnectionPanel - displayed when backend is disconnected.
 *
 * Sprint v0.14.0: GUI-first onboarding with:
 * - Clear connection status
 * - Quick fix hints (port, health endpoint)
 * - Auto-detect localhost capability
 *
 * Sprint 22: Added auto-detect backend feature.
 */

import { useState, useCallback } from "react";
import { detectBackendPort, type DetectedBackend } from "../api/constants";

interface ConnectionPanelProps {
  port: number;
  onReconnect: () => void;
  onPortChange: (port: number) => void;
  /** Opens connection settings modal for token entry */
  onOpenSettings?: () => void;
}

// Styles - Sprint 22: Calmer colors (warning amber instead of panic red)
const containerStyle: React.CSSProperties = {
  padding: "24px",
  margin: "16px",
  backgroundColor: "#1f2937", // Dark gray instead of dark red
  borderRadius: "8px",
  border: "1px solid #f59e0b", // Amber border instead of red
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "12px",
  marginBottom: "16px",
};

const iconStyle: React.CSSProperties = {
  width: "40px",
  height: "40px",
  borderRadius: "50%",
  backgroundColor: "#f59e0b", // Amber instead of red
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontSize: "20px",
  color: "#1f2937",
};

const titleStyle: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 600,
  color: "#fcd34d", // Amber text instead of red
};

const subtitleStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#9ca3af", // Neutral gray instead of red tint
  marginTop: "4px",
};

const sectionStyle: React.CSSProperties = {
  marginBottom: "20px",
};

const labelStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#9ca3af", // Neutral gray
  textTransform: "uppercase",
  marginBottom: "8px",
};

const inputRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "8px",
  alignItems: "center",
};

const inputStyle: React.CSSProperties = {
  padding: "10px 14px",
  fontSize: "14px",
  backgroundColor: "#1a1a2e",
  border: "1px solid #4b5563",
  borderRadius: "4px",
  color: "#eaeaea",
  width: "120px",
};

const buttonStyle: React.CSSProperties = {
  padding: "10px 20px",
  fontSize: "14px",
  fontWeight: 500,
  backgroundColor: "#3b82f6",
  color: "white",
  border: "none",
  borderRadius: "4px",
  cursor: "pointer",
};

const secondaryButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "#4b5563",
};

const hintsStyle: React.CSSProperties = {
  backgroundColor: "#1a1a2e",
  borderRadius: "6px",
  padding: "16px",
  marginTop: "16px",
};

const hintTitleStyle: React.CSSProperties = {
  fontSize: "13px",
  fontWeight: 600,
  color: "#9ca3af",
  marginBottom: "12px",
};

const hintItemStyle: React.CSSProperties = {
  fontSize: "13px",
  color: "#9ca3af",
  marginBottom: "8px",
  paddingLeft: "16px",
  position: "relative" as const,
};

const codeStyle: React.CSSProperties = {
  fontFamily: "monospace",
  backgroundColor: "#374151",
  padding: "2px 6px",
  borderRadius: "3px",
  fontSize: "12px",
};

const statusStyle: React.CSSProperties = {
  fontSize: "12px",
  marginTop: "8px",
};

export function ConnectionPanel({
  port,
  onReconnect,
  onPortChange,
  onOpenSettings,
}: ConnectionPanelProps) {
  const [localPort, setLocalPort] = useState(port.toString());
  const [checking, setChecking] = useState(false);
  const [checkResult, setCheckResult] = useState<string | null>(null);
  const [autoDetecting, setAutoDetecting] = useState(false);
  const [detectedBackend, setDetectedBackend] =
    useState<DetectedBackend | null>(null);

  const handlePortChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setLocalPort(e.target.value);
      setCheckResult(null);
    },
    [],
  );

  const handleApplyPort = useCallback(() => {
    const newPort = parseInt(localPort, 10);
    if (!isNaN(newPort) && newPort > 0 && newPort < 65536) {
      onPortChange(newPort);
      onReconnect();
    }
  }, [localPort, onPortChange, onReconnect]);

  const handleCheckHealth = useCallback(async () => {
    setChecking(true);
    setCheckResult(null);

    try {
      // Use root endpoint which is exempt from auth (per ADR-005)
      // This allows health checks without requiring a valid token
      const response = await fetch(`http://127.0.0.1:${localPort}/`, {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
      });

      if (response.ok) {
        const data = await response.json();
        // Root endpoint returns: { name, version, api, docs }
        setCheckResult(
          `Connected! ${data.name || "Red Letters Engine"} v${data.version || "unknown"}`,
        );
        // Auto-apply and reconnect on success
        const newPort = parseInt(localPort, 10);
        if (!isNaN(newPort)) {
          onPortChange(newPort);
          onReconnect();
        }
      } else if (response.status === 401) {
        // Server is reachable but requires auth - prompt user to configure token
        setCheckResult("auth_required");
        const newPort = parseInt(localPort, 10);
        if (!isNaN(newPort)) {
          onPortChange(newPort);
        }
      } else {
        setCheckResult(`Server responded with ${response.status}`);
      }
    } catch (err) {
      const url = `http://127.0.0.1:${localPort}/`;
      setCheckResult(`Cannot reach server at ${url} - Is the backend running?`);
    } finally {
      setChecking(false);
    }
  }, [localPort, onPortChange, onReconnect]);

  const handleAutoDetect = useCallback(async () => {
    setAutoDetecting(true);
    setDetectedBackend(null);
    setCheckResult(null);

    const result = await detectBackendPort();
    setAutoDetecting(false);

    if (result) {
      setDetectedBackend(result);
      // Auto-update port field to detected port
      setLocalPort(result.port.toString());
    } else {
      setCheckResult("No backend found on ports 47200, 8000, or 5000");
    }
  }, []);

  const handleSwitchToDetected = useCallback(() => {
    if (detectedBackend) {
      onPortChange(detectedBackend.port);
      setDetectedBackend(null);
      if (detectedBackend.requiresAuth && onOpenSettings) {
        onOpenSettings();
      } else {
        onReconnect();
      }
    }
  }, [detectedBackend, onPortChange, onReconnect, onOpenSettings]);

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <div style={iconStyle}>!</div>
        <div>
          <div style={titleStyle}>Not Connected</div>
          <div style={subtitleStyle}>
            Cannot reach the Red Letters backend server
          </div>
        </div>
      </div>

      <div style={sectionStyle}>
        <div style={labelStyle}>Engine Port</div>
        <div style={inputRowStyle}>
          <input
            type="text"
            style={inputStyle}
            value={localPort}
            onChange={handlePortChange}
            placeholder="47200"
          />
          <button
            style={secondaryButtonStyle}
            onClick={handleCheckHealth}
            disabled={checking}
          >
            {checking ? "Checking..." : "Check Health"}
          </button>
          <button style={buttonStyle} onClick={handleApplyPort}>
            Reconnect
          </button>
          <button
            style={{
              ...secondaryButtonStyle,
              backgroundColor: "#6366f1",
            }}
            onClick={handleAutoDetect}
            disabled={autoDetecting}
          >
            {autoDetecting ? "Scanning..." : "Auto-detect"}
          </button>
        </div>
        {checkResult && (
          <div
            style={{
              ...statusStyle,
              color: checkResult.startsWith("Connected")
                ? "#22c55e"
                : checkResult === "auth_required"
                  ? "#fcd34d"
                  : "#fca5a5",
            }}
          >
            {checkResult === "auth_required" ? (
              <div
                style={{ display: "flex", alignItems: "center", gap: "12px" }}
              >
                <span>Server found! Configure your auth token to connect.</span>
                {onOpenSettings && (
                  <button
                    onClick={onOpenSettings}
                    style={{
                      ...buttonStyle,
                      padding: "6px 12px",
                      fontSize: "12px",
                    }}
                  >
                    Configure Token
                  </button>
                )}
              </div>
            ) : (
              checkResult
            )}
          </div>
        )}
        {detectedBackend && (
          <div
            style={{
              ...statusStyle,
              marginTop: "12px",
              padding: "12px",
              backgroundColor: "#1e3a5f",
              borderRadius: "6px",
              border: "1px solid #3b82f6",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                flexWrap: "wrap",
              }}
            >
              <span style={{ color: "#93c5fd" }}>
                Backend found on port {detectedBackend.port}
                {detectedBackend.version && ` (v${detectedBackend.version})`}
                {detectedBackend.requiresAuth && " - Auth required"}
              </span>
              <button
                onClick={handleSwitchToDetected}
                style={{
                  ...buttonStyle,
                  padding: "6px 12px",
                  fontSize: "12px",
                  backgroundColor: "#22c55e",
                }}
              >
                {detectedBackend.requiresAuth
                  ? "Configure & Connect"
                  : "Switch to Port " + detectedBackend.port}
              </button>
            </div>
          </div>
        )}
      </div>

      <div style={hintsStyle}>
        <div style={hintTitleStyle}>Quick Fix Steps</div>
        <div style={hintItemStyle}>
          1. Start the backend:{" "}
          <code style={codeStyle}>
            redletters engine start --port {localPort}
          </code>
        </div>
        <div style={hintItemStyle}>
          2. Click "Check Health" above to verify the server is running
        </div>
        <div style={hintItemStyle}>
          3. If server found, configure your auth token (from{" "}
          <code style={codeStyle}>redletters init</code>)
        </div>
        <div style={hintItemStyle}>
          4. If using a different port, update the port number above
        </div>

        {onOpenSettings && (
          <button
            onClick={onOpenSettings}
            style={{
              ...buttonStyle,
              marginTop: "16px",
              width: "100%",
              backgroundColor: "#3b82f6",
            }}
          >
            Configure Connection Settings
          </button>
        )}
      </div>
    </div>
  );
}
