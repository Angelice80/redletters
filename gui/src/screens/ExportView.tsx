/**
 * ExportView - Export workflow screen with wizard and scholarly run.
 *
 * Sprint v0.14.0: Task-shaped export interface with:
 * - Export Wizard (detect gates, acknowledge, choose type)
 * - Scholarly Run button triggering full workflow
 * - Gate enforcement matching backend rules
 */

import { useState, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAppStore, selectSettings } from "../store";
import type { ApiClient } from "../api/client";
import type { ApiErrorDetail } from "../api/types";
import {
  ApiErrorPanel,
  createApiErrorDetail,
} from "../components/ApiErrorPanel";

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
  step:
    | "reference"
    | "gates"
    | "acknowledge"
    | "export"
    | "running"
    | "complete";
  reference: string;
  pendingGates: GateInfo[];
  forceSelected: boolean;
  forceReason: string;
  exportType: ExportType;
  result: ScholarlyRunResult | null;
}

interface ScholarlyRunResult {
  success: boolean;
  gate_blocked: boolean;
  pending_gates: string[];
  message: string;
  output_dir?: string;
  bundle_path?: string;
  errors: string[];
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

const warningButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "#f59e0b",
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

const resultCardStyle: React.CSSProperties = {
  backgroundColor: "#1a1a2e",
  borderRadius: "6px",
  padding: "16px",
  marginTop: "16px",
};

const errorStyle: React.CSSProperties = {
  padding: "12px",
  backgroundColor: "#7f1d1d",
  color: "#fca5a5",
  borderRadius: "4px",
  marginBottom: "16px",
};

const successStyle: React.CSSProperties = {
  padding: "12px",
  backgroundColor: "#14532d",
  color: "#86efac",
  borderRadius: "4px",
  marginBottom: "16px",
};

const codeStyle: React.CSSProperties = {
  fontFamily: "monospace",
  backgroundColor: "#374151",
  padding: "2px 6px",
  borderRadius: "3px",
  fontSize: "12px",
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
    result: null,
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiErrorDetail | null>(null);
  const [mode, setMode] = useState<"readable" | "traceable">("traceable");

  // Step 1: Check gates for reference
  // Uses dedicated /v1/gates/pending endpoint for consistency with ScholarlyRunner
  const handleCheckGates = useCallback(async () => {
    if (!client || !wizard.reference.trim()) return;

    setLoading(true);
    setError(null);

    try {
      // Use dedicated gates endpoint for consistent gate detection
      const response = await client.getPendingGates(
        wizard.reference.trim(),
        settings.sessionId,
      );

      if (response.pending_gates.length > 0) {
        // Gates detected
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
        // No gates - skip to export
        setWizard((prev) => ({
          ...prev,
          step: "export",
          pendingGates: [],
        }));
      }
    } catch (err) {
      // Sprint 17: Include contract diagnostics in error
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

  // Step 4: Run scholarly export
  // Sprint 17: Uses ApiClient.runScholarly() instead of raw fetch()
  const handleScholarlyRun = useCallback(async () => {
    if (!client) return;

    setLoading(true);
    setError(null);
    setWizard((prev) => ({ ...prev, step: "running" }));

    try {
      // Sprint 17: Use ApiClient method for contract-first routing
      const result = await client.runScholarly({
        reference: wizard.reference.trim(),
        mode,
        force: wizard.forceSelected,
        session_id: settings.sessionId,
        include_schemas: true,
        create_zip: wizard.exportType === "bundle",
      });

      if (result.gate_blocked) {
        // Gate blocked - update wizard state
        setWizard((prev) => ({
          ...prev,
          step: "gates",
          pendingGates: result.pending_gates.map((ref: string) => ({
            ref,
            significance: "significant",
            message: "Pending acknowledgement",
          })),
          result: null,
        }));
        // Gate blocked is expected flow, not an error - clear any previous error
        setError(null);
      } else {
        // Success or failure
        setWizard((prev) => ({
          ...prev,
          step: "complete",
          result,
        }));
      }
    } catch (err) {
      // Sprint 17: Include contract diagnostics in error
      const diagnosticsUrl = client.contract
        ? `${client.baseUrl}${client.contract.runScholarly()}`
        : "/v1/run/scholarly";
      const contractDiags = client.getContractDiagnostics?.()
        ? client.getContractDiagnostics()
        : undefined;
      setError(
        createApiErrorDetail("POST", diagnosticsUrl, err, contractDiags),
      );
      setWizard((prev) => ({ ...prev, step: "export" }));
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

  const handleReset = useCallback(() => {
    setWizard({
      step: "reference",
      reference: "",
      pendingGates: [],
      forceSelected: false,
      forceReason: "",
      exportType: "bundle",
      result: null,
    });
    setError(null);
  }, []);

  const currentStepIndex =
    wizard.step === "reference"
      ? 0
      : wizard.step === "gates"
        ? 1
        : wizard.step === "acknowledge"
          ? 2
          : wizard.step === "export" ||
              wizard.step === "running" ||
              wizard.step === "complete"
            ? 3
            : 0;

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
            >
              {loading ? "Running..." : "Run Scholarly Export"}
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

      {/* Running */}
      {wizard.step === "running" && (
        <div style={sectionStyle}>
          <div style={sectionHeaderStyle}>Running Scholarly Export...</div>
          <div style={{ color: "#9ca3af" }}>
            Generating verified bundle for {wizard.reference}. This may take a
            moment.
          </div>
          <div
            style={{
              marginTop: "16px",
              padding: "12px",
              backgroundColor: "#1a1a2e",
              borderRadius: "4px",
            }}
          >
            <div style={{ color: "#60a5fa" }}>Processing...</div>
          </div>
        </div>
      )}

      {/* Complete */}
      {wizard.step === "complete" && wizard.result && (
        <div style={sectionStyle}>
          <div style={sectionHeaderStyle}>Export Complete</div>

          {wizard.result.success ? (
            <div style={successStyle}>
              Scholarly run completed successfully!
            </div>
          ) : (
            <div style={errorStyle}>
              Export completed with errors. Check the run log for details.
            </div>
          )}

          <div style={resultCardStyle}>
            <div style={{ marginBottom: "12px" }}>
              <span style={{ color: "#9ca3af" }}>Reference: </span>
              <span style={{ color: "#eaeaea" }}>{wizard.reference}</span>
            </div>

            {wizard.result.output_dir && (
              <div style={{ marginBottom: "12px" }}>
                <span style={{ color: "#9ca3af" }}>Output Directory: </span>
                <code style={codeStyle}>{wizard.result.output_dir}</code>
              </div>
            )}

            {wizard.result.bundle_path && (
              <div style={{ marginBottom: "12px" }}>
                <span style={{ color: "#9ca3af" }}>Bundle Path: </span>
                <code style={codeStyle}>{wizard.result.bundle_path}</code>
              </div>
            )}

            {wizard.result.errors.length > 0 && (
              <div style={{ marginTop: "12px" }}>
                <div
                  style={{
                    color: "#f59e0b",
                    fontSize: "13px",
                    marginBottom: "4px",
                  }}
                >
                  Warnings/Errors:
                </div>
                {wizard.result.errors.map((err, i) => (
                  <div key={i} style={{ color: "#fca5a5", fontSize: "12px" }}>
                    - {err}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div style={{ display: "flex", gap: "12px", marginTop: "20px" }}>
            <button style={primaryButtonStyle} onClick={handleReset}>
              Export Another
            </button>
            <Link to="/jobs">
              <button style={secondaryButtonStyle}>View in Jobs</button>
            </Link>
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
    </div>
  );
}
