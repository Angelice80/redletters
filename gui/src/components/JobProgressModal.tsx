/**
 * JobProgressModal - Progress modal for async scholarly runs.
 *
 * Sprint 19: Jobs-native GUI
 *
 * Features:
 * - Stage list showing progress through scholarly workflow
 * - Progress bar with percent
 * - Current stage message
 * - Cancel button with "Cancel requested..." state
 * - Terminal state display (success, gate_blocked, failed, canceled)
 */

import { useCallback } from "react";
import type { JobUIState, ScholarlyJobResult } from "../api/types";

interface JobProgressModalProps {
  state: JobUIState;
  onCancel: () => void;
  onClose: () => void;
  onViewInJobs?: () => void;
  onViewReceipt?: () => void;
  onResolveGates?: () => void;
}

// Scholarly workflow stages
const STAGES = [
  { id: "init", label: "Initializing" },
  { id: "lockfile", label: "Generating lockfile" },
  { id: "gates", label: "Checking gates" },
  { id: "translate", label: "Running translation" },
  { id: "apparatus", label: "Exporting apparatus" },
  { id: "translation", label: "Exporting translation" },
  { id: "citations", label: "Exporting citations" },
  { id: "quote", label: "Exporting quote" },
  { id: "snapshot", label: "Creating snapshot" },
  { id: "bundle", label: "Building bundle" },
];

// Map backend phases to stage indices
function getStageIndex(phase: string): number {
  const phaseMap: Record<string, number> = {
    init: 0,
    initializing: 0,
    lockfile: 1,
    "generating lockfile": 1,
    gates: 2,
    "checking gates": 2,
    translate: 3,
    translation: 3,
    "running translation": 3,
    apparatus: 4,
    "exporting apparatus": 4,
    "export translation": 5,
    "exporting translation": 5,
    citations: 6,
    "exporting citations": 6,
    quote: 7,
    "exporting quote": 7,
    snapshot: 8,
    "creating snapshot": 8,
    bundle: 9,
    "building bundle": 9,
    finalizing: 9,
    complete: 9,
  };

  const normalized = phase.toLowerCase().trim();
  return phaseMap[normalized] ?? 0;
}

// Styles
const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  backgroundColor: "rgba(0, 0, 0, 0.6)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
};

const modalStyle: React.CSSProperties = {
  backgroundColor: "#2d2d44",
  borderRadius: "12px",
  padding: "24px",
  width: "480px",
  maxWidth: "90vw",
  maxHeight: "90vh",
  overflow: "auto",
  boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)",
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "20px",
};

const titleStyle: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 600,
  color: "#eaeaea",
};

const closeButtonStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  color: "#6b7280",
  cursor: "pointer",
  fontSize: "24px",
  padding: 0,
  lineHeight: 1,
};

const progressBarContainerStyle: React.CSSProperties = {
  marginBottom: "16px",
};

const progressBarStyle: React.CSSProperties = {
  height: "8px",
  backgroundColor: "#1a1a2e",
  borderRadius: "4px",
  overflow: "hidden",
};

const progressFillStyle: React.CSSProperties = {
  height: "100%",
  backgroundColor: "#3b82f6",
  transition: "width 0.3s ease",
};

const percentLabelStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  fontSize: "12px",
  color: "#9ca3af",
  marginTop: "4px",
};

const stageListStyle: React.CSSProperties = {
  marginBottom: "20px",
};

const stageItemStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "10px",
  padding: "8px 0",
  borderBottom: "1px solid #374151",
  fontSize: "13px",
};

const stageDotStyle: React.CSSProperties = {
  width: "10px",
  height: "10px",
  borderRadius: "50%",
  flexShrink: 0,
};

const messageBoxStyle: React.CSSProperties = {
  padding: "12px",
  backgroundColor: "#1a1a2e",
  borderRadius: "6px",
  marginBottom: "20px",
  fontSize: "13px",
  color: "#9ca3af",
};

const buttonRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "12px",
  justifyContent: "flex-end",
};

const buttonStyle: React.CSSProperties = {
  padding: "10px 20px",
  borderRadius: "6px",
  border: "none",
  cursor: "pointer",
  fontSize: "13px",
  fontWeight: 500,
};

const cancelButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "#ef4444",
  color: "white",
};

const cancelRequestedStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "#f59e0b",
  color: "white",
  cursor: "wait",
};

const primaryButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "#3b82f6",
  color: "white",
};

const secondaryButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "#4b5563",
  color: "white",
};

const successBoxStyle: React.CSSProperties = {
  padding: "16px",
  backgroundColor: "#14532d",
  borderRadius: "8px",
  marginBottom: "20px",
};

const gateBlockedBoxStyle: React.CSSProperties = {
  padding: "16px",
  backgroundColor: "#78350f",
  borderRadius: "8px",
  marginBottom: "20px",
};

const errorBoxStyle: React.CSSProperties = {
  padding: "16px",
  backgroundColor: "#7f1d1d",
  borderRadius: "8px",
  marginBottom: "20px",
};

const codeStyle: React.CSSProperties = {
  fontFamily: "monospace",
  backgroundColor: "#374151",
  padding: "2px 6px",
  borderRadius: "3px",
  fontSize: "11px",
};

function StageList({
  currentStage,
  percent,
}: {
  currentStage: number;
  percent: number;
}) {
  return (
    <div style={stageListStyle}>
      {STAGES.map((stage, index) => {
        const isComplete = index < currentStage;
        const isCurrent = index === currentStage;
        const isPending = index > currentStage;

        return (
          <div key={stage.id} style={stageItemStyle}>
            <div
              style={{
                ...stageDotStyle,
                backgroundColor: isComplete
                  ? "#22c55e"
                  : isCurrent
                    ? "#3b82f6"
                    : "#4b5563",
              }}
            />
            <span
              style={{
                color: isComplete
                  ? "#22c55e"
                  : isCurrent
                    ? "#eaeaea"
                    : "#6b7280",
                fontWeight: isCurrent ? 500 : 400,
              }}
            >
              {stage.label}
            </span>
            {isCurrent && (
              <span
                style={{
                  marginLeft: "auto",
                  color: "#3b82f6",
                  fontSize: "11px",
                }}
              >
                {percent}%
              </span>
            )}
            {isComplete && (
              <span
                style={{
                  marginLeft: "auto",
                  color: "#22c55e",
                  fontSize: "11px",
                }}
              >
                Done
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function SuccessResult({
  result,
  onViewInJobs,
  onViewReceipt,
  onClose,
}: {
  result: ScholarlyJobResult;
  onViewInJobs?: () => void;
  onViewReceipt?: () => void;
  onClose: () => void;
}) {
  return (
    <>
      <div style={successBoxStyle}>
        <div style={{ color: "#86efac", fontWeight: 600, marginBottom: "8px" }}>
          Scholarly Run Complete
        </div>
        {result.output_dir && (
          <div
            style={{ color: "#d1fae5", fontSize: "13px", marginBottom: "4px" }}
          >
            Output: <code style={codeStyle}>{result.output_dir}</code>
          </div>
        )}
        {result.bundle_path && (
          <div style={{ color: "#d1fae5", fontSize: "13px" }}>
            Bundle: <code style={codeStyle}>{result.bundle_path}</code>
          </div>
        )}
        {result.run_log_summary && (
          <div style={{ color: "#9ca3af", fontSize: "12px", marginTop: "8px" }}>
            {result.run_log_summary.verse_count} verses,{" "}
            {result.run_log_summary.file_count} files
          </div>
        )}
      </div>
      <div style={buttonRowStyle}>
        {onViewReceipt && (
          <button style={primaryButtonStyle} onClick={onViewReceipt}>
            View Receipt
          </button>
        )}
        {onViewInJobs && (
          <button style={secondaryButtonStyle} onClick={onViewInJobs}>
            View in Jobs
          </button>
        )}
        <button style={secondaryButtonStyle} onClick={onClose}>
          Close
        </button>
      </div>
    </>
  );
}

function GateBlockedResult({
  pendingGates,
  onResolveGates,
  onClose,
}: {
  pendingGates: string[];
  onResolveGates?: () => void;
  onClose: () => void;
}) {
  return (
    <>
      <div style={gateBlockedBoxStyle}>
        <div style={{ color: "#fcd34d", fontWeight: 600, marginBottom: "8px" }}>
          Gates Pending
        </div>
        <div
          style={{ color: "#fef3c7", fontSize: "13px", marginBottom: "12px" }}
        >
          {pendingGates.length} variant(s) require acknowledgement before export
          can proceed.
        </div>
        <div style={{ maxHeight: "120px", overflow: "auto" }}>
          {pendingGates.map((gate) => (
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
      <div style={buttonRowStyle}>
        {onResolveGates && (
          <button style={primaryButtonStyle} onClick={onResolveGates}>
            Resolve Gates
          </button>
        )}
        <button style={secondaryButtonStyle} onClick={onClose}>
          Close
        </button>
      </div>
    </>
  );
}

function FailedResult({
  errors,
  onClose,
}: {
  errors: string[];
  onClose: () => void;
}) {
  return (
    <>
      <div style={errorBoxStyle}>
        <div style={{ color: "#fca5a5", fontWeight: 600, marginBottom: "8px" }}>
          Export Failed
        </div>
        <div style={{ color: "#fecaca", fontSize: "13px" }}>
          {errors.length > 0 ? (
            <ul style={{ margin: 0, paddingLeft: "20px" }}>
              {errors.map((err, i) => (
                <li key={i} style={{ marginBottom: "4px" }}>
                  {err}
                </li>
              ))}
            </ul>
          ) : (
            "An unknown error occurred."
          )}
        </div>
      </div>
      <div style={buttonRowStyle}>
        <button style={secondaryButtonStyle} onClick={onClose}>
          Close
        </button>
      </div>
    </>
  );
}

export function JobProgressModal({
  state,
  onCancel,
  onClose,
  onViewInJobs,
  onViewReceipt,
  onResolveGates,
}: JobProgressModalProps) {
  // Don't show modal for idle state
  if (state.status === "idle") {
    return null;
  }

  const isTerminal = [
    "completed_success",
    "completed_gate_blocked",
    "completed_failed",
    "canceled",
  ].includes(state.status);

  const canCancel = state.status === "enqueued" || state.status === "streaming";
  const isCancelRequested = state.status === "cancel_requested";

  // Get current stage and percent
  let currentStage = 0;
  let percent = 0;
  let message = "";

  if (state.status === "enqueued") {
    message = "Job queued, waiting to start...";
  } else if (state.status === "streaming") {
    currentStage = getStageIndex(state.stage);
    percent = state.percent;
    message = state.message || state.stage;
  } else if (state.status === "cancel_requested") {
    message = "Cancel requested, waiting for confirmation...";
  } else if (state.status === "canceled") {
    message = "Job was cancelled.";
  }

  const getTitle = (): string => {
    switch (state.status) {
      case "enqueued":
      case "streaming":
        return "Running Scholarly Export...";
      case "cancel_requested":
        return "Cancelling...";
      case "completed_success":
        return "Export Complete";
      case "completed_gate_blocked":
        return "Gates Pending";
      case "completed_failed":
        return "Export Failed";
      case "canceled":
        return "Export Cancelled";
      default:
        return "Scholarly Export";
    }
  };

  return (
    <div style={overlayStyle} onClick={isTerminal ? onClose : undefined}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={headerStyle}>
          <span style={titleStyle}>{getTitle()}</span>
          {isTerminal && (
            <button style={closeButtonStyle} onClick={onClose}>
              &times;
            </button>
          )}
        </div>

        {/* Progress view for active states */}
        {(state.status === "enqueued" ||
          state.status === "streaming" ||
          state.status === "cancel_requested") && (
          <>
            {/* Progress bar */}
            <div style={progressBarContainerStyle}>
              <div style={progressBarStyle}>
                <div
                  style={{
                    ...progressFillStyle,
                    width: `${percent}%`,
                    backgroundColor:
                      state.status === "cancel_requested"
                        ? "#f59e0b"
                        : "#3b82f6",
                  }}
                />
              </div>
              <div style={percentLabelStyle}>
                <span>{percent}%</span>
                <span>
                  Stage {currentStage + 1} of {STAGES.length}
                </span>
              </div>
            </div>

            {/* Stage list */}
            <StageList currentStage={currentStage} percent={percent} />

            {/* Message */}
            <div style={messageBoxStyle}>{message}</div>

            {/* Action buttons */}
            <div style={buttonRowStyle}>
              {canCancel && (
                <button style={cancelButtonStyle} onClick={onCancel}>
                  Cancel
                </button>
              )}
              {isCancelRequested && (
                <button style={cancelRequestedStyle} disabled>
                  Cancel Requested...
                </button>
              )}
            </div>
          </>
        )}

        {/* Success result */}
        {state.status === "completed_success" && (
          <SuccessResult
            result={state.result}
            onViewInJobs={onViewInJobs}
            onViewReceipt={onViewReceipt}
            onClose={onClose}
          />
        )}

        {/* Gate blocked result */}
        {state.status === "completed_gate_blocked" && (
          <GateBlockedResult
            pendingGates={state.pendingGates}
            onResolveGates={onResolveGates}
            onClose={onClose}
          />
        )}

        {/* Failed result */}
        {state.status === "completed_failed" && (
          <FailedResult errors={state.errors} onClose={onClose} />
        )}

        {/* Canceled result */}
        {state.status === "canceled" && (
          <>
            <div style={messageBoxStyle}>
              This export was cancelled before completion.
            </div>
            <div style={buttonRowStyle}>
              <button style={secondaryButtonStyle} onClick={onClose}>
                Close
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default JobProgressModal;
