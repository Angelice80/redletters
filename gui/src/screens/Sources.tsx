/**
 * Sources management screen for Red Letters GUI.
 *
 * Sprint 6: Source installation interface with:
 * - List of configured sources with status
 * - Install/Uninstall actions
 * - EULA acceptance modal for restricted licenses
 */

import { useState, useEffect, useCallback } from "react";
import { BOOTSTRAP_COMPLETED_KEY } from "../constants/storageKeys";
import type { ApiClient } from "../api/client";
import { detectBackendMismatch } from "../api/client";
import type {
  SourceStatus,
  LicenseInfoResponse,
  ApiErrorDetail,
  BackendMismatchInfo,
} from "../api/types";
import {
  ApiErrorPanel,
  createApiErrorDetail,
} from "../components/ApiErrorPanel";
import { BackendMismatchPanel } from "../components/BackendMismatchPanel";

interface SourcesProps {
  client: ApiClient | null;
}

// Styles
const containerStyle: React.CSSProperties = {
  padding: "24px",
  maxWidth: "900px",
};

const headerStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xl)",
  fontWeight: 600,
  marginBottom: "24px",
  color: "var(--rl-text)",
};

const subHeaderStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-base)",
  color: "var(--rl-text-muted)",
  marginBottom: "16px",
};

const sourceListStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "12px",
};

const sourceCardStyle: React.CSSProperties = {
  backgroundColor: "var(--rl-bg-card)",
  borderRadius: "8px",
  padding: "16px",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

const sourceInfoStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "6px",
};

const sourceNameStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-md)",
  fontWeight: 500,
  color: "var(--rl-text)",
};

const sourceMetaStyle: React.CSSProperties = {
  display: "flex",
  gap: "12px",
  fontSize: "var(--rl-fs-sm)",
  color: "var(--rl-text-muted)",
};

const badgeStyle: React.CSSProperties = {
  display: "inline-block",
  padding: "2px 8px",
  borderRadius: "4px",
  fontSize: "var(--rl-fs-xs)",
  fontWeight: 500,
};

const spineBadgeStyle: React.CSSProperties = {
  ...badgeStyle,
  backgroundColor: "var(--rl-error)",
  color: "white",
};

const installedBadgeStyle: React.CSSProperties = {
  ...badgeStyle,
  backgroundColor: "var(--rl-success)",
  color: "var(--rl-bg-app)",
};

const notInstalledBadgeStyle: React.CSSProperties = {
  ...badgeStyle,
  backgroundColor: "var(--rl-border-strong)",
  color: "var(--rl-text)",
};

const eulaBadgeStyle: React.CSSProperties = {
  ...badgeStyle,
  backgroundColor: "var(--rl-warning)",
  color: "var(--rl-bg-app)",
};

const buttonStyle: React.CSSProperties = {
  padding: "8px 16px",
  fontSize: "var(--rl-fs-base)",
  fontWeight: 500,
  border: "none",
  borderRadius: "4px",
  cursor: "pointer",
  transition: "background-color 0.15s",
};

const installButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "var(--rl-primary)",
  color: "white",
};

const uninstallButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "#7f1d1d",
  color: "#fca5a5",
};

const disabledButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "var(--rl-border-strong)",
  color: "var(--rl-text-muted)",
  cursor: "not-allowed",
};

const statusBarStyle: React.CSSProperties = {
  display: "flex",
  gap: "16px",
  marginBottom: "24px",
  padding: "12px 16px",
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "8px",
  fontSize: "var(--rl-fs-base)",
  color: "var(--rl-text-muted)",
};

// Sprint 17: Bootstrap CTA styles
const bootstrapCtaStyle: React.CSSProperties = {
  padding: "24px",
  backgroundColor: "#1e3a5f",
  borderRadius: "8px",
  marginBottom: "24px",
  border: "1px solid var(--rl-primary)",
  textAlign: "center",
};

const bootstrapTitleStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-lg)",
  fontWeight: 600,
  color: "#60a5fa",
  marginBottom: "8px",
};

const bootstrapTextStyle: React.CSSProperties = {
  color: "var(--rl-text-muted)",
  fontSize: "var(--rl-fs-base)",
  marginBottom: "16px",
};

const emptyStateContainerStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "48px",
  backgroundColor: "var(--rl-bg-card)",
  borderRadius: "8px",
};

// Modal styles
const modalOverlayStyle: React.CSSProperties = {
  position: "fixed",
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: "rgba(0, 0, 0, 0.7)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
};

const modalContentStyle: React.CSSProperties = {
  backgroundColor: "var(--rl-bg-card)",
  borderRadius: "12px",
  padding: "24px",
  maxWidth: "500px",
  width: "90%",
  maxHeight: "80vh",
  overflow: "auto",
};

const modalHeaderStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-lg)",
  fontWeight: 600,
  color: "var(--rl-text)",
  marginBottom: "16px",
};

const modalTextStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-base)",
  color: "var(--rl-text-muted)",
  lineHeight: 1.6,
  marginBottom: "16px",
};

const checkboxContainerStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "10px",
  marginBottom: "20px",
  padding: "12px",
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "6px",
};

const modalButtonRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "flex-end",
  gap: "12px",
};

const cancelButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "var(--rl-border-strong)",
  color: "var(--rl-text)",
};

interface EulaModalProps {
  licenseInfo: LicenseInfoResponse;
  onConfirm: () => void;
  onCancel: () => void;
  loading: boolean;
}

function EulaModal({
  licenseInfo,
  onConfirm,
  onCancel,
  loading,
}: EulaModalProps) {
  const [accepted, setAccepted] = useState(false);

  return (
    <div style={modalOverlayStyle} onClick={onCancel}>
      <div style={modalContentStyle} onClick={(e) => e.stopPropagation()}>
        <div style={modalHeaderStyle}>License Agreement</div>

        <div style={modalTextStyle}>
          <strong>{licenseInfo.name}</strong>
        </div>

        <div style={modalTextStyle}>
          <strong>License:</strong> {licenseInfo.license}
        </div>

        {licenseInfo.eula_summary && (
          <div style={modalTextStyle}>{licenseInfo.eula_summary}</div>
        )}

        {licenseInfo.notes && (
          <div style={{ ...modalTextStyle, fontSize: "var(--rl-fs-sm)" }}>
            <strong>Notes:</strong> {licenseInfo.notes}
          </div>
        )}

        {licenseInfo.license_url && (
          <div style={{ ...modalTextStyle, fontSize: "var(--rl-fs-sm)" }}>
            <a
              href={licenseInfo.license_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "#60a5fa" }}
            >
              View full license text
            </a>
          </div>
        )}

        <div style={checkboxContainerStyle}>
          <input
            type="checkbox"
            id="accept-eula"
            checked={accepted}
            onChange={(e) => setAccepted(e.target.checked)}
            style={{ width: "18px", height: "18px", cursor: "pointer" }}
          />
          <label
            htmlFor="accept-eula"
            style={{
              color: "var(--rl-text)",
              fontSize: "var(--rl-fs-base)",
              cursor: "pointer",
            }}
          >
            I accept the license terms
          </label>
        </div>

        <div style={modalButtonRowStyle}>
          <button
            style={cancelButtonStyle}
            onClick={onCancel}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            style={
              accepted && !loading ? installButtonStyle : disabledButtonStyle
            }
            onClick={onConfirm}
            disabled={!accepted || loading}
          >
            {loading ? "Installing..." : "Install"}
          </button>
        </div>
      </div>
    </div>
  );
}

function getRoleBadge(role: string): React.ReactNode {
  if (role === "canonical_spine") {
    return <span style={spineBadgeStyle}>SPINE</span>;
  }
  return (
    <span
      style={{
        ...badgeStyle,
        backgroundColor: "var(--rl-border-strong)",
        color: "var(--rl-text-muted)",
      }}
    >
      {role.replace(/_/g, " ")}
    </span>
  );
}

export function Sources({ client }: SourcesProps) {
  const [sources, setSources] = useState<SourceStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiErrorDetail | null>(null);
  const [spineInstalled, setSpineInstalled] = useState(false);
  const [spineSourceId, setSpineSourceId] = useState<string | null>(null);
  const [dataRoot, setDataRoot] = useState<string>("");

  // Sprint 19: Backend mismatch detection
  const [mismatch, setMismatch] = useState<BackendMismatchInfo | null>(null);

  // Per-source loading states
  const [operatingOn, setOperatingOn] = useState<string | null>(null);
  const [operationStatus, setOperationStatus] = useState<{
    [key: string]: string;
  }>({});

  // EULA modal state
  const [eulaModal, setEulaModal] = useState<{
    sourceId: string;
    licenseInfo: LicenseInfoResponse;
  } | null>(null);

  const loadSources = useCallback(async () => {
    if (!client) return;

    setLoading(true);
    setError(null);
    setMismatch(null);

    try {
      const response = await client.getSourcesStatus();

      // Convert sources dict to array
      const sourcesList = Object.values(response.sources);
      setSources(sourcesList);
      setSpineInstalled(response.spine_installed);
      setSpineSourceId(response.spine_source_id);
      setDataRoot(response.data_root);
    } catch (err) {
      const errorDetail = createApiErrorDetail("GET", "/sources/status", err);

      // Sprint 19: Check for backend mismatch on 404
      if (errorDetail.status === 404) {
        const mismatchInfo = await detectBackendMismatch(
          client.baseUrl,
          client.token,
          "/sources/status",
        );
        if (mismatchInfo.detected) {
          setMismatch(mismatchInfo);
          return;
        }
      }

      setError(errorDetail);
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    loadSources();
  }, [loadSources]);

  const handleInstall = useCallback(
    async (sourceId: string, acceptEula: boolean = false) => {
      if (!client) return;

      setOperatingOn(sourceId);
      setOperationStatus((prev) => ({ ...prev, [sourceId]: "Installing..." }));

      try {
        const result = await client.installSource({
          source_id: sourceId,
          accept_eula: acceptEula,
        });

        if (result.eula_required && !result.success) {
          // Need EULA acceptance - show modal
          const licenseInfo = await client.getLicenseInfo(sourceId);
          setEulaModal({ sourceId, licenseInfo });
          setOperationStatus((prev) => ({ ...prev, [sourceId]: "" }));
        } else if (result.success) {
          setOperationStatus((prev) => ({ ...prev, [sourceId]: "Installed!" }));
          // Refresh sources list
          await loadSources();
          setTimeout(() => {
            setOperationStatus((prev) => ({ ...prev, [sourceId]: "" }));
          }, 2000);
        } else {
          setOperationStatus((prev) => ({
            ...prev,
            [sourceId]: `Error: ${result.error || result.message}`,
          }));
        }
      } catch (err) {
        setOperationStatus((prev) => ({
          ...prev,
          [sourceId]: `Error: ${err instanceof Error ? err.message : "Failed"}`,
        }));
      } finally {
        setOperatingOn(null);
      }
    },
    [client, loadSources],
  );

  const handleUninstall = useCallback(
    async (sourceId: string) => {
      if (!client) return;

      setOperatingOn(sourceId);
      setOperationStatus((prev) => ({
        ...prev,
        [sourceId]: "Uninstalling...",
      }));

      try {
        const result = await client.uninstallSource({ source_id: sourceId });

        if (result.success) {
          setOperationStatus((prev) => ({
            ...prev,
            [sourceId]: "Uninstalled!",
          }));
          // Refresh sources list
          await loadSources();
          setTimeout(() => {
            setOperationStatus((prev) => ({ ...prev, [sourceId]: "" }));
          }, 2000);
        } else {
          setOperationStatus((prev) => ({
            ...prev,
            [sourceId]: `Error: ${result.error || result.message}`,
          }));
        }
      } catch (err) {
        setOperationStatus((prev) => ({
          ...prev,
          [sourceId]: `Error: ${err instanceof Error ? err.message : "Failed"}`,
        }));
      } finally {
        setOperatingOn(null);
      }
    },
    [client, loadSources],
  );

  const handleEulaConfirm = useCallback(async () => {
    if (!eulaModal) return;

    setOperatingOn(eulaModal.sourceId);
    await handleInstall(eulaModal.sourceId, true);
    setEulaModal(null);
  }, [eulaModal, handleInstall]);

  const handleEulaCancel = useCallback(() => {
    setEulaModal(null);
  }, []);

  if (!client) {
    return (
      <div style={containerStyle}>
        <h1 style={headerStyle}>Sources</h1>
        <div style={{ color: "var(--rl-text-muted)" }}>
          Not connected to backend.
        </div>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <h1 style={headerStyle}>Sources</h1>
      <div style={subHeaderStyle}>
        Manage text sources for the Red Letters translation system.
      </div>

      {/* Status bar */}
      <div style={statusBarStyle}>
        <span>Data root: {dataRoot || "..."}</span>
        <span>Total sources: {sources.length}</span>
        <span>
          Spine:{" "}
          {spineInstalled ? (
            <span style={{ color: "var(--rl-success)" }}>Installed</span>
          ) : (
            <span style={{ color: "var(--rl-error)" }}>Not installed</span>
          )}
        </span>
      </div>

      {/* Sprint 17: Enhanced spine missing alert with bootstrap CTA */}
      {!loading && !spineInstalled && spineSourceId && (
        <div style={bootstrapCtaStyle}>
          <div style={bootstrapTitleStyle}>Spine Source Required</div>
          <div style={bootstrapTextStyle}>
            The canonical Greek text source (MorphGNT/SBLGNT) is required for
            translation. Install it now to start exploring.
          </div>
          <div
            style={{ display: "flex", justifyContent: "center", gap: "12px" }}
          >
            <button
              style={installButtonStyle}
              onClick={() => handleInstall(spineSourceId)}
              disabled={operatingOn === spineSourceId}
            >
              {operatingOn === spineSourceId
                ? "Installing..."
                : "Install Spine"}
            </button>
            <button
              style={cancelButtonStyle}
              onClick={() => {
                // Trigger bootstrap wizard by clearing the flag
                localStorage.removeItem(BOOTSTRAP_COMPLETED_KEY);
                window.location.reload();
              }}
            >
              Run Setup Wizard
            </button>
          </div>
        </div>
      )}

      {/* Sprint 19: Backend mismatch display */}
      {mismatch && (
        <BackendMismatchPanel
          mismatchInfo={mismatch}
          onRetry={loadSources}
          onDismiss={() => setMismatch(null)}
        />
      )}

      {/* Error display */}
      {error && !mismatch && (
        <ApiErrorPanel
          error={error}
          onRetry={loadSources}
          onDismiss={() => setError(null)}
        />
      )}

      {/* Loading state */}
      {loading && (
        <div
          style={{
            textAlign: "center",
            padding: "48px",
            color: "var(--rl-text-muted)",
          }}
        >
          Loading sources...
        </div>
      )}

      {/* Sources list */}
      {!loading && (
        <div style={sourceListStyle}>
          {sources.map((source) => (
            <div key={source.source_id} style={sourceCardStyle}>
              <div style={sourceInfoStyle}>
                <div
                  style={{ display: "flex", alignItems: "center", gap: "10px" }}
                >
                  <span style={sourceNameStyle}>{source.name}</span>
                  {getRoleBadge(source.role)}
                  {source.installed ? (
                    <span style={installedBadgeStyle}>Installed</span>
                  ) : (
                    <span style={notInstalledBadgeStyle}>Not installed</span>
                  )}
                  {source.requires_eula && (
                    <span style={eulaBadgeStyle}>EULA</span>
                  )}
                </div>
                <div style={sourceMetaStyle}>
                  <span>ID: {source.source_id}</span>
                  <span>License: {source.license}</span>
                  {source.installed && source.version && (
                    <span>Version: {source.version}</span>
                  )}
                </div>
                {operationStatus[source.source_id] && (
                  <div
                    style={{
                      fontSize: "var(--rl-fs-sm)",
                      color: operationStatus[source.source_id].startsWith(
                        "Error",
                      )
                        ? "#fca5a5"
                        : "var(--rl-success)",
                      marginTop: "4px",
                    }}
                  >
                    {operationStatus[source.source_id]}
                  </div>
                )}
              </div>

              <div>
                {source.installed ? (
                  <button
                    style={
                      operatingOn === source.source_id
                        ? disabledButtonStyle
                        : uninstallButtonStyle
                    }
                    onClick={() => handleUninstall(source.source_id)}
                    disabled={operatingOn === source.source_id}
                  >
                    {operatingOn === source.source_id ? "..." : "Uninstall"}
                  </button>
                ) : (
                  <button
                    style={
                      operatingOn === source.source_id
                        ? disabledButtonStyle
                        : installButtonStyle
                    }
                    onClick={() => handleInstall(source.source_id)}
                    disabled={operatingOn === source.source_id}
                  >
                    {operatingOn === source.source_id ? "..." : "Install"}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Sprint 17: Enhanced empty state with bootstrap CTA */}
      {!loading && sources.length === 0 && (
        <div style={emptyStateContainerStyle}>
          <div
            style={{
              fontSize: "var(--rl-fs-lg)",
              color: "var(--rl-text)",
              marginBottom: "8px",
            }}
          >
            No Sources Configured
          </div>
          <div style={{ color: "var(--rl-text-muted)", marginBottom: "16px" }}>
            The sources catalog is empty. Run the setup wizard to configure your
            data sources.
          </div>
          <button
            style={installButtonStyle}
            onClick={() => {
              // Trigger bootstrap wizard by clearing the flag
              localStorage.removeItem(BOOTSTRAP_COMPLETED_KEY);
              window.location.reload();
            }}
          >
            Run Setup Wizard
          </button>
        </div>
      )}

      {/* EULA Modal */}
      {eulaModal && (
        <EulaModal
          licenseInfo={eulaModal.licenseInfo}
          onConfirm={handleEulaConfirm}
          onCancel={handleEulaCancel}
          loading={operatingOn === eulaModal.sourceId}
        />
      )}
    </div>
  );
}
