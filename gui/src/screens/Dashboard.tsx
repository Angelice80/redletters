/**
 * Dashboard screen - Shows engine status overview.
 * Sprint 21: Added skeleton loaders and empty states.
 * Visual Polish v2 (P12): Added Continue Studying, System Overview, Recent Activity blocks.
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { StatusPill } from "../components/StatusPill";
import { Skeleton, SkeletonStats, EmptyState } from "../components/Skeleton";
import { useAppStore, checkConnectionHealth, selectJobs } from "../store";
import type { ConnectionState } from "../api/types";
import { theme } from "../theme";
import { RECENT_REFS_KEY } from "../constants/storageKeys";

const dashCardStyle: React.CSSProperties = {
  padding: "16px",
  backgroundColor: "var(--rl-bg-card)",
  borderRadius: "var(--rl-radius-lg)",
  border: "1px solid var(--rl-border)",
  borderTop: "1px solid var(--rl-border-subtle)",
  boxShadow: "var(--rl-shadow-md)",
};

export function Dashboard() {
  const engineStatus = useAppStore((state) => state.engineStatus);
  const lastHeartbeat = useAppStore((state) => state.lastHeartbeat);
  const connectionState = useAppStore((state) => state.connectionState);
  const jobs = useAppStore(selectJobs);
  const navigate = useNavigate();
  const [displayState, setDisplayState] =
    useState<ConnectionState>(connectionState);

  // Read recent refs from localStorage
  const recentRefs: string[] = (() => {
    try {
      const raw = localStorage.getItem(RECENT_REFS_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  })();

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
        <h1 style={{ margin: 0 }}>Dashboard</h1>
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
                borderTop: "1px solid var(--rl-border-subtle)",
                boxShadow: "var(--rl-shadow-md)",
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
                borderTop: "1px solid var(--rl-border-subtle)",
                boxShadow: "var(--rl-shadow-md)",
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
                borderTop: "1px solid var(--rl-border-subtle)",
                boxShadow: "var(--rl-shadow-md)",
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
                borderTop: "1px solid var(--rl-border-subtle)",
                boxShadow: "var(--rl-shadow-md)",
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
                borderTop: "1px solid var(--rl-border-subtle)",
                boxShadow: "var(--rl-shadow-md)",
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
                borderTop: "1px solid var(--rl-border-subtle)",
                boxShadow: "var(--rl-shadow-md)",
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

          {/* Bottom grid: Continue Studying + System + Recent Activity */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "16px",
              marginTop: "24px",
            }}
          >
            {/* Continue Studying */}
            <div style={dashCardStyle}>
              <h2 style={{ marginBottom: "12px", color: "var(--rl-text)" }}>
                Continue Studying
              </h2>
              {recentRefs.length > 0 ? (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "6px",
                  }}
                >
                  {recentRefs.slice(0, 5).map((ref) => (
                    <button
                      key={ref}
                      onClick={() =>
                        navigate(`/explore?ref=${encodeURIComponent(ref)}`)
                      }
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        padding: "8px 12px",
                        backgroundColor: "var(--rl-bg-hover)",
                        border: "1px solid var(--rl-border)",
                        borderRadius: "var(--rl-radius-sm)",
                        color: "var(--rl-text)",
                        cursor: "pointer",
                        fontSize: "var(--rl-fs-sm)",
                        textAlign: "left",
                        transition:
                          "background-color var(--rl-transition-fast)",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor =
                          "var(--rl-accent-subtle)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor =
                          "var(--rl-bg-hover)";
                      }}
                    >
                      <span
                        style={{
                          color: "var(--rl-accent)",
                          fontSize: "var(--rl-fs-xs)",
                        }}
                      >
                        &#9654;
                      </span>
                      {ref}
                    </button>
                  ))}
                </div>
              ) : (
                <div
                  style={{
                    color: "var(--rl-text-dim)",
                    fontSize: "var(--rl-fs-sm)",
                  }}
                >
                  No recent passages. Visit{" "}
                  <button
                    onClick={() => navigate("/explore")}
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--rl-accent)",
                      cursor: "pointer",
                      fontSize: "inherit",
                      textDecoration: "underline",
                      padding: 0,
                    }}
                  >
                    Explore
                  </button>{" "}
                  to start studying.
                </div>
              )}
            </div>

            {/* System Overview */}
            <div style={dashCardStyle}>
              <h2 style={{ marginBottom: "12px", color: "var(--rl-text)" }}>
                System Overview
              </h2>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "auto 1fr",
                  gap: "6px 16px",
                  fontSize: "var(--rl-fs-sm)",
                }}
              >
                <span style={{ color: "var(--rl-text-dim)" }}>
                  API Version:
                </span>
                <span>{engineStatus?.api_version ?? "---"}</span>

                <span style={{ color: "var(--rl-text-dim)" }}>
                  Capabilities:
                </span>
                <span style={{ fontSize: "var(--rl-fs-xs)" }}>
                  {engineStatus?.capabilities?.join(", ") || "none"}
                </span>

                <span style={{ color: "var(--rl-text-dim)" }}>Health:</span>
                <span
                  style={{
                    color:
                      engineStatus?.health === "healthy"
                        ? "var(--rl-success)"
                        : "var(--rl-warning)",
                    fontWeight: 600,
                  }}
                >
                  {engineStatus?.health ?? "---"}
                </span>

                <span style={{ color: "var(--rl-text-dim)" }}>
                  Last heartbeat:
                </span>
                <span>
                  {lastHeartbeat
                    ? new Date(lastHeartbeat).toLocaleTimeString()
                    : "Never"}
                </span>
              </div>
            </div>

            {/* Recent Activity */}
            <div style={{ ...dashCardStyle, gridColumn: "1 / -1" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "12px",
                }}
              >
                <h2 style={{ margin: 0, color: "var(--rl-text)" }}>
                  Recent Activity
                </h2>
                <button
                  onClick={() => navigate("/jobs")}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--rl-accent)",
                    cursor: "pointer",
                    fontSize: "var(--rl-fs-sm)",
                    fontWeight: 500,
                  }}
                >
                  View all jobs &rarr;
                </button>
              </div>
              {jobs.length > 0 ? (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  {jobs.slice(0, 4).map((job) => (
                    <div
                      key={job.job_id}
                      onClick={() => navigate(`/jobs`)}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: "10px 12px",
                        backgroundColor: "var(--rl-bg-hover)",
                        borderRadius: "var(--rl-radius-sm)",
                        cursor: "pointer",
                        border: "1px solid var(--rl-border)",
                        transition:
                          "background-color var(--rl-transition-fast)",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor =
                          "var(--rl-accent-subtle)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor =
                          "var(--rl-bg-hover)";
                      }}
                    >
                      <div>
                        <div
                          style={{
                            fontSize: "var(--rl-fs-sm)",
                            fontFamily: "var(--rl-font-mono)",
                            color: "var(--rl-text-muted)",
                          }}
                        >
                          {job.job_id.slice(0, 30)}
                        </div>
                        {job.config.reference && (
                          <div
                            style={{
                              fontSize: "var(--rl-fs-xs)",
                              color: "var(--rl-primary)",
                              marginTop: "2px",
                            }}
                          >
                            {job.config.reference}
                          </div>
                        )}
                      </div>
                      <span
                        style={{
                          padding: "3px 8px",
                          borderRadius: "var(--rl-radius-sm)",
                          fontSize: "var(--rl-fs-xs)",
                          fontWeight: 600,
                          textTransform: "uppercase",
                          backgroundColor:
                            job.state === "completed"
                              ? "rgba(34, 197, 94, 0.15)"
                              : job.state === "failed"
                                ? "rgba(239, 68, 68, 0.15)"
                                : "rgba(59, 130, 246, 0.15)",
                          color:
                            job.state === "completed"
                              ? "var(--rl-success)"
                              : job.state === "failed"
                                ? "var(--rl-error)"
                                : "var(--rl-primary)",
                        }}
                      >
                        {job.state}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div
                  style={{
                    color: "var(--rl-text-dim)",
                    fontSize: "var(--rl-fs-sm)",
                  }}
                >
                  No recent jobs.{" "}
                  <button
                    onClick={() => navigate("/jobs")}
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--rl-accent)",
                      cursor: "pointer",
                      fontSize: "inherit",
                      textDecoration: "underline",
                      padding: 0,
                    }}
                  >
                    Start a demo job
                  </button>{" "}
                  to see activity here.
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
