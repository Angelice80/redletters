/**
 * Tests for SSE Manager and React hooks.
 *
 * Sprint 19: Jobs-native GUI
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import {
  SSEManager,
  SSEProvider,
  useSSE,
  useJobEvents,
  BoundedSequenceSet,
} from "./sse";
import type { SSEEvent, SSEHealthInfo } from "./types";
import type { ReactNode } from "react";

describe("BoundedSequenceSet", () => {
  it("adds and checks sequences", () => {
    const set = new BoundedSequenceSet(100);
    expect(set.has(1)).toBe(false);
    set.add(1);
    expect(set.has(1)).toBe(true);
    expect(set.size).toBe(1);
  });

  it("deduplicates sequences", () => {
    const set = new BoundedSequenceSet(100);
    set.add(1);
    set.add(1);
    set.add(1);
    expect(set.size).toBe(1);
  });

  it("prunes oldest entries when max size exceeded", () => {
    const maxSize = 10;
    const set = new BoundedSequenceSet(maxSize);

    // Add more than maxSize entries
    for (let i = 0; i < 15; i++) {
      set.add(i);
    }

    // Size should be capped at maxSize
    expect(set.size).toBe(maxSize);

    // Oldest entries (0-4) should be pruned
    expect(set.has(0)).toBe(false);
    expect(set.has(1)).toBe(false);
    expect(set.has(2)).toBe(false);
    expect(set.has(3)).toBe(false);
    expect(set.has(4)).toBe(false);

    // Newest entries (5-14) should still exist
    expect(set.has(5)).toBe(true);
    expect(set.has(14)).toBe(true);
  });

  it("clears all entries", () => {
    const set = new BoundedSequenceSet(100);
    set.add(1);
    set.add(2);
    set.add(3);
    expect(set.size).toBe(3);

    set.clear();
    expect(set.size).toBe(0);
    expect(set.has(1)).toBe(false);
  });

  it("handles continuous stream without memory leak", () => {
    const maxSize = 5000;
    const set = new BoundedSequenceSet(maxSize);

    // Simulate continuous stream of 10000 events
    for (let i = 0; i < 10000; i++) {
      set.add(i);
    }

    // Size should stay bounded
    expect(set.size).toBe(maxSize);

    // Should still filter duplicates
    const beforeSize = set.size;
    set.add(9999); // Already exists
    expect(set.size).toBe(beforeSize);
  });
});

describe("SSEManager", () => {
  let manager: SSEManager;
  let onEvent: ReturnType<typeof vi.fn<(event: SSEEvent) => void>>;
  let onHealthChange: ReturnType<typeof vi.fn<(health: SSEHealthInfo) => void>>;

  beforeEach(() => {
    onEvent = vi.fn();
    onHealthChange = vi.fn();
    manager = new SSEManager({
      baseUrl: "http://127.0.0.1:47200",
      token: "test-token",
      onEvent,
      onHealthChange,
      reconnectDelayMs: 100,
      maxReconnectDelayMs: 1000,
    });
  });

  afterEach(() => {
    manager.disconnect();
    vi.restoreAllMocks();
  });

  describe("initialization", () => {
    it("starts disconnected", () => {
      expect(manager.state).toBe("disconnected");
    });

    it("has null lastEventId initially", () => {
      expect(manager.lastEventId).toBeNull();
    });

    it("has null lastMessageAt initially", () => {
      expect(manager.lastMessageAt).toBeNull();
    });

    it("provides health info", () => {
      const health = manager.health;
      expect(health.state).toBe("disconnected");
      expect(health.baseUrl).toBe("http://127.0.0.1:47200");
      expect(health.lastEventId).toBeNull();
      expect(health.lastMessageAt).toBeNull();
      expect(health.reconnectAttempt).toBe(0);
    });
  });

  describe("configuration updates", () => {
    it("allows updating token", () => {
      manager.updateToken("new-token");
      // Token is private, but we can verify it doesn't throw
      expect(manager.state).toBe("disconnected");
    });

    it("allows updating base URL", () => {
      manager.updateBaseUrl("http://localhost:8080");
      expect(manager.health.baseUrl).toBe("http://localhost:8080");
    });

    it("strips trailing slash from base URL", () => {
      manager.updateBaseUrl("http://localhost:8080/");
      expect(manager.health.baseUrl).toBe("http://localhost:8080");
    });
  });

  describe("disconnect", () => {
    it("sets state to disconnected", () => {
      manager.disconnect();
      expect(manager.state).toBe("disconnected");
    });

    it("remains disconnected when already disconnected", () => {
      // Manager starts disconnected, so disconnect() is a no-op for state
      manager.disconnect();
      expect(manager.state).toBe("disconnected");
      // onHealthChange is only called when state actually changes
    });
  });

  describe("clearSeenSequences", () => {
    it("clears seen sequences without error", () => {
      manager.clearSeenSequences();
      expect(manager.state).toBe("disconnected");
    });
  });
});

describe("SSE types", () => {
  describe("SSEHealthInfo", () => {
    it("accepts valid health info", () => {
      const health: SSEHealthInfo = {
        state: "connected",
        baseUrl: "http://127.0.0.1:47200",
        lastEventId: 42,
        lastMessageAt: new Date(),
        reconnectAttempt: 0,
      };
      expect(health.state).toBe("connected");
    });

    it("accepts all state values", () => {
      const states: SSEHealthInfo["state"][] = [
        "connected",
        "reconnecting",
        "disconnected",
      ];
      states.forEach((state) => {
        const health: SSEHealthInfo = {
          state,
          baseUrl: "",
          lastEventId: null,
          lastMessageAt: null,
          reconnectAttempt: 0,
        };
        expect(health.state).toBe(state);
      });
    });
  });
});

describe("SSEProvider and useSSE", () => {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <SSEProvider
      baseUrl="http://127.0.0.1:47200"
      token="test-token"
      autoConnect={false}
    >
      {children}
    </SSEProvider>
  );

  it("provides context with default values when no token", () => {
    const emptyWrapper = ({ children }: { children: ReactNode }) => (
      <SSEProvider
        baseUrl="http://127.0.0.1:47200"
        token=""
        autoConnect={false}
      >
        {children}
      </SSEProvider>
    );

    const { result } = renderHook(() => useSSE(), { wrapper: emptyWrapper });

    expect(result.current.health.state).toBe("disconnected");
    expect(result.current.manager).toBeNull();
  });

  it("provides health state", () => {
    const { result } = renderHook(() => useSSE(), { wrapper });

    expect(result.current.health).toBeDefined();
    expect(result.current.health.state).toBe("disconnected");
  });

  it("provides connect function", () => {
    const { result } = renderHook(() => useSSE(), { wrapper });

    expect(typeof result.current.connect).toBe("function");
  });

  it("provides disconnect function", () => {
    const { result } = renderHook(() => useSSE(), { wrapper });

    expect(typeof result.current.disconnect).toBe("function");
  });
});

describe("useJobEvents", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns disconnected health when disabled", () => {
    const onEvent = vi.fn();
    const { result } = renderHook(() =>
      useJobEvents(
        "http://127.0.0.1:47200",
        "test-token",
        "job-123",
        onEvent,
        false, // disabled
      ),
    );

    expect(result.current.state).toBe("disconnected");
  });

  it("returns disconnected health when no token", () => {
    const onEvent = vi.fn();
    const { result } = renderHook(() =>
      useJobEvents(
        "http://127.0.0.1:47200",
        "", // no token
        "job-123",
        onEvent,
        true,
      ),
    );

    expect(result.current.state).toBe("disconnected");
  });

  it("returns disconnected health when no job ID", () => {
    const onEvent = vi.fn();
    const { result } = renderHook(() =>
      useJobEvents(
        "http://127.0.0.1:47200",
        "test-token",
        null, // no job ID
        onEvent,
        true,
      ),
    );

    expect(result.current.state).toBe("disconnected");
  });
});
