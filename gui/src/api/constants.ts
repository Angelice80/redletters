/**
 * Connection constants - single source of truth for port/URL configuration.
 *
 * Sprint 22: Unify backend URL/port config across GUI.
 */

/** Default port for the Red Letters Engine Spine */
export const DEFAULT_PORT = 47200;

/** Ports to try when auto-detecting backend */
export const FALLBACK_PORTS = [47200, 8000, 5000];

/** Correct command to start the backend engine */
export const ENGINE_START_COMMAND = "redletters engine start";

/** Connection timeout for auto-detect (ms) */
export const CONNECTION_TIMEOUT_MS = 2000;

/** Build base URL from host and port */
export function buildBaseUrl(port: number, host: string = "127.0.0.1"): string {
  return `http://${host}:${port}`;
}

/** Result of auto-detecting backend */
export interface DetectedBackend {
  port: number;
  requiresAuth: boolean;
  version?: string;
}

/**
 * Auto-detect backend by trying common ports.
 *
 * Tries each port in FALLBACK_PORTS with a fast timeout.
 * Returns the first responsive port, or null if none found.
 */
export async function detectBackendPort(
  ports: number[] = FALLBACK_PORTS,
  timeoutMs: number = CONNECTION_TIMEOUT_MS,
): Promise<DetectedBackend | null> {
  for (const port of ports) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);

    try {
      // Try root endpoint first (no auth required per ADR-005)
      const url = `http://127.0.0.1:${port}/`;
      const response = await fetch(url, {
        method: "GET",
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (response.ok) {
        // Parse response for version info
        try {
          const data = await response.json();
          return {
            port,
            requiresAuth: false,
            version: data.version,
          };
        } catch {
          return { port, requiresAuth: false };
        }
      }

      if (response.status === 401) {
        // Server found but requires auth
        return { port, requiresAuth: true };
      }

      // Other status codes - not a valid backend, continue
    } catch {
      clearTimeout(timeout);
      // Network error or timeout - try next port
    }
  }

  return null;
}
