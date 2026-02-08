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
      { label: "OK", value: summary.ok, color: "var(--rl-success)" },
      { label: "Warnings", value: summary.warn, color: "var(--rl-warning)" },
      { label: "Failures", value: summary.fail, color: "var(--rl-error)" },
      { label: "Skipped", value: summary.skipped, color: "var(--rl-text-dim)" },
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
              backgroundColor: "var(--rl-bg-app)",
              borderRadius: "4px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: "var(--rl-fs-xl)",
                fontWeight: 600,
                color: item.color,
              }}
            >
              {item.value}
            </div>
            <div style={{ fontSize: "var(--rl-fs-sm)", color: "var(--rl-text-muted)" }}>
              {item.label}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div style={{ padding: "24px" }}>
      <h1 style={{ fontSize: "var(--rl-fs-xl)", fontWeight: 600, marginBottom: "24px" }}>
        Diagnostics
      </h1>

      {/* Export Controls */}
      <div
        style={{
          padding: "16px",
          backgroundColor: "var(--rl-bg-card)",
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
            <span style={{ fontSize: "var(--rl-fs-base)" }}>Full integrity check</span>
          </label>
          <span style={{ fontSize: "var(--rl-fs-sm)", color: "var(--rl-text-dim)" }}>
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
            backgroundColor: "var(--rl-primary)",
            color: "white",
            cursor: exporting ? "wait" : "pointer",
            fontSize: "var(--rl-fs-base)",
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
            backgroundColor: "var(--rl-error)",
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
            backgroundColor: "var(--rl-bg-card)",
            borderRadius: "8px",
          }}
        >
          <h2
            style={{
              fontSize: "var(--rl-fs-md)",
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
              backgroundColor: "var(--rl-bg-app)",
              borderRadius: "4px",
              marginBottom: "16px",
            }}
          >
            <div
              style={{
                color: "var(--rl-text-muted)",
                fontSize: "var(--rl-fs-sm)",
                marginBottom: "4px",
              }}
            >
              Bundle Location
            </div>
            <div
              style={{
                fontFamily: "var(--rl-font-mono)",
                fontSize: "var(--rl-fs-base)",
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
                color: "var(--rl-text-muted)",
                fontSize: "var(--rl-fs-sm)",
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
                  color: "var(--rl-error)",
                  fontSize: "var(--rl-fs-sm)",
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
                  backgroundColor: "var(--rl-bg-app)",
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
                          ? "1px solid var(--rl-bg-card)"
                          : "none",
                    }}
                  >
                    <div style={{ fontSize: "var(--rl-fs-sm)", color: "var(--rl-error)" }}>
                      [{failure.reason}] {failure.job_id}
                    </div>
                    <div
                      style={{
                        fontSize: "var(--rl-fs-xs)",
                        color: "var(--rl-text-dim)",
                        fontFamily: "var(--rl-font-mono)",
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
              backgroundColor: "var(--rl-bg-app)",
              borderRadius: "4px",
              fontSize: "var(--rl-fs-xs)",
              color: "var(--rl-text-dim)",
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
