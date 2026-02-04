/**
 * Tests for ConnectionBadge component.
 *
 * Sprint 19: Jobs-native GUI
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConnectionBadge } from "./ConnectionBadge";
import type { SSEHealthInfo } from "../api/types";

describe("ConnectionBadge", () => {
  const baseHealth: SSEHealthInfo = {
    state: "connected",
    baseUrl: "http://127.0.0.1:47200",
    lastEventId: null,
    lastMessageAt: null,
    reconnectAttempt: 0,
  };

  describe("state display", () => {
    it("shows Connected for connected state", () => {
      render(
        <ConnectionBadge health={{ ...baseHealth, state: "connected" }} />,
      );
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    it("shows Reconnecting... for reconnecting state", () => {
      render(
        <ConnectionBadge health={{ ...baseHealth, state: "reconnecting" }} />,
      );
      expect(screen.getByText("Reconnecting...")).toBeInTheDocument();
    });

    it("shows Disconnected for disconnected state", () => {
      render(
        <ConnectionBadge health={{ ...baseHealth, state: "disconnected" }} />,
      );
      expect(screen.getByText("Disconnected")).toBeInTheDocument();
    });
  });

  describe("tooltip", () => {
    it("shows tooltip on click", () => {
      render(<ConnectionBadge health={baseHealth} />);

      // Click to show tooltip
      fireEvent.click(screen.getByText("Connected"));

      // Tooltip should show SSE Connection header
      expect(screen.getByText("SSE Connection")).toBeInTheDocument();
    });

    it("shows base URL in tooltip", () => {
      render(<ConnectionBadge health={baseHealth} />);
      fireEvent.click(screen.getByText("Connected"));

      expect(screen.getByText("http://127.0.0.1:47200")).toBeInTheDocument();
    });

    it("shows last event ID when present", () => {
      render(<ConnectionBadge health={{ ...baseHealth, lastEventId: 42 }} />);
      fireEvent.click(screen.getByText("Connected"));

      expect(screen.getByText("42")).toBeInTheDocument();
    });

    it("shows None when no last event ID", () => {
      render(<ConnectionBadge health={baseHealth} />);
      fireEvent.click(screen.getByText("Connected"));

      expect(screen.getByText("None")).toBeInTheDocument();
    });

    it("shows Never when no last message", () => {
      render(<ConnectionBadge health={baseHealth} />);
      fireEvent.click(screen.getByText("Connected"));

      expect(screen.getByText("Never")).toBeInTheDocument();
    });

    it("shows reconnect attempt when reconnecting", () => {
      render(
        <ConnectionBadge
          health={{ ...baseHealth, state: "reconnecting", reconnectAttempt: 3 }}
        />,
      );
      fireEvent.click(screen.getByText("Reconnecting..."));

      expect(screen.getByText("#3")).toBeInTheDocument();
    });
  });

  describe("reconnect button", () => {
    it("shows reconnect button when disconnected", () => {
      const onReconnect = vi.fn();
      render(
        <ConnectionBadge
          health={{ ...baseHealth, state: "disconnected" }}
          onReconnect={onReconnect}
        />,
      );

      fireEvent.click(screen.getByText("Disconnected"));
      const reconnectBtn = screen.getByText("Reconnect");
      expect(reconnectBtn).toBeInTheDocument();
    });

    it("calls onReconnect when button clicked", () => {
      const onReconnect = vi.fn();
      render(
        <ConnectionBadge
          health={{ ...baseHealth, state: "disconnected" }}
          onReconnect={onReconnect}
        />,
      );

      fireEvent.click(screen.getByText("Disconnected"));
      fireEvent.click(screen.getByText("Reconnect"));

      expect(onReconnect).toHaveBeenCalledTimes(1);
    });

    it("does not show reconnect button when connected", () => {
      const onReconnect = vi.fn();
      render(
        <ConnectionBadge
          health={{ ...baseHealth, state: "connected" }}
          onReconnect={onReconnect}
        />,
      );

      fireEvent.click(screen.getByText("Connected"));
      expect(screen.queryByText("Reconnect")).not.toBeInTheDocument();
    });
  });

  describe("title attribute", () => {
    it("has SSE status title", () => {
      const { container } = render(<ConnectionBadge health={baseHealth} />);
      const badge = container.querySelector('[title="SSE: Connected"]');
      expect(badge).toBeInTheDocument();
    });
  });
});
