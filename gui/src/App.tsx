/**
 * Main App component with navigation and global state management.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AUTH_TOKEN_KEY,
  BOOTSTRAP_COMPLETED_KEY,
} from "./constants/storageKeys";
import { useMediaQuery } from "./hooks/useMediaQuery";
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
import { PassageWorkspace } from "./screens/PassageWorkspace";
import { Gate } from "./screens/Gate";
import { Sources } from "./screens/Sources";
import { ExportView } from "./screens/ExportView";
import { ConnectionPanel } from "./components/ConnectionPanel";
import { ConnectionBadge } from "./components/ConnectionBadge";
import { BootstrapWizard } from "./components/BootstrapWizard";
import { CompatibilityModal } from "./components/CompatibilityModal";
import { ConnectionSettingsModal } from "./components/ConnectionSettingsModal";

import { useAppStore, selectSettings, checkConnectionHealth } from "./store";
import { useEventStream } from "./hooks/useEventStream";
import { useEngineStatus } from "./hooks/useEngineStatus";
import { useJobs } from "./hooks/useJobs";
import { createApiClient, ApiClient, validateCapabilities } from "./api/client";
import type {
  SSEEvent,
  SSEHealthInfo,
  ConnectionState,
  ApiCapabilities,
  CapabilitiesValidation,
} from "./api/types";

// Nav link styles
const navLinkStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  padding: "8px 12px",
  color: "var(--rl-text-muted)",
  textDecoration: "none",
  borderRadius: "var(--rl-radius-sm)",
  fontSize: "var(--rl-fs-sm)",
  transition:
    "background-color var(--rl-transition-fast), color var(--rl-transition-fast)",
  borderLeft: "3px solid transparent",
};

const navLinkActiveStyle: React.CSSProperties = {
  ...navLinkStyle,
  backgroundColor: "var(--rl-accent-subtle)",
  color: "var(--rl-text)",
  borderLeft: "3px solid var(--rl-accent)",
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
  const [sseHealth, setSseHealth] = useState<SSEHealthInfo>({
    state: "disconnected",
    baseUrl: "",
    lastEventId: null,
    lastMessageAt: null,
    reconnectAttempt: 0,
  });

  // Sprint 16: Capabilities and bootstrap state
  const [capabilities, setCapabilities] = useState<ApiCapabilities | null>(
    null,
  );
  const [showBootstrap, setShowBootstrap] = useState(false);
  const [bootstrapChecked, setBootstrapChecked] = useState(false);

  // Sprint 17: Compatibility validation state
  const [compatibilityValidation, setCompatibilityValidation] =
    useState<CapabilitiesValidation | null>(null);
  const [showCompatibilityModal, setShowCompatibilityModal] = useState(false);
  const [capabilitiesReady, setCapabilitiesReady] = useState(false);

  // Sprint 21: Connection settings modal state
  const [showSettingsModal, setShowSettingsModal] = useState(false);

  // UX3.2: Responsive sidebar
  const isMobileSidebar = useMediaQuery("(max-width: 640px)");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Create API client
  const client = useMemo<ApiClient | null>(() => {
    if (!token) return null;
    return createApiClient(settings.enginePort, token);
  }, [settings.enginePort, token]);

  // Update client and SSE health when settings change
  useEffect(() => {
    if (client) {
      client.setBaseUrl(`http://127.0.0.1:${settings.enginePort}`);
    }
    setSseHealth((prev) => ({
      ...prev,
      baseUrl: `http://127.0.0.1:${settings.enginePort}`,
    }));
  }, [client, settings.enginePort]);

  // Load auth token from keychain (Tauri) or localStorage (browser)
  // Note: URL hash token is handled in index.html before React loads
  useEffect(() => {
    const loadToken = async () => {
      // Check if running in Tauri (desktop app)
      const isTauri = "__TAURI__" in window;

      if (isTauri) {
        try {
          const result = await invoke<{ token: string; source: string }>(
            "get_auth_token",
          );
          setToken(result.token);
          setTokenSource(result.source);
          setTokenError(null);
          return;
        } catch (err) {
          console.error("Failed to get auth token from Tauri:", err);
        }
      }

      // Browser: check localStorage (includes auto-injected tokens from URL hash)
      const storedToken = localStorage.getItem(AUTH_TOKEN_KEY);
      if (storedToken) {
        setToken(storedToken);
        setTokenSource("localStorage");
        setTokenError(null);
        return;
      }

      // No token found - show settings modal
      console.warn("No auth token found. Opening settings modal.");
      setTokenError("No auth token configured");
      setToken("");
      setShowSettingsModal(true);
    };

    loadToken();
  }, []);

  // Handler for saving connection settings from modal
  const handleSaveConnectionSettings = useCallback(
    (newToken: string, newPort: number) => {
      // Save token to localStorage
      localStorage.setItem(AUTH_TOKEN_KEY, newToken);

      // Update state
      setToken(newToken);
      setTokenSource("localStorage");
      setTokenError(null);

      // Update port in store
      useAppStore.getState().updateSettings({ enginePort: newPort });

      // Close modal
      setShowSettingsModal(false);

      // Reconnect will happen automatically due to token change
    },
    [],
  );

  // Handler to open settings modal
  const handleOpenSettings = useCallback(() => {
    setShowSettingsModal(true);
  }, []);

  // Event stream
  const handleEvent = useCallback(
    (event: SSEEvent) => {
      processEvent(event);
      // Update SSE health tracking
      setSseHealth((prev) => ({
        ...prev,
        lastMessageAt: new Date(),
        lastEventId: event.sequence_number ?? prev.lastEventId,
      }));
    },
    [processEvent],
  );

  const handleConnect = useCallback(() => {
    setSseConnected(true);
    setConnectionState("connected");
    setSseHealth((prev) => ({
      ...prev,
      state: "connected",
      lastMessageAt: new Date(),
    }));
  }, [setConnectionState]);

  const handleDisconnect = useCallback(() => {
    setSseConnected(false);
    setConnectionState("disconnected");
    setSseHealth((prev) => ({
      ...prev,
      state: "disconnected",
    }));
  }, [setConnectionState]);

  const {
    connected: _streamConnected,
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
  // Only poll when SSE is connected to avoid noise when backend is down
  const { status, refresh: refreshStatus } = useEngineStatus({
    client,
    pollInterval: 30000, // Poll every 30s as backup
    enabled: !!client && sseConnected,
  });

  useEffect(() => {
    if (status) {
      setEngineStatus(status);
    }
  }, [status, setEngineStatus]);

  // Sprint 16/17: Check capabilities and validate compatibility on connect
  useEffect(() => {
    const checkCapabilities = async () => {
      if (!client || !sseConnected) return;

      try {
        const caps = await client.getCapabilities();
        setCapabilities(caps);

        // Sprint 17: Validate compatibility
        const validation = validateCapabilities(caps);
        setCompatibilityValidation(validation);

        if (!validation.valid) {
          // Show blocking modal if incompatible
          setShowCompatibilityModal(true);
          setCapabilitiesReady(false);
        } else {
          // Compatibility check passed
          setShowCompatibilityModal(false);
          setCapabilitiesReady(true);

          // Check if first run (no bootstrap completed flag in localStorage)
          const bootstrapCompleted = localStorage.getItem(
            BOOTSTRAP_COMPLETED_KEY,
          );
          if (!bootstrapCompleted && !bootstrapChecked) {
            setShowBootstrap(true);
          }
        }
        setBootstrapChecked(true);
      } catch (err) {
        console.warn("Failed to get capabilities:", err);
        // Don't show bootstrap on error - user might be on older backend
        setBootstrapChecked(true);
        setCapabilitiesReady(false);
      }
    };

    checkCapabilities();
  }, [client, sseConnected, bootstrapChecked]);

  // Bootstrap wizard handlers
  const handleBootstrapComplete = useCallback(() => {
    localStorage.setItem(BOOTSTRAP_COMPLETED_KEY, "true");
    setShowBootstrap(false);
  }, []);

  const handleBootstrapSkip = useCallback(() => {
    localStorage.setItem(BOOTSTRAP_COMPLETED_KEY, "skipped");
    setShowBootstrap(false);
  }, []);

  // Jobs - only fetch when SSE is connected to avoid noise when backend is down
  const { jobs, refresh: refreshJobs } = useJobs({
    client,
    enabled: !!client && sseConnected,
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

  // Sprint 17: Handler for retrying capability check
  const handleRetryCapabilityCheck = useCallback(async () => {
    if (!client) return;

    try {
      const caps = await client.getCapabilities();
      setCapabilities(caps);

      const validation = validateCapabilities(caps);
      setCompatibilityValidation(validation);

      if (validation.valid) {
        setShowCompatibilityModal(false);
        setCapabilitiesReady(true);
      }
    } catch (err) {
      console.warn("Failed to get capabilities:", err);
    }
  }, [client]);

  return (
    <BrowserRouter>
      <div
        style={{
          display: "flex",
          height: "100vh",
          backgroundColor: "var(--rl-bg-app)",
          color: "var(--rl-text)",
        }}
      >
        {/* UX3.2: Hamburger button for mobile */}
        {isMobileSidebar && (
          <button
            data-testid="hamburger-btn"
            aria-label={sidebarOpen ? "Close menu" : "Open menu"}
            onClick={() => setSidebarOpen((o) => !o)}
            style={{
              position: "fixed",
              top: "8px",
              left: "8px",
              zIndex: 1100,
              width: "36px",
              height: "36px",
              backgroundColor: "var(--rl-bg-card)",
              border: "1px solid var(--rl-border-strong)",
              borderRadius: "var(--rl-radius-md)",
              color: "var(--rl-text)",
              fontSize: "var(--rl-fs-lg)",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {sidebarOpen ? "\u2715" : "\u2630"}
          </button>
        )}

        {/* Sidebar — hidden on mobile unless hamburger toggled */}
        {(!isMobileSidebar || sidebarOpen) && (
          <>
            {/* Overlay backdrop on mobile */}
            {isMobileSidebar && sidebarOpen && (
              <div
                data-testid="sidebar-backdrop"
                onClick={() => setSidebarOpen(false)}
                style={{
                  position: "fixed",
                  inset: 0,
                  backgroundColor: "rgba(0,0,0,0.5)",
                  zIndex: 1199,
                }}
              />
            )}
            <nav
              data-testid="sidebar-nav"
              style={{
                width: "200px",
                backgroundColor: "var(--rl-bg-panel)",
                padding: "16px",
                display: "flex",
                flexDirection: "column",
                ...(isMobileSidebar
                  ? {
                      position: "fixed",
                      top: 0,
                      left: 0,
                      bottom: 0,
                      zIndex: 1200,
                      boxShadow: "4px 0 20px rgba(0,0,0,0.5)",
                    }
                  : {}),
              }}
            >
              <div style={{ padding: "8px", marginBottom: "16px" }}>
                <div
                  style={{
                    fontSize: "var(--rl-fs-lg)",
                    fontWeight: 700,
                    color: "var(--rl-accent)",
                  }}
                >
                  Red Letters
                </div>
                <div
                  style={{
                    fontSize: "var(--rl-fs-xs)",
                    color: "var(--rl-text-dim)",
                    letterSpacing: "0.03em",
                  }}
                >
                  Greek Scholarly Tools
                </div>
              </div>

              <div
                style={{ display: "flex", flexDirection: "column", gap: "2px" }}
                onClick={() => isMobileSidebar && setSidebarOpen(false)}
              >
                {/* Study section */}
                <div
                  style={{
                    fontSize: "var(--rl-fs-xs)",
                    textTransform: "uppercase",
                    color: "var(--rl-text-dim)",
                    padding: "4px 12px",
                    marginTop: "4px",
                    letterSpacing: "0.06em",
                  }}
                >
                  Study
                </div>
                <NavLink
                  to="/explore"
                  style={({ isActive }) =>
                    isActive ? navLinkActiveStyle : navLinkStyle
                  }
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                    fill="none"
                    style={{ marginRight: "8px", flexShrink: 0 }}
                  >
                    <path
                      d="M2 2h5v5H2V2zm7 0h5v5H9V2zM2 9h5v5H2V9zm7 2.5a2.5 2.5 0 105 0 2.5 2.5 0 00-5 0z"
                      stroke="currentColor"
                      strokeWidth="1.3"
                    />
                  </svg>
                  Explore
                </NavLink>
                <NavLink
                  to="/export"
                  style={({ isActive }) =>
                    isActive ? navLinkActiveStyle : navLinkStyle
                  }
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                    fill="none"
                    style={{ marginRight: "8px", flexShrink: 0 }}
                  >
                    <path
                      d="M8 2v8m0 0l-3-3m3 3l3-3M3 12h10"
                      stroke="currentColor"
                      strokeWidth="1.3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  Export
                </NavLink>

                {/* Data section */}
                <div
                  style={{
                    fontSize: "var(--rl-fs-xs)",
                    textTransform: "uppercase",
                    color: "var(--rl-text-dim)",
                    padding: "4px 12px",
                    marginTop: "12px",
                    letterSpacing: "0.06em",
                  }}
                >
                  Data
                </div>
                <NavLink
                  to="/sources"
                  style={({ isActive }) =>
                    isActive ? navLinkActiveStyle : navLinkStyle
                  }
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                    fill="none"
                    style={{ marginRight: "8px", flexShrink: 0 }}
                  >
                    <ellipse
                      cx="8"
                      cy="4"
                      rx="5"
                      ry="2"
                      stroke="currentColor"
                      strokeWidth="1.3"
                    />
                    <path
                      d="M3 4v4c0 1.1 2.24 2 5 2s5-.9 5-2V4"
                      stroke="currentColor"
                      strokeWidth="1.3"
                    />
                    <path
                      d="M3 8v4c0 1.1 2.24 2 5 2s5-.9 5-2V8"
                      stroke="currentColor"
                      strokeWidth="1.3"
                    />
                  </svg>
                  Sources
                </NavLink>
                <NavLink
                  to="/jobs"
                  style={({ isActive }) =>
                    isActive ? navLinkActiveStyle : navLinkStyle
                  }
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                    fill="none"
                    style={{ marginRight: "8px", flexShrink: 0 }}
                  >
                    <rect
                      x="2"
                      y="3"
                      width="12"
                      height="10"
                      rx="1.5"
                      stroke="currentColor"
                      strokeWidth="1.3"
                    />
                    <path
                      d="M5 7h6M5 10h4"
                      stroke="currentColor"
                      strokeWidth="1.3"
                      strokeLinecap="round"
                    />
                  </svg>
                  Jobs
                </NavLink>

                {/* System section */}
                <div
                  style={{
                    fontSize: "var(--rl-fs-xs)",
                    textTransform: "uppercase",
                    color: "var(--rl-text-dim)",
                    padding: "4px 12px",
                    marginTop: "12px",
                    letterSpacing: "0.06em",
                  }}
                >
                  System
                </div>
                <NavLink
                  to="/"
                  style={({ isActive }) =>
                    isActive ? navLinkActiveStyle : navLinkStyle
                  }
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                    fill="none"
                    style={{ marginRight: "8px", flexShrink: 0 }}
                  >
                    <rect
                      x="2"
                      y="2"
                      width="12"
                      height="12"
                      rx="2"
                      stroke="currentColor"
                      strokeWidth="1.3"
                    />
                    <path
                      d="M5 6h6M5 8.5h4M5 11h2"
                      stroke="currentColor"
                      strokeWidth="1.3"
                      strokeLinecap="round"
                    />
                  </svg>
                  Dashboard
                </NavLink>
                <NavLink
                  to="/settings"
                  style={({ isActive }) =>
                    isActive ? navLinkActiveStyle : navLinkStyle
                  }
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                    fill="none"
                    style={{ marginRight: "8px", flexShrink: 0 }}
                  >
                    <circle
                      cx="8"
                      cy="8"
                      r="2"
                      stroke="currentColor"
                      strokeWidth="1.3"
                    />
                    <path
                      d="M8 1.5v2m0 9v2m-4.6-10.9l1.4 1.4m6.4 6.4l1.4 1.4M1.5 8h2m9 0h2M3.4 12.6l1.4-1.4m6.4-6.4l1.4-1.4"
                      stroke="currentColor"
                      strokeWidth="1.3"
                      strokeLinecap="round"
                    />
                  </svg>
                  Settings
                </NavLink>
              </div>

              {/* Status footer - Sprint 17: Enhanced with capability status */}
              <div
                style={{
                  marginTop: "auto",
                  padding: "12px",
                  backgroundColor: "var(--rl-bg-app)",
                  borderRadius: "var(--rl-radius-sm)",
                  fontSize: "var(--rl-fs-xs)",
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
                        displayConnectionState === "connected" &&
                        capabilitiesReady
                          ? "var(--rl-success)"
                          : displayConnectionState === "connected" &&
                              !capabilitiesReady
                            ? "var(--rl-warning)"
                            : displayConnectionState === "degraded"
                              ? "var(--rl-warning)"
                              : "var(--rl-error)",
                    }}
                  />
                  <span style={{ textTransform: "capitalize" }}>
                    {displayConnectionState === "connected" &&
                    !capabilitiesReady
                      ? "Validating..."
                      : displayConnectionState}
                  </span>
                </div>
                {/* Show version when connected and validated */}
                {displayConnectionState === "connected" &&
                  capabilitiesReady &&
                  capabilities && (
                    <div
                      style={{
                        color: "var(--rl-text-dim)",
                        marginBottom: "4px",
                      }}
                    >
                      Backend: v{capabilities.version}
                    </div>
                  )}
                <div style={{ color: "var(--rl-text-dim)" }}>
                  Port: {settings.enginePort}
                </div>
                {tokenSource && (
                  <div style={{ color: "var(--rl-text-dim)" }}>
                    Token: {tokenSource}
                  </div>
                )}
                {/* Show warning if capabilities check failed */}
                {displayConnectionState === "connected" &&
                  compatibilityValidation &&
                  !compatibilityValidation.valid && (
                    <div
                      style={{
                        color: "#fca5a5",
                        marginTop: "4px",
                        fontSize: "var(--rl-fs-xs)",
                      }}
                    >
                      Compatibility issue
                    </div>
                  )}
              </div>
            </nav>
          </>
        )}

        {/* Main content */}
        <main
          style={{
            flex: 1,
            overflow: "auto",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {/* Header bar with SSE connection badge */}
          <header
            style={{
              display: "flex",
              justifyContent: "flex-end",
              alignItems: "center",
              padding: "8px 16px",
              backgroundColor: "var(--rl-bg-panel)",
              borderBottom: "1px solid var(--rl-border)",
              flexShrink: 0,
            }}
          >
            <ConnectionBadge health={sseHealth} onReconnect={handleReconnect} />
          </header>

          {/* Content area */}
          <div style={{ flex: 1, overflow: "auto" }}>
            {/* Token required banner */}
            {tokenError && !token && (
              <div
                style={{
                  padding: "16px 20px",
                  backgroundColor: "#7f1d1d",
                  color: "#fecaca",
                  fontSize: "var(--rl-fs-base)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  borderBottom: "1px solid var(--rl-error)",
                }}
              >
                <div
                  style={{ display: "flex", alignItems: "center", gap: "12px" }}
                >
                  <span style={{ fontSize: "var(--rl-fs-lg)" }}>&#9888;</span>
                  <span>
                    <strong>Authentication required.</strong> Configure your
                    connection to start using Red Letters.
                  </span>
                </div>
                <button
                  onClick={handleOpenSettings}
                  style={{
                    padding: "8px 16px",
                    backgroundColor: "transparent",
                    color: "var(--rl-accent)",
                    border: "1px solid var(--rl-accent)",
                    borderRadius: "var(--rl-radius-sm)",
                    cursor: "pointer",
                    fontWeight: 500,
                    fontSize: "var(--rl-fs-base)",
                  }}
                >
                  Configure Connection
                </button>
              </div>
            )}

            {/* Capability warnings banner - shown when connected but with warnings */}
            {displayConnectionState === "connected" &&
              compatibilityValidation?.valid &&
              compatibilityValidation.warnings &&
              compatibilityValidation.warnings.length > 0 && (
                <div
                  style={{
                    padding: "12px 20px",
                    backgroundColor: "#78350f",
                    color: "#fcd34d",
                    fontSize: "var(--rl-fs-base)",
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                    borderBottom: "1px solid var(--rl-warning)",
                  }}
                >
                  <span style={{ fontSize: "var(--rl-fs-md)" }}>&#9888;</span>
                  <span>{compatibilityValidation.warnings[0]}</span>
                </div>
              )}

            {/* Connection Panel - shown when disconnected */}
            {displayConnectionState === "disconnected" && (
              <ConnectionPanel
                port={settings.enginePort}
                onReconnect={handleReconnect}
                onPortChange={(port) =>
                  useAppStore.getState().updateSettings({ enginePort: port })
                }
                onOpenSettings={handleOpenSettings}
              />
            )}

            <Routes>
              <Route path="/" element={<Dashboard />} />
              {/* Task-shaped routes (v0.15.0 - Passage Workspace) */}
              <Route
                path="/explore"
                element={<PassageWorkspace client={client} />}
              />
              <Route path="/export" element={<ExportView client={client} />} />
              {/* Legacy route redirect */}
              <Route
                path="/translate"
                element={<Navigate to="/explore" replace />}
              />
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
                    onOpenConnectionSettings={handleOpenSettings}
                  />
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </main>
      </div>

      {/* Bootstrap Wizard - shown on first run */}
      {showBootstrap && client && (
        <BootstrapWizard
          client={client}
          capabilities={capabilities}
          onComplete={handleBootstrapComplete}
          onSkip={handleBootstrapSkip}
        />
      )}

      {/* Sprint 17: Compatibility Modal - shown when GUI/backend mismatch */}
      {showCompatibilityModal &&
        compatibilityValidation &&
        !compatibilityValidation.valid && (
          <CompatibilityModal
            validation={compatibilityValidation}
            backendVersion={capabilities?.version}
            onRetry={handleRetryCapabilityCheck}
            onDismiss={() => setShowCompatibilityModal(false)}
          />
        )}

      {/* Sprint 21: Connection Settings Modal */}
      {showSettingsModal && (
        <ConnectionSettingsModal
          port={settings.enginePort}
          currentToken={token}
          canClose={!!token}
          errorMessage={tokenError}
          onSave={handleSaveConnectionSettings}
          onClose={() => setShowSettingsModal(false)}
        />
      )}
    </BrowserRouter>
  );
}
