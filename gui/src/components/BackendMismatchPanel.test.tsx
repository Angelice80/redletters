/**
 * Tests for BackendMismatchPanel component.
 *
 * Sprint 19: Guardrail against backend mode mismatch.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { BackendMismatchPanel } from "./BackendMismatchPanel";
import type { BackendMismatchInfo } from "../api/types";

describe("BackendMismatchPanel", () => {
  const onRetry = vi.fn();
  const onDismiss = vi.fn();

  const defaultMismatchInfo: BackendMismatchInfo = {
    detected: true,
    backendMode: "engine_only",
    missingRoutes: ["/translate", "/sources/status"],
    correctStartCommand: "python -m redletters engine start",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  describe("rendering", () => {
    it("shows Backend Mode Mismatch title", () => {
      render(
        <BackendMismatchPanel
          mismatchInfo={defaultMismatchInfo}
          onRetry={onRetry}
        />,
      );
      expect(screen.getByText("Backend Mode Mismatch")).toBeInTheDocument();
    });

    it("shows detected backend mode", () => {
      render(
        <BackendMismatchPanel
          mismatchInfo={defaultMismatchInfo}
          onRetry={onRetry}
        />,
      );
      expect(screen.getByText("engine_only")).toBeInTheDocument();
    });

    it("shows required mode as full", () => {
      render(
        <BackendMismatchPanel
          mismatchInfo={defaultMismatchInfo}
          onRetry={onRetry}
        />,
      );
      // "full" appears in both description and details - verify at least one exists
      expect(screen.getAllByText("full").length).toBeGreaterThan(0);
    });

    it("shows missing routes", () => {
      render(
        <BackendMismatchPanel
          mismatchInfo={defaultMismatchInfo}
          onRetry={onRetry}
        />,
      );
      // Missing routes are shown with error styling (prefixed with X)
      expect(screen.getByText(/\/translate/)).toBeInTheDocument();
      expect(screen.getByText(/\/sources\/status/)).toBeInTheDocument();
    });

    it("shows correct start command", () => {
      render(
        <BackendMismatchPanel
          mismatchInfo={defaultMismatchInfo}
          onRetry={onRetry}
        />,
      );
      expect(
        screen.getByText("python -m redletters engine start"),
      ).toBeInTheDocument();
    });

    it("shows Correct Start Command label", () => {
      render(
        <BackendMismatchPanel
          mismatchInfo={defaultMismatchInfo}
          onRetry={onRetry}
        />,
      );
      expect(screen.getByText("Correct Start Command")).toBeInTheDocument();
    });

    it("shows How to Fix section", () => {
      render(
        <BackendMismatchPanel
          mismatchInfo={defaultMismatchInfo}
          onRetry={onRetry}
        />,
      );
      expect(screen.getByText("How to Fix")).toBeInTheDocument();
    });
  });

  describe("button interactions", () => {
    it("shows Retry Connection button", () => {
      render(
        <BackendMismatchPanel
          mismatchInfo={defaultMismatchInfo}
          onRetry={onRetry}
        />,
      );
      expect(screen.getByText("Retry Connection")).toBeInTheDocument();
    });

    it("calls onRetry when Retry Connection clicked", () => {
      render(
        <BackendMismatchPanel
          mismatchInfo={defaultMismatchInfo}
          onRetry={onRetry}
        />,
      );
      fireEvent.click(screen.getByText("Retry Connection"));
      expect(onRetry).toHaveBeenCalledTimes(1);
    });

    it("shows Dismiss button when onDismiss provided", () => {
      render(
        <BackendMismatchPanel
          mismatchInfo={defaultMismatchInfo}
          onRetry={onRetry}
          onDismiss={onDismiss}
        />,
      );
      expect(screen.getByText("Dismiss")).toBeInTheDocument();
    });

    it("calls onDismiss when Dismiss clicked", () => {
      render(
        <BackendMismatchPanel
          mismatchInfo={defaultMismatchInfo}
          onRetry={onRetry}
          onDismiss={onDismiss}
        />,
      );
      fireEvent.click(screen.getByText("Dismiss"));
      expect(onDismiss).toHaveBeenCalledTimes(1);
    });

    it("does not show Dismiss button when onDismiss not provided", () => {
      render(
        <BackendMismatchPanel
          mismatchInfo={defaultMismatchInfo}
          onRetry={onRetry}
        />,
      );
      expect(screen.queryByText("Dismiss")).not.toBeInTheDocument();
    });

    it("shows Copy button for command", () => {
      render(
        <BackendMismatchPanel
          mismatchInfo={defaultMismatchInfo}
          onRetry={onRetry}
        />,
      );
      // There should be a "Copy" button in the command box
      expect(screen.getByText("Copy")).toBeInTheDocument();
    });

    it("copies command to clipboard when Copy clicked", () => {
      render(
        <BackendMismatchPanel
          mismatchInfo={defaultMismatchInfo}
          onRetry={onRetry}
        />,
      );
      fireEvent.click(screen.getByText("Copy"));
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        "python -m redletters engine start",
      );
    });

    it("shows Copy Diagnostics button", () => {
      render(
        <BackendMismatchPanel
          mismatchInfo={defaultMismatchInfo}
          onRetry={onRetry}
        />,
      );
      expect(screen.getByText("Copy Diagnostics")).toBeInTheDocument();
    });

    it("copies diagnostics to clipboard when Copy Diagnostics clicked", async () => {
      render(
        <BackendMismatchPanel
          mismatchInfo={defaultMismatchInfo}
          onRetry={onRetry}
        />,
      );
      fireEvent.click(screen.getByText("Copy Diagnostics"));
      // Wait for async clipboard operation
      await vi.waitFor(() => {
        expect(navigator.clipboard.writeText).toHaveBeenCalled();
      });
      // Verify the diagnostics contains key info
      const copiedText = (
        navigator.clipboard.writeText as ReturnType<typeof vi.fn>
      ).mock.calls[0][0];
      expect(copiedText).toContain("Backend Mismatch");
      expect(copiedText).toContain("engine_only");
      expect(copiedText).toContain("/translate");
    });
  });

  describe("edge cases", () => {
    it("handles empty missing routes array", () => {
      const mismatchInfo: BackendMismatchInfo = {
        detected: true,
        backendMode: "engine_only",
        missingRoutes: [],
        correctStartCommand: "python -m redletters engine start",
      };
      render(
        <BackendMismatchPanel mismatchInfo={mismatchInfo} onRetry={onRetry} />,
      );
      // Should not crash and should still show the panel
      expect(screen.getByText("Backend Mode Mismatch")).toBeInTheDocument();
    });

    it("handles undefined backend mode", () => {
      const mismatchInfo: BackendMismatchInfo = {
        detected: true,
        missingRoutes: ["/translate"],
        correctStartCommand: "python -m redletters engine start",
      };
      render(
        <BackendMismatchPanel mismatchInfo={mismatchInfo} onRetry={onRetry} />,
      );
      // Should default to showing "engine_only"
      expect(screen.getByText("Backend Mode Mismatch")).toBeInTheDocument();
    });
  });
});
