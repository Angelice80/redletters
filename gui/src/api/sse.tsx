/**
 * SSE Manager - Shared SSE subscription manager for job events.
 *
 * Sprint 19: Jobs-native GUI
 *
 * Features:
 * - Single shared manager instance via React Context
 * - Connection health state (connected/reconnecting/disconnected)
 * - Automatic reconnect with exponential backoff
 * - Job-specific subscriptions with optional filtering
 * - Exposes diagnostics for ConnectionBadge
 */

import {
  createContext,
  useContext,
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { SSEEvent, SSEHealthState, SSEHealthInfo } from "./types";

// --- SSE Frame Parser ---

interface SSEFrame {
  event?: string;
  id?: string;
  data?: string;
}

/**
 * Parse SSE frames from text chunks.
 * SSE format: event/id/data fields separated by double newlines.
 */
function parseSSEFrames(
  text: string,
  buffer: string,
): { frames: SSEFrame[]; remaining: string } {
  const combined = buffer + text;
  const frames: SSEFrame[] = [];
  const parts = combined.split("\n\n");

  // Last part may be incomplete
  const remaining = parts.pop() ?? "";

  for (const part of parts) {
    if (!part.trim()) continue;

    const frame: SSEFrame = {};
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

// --- Bounded Dedup Buffer ---

/**
 * Bounded set for SSE sequence deduplication.
 * Uses a ring buffer approach: when maxSize is exceeded, oldest entries are pruned.
 * Exported for testing.
 */
export class BoundedSequenceSet {
  private _set = new Set<number>();
  private _queue: number[] = [];
  private _maxSize: number;

  constructor(maxSize = 5000) {
    this._maxSize = maxSize;
  }

  has(seq: number): boolean {
    return this._set.has(seq);
  }

  add(seq: number): void {
    if (this._set.has(seq)) return;

    this._set.add(seq);
    this._queue.push(seq);

    // Prune if over capacity
    while (this._queue.length > this._maxSize) {
      const oldest = this._queue.shift();
      if (oldest !== undefined) {
        this._set.delete(oldest);
      }
    }
  }

  clear(): void {
    this._set.clear();
    this._queue = [];
  }

  get size(): number {
    return this._set.size;
  }
}

// --- SSE Manager Class ---

export interface SSEManagerOptions {
  baseUrl: string;
  token: string;
  onEvent?: (event: SSEEvent) => void;
  onHealthChange?: (health: SSEHealthInfo) => void;
  reconnectDelayMs?: number;
  maxReconnectDelayMs?: number;
  maxDedupSize?: number;
}

export class SSEManager {
  private _baseUrl: string;
  private _token: string;
  private _onEvent?: (event: SSEEvent) => void;
  private _onHealthChange?: (health: SSEHealthInfo) => void;
  private _reconnectDelayMs: number;
  private _maxReconnectDelayMs: number;

  private _state: SSEHealthState = "disconnected";
  private _lastEventId: number | null = null;
  private _lastMessageAt: Date | null = null;
  private _reconnectAttempt = 0;
  private _abortController: AbortController | null = null;
  private _reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private _seenSequences: BoundedSequenceSet;
  private _jobId: string | null = null;

  constructor(options: SSEManagerOptions) {
    this._baseUrl = options.baseUrl.replace(/\/$/, "");
    this._token = options.token;
    this._onEvent = options.onEvent;
    this._onHealthChange = options.onHealthChange;
    this._reconnectDelayMs = options.reconnectDelayMs ?? 1000;
    this._maxReconnectDelayMs = options.maxReconnectDelayMs ?? 30000;
    this._seenSequences = new BoundedSequenceSet(options.maxDedupSize ?? 5000);
  }

  get health(): SSEHealthInfo {
    return {
      state: this._state,
      baseUrl: this._baseUrl,
      lastEventId: this._lastEventId,
      lastMessageAt: this._lastMessageAt,
      reconnectAttempt: this._reconnectAttempt,
    };
  }

  get state(): SSEHealthState {
    return this._state;
  }

  get lastEventId(): number | null {
    return this._lastEventId;
  }

  get lastMessageAt(): Date | null {
    return this._lastMessageAt;
  }

  updateToken(token: string): void {
    this._token = token;
  }

  updateBaseUrl(url: string): void {
    this._baseUrl = url.replace(/\/$/, "");
  }

  private _emitHealth(): void {
    this._onHealthChange?.(this.health);
  }

  private _setState(state: SSEHealthState): void {
    if (this._state !== state) {
      this._state = state;
      this._emitHealth();
    }
  }

  /**
   * Connect to SSE stream, optionally filtering by job ID.
   */
  async connect(jobId?: string): Promise<void> {
    // Abort any existing connection
    this.disconnect();

    this._jobId = jobId ?? null;
    this._abortController = new AbortController();
    this._setState("reconnecting");

    try {
      // Build URL
      let url = `${this._baseUrl}/v1/stream`;
      if (jobId) {
        url += `?job_id=${encodeURIComponent(jobId)}`;
      }

      // Build headers
      const headers: Record<string, string> = {
        Authorization: `Bearer ${this._token}`,
        Accept: "text/event-stream",
        "Cache-Control": "no-cache",
      };

      // Add Last-Event-ID for reconnection
      if (this._lastEventId !== null) {
        headers["Last-Event-ID"] = String(this._lastEventId);
      }

      const response = await fetch(url, {
        headers,
        signal: this._abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error("No response body");
      }

      // Connected successfully
      this._setState("connected");
      this._reconnectAttempt = 0;

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

            // Update last message time
            this._lastMessageAt = new Date();

            // Dedup by sequence number
            if (this._seenSequences.has(seqNum)) {
              continue;
            }
            this._seenSequences.add(seqNum);

            // Update last event ID
            if (frame.id) {
              const id = parseInt(frame.id, 10);
              if (!isNaN(id)) {
                this._lastEventId = id;
              }
            }

            // Emit event
            this._onEvent?.(event);
            this._emitHealth();
          } catch (parseError) {
            console.error("Failed to parse SSE event:", parseError);
          }
        }
      }

      // Stream ended normally
      this._setState("disconnected");
    } catch (error) {
      if ((error as Error).name === "AbortError") {
        // Intentional disconnect
        return;
      }

      this._setState("disconnected");

      // Schedule reconnection with exponential backoff
      const delay = Math.min(
        this._reconnectDelayMs * Math.pow(2, this._reconnectAttempt),
        this._maxReconnectDelayMs,
      );
      this._reconnectAttempt++;
      this._setState("reconnecting");

      this._reconnectTimeout = setTimeout(() => {
        this.connect(this._jobId ?? undefined);
      }, delay);
    }
  }

  /**
   * Disconnect from SSE stream.
   */
  disconnect(): void {
    if (this._reconnectTimeout) {
      clearTimeout(this._reconnectTimeout);
      this._reconnectTimeout = null;
    }
    if (this._abortController) {
      this._abortController.abort();
      this._abortController = null;
    }
    this._setState("disconnected");
  }

  /**
   * Clear seen sequences (useful for testing reconnection).
   */
  clearSeenSequences(): void {
    this._seenSequences.clear();
  }
}

// --- React Context ---

interface SSEContextValue {
  manager: SSEManager | null;
  health: SSEHealthInfo;
  connect: (jobId?: string) => void;
  disconnect: () => void;
}

const defaultHealth: SSEHealthInfo = {
  state: "disconnected",
  baseUrl: "",
  lastEventId: null,
  lastMessageAt: null,
  reconnectAttempt: 0,
};

const SSEContext = createContext<SSEContextValue>({
  manager: null,
  health: defaultHealth,
  connect: () => {},
  disconnect: () => {},
});

export interface SSEProviderProps {
  baseUrl: string;
  token: string;
  onEvent?: (event: SSEEvent) => void;
  children: ReactNode;
  autoConnect?: boolean;
}

/**
 * SSE Provider - Provides shared SSE manager to the component tree.
 */
export function SSEProvider({
  baseUrl,
  token,
  onEvent,
  children,
  autoConnect = true,
}: SSEProviderProps) {
  const [health, setHealth] = useState<SSEHealthInfo>(defaultHealth);
  const managerRef = useRef<SSEManager | null>(null);

  // Create/update manager when config changes
  useEffect(() => {
    if (!token) {
      managerRef.current?.disconnect();
      managerRef.current = null;
      setHealth(defaultHealth);
      return;
    }

    if (managerRef.current) {
      // Update existing manager
      managerRef.current.updateBaseUrl(baseUrl);
      managerRef.current.updateToken(token);
    } else {
      // Create new manager
      managerRef.current = new SSEManager({
        baseUrl,
        token,
        onEvent,
        onHealthChange: setHealth,
      });

      if (autoConnect) {
        managerRef.current.connect();
      }
    }

    return () => {
      managerRef.current?.disconnect();
    };
  }, [baseUrl, token, onEvent, autoConnect]);

  const connect = useCallback((jobId?: string) => {
    managerRef.current?.connect(jobId);
  }, []);

  const disconnect = useCallback(() => {
    managerRef.current?.disconnect();
  }, []);

  const value: SSEContextValue = {
    manager: managerRef.current,
    health,
    connect,
    disconnect,
  };

  return <SSEContext.Provider value={value}>{children}</SSEContext.Provider>;
}

/**
 * Hook to access SSE manager and health state.
 */
export function useSSE(): SSEContextValue {
  return useContext(SSEContext);
}

/**
 * Hook to subscribe to job-specific events.
 *
 * Creates a separate SSE connection filtered by job ID.
 * Cleans up when component unmounts or job ID changes.
 */
export function useJobEvents(
  baseUrl: string,
  token: string,
  jobId: string | null,
  onEvent: (event: SSEEvent) => void,
  enabled = true,
): SSEHealthInfo {
  const [health, setHealth] = useState<SSEHealthInfo>(defaultHealth);
  const managerRef = useRef<SSEManager | null>(null);

  useEffect(() => {
    if (!enabled || !token || !jobId) {
      managerRef.current?.disconnect();
      managerRef.current = null;
      setHealth(defaultHealth);
      return;
    }

    // Create job-specific manager
    managerRef.current = new SSEManager({
      baseUrl,
      token,
      onEvent,
      onHealthChange: setHealth,
    });

    // Connect with job filter
    managerRef.current.connect(jobId);

    return () => {
      managerRef.current?.disconnect();
      managerRef.current = null;
    };
  }, [baseUrl, token, jobId, onEvent, enabled]);

  return health;
}
