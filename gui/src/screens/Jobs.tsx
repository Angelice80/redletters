/**
 * Jobs screen - List jobs and create demo jobs.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore, selectJobs } from "../store";
import type { JobResponse, JobState } from "../api/types";
import { ApiClient } from "../api/client";

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

export function Jobs({ client, onRefresh }: JobsProps) {
  const navigate = useNavigate();
  const jobs = useAppStore(selectJobs);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      setError((err as Error).message);
    } finally {
      setCreating(false);
    }
  };

  const handleCancelJob = async (jobId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!client) return;

    try {
      await client.cancelJob(jobId);
      await onRefresh();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  // Sort jobs by created_at (newest first)
  const sortedJobs = [...jobs].sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

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

      {error && (
        <div
          style={{
            padding: "12px 16px",
            backgroundColor: "#ef4444",
            borderRadius: "4px",
            marginBottom: "16px",
            color: "white",
          }}
        >
          {error}
        </div>
      )}

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
          No jobs yet. Click "Start Demo Job" to create one.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {sortedJobs.map((job: JobResponse) => (
            <div
              key={job.job_id}
              onClick={() => navigate(`/jobs/${job.job_id}`)}
              style={{
                padding: "16px",
                backgroundColor: "#2d2d44",
                borderRadius: "8px",
                cursor: "pointer",
                transition: "background-color 0.15s",
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
                </div>
                <div
                  style={{ display: "flex", alignItems: "center", gap: "8px" }}
                >
                  {/* Progress */}
                  {job.state === "running" && job.progress_percent != null && (
                    <span style={{ fontSize: "12px", color: "#9ca3af" }}>
                      {job.progress_percent}%
                    </span>
                  )}

                  {/* State Badge */}
                  <span
                    style={{
                      padding: "4px 8px",
                      borderRadius: "4px",
                      backgroundColor: STATE_COLORS[job.state],
                      color: "white",
                      fontSize: "11px",
                      fontWeight: 600,
                      textTransform: "uppercase",
                    }}
                  >
                    {job.state}
                  </span>

                  {/* Cancel Button */}
                  {(job.state === "queued" || job.state === "running") && (
                    <button
                      onClick={(e) => handleCancelJob(job.job_id, e)}
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

              {/* Error Message */}
              {job.error_message && (
                <div
                  style={{
                    marginTop: "8px",
                    padding: "8px",
                    backgroundColor: "#1a1a2e",
                    borderRadius: "4px",
                    fontSize: "12px",
                    color: "#ef4444",
                  }}
                >
                  {job.error_code}: {job.error_message}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
