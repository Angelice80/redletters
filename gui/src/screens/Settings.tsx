/**
 * Settings screen - Engine configuration.
 */

import { useState } from "react";
import { useAppStore, selectSettings } from "../store";
import type { EngineMode } from "../api/types";
import { invoke } from "@tauri-apps/api/core";

interface SettingsProps {
  engineMode?: EngineMode;
  onReconnect: () => void;
  onTestReconnection: () => Promise<{ gaps: number; dupes: number }>;
}

export function Settings({
  engineMode,
  onReconnect,
  onTestReconnection,
}: SettingsProps) {
  const settings = useAppStore(selectSettings);
  const updateSettings = useAppStore((state) => state.updateSettings);

  const [port, setPort] = useState(settings.enginePort.toString());
  const [threshold, setThreshold] = useState(
    settings.integritySizeThreshold.toString(),
  );
  const [testResult, setTestResult] = useState<{
    gaps: number;
    dupes: number;
  } | null>(null);
  const [testing, setTesting] = useState(false);
  const [resetConfirm, setResetConfirm] = useState(false);
  const [safeStarting, setSafeStarting] = useState(false);

  const handlePortChange = (value: string) => {
    setPort(value);
    const num = parseInt(value, 10);
    if (!isNaN(num) && num > 0 && num < 65536) {
      updateSettings({ enginePort: num });
    }
  };

  const handleThresholdChange = (value: string) => {
    setThreshold(value);
    const num = parseInt(value, 10);
    if (!isNaN(num) && num > 0) {
      updateSettings({ integritySizeThreshold: num });
    }
  };

  const handleTestReconnection = async () => {
    setTesting(true);
    setTestResult(null);

    try {
      const result = await onTestReconnection();
      setTestResult(result);
    } catch (err) {
      console.error("Reconnection test failed:", err);
    } finally {
      setTesting(false);
    }
  };

  const handleStartSafeMode = async () => {
    setSafeStarting(true);
    try {
      await invoke("start_engine_safe_mode", { port: settings.enginePort });
      // Wait a bit for engine to start
      setTimeout(() => {
        onReconnect();
        setSafeStarting(false);
      }, 2000);
    } catch (err) {
      console.error("Failed to start safe mode:", err);
      setSafeStarting(false);
    }
  };

  return (
    <div style={{ padding: "24px" }}>
      <h1 style={{ fontSize: "24px", fontWeight: 600, marginBottom: "24px" }}>
        Settings
      </h1>

      {/* Engine Connection */}
      <section
        style={{
          padding: "16px",
          backgroundColor: "#2d2d44",
          borderRadius: "8px",
          marginBottom: "16px",
        }}
      >
        <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "16px" }}>
          Engine Connection
        </h2>

        <div style={{ marginBottom: "16px" }}>
          <label
            style={{
              display: "block",
              marginBottom: "4px",
              fontSize: "13px",
              color: "#9ca3af",
            }}
          >
            Engine Port
          </label>
          <input
            type="number"
            value={port}
            onChange={(e) => handlePortChange(e.target.value)}
            style={{
              width: "120px",
              padding: "8px 12px",
              borderRadius: "4px",
              border: "1px solid #4a4a6a",
              backgroundColor: "#1a1a2e",
              color: "#eaeaea",
              fontSize: "14px",
            }}
          />
          <span
            style={{ marginLeft: "8px", fontSize: "12px", color: "#6b7280" }}
          >
            Default: 47200
          </span>
        </div>

        <button
          onClick={onReconnect}
          style={{
            padding: "8px 16px",
            borderRadius: "4px",
            border: "none",
            backgroundColor: "#3b82f6",
            color: "white",
            cursor: "pointer",
            fontSize: "14px",
          }}
        >
          Reconnect
        </button>
      </section>

      {/* Engine Mode */}
      <section
        style={{
          padding: "16px",
          backgroundColor: "#2d2d44",
          borderRadius: "8px",
          marginBottom: "16px",
        }}
      >
        <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "16px" }}>
          Engine Mode
        </h2>

        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "14px", marginBottom: "4px" }}>
            Current Mode:{" "}
            <span
              style={{
                fontWeight: 600,
                color: engineMode === "safe" ? "#f59e0b" : "#22c55e",
              }}
            >
              {engineMode === "safe" ? "Safe Mode" : "Normal"}
            </span>
          </div>
          <p style={{ fontSize: "12px", color: "#6b7280", marginTop: "4px" }}>
            Safe mode disables job creation. Useful for diagnostics and
            recovery.
          </p>
        </div>

        <button
          onClick={handleStartSafeMode}
          disabled={safeStarting}
          style={{
            padding: "8px 16px",
            borderRadius: "4px",
            border: "1px solid #f59e0b",
            backgroundColor: "transparent",
            color: "#f59e0b",
            cursor: safeStarting ? "wait" : "pointer",
            fontSize: "14px",
            opacity: safeStarting ? 0.6 : 1,
          }}
        >
          {safeStarting ? "Starting..." : "Restart Engine in Safe Mode"}
        </button>
        <p style={{ fontSize: "11px", color: "#6b7280", marginTop: "8px" }}>
          Or restart manually: <code>redletters engine start --safe-mode</code>
        </p>
      </section>

      {/* Integrity Settings */}
      <section
        style={{
          padding: "16px",
          backgroundColor: "#2d2d44",
          borderRadius: "8px",
          marginBottom: "16px",
        }}
      >
        <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "16px" }}>
          Integrity Settings
        </h2>

        <div style={{ marginBottom: "16px" }}>
          <label
            style={{
              display: "block",
              marginBottom: "4px",
              fontSize: "13px",
              color: "#9ca3af",
            }}
          >
            Size Threshold (MB)
          </label>
          <input
            type="number"
            value={threshold}
            onChange={(e) => handleThresholdChange(e.target.value)}
            style={{
              width: "120px",
              padding: "8px 12px",
              borderRadius: "4px",
              border: "1px solid #4a4a6a",
              backgroundColor: "#1a1a2e",
              color: "#eaeaea",
              fontSize: "14px",
            }}
          />
          <span
            style={{ marginLeft: "8px", fontSize: "12px", color: "#6b7280" }}
          >
            Files larger than this are skipped during integrity checks
          </span>
        </div>
      </section>

      {/* Reconnection Test */}
      <section
        style={{
          padding: "16px",
          backgroundColor: "#2d2d44",
          borderRadius: "8px",
          marginBottom: "16px",
        }}
      >
        <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "16px" }}>
          Connection Testing
        </h2>

        <p style={{ fontSize: "13px", color: "#9ca3af", marginBottom: "16px" }}>
          Test SSE reconnection with Last-Event-ID to verify no gaps or
          duplicates.
        </p>

        <button
          onClick={handleTestReconnection}
          disabled={testing}
          style={{
            padding: "8px 16px",
            borderRadius: "4px",
            border: "none",
            backgroundColor: "#6b7280",
            color: "white",
            cursor: testing ? "wait" : "pointer",
            fontSize: "14px",
            opacity: testing ? 0.6 : 1,
          }}
        >
          {testing ? "Testing..." : "Test Reconnection"}
        </button>

        {testResult && (
          <div
            style={{
              marginTop: "16px",
              padding: "12px",
              backgroundColor: "#1a1a2e",
              borderRadius: "4px",
            }}
          >
            <div
              style={{ fontSize: "14px", fontWeight: 600, marginBottom: "8px" }}
            >
              {testResult.gaps === 0 && testResult.dupes === 0
                ? "No gaps or duplicates detected"
                : `Gaps: ${testResult.gaps}, Duplicates: ${testResult.dupes}`}
            </div>
            <div
              style={{
                fontSize: "12px",
                color:
                  testResult.gaps === 0 && testResult.dupes === 0
                    ? "#22c55e"
                    : "#ef4444",
              }}
            >
              {testResult.gaps === 0 && testResult.dupes === 0
                ? "Event delivery is working correctly."
                : "Event delivery may have issues."}
            </div>
          </div>
        )}
      </section>

      {/* Danger Zone */}
      <section
        style={{
          padding: "16px",
          backgroundColor: "#2d2d44",
          borderRadius: "8px",
          border: "1px solid #ef4444",
        }}
      >
        <h2
          style={{
            fontSize: "16px",
            fontWeight: 600,
            marginBottom: "16px",
            color: "#ef4444",
          }}
        >
          Danger Zone
        </h2>

        {!resetConfirm ? (
          <button
            onClick={() => setResetConfirm(true)}
            style={{
              padding: "8px 16px",
              borderRadius: "4px",
              border: "1px solid #ef4444",
              backgroundColor: "transparent",
              color: "#ef4444",
              cursor: "pointer",
              fontSize: "14px",
            }}
          >
            Reset Engine Data
          </button>
        ) : (
          <div
            style={{
              padding: "16px",
              backgroundColor: "#1a1a2e",
              borderRadius: "4px",
            }}
          >
            <p
              style={{
                color: "#ef4444",
                fontSize: "14px",
                marginBottom: "16px",
              }}
            >
              Are you sure? This will delete all jobs, receipts, and settings. A
              diagnostics bundle will be exported first.
            </p>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                onClick={() => {
                  // TODO: Implement reset
                  console.log("Reset confirmed");
                  setResetConfirm(false);
                }}
                style={{
                  padding: "8px 16px",
                  borderRadius: "4px",
                  border: "none",
                  backgroundColor: "#ef4444",
                  color: "white",
                  cursor: "pointer",
                  fontSize: "14px",
                }}
              >
                Yes, Reset Everything
              </button>
              <button
                onClick={() => setResetConfirm(false)}
                style={{
                  padding: "8px 16px",
                  borderRadius: "4px",
                  border: "1px solid #4a4a6a",
                  backgroundColor: "transparent",
                  color: "#9ca3af",
                  cursor: "pointer",
                  fontSize: "14px",
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
