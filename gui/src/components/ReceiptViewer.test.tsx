/**
 * Tests for ReceiptViewer component.
 *
 * Sprint 20: Jobs-first GUI UX loop
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ReceiptViewer } from "./ReceiptViewer";
import type { JobReceipt, JobState } from "../api/types";
import { ApiClient } from "../api/client";

// Mock ApiClient
const mockGetReceipt = vi.fn();
const mockClient = {
  getReceipt: mockGetReceipt,
} as unknown as ApiClient;

const mockReceipt: JobReceipt = {
  schema_version: "1.0.0",
  job_id: "job-123",
  run_id: "run-456",
  receipt_status: "completed",
  timestamps: {
    created: "2025-01-15T10:00:00Z",
    started: "2025-01-15T10:00:01Z",
    completed: "2025-01-15T10:00:30Z",
  },
  config_snapshot: {
    reference: "John 1:1-5",
    mode: "traceable",
  },
  source_pins: {
    sblgnt: "v1.0.0",
    na28: "v28.1",
  },
  outputs: [
    {
      path: "/output/translation.json",
      size_bytes: 12345,
      sha256:
        "abc123def456abc123def456abc123def456abc123def456abc123def456abcd",
    },
    {
      path: "/output/bundle.zip",
      size_bytes: 1048576,
      sha256:
        "xyz789xyz789xyz789xyz789xyz789xyz789xyz789xyz789xyz789xyz789xyz7",
    },
  ],
  inputs_summary: {
    verse_count: 5,
  },
};

describe("ReceiptViewer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset clipboard mock
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn(),
      },
    });
  });

  describe("non-terminal states", () => {
    const nonTerminalStates: JobState[] = ["queued", "running", "cancelling"];

    nonTerminalStates.forEach((state) => {
      it(`shows pending message for ${state} state`, () => {
        render(
          <ReceiptViewer
            jobId="job-123"
            jobState={state}
            client={mockClient}
          />,
        );
        expect(
          screen.getByText("Receipt will be available when job completes."),
        ).toBeInTheDocument();
      });
    });

    it("does not fetch receipt for non-terminal state", () => {
      render(
        <ReceiptViewer
          jobId="job-123"
          jobState="running"
          client={mockClient}
        />,
      );
      expect(mockGetReceipt).not.toHaveBeenCalled();
    });
  });

  describe("terminal states - loading", () => {
    it("shows loading state while fetching", async () => {
      mockGetReceipt.mockImplementation(
        () => new Promise(() => {}), // Never resolves
      );

      render(
        <ReceiptViewer
          jobId="job-123"
          jobState="completed"
          client={mockClient}
        />,
      );

      expect(screen.getByText("Loading receipt...")).toBeInTheDocument();
    });
  });

  describe("terminal states - success", () => {
    beforeEach(() => {
      mockGetReceipt.mockResolvedValue(mockReceipt);
    });

    it("fetches receipt on mount for completed state", async () => {
      render(
        <ReceiptViewer
          jobId="job-123"
          jobState="completed"
          client={mockClient}
        />,
      );

      await waitFor(() => {
        expect(mockGetReceipt).toHaveBeenCalledWith("job-123");
      });
    });

    it("fetches receipt for failed state", async () => {
      render(
        <ReceiptViewer jobId="job-123" jobState="failed" client={mockClient} />,
      );

      await waitFor(() => {
        expect(mockGetReceipt).toHaveBeenCalledWith("job-123");
      });
    });

    it("fetches receipt for cancelled state", async () => {
      render(
        <ReceiptViewer
          jobId="job-123"
          jobState="cancelled"
          client={mockClient}
        />,
      );

      await waitFor(() => {
        expect(mockGetReceipt).toHaveBeenCalledWith("job-123");
      });
    });

    it("renders job metadata", async () => {
      render(
        <ReceiptViewer
          jobId="job-123"
          jobState="completed"
          client={mockClient}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Job Receipt")).toBeInTheDocument();
      });

      expect(screen.getByText("job-123")).toBeInTheDocument();
      expect(screen.getByText("run-456")).toBeInTheDocument();
      expect(screen.getByText("1.0.0")).toBeInTheDocument();
      expect(screen.getByText("completed")).toBeInTheDocument();
    });

    it("renders artifacts list", async () => {
      render(
        <ReceiptViewer
          jobId="job-123"
          jobState="completed"
          client={mockClient}
        />,
      );

      await waitFor(() => {
        expect(
          screen.getByText("/output/translation.json"),
        ).toBeInTheDocument();
      });

      expect(screen.getByText("/output/bundle.zip")).toBeInTheDocument();
      // Check for size display
      expect(screen.getByText("12.1 KB")).toBeInTheDocument();
      expect(screen.getByText("1.00 MB")).toBeInTheDocument();
    });

    it("renders Copy JSON button", async () => {
      render(
        <ReceiptViewer
          jobId="job-123"
          jobState="completed"
          client={mockClient}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Copy JSON")).toBeInTheDocument();
      });
    });

    it("copies JSON to clipboard when Copy JSON clicked", async () => {
      render(
        <ReceiptViewer
          jobId="job-123"
          jobState="completed"
          client={mockClient}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Copy JSON")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Copy JSON"));

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        JSON.stringify(mockReceipt, null, 2),
      );
    });

    it("shows Copied! feedback after copy", async () => {
      render(
        <ReceiptViewer
          jobId="job-123"
          jobState="completed"
          client={mockClient}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Copy JSON")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Copy JSON"));

      expect(screen.getByText("Copied!")).toBeInTheDocument();
    });
  });

  describe("collapsible sections", () => {
    beforeEach(() => {
      mockGetReceipt.mockResolvedValue(mockReceipt);
    });

    it("renders Timestamps section expanded by default", async () => {
      render(
        <ReceiptViewer
          jobId="job-123"
          jobState="completed"
          client={mockClient}
        />,
      );

      // textTransform: uppercase is CSS only, actual text is lowercase
      await waitFor(() => {
        expect(screen.getByText("Timestamps")).toBeInTheDocument();
      });

      // Should show timestamps content
      expect(screen.getByText("Created")).toBeInTheDocument();
    });

    it("renders Artifacts section expanded by default", async () => {
      render(
        <ReceiptViewer
          jobId="job-123"
          jobState="completed"
          client={mockClient}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Artifacts (2)")).toBeInTheDocument();
      });
    });

    it("renders Source Pins section collapsed", async () => {
      render(
        <ReceiptViewer
          jobId="job-123"
          jobState="completed"
          client={mockClient}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Source Pins (2)")).toBeInTheDocument();
      });

      // Source pins content should not be visible initially
      expect(screen.queryByText("sblgnt")).not.toBeInTheDocument();
    });

    it("expands Source Pins section on click", async () => {
      render(
        <ReceiptViewer
          jobId="job-123"
          jobState="completed"
          client={mockClient}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Source Pins (2)")).toBeInTheDocument();
      });

      // Click to expand
      fireEvent.click(screen.getByText("Source Pins (2)"));

      // Now source pins should be visible
      await waitFor(() => {
        expect(screen.getByText("sblgnt")).toBeInTheDocument();
      });
      expect(screen.getByText("v1.0.0")).toBeInTheDocument();
    });

    it("renders Config Snapshot section", async () => {
      render(
        <ReceiptViewer
          jobId="job-123"
          jobState="completed"
          client={mockClient}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Config Snapshot")).toBeInTheDocument();
      });
    });
  });

  describe("error handling", () => {
    it("shows error message when fetch fails", async () => {
      mockGetReceipt.mockRejectedValue(new Error("Network error"));

      render(
        <ReceiptViewer
          jobId="job-123"
          jobState="completed"
          client={mockClient}
        />,
      );

      await waitFor(() => {
        expect(
          screen.getByText("Failed to load receipt: Network error"),
        ).toBeInTheDocument();
      });
    });

    it("shows Retry button on error", async () => {
      mockGetReceipt.mockRejectedValue(new Error("Network error"));

      render(
        <ReceiptViewer
          jobId="job-123"
          jobState="completed"
          client={mockClient}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Retry")).toBeInTheDocument();
      });
    });

    it("retries fetch when Retry clicked", async () => {
      mockGetReceipt
        .mockRejectedValueOnce(new Error("Network error"))
        .mockResolvedValueOnce(mockReceipt);

      render(
        <ReceiptViewer
          jobId="job-123"
          jobState="completed"
          client={mockClient}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Retry")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Retry"));

      await waitFor(() => {
        expect(mockGetReceipt).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe("failed receipt status", () => {
    it("shows error box for failed receipt", async () => {
      const failedReceipt: JobReceipt = {
        ...mockReceipt,
        receipt_status: "failed",
        error_code: "SOURCE_NOT_FOUND",
        error_message: "Could not find source: invalid-source",
      };
      mockGetReceipt.mockResolvedValue(failedReceipt);

      render(
        <ReceiptViewer jobId="job-123" jobState="failed" client={mockClient} />,
      );

      await waitFor(() => {
        expect(screen.getByText("SOURCE_NOT_FOUND")).toBeInTheDocument();
      });

      expect(
        screen.getByText("Could not find source: invalid-source"),
      ).toBeInTheDocument();
    });
  });

  describe("no client", () => {
    it("returns null when client is null for terminal state", () => {
      const { container } = render(
        <ReceiptViewer jobId="job-123" jobState="completed" client={null} />,
      );

      // Without a client and no fetch possible, receipt will be null and component returns null
      expect(container.firstChild).toBeNull();
    });
  });
});
