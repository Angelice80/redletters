/**
 * Hook for fetching and polling engine status.
 */

import { useCallback, useEffect, useState } from "react";
import type { EngineStatus } from "../api/types";
import { ApiClient } from "../api/client";

export interface UseEngineStatusOptions {
  client: ApiClient | null;
  pollInterval?: number; // ms, 0 to disable polling
  enabled?: boolean;
}

export interface UseEngineStatusResult {
  status: EngineStatus | null;
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
}

export function useEngineStatus(
  options: UseEngineStatusOptions,
): UseEngineStatusResult {
  const { client, pollInterval = 0, enabled = true } = options;

  const [status, setStatus] = useState<EngineStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(async () => {
    if (!client) return;

    setLoading(true);
    try {
      const newStatus = await client.getStatus();
      setStatus(newStatus);
      setError(null);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [client]);

  // Initial fetch
  useEffect(() => {
    if (enabled && client) {
      refresh();
    }
  }, [enabled, client, refresh]);

  // Polling
  useEffect(() => {
    if (!enabled || !client || pollInterval <= 0) return;

    const interval = setInterval(refresh, pollInterval);
    return () => clearInterval(interval);
  }, [enabled, client, pollInterval, refresh]);

  return { status, loading, error, refresh };
}
