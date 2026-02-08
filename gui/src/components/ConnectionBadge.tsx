/**
 * ConnectionBadge - Persistent SSE connection health indicator.
 *
 * Sprint 19: Jobs-native GUI
 *
 * Shows connected/reconnecting/disconnected state with:
 * - Color-coded dot (green/yellow/red)
 * - Tooltip with diagnostics (base URL, lastEventId, lastMessageAt)
 * - Click to expand details
 */

import { useState } from "react";
import type { SSEHealthInfo, SSEHealthState } from "../api/types";

interface ConnectionBadgeProps {
  health: SSEHealthInfo;
  onReconnect?: () => void;
}

const STATE_COLORS: Record<SSEHealthState, string> = {
  connected: "var(--rl-success)",
  reconnecting: "var(--rl-warning)",
  disconnected: "var(--rl-error)",
};

const STATE_LABELS: Record<SSEHealthState, string> = {
  connected: "Connected",
  reconnecting: "Reconnecting...",
  disconnected: "Disconnected",
};

// Styles
const badgeContainerStyle: React.CSSProperties = {
  position: "relative",
  display: "inline-flex",
  alignItems: "center",
  gap: "6px",
  padding: "4px 10px",
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "16px",
  cursor: "pointer",
  fontSize: "var(--rl-fs-xs)",
  userSelect: "none",
  transition: "background-color 0.15s",
};

const dotStyle: React.CSSProperties = {
  width: "8px",
  height: "8px",
  borderRadius: "50%",
  flexShrink: 0,
};

const pulseStyle: React.CSSProperties = {
  ...dotStyle,
  animation: "pulse 1.5s ease-in-out infinite",
};

const tooltipStyle: React.CSSProperties = {
  position: "absolute",
  top: "calc(100% + 8px)",
  right: 0,
  backgroundColor: "var(--rl-bg-card)",
  border: "1px solid var(--rl-border-strong)",
  borderRadius: "8px",
  padding: "12px",
  minWidth: "240px",
  boxShadow: "0 4px 12px rgba(0, 0, 0, 0.3)",
  zIndex: 1000,
  fontSize: "var(--rl-fs-sm)",
};

const rowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "8px",
};

const labelStyle: React.CSSProperties = {
  color: "var(--rl-text-muted)",
};

const valueStyle: React.CSSProperties = {
  color: "var(--rl-text)",
  fontFamily: "var(--rl-font-mono)",
  fontSize: "var(--rl-fs-xs)",
};

const reconnectButtonStyle: React.CSSProperties = {
  marginTop: "8px",
  padding: "6px 12px",
  backgroundColor: "var(--rl-primary)",
  color: "white",
  border: "none",
  borderRadius: "4px",
  cursor: "pointer",
  fontSize: "var(--rl-fs-xs)",
  width: "100%",
};

export function ConnectionBadge({ health, onReconnect }: ConnectionBadgeProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  const color = STATE_COLORS[health.state];
  const label = STATE_LABELS[health.state];
  const isPulsing = health.state === "reconnecting";

  const formatTime = (date: Date | null): string => {
    if (!date) return "Never";
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    if (diffMs < 1000) return "Just now";
    if (diffMs < 60000) return `${Math.floor(diffMs / 1000)}s ago`;
    if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)}m ago`;
    return date.toLocaleTimeString();
  };

  return (
    <div
      data-testid="connection-badge"
      style={badgeContainerStyle}
      onClick={() => setShowTooltip(!showTooltip)}
      onMouseLeave={() => setShowTooltip(false)}
      title={`SSE: ${label}`}
    >
      {/* Pulse animation keyframes - inject once */}
      <style>
        {`
          @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
          }
        `}
      </style>

      {/* Status dot */}
      <div
        style={{
          ...(isPulsing ? pulseStyle : dotStyle),
          backgroundColor: color,
        }}
      />

      {/* Label */}
      <span style={{ color: health.state === "connected" ? "var(--rl-text-muted)" : color }}>
        {label}
      </span>

      {/* Tooltip */}
      {showTooltip && (
        <div style={tooltipStyle} onClick={(e) => e.stopPropagation()}>
          <div
            style={{
              fontSize: "var(--rl-fs-base)",
              fontWeight: 600,
              marginBottom: "12px",
              color: "var(--rl-text)",
            }}
          >
            SSE Connection
          </div>

          <div style={rowStyle}>
            <span style={labelStyle}>Status</span>
            <span style={{ ...valueStyle, color }}>{label}</span>
          </div>

          <div style={rowStyle}>
            <span style={labelStyle}>Base URL</span>
            <span style={valueStyle}>{health.baseUrl || "Not set"}</span>
          </div>

          <div style={rowStyle}>
            <span style={labelStyle}>Last Event ID</span>
            <span style={valueStyle}>{health.lastEventId ?? "None"}</span>
          </div>

          <div style={rowStyle}>
            <span style={labelStyle}>Last Message</span>
            <span style={valueStyle}>{formatTime(health.lastMessageAt)}</span>
          </div>

          {health.state === "reconnecting" && (
            <div style={{ ...rowStyle, marginBottom: 0 }}>
              <span style={labelStyle}>Reconnect Attempt</span>
              <span style={valueStyle}>#{health.reconnectAttempt}</span>
            </div>
          )}

          {health.state === "disconnected" && onReconnect && (
            <button style={reconnectButtonStyle} onClick={onReconnect}>
              Reconnect
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default ConnectionBadge;
