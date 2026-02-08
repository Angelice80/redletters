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
          backgroundColor: "#1a1a2e",
          color: "#eaeaea",
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
              backgroundColor: "#2d2d44",
              border: "1px solid #4b5563",
              borderRadius: "6px",
              color: "#eaeaea",
              fontSize: "20px",
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
                backgroundColor: "#2d2d44",
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

              <div
                style={{ display: "flex", flexDirection: "column", gap: "4px" }}
                onClick={() => isMobileSidebar && setSidebarOpen(false)}
              >
                <NavLink
                  to="/"
                  style={({ isActive }) =>
                    isActive ? navLinkActiveStyle : navLinkStyle
                  }
                >
                  Dashboard
                </NavLink>
                <NavLink
                  to="/explore"
                  style={({ isActive }) =>
                    isActive ? navLinkActiveStyle : navLinkStyle
                  }
                >
                  Explore
                </NavLink>
                <NavLink
                  to="/export"
                  style={({ isActive }) =>
                    isActive ? navLinkActiveStyle : navLinkStyle
                  }
                >
                  Export
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
                  to="/settings"
                  style={({ isActive }) =>
                    isActive ? navLinkActiveStyle : navLinkStyle
                  }
                >
                  Settings
                </NavLink>
              </div>

              {/* Status footer - Sprint 17: Enhanced with capability status */}
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
                        displayConnectionState === "connected" &&
                        capabilitiesReady
                          ? "#22c55e"
                          : displayConnectionState === "connected" &&
                              !capabilitiesReady
                            ? "#f59e0b"
                            : displayConnectionState === "degraded"
                              ? "#f59e0b"
                              : "#ef4444",
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
                    <div style={{ color: "#6b7280", marginBottom: "4px" }}>
                      Backend: v{capabilities.version}
                    </div>
                  )}
                <div style={{ color: "#6b7280" }}>
                  Port: {settings.enginePort}
                </div>
                {tokenSource && (
                  <div style={{ color: "#6b7280" }}>Token: {tokenSource}</div>
                )}
                {/* Show warning if capabilities check failed */}
                {displayConnectionState === "connected" &&
                  compatibilityValidation &&
                  !compatibilityValidation.valid && (
                    <div
                      style={{
                        color: "#fca5a5",
                        marginTop: "4px",
                        fontSize: "10px",
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
              backgroundColor: "#2d2d44",
              borderBottom: "1px solid #374151",
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
                  fontSize: "14px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  borderBottom: "1px solid #ef4444",
                }}
              >
                <div
                  style={{ display: "flex", alignItems: "center", gap: "12px" }}
                >
                  <span style={{ fontSize: "20px" }}>&#9888;</span>
                  <span>
                    <strong>Authentication required.</strong> Configure your
                    connection to start using Red Letters.
                  </span>
                </div>
                <button
                  onClick={handleOpenSettings}
                  style={{
                    padding: "8px 16px",
                    backgroundColor: "#3b82f6",
                    color: "white",
                    border: "none",
                    borderRadius: "4px",
                    cursor: "pointer",
                    fontWeight: 500,
                    fontSize: "13px",
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
                    fontSize: "13px",
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                    borderBottom: "1px solid #f59e0b",
                  }}
                >
                  <span style={{ fontSize: "16px" }}>&#9888;</span>
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
