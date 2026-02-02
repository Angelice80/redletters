/**
 * Sources management screen for Red Letters GUI.
 *
 * Sprint 6: Source installation interface with:
 * - List of configured sources with status
 * - Install/Uninstall actions
 * - EULA acceptance modal for restricted licenses
 */

import { useState, useEffect, useCallback } from "react";
import type { ApiClient } from "../api/client";
import type { SourceStatus, LicenseInfoResponse } from "../api/types";

interface SourcesProps {
  client: ApiClient | null;
}

// Styles
const containerStyle: React.CSSProperties = {
  padding: "24px",
  maxWidth: "900px",
};

const headerStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 600,
  marginBottom: "24px",
  color: "#eaeaea",
};

const subHeaderStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#9ca3af",
  marginBottom: "16px",
};

const sourceListStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "12px",
};

const sourceCardStyle: React.CSSProperties = {
  backgroundColor: "#2d2d44",
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
  fontSize: "16px",
  fontWeight: 500,
  color: "#eaeaea",
};

const sourceMetaStyle: React.CSSProperties = {
  display: "flex",
  gap: "12px",
  fontSize: "12px",
  color: "#9ca3af",
};

const badgeStyle: React.CSSProperties = {
  display: "inline-block",
  padding: "2px 8px",
  borderRadius: "4px",
  fontSize: "11px",
  fontWeight: 500,
};

const spineBadgeStyle: React.CSSProperties = {
  ...badgeStyle,
  backgroundColor: "#ef4444",
  color: "white",
};

const installedBadgeStyle: React.CSSProperties = {
  ...badgeStyle,
  backgroundColor: "#22c55e",
  color: "#1a1a2e",
};

const notInstalledBadgeStyle: React.CSSProperties = {
  ...badgeStyle,
  backgroundColor: "#4b5563",
  color: "#eaeaea",
};

const eulaBadgeStyle: React.CSSProperties = {
  ...badgeStyle,
  backgroundColor: "#f59e0b",
  color: "#1a1a2e",
};

const buttonStyle: React.CSSProperties = {
  padding: "8px 16px",
  fontSize: "13px",
  fontWeight: 500,
  border: "none",
  borderRadius: "4px",
  cursor: "pointer",
  transition: "background-color 0.15s",
};

const installButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "#3b82f6",
  color: "white",
};

const uninstallButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "#7f1d1d",
  color: "#fca5a5",
};

const disabledButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "#4b5563",
  color: "#9ca3af",
  cursor: "not-allowed",
};

const statusBarStyle: React.CSSProperties = {
  display: "flex",
  gap: "16px",
  marginBottom: "24px",
  padding: "12px 16px",
  backgroundColor: "#1a1a2e",
  borderRadius: "8px",
  fontSize: "13px",
  color: "#9ca3af",
};

const spineAlertStyle: React.CSSProperties = {
  padding: "16px",
  backgroundColor: "#7f1d1d",
  borderRadius: "8px",
  marginBottom: "24px",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

const alertTextStyle: React.CSSProperties = {
  color: "#fca5a5",
  fontSize: "14px",
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
  backgroundColor: "#2d2d44",
  borderRadius: "12px",
  padding: "24px",
  maxWidth: "500px",
  width: "90%",
  maxHeight: "80vh",
  overflow: "auto",
};

const modalHeaderStyle: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 600,
  color: "#eaeaea",
  marginBottom: "16px",
};

const modalTextStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#9ca3af",
  lineHeight: 1.6,
  marginBottom: "16px",
};

const checkboxContainerStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "10px",
  marginBottom: "20px",
  padding: "12px",
  backgroundColor: "#1a1a2e",
  borderRadius: "6px",
};

const modalButtonRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "flex-end",
  gap: "12px",
};

const cancelButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "#4b5563",
  color: "#eaeaea",
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
          <div style={{ ...modalTextStyle, fontSize: "12px" }}>
            <strong>Notes:</strong> {licenseInfo.notes}
          </div>
        )}

        {licenseInfo.license_url && (
          <div style={{ ...modalTextStyle, fontSize: "12px" }}>
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
            style={{ color: "#eaeaea", fontSize: "14px", cursor: "pointer" }}
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
      style={{ ...badgeStyle, backgroundColor: "#374151", color: "#9ca3af" }}
    >
      {role.replace(/_/g, " ")}
    </span>
  );
}

export function Sources({ client }: SourcesProps) {
  const [sources, setSources] = useState<SourceStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [spineInstalled, setSpineInstalled] = useState(false);
  const [spineSourceId, setSpineSourceId] = useState<string | null>(null);
  const [dataRoot, setDataRoot] = useState<string>("");

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

    try {
      const response = await client.getSourcesStatus();

      // Convert sources dict to array
      const sourcesList = Object.values(response.sources);
      setSources(sourcesList);
      setSpineInstalled(response.spine_installed);
      setSpineSourceId(response.spine_source_id);
      setDataRoot(response.data_root);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sources");
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
        <div style={{ color: "#9ca3af" }}>Not connected to backend.</div>
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
            <span style={{ color: "#22c55e" }}>Installed</span>
          ) : (
            <span style={{ color: "#ef4444" }}>Not installed</span>
          )}
        </span>
      </div>

      {/* Spine missing alert */}
      {!loading && !spineInstalled && spineSourceId && (
        <div style={spineAlertStyle}>
          <span style={alertTextStyle}>
            The canonical spine source is not installed. Translation will not
            work until it is installed.
          </span>
          <button
            style={installButtonStyle}
            onClick={() => handleInstall(spineSourceId)}
            disabled={operatingOn === spineSourceId}
          >
            {operatingOn === spineSourceId ? "Installing..." : "Install Spine"}
          </button>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div
          style={{
            padding: "12px",
            backgroundColor: "#7f1d1d",
            color: "#fca5a5",
            borderRadius: "4px",
            marginBottom: "16px",
          }}
        >
          {error}
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div style={{ textAlign: "center", padding: "48px", color: "#9ca3af" }}>
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
                      fontSize: "12px",
                      color: operationStatus[source.source_id].startsWith(
                        "Error",
                      )
                        ? "#fca5a5"
                        : "#22c55e",
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

      {/* Empty state */}
      {!loading && sources.length === 0 && (
        <div
          style={{
            textAlign: "center",
            padding: "48px",
            color: "#6b7280",
          }}
        >
          No sources configured in the catalog.
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
