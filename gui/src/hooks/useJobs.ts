/**
 * Hook for managing jobs.
 */

import { useCallback, useEffect, useState } from "react";
import type { JobResponse, JobConfig, JobReceipt } from "../api/types";
import { ApiClient } from "../api/client";

export interface UseJobsOptions {
  client: ApiClient | null;
  enabled?: boolean;
}

export interface UseJobsResult {
  jobs: JobResponse[];
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
  createJob: (
    config: JobConfig,
    idempotencyKey?: string,
  ) => Promise<JobResponse>;
  cancelJob: (jobId: string) => Promise<JobResponse>;
  getJob: (jobId: string) => Promise<JobResponse>;
  getReceipt: (jobId: string) => Promise<JobReceipt>;
}

export function useJobs(options: UseJobsOptions): UseJobsResult {
  const { client, enabled = true } = options;

  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(async () => {
    if (!client) return;

    setLoading(true);
    try {
      const jobList = await client.listJobs();
      setJobs(jobList);
      setError(null);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [client]);

  const createJob = useCallback(
    async (
      config: JobConfig,
      idempotencyKey?: string,
    ): Promise<JobResponse> => {
      if (!client) throw new Error("Client not initialized");

      const job = await client.createJob({
        config,
        idempotency_key: idempotencyKey,
      });

      // Refresh job list
      await refresh();

      return job;
    },
    [client, refresh],
  );

  const cancelJob = useCallback(
    async (jobId: string): Promise<JobResponse> => {
      if (!client) throw new Error("Client not initialized");

      const job = await client.cancelJob(jobId);

      // Refresh job list
      await refresh();

      return job;
    },
    [client, refresh],
  );

  const getJob = useCallback(
    async (jobId: string): Promise<JobResponse> => {
      if (!client) throw new Error("Client not initialized");
      return client.getJob(jobId);
    },
    [client],
  );

  const getReceipt = useCallback(
    async (jobId: string): Promise<JobReceipt> => {
      if (!client) throw new Error("Client not initialized");
      return client.getReceipt(jobId);
    },
    [client],
  );

  // Initial fetch
  useEffect(() => {
    if (enabled && client) {
      refresh();
    }
  }, [enabled, client, refresh]);

  return {
    jobs,
    loading,
    error,
    refresh,
    createJob,
    cancelJob,
    getJob,
    getReceipt,
  };
}
