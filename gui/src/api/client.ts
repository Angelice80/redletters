/**
 * HTTP client for Engine Spine API.
 *
 * Uses fetch with Bearer token authentication.
 * All methods handle errors and return typed responses.
 */

import type {
  EngineStatus,
  JobCreateRequest,
  JobResponse,
  JobReceipt,
  DiagnosticsReport,
  ErrorResponse,
  TranslateRequest,
  TranslateResult,
  AcknowledgeRequest,
  AcknowledgeResponse,
} from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface ApiClientConfig {
  baseUrl: string;
  token: string;
}

export class ApiClient {
  private baseUrl: string;
  private token: string;

  constructor(config: ApiClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, "");
    this.token = config.token;
  }

  /**
   * Update the auth token (e.g., after refresh).
   */
  setToken(token: string): void {
    this.token = token;
  }

  /**
   * Update the base URL (e.g., if port changes).
   */
  setBaseUrl(url: string): void {
    this.baseUrl = url.replace(/\/$/, "");
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers: Record<string, string> = {
      Authorization: `Bearer ${this.token}`,
      "Content-Type": "application/json",
    };

    const response = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      let errorData: ErrorResponse | null = null;
      try {
        errorData = await response.json();
      } catch {
        // Response may not be JSON
      }

      throw new ApiError(
        response.status,
        errorData?.code ?? "unknown",
        errorData?.message ?? response.statusText,
        errorData?.details,
      );
    }

    // Handle empty responses
    const text = await response.text();
    if (!text) {
      return {} as T;
    }

    return JSON.parse(text) as T;
  }

  // --- Engine Status ---

  /**
   * GET /v1/engine/status - Get engine status.
   */
  async getStatus(): Promise<EngineStatus> {
    return this.request<EngineStatus>("GET", "/v1/engine/status");
  }

  // --- Job Management ---

  /**
   * POST /v1/jobs - Create a new job.
   */
  async createJob(request: JobCreateRequest): Promise<JobResponse> {
    return this.request<JobResponse>("POST", "/v1/jobs", request);
  }

  /**
   * GET /v1/jobs - List jobs.
   */
  async listJobs(states?: string[], limit?: number): Promise<JobResponse[]> {
    const params = new URLSearchParams();
    if (states?.length) {
      states.forEach((s) => params.append("state", s));
    }
    if (limit) {
      params.set("limit", limit.toString());
    }
    const query = params.toString();
    return this.request<JobResponse[]>(
      "GET",
      `/v1/jobs${query ? `?${query}` : ""}`,
    );
  }

  /**
   * GET /v1/jobs/{job_id} - Get job by ID.
   */
  async getJob(jobId: string): Promise<JobResponse> {
    return this.request<JobResponse>("GET", `/v1/jobs/${jobId}`);
  }

  /**
   * GET /v1/jobs/{job_id}/receipt - Get job receipt.
   */
  async getReceipt(jobId: string): Promise<JobReceipt> {
    return this.request<JobReceipt>("GET", `/v1/jobs/${jobId}/receipt`);
  }

  /**
   * POST /v1/jobs/{job_id}/cancel - Cancel a job.
   */
  async cancelJob(jobId: string): Promise<JobResponse> {
    return this.request<JobResponse>("POST", `/v1/jobs/${jobId}/cancel`);
  }

  // --- Diagnostics ---

  /**
   * POST /v1/diagnostics/export - Export diagnostics bundle.
   */
  async exportDiagnostics(fullIntegrity?: boolean): Promise<DiagnosticsReport> {
    const params = new URLSearchParams();
    if (fullIntegrity !== undefined) {
      params.set("full_integrity", fullIntegrity.toString());
    }
    const query = params.toString();
    return this.request<DiagnosticsReport>(
      "POST",
      `/v1/diagnostics/export${query ? `?${query}` : ""}`,
    );
  }

  // --- Engine Control ---

  /**
   * POST /v1/engine/shutdown - Request graceful shutdown.
   */
  async requestShutdown(
    reason?: string,
    gracePeriodMs?: number,
  ): Promise<{ status: string; reason: string; grace_period_ms: number }> {
    const params = new URLSearchParams();
    if (reason) {
      params.set("reason", reason);
    }
    if (gracePeriodMs) {
      params.set("grace_period_ms", gracePeriodMs.toString());
    }
    const query = params.toString();
    return this.request(
      "POST",
      `/v1/engine/shutdown${query ? `?${query}` : ""}`,
    );
  }

  // --- Translation (Sprint 5) ---

  /**
   * POST /translate - Translate a scripture passage.
   *
   * Returns either a TranslateResponse (success) or GateResponse (gate triggered).
   */
  async translate(request: TranslateRequest): Promise<TranslateResult> {
    return this.request<TranslateResult>("POST", "/translate", request);
  }

  /**
   * POST /acknowledge - Acknowledge a variant reading.
   *
   * Must be called before translate will proceed past a variant gate.
   */
  async acknowledge(request: AcknowledgeRequest): Promise<AcknowledgeResponse> {
    return this.request<AcknowledgeResponse>("POST", "/acknowledge", request);
  }
}

/**
 * Create an API client with default configuration.
 */
export function createApiClient(
  port: number = 47200,
  token: string = "",
): ApiClient {
  return new ApiClient({
    baseUrl: `http://127.0.0.1:${port}`,
    token,
  });
}
