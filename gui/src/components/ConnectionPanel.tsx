/**
 * ConnectionPanel - displayed when backend is disconnected.
 *
 * Sprint v0.14.0: GUI-first onboarding with:
 * - Clear connection status
 * - Quick fix hints (port, health endpoint)
 * - Auto-detect localhost capability
 */

import { useState, useCallback } from "react";

interface ConnectionPanelProps {
  port: number;
  onReconnect: () => void;
  onPortChange: (port: number) => void;
}

// Styles
const containerStyle: React.CSSProperties = {
  padding: "24px",
  margin: "16px",
  backgroundColor: "#7f1d1d",
  borderRadius: "8px",
  border: "1px solid #991b1b",
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
  backgroundColor: "#ef4444",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontSize: "20px",
};

const titleStyle: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 600,
  color: "#fecaca",
};

const subtitleStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#fca5a5",
  marginTop: "4px",
};

const sectionStyle: React.CSSProperties = {
  marginBottom: "20px",
};

const labelStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#fca5a5",
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
}: ConnectionPanelProps) {
  const [localPort, setLocalPort] = useState(port.toString());
  const [checking, setChecking] = useState(false);
  const [checkResult, setCheckResult] = useState<string | null>(null);

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
        // Server is reachable but requires auth - this is actually good!
        setCheckResult(
          `Server found at port ${localPort}. Authentication required.`,
        );
        const newPort = parseInt(localPort, 10);
        if (!isNaN(newPort)) {
          onPortChange(newPort);
          onReconnect();
        }
      } else {
        setCheckResult(`Server responded with ${response.status}`);
      }
    } catch (err) {
      setCheckResult(
        `Cannot reach server at port ${localPort}. Is the backend running?`,
      );
    } finally {
      setChecking(false);
    }
  }, [localPort, onPortChange, onReconnect]);

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
        </div>
        {checkResult && (
          <div
            style={{
              ...statusStyle,
              color: checkResult.startsWith("Connected")
                ? "#22c55e"
                : "#fca5a5",
            }}
          >
            {checkResult}
          </div>
        )}
      </div>

      <div style={hintsStyle}>
        <div style={hintTitleStyle}>Quick Fix Steps</div>
        <div style={hintItemStyle}>
          1. Start the backend: <code style={codeStyle}>redletters serve</code>
        </div>
        <div style={hintItemStyle}>
          2. Verify it's running:{" "}
          <code style={codeStyle}>curl http://127.0.0.1:47200/</code>
        </div>
        <div style={hintItemStyle}>
          3. If using a different port, update the port number above
        </div>
        <div style={hintItemStyle}>
          4. Check firewall settings if connection still fails
        </div>
      </div>
    </div>
  );
}
