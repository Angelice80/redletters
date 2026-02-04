/**
 * ExportView - Export workflow screen with wizard and scholarly run.
 *
 * Sprint v0.19.0: Jobs-native GUI
 * - Async job flow with immediate job_id return
 * - Live progress via SSE subscription
 * - Cancel support with cancel_requested state
 * - Gate-blocked as terminal non-error state
 *
 * Sprint v0.14.0: Task-shaped export interface with:
 * - Export Wizard (detect gates, acknowledge, choose type)
 * - Scholarly Run button triggering full workflow
 * - Gate enforcement matching backend rules
 */

import { useState, useCallback, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAppStore, selectSettings } from "../store";
import type { ApiClient } from "../api/client";
import type {
  ApiErrorDetail,
  JobUIState,
  SSEEvent,
  JobProgress,
  JobStateChanged,
  ScholarlyJobResult,
} from "../api/types";
import {
  ApiErrorPanel,
  createApiErrorDetail,
} from "../components/ApiErrorPanel";
import { JobProgressModal } from "../components/JobProgressModal";
import { useJobEvents } from "../api/sse";

interface ExportViewProps {
  client: ApiClient | null;
}

// Export types
type ExportType = "quote" | "apparatus" | "snapshot" | "bundle";

interface GateInfo {
  ref: string;
  significance: string;
  message: string;
}

interface ExportWizardState {
  step: "reference" | "gates" | "acknowledge" | "export";
  reference: string;
  pendingGates: GateInfo[];
  forceSelected: boolean;
  forceReason: string;
  exportType: ExportType;
}

// Styles
const containerStyle: React.CSSProperties = {
  padding: "24px",
  maxWidth: "900px",
};

const headerStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 600,
  marginBottom: "8px",
  color: "#eaeaea",
};

const subHeaderStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#9ca3af",
  marginBottom: "24px",
};

const sectionStyle: React.CSSProperties = {
  backgroundColor: "#2d2d44",
  borderRadius: "8px",
  padding: "20px",
  marginBottom: "16px",
};

const sectionHeaderStyle: React.CSSProperties = {
  fontSize: "16px",
  fontWeight: 600,
  color: "#eaeaea",
  marginBottom: "16px",
};

const inputGroupStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "4px",
  marginBottom: "16px",
};

const labelStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#9ca3af",
  textTransform: "uppercase",
};

const inputStyle: React.CSSProperties = {
  padding: "12px 14px",
  fontSize: "16px",
  backgroundColor: "#1a1a2e",
  border: "1px solid #4b5563",
  borderRadius: "4px",
  color: "#eaeaea",
  width: "100%",
  maxWidth: "400px",
};

const selectStyle: React.CSSProperties = {
  ...inputStyle,
  cursor: "pointer",
};

const buttonStyle: React.CSSProperties = {
  padding: "12px 24px",
  fontSize: "14px",
  fontWeight: 500,
  backgroundColor: "#3b82f6",
  color: "white",
  border: "none",
  borderRadius: "4px",
  cursor: "pointer",
};

const primaryButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "#22c55e",
};

const secondaryButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "#4b5563",
};

const disabledButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "#374151",
  cursor: "not-allowed",
};

const dangerButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "#ef4444",
};

const stepIndicatorStyle: React.CSSProperties = {
  display: "flex",
  gap: "8px",
  marginBottom: "24px",
};

const stepDotStyle: React.CSSProperties = {
  width: "32px",
  height: "32px",
  borderRadius: "50%",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontSize: "14px",
  fontWeight: 600,
};

const stepActiveStyle: React.CSSProperties = {
  ...stepDotStyle,
  backgroundColor: "#3b82f6",
  color: "white",
};

const stepCompleteStyle: React.CSSProperties = {
  ...stepDotStyle,
  backgroundColor: "#22c55e",
  color: "white",
};

const stepInactiveStyle: React.CSSProperties = {
  ...stepDotStyle,
  backgroundColor: "#4b5563",
  color: "#9ca3af",
};

const gateCardStyle: React.CSSProperties = {
  backgroundColor: "#1a1a2e",
  borderRadius: "6px",
  padding: "12px 16px",
  marginBottom: "8px",
  border: "1px solid #f59e0b",
};

const checkboxContainerStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "10px",
  padding: "12px",
  backgroundColor: "#1a1a2e",
  borderRadius: "6px",
  marginTop: "16px",
};

function StepIndicator({
  currentStep,
  steps,
}: {
  currentStep: number;
  steps: string[];
}) {
  return (
    <div style={stepIndicatorStyle}>
      {steps.map((step, index) => (
        <div key={step} style={{ display: "flex", alignItems: "center" }}>
          <div
            style={
              index < currentStep
                ? stepCompleteStyle
                : index === currentStep
                  ? stepActiveStyle
                  : stepInactiveStyle
            }
          >
            {index < currentStep ? "✓" : index + 1}
          </div>
          {index < steps.length - 1 && (
            <div
              style={{
                width: "40px",
                height: "2px",
                backgroundColor: index < currentStep ? "#22c55e" : "#4b5563",
                marginLeft: "8px",
              }}
            />
          )}
        </div>
      ))}
    </div>
  );
}

const STEPS = ["Reference", "Gates", "Acknowledge", "Export"];

export function ExportView({ client }: ExportViewProps) {
  const navigate = useNavigate();
  const settings = useAppStore(selectSettings);

  const [wizard, setWizard] = useState<ExportWizardState>({
    step: "reference",
    reference: "",
    pendingGates: [],
    forceSelected: false,
    forceReason: "",
    exportType: "bundle",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiErrorDetail | null>(null);
  const [mode, setMode] = useState<"readable" | "traceable">("traceable");

  // Sprint 19: Job UI state for async job flow
  const [jobState, setJobState] = useState<JobUIState>({ status: "idle" });
  const [showModal, setShowModal] = useState(false);

  // Get current job ID if running
  const currentJobId =
    jobState.status !== "idle" && "jobId" in jobState ? jobState.jobId : null;

  // Sprint 19: SSE subscription for job events
  const handleJobEvent = useCallback(
    (event: SSEEvent) => {
      if (!currentJobId) return;

      switch (event.event_type) {
        case "job.progress": {
          const progressEvent = event as JobProgress;
          if (progressEvent.job_id === currentJobId) {
            setJobState({
              status: "streaming",
              jobId: currentJobId,
              stage: progressEvent.phase,
              percent: progressEvent.progress_percent ?? 0,
              message: progressEvent.phase,
            });
          }
          break;
        }
        case "job.state_changed": {
          const stateEvent = event as JobStateChanged;
          if (stateEvent.job_id !== currentJobId) return;

          // Handle terminal states
          if (stateEvent.new_state === "completed") {
            // Fetch job to get result
            fetchJobResult(currentJobId);
          } else if (stateEvent.new_state === "cancelled") {
            setJobState({ status: "canceled", jobId: currentJobId });
          } else if (stateEvent.new_state === "failed") {
            setJobState({
              status: "completed_failed",
              jobId: currentJobId,
              errors: ["Job failed - check job details for more info"],
            });
          } else if (stateEvent.new_state === "cancelling") {
            setJobState({ status: "cancel_requested", jobId: currentJobId });
          }
          break;
        }
      }
    },
    [currentJobId],
  );

  // SSE subscription hook - only active when we have a job
  useJobEvents(
    client?.baseUrl ?? "",
    client?.token ?? "",
    currentJobId,
    handleJobEvent,
    !!currentJobId &&
      jobState.status !== "completed_success" &&
      jobState.status !== "completed_gate_blocked" &&
      jobState.status !== "completed_failed" &&
      jobState.status !== "canceled",
  );

  // Fetch job result on completion
  const fetchJobResult = useCallback(
    async (jobId: string) => {
      if (!client) return;

      try {
        const job = await client.getJob(jobId);
        const result = job.result as ScholarlyJobResult | undefined;

        if (result?.gate_blocked) {
          setJobState({
            status: "completed_gate_blocked",
            jobId,
            pendingGates: result.pending_gates ?? [],
          });
        } else if (result?.success) {
          setJobState({
            status: "completed_success",
            jobId,
            result,
          });
        } else {
          setJobState({
            status: "completed_failed",
            jobId,
            errors: result?.errors ?? ["Unknown error"],
          });
        }
      } catch (err) {
        setJobState({
          status: "completed_failed",
          jobId,
          errors: [(err as Error).message],
        });
      }
    },
    [client],
  );

  // Step 1: Check gates for reference
  const handleCheckGates = useCallback(async () => {
    if (!client || !wizard.reference.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await client.getPendingGates(
        wizard.reference.trim(),
        settings.sessionId,
      );

      if (response.pending_gates.length > 0) {
        const gates: GateInfo[] = response.pending_gates.map((gate) => ({
          ref: gate.ref,
          significance: gate.significance,
          message: gate.message,
        }));

        setWizard((prev) => ({
          ...prev,
          step: "gates",
          pendingGates: gates,
        }));
      } else {
        setWizard((prev) => ({
          ...prev,
          step: "export",
          pendingGates: [],
        }));
      }
    } catch (err) {
      const diagnosticsUrl = client.contract
        ? `${client.baseUrl}${client.contract.gatesPending()}`
        : "/v1/gates/pending";
      const contractDiags = client.getContractDiagnostics?.()
        ? client.getContractDiagnostics()
        : undefined;
      setError(createApiErrorDetail("GET", diagnosticsUrl, err, contractDiags));
    } finally {
      setLoading(false);
    }
  }, [client, wizard.reference, settings.sessionId]);

  // Step 2: Handle force option
  const handleForceToggle = useCallback((checked: boolean) => {
    setWizard((prev) => ({
      ...prev,
      forceSelected: checked,
    }));
  }, []);

  const handleProceedWithForce = useCallback(() => {
    setWizard((prev) => ({
      ...prev,
      step: "export",
    }));
  }, []);

  const handleGoToAcknowledge = useCallback(() => {
    setWizard((prev) => ({
      ...prev,
      step: "acknowledge",
    }));
  }, []);

  // Step 3: Navigate to gate acknowledgement
  const handleAcknowledgeGates = useCallback(() => {
    navigate("/gate", {
      state: {
        gate: {
          response_type: "gate",
          gate_id: "export-wizard",
          gate_type: "variant",
          title: "Variants Require Acknowledgement",
          message: `${wizard.pendingGates.length} variant(s) need acknowledgement before export`,
          prompt: "Review and acknowledge each variant to proceed",
          required_acks: wizard.pendingGates.map((g) => ({
            variant_ref: g.ref,
            significance: g.significance,
            message: g.message,
          })),
          variants_side_by_side: [],
          reference: wizard.reference,
          verse_ids: [],
          session_id: settings.sessionId,
        },
        originalReference: wizard.reference,
      },
    });
  }, [navigate, wizard.pendingGates, wizard.reference, settings.sessionId]);

  // Sprint 19: Run scholarly export as async job
  const handleScholarlyRun = useCallback(async () => {
    if (!client) return;

    setLoading(true);
    setError(null);

    try {
      // Enqueue job - returns immediately with job_id
      const response = await client.runScholarly({
        reference: wizard.reference.trim(),
        mode,
        force: wizard.forceSelected,
        session_id: settings.sessionId,
        include_schemas: true,
        create_zip: wizard.exportType === "bundle",
      });

      // Set enqueued state and show modal
      setJobState({
        status: "enqueued",
        jobId: response.job_id,
      });
      setShowModal(true);
    } catch (err) {
      const diagnosticsUrl = client.contract
        ? `${client.baseUrl}${client.contract.runScholarly()}`
        : "/v1/run/scholarly";
      const contractDiags = client.getContractDiagnostics?.()
        ? client.getContractDiagnostics()
        : undefined;
      setError(
        createApiErrorDetail("POST", diagnosticsUrl, err, contractDiags),
      );
    } finally {
      setLoading(false);
    }
  }, [
    client,
    wizard.reference,
    wizard.forceSelected,
    wizard.exportType,
    mode,
    settings,
  ]);

  // Sprint 19: Cancel job
  const handleCancelJob = useCallback(async () => {
    if (!client || !currentJobId) return;

    // Immediately show cancel_requested state
    setJobState({ status: "cancel_requested", jobId: currentJobId });

    try {
      await client.cancelJob(currentJobId);
      // State will be updated via SSE event
    } catch (err) {
      // Revert to streaming state on error
      setJobState((prev) =>
        prev.status === "cancel_requested" && "jobId" in prev
          ? {
              status: "streaming",
              jobId: prev.jobId,
              stage: "",
              percent: 0,
              message: "",
            }
          : prev,
      );
    }
  }, [client, currentJobId]);

  // Sprint 19: Close modal and reset state
  const handleCloseModal = useCallback(() => {
    setShowModal(false);
    // Reset job state after a brief delay to allow closing animation
    setTimeout(() => {
      setJobState({ status: "idle" });
    }, 200);
  }, []);

  // Sprint 19: Navigate to jobs screen
  const handleViewInJobs = useCallback(() => {
    handleCloseModal();
    navigate("/jobs");
  }, [handleCloseModal, navigate]);

  // Sprint 20: Navigate to receipt view (job detail page)
  const handleViewReceipt = useCallback(() => {
    handleCloseModal();
    if (currentJobId) {
      navigate(`/jobs/${currentJobId}`);
    }
  }, [handleCloseModal, navigate, currentJobId]);

  // Sprint 19: Navigate to resolve gates
  const handleResolveGates = useCallback(() => {
    handleCloseModal();
    if (jobState.status === "completed_gate_blocked") {
      // Update wizard state with pending gates
      setWizard((prev) => ({
        ...prev,
        step: "gates",
        pendingGates: jobState.pendingGates.map((ref) => ({
          ref,
          significance: "significant",
          message: "Pending acknowledgement",
        })),
      }));
    }
  }, [handleCloseModal, jobState]);

  const handleReset = useCallback(() => {
    setWizard({
      step: "reference",
      reference: "",
      pendingGates: [],
      forceSelected: false,
      forceReason: "",
      exportType: "bundle",
    });
    setError(null);
    setJobState({ status: "idle" });
    setShowModal(false);
  }, []);

  const currentStepIndex =
    wizard.step === "reference"
      ? 0
      : wizard.step === "gates"
        ? 1
        : wizard.step === "acknowledge"
          ? 2
          : 3;

  if (!client) {
    return (
      <div style={containerStyle}>
        <h1 style={headerStyle}>Export</h1>
        <div style={{ color: "#9ca3af" }}>
          Not connected to backend.{" "}
          <Link to="/settings" style={{ color: "#60a5fa" }}>
            Check connection settings
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <h1 style={headerStyle}>Export</h1>
      <div style={subHeaderStyle}>
        Create verified scholarly exports with full provenance and gate
        enforcement.
      </div>

      {/* Step Indicator */}
      <StepIndicator currentStep={currentStepIndex} steps={STEPS} />

      {/* Error display */}
      {error && (
        <ApiErrorPanel
          error={error}
          onRetry={handleCheckGates}
          onDismiss={() => setError(null)}
        />
      )}

      {/* Step 1: Reference Input */}
      {wizard.step === "reference" && (
        <div style={sectionStyle}>
          <div style={sectionHeaderStyle}>Step 1: Enter Reference</div>

          <div style={inputGroupStyle}>
            <label style={labelStyle}>Scripture Reference</label>
            <input
              type="text"
              style={inputStyle}
              placeholder="e.g., John 1:1-18 or Matthew 5:3-12"
              value={wizard.reference}
              onChange={(e) =>
                setWizard((prev) => ({ ...prev, reference: e.target.value }))
              }
              data-testid="export-reference"
            />
          </div>

          <div style={inputGroupStyle}>
            <label style={labelStyle}>Mode</label>
            <select
              style={selectStyle}
              value={mode}
              onChange={(e) =>
                setMode(e.target.value as "readable" | "traceable")
              }
              data-testid="export-mode"
            >
              <option value="traceable">Traceable (full evidence)</option>
              <option value="readable">Readable (flowing text)</option>
            </select>
          </div>

          <div style={inputGroupStyle}>
            <label style={labelStyle}>Export Type</label>
            <select
              style={selectStyle}
              value={wizard.exportType}
              onChange={(e) =>
                setWizard((prev) => ({
                  ...prev,
                  exportType: e.target.value as ExportType,
                }))
              }
            >
              <option value="bundle">Complete Bundle (recommended)</option>
              <option value="quote">Quote Only</option>
              <option value="apparatus">Apparatus Only</option>
              <option value="snapshot">Snapshot</option>
            </select>
          </div>

          <button
            style={
              loading || !wizard.reference.trim()
                ? disabledButtonStyle
                : buttonStyle
            }
            onClick={handleCheckGates}
            disabled={loading || !wizard.reference.trim()}
            data-testid="export-check-gates"
          >
            {loading ? "Checking..." : "Check Gates & Continue"}
          </button>
        </div>
      )}

      {/* Step 2: Gates Detected */}
      {wizard.step === "gates" && (
        <div style={sectionStyle}>
          <div style={sectionHeaderStyle}>
            Step 2: Gates Detected ({wizard.pendingGates.length})
          </div>

          <div style={{ marginBottom: "16px", color: "#f59e0b" }}>
            The following textual variants require acknowledgement before
            export:
          </div>

          {wizard.pendingGates.map((gate) => (
            <div key={gate.ref} style={gateCardStyle}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span style={{ color: "#60a5fa", fontWeight: 500 }}>
                  {gate.ref}
                </span>
                <span
                  style={{
                    fontSize: "11px",
                    padding: "2px 8px",
                    borderRadius: "4px",
                    backgroundColor:
                      gate.significance === "major" ? "#ef4444" : "#f59e0b",
                    color: "white",
                  }}
                >
                  {gate.significance}
                </span>
              </div>
              <div
                style={{ color: "#9ca3af", fontSize: "13px", marginTop: "4px" }}
              >
                {gate.message}
              </div>
            </div>
          ))}

          <div style={{ display: "flex", gap: "12px", marginTop: "20px" }}>
            <button style={primaryButtonStyle} onClick={handleGoToAcknowledge}>
              Acknowledge Variants
            </button>
            <button
              style={dangerButtonStyle}
              onClick={() => handleForceToggle(true)}
            >
              Force Export (Not Recommended)
            </button>
          </div>

          {wizard.forceSelected && (
            <div style={checkboxContainerStyle}>
              <input
                type="checkbox"
                id="force-confirm"
                checked={wizard.forceSelected}
                onChange={(e) => handleForceToggle(e.target.checked)}
                style={{ width: "18px", height: "18px" }}
              />
              <label
                htmlFor="force-confirm"
                style={{ color: "#ef4444", fontSize: "14px" }}
              >
                I understand this export will include unacknowledged variants
                and my responsibility will be recorded in the run log.
              </label>
              <button
                style={dangerButtonStyle}
                onClick={handleProceedWithForce}
              >
                Proceed Anyway
              </button>
            </div>
          )}
        </div>
      )}

      {/* Step 3: Acknowledge */}
      {wizard.step === "acknowledge" && (
        <div style={sectionStyle}>
          <div style={sectionHeaderStyle}>Step 3: Acknowledge Variants</div>

          <div style={{ marginBottom: "16px", color: "#9ca3af" }}>
            Review each variant and select your preferred reading before
            proceeding.
          </div>

          <button style={primaryButtonStyle} onClick={handleAcknowledgeGates}>
            Open Acknowledgement Screen
          </button>

          <div
            style={{ marginTop: "16px", color: "#6b7280", fontSize: "13px" }}
          >
            After acknowledging, return here and click "Re-check Gates" to
            continue.
          </div>

          <button
            style={{ ...secondaryButtonStyle, marginTop: "12px" }}
            onClick={handleCheckGates}
            disabled={loading}
          >
            {loading ? "Checking..." : "Re-check Gates"}
          </button>
        </div>
      )}

      {/* Step 4: Export */}
      {wizard.step === "export" && (
        <div style={sectionStyle}>
          <div style={sectionHeaderStyle}>Step 4: Run Scholarly Export</div>

          <div style={{ marginBottom: "16px" }}>
            <div style={{ color: "#9ca3af", marginBottom: "8px" }}>
              Reference:{" "}
              <span style={{ color: "#eaeaea" }}>{wizard.reference}</span>
            </div>
            <div style={{ color: "#9ca3af", marginBottom: "8px" }}>
              Mode: <span style={{ color: "#eaeaea" }}>{mode}</span>
            </div>
            <div style={{ color: "#9ca3af", marginBottom: "8px" }}>
              Export Type:{" "}
              <span style={{ color: "#eaeaea" }}>{wizard.exportType}</span>
            </div>
            <div style={{ color: "#9ca3af" }}>
              Gates:{" "}
              <span style={{ color: "#22c55e" }}>
                {wizard.pendingGates.length === 0
                  ? "All clear"
                  : wizard.forceSelected
                    ? `${wizard.pendingGates.length} bypassed (forced)`
                    : `${wizard.pendingGates.length} pending`}
              </span>
            </div>
          </div>

          <div style={{ display: "flex", gap: "12px" }}>
            <button
              style={loading ? disabledButtonStyle : primaryButtonStyle}
              onClick={handleScholarlyRun}
              disabled={loading}
              data-testid="export-run"
            >
              {loading ? "Starting..." : "Run Scholarly Export"}
            </button>
            <button style={secondaryButtonStyle} onClick={handleReset}>
              Start Over
            </button>
          </div>

          <div
            style={{ marginTop: "16px", color: "#6b7280", fontSize: "13px" }}
          >
            This will generate: lockfile, apparatus, translation, citations,
            quote, snapshot, verified bundle, and run_log.json
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div style={{ ...sectionStyle, backgroundColor: "#1a1a2e" }}>
        <div style={{ ...sectionHeaderStyle, fontSize: "14px" }}>
          Quick Actions
        </div>
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <Link to="/explore">
            <button style={secondaryButtonStyle}>Explore Passage</button>
          </Link>
          <Link to="/sources">
            <button style={secondaryButtonStyle}>Manage Sources</button>
          </Link>
          <Link to="/jobs">
            <button style={secondaryButtonStyle}>View Jobs</button>
          </Link>
        </div>
      </div>

      {/* Sprint 19: Job Progress Modal */}
      {showModal && (
        <JobProgressModal
          state={jobState}
          onCancel={handleCancelJob}
          onClose={handleCloseModal}
          onViewInJobs={handleViewInJobs}
          onViewReceipt={handleViewReceipt}
          onResolveGates={handleResolveGates}
        />
      )}
    </div>
  );
}
