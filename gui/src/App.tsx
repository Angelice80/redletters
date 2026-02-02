/**
 * Main App component with navigation and global state management.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  NavLink,
  Navigate,
} from "react-router-dom";
import { invoke } from "@tauri-apps/api/core";

import { Dashboard } from "./screens/Dashboard";
import { Jobs } from "./screens/Jobs";
import { JobDetail } from "./screens/JobDetail";
import { Diagnostics } from "./screens/Diagnostics";
import { Settings } from "./screens/Settings";
import { Translate } from "./screens/Translate";
import { Gate } from "./screens/Gate";
import { Sources } from "./screens/Sources";

import { useAppStore, selectSettings, checkConnectionHealth } from "./store";
import { useEventStream } from "./hooks/useEventStream";
import { useEngineStatus } from "./hooks/useEngineStatus";
import { useJobs } from "./hooks/useJobs";
import { createApiClient, ApiClient } from "./api/client";
import type { SSEEvent, ConnectionState } from "./api/types";

// Nav link styles
const navLinkStyle = {
  display: "block",
  padding: "12px 16px",
  color: "#9ca3af",
  textDecoration: "none",
  borderRadius: "4px",
  fontSize: "14px",
  transition: "background-color 0.15s, color 0.15s",
};

const navLinkActiveStyle = {
  ...navLinkStyle,
  backgroundColor: "#3b82f6",
  color: "white",
};

export function App() {
  const settings = useAppStore(selectSettings);
  const setEngineStatus = useAppStore((state) => state.setEngineStatus);
  const setConnectionState = useAppStore((state) => state.setConnectionState);
  const processEvent = useAppStore((state) => state.processEvent);
  const setJobs = useAppStore((state) => state.setJobs);
  const lastHeartbeat = useAppStore((state) => state.lastHeartbeat);

  const [token, setToken] = useState<string>("");
  const [tokenSource, setTokenSource] = useState<string>("");
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [sseConnected, setSseConnected] = useState(false);

  // Create API client
  const client = useMemo<ApiClient | null>(() => {
    if (!token) return null;
    return createApiClient(settings.enginePort, token);
  }, [settings.enginePort, token]);

  // Update client when settings change
  useEffect(() => {
    if (client) {
      client.setBaseUrl(`http://127.0.0.1:${settings.enginePort}`);
    }
  }, [client, settings.enginePort]);

  // Load auth token from keychain
  useEffect(() => {
    const loadToken = async () => {
      try {
        const result = await invoke<{ token: string; source: string }>(
          "get_auth_token",
        );
        setToken(result.token);
        setTokenSource(result.source);
        setTokenError(null);
      } catch (err) {
        console.error("Failed to get auth token:", err);
        setTokenError(String(err));
        // Try with empty token for testing
        setToken("");
      }
    };

    loadToken();
  }, []);

  // Event stream
  const handleEvent = useCallback(
    (event: SSEEvent) => {
      processEvent(event);
    },
    [processEvent],
  );

  const handleConnect = useCallback(() => {
    setSseConnected(true);
    setConnectionState("connected");
  }, [setConnectionState]);

  const handleDisconnect = useCallback(() => {
    setSseConnected(false);
    setConnectionState("disconnected");
  }, [setConnectionState]);

  const {
    connected: streamConnected,
    reconnect,
    testReconnection,
  } = useEventStream({
    baseUrl: `http://127.0.0.1:${settings.enginePort}`,
    token,
    enabled: !!token,
    onEvent: handleEvent,
    onConnect: handleConnect,
    onDisconnect: handleDisconnect,
    onError: (err) => console.error("SSE error:", err),
  });

  // Engine status polling (backup for when SSE doesn't have status)
  const { status, refresh: refreshStatus } = useEngineStatus({
    client,
    pollInterval: 30000, // Poll every 30s as backup
    enabled: !!client,
  });

  useEffect(() => {
    if (status) {
      setEngineStatus(status);
    }
  }, [status, setEngineStatus]);

  // Jobs
  const { jobs, refresh: refreshJobs } = useJobs({
    client,
    enabled: !!client,
  });

  useEffect(() => {
    if (jobs.length > 0) {
      setJobs(jobs);
    }
  }, [jobs, setJobs]);

  // Update connection state based on heartbeat
  useEffect(() => {
    const interval = setInterval(() => {
      const state = checkConnectionHealth(lastHeartbeat, sseConnected);
      setConnectionState(state);
    }, 1000);

    return () => clearInterval(interval);
  }, [lastHeartbeat, sseConnected, setConnectionState]);

  // Computed connection state for display
  const displayConnectionState: ConnectionState = checkConnectionHealth(
    lastHeartbeat,
    sseConnected,
  );

  const handleReconnect = useCallback(() => {
    reconnect();
    refreshStatus();
    refreshJobs();
  }, [reconnect, refreshStatus, refreshJobs]);

  return (
    <BrowserRouter>
      <div
        style={{
          display: "flex",
          height: "100vh",
          backgroundColor: "#1a1a2e",
          color: "#eaeaea",
        }}
      >
        {/* Sidebar */}
        <nav
          style={{
            width: "200px",
            backgroundColor: "#2d2d44",
            padding: "16px",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div
            style={{
              fontSize: "20px",
              fontWeight: 700,
              color: "#ef4444",
              marginBottom: "24px",
              padding: "8px",
            }}
          >
            Red Letters
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <NavLink
              to="/"
              style={({ isActive }) =>
                isActive ? navLinkActiveStyle : navLinkStyle
              }
            >
              Dashboard
            </NavLink>
            <NavLink
              to="/translate"
              style={({ isActive }) =>
                isActive ? navLinkActiveStyle : navLinkStyle
              }
            >
              Translate
            </NavLink>
            <NavLink
              to="/sources"
              style={({ isActive }) =>
                isActive ? navLinkActiveStyle : navLinkStyle
              }
            >
              Sources
            </NavLink>
            <NavLink
              to="/jobs"
              style={({ isActive }) =>
                isActive ? navLinkActiveStyle : navLinkStyle
              }
            >
              Jobs
            </NavLink>
            <NavLink
              to="/diagnostics"
              style={({ isActive }) =>
                isActive ? navLinkActiveStyle : navLinkStyle
              }
            >
              Diagnostics
            </NavLink>
            <NavLink
              to="/settings"
              style={({ isActive }) =>
                isActive ? navLinkActiveStyle : navLinkStyle
              }
            >
              Settings
            </NavLink>
          </div>

          {/* Status footer */}
          <div
            style={{
              marginTop: "auto",
              padding: "12px",
              backgroundColor: "#1a1a2e",
              borderRadius: "4px",
              fontSize: "11px",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                marginBottom: "4px",
              }}
            >
              <span
                style={{
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  backgroundColor:
                    displayConnectionState === "connected"
                      ? "#22c55e"
                      : displayConnectionState === "degraded"
                        ? "#f59e0b"
                        : "#ef4444",
                }}
              />
              <span style={{ textTransform: "capitalize" }}>
                {displayConnectionState}
              </span>
            </div>
            <div style={{ color: "#6b7280" }}>Port: {settings.enginePort}</div>
            {tokenSource && (
              <div style={{ color: "#6b7280" }}>Token: {tokenSource}</div>
            )}
          </div>
        </nav>

        {/* Main content */}
        <main style={{ flex: 1, overflow: "auto" }}>
          {tokenError && !token && (
            <div
              style={{
                padding: "12px 16px",
                backgroundColor: "#f59e0b",
                color: "#1a1a2e",
                fontSize: "13px",
              }}
            >
              No auth token found. Set one in your keychain or create
              ~/.greek2english/.auth_token
            </div>
          )}

          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/translate" element={<Translate client={client} />} />
            <Route path="/gate" element={<Gate client={client} />} />
            <Route path="/sources" element={<Sources client={client} />} />
            <Route
              path="/jobs"
              element={<Jobs client={client} onRefresh={refreshJobs} />}
            />
            <Route
              path="/jobs/:jobId"
              element={<JobDetail client={client} />}
            />
            <Route
              path="/diagnostics"
              element={<Diagnostics client={client} />}
            />
            <Route
              path="/settings"
              element={
                <Settings
                  engineMode={status?.mode}
                  onReconnect={handleReconnect}
                  onTestReconnection={testReconnection}
                />
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
