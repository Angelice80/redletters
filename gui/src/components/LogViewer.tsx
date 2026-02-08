/**
 * LogViewer component - Scrolling log viewer with pause and search.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { JobLogEntry } from "../store";

interface LogViewerProps {
  logs: JobLogEntry[];
  maxHeight?: string;
}

const LEVEL_COLORS: Record<string, string> = {
  trace: "var(--rl-text-dim)",
  debug: "var(--rl-text-muted)",
  info: "var(--rl-primary)",
  warn: "var(--rl-warning)",
  error: "var(--rl-error)",
};

export function LogViewer({ logs, maxHeight = "400px" }: LogViewerProps) {
  const [paused, setPaused] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Filter logs by search term
  const filteredLogs = searchTerm
    ? logs.filter(
        (log) =>
          log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
          log.subsystem.toLowerCase().includes(searchTerm.toLowerCase()),
      )
    : logs;

  // Auto-scroll to bottom when not paused
  useEffect(() => {
    if (!paused && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, paused]);

  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;

    // Auto-pause when user scrolls up
    if (!isAtBottom && !paused) {
      setPaused(true);
    }
  }, [paused]);

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString("en-US", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        fractionalSecondDigits: 3,
      } as Intl.DateTimeFormatOptions);
    } catch {
      return timestamp;
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      {/* Controls */}
      <div
        style={{
          display: "flex",
          gap: "12px",
          alignItems: "center",
          padding: "8px",
          backgroundColor: "var(--rl-bg-card)",
          borderRadius: "4px",
        }}
      >
        <button
          onClick={() => {
            setPaused(!paused);
            if (paused && bottomRef.current) {
              bottomRef.current.scrollIntoView({ behavior: "smooth" });
            }
          }}
          style={{
            padding: "4px 12px",
            borderRadius: "4px",
            border: "none",
            backgroundColor: paused
              ? "var(--rl-success)"
              : "var(--rl-text-dim)",
            color: "white",
            cursor: "pointer",
            fontSize: "var(--rl-fs-sm)",
            fontWeight: 500,
          }}
        >
          {paused ? "Resume" : "Pause"}
        </button>

        <input
          type="text"
          placeholder="Search logs..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            flex: 1,
            padding: "4px 8px",
            borderRadius: "4px",
            border: "1px solid #4a4a6a",
            backgroundColor: "var(--rl-bg-app)",
            color: "var(--rl-text)",
            fontSize: "var(--rl-fs-sm)",
          }}
        />

        <span style={{ fontSize: "var(--rl-fs-sm)", color: "var(--rl-text-muted)" }}>
          {filteredLogs.length} / {logs.length} logs
        </span>
      </div>

      {/* Log list */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        style={{
          maxHeight,
          overflowY: "auto",
          backgroundColor: "var(--rl-bg-app)",
          borderRadius: "4px",
          fontFamily: "var(--rl-font-mono)",
          fontSize: "var(--rl-fs-sm)",
        }}
      >
        {filteredLogs.length === 0 ? (
          <div
            style={{
              padding: "16px",
              color: "var(--rl-text-dim)",
              textAlign: "center",
            }}
          >
            {logs.length === 0 ? "No logs yet" : "No matching logs"}
          </div>
        ) : (
          filteredLogs.map((log, index) => (
            <div
              key={`${log.sequenceNumber}-${index}`}
              style={{
                display: "flex",
                padding: "4px 8px",
                borderBottom: "1px solid var(--rl-bg-card)",
                gap: "8px",
              }}
            >
              <span style={{ color: "var(--rl-text-dim)", minWidth: "85px" }}>
                {formatTimestamp(log.timestamp)}
              </span>
              <span
                style={{
                  color: LEVEL_COLORS[log.level] ?? "var(--rl-text-muted)",
                  minWidth: "50px",
                  textTransform: "uppercase",
                  fontWeight: 600,
                }}
              >
                {log.level}
              </span>
              <span style={{ color: "#8b5cf6", minWidth: "100px" }}>
                [{log.subsystem}]
              </span>
              <span style={{ color: "var(--rl-text)", flex: 1 }}>
                {log.message}
              </span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {paused && (
        <div
          style={{
            textAlign: "center",
            padding: "4px",
            backgroundColor: "var(--rl-warning)",
            color: "var(--rl-bg-app)",
            borderRadius: "4px",
            fontSize: "var(--rl-fs-sm)",
            fontWeight: 500,
          }}
        >
          Auto-scroll paused. Click Resume to continue.
        </div>
      )}
    </div>
  );
}
