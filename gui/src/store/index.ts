/**
 * Zustand store for Red Letters GUI state.
 *
 * Manages:
 * - Connection state and heartbeat tracking
 * - Jobs and their real-time updates
 * - Log entries from SSE events
 * - Application settings
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  ConnectionState,
  EngineStatus,
  JobResponse,
  JobLog,
  SSEEvent,
  EngineHeartbeat,
  JobStateChanged,
  JobProgress,
} from "../api/types";

// --- Types ---

export interface JobLogEntry {
  timestamp: string;
  level: string;
  subsystem: string;
  message: string;
  sequenceNumber: number;
}

export interface Settings {
  enginePort: number;
  integritySizeThreshold: number; // MB
  sessionId: string; // UUID for translation session tracking
}

export interface AppState {
  // Connection
  connectionState: ConnectionState;
  lastHeartbeat: number | null; // Unix timestamp ms
  engineStatus: EngineStatus | null;

  // Jobs
  jobs: Map<string, JobResponse>;
  jobLogs: Map<string, JobLogEntry[]>;

  // Deduplication
  seenSequences: Set<number>;

  // Settings (persisted)
  settings: Settings;

  // Actions
  setConnectionState: (state: ConnectionState) => void;
  updateHeartbeat: (heartbeat: EngineHeartbeat) => void;
  setEngineStatus: (status: EngineStatus | null) => void;

  updateJob: (job: JobResponse) => void;
  setJobs: (jobs: JobResponse[]) => void;
  removeJob: (jobId: string) => void;

  addLog: (jobId: string, log: JobLogEntry) => void;
  clearLogs: (jobId: string) => void;

  processEvent: (event: SSEEvent) => boolean; // Returns true if processed, false if dupe

  updateSettings: (settings: Partial<Settings>) => void;

  // For reconnection testing
  getSeenCount: () => number;
  clearSeen: () => void;
}

// --- Constants ---

const HEARTBEAT_STALE_MS = 10000; // 10 seconds = degraded
const HEARTBEAT_DEAD_MS = 30000; // 30 seconds = disconnected

// Generate a UUID for session tracking
function generateSessionId(): string {
  // Use crypto.randomUUID if available, otherwise fallback
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for older environments
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

const DEFAULT_SETTINGS: Settings = {
  enginePort: 47200,
  integritySizeThreshold: 100, // 100 MB
  sessionId: generateSessionId(),
};

// --- Store ---

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Initial state
      connectionState: "disconnected",
      lastHeartbeat: null,
      engineStatus: null,
      jobs: new Map(),
      jobLogs: new Map(),
      seenSequences: new Set(),
      settings: DEFAULT_SETTINGS,

      // Connection actions
      setConnectionState: (state) => set({ connectionState: state }),

      updateHeartbeat: (heartbeat) => {
        const now = Date.now();
        set({
          lastHeartbeat: now,
          connectionState: "connected",
          engineStatus: get().engineStatus
            ? {
                ...get().engineStatus!,
                health: heartbeat.health,
                active_jobs: heartbeat.active_jobs,
                queue_depth: heartbeat.queue_depth,
              }
            : null,
        });
      },

      setEngineStatus: (status) => set({ engineStatus: status }),

      // Job actions
      updateJob: (job) => {
        const jobs = new Map(get().jobs);
        jobs.set(job.job_id, job);
        set({ jobs });
      },

      setJobs: (jobList) => {
        const jobs = new Map<string, JobResponse>();
        for (const job of jobList) {
          jobs.set(job.job_id, job);
        }
        set({ jobs });
      },

      removeJob: (jobId) => {
        const jobs = new Map(get().jobs);
        jobs.delete(jobId);
        const jobLogs = new Map(get().jobLogs);
        jobLogs.delete(jobId);
        set({ jobs, jobLogs });
      },

      // Log actions
      addLog: (jobId, log) => {
        const jobLogs = new Map(get().jobLogs);
        const logs = jobLogs.get(jobId) ?? [];
        jobLogs.set(jobId, [...logs, log]);
        set({ jobLogs });
      },

      clearLogs: (jobId) => {
        const jobLogs = new Map(get().jobLogs);
        jobLogs.delete(jobId);
        set({ jobLogs });
      },

      // Event processing with dedup
      processEvent: (event) => {
        const { seenSequences } = get();

        // Dedup check
        if (seenSequences.has(event.sequence_number)) {
          return false;
        }

        // Mark as seen
        const newSeen = new Set(seenSequences);
        newSeen.add(event.sequence_number);
        set({ seenSequences: newSeen });

        // Process by event type
        switch (event.event_type) {
          case "engine.heartbeat":
            get().updateHeartbeat(event as EngineHeartbeat);
            break;

          case "job.state_changed": {
            const stateEvent = event as JobStateChanged;
            const jobs = get().jobs;
            const existingJob = jobs.get(stateEvent.job_id);
            if (existingJob) {
              get().updateJob({
                ...existingJob,
                state: stateEvent.new_state,
              });
            }
            break;
          }

          case "job.progress": {
            const progressEvent = event as JobProgress;
            const jobs = get().jobs;
            const existingJob = jobs.get(progressEvent.job_id);
            if (existingJob) {
              get().updateJob({
                ...existingJob,
                progress_percent: progressEvent.progress_percent,
                progress_phase: progressEvent.phase,
              });
            }
            break;
          }

          case "job.log": {
            const logEvent = event as JobLog;
            get().addLog(logEvent.job_id, {
              timestamp: logEvent.timestamp_utc,
              level: logEvent.level,
              subsystem: logEvent.subsystem,
              message: logEvent.message,
              sequenceNumber: logEvent.sequence_number,
            });
            break;
          }
        }

        return true;
      },

      // Settings
      updateSettings: (newSettings) => {
        set({ settings: { ...get().settings, ...newSettings } });
      },

      // Utility
      getSeenCount: () => get().seenSequences.size,
      clearSeen: () => set({ seenSequences: new Set() }),
    }),
    {
      name: "redletters-storage",
      partialize: (state) => ({
        settings: state.settings,
      }),
    },
  ),
);

// --- Selectors ---

export const selectConnectionState = (state: AppState) => state.connectionState;
export const selectEngineStatus = (state: AppState) => state.engineStatus;
export const selectJobs = (state: AppState) => Array.from(state.jobs.values());
export const selectJob = (state: AppState, jobId: string) =>
  state.jobs.get(jobId);
export const selectJobLogs = (state: AppState, jobId: string) =>
  state.jobLogs.get(jobId) ?? [];
export const selectSettings = (state: AppState) => state.settings;

/**
 * Check connection health based on heartbeat staleness.
 */
export function checkConnectionHealth(
  lastHeartbeat: number | null,
  sseConnected: boolean,
): ConnectionState {
  if (!sseConnected) {
    return "disconnected";
  }

  if (!lastHeartbeat) {
    return "connected"; // Just connected, waiting for first heartbeat
  }

  const elapsed = Date.now() - lastHeartbeat;

  if (elapsed > HEARTBEAT_DEAD_MS) {
    return "disconnected";
  }

  if (elapsed > HEARTBEAT_STALE_MS) {
    return "degraded";
  }

  return "connected";
}
