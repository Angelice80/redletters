/**
 * SSE event stream hook using fetch() with ReadableStream.
 *
 * IMPORTANT: We use fetch() instead of EventSource because EventSource
 * cannot send custom Authorization headers. This is critical for ADR-005
 * token-based authentication.
 *
 * Features:
 * - Manual SSE frame parsing
 * - Authorization header with Bearer token
 * - Last-Event-ID header for reconnection
 * - Client-side dedup by sequence_number
 * - Automatic reconnection with exponential backoff
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { SSEEvent } from "../api/types";

export interface UseEventStreamOptions {
  baseUrl: string;
  token: string;
  enabled?: boolean;
  onEvent?: (event: SSEEvent) => void;
  onError?: (error: Error) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  jobId?: string; // Filter events by job ID
  reconnectDelayMs?: number;
  maxReconnectDelayMs?: number;
}

export interface UseEventStreamResult {
  connected: boolean;
  lastEventId: number | null;
  reconnect: () => void;
  disconnect: () => void;
  testReconnection: () => Promise<{ gaps: number; dupes: number }>;
}

/**
 * Parse SSE frames from a text chunk.
 *
 * SSE format:
 * ```
 * event: <event_type>
 * id: <sequence_number>
 * data: <json>
 *
 * ```
 * Frames are separated by double newlines.
 */
function parseSSEFrames(
  text: string,
  buffer: string,
): {
  frames: Array<{ event?: string; id?: string; data?: string }>;
  remaining: string;
} {
  const combined = buffer + text;
  const frames: Array<{ event?: string; id?: string; data?: string }> = [];
  const parts = combined.split("\n\n");

  // Last part may be incomplete
  const remaining = parts.pop() ?? "";

  for (const part of parts) {
    if (!part.trim()) continue;

    const frame: { event?: string; id?: string; data?: string } = {};
    const lines = part.split("\n");

    for (const line of lines) {
      if (line.startsWith("event:")) {
        frame.event = line.slice(6).trim();
      } else if (line.startsWith("id:")) {
        frame.id = line.slice(3).trim();
      } else if (line.startsWith("data:")) {
        frame.data = line.slice(5).trim();
      }
    }

    if (frame.data) {
      frames.push(frame);
    }
  }

  return { frames, remaining };
}

export function useEventStream(
  options: UseEventStreamOptions,
): UseEventStreamResult {
  const {
    baseUrl,
    token,
    enabled = true,
    onEvent,
    onError,
    onConnect,
    onDisconnect,
    jobId,
    reconnectDelayMs = 2000, // Increased from 1000 to reduce noise when disconnected
    maxReconnectDelayMs = 30000,
  } = options;

  const [connected, setConnected] = useState(false);
  const [lastEventId, setLastEventId] = useState<number | null>(null);

  // Use ref for lastEventId to avoid triggering reconnections on every event
  const lastEventIdRef = useRef<number | null>(null);

  // Track seen sequence numbers for dedup
  const seenSequences = useRef<Set<number>>(new Set());
  const abortController = useRef<AbortController | null>(null);
  const reconnectAttempt = useRef(0);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Track if we're currently connecting to prevent duplicate connections
  const isConnecting = useRef(false);

  // Store connect function ref to avoid dependency issues (defined early, updated later)
  const connectRef = useRef<() => Promise<void>>(() => Promise.resolve());

  // For reconnection testing
  const preReconnectLastId = useRef<number | null>(null);
  const reconnectionTestPromise = useRef<{
    resolve: (result: { gaps: number; dupes: number }) => void;
    startId: number;
    dupes: number;
    events: number[];
  } | null>(null);

  const connect = useCallback(async () => {
    // Prevent duplicate connections
    if (isConnecting.current) {
      return;
    }

    if (abortController.current) {
      abortController.current.abort();
    }

    isConnecting.current = true;
    abortController.current = new AbortController();

    try {
      // Build URL with optional job filter
      let url = `${baseUrl}/v1/stream`;
      if (jobId) {
        url += `?job_id=${encodeURIComponent(jobId)}`;
      }

      // Build headers
      const headers: Record<string, string> = {
        Authorization: `Bearer ${token}`,
        Accept: "text/event-stream",
        "Cache-Control": "no-cache",
      };

      // Add Last-Event-ID for reconnection (use ref to avoid dependency issues)
      if (lastEventIdRef.current !== null) {
        headers["Last-Event-ID"] = String(lastEventIdRef.current);
      }

      const response = await fetch(url, {
        headers,
        signal: abortController.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error("No response body");
      }

      // Connected successfully
      isConnecting.current = false;
      setConnected(true);
      reconnectAttempt.current = 0;
      onConnect?.();

      // Read the stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const text = decoder.decode(value, { stream: true });
        const { frames, remaining } = parseSSEFrames(text, buffer);
        buffer = remaining;

        for (const frame of frames) {
          if (!frame.data) continue;

          try {
            const event = JSON.parse(frame.data) as SSEEvent;
            const seqNum = event.sequence_number;

            // Check for reconnection test
            if (reconnectionTestPromise.current) {
              reconnectionTestPromise.current.events.push(seqNum);
              if (seenSequences.current.has(seqNum)) {
                reconnectionTestPromise.current.dupes++;
              }
            }

            // Dedup by sequence number
            if (seenSequences.current.has(seqNum)) {
              continue; // Skip duplicate
            }
            seenSequences.current.add(seqNum);

            // Update last event ID (both ref and state)
            if (frame.id) {
              const id = parseInt(frame.id, 10);
              if (!isNaN(id)) {
                lastEventIdRef.current = id;
                setLastEventId(id);
              }
            }

            // Emit event
            onEvent?.(event);
          } catch (parseError) {
            console.error("Failed to parse SSE event:", parseError);
          }
        }
      }

      // Stream ended normally
      isConnecting.current = false;
      setConnected(false);
      onDisconnect?.();
    } catch (error) {
      isConnecting.current = false;

      if ((error as Error).name === "AbortError") {
        // Intentional disconnect
        return;
      }

      setConnected(false);
      onError?.(error as Error);
      onDisconnect?.();

      // Schedule reconnection with exponential backoff
      const delay = Math.min(
        reconnectDelayMs * Math.pow(2, reconnectAttempt.current),
        maxReconnectDelayMs,
      );
      reconnectAttempt.current++;

      reconnectTimeout.current = setTimeout(() => {
        if (enabled) {
          connect();
        }
      }, delay);
    }
  }, [
    baseUrl,
    token,
    enabled,
    onEvent,
    onError,
    onConnect,
    onDisconnect,
    jobId,
    // Note: lastEventId removed - we use lastEventIdRef to avoid reconnection loops
    reconnectDelayMs,
    maxReconnectDelayMs,
  ]);

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
    if (abortController.current) {
      abortController.current.abort();
      abortController.current = null;
    }
    setConnected(false);
  }, []);

  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttempt.current = 0;
    isConnecting.current = false; // Reset connecting state
    connectRef.current();
  }, [disconnect]);

  /**
   * Test reconnection for gap/dupe detection.
   * Disconnects, waits 2s, reconnects with saved lastEventId.
   */
  const testReconnection = useCallback(async (): Promise<{
    gaps: number;
    dupes: number;
  }> => {
    return new Promise((resolve) => {
      // Save current state
      preReconnectLastId.current = lastEventId;

      // Set up test tracking
      reconnectionTestPromise.current = {
        resolve,
        startId: lastEventId ?? 0,
        dupes: 0,
        events: [],
      };

      // Disconnect
      disconnect();

      // Wait 2 seconds
      setTimeout(() => {
        // Reconnect using ref
        isConnecting.current = false;
        connectRef.current();

        // Wait for some events, then analyze
        setTimeout(() => {
          const test = reconnectionTestPromise.current;
          if (!test) {
            resolve({ gaps: 0, dupes: 0 });
            return;
          }

          // Calculate gaps (missing sequence numbers)
          const events = test.events.sort((a, b) => a - b);
          let gaps = 0;
          for (let i = 1; i < events.length; i++) {
            const expected = events[i - 1] + 1;
            if (events[i] > expected) {
              gaps += events[i] - expected;
            }
          }

          reconnectionTestPromise.current = null;
          resolve({ gaps, dupes: test.dupes });
        }, 3000); // Wait 3 seconds for events
      }, 2000);
    });
  }, [lastEventId, disconnect]);

  // Update connect ref after connect is defined
  connectRef.current = connect;

  // Connect when enabled - use stable dependencies only
  useEffect(() => {
    if (enabled && token) {
      connectRef.current();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
    // Only re-run when enabled/token/baseUrl change, not on every connect recreation
  }, [enabled, token, baseUrl, disconnect]);

  return {
    connected,
    lastEventId,
    reconnect,
    disconnect,
    testReconnection,
  };
}
