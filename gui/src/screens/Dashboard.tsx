/**
 * Dashboard screen - Shows engine status overview.
 * Sprint 21: Added skeleton loaders and empty states.
 */

import { useEffect, useState } from "react";
import { StatusPill } from "../components/StatusPill";
import { Skeleton, SkeletonStats, EmptyState } from "../components/Skeleton";
import { useAppStore, checkConnectionHealth } from "../store";
import type { ConnectionState } from "../api/types";
import { theme } from "../theme";

export function Dashboard() {
  const engineStatus = useAppStore((state) => state.engineStatus);
  const lastHeartbeat = useAppStore((state) => state.lastHeartbeat);
  const connectionState = useAppStore((state) => state.connectionState);
  const [displayState, setDisplayState] =
    useState<ConnectionState>(connectionState);

  // Update display state based on heartbeat staleness
  useEffect(() => {
    const interval = setInterval(() => {
      const newState = checkConnectionHealth(
        lastHeartbeat,
        connectionState === "connected",
      );
      setDisplayState(newState);
    }, 1000);

    return () => clearInterval(interval);
  }, [lastHeartbeat, connectionState]);

  const formatUptime = (seconds: number) => {
    if (seconds < 60) return `${Math.floor(seconds)}s`;
    if (seconds < 3600)
      return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${mins}m`;
  };

  const isDisconnected = displayState === "disconnected";
  const isLoading = !isDisconnected && !engineStatus;

  return (
    <div style={{ padding: "24px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "24px",
        }}
      >
        <h1 style={{ fontSize: "var(--rl-fs-xl)", fontWeight: 600, margin: 0 }}>
          Dashboard
        </h1>
        <StatusPill state={displayState} />
      </div>

      {/* Empty state when disconnected */}
      {isDisconnected && (
        <EmptyState
          icon="&#128268;"
          title="Not Connected"
          description="Connect to the Red Letters backend to see engine status and manage jobs."
        />
      )}

      {/* Loading skeleton */}
      {isLoading && (
        <div>
          <SkeletonStats count={6} />
          <div style={{ marginTop: theme.spacing.lg }}>
            <Skeleton height="120px" borderRadius={theme.borderRadius.lg} />
          </div>
        </div>
      )}

      {/* Status Cards - only show when connected and have data */}
      {!isDisconnected && !isLoading && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: "16px",
              marginBottom: "24px",
            }}
          >
            {/* Version Card */}
            <div
              style={{
                padding: "16px",
                backgroundColor: "var(--rl-bg-card)",
                borderRadius: "var(--rl-radius-lg)",
                border: "1px solid var(--rl-border)",
                boxShadow: "var(--rl-shadow-sm)",
              }}
            >
              <div
                style={{
                  color: "var(--rl-text-muted)",
                  fontSize: "var(--rl-fs-sm)",
                  marginBottom: "4px",
                }}
              >
                Version
              </div>
              <div style={{ fontSize: "var(--rl-fs-lg)", fontWeight: 600 }}>
                {engineStatus?.version ?? "---"}
              </div>
              <div
                style={{
                  color: "var(--rl-text-dim)",
                  fontSize: "var(--rl-fs-xs)",
                  fontFamily: "var(--rl-font-mono)",
                }}
              >
                {engineStatus?.build_hash?.slice(0, 8) ?? ""}
              </div>
            </div>

            {/* Mode Card */}
            <div
              style={{
                padding: "16px",
                backgroundColor: "var(--rl-bg-card)",
                borderRadius: "var(--rl-radius-lg)",
                border: "1px solid var(--rl-border)",
                boxShadow: "var(--rl-shadow-sm)",
              }}
            >
              <div
                style={{
                  color: "var(--rl-text-muted)",
                  fontSize: "var(--rl-fs-sm)",
                  marginBottom: "4px",
                }}
              >
                Mode
              </div>
              <div
                style={{
                  fontSize: "var(--rl-fs-lg)",
                  fontWeight: 600,
                  color:
                    engineStatus?.mode === "safe"
                      ? "var(--rl-warning)"
                      : "var(--rl-success)",
                }}
              >
                {engineStatus?.mode === "safe" ? "Safe Mode" : "Normal"}
              </div>
            </div>

            {/* Uptime Card */}
            <div
              style={{
                padding: "16px",
                backgroundColor: "var(--rl-bg-card)",
                borderRadius: "var(--rl-radius-lg)",
                border: "1px solid var(--rl-border)",
                boxShadow: "var(--rl-shadow-sm)",
              }}
            >
              <div
                style={{
                  color: "var(--rl-text-muted)",
                  fontSize: "var(--rl-fs-sm)",
                  marginBottom: "4px",
                }}
              >
                Uptime
              </div>
              <div style={{ fontSize: "var(--rl-fs-lg)", fontWeight: 600 }}>
                {engineStatus
                  ? formatUptime(engineStatus.uptime_seconds)
                  : "---"}
              </div>
            </div>

            {/* Active Jobs Card */}
            <div
              style={{
                padding: "16px",
                backgroundColor: "var(--rl-bg-card)",
                borderRadius: "var(--rl-radius-lg)",
                border: "1px solid var(--rl-border)",
                boxShadow: "var(--rl-shadow-sm)",
              }}
            >
              <div
                style={{
                  color: "var(--rl-text-muted)",
                  fontSize: "var(--rl-fs-sm)",
                  marginBottom: "4px",
                }}
              >
                Active Jobs
              </div>
              <div style={{ fontSize: "var(--rl-fs-lg)", fontWeight: 600 }}>
                {engineStatus?.active_jobs ?? "---"}
              </div>
            </div>

            {/* Queue Depth Card */}
            <div
              style={{
                padding: "16px",
                backgroundColor: "var(--rl-bg-card)",
                borderRadius: "var(--rl-radius-lg)",
                border: "1px solid var(--rl-border)",
                boxShadow: "var(--rl-shadow-sm)",
              }}
            >
              <div
                style={{
                  color: "var(--rl-text-muted)",
                  fontSize: "var(--rl-fs-sm)",
                  marginBottom: "4px",
                }}
              >
                Queue Depth
              </div>
              <div style={{ fontSize: "var(--rl-fs-lg)", fontWeight: 600 }}>
                {engineStatus?.queue_depth ?? "---"}
              </div>
            </div>

            {/* Health Card */}
            <div
              style={{
                padding: "16px",
                backgroundColor: "var(--rl-bg-card)",
                borderRadius: "var(--rl-radius-lg)",
                border: "1px solid var(--rl-border)",
                boxShadow: "var(--rl-shadow-sm)",
              }}
            >
              <div
                style={{
                  color: "var(--rl-text-muted)",
                  fontSize: "var(--rl-fs-sm)",
                  marginBottom: "4px",
                }}
              >
                Health
              </div>
              <div
                style={{
                  fontSize: "var(--rl-fs-lg)",
                  fontWeight: 600,
                  color:
                    engineStatus?.health === "healthy"
                      ? "var(--rl-success)"
                      : "var(--rl-warning)",
                }}
              >
                {engineStatus?.health ?? "---"}
              </div>
            </div>
          </div>

          {/* API Info */}
          <div
            style={{
              padding: "16px",
              backgroundColor: "var(--rl-bg-card)",
              borderRadius: "8px",
            }}
          >
            <div
              style={{
                color: "var(--rl-text-muted)",
                fontSize: "var(--rl-fs-sm)",
                marginBottom: "8px",
              }}
            >
              API Information
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "auto 1fr",
                gap: "4px 16px",
                fontSize: "var(--rl-fs-base)",
              }}
            >
              <span style={{ color: "var(--rl-text-dim)" }}>API Version:</span>
              <span>{engineStatus?.api_version ?? "---"}</span>

              <span style={{ color: "var(--rl-text-dim)" }}>Capabilities:</span>
              <span>{engineStatus?.capabilities?.join(", ") || "none"}</span>
            </div>
          </div>

          {/* Connection Info */}
          <div
            style={{
              marginTop: "16px",
              padding: "12px 16px",
              backgroundColor: "var(--rl-bg-app)",
              borderRadius: "4px",
              fontSize: "var(--rl-fs-sm)",
              color: "var(--rl-text-dim)",
            }}
          >
            Last heartbeat:{" "}
            {lastHeartbeat
              ? new Date(lastHeartbeat).toLocaleTimeString()
              : "Never"}
          </div>
        </>
      )}
    </div>
  );
}
