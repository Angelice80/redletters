/**
 * Diagnostics screen - Export diagnostics bundle.
 */

import { useState } from "react";
import type { DiagnosticsReport, IntegritySummary } from "../api/types";
import { ApiClient } from "../api/client";

interface DiagnosticsProps {
  client: ApiClient | null;
}

export function Diagnostics({ client }: DiagnosticsProps) {
  const [exporting, setExporting] = useState(false);
  const [fullIntegrity, setFullIntegrity] = useState(false);
  const [result, setResult] = useState<DiagnosticsReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    if (!client) return;

    setExporting(true);
    setError(null);
    setResult(null);

    try {
      const report = await client.exportDiagnostics(fullIntegrity);
      setResult(report);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setExporting(false);
    }
  };

  const renderSummary = (summary: IntegritySummary) => {
    const items = [
      { label: "OK", value: summary.ok, color: "#22c55e" },
      { label: "Warnings", value: summary.warn, color: "#f59e0b" },
      { label: "Failures", value: summary.fail, color: "#ef4444" },
      { label: "Skipped", value: summary.skipped, color: "#6b7280" },
    ];

    return (
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "12px",
          marginBottom: "16px",
        }}
      >
        {items.map((item) => (
          <div
            key={item.label}
            style={{
              padding: "12px",
              backgroundColor: "#1a1a2e",
              borderRadius: "4px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: "24px",
                fontWeight: 600,
                color: item.color,
              }}
            >
              {item.value}
            </div>
            <div style={{ fontSize: "12px", color: "#9ca3af" }}>
              {item.label}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div style={{ padding: "24px" }}>
      <h1 style={{ fontSize: "24px", fontWeight: 600, marginBottom: "24px" }}>
        Diagnostics
      </h1>

      {/* Export Controls */}
      <div
        style={{
          padding: "16px",
          backgroundColor: "#2d2d44",
          borderRadius: "8px",
          marginBottom: "24px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "16px",
            marginBottom: "16px",
          }}
        >
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              cursor: "pointer",
            }}
          >
            <input
              type="checkbox"
              checked={fullIntegrity}
              onChange={(e) => setFullIntegrity(e.target.checked)}
              style={{ width: "16px", height: "16px" }}
            />
            <span style={{ fontSize: "14px" }}>Full integrity check</span>
          </label>
          <span style={{ fontSize: "12px", color: "#6b7280" }}>
            (includes large files, may take longer)
          </span>
        </div>

        <button
          onClick={handleExport}
          disabled={exporting || !client}
          style={{
            padding: "10px 20px",
            borderRadius: "4px",
            border: "none",
            backgroundColor: "#3b82f6",
            color: "white",
            cursor: exporting ? "wait" : "pointer",
            fontSize: "14px",
            fontWeight: 500,
            opacity: exporting || !client ? 0.6 : 1,
          }}
        >
          {exporting ? "Exporting..." : "Export Bundle"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div
          style={{
            padding: "12px 16px",
            backgroundColor: "#ef4444",
            borderRadius: "4px",
            color: "white",
            marginBottom: "16px",
          }}
        >
          Error: {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div
          style={{
            padding: "16px",
            backgroundColor: "#2d2d44",
            borderRadius: "8px",
          }}
        >
          <h2
            style={{
              fontSize: "16px",
              fontWeight: 600,
              marginBottom: "16px",
            }}
          >
            Export Complete
          </h2>

          {/* File Path */}
          <div
            style={{
              padding: "12px",
              backgroundColor: "#1a1a2e",
              borderRadius: "4px",
              marginBottom: "16px",
            }}
          >
            <div
              style={{
                color: "#9ca3af",
                fontSize: "12px",
                marginBottom: "4px",
              }}
            >
              Bundle Location
            </div>
            <div
              style={{
                fontFamily: "monospace",
                fontSize: "13px",
                wordBreak: "break-all",
              }}
            >
              {result.path}
            </div>
          </div>

          {/* Integrity Summary */}
          <div style={{ marginBottom: "16px" }}>
            <div
              style={{
                color: "#9ca3af",
                fontSize: "12px",
                marginBottom: "8px",
                textTransform: "uppercase",
                fontWeight: 600,
              }}
            >
              Integrity Summary
            </div>
            {renderSummary(result.report.summary)}
          </div>

          {/* Failures */}
          {result.report.failures.length > 0 && (
            <div>
              <div
                style={{
                  color: "#ef4444",
                  fontSize: "12px",
                  marginBottom: "8px",
                  textTransform: "uppercase",
                  fontWeight: 600,
                }}
              >
                Failures ({result.report.failures.length})
              </div>
              <div
                style={{
                  maxHeight: "200px",
                  overflowY: "auto",
                  backgroundColor: "#1a1a2e",
                  borderRadius: "4px",
                }}
              >
                {result.report.failures.map((failure, index) => (
                  <div
                    key={index}
                    style={{
                      padding: "8px 12px",
                      borderBottom:
                        index < result.report.failures.length - 1
                          ? "1px solid #2d2d44"
                          : "none",
                    }}
                  >
                    <div style={{ fontSize: "12px", color: "#ef4444" }}>
                      [{failure.reason}] {failure.job_id}
                    </div>
                    <div
                      style={{
                        fontSize: "11px",
                        color: "#6b7280",
                        fontFamily: "monospace",
                      }}
                    >
                      {failure.path}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Report Metadata */}
          <div
            style={{
              marginTop: "16px",
              padding: "8px 12px",
              backgroundColor: "#1a1a2e",
              borderRadius: "4px",
              fontSize: "11px",
              color: "#6b7280",
            }}
          >
            <div>
              Generated: {new Date(result.report.generated_at).toLocaleString()}
            </div>
            <div>
              Mode:{" "}
              {result.report.full_integrity_mode ? "Full Integrity" : "Default"}
            </div>
            <div>
              Size Threshold:{" "}
              {(result.report.size_threshold_bytes / 1024 / 1024).toFixed(0)} MB
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
