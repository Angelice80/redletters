/**
 * BootstrapWizard - First-run onboarding flow.
 *
 * Sprint 16: Guides users through:
 * 1. Connecting to backend
 * 2. Installing spine source
 * 3. Running first translation
 * 4. Running first export
 */

import { useState, useCallback, useEffect } from "react";
import type { ApiClient } from "../api/client";
import type { ApiCapabilities, SourcesStatusResponse } from "../api/types";

interface BootstrapWizardProps {
  client: ApiClient | null;
  capabilities: ApiCapabilities | null;
  onComplete: () => void;
  onSkip: () => void;
}

type WizardStep =
  | "welcome"
  | "check_backend"
  | "install_spine"
  | "test_translation"
  | "complete";

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: "rgba(0, 0, 0, 0.85)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 2000,
};

const modalStyle: React.CSSProperties = {
  backgroundColor: "var(--rl-bg-card)",
  borderRadius: "12px",
  padding: "32px",
  maxWidth: "600px",
  width: "90%",
  maxHeight: "80vh",
  overflow: "auto",
  boxShadow: "0 20px 60px rgba(0, 0, 0, 0.5)",
};

const headerStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-xl)",
  fontWeight: 600,
  color: "var(--rl-text)",
  marginBottom: "8px",
};

const subHeaderStyle: React.CSSProperties = {
  fontSize: "var(--rl-fs-base)",
  color: "var(--rl-text-muted)",
  marginBottom: "24px",
};

const stepIndicatorStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "center",
  gap: "8px",
  marginBottom: "32px",
};

const stepDotStyle: React.CSSProperties = {
  width: "10px",
  height: "10px",
  borderRadius: "50%",
  backgroundColor: "var(--rl-border-strong)",
  transition: "background-color 0.2s",
};

const stepDotActiveStyle: React.CSSProperties = {
  ...stepDotStyle,
  backgroundColor: "var(--rl-primary)",
};

const stepDotCompleteStyle: React.CSSProperties = {
  ...stepDotStyle,
  backgroundColor: "var(--rl-success)",
};

const contentStyle: React.CSSProperties = {
  minHeight: "200px",
};

const statusCardStyle: React.CSSProperties = {
  backgroundColor: "var(--rl-bg-app)",
  borderRadius: "8px",
  padding: "16px",
  marginBottom: "16px",
};

const statusItemStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "12px",
  padding: "8px 0",
};

const statusIconStyle: React.CSSProperties = {
  width: "24px",
  height: "24px",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontSize: "var(--rl-fs-base)",
};

const buttonContainerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  marginTop: "24px",
};

const buttonStyle: React.CSSProperties = {
  padding: "12px 24px",
  fontSize: "var(--rl-fs-base)",
  fontWeight: 500,
  border: "none",
  borderRadius: "6px",
  cursor: "pointer",
  transition: "background-color 0.15s",
};

const primaryButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "var(--rl-primary)",
  color: "white",
};

const secondaryButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "var(--rl-border-strong)",
  color: "var(--rl-text)",
};

const successButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "var(--rl-success)",
  color: "white",
};

const disabledButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  backgroundColor: "var(--rl-border-strong)",
  color: "var(--rl-text-dim)",
  cursor: "not-allowed",
};

const STEPS: WizardStep[] = [
  "welcome",
  "check_backend",
  "install_spine",
  "test_translation",
  "complete",
];

export function BootstrapWizard({
  client,
  capabilities,
  onComplete,
  onSkip,
}: BootstrapWizardProps) {
  const [currentStep, setCurrentStep] = useState<WizardStep>("welcome");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Status checks
  const [backendConnected, setBackendConnected] = useState(false);
  const [spineInstalled, setSpineInstalled] = useState(false);
  const [spineSourceId, setSpineSourceId] = useState<string | null>(null);
  const [translationTested, setTranslationTested] = useState(false);

  // Check backend connection
  useEffect(() => {
    if (capabilities) {
      setBackendConnected(true);
    }
  }, [capabilities]);

  // Check spine status when on that step
  const checkSpineStatus = useCallback(async () => {
    if (!client) return;

    setLoading(true);
    setError(null);

    try {
      const status: SourcesStatusResponse = await client.getSourcesStatus();
      setSpineInstalled(status.spine_installed);
      setSpineSourceId(status.spine_source_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to check sources");
    } finally {
      setLoading(false);
    }
  }, [client]);

  // Install spine
  const handleInstallSpine = useCallback(async () => {
    if (!client || !spineSourceId) return;

    setLoading(true);
    setError(null);

    try {
      const result = await client.installSource({
        source_id: spineSourceId,
        accept_eula: true,
      });

      if (result.success) {
        setSpineInstalled(true);
        setCurrentStep("test_translation");
      } else {
        setError(result.error || result.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to install spine");
    } finally {
      setLoading(false);
    }
  }, [client, spineSourceId]);

  // Test translation
  const handleTestTranslation = useCallback(async () => {
    if (!client) return;

    setLoading(true);
    setError(null);

    try {
      const result = await client.translate({
        reference: "John 1:1",
        mode: "readable",
        session_id: "bootstrap-test",
        translator: "literal",
      });

      if ("translation_text" in result) {
        setTranslationTested(true);
        setCurrentStep("complete");
      } else {
        // Gate response is also success
        setTranslationTested(true);
        setCurrentStep("complete");
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to test translation",
      );
    } finally {
      setLoading(false);
    }
  }, [client]);

  // Step navigation
  const handleNext = useCallback(() => {
    const idx = STEPS.indexOf(currentStep);
    if (idx < STEPS.length - 1) {
      const nextStep = STEPS[idx + 1];
      setCurrentStep(nextStep);

      // Trigger checks on step entry
      if (nextStep === "install_spine") {
        checkSpineStatus();
      }
    }
  }, [currentStep, checkSpineStatus]);

  const handleBack = useCallback(() => {
    const idx = STEPS.indexOf(currentStep);
    if (idx > 0) {
      setCurrentStep(STEPS[idx - 1]);
    }
  }, [currentStep]);

  const getStepDotStyle = (step: WizardStep) => {
    const currentIdx = STEPS.indexOf(currentStep);
    const stepIdx = STEPS.indexOf(step);

    if (stepIdx < currentIdx) return stepDotCompleteStyle;
    if (stepIdx === currentIdx) return stepDotActiveStyle;
    return stepDotStyle;
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case "welcome":
        return (
          <div style={contentStyle}>
            <div style={{ textAlign: "center", marginBottom: "24px" }}>
              <div
                style={{
                  fontSize: "48px",
                  marginBottom: "16px",
                  color: "var(--rl-error)",
                }}
              >
                +
              </div>
              <h2 style={headerStyle}>Welcome to Red Letters</h2>
              <p style={subHeaderStyle}>
                Let's get you set up to explore and translate Greek New
                Testament texts with full scholarly rigor.
              </p>
            </div>

            <div style={statusCardStyle}>
              <div style={{ color: "var(--rl-text-muted)", fontSize: "var(--rl-fs-base)" }}>
                This wizard will help you:
              </div>
              <ul
                style={{
                  color: "var(--rl-text)",
                  marginTop: "12px",
                  paddingLeft: "20px",
                }}
              >
                <li>Connect to the translation engine</li>
                <li>Install the required Greek text sources</li>
                <li>Run your first translation</li>
              </ul>
            </div>
          </div>
        );

      case "check_backend":
        return (
          <div style={contentStyle}>
            <h2 style={headerStyle}>Backend Connection</h2>
            <p style={subHeaderStyle}>
              Checking connection to the Red Letters engine...
            </p>

            <div style={statusCardStyle}>
              <div style={statusItemStyle}>
                <div style={statusIconStyle}>
                  {backendConnected ? "✅" : loading ? "⏳" : "❌"}
                </div>
                <div>
                  <div style={{ color: "var(--rl-text)" }}>
                    Engine Connection
                  </div>
                  <div
                    style={{ color: "var(--rl-text-dim)", fontSize: "var(--rl-fs-sm)" }}
                  >
                    {backendConnected
                      ? `Connected to v${capabilities?.version || "unknown"}`
                      : "Checking..."}
                  </div>
                </div>
              </div>

              {capabilities && (
                <div style={statusItemStyle}>
                  <div style={statusIconStyle}>
                    {capabilities.initialized ? "✅" : "⚠️"}
                  </div>
                  <div>
                    <div style={{ color: "var(--rl-text)" }}>
                      Engine Initialized
                    </div>
                    <div
                      style={{ color: "var(--rl-text-dim)", fontSize: "var(--rl-fs-sm)" }}
                    >
                      {capabilities.initialized
                        ? "Ready to process requests"
                        : "Engine starting up..."}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {error && (
              <div
                style={{
                  padding: "12px",
                  backgroundColor: "#7f1d1d",
                  color: "#fca5a5",
                  borderRadius: "4px",
                  marginTop: "12px",
                }}
              >
                {error}
              </div>
            )}
          </div>
        );

      case "install_spine":
        return (
          <div style={contentStyle}>
            <h2 style={headerStyle}>Install Text Sources</h2>
            <p style={subHeaderStyle}>
              The canonical Greek text source is required for translation.
            </p>

            <div style={statusCardStyle}>
              <div style={statusItemStyle}>
                <div style={statusIconStyle}>
                  {spineInstalled ? "✅" : "📦"}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ color: "var(--rl-text)" }}>
                    MorphGNT/SBLGNT Spine
                  </div>
                  <div
                    style={{ color: "var(--rl-text-dim)", fontSize: "var(--rl-fs-sm)" }}
                  >
                    {spineInstalled
                      ? "Installed and ready"
                      : "Required for translation"}
                  </div>
                </div>
                {!spineInstalled && spineSourceId && (
                  <button
                    style={loading ? disabledButtonStyle : primaryButtonStyle}
                    onClick={handleInstallSpine}
                    disabled={loading}
                  >
                    {loading ? "Installing..." : "Install"}
                  </button>
                )}
              </div>
            </div>

            {spineInstalled && (
              <div
                style={{
                  padding: "12px",
                  backgroundColor: "#14532d",
                  color: "#86efac",
                  borderRadius: "4px",
                  marginTop: "12px",
                }}
              >
                Spine installed! You can now translate passages.
              </div>
            )}

            {error && (
              <div
                style={{
                  padding: "12px",
                  backgroundColor: "#7f1d1d",
                  color: "#fca5a5",
                  borderRadius: "4px",
                  marginTop: "12px",
                }}
              >
                {error}
              </div>
            )}
          </div>
        );

      case "test_translation":
        return (
          <div style={contentStyle}>
            <h2 style={headerStyle}>Test Translation</h2>
            <p style={subHeaderStyle}>
              Let's verify everything works with a sample translation.
            </p>

            <div style={statusCardStyle}>
              <div
                style={{ color: "var(--rl-text-muted)", marginBottom: "8px" }}
              >
                Test passage:
              </div>
              <div
                style={{
                  fontFamily: "'SBL Greek', serif",
                  color: "#60a5fa",
                  fontSize: "var(--rl-fs-lg)",
                }}
              >
                John 1:1
              </div>
            </div>

            <button
              style={loading ? disabledButtonStyle : primaryButtonStyle}
              onClick={handleTestTranslation}
              disabled={loading}
            >
              {loading ? "Translating..." : "Run Test Translation"}
            </button>

            {translationTested && (
              <div
                style={{
                  padding: "12px",
                  backgroundColor: "#14532d",
                  color: "#86efac",
                  borderRadius: "4px",
                  marginTop: "12px",
                }}
              >
                Translation successful! Your setup is complete.
              </div>
            )}

            {error && (
              <div
                style={{
                  padding: "12px",
                  backgroundColor: "#7f1d1d",
                  color: "#fca5a5",
                  borderRadius: "4px",
                  marginTop: "12px",
                }}
              >
                {error}
              </div>
            )}
          </div>
        );

      case "complete":
        return (
          <div style={contentStyle}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "64px", marginBottom: "16px" }}>✅</div>
              <h2 style={headerStyle}>Setup Complete!</h2>
              <p style={subHeaderStyle}>
                You're ready to explore the Greek New Testament with full
                scholarly tools.
              </p>

              <div style={statusCardStyle}>
                <div
                  style={{
                    color: "var(--rl-text-muted)",
                    marginBottom: "12px",
                  }}
                >
                  Quick start suggestions:
                </div>
                <ul
                  style={{
                    color: "var(--rl-text)",
                    textAlign: "left",
                    paddingLeft: "20px",
                  }}
                >
                  <li>
                    <strong>Explore</strong> - Translate passages with variant
                    analysis
                  </li>
                  <li>
                    <strong>Export</strong> - Create scholarly bundles for
                    publication
                  </li>
                  <li>
                    <strong>Sources</strong> - Manage additional text sources
                  </li>
                </ul>
              </div>
            </div>
          </div>
        );
    }
  };

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        {/* Step indicators */}
        <div style={stepIndicatorStyle}>
          {STEPS.map((step) => (
            <div key={step} style={getStepDotStyle(step)} />
          ))}
        </div>

        {/* Content */}
        {renderStepContent()}

        {/* Navigation */}
        <div style={buttonContainerStyle}>
          {currentStep === "welcome" ? (
            <button style={secondaryButtonStyle} onClick={onSkip}>
              Skip Setup
            </button>
          ) : currentStep !== "complete" ? (
            <button style={secondaryButtonStyle} onClick={handleBack}>
              Back
            </button>
          ) : (
            <div />
          )}

          {currentStep === "welcome" && (
            <button style={primaryButtonStyle} onClick={handleNext}>
              Get Started
            </button>
          )}

          {currentStep === "check_backend" && backendConnected && (
            <button style={primaryButtonStyle} onClick={handleNext}>
              Continue
            </button>
          )}

          {currentStep === "install_spine" && spineInstalled && (
            <button style={primaryButtonStyle} onClick={handleNext}>
              Continue
            </button>
          )}

          {currentStep === "complete" && (
            <button style={successButtonStyle} onClick={onComplete}>
              Start Exploring
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default BootstrapWizard;
