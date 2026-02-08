/**
 * ConnectionSettingsModal - Modal for auth token and port configuration.
 *
 * Sprint 21: Provides user-visible UI to enter and save auth token,
 * replacing the developer-only console instructions.
 */

import { useState, useCallback, useEffect } from "react";
import { theme, commonStyles } from "../theme";

interface ConnectionSettingsModalProps {
  /** Current port value */
  port: number;
  /** Current token (empty string if none) */
  currentToken: string;
  /** Whether the modal can be closed (false if token is required) */
  canClose: boolean;
  /** Error message to display (e.g., auth failure) */
  errorMessage?: string | null;
  /** Called when settings are saved */
  onSave: (token: string, port: number) => void;
  /** Called when modal is closed */
  onClose: () => void;
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
  zIndex: theme.zIndex.modal,
};

const modalStyle: React.CSSProperties = {
  backgroundColor: theme.colors.bgSecondary,
  borderRadius: theme.borderRadius.xl,
  padding: theme.spacing.xxl,
  maxWidth: "480px",
  width: "90%",
  boxShadow: theme.shadows.xl,
  border: `1px solid ${theme.colors.bgTertiary}`,
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: theme.spacing.md,
  marginBottom: theme.spacing.xl,
};

const iconStyle: React.CSSProperties = {
  width: "48px",
  height: "48px",
  borderRadius: theme.borderRadius.full,
  backgroundColor: theme.colors.primary,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontSize: "var(--rl-fs-xl)",
};

const titleStyle: React.CSSProperties = {
  fontSize: theme.fontSize.xl,
  fontWeight: theme.fontWeight.semibold,
  color: theme.colors.textPrimary,
};

const subtitleStyle: React.CSSProperties = {
  fontSize: theme.fontSize.md,
  color: theme.colors.textSecondary,
  marginTop: "4px",
};

const fieldStyle: React.CSSProperties = {
  marginBottom: theme.spacing.xl,
};

const inputContainerStyle: React.CSSProperties = {
  position: "relative",
  display: "flex",
  alignItems: "center",
};

const inputStyle: React.CSSProperties = {
  ...commonStyles.input,
  width: "100%",
  paddingRight: "80px", // Room for two buttons
};

const inputButtonStyle: React.CSSProperties = {
  position: "absolute",
  background: "none",
  border: "none",
  color: theme.colors.textSecondary,
  cursor: "pointer",
  padding: "4px",
  fontSize: "var(--rl-fs-base)",
};

const revealButtonStyle: React.CSSProperties = {
  ...inputButtonStyle,
  right: "40px",
};

const copyButtonStyle: React.CSSProperties = {
  ...inputButtonStyle,
  right: "12px",
};

const errorBannerStyle: React.CSSProperties = {
  backgroundColor: theme.colors.brandRedDark,
  borderRadius: theme.borderRadius.md,
  padding: theme.spacing.lg,
  marginBottom: theme.spacing.xl,
  display: "flex",
  alignItems: "flex-start",
  gap: theme.spacing.md,
  border: `1px solid ${theme.colors.brandRed}`,
};

const statusStyle: React.CSSProperties = {
  fontSize: theme.fontSize.sm,
  marginTop: theme.spacing.sm,
  display: "flex",
  alignItems: "center",
  gap: theme.spacing.sm,
};

const buttonContainerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "flex-end",
  gap: theme.spacing.md,
  marginTop: theme.spacing.xl,
};

const helpTextStyle: React.CSSProperties = {
  fontSize: theme.fontSize.sm,
  color: theme.colors.textTertiary,
  marginTop: theme.spacing.sm,
  lineHeight: 1.5,
};

export function ConnectionSettingsModal({
  port,
  currentToken,
  canClose,
  errorMessage,
  onSave,
  onClose,
}: ConnectionSettingsModalProps) {
  const [token, setToken] = useState(currentToken);
  const [localPort, setLocalPort] = useState(port.toString());
  const [showToken, setShowToken] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);
  const [copied, setCopied] = useState(false);

  // Copy token to clipboard
  const handleCopyToken = useCallback(async () => {
    if (!token.trim()) return;
    try {
      await navigator.clipboard.writeText(token.trim());
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API not available
    }
  }, [token]);

  // Reset test result when inputs change
  useEffect(() => {
    setTestResult(null);
  }, [token, localPort]);

  const handleTest = useCallback(async () => {
    const portNum = parseInt(localPort, 10);
    if (isNaN(portNum) || portNum < 1 || portNum > 65535) {
      setTestResult({ success: false, message: "Invalid port number" });
      return;
    }

    if (!token.trim()) {
      setTestResult({ success: false, message: "Token is required" });
      return;
    }

    setTesting(true);
    setTestResult(null);

    try {
      // Test connection to engine status endpoint
      const response = await fetch(
        `http://127.0.0.1:${portNum}/v1/engine/status`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token.trim()}`,
            "Content-Type": "application/json",
          },
        },
      );

      if (response.ok) {
        const data = await response.json();
        setTestResult({
          success: true,
          message: `Connected! Engine v${data.version || "unknown"}`,
        });
      } else if (response.status === 401) {
        setTestResult({
          success: false,
          message: "Invalid token - authentication failed",
        });
      } else if (response.status === 404) {
        // Try root endpoint as fallback
        const rootResponse = await fetch(`http://127.0.0.1:${portNum}/`, {
          method: "GET",
          headers: { Accept: "application/json" },
        });
        if (rootResponse.ok) {
          setTestResult({
            success: true,
            message:
              "Server found. Token cannot be verified without auth endpoint.",
          });
        } else {
          setTestResult({
            success: false,
            message: `Server responded with ${response.status}`,
          });
        }
      } else {
        setTestResult({
          success: false,
          message: `Server responded with ${response.status}`,
        });
      }
    } catch (err) {
      const url = `http://127.0.0.1:${portNum}/v1/engine/status`;
      setTestResult({
        success: false,
        message: `Cannot reach server at ${url}`,
      });
    } finally {
      setTesting(false);
    }
  }, [token, localPort]);

  const handleSave = useCallback(() => {
    const portNum = parseInt(localPort, 10);
    if (isNaN(portNum) || portNum < 1 || portNum > 65535) {
      setTestResult({ success: false, message: "Invalid port number" });
      return;
    }

    if (!token.trim()) {
      setTestResult({ success: false, message: "Token is required" });
      return;
    }

    onSave(token.trim(), portNum);
  }, [token, localPort, onSave]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && token.trim()) {
        handleSave();
      }
      if (e.key === "Escape" && canClose) {
        onClose();
      }
    },
    [token, canClose, handleSave, onClose],
  );

  return (
    <div style={overlayStyle} onClick={canClose ? onClose : undefined}>
      <div
        style={modalStyle}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
      >
        <div style={headerStyle}>
          <div style={iconStyle}>
            <span role="img" aria-label="settings">
              {"\u2699"}
            </span>
          </div>
          <div>
            <div id="settings-title" style={titleStyle}>
              Connection Settings
            </div>
            <div style={subtitleStyle}>Configure your backend connection</div>
          </div>
        </div>

        {errorMessage && (
          <div style={errorBannerStyle}>
            <span style={{ fontSize: "var(--rl-fs-lg)" }}>{"\u26A0"}</span>
            <div>
              <div
                style={{
                  fontWeight: theme.fontWeight.medium,
                  color: theme.colors.brandRedLight,
                  marginBottom: "4px",
                }}
              >
                Connection Error
              </div>
              <div
                style={{
                  fontSize: theme.fontSize.sm,
                  color: theme.colors.errorLight,
                }}
              >
                {errorMessage}
              </div>
            </div>
          </div>
        )}

        {/* Token Field */}
        <div style={fieldStyle}>
          <label style={commonStyles.label}>Auth Token</label>
          <div style={inputContainerStyle}>
            <input
              type={showToken ? "text" : "password"}
              style={inputStyle}
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Enter your authentication token"
              autoFocus
              aria-describedby="token-help"
            />
            <button
              style={revealButtonStyle}
              onClick={() => setShowToken(!showToken)}
              type="button"
              aria-label={showToken ? "Hide token" : "Show token"}
              title={showToken ? "Hide token" : "Show token"}
            >
              {showToken ? "\u{1F441}" : "\u{1F440}"}
            </button>
            <button
              style={copyButtonStyle}
              onClick={handleCopyToken}
              type="button"
              aria-label={copied ? "Copied!" : "Copy token"}
              title={copied ? "Copied!" : "Copy token"}
              disabled={!token.trim()}
            >
              {copied ? "\u2714" : "\u{1F4CB}"}
            </button>
          </div>
          <div id="token-help" style={helpTextStyle}>
            The auth token is generated when you run{" "}
            <code
              style={{
                ...commonStyles.code,
                color: theme.colors.warning,
              }}
            >
              redletters init
            </code>
            . Check your terminal output or config file.
          </div>
        </div>

        {/* Port Field */}
        <div style={fieldStyle}>
          <label style={commonStyles.label}>Backend Port</label>
          <input
            type="number"
            style={{ ...commonStyles.input, width: "120px" }}
            value={localPort}
            onChange={(e) => setLocalPort(e.target.value)}
            min={1}
            max={65535}
            aria-describedby="port-help"
          />
          <div id="port-help" style={helpTextStyle}>
            Default is 47200. Change only if you started the backend on a
            different port.
          </div>
        </div>

        {/* Test Result */}
        {testResult && (
          <div
            style={{
              ...statusStyle,
              color: testResult.success
                ? theme.colors.success
                : theme.colors.error,
            }}
          >
            <span>{testResult.success ? "\u2714" : "\u2716"}</span>
            <span>{testResult.message}</span>
          </div>
        )}

        {/* Actions */}
        <div style={buttonContainerStyle}>
          {canClose && (
            <button
              style={commonStyles.buttonSecondary}
              onClick={onClose}
              type="button"
            >
              Cancel
            </button>
          )}
          <button
            style={{
              ...commonStyles.buttonSecondary,
              backgroundColor: theme.colors.bgTertiary,
            }}
            onClick={handleTest}
            disabled={testing || !token.trim()}
            type="button"
          >
            {testing ? "Testing..." : "Test Connection"}
          </button>
          <button
            style={commonStyles.buttonPrimary}
            onClick={handleSave}
            disabled={!token.trim()}
            type="button"
          >
            Save &amp; Connect
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConnectionSettingsModal;
