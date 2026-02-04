/**
 * ApiContract - Single source of truth for API endpoint paths.
 *
 * Sprint 17: Contract-first GUI routing.
 *
 * This module:
 * - Stores capabilities fetched from /v1/capabilities
 * - Provides typed endpoint builders derived from capabilities
 * - Falls back to hardcoded defaults if capabilities unavailable
 * - Centralizes base URL management
 */

import type { ApiCapabilities } from "./types";

/**
 * Default endpoint paths (fallback when capabilities unavailable).
 * These MUST match the backend's actual routes.
 */
export const DEFAULT_ENDPOINTS = {
  // Engine spine routes (always /v1 prefixed)
  engine_status: "/v1/engine/status",
  capabilities: "/v1/capabilities",
  stream: "/v1/stream",
  jobs: "/v1/jobs",
  gates_pending: "/v1/gates/pending",
  run_scholarly: "/v1/run/scholarly",
  diagnostics_export: "/v1/diagnostics/export",
  engine_shutdown: "/v1/engine/shutdown",

  // API routes (no /v1 prefix per current backend)
  translate: "/translate",
  acknowledge: "/acknowledge",
  acknowledge_multi: "/acknowledge/multi",
  sources: "/sources",
  sources_status: "/sources/status",
  sources_install: "/sources/install",
  sources_uninstall: "/sources/uninstall",
  sources_license: "/sources/license",
  variants_dossier: "/variants/dossier",
} as const;

export type EndpointKey = keyof typeof DEFAULT_ENDPOINTS;

/**
 * ApiContract manages base URL and endpoint path resolution.
 *
 * Usage:
 * ```ts
 * const contract = new ApiContract("http://127.0.0.1:47200");
 * await contract.loadCapabilities();
 *
 * const url = contract.url("translate"); // -> "http://127.0.0.1:47200/translate"
 * const path = contract.path("translate"); // -> "/translate"
 * ```
 */
export class ApiContract {
  private _baseUrl: string;
  private _capabilities: ApiCapabilities | null = null;

  constructor(baseUrl: string = "http://127.0.0.1:47200") {
    this._baseUrl = baseUrl.replace(/\/$/, "");
  }

  /**
   * Get the current base URL.
   */
  get baseUrl(): string {
    return this._baseUrl;
  }

  /**
   * Update the base URL (e.g., when port changes).
   */
  setBaseUrl(url: string): void {
    this._baseUrl = url.replace(/\/$/, "");
  }

  /**
   * Get the loaded capabilities (null if not loaded).
   */
  get capabilities(): ApiCapabilities | null {
    return this._capabilities;
  }

  /**
   * Store capabilities (called after fetching from /v1/capabilities).
   */
  setCapabilities(caps: ApiCapabilities): void {
    this._capabilities = caps;
  }

  /**
   * Clear stored capabilities.
   */
  clearCapabilities(): void {
    this._capabilities = null;
  }

  /**
   * Check if capabilities are loaded.
   */
  get hasCapabilities(): boolean {
    return this._capabilities !== null;
  }

  /**
   * Get endpoint path from capabilities or fallback to defaults.
   *
   * @param key - Endpoint key (e.g., "translate", "sources_status")
   * @returns Path string (e.g., "/translate", "/sources/status")
   */
  path(key: EndpointKey): string {
    // Try to get from capabilities first
    if (this._capabilities?.endpoints) {
      const capsKey = key as keyof typeof this._capabilities.endpoints;
      const capsPath = this._capabilities.endpoints[capsKey];
      if (capsPath) {
        return capsPath;
      }
    }

    // Fallback to defaults
    return DEFAULT_ENDPOINTS[key];
  }

  /**
   * Get full URL for an endpoint.
   *
   * @param key - Endpoint key
   * @param pathSuffix - Optional suffix to append (e.g., "/{job_id}")
   * @returns Full URL (e.g., "http://127.0.0.1:47200/translate")
   */
  url(key: EndpointKey, pathSuffix?: string): string {
    const basePath = this.path(key);
    const fullPath = pathSuffix ? `${basePath}${pathSuffix}` : basePath;
    return `${this._baseUrl}${fullPath}`;
  }

  /**
   * Get URL with query parameters.
   *
   * @param key - Endpoint key
   * @param params - Query parameters
   * @returns Full URL with query string
   */
  urlWithParams(
    key: EndpointKey,
    params: URLSearchParams | Record<string, string>,
  ): string {
    const searchParams =
      params instanceof URLSearchParams ? params : new URLSearchParams(params);
    const queryString = searchParams.toString();
    const baseUrl = this.url(key);
    return queryString ? `${baseUrl}?${queryString}` : baseUrl;
  }

  // === Typed endpoint builders ===

  /**
   * Get translate endpoint path.
   */
  translate(): string {
    return this.path("translate");
  }

  /**
   * Get acknowledge endpoint path.
   */
  acknowledge(): string {
    return this.path("acknowledge");
  }

  /**
   * Get acknowledge/multi endpoint path.
   */
  acknowledgeMulti(): string {
    return this.path("acknowledge_multi");
  }

  /**
   * Get sources endpoint path.
   */
  sources(): string {
    return this.path("sources");
  }

  /**
   * Get sources/status endpoint path.
   */
  sourcesStatus(): string {
    return this.path("sources_status");
  }

  /**
   * Get sources/install endpoint path.
   */
  sourcesInstall(): string {
    return this.path("sources_install");
  }

  /**
   * Get sources/uninstall endpoint path.
   */
  sourcesUninstall(): string {
    return this.path("sources_uninstall");
  }

  /**
   * Get sources/license endpoint path.
   */
  sourcesLicense(): string {
    return this.path("sources_license");
  }

  /**
   * Get variants/dossier endpoint path.
   */
  variantsDossier(): string {
    return this.path("variants_dossier");
  }

  /**
   * Get gates/pending endpoint path.
   */
  gatesPending(): string {
    return this.path("gates_pending");
  }

  /**
   * Get run/scholarly endpoint path.
   */
  runScholarly(): string {
    return this.path("run_scholarly");
  }

  /**
   * Get jobs endpoint path.
   */
  jobs(): string {
    return this.path("jobs");
  }

  /**
   * Get jobs/{id} endpoint URL.
   */
  jobById(jobId: string): string {
    return `${this.path("jobs")}/${jobId}`;
  }

  /**
   * Get jobs/{id}/receipt endpoint URL.
   */
  jobReceipt(jobId: string): string {
    return `${this.path("jobs")}/${jobId}/receipt`;
  }

  /**
   * Get jobs/{id}/cancel endpoint URL.
   */
  jobCancel(jobId: string): string {
    return `${this.path("jobs")}/${jobId}/cancel`;
  }

  /**
   * Get engine/status endpoint path.
   */
  engineStatus(): string {
    return this.path("engine_status");
  }

  /**
   * Get capabilities endpoint path.
   */
  capabilitiesPath(): string {
    return this.path("capabilities");
  }

  /**
   * Get stream endpoint path.
   */
  stream(): string {
    return this.path("stream");
  }

  /**
   * Sprint 19: Get full URL for job-specific SSE stream.
   *
   * @param jobId - Job ID to filter events for
   * @returns Full URL with job_id query param
   */
  jobStreamUrl(jobId: string): string {
    const baseUrl = this.url("stream");
    return `${baseUrl}?job_id=${encodeURIComponent(jobId)}`;
  }

  /**
   * Sprint 19: Get full URL for global SSE stream (no job filter).
   *
   * @returns Full stream URL
   */
  globalStreamUrl(): string {
    return this.url("stream");
  }

  /**
   * Get diagnostics/export endpoint path.
   */
  diagnosticsExport(): string {
    return this.path("diagnostics_export");
  }

  /**
   * Get engine/shutdown endpoint path.
   */
  engineShutdown(): string {
    return this.path("engine_shutdown");
  }

  // === Diagnostics helpers ===

  /**
   * Get a snapshot of the contract state for diagnostics.
   */
  getDiagnosticsSnapshot(): ContractDiagnostics {
    return {
      baseUrl: this._baseUrl,
      hasCapabilities: this.hasCapabilities,
      capabilities: this._capabilities
        ? {
            version: this._capabilities.version,
            api_version: this._capabilities.api_version,
            min_gui_version: this._capabilities.min_gui_version,
            features: this._capabilities.features,
            initialized: this._capabilities.initialized,
          }
        : null,
      resolvedEndpoints: {
        translate: this.translate(),
        sources: this.sources(),
        sources_status: this.sourcesStatus(),
        gates_pending: this.gatesPending(),
        run_scholarly: this.runScholarly(),
        jobs: this.jobs(),
      },
    };
  }
}

/**
 * Contract diagnostics snapshot for error reporting.
 */
export interface ContractDiagnostics {
  baseUrl: string;
  hasCapabilities: boolean;
  capabilities: {
    version: string;
    api_version: string;
    min_gui_version: string;
    features: string[];
    initialized: boolean;
  } | null;
  resolvedEndpoints: Record<string, string>;
}

/**
 * Create a contract instance with default configuration.
 */
export function createApiContract(port: number = 47200): ApiContract {
  return new ApiContract(`http://127.0.0.1:${port}`);
}
