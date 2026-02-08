/**
 * Tests for JobProgressModal component.
 *
 * Sprint 19: Jobs-native GUI
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { JobProgressModal } from "./JobProgressModal";
import type { JobUIState, ScholarlyJobResult } from "../api/types";

describe("JobProgressModal", () => {
  const onCancel = vi.fn();
  const onClose = vi.fn();
  const onViewInJobs = vi.fn();
  const onResolveGates = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("idle state", () => {
    it("returns null for idle state", () => {
      const state: JobUIState = { status: "idle" };
      const { container } = render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(container.firstChild).toBeNull();
    });
  });

  describe("enqueued state", () => {
    const state: JobUIState = { status: "enqueued", jobId: "job-123" };

    it("shows Running Scholarly Export title", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(
        screen.getByText("Running Scholarly Export..."),
      ).toBeInTheDocument();
    });

    it("shows queued message", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(
        screen.getByText("Job queued, waiting to start..."),
      ).toBeInTheDocument();
    });

    it("shows Cancel button", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(screen.getByText("Cancel")).toBeInTheDocument();
    });

    it("calls onCancel when Cancel clicked", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      fireEvent.click(screen.getByText("Cancel"));
      expect(onCancel).toHaveBeenCalledTimes(1);
    });
  });

  describe("streaming state", () => {
    const state: JobUIState = {
      status: "streaming",
      jobId: "job-123",
      stage: "translate",
      percent: 45,
      message: "Processing verses...",
    };

    it("shows Running Scholarly Export title", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(
        screen.getByText("Running Scholarly Export..."),
      ).toBeInTheDocument();
    });

    it("shows current message", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(screen.getByText("Processing verses...")).toBeInTheDocument();
    });

    it("shows percent progress", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      // Should show 45% in progress bar area
      expect(screen.getAllByText("45%").length).toBeGreaterThan(0);
    });

    it("shows Cancel button", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(screen.getByText("Cancel")).toBeInTheDocument();
    });
  });

  describe("cancel_requested state", () => {
    const state: JobUIState = { status: "cancel_requested", jobId: "job-123" };

    it("shows Cancelling title", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(screen.getByText("Cancelling...")).toBeInTheDocument();
    });

    it("shows Cancel Requested button (disabled)", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      const btn = screen.getByText("Cancel Requested...");
      expect(btn).toBeInTheDocument();
      expect(btn).toBeDisabled();
    });

    it("shows cancel waiting message", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(
        screen.getByText("Cancel requested, waiting for confirmation..."),
      ).toBeInTheDocument();
    });
  });

  describe("completed_success state", () => {
    const result: ScholarlyJobResult = {
      success: true,
      output_dir: "/output/scholarly-20250101",
      bundle_path: "/output/bundle.zip",
      run_log_summary: {
        reference: "John 1:1-51",
        mode: "traceable",
        verse_count: 100,
        file_count: 5,
      },
    };
    const state: JobUIState = {
      status: "completed_success",
      jobId: "job-123",
      result,
    };

    it("shows Export Complete title", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(screen.getByText("Export Complete")).toBeInTheDocument();
    });

    it("shows Scholarly Run Complete message", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(screen.getByText("Scholarly Run Complete")).toBeInTheDocument();
    });

    it("shows output directory", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(
        screen.getByText("/output/scholarly-20250101"),
      ).toBeInTheDocument();
    });

    it("shows bundle path", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(screen.getByText("/output/bundle.zip")).toBeInTheDocument();
    });

    it("shows run log summary", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(screen.getByText("100 verses, 5 files")).toBeInTheDocument();
    });

    it("shows Close button", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(screen.getByText("Close")).toBeInTheDocument();
    });

    it("calls onClose when Close clicked", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      fireEvent.click(screen.getByText("Close"));
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("shows View in Jobs button when handler provided", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
          onViewInJobs={onViewInJobs}
        />,
      );
      expect(screen.getByText("View in Jobs")).toBeInTheDocument();
    });

    it("calls onViewInJobs when clicked", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
          onViewInJobs={onViewInJobs}
        />,
      );
      fireEvent.click(screen.getByText("View in Jobs"));
      expect(onViewInJobs).toHaveBeenCalledTimes(1);
    });
  });

  describe("completed_gate_blocked state", () => {
    const state: JobUIState = {
      status: "completed_gate_blocked",
      jobId: "job-123",
      pendingGates: ["variant-A", "variant-B"],
    };

    it("shows Gates Pending title", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      // "Gates Pending" appears in both title and content box - use getAllByText
      expect(screen.getAllByText("Gates Pending").length).toBeGreaterThan(0);
    });

    it("shows pending gate count", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(
        screen.getByText(
          "2 variant(s) require acknowledgement before export can proceed.",
        ),
      ).toBeInTheDocument();
    });

    it("shows pending gate names", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(screen.getByText("variant-A")).toBeInTheDocument();
      expect(screen.getByText("variant-B")).toBeInTheDocument();
    });

    it("shows Resolve Gates button when handler provided", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
          onResolveGates={onResolveGates}
        />,
      );
      expect(screen.getByText("Resolve Gates")).toBeInTheDocument();
    });

    it("calls onResolveGates when clicked", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
          onResolveGates={onResolveGates}
        />,
      );
      fireEvent.click(screen.getByText("Resolve Gates"));
      expect(onResolveGates).toHaveBeenCalledTimes(1);
    });
  });

  describe("completed_failed state", () => {
    const state: JobUIState = {
      status: "completed_failed",
      jobId: "job-123",
      errors: ["Source not found", "Translation failed"],
    };

    it("shows Export Failed title", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      // "Export Failed" appears in both title and content box - use getAllByText
      expect(screen.getAllByText("Export Failed").length).toBeGreaterThan(0);
    });

    it("shows error messages", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(screen.getByText("Source not found")).toBeInTheDocument();
      expect(screen.getByText("Translation failed")).toBeInTheDocument();
    });

    it("shows unknown error when empty errors", () => {
      const emptyState: JobUIState = {
        status: "completed_failed",
        jobId: "job-123",
        errors: [],
      };
      render(
        <JobProgressModal
          state={emptyState}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(
        screen.getByText("An unknown error occurred."),
      ).toBeInTheDocument();
    });
  });

  describe("canceled state", () => {
    const state: JobUIState = { status: "canceled", jobId: "job-123" };

    it("shows Export Cancelled title", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(screen.getByText("Export Cancelled")).toBeInTheDocument();
    });

    it("shows cancelled message", () => {
      render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );
      expect(
        screen.getByText("This export was cancelled before completion."),
      ).toBeInTheDocument();
    });
  });

  describe("overlay click behavior", () => {
    it("closes on overlay click for terminal states", () => {
      const state: JobUIState = {
        status: "completed_success",
        jobId: "job-123",
        result: { output_dir: "/out", success: true },
      };
      const { container } = render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );

      // Click the overlay (first div)
      const overlay = container.firstChild as HTMLElement;
      fireEvent.click(overlay);
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("does not close on overlay click for non-terminal states", () => {
      const state: JobUIState = {
        status: "streaming",
        jobId: "job-123",
        stage: "translate",
        percent: 50,
        message: "...",
      };
      const { container } = render(
        <JobProgressModal
          state={state}
          onCancel={onCancel}
          onClose={onClose}
        />,
      );

      const overlay = container.firstChild as HTMLElement;
      fireEvent.click(overlay);
      expect(onClose).not.toHaveBeenCalled();
    });
  });
});
