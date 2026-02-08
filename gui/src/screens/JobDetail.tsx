/**
 * JobDetail screen - Shows job logs and receipt.
 */

import { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { LogViewer } from "../components/LogViewer";
import { ReceiptViewer } from "../components/ReceiptViewer";
import { useAppStore, selectJob, selectJobLogs } from "../store";
import type { JobResponse, JobState } from "../api/types";
import { ApiClient } from "../api/client";

interface JobDetailProps {
  client: ApiClient | null;
}

const STATE_COLORS: Record<JobState, string> = {
  queued: "var(--rl-text-dim)",
  running: "var(--rl-primary)",
  cancelling: "var(--rl-warning)",
  cancelled: "var(--rl-text-muted)",
  completed: "var(--rl-success)",
  failed: "var(--rl-error)",
  archived: "var(--rl-text-dim)",
};

export function JobDetail({ client }: JobDetailProps) {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  // Get job from store or fetch it
  const storeJob = useAppStore((state) =>
    jobId ? selectJob(state, jobId) : undefined,
  );
  const storeLogs = useAppStore((state) =>
    jobId ? selectJobLogs(state, jobId) : [],
  );

  const [job, setJob] = useState<JobResponse | null>(storeJob ?? null);
  const [loading, setLoading] = useState(!storeJob);
  const [error, setError] = useState<string | null>(null);

  // Fetch job if not in store
  const fetchJob = useCallback(async () => {
    if (!client || !jobId) return;

    setLoading(true);
    try {
      const data = await client.getJob(jobId);
      setJob(data);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [client, jobId]);

  useEffect(() => {
    if (!storeJob && client && jobId) {
      fetchJob();
    }
  }, [storeJob, client, jobId, fetchJob]);

  // Update from store when available
  useEffect(() => {
    if (storeJob) {
      setJob(storeJob);
    }
  }, [storeJob]);

  const handleCancel = async () => {
    if (!client || !jobId) return;

    try {
      await client.cancelJob(jobId);
      await fetchJob();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  if (!jobId) {
    return (
      <div style={{ padding: "24px" }}>
        <p>Invalid job ID</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ padding: "24px" }}>
        <p>Loading job...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "24px" }}>
        <div
          style={{
            padding: "16px",
            backgroundColor: "var(--rl-error)",
            borderRadius: "4px",
            color: "white",
            marginBottom: "16px",
          }}
        >
          Error: {error}
        </div>
        <button
          onClick={() => navigate("/jobs")}
          style={{
            padding: "8px 16px",
            borderRadius: "4px",
            border: "none",
            backgroundColor: "var(--rl-primary)",
            color: "white",
            cursor: "pointer",
          }}
        >
          Back to Jobs
        </button>
      </div>
    );
  }

  if (!job) {
    return (
      <div style={{ padding: "24px" }}>
        <p>Job not found</p>
        <button
          onClick={() => navigate("/jobs")}
          style={{
            marginTop: "16px",
            padding: "8px 16px",
            borderRadius: "4px",
            border: "none",
            backgroundColor: "var(--rl-primary)",
            color: "white",
            cursor: "pointer",
          }}
        >
          Back to Jobs
        </button>
      </div>
    );
  }

  const formatDate = (dateStr: string | undefined) => {
    if (!dateStr) return "N/A";
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  return (
    <div style={{ padding: "24px" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: "24px",
        }}
      >
        <div>
          <button
            onClick={() => navigate("/jobs")}
            style={{
              padding: "4px 12px",
              borderRadius: "4px",
              border: "1px solid #4a4a6a",
              backgroundColor: "transparent",
              color: "var(--rl-text-muted)",
              cursor: "pointer",
              fontSize: "var(--rl-fs-sm)",
              marginBottom: "8px",
            }}
          >
            &larr; Back to Jobs
          </button>
          <h1
            style={{
              fontSize: "var(--rl-fs-lg)",
              fontWeight: 600,
              margin: 0,
              fontFamily: "var(--rl-font-mono)",
            }}
          >
            {job.job_id}
          </h1>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span
            style={{
              padding: "4px 12px",
              borderRadius: "4px",
              backgroundColor: STATE_COLORS[job.state],
              color: "white",
              fontSize: "var(--rl-fs-sm)",
              fontWeight: 600,
              textTransform: "uppercase",
            }}
          >
            {job.state}
          </span>

          {(job.state === "queued" || job.state === "running") && (
            <button
              onClick={handleCancel}
              style={{
                padding: "4px 12px",
                borderRadius: "4px",
                border: "1px solid var(--rl-error)",
                backgroundColor: "transparent",
                color: "var(--rl-error)",
                cursor: "pointer",
                fontSize: "var(--rl-fs-sm)",
              }}
            >
              Cancel Job
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar (if running) */}
      {job.state === "running" && (
        <div style={{ marginBottom: "24px" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: "4px",
              fontSize: "var(--rl-fs-sm)",
              color: "var(--rl-text-muted)",
            }}
          >
            <span>{job.progress_phase ?? "Processing"}</span>
            <span>{job.progress_percent ?? 0}%</span>
          </div>
          <div
            style={{
              height: "8px",
              backgroundColor: "var(--rl-bg-card)",
              borderRadius: "4px",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${job.progress_percent ?? 0}%`,
                backgroundColor: "var(--rl-primary)",
                transition: "width 0.3s",
              }}
            />
          </div>
        </div>
      )}

      {/* Job Info */}
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
            display: "grid",
            gridTemplateColumns: "auto 1fr auto 1fr",
            gap: "8px 16px",
            fontSize: "var(--rl-fs-base)",
          }}
        >
          <span style={{ color: "var(--rl-text-muted)" }}>Created:</span>
          <span>{formatDate(job.created_at)}</span>

          <span style={{ color: "var(--rl-text-muted)" }}>Started:</span>
          <span>{formatDate(job.started_at)}</span>

          <span style={{ color: "var(--rl-text-muted)" }}>Completed:</span>
          <span>{formatDate(job.completed_at)}</span>

          <span style={{ color: "var(--rl-text-muted)" }}>Style:</span>
          <span>{job.config.style}</span>
        </div>

        {job.error_message && (
          <div
            style={{
              marginTop: "12px",
              padding: "8px 12px",
              backgroundColor: "var(--rl-bg-app)",
              borderRadius: "4px",
              borderLeft: "3px solid var(--rl-error)",
            }}
          >
            <div
              style={{ color: "var(--rl-error)", fontSize: "var(--rl-fs-sm)", fontWeight: 600 }}
            >
              {job.error_code}
            </div>
            <div
              style={{ color: "var(--rl-text)", fontSize: "var(--rl-fs-base)", marginTop: "4px" }}
            >
              {job.error_message}
            </div>
          </div>
        )}
      </div>

      {/* Logs Section */}
      <div style={{ marginBottom: "24px" }}>
        <h2
          style={{
            fontSize: "var(--rl-fs-md)",
            fontWeight: 600,
            marginBottom: "12px",
          }}
        >
          Logs
        </h2>
        <LogViewer logs={storeLogs} maxHeight="300px" />
      </div>

      {/* Receipt Section */}
      <div>
        <h2
          style={{
            fontSize: "var(--rl-fs-md)",
            fontWeight: 600,
            marginBottom: "12px",
          }}
        >
          Receipt
        </h2>
        <ReceiptViewer
          jobId={job.job_id}
          jobState={job.state}
          client={client}
        />
      </div>
    </div>
  );
}
