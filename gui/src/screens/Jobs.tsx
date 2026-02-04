/**
 * Jobs screen - List jobs with filters, cancel, and detail drawer.
 *
 * Sprint 19: Jobs-native GUI
 * - Cancel with confirmation dialog
 * - Job detail drawer with full result info
 * - Gate-blocked as terminal non-error state
 * - Live SSE updates via store
 *
 * Sprint 17: Enhanced with:
 * - Job state filters (All / Running / Failed / Completed)
 * - Failed job summary with tucked traceback
 * - Copy Diagnostics button for failed jobs
 */

import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore, selectJobs } from "../store";
import type {
  JobResponse,
  JobState,
  ApiErrorDetail,
  ScholarlyJobResult,
} from "../api/types";
import { ApiClient } from "../api/client";
import {
  ApiErrorPanel,
  createApiErrorDetail,
} from "../components/ApiErrorPanel";
import { ReceiptViewer } from "../components/ReceiptViewer";

interface JobsProps {
  client: ApiClient | null;
  onRefresh: () => Promise<void>;
}

const STATE_COLORS: Record<JobState, string> = {
  queued: "#6b7280",
  running: "#3b82f6",
  cancelling: "#f59e0b",
  cancelled: "#9ca3af",
  completed: "#22c55e",
  failed: "#ef4444",
  archived: "#6b7280",
};

// Sprint 17: Filter types
type JobFilter = "all" | "running" | "failed" | "completed";

const filterStyle: React.CSSProperties = {
  display: "flex",
  gap: "8px",
  marginBottom: "16px",
};

const filterButtonStyle: React.CSSProperties = {
  padding: "6px 12px",
  fontSize: "12px",
  backgroundColor: "#374151",
  color: "#9ca3af",
  border: "1px solid #4b5563",
  borderRadius: "4px",
  cursor: "pointer",
};

const filterActiveStyle: React.CSSProperties = {
  ...filterButtonStyle,
  backgroundColor: "#3b82f6",
  color: "white",
  borderColor: "#3b82f6",
};

const errorSummaryStyle: React.CSSProperties = {
  backgroundColor: "#450a0a",
  borderRadius: "4px",
  padding: "12px",
  marginTop: "12px",
  fontSize: "13px",
};

const errorDetailsStyle: React.CSSProperties = {
  marginTop: "8px",
  padding: "8px",
  backgroundColor: "#1a1a2e",
  borderRadius: "4px",
  fontSize: "11px",
  fontFamily: "monospace",
  color: "#9ca3af",
  maxHeight: "150px",
  overflow: "auto",
  whiteSpace: "pre-wrap",
  wordBreak: "break-word",
};

const copyButtonStyle: React.CSSProperties = {
  padding: "4px 8px",
  fontSize: "10px",
  backgroundColor: "#374151",
  color: "#9ca3af",
  border: "none",
  borderRadius: "3px",
  cursor: "pointer",
  marginLeft: "8px",
};

// Sprint 19: Drawer styles
const drawerOverlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  backgroundColor: "rgba(0, 0, 0, 0.5)",
  zIndex: 1000,
};

const drawerStyle: React.CSSProperties = {
  position: "fixed",
  top: 0,
  right: 0,
  width: "480px",
  height: "100vh",
  backgroundColor: "#2d2d44",
  boxShadow: "-4px 0 20px rgba(0, 0, 0, 0.3)",
  zIndex: 1001,
  display: "flex",
  flexDirection: "column",
  overflow: "hidden",
};

const drawerHeaderStyle: React.CSSProperties = {
  padding: "20px",
  borderBottom: "1px solid #4b5563",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

const drawerContentStyle: React.CSSProperties = {
  padding: "20px",
  flex: 1,
  overflow: "auto",
};

const drawerSectionStyle: React.CSSProperties = {
  marginBottom: "20px",
};

const drawerLabelStyle: React.CSSProperties = {
  fontSize: "11px",
  color: "#6b7280",
  textTransform: "uppercase",
  marginBottom: "4px",
};

const drawerValueStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#eaeaea",
};

const codeStyle: React.CSSProperties = {
  fontFamily: "monospace",
  backgroundColor: "#1a1a2e",
  padding: "4px 8px",
  borderRadius: "4px",
  fontSize: "12px",
  color: "#9ca3af",
  wordBreak: "break-all",
};

const gateBlockedBoxStyle: React.CSSProperties = {
  padding: "16px",
  backgroundColor: "#78350f",
  borderRadius: "8px",
  marginBottom: "16px",
};

const confirmDialogOverlay: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  backgroundColor: "rgba(0, 0, 0, 0.6)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 2000,
};

const confirmDialogStyle: React.CSSProperties = {
  backgroundColor: "#2d2d44",
  borderRadius: "8px",
  padding: "24px",
  width: "360px",
  boxShadow: "0 4px 20px rgba(0, 0, 0, 0.4)",
};

export function Jobs({ client, onRefresh }: JobsProps) {
  const navigate = useNavigate();
  const jobs = useAppStore(selectJobs);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<ApiErrorDetail | null>(null);

  // Sprint 17: Filter state
  const [filter, setFilter] = useState<JobFilter>("all");
  // Track which jobs have expanded error details
  const [expandedErrors, setExpandedErrors] = useState<Set<string>>(new Set());
  // Track copy state
  const [copiedJobId, setCopiedJobId] = useState<string | null>(null);

  // Sprint 19: Drawer and cancel dialog state
  const [selectedJob, setSelectedJob] = useState<JobResponse | null>(null);
  const [cancelConfirmJob, setCancelConfirmJob] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);

  const handleCreateDemoJob = async () => {
    if (!client) return;

    setCreating(true);
    setError(null);

    try {
      await client.createJob({
        config: {
          input_paths: ["demo:matthew"],
          style: "natural",
          options: {},
        },
      });
      await onRefresh();
    } catch (err) {
      setError(createApiErrorDetail("POST", "/v1/jobs", err));
    } finally {
      setCreating(false);
    }
  };

  // Sprint 19: Cancel with confirmation
  const handleCancelClick = (jobId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setCancelConfirmJob(jobId);
  };

  const handleCancelConfirm = async () => {
    if (!client || !cancelConfirmJob) return;

    setCancelling(true);
    try {
      await client.cancelJob(cancelConfirmJob);
      await onRefresh();
    } catch (err) {
      setError(
        createApiErrorDetail(
          "POST",
          `/v1/jobs/${cancelConfirmJob}/cancel`,
          err,
        ),
      );
    } finally {
      setCancelling(false);
      setCancelConfirmJob(null);
    }
  };

  const handleCancelDismiss = () => {
    setCancelConfirmJob(null);
  };

  const toggleErrorDetails = (jobId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedErrors((prev) => {
      const next = new Set(prev);
      if (next.has(jobId)) {
        next.delete(jobId);
      } else {
        next.add(jobId);
      }
      return next;
    });
  };

  const handleCopyDiagnostics = useCallback(
    (job: JobResponse, e: React.MouseEvent) => {
      e.stopPropagation();

      const diagnostics = `Job Diagnostics
===============
Job ID: ${job.job_id}
State: ${job.state}
Created: ${job.created_at}
${job.started_at ? `Started: ${job.started_at}` : ""}
${job.completed_at ? `Completed: ${job.completed_at}` : ""}

Config:
${JSON.stringify(job.config, null, 2)}

${
  job.error_code
    ? `Error
-----
Code: ${job.error_code}
Message: ${job.error_message || "No message"}
`
    : ""
}
`;

      navigator.clipboard.writeText(diagnostics);
      setCopiedJobId(job.job_id);
      setTimeout(() => setCopiedJobId(null), 2000);
    },
    [],
  );

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  // Get friendly error summary
  const getErrorSummary = (job: JobResponse): string => {
    if (!job.error_code) return "";

    const msg = job.error_message || "";
    const lines = msg.split("\n").filter((l) => l.trim());

    if (lines.length === 0) return job.error_code;

    if (msg.includes("Traceback") || msg.includes("Error:")) {
      const errorLine = lines.find(
        (l) => l.includes("Error:") || l.includes("Exception:"),
      );
      if (errorLine) {
        return errorLine.trim().slice(0, 100);
      }
    }

    return lines[0].slice(0, 100);
  };

  // Sprint 19: Check if job is gate-blocked
  const isGateBlocked = (job: JobResponse): boolean => {
    const result = job.result as ScholarlyJobResult | undefined;
    return job.state === "completed" && result?.gate_blocked === true;
  };

  // Sprint 19: Get job result details
  const getJobResult = (job: JobResponse): ScholarlyJobResult | null => {
    return (job.result as ScholarlyJobResult) || null;
  };

  // Filter jobs
  const filteredJobs = jobs.filter((job) => {
    if (filter === "all") return true;
    if (filter === "running")
      return job.state === "running" || job.state === "queued";
    if (filter === "failed") return job.state === "failed";
    if (filter === "completed") return job.state === "completed";
    return true;
  });

  // Sort jobs by created_at (newest first)
  const sortedJobs = [...filteredJobs].sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  // Count jobs by state
  const counts = {
    all: jobs.length,
    running: jobs.filter((j) => j.state === "running" || j.state === "queued")
      .length,
    failed: jobs.filter((j) => j.state === "failed").length,
    completed: jobs.filter((j) => j.state === "completed").length,
  };

  return (
    <div style={{ padding: "24px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "24px",
        }}
      >
        <h1 style={{ fontSize: "24px", fontWeight: 600, margin: 0 }}>Jobs</h1>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={onRefresh}
            style={{
              padding: "8px 16px",
              borderRadius: "4px",
              border: "1px solid #4a4a6a",
              backgroundColor: "transparent",
              color: "#eaeaea",
              cursor: "pointer",
              fontSize: "14px",
            }}
          >
            Refresh
          </button>
          <button
            onClick={handleCreateDemoJob}
            disabled={creating || !client}
            style={{
              padding: "8px 16px",
              borderRadius: "4px",
              border: "none",
              backgroundColor: "#3b82f6",
              color: "white",
              cursor: creating ? "wait" : "pointer",
              fontSize: "14px",
              fontWeight: 500,
              opacity: creating || !client ? 0.6 : 1,
            }}
          >
            {creating ? "Creating..." : "Start Demo Job"}
          </button>
        </div>
      </div>

      {/* Error display */}
      {error && (
        <ApiErrorPanel
          error={error}
          onRetry={onRefresh}
          onDismiss={() => setError(null)}
        />
      )}

      {/* Sprint 17: Filter bar */}
      <div style={filterStyle}>
        <button
          style={filter === "all" ? filterActiveStyle : filterButtonStyle}
          onClick={() => setFilter("all")}
        >
          All ({counts.all})
        </button>
        <button
          style={filter === "running" ? filterActiveStyle : filterButtonStyle}
          onClick={() => setFilter("running")}
        >
          Running ({counts.running})
        </button>
        <button
          style={filter === "failed" ? filterActiveStyle : filterButtonStyle}
          onClick={() => setFilter("failed")}
        >
          Failed ({counts.failed})
        </button>
        <button
          style={filter === "completed" ? filterActiveStyle : filterButtonStyle}
          onClick={() => setFilter("completed")}
        >
          Completed ({counts.completed})
        </button>
      </div>

      {/* Job List */}
      {sortedJobs.length === 0 ? (
        <div
          style={{
            padding: "48px",
            textAlign: "center",
            backgroundColor: "#2d2d44",
            borderRadius: "8px",
            color: "#9ca3af",
          }}
        >
          {filter === "all"
            ? 'No jobs yet. Click "Start Demo Job" to create one.'
            : `No ${filter} jobs.`}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {sortedJobs.map((job: JobResponse) => {
            const gateBlocked = isGateBlocked(job);

            return (
              <div
                key={job.job_id}
                onClick={() => setSelectedJob(job)}
                style={{
                  padding: "16px",
                  backgroundColor: "#2d2d44",
                  borderRadius: "8px",
                  cursor: "pointer",
                  transition: "background-color 0.15s",
                  borderLeft:
                    job.state === "failed"
                      ? "3px solid #ef4444"
                      : gateBlocked
                        ? "3px solid #f59e0b"
                        : "none",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = "#3d3d54";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = "#2d2d44";
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontFamily: "monospace",
                        fontSize: "14px",
                        fontWeight: 500,
                        marginBottom: "4px",
                      }}
                    >
                      {job.job_id}
                    </div>
                    <div style={{ color: "#9ca3af", fontSize: "12px" }}>
                      Created: {formatDate(job.created_at)}
                    </div>
                    {/* Sprint 19: Show reference for scholarly jobs */}
                    {job.config.reference && (
                      <div
                        style={{
                          color: "#60a5fa",
                          fontSize: "12px",
                          marginTop: "2px",
                        }}
                      >
                        {job.config.reference}
                      </div>
                    )}
                  </div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >
                    {/* Progress */}
                    {job.state === "running" &&
                      job.progress_percent != null && (
                        <span style={{ fontSize: "12px", color: "#9ca3af" }}>
                          {job.progress_percent}%
                        </span>
                      )}

                    {/* State Badge */}
                    <span
                      style={{
                        padding: "4px 8px",
                        borderRadius: "4px",
                        backgroundColor: gateBlocked
                          ? "#f59e0b"
                          : STATE_COLORS[job.state],
                        color: "white",
                        fontSize: "11px",
                        fontWeight: 600,
                        textTransform: "uppercase",
                      }}
                    >
                      {gateBlocked ? "GATE BLOCKED" : job.state}
                    </span>

                    {/* Cancel Button */}
                    {(job.state === "queued" || job.state === "running") && (
                      <button
                        onClick={(e) => handleCancelClick(job.job_id, e)}
                        style={{
                          padding: "4px 8px",
                          borderRadius: "4px",
                          border: "1px solid #ef4444",
                          backgroundColor: "transparent",
                          color: "#ef4444",
                          cursor: "pointer",
                          fontSize: "11px",
                        }}
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>

                {/* Progress Bar */}
                {job.state === "running" && (
                  <div style={{ marginTop: "12px" }}>
                    <div
                      style={{
                        height: "4px",
                        backgroundColor: "#1a1a2e",
                        borderRadius: "2px",
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          height: "100%",
                          width: `${job.progress_percent ?? 0}%`,
                          backgroundColor: "#3b82f6",
                          transition: "width 0.3s",
                        }}
                      />
                    </div>
                    {job.progress_phase && (
                      <div
                        style={{
                          marginTop: "4px",
                          fontSize: "11px",
                          color: "#6b7280",
                        }}
                      >
                        {job.progress_phase}
                      </div>
                    )}
                  </div>
                )}

                {/* Sprint 19: Gate-blocked summary */}
                {gateBlocked && (
                  <div
                    style={{
                      marginTop: "12px",
                      padding: "8px 12px",
                      backgroundColor: "#451a03",
                      borderRadius: "4px",
                      fontSize: "12px",
                      color: "#fcd34d",
                    }}
                  >
                    {getJobResult(job)?.pending_gates?.length ?? 0} variant(s)
                    require acknowledgement
                  </div>
                )}

                {/* Sprint 17: Enhanced failed job display */}
                {job.state === "failed" && job.error_message && (
                  <div style={errorSummaryStyle}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "flex-start",
                      }}
                    >
                      <div>
                        <div style={{ color: "#fca5a5", marginBottom: "4px" }}>
                          {job.error_code || "Error"}
                        </div>
                        <div style={{ color: "#9ca3af" }}>
                          {getErrorSummary(job)}
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: "4px" }}>
                        <button
                          style={copyButtonStyle}
                          onClick={(e) => handleCopyDiagnostics(job, e)}
                        >
                          {copiedJobId === job.job_id ? "Copied!" : "Copy"}
                        </button>
                        <button
                          style={copyButtonStyle}
                          onClick={(e) => toggleErrorDetails(job.job_id, e)}
                        >
                          {expandedErrors.has(job.job_id) ? "Hide" : "Details"}
                        </button>
                      </div>
                    </div>

                    {/* Expanded error details */}
                    {expandedErrors.has(job.job_id) && (
                      <div style={errorDetailsStyle}>{job.error_message}</div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Sprint 19: Job Detail Drawer */}
      {selectedJob && (
        <>
          <div
            style={drawerOverlayStyle}
            onClick={() => setSelectedJob(null)}
          />
          <div style={drawerStyle}>
            <div style={drawerHeaderStyle}>
              <div>
                <div
                  style={{
                    fontSize: "18px",
                    fontWeight: 600,
                    color: "#eaeaea",
                  }}
                >
                  Job Details
                </div>
                <div
                  style={{
                    fontSize: "12px",
                    fontFamily: "monospace",
                    color: "#6b7280",
                    marginTop: "4px",
                  }}
                >
                  {selectedJob.job_id}
                </div>
              </div>
              <button
                onClick={() => setSelectedJob(null)}
                style={{
                  background: "none",
                  border: "none",
                  color: "#6b7280",
                  cursor: "pointer",
                  fontSize: "24px",
                  padding: 0,
                  lineHeight: 1,
                }}
              >
                &times;
              </button>
            </div>

            <div style={drawerContentStyle}>
              {/* Status */}
              <div style={drawerSectionStyle}>
                <div style={drawerLabelStyle}>Status</div>
                <span
                  style={{
                    padding: "4px 12px",
                    borderRadius: "4px",
                    backgroundColor: isGateBlocked(selectedJob)
                      ? "#f59e0b"
                      : STATE_COLORS[selectedJob.state],
                    color: "white",
                    fontSize: "12px",
                    fontWeight: 600,
                  }}
                >
                  {isGateBlocked(selectedJob)
                    ? "GATE BLOCKED"
                    : selectedJob.state.toUpperCase()}
                </span>
              </div>

              {/* Reference */}
              {selectedJob.config.reference && (
                <div style={drawerSectionStyle}>
                  <div style={drawerLabelStyle}>Reference</div>
                  <div style={drawerValueStyle}>
                    {selectedJob.config.reference}
                  </div>
                </div>
              )}

              {/* Mode */}
              {selectedJob.config.mode && (
                <div style={drawerSectionStyle}>
                  <div style={drawerLabelStyle}>Mode</div>
                  <div style={drawerValueStyle}>{selectedJob.config.mode}</div>
                </div>
              )}

              {/* Timestamps */}
              <div style={drawerSectionStyle}>
                <div style={drawerLabelStyle}>Created</div>
                <div style={drawerValueStyle}>
                  {formatDate(selectedJob.created_at)}
                </div>
              </div>
              {selectedJob.started_at && (
                <div style={drawerSectionStyle}>
                  <div style={drawerLabelStyle}>Started</div>
                  <div style={drawerValueStyle}>
                    {formatDate(selectedJob.started_at)}
                  </div>
                </div>
              )}
              {selectedJob.completed_at && (
                <div style={drawerSectionStyle}>
                  <div style={drawerLabelStyle}>Completed</div>
                  <div style={drawerValueStyle}>
                    {formatDate(selectedJob.completed_at)}
                  </div>
                </div>
              )}

              {/* Progress */}
              {selectedJob.state === "running" && (
                <div style={drawerSectionStyle}>
                  <div style={drawerLabelStyle}>Progress</div>
                  <div style={{ marginTop: "8px" }}>
                    <div
                      style={{
                        height: "8px",
                        backgroundColor: "#1a1a2e",
                        borderRadius: "4px",
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          height: "100%",
                          width: `${selectedJob.progress_percent ?? 0}%`,
                          backgroundColor: "#3b82f6",
                        }}
                      />
                    </div>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        fontSize: "11px",
                        color: "#6b7280",
                        marginTop: "4px",
                      }}
                    >
                      <span>{selectedJob.progress_phase || "Processing"}</span>
                      <span>{selectedJob.progress_percent ?? 0}%</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Sprint 19: Gate-blocked result */}
              {isGateBlocked(selectedJob) && (
                <div style={gateBlockedBoxStyle}>
                  <div
                    style={{
                      color: "#fcd34d",
                      fontWeight: 600,
                      marginBottom: "8px",
                    }}
                  >
                    Gates Pending
                  </div>
                  <div
                    style={{
                      color: "#fef3c7",
                      fontSize: "13px",
                      marginBottom: "12px",
                    }}
                  >
                    The following variants require acknowledgement:
                  </div>
                  <div style={{ maxHeight: "150px", overflow: "auto" }}>
                    {getJobResult(selectedJob)?.pending_gates?.map((gate) => (
                      <div
                        key={gate}
                        style={{
                          color: "#fde68a",
                          fontSize: "12px",
                          padding: "4px 8px",
                          backgroundColor: "#451a03",
                          borderRadius: "4px",
                          marginBottom: "4px",
                        }}
                      >
                        {gate}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Success result */}
              {selectedJob.state === "completed" &&
                !isGateBlocked(selectedJob) && (
                  <div style={drawerSectionStyle}>
                    <div style={drawerLabelStyle}>Result</div>
                    {getJobResult(selectedJob)?.output_dir && (
                      <div style={{ marginTop: "8px" }}>
                        <div
                          style={{
                            fontSize: "11px",
                            color: "#6b7280",
                            marginBottom: "4px",
                          }}
                        >
                          Output Directory
                        </div>
                        <code style={codeStyle}>
                          {getJobResult(selectedJob)?.output_dir}
                        </code>
                      </div>
                    )}
                    {getJobResult(selectedJob)?.bundle_path && (
                      <div style={{ marginTop: "12px" }}>
                        <div
                          style={{
                            fontSize: "11px",
                            color: "#6b7280",
                            marginBottom: "4px",
                          }}
                        >
                          Bundle Path
                        </div>
                        <code style={codeStyle}>
                          {getJobResult(selectedJob)?.bundle_path}
                        </code>
                      </div>
                    )}
                    {getJobResult(selectedJob)?.run_log_summary && (
                      <div style={{ marginTop: "12px" }}>
                        <div
                          style={{
                            fontSize: "11px",
                            color: "#6b7280",
                            marginBottom: "4px",
                          }}
                        >
                          Summary
                        </div>
                        <div style={{ color: "#9ca3af", fontSize: "12px" }}>
                          {getJobResult(selectedJob)?.run_log_summary
                            ?.verse_count ?? 0}{" "}
                          verses,{" "}
                          {getJobResult(selectedJob)?.run_log_summary
                            ?.file_count ?? 0}{" "}
                          files
                        </div>
                      </div>
                    )}
                  </div>
                )}

              {/* Error */}
              {selectedJob.state === "failed" && selectedJob.error_message && (
                <div style={drawerSectionStyle}>
                  <div style={drawerLabelStyle}>Error</div>
                  <div
                    style={{
                      padding: "12px",
                      backgroundColor: "#450a0a",
                      borderRadius: "6px",
                      marginTop: "8px",
                    }}
                  >
                    <div
                      style={{
                        color: "#fca5a5",
                        fontWeight: 500,
                        marginBottom: "8px",
                      }}
                    >
                      {selectedJob.error_code || "Error"}
                    </div>
                    <div
                      style={{
                        color: "#9ca3af",
                        fontSize: "12px",
                        fontFamily: "monospace",
                        whiteSpace: "pre-wrap",
                        maxHeight: "200px",
                        overflow: "auto",
                      }}
                    >
                      {selectedJob.error_message}
                    </div>
                  </div>
                </div>
              )}

              {/* Sprint 20: Receipt Viewer for terminal jobs */}
              <div style={drawerSectionStyle}>
                <div style={drawerLabelStyle}>Receipt</div>
                <div style={{ marginTop: "8px" }}>
                  <ReceiptViewer
                    jobId={selectedJob.job_id}
                    jobState={selectedJob.state}
                    client={client}
                  />
                </div>
              </div>

              {/* Actions */}
              <div style={{ marginTop: "24px", display: "flex", gap: "12px" }}>
                <button
                  onClick={() => navigate(`/jobs/${selectedJob.job_id}`)}
                  style={{
                    padding: "10px 20px",
                    borderRadius: "6px",
                    border: "none",
                    backgroundColor: "#3b82f6",
                    color: "white",
                    cursor: "pointer",
                    fontSize: "13px",
                    fontWeight: 500,
                  }}
                >
                  View Full Details
                </button>
                {(selectedJob.state === "queued" ||
                  selectedJob.state === "running") && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setCancelConfirmJob(selectedJob.job_id);
                    }}
                    style={{
                      padding: "10px 20px",
                      borderRadius: "6px",
                      border: "1px solid #ef4444",
                      backgroundColor: "transparent",
                      color: "#ef4444",
                      cursor: "pointer",
                      fontSize: "13px",
                      fontWeight: 500,
                    }}
                  >
                    Cancel Job
                  </button>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {/* Sprint 19: Cancel Confirmation Dialog */}
      {cancelConfirmJob && (
        <div style={confirmDialogOverlay} onClick={handleCancelDismiss}>
          <div style={confirmDialogStyle} onClick={(e) => e.stopPropagation()}>
            <div
              style={{
                fontSize: "16px",
                fontWeight: 600,
                color: "#eaeaea",
                marginBottom: "12px",
              }}
            >
              Cancel Job?
            </div>
            <div
              style={{
                color: "#9ca3af",
                fontSize: "14px",
                marginBottom: "20px",
              }}
            >
              This is a best-effort cancellation. The job may still complete if
              it's already in a critical section.
            </div>
            <div
              style={{
                fontFamily: "monospace",
                fontSize: "12px",
                color: "#6b7280",
                backgroundColor: "#1a1a2e",
                padding: "8px",
                borderRadius: "4px",
                marginBottom: "20px",
              }}
            >
              {cancelConfirmJob}
            </div>
            <div
              style={{
                display: "flex",
                gap: "12px",
                justifyContent: "flex-end",
              }}
            >
              <button
                onClick={handleCancelDismiss}
                style={{
                  padding: "8px 16px",
                  borderRadius: "4px",
                  border: "1px solid #4b5563",
                  backgroundColor: "transparent",
                  color: "#9ca3af",
                  cursor: "pointer",
                  fontSize: "13px",
                }}
              >
                Keep Running
              </button>
              <button
                onClick={handleCancelConfirm}
                disabled={cancelling}
                style={{
                  padding: "8px 16px",
                  borderRadius: "4px",
                  border: "none",
                  backgroundColor: "#ef4444",
                  color: "white",
                  cursor: cancelling ? "wait" : "pointer",
                  fontSize: "13px",
                  fontWeight: 500,
                  opacity: cancelling ? 0.7 : 1,
                }}
              >
                {cancelling ? "Cancelling..." : "Cancel Job"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
