/**
 * ReceiptViewer component - Displays job receipt JSON.
 */

import { useCallback, useEffect, useState } from "react";
import type { JobReceipt, JobState } from "../api/types";
import { ApiClient } from "../api/client";

interface ReceiptViewerProps {
  jobId: string;
  jobState: JobState;
  client: ApiClient | null;
}

const TERMINAL_STATES: JobState[] = ["completed", "failed", "cancelled"];

export function ReceiptViewer({ jobId, jobState, client }: ReceiptViewerProps) {
  const [receipt, setReceipt] = useState<JobReceipt | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isTerminal = TERMINAL_STATES.includes(jobState);

  const fetchReceipt = useCallback(async () => {
    if (!client || !isTerminal) return;

    setLoading(true);
    setError(null);

    try {
      const data = await client.getReceipt(jobId);
      setReceipt(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [client, jobId, isTerminal]);

  // Fetch receipt when job reaches terminal state
  useEffect(() => {
    if (isTerminal && !receipt && !loading && !error) {
      fetchReceipt();
    }
  }, [isTerminal, receipt, loading, error, fetchReceipt]);

  if (!isTerminal) {
    return (
      <div
        style={{
          padding: "16px",
          backgroundColor: "#2d2d44",
          borderRadius: "4px",
          color: "#9ca3af",
          textAlign: "center",
        }}
      >
        Receipt will be available when job completes.
      </div>
    );
  }

  if (loading) {
    return (
      <div
        style={{
          padding: "16px",
          backgroundColor: "#2d2d44",
          borderRadius: "4px",
          color: "#9ca3af",
          textAlign: "center",
        }}
      >
        Loading receipt...
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          padding: "16px",
          backgroundColor: "#2d2d44",
          borderRadius: "4px",
        }}
      >
        <div style={{ color: "#ef4444", marginBottom: "8px" }}>
          Failed to load receipt: {error}
        </div>
        <button
          onClick={fetchReceipt}
          style={{
            padding: "4px 12px",
            borderRadius: "4px",
            border: "none",
            backgroundColor: "#3b82f6",
            color: "white",
            cursor: "pointer",
            fontSize: "12px",
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  if (!receipt) {
    return null;
  }

  const formatTimestamp = (ts: string | undefined) => {
    if (!ts) return "N/A";
    try {
      return new Date(ts).toLocaleString();
    } catch {
      return ts;
    }
  };

  return (
    <div
      style={{
        backgroundColor: "#2d2d44",
        borderRadius: "4px",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid #4a4a6a",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span style={{ fontWeight: 600 }}>Job Receipt</span>
        <span
          style={{
            padding: "2px 8px",
            borderRadius: "4px",
            backgroundColor:
              receipt.receipt_status === "completed"
                ? "#22c55e"
                : receipt.receipt_status === "failed"
                  ? "#ef4444"
                  : "#6b7280",
            color: "white",
            fontSize: "12px",
            fontWeight: 500,
            textTransform: "uppercase",
          }}
        >
          {receipt.receipt_status}
        </span>
      </div>

      {/* Summary */}
      <div style={{ padding: "16px" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "auto 1fr",
            gap: "8px 16px",
            marginBottom: "16px",
            fontSize: "13px",
          }}
        >
          <span style={{ color: "#9ca3af" }}>Job ID:</span>
          <span style={{ fontFamily: "monospace" }}>{receipt.job_id}</span>

          <span style={{ color: "#9ca3af" }}>Run ID:</span>
          <span style={{ fontFamily: "monospace" }}>{receipt.run_id}</span>

          <span style={{ color: "#9ca3af" }}>Created:</span>
          <span>{formatTimestamp(receipt.timestamps.created)}</span>

          <span style={{ color: "#9ca3af" }}>Started:</span>
          <span>{formatTimestamp(receipt.timestamps.started)}</span>

          <span style={{ color: "#9ca3af" }}>Completed:</span>
          <span>{formatTimestamp(receipt.timestamps.completed)}</span>

          {receipt.error_code && (
            <>
              <span style={{ color: "#ef4444" }}>Error:</span>
              <span style={{ color: "#ef4444" }}>
                {receipt.error_code}: {receipt.error_message}
              </span>
            </>
          )}
        </div>

        {/* Outputs */}
        {receipt.outputs.length > 0 && (
          <div style={{ marginBottom: "16px" }}>
            <div
              style={{
                color: "#9ca3af",
                marginBottom: "8px",
                fontSize: "12px",
                fontWeight: 600,
                textTransform: "uppercase",
              }}
            >
              Outputs ({receipt.outputs.length})
            </div>
            {receipt.outputs.map((output, index) => (
              <div
                key={index}
                style={{
                  padding: "8px",
                  backgroundColor: "#1a1a2e",
                  borderRadius: "4px",
                  marginBottom: "4px",
                  fontFamily: "monospace",
                  fontSize: "12px",
                }}
              >
                <div>{output.path}</div>
                <div style={{ color: "#6b7280", marginTop: "4px" }}>
                  {(output.size_bytes / 1024).toFixed(1)} KB | sha256:{" "}
                  {output.sha256.slice(0, 16)}...
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Full JSON */}
        <details>
          <summary
            style={{
              cursor: "pointer",
              color: "#3b82f6",
              fontSize: "12px",
              marginBottom: "8px",
            }}
          >
            View Full JSON
          </summary>
          <pre
            style={{
              backgroundColor: "#1a1a2e",
              padding: "12px",
              borderRadius: "4px",
              overflow: "auto",
              maxHeight: "300px",
              fontSize: "11px",
              lineHeight: 1.4,
            }}
          >
            {JSON.stringify(receipt, null, 2)}
          </pre>
        </details>
      </div>
    </div>
  );
}
