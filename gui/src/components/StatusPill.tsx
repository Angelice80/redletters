/**
 * StatusPill component - Shows connection state.
 *
 * Colors:
 * - Connected: Green
 * - Degraded: Orange (heartbeat stale >10s)
 * - Disconnected: Red
 */

import type { ConnectionState } from "../api/types";

interface StatusPillProps {
  state: ConnectionState;
  className?: string;
}

const COLORS: Record<ConnectionState, { bg: string; text: string }> = {
  connected: { bg: "#22c55e", text: "#ffffff" },
  degraded: { bg: "#f97316", text: "#ffffff" },
  disconnected: { bg: "#ef4444", text: "#ffffff" },
};

const LABELS: Record<ConnectionState, string> = {
  connected: "Connected",
  degraded: "Degraded",
  disconnected: "Disconnected",
};

export function StatusPill({ state, className = "" }: StatusPillProps) {
  const colors = COLORS[state];

  return (
    <span
      className={className}
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "4px 12px",
        borderRadius: "9999px",
        backgroundColor: colors.bg,
        color: colors.text,
        fontSize: "12px",
        fontWeight: 600,
        textTransform: "uppercase",
        letterSpacing: "0.05em",
      }}
    >
      <span
        style={{
          width: "8px",
          height: "8px",
          borderRadius: "50%",
          backgroundColor: colors.text,
          marginRight: "6px",
          animation: state === "connected" ? "pulse 2s infinite" : undefined,
        }}
      />
      {LABELS[state]}
    </span>
  );
}
