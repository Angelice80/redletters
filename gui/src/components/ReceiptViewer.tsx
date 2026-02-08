/**
 * ReceiptViewer - Displays job receipt with structured collapsible sections.
 *
 * Sprint 20: Jobs-first GUI UX loop
 *
 * Features:
 * - Job metadata (job_id, run_id, receipt_status, timestamps)
 * - Artifacts list with paths, sizes, sha256
 * - Collapsible sections for config snapshot and source pins
 * - Error details for failed jobs
 * - Copy JSON button for full receipt
 */

import { useCallback, useEffect, useState } from "react";
import type { JobReceipt, JobState, ArtifactInfo } from "../api/types";
import { ApiClient } from "../api/client";

interface ReceiptViewerProps {
  jobId: string;
  jobState: JobState;
  client: ApiClient | null;
}

const TERMINAL_STATES: JobState[] = ["completed", "failed", "cancelled"];

// Styles
const containerStyle: React.CSSProperties = {
  backgroundColor: "var(--rl-bg-card)",
  borderRadius: "8px",
  overflow: "hidden",
};

const headerStyle: React.CSSProperties = {
  padding: "12px 16px",
  borderBottom: "1px solid var(--rl-border-strong)",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

const copyButtonStyle: React.CSSProperties = {
  padding: "4px 10px",
  fontSize: "var(--rl-fs-xs)",
  backgroundColor: "var(--rl-border-strong)",
  color: "var(--rl-text-muted)",
  border: "none",
  borderRadius: "4px",
  cursor: "pointer",
};

const contentStyle: React.CSSProperties = {
  padding: "16px",
};

const sectionStyle: React.CSSProperties = {
  marginBottom: "16px",
};

const sectionHeaderStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
  padding: "8px 0",
  cursor: "pointer",
  userSelect: "none",
  borderBottom: "1px solid var(--rl-border-strong)",
};

const sectionLabelStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-sm)",
  fontWeight: 500,
  color: "var(--rl-text-muted)",
  textTransform: "uppercase",
};

const chevronStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xs)",
  color: "var(--rl-text-dim)",
  transition: "transform 0.15s",
};

const rowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  padding: "8px 0",
  borderBottom: "1px solid var(--rl-border-strong)",
};

const labelStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-sm)",
  color: "var(--rl-text-dim)",
  minWidth: "100px",
};

const valueStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-sm)",
  color: "var(--rl-text)",
  textAlign: "right",
  wordBreak: "break-all",
};

const codeStyle: React.CSSProperties = {
  fontFamily: "var(--rl-font-mono)",
  fontSize: "var(--rl-fs-xs)",
  backgroundColor: "var(--rl-border-strong)",
  padding: "2px 6px",
  borderRadius: "3px",
  color: "var(--rl-text-muted)",
  wordBreak: "break-all",
};

const artifactRowStyle: React.CSSProperties = {
  padding: "10px",
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "4px",
  marginBottom: "6px",
};

const artifactPathStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-sm)",
  color: "#60a5fa",
  fontFamily: "var(--rl-font-mono)",
  wordBreak: "break-all",
  marginBottom: "4px",
};

const artifactMetaStyle: React.CSSProperties = {
  display: "flex",
  gap: "16px",
  fontSize: "var(--rl-fs-xs)",
  color: "var(--rl-text-dim)",
};

const errorBoxStyle: React.CSSProperties = {
  padding: "12px",
  backgroundColor: "#450a0a",
  borderRadius: "6px",
  marginBottom: "16px",
};

const preStyle: React.CSSProperties = {
  fontFamily: "var(--rl-font-mono)",
  fontSize: "var(--rl-fs-xs)",
  color: "var(--rl-text-muted)",
  backgroundColor: "var(--rl-bg-app)",
  padding: "12px",
  borderRadius: "4px",
  overflow: "auto",
  maxHeight: "200px",
  whiteSpace: "pre-wrap",
  wordBreak: "break-word",
  margin: 0,
};

const statusBadgeStyle: React.CSSProperties = {
  padding: "3px 8px",
  borderRadius: "4px",
  fontSize: "var(--rl-fs-xs)",
  fontWeight: 600,
  textTransform: "uppercase",
};

const loadingStyle: React.CSSProperties = {
  padding: "24px",
  textAlign: "center",
  color: "var(--rl-text-dim)",
  fontSize: "var(--rl-fs-base)",
  backgroundColor: "var(--rl-bg-card)",
  borderRadius: "8px",
};

const errorMessageStyle: React.CSSProperties = {
  padding: "16px",
  backgroundColor: "var(--rl-bg-card)",
  borderRadius: "8px",
};

const retryButtonStyle: React.CSSProperties = {
  padding: "6px 14px",
  borderRadius: "4px",
  border: "none",
  backgroundColor: "var(--rl-primary)",
  color: "white",
  cursor: "pointer",
  fontSize: "var(--rl-fs-sm)",
};

const pendingStyle: React.CSSProperties = {
  padding: "16px",
  backgroundColor: "var(--rl-bg-card)",
  borderRadius: "8px",
  color: "var(--rl-text-muted)",
  textAlign: "center",
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatTimestamp(ts: string | undefined): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    completed: { bg: "#14532d", text: "#86efac" },
    failed: { bg: "#7f1d1d", text: "#fca5a5" },
    cancelled: { bg: "#78350f", text: "#fcd34d" },
  };

  const color = colors[status] ?? { bg: "var(--rl-border-strong)", text: "var(--rl-text-muted)" };

  return (
    <span
      style={{
        ...statusBadgeStyle,
        backgroundColor: color.bg,
        color: color.text,
      }}
    >
      {status}
    </span>
  );
}

function CollapsibleSection({
  title,
  count,
  defaultOpen = false,
  children,
}: {
  title: string;
  count?: number;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div style={sectionStyle}>
      <div
        style={sectionHeaderStyle}
        onClick={() => setIsOpen(!isOpen)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && setIsOpen(!isOpen)}
      >
        <span
          style={{
            ...chevronStyle,
            transform: isOpen ? "rotate(90deg)" : "rotate(0deg)",
          }}
        >
          ▶
        </span>
        <span style={sectionLabelStyle}>
          {title}
          {count !== undefined && ` (${count})`}
        </span>
      </div>
      {isOpen && <div style={{ paddingTop: "8px" }}>{children}</div>}
    </div>
  );
}

function ArtifactsList({ artifacts }: { artifacts: ArtifactInfo[] }) {
  return (
    <>
      {artifacts.map((artifact, idx) => (
        <div key={idx} style={artifactRowStyle}>
          <div style={artifactPathStyle}>{artifact.path}</div>
          <div style={artifactMetaStyle}>
            <span>{formatBytes(artifact.size_bytes)}</span>
            <span title={artifact.sha256}>
              sha256: {artifact.sha256.slice(0, 16)}...
            </span>
          </div>
        </div>
      ))}
    </>
  );
}

function ReceiptContent({ receipt }: { receipt: JobReceipt }) {
  const [copied, setCopied] = useState(false);

  const handleCopyJson = useCallback(() => {
    const json = JSON.stringify(receipt, null, 2);
    navigator.clipboard.writeText(json);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [receipt]);

  const hasSourcePins =
    receipt.source_pins && Object.keys(receipt.source_pins).length > 0;
  const hasConfigSnapshot =
    receipt.config_snapshot && Object.keys(receipt.config_snapshot).length > 0;
  const hasInputsSummary =
    receipt.inputs_summary && Object.keys(receipt.inputs_summary).length > 0;
  const hasErrorDetails =
    receipt.error_details && Object.keys(receipt.error_details).length > 0;

  return (
    <div style={containerStyle}>
      {/* Header */}
      <div style={headerStyle}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{ fontWeight: 600, color: "var(--rl-text)" }}>Job Receipt</span>
          <StatusBadge status={receipt.receipt_status} />
        </div>
        <button style={copyButtonStyle} onClick={handleCopyJson}>
          {copied ? "Copied!" : "Copy JSON"}
        </button>
      </div>

      <div style={contentStyle}>
        {/* Metadata */}
        <div style={sectionStyle}>
          <div style={rowStyle}>
            <span style={labelStyle}>Job ID</span>
            <code style={codeStyle}>{receipt.job_id}</code>
          </div>
          <div style={rowStyle}>
            <span style={labelStyle}>Run ID</span>
            <code style={codeStyle}>{receipt.run_id}</code>
          </div>
          <div style={rowStyle}>
            <span style={labelStyle}>Schema</span>
            <span style={valueStyle}>{receipt.schema_version}</span>
          </div>
          {receipt.exit_code && (
            <div style={rowStyle}>
              <span style={labelStyle}>Exit Code</span>
              <code style={codeStyle}>{receipt.exit_code}</code>
            </div>
          )}
        </div>

        {/* Timestamps */}
        <CollapsibleSection title="Timestamps" defaultOpen>
          <div style={rowStyle}>
            <span style={labelStyle}>Created</span>
            <span style={valueStyle}>
              {formatTimestamp(receipt.timestamps.created)}
            </span>
          </div>
          {receipt.timestamps.started && (
            <div style={rowStyle}>
              <span style={labelStyle}>Started</span>
              <span style={valueStyle}>
                {formatTimestamp(receipt.timestamps.started)}
              </span>
            </div>
          )}
          {receipt.timestamps.completed && (
            <div style={rowStyle}>
              <span style={labelStyle}>Completed</span>
              <span style={valueStyle}>
                {formatTimestamp(receipt.timestamps.completed)}
              </span>
            </div>
          )}
        </CollapsibleSection>

        {/* Error Details (if failed) */}
        {receipt.receipt_status === "failed" && receipt.error_message && (
          <div style={errorBoxStyle}>
            <div
              style={{ color: "#fca5a5", fontWeight: 500, marginBottom: "8px" }}
            >
              {receipt.error_code || "Error"}
            </div>
            <div
              style={{
                color: "#fecaca",
                fontSize: "var(--rl-fs-sm)",
                fontFamily: "var(--rl-font-mono)",
                whiteSpace: "pre-wrap",
                maxHeight: "150px",
                overflow: "auto",
              }}
            >
              {receipt.error_message}
            </div>
          </div>
        )}

        {/* Artifacts */}
        {receipt.outputs && receipt.outputs.length > 0 && (
          <CollapsibleSection
            title="Artifacts"
            count={receipt.outputs.length}
            defaultOpen
          >
            <ArtifactsList artifacts={receipt.outputs} />
          </CollapsibleSection>
        )}

        {/* Source Pins */}
        {hasSourcePins && (
          <CollapsibleSection
            title="Source Pins"
            count={Object.keys(receipt.source_pins).length}
          >
            {Object.entries(receipt.source_pins).map(([source, version]) => (
              <div key={source} style={rowStyle}>
                <span style={labelStyle}>{source}</span>
                <code style={codeStyle}>{version}</code>
              </div>
            ))}
          </CollapsibleSection>
        )}

        {/* Config Snapshot */}
        {hasConfigSnapshot && (
          <CollapsibleSection title="Config Snapshot">
            <pre style={preStyle}>
              {JSON.stringify(receipt.config_snapshot, null, 2)}
            </pre>
          </CollapsibleSection>
        )}

        {/* Inputs Summary */}
        {hasInputsSummary && (
          <CollapsibleSection title="Inputs Summary">
            <pre style={preStyle}>
              {JSON.stringify(receipt.inputs_summary, null, 2)}
            </pre>
          </CollapsibleSection>
        )}

        {/* Error Details JSON */}
        {hasErrorDetails && (
          <CollapsibleSection title="Error Details">
            <pre style={preStyle}>
              {JSON.stringify(receipt.error_details, null, 2)}
            </pre>
          </CollapsibleSection>
        )}
      </div>
    </div>
  );
}

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
      <div style={pendingStyle}>
        Receipt will be available when job completes.
      </div>
    );
  }

  if (loading) {
    return <div style={loadingStyle}>Loading receipt...</div>;
  }

  if (error) {
    return (
      <div style={errorMessageStyle}>
        <div style={{ color: "var(--rl-error)", marginBottom: "12px" }}>
          Failed to load receipt: {error}
        </div>
        <button onClick={fetchReceipt} style={retryButtonStyle}>
          Retry
        </button>
      </div>
    );
  }

  if (!receipt) {
    return null;
  }

  return <ReceiptContent receipt={receipt} />;
}

export default ReceiptViewer;
