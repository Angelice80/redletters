/**
 * HTTP client for Engine Spine API.
 *
 * Uses fetch with Bearer token authentication.
 * All methods handle errors and return typed responses.
 *
 * Sprint 17: Uses ApiContract for endpoint path resolution.
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
  SourcesListResponse,
  SourcesStatusResponse,
  InstallSourceRequest,
  InstallSourceResponse,
  UninstallSourceRequest,
  UninstallSourceResponse,
  LicenseInfoResponse,
  AcknowledgeMultiRequest,
  AcknowledgeMultiResponse,
  // Sprint 8: Dossier types
  DossierResponse,
  DossierScope,
  // Sprint 14: Scholarly Run types
  ScholarlyRunRequest,
  ScholarlyRunResponse,
  // Sprint 15: Gate Pending types
  PendingGatesResponse,
  // Sprint 16: Capabilities Handshake
  ApiCapabilities,
  // Sprint 17: Enhanced error handling
  ApiErrorDetail,
  ErrorCategory,
  CapabilitiesValidation,
} from "./types";

// Import const value separately (not as type)
import { GUI_VERSION } from "./types";

// Sprint 17: Import ApiContract for endpoint resolution
import { ApiContract, type ContractDiagnostics } from "./contract";

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

/**
 * Sprint 17: Normalize any error into a structured ApiErrorDetail.
 *
 * Categorizes errors and provides actionable suggestions.
 * Optionally includes contract diagnostics for debugging endpoint resolution.
 */
export function normalizeApiError(
  method: string,
  url: string,
  error: unknown,
  contractDiagnostics?: ContractDiagnostics,
): ApiErrorDetail {
  const timestamp = new Date().toISOString();

  // Network error (fetch failed entirely)
  if (error instanceof TypeError && error.message.includes("fetch")) {
    return {
      method,
      url,
      status: null,
      statusText: "Network Error",
      responseSnippet: error.message,
      category: "network",
      likelyCause: "Connection refused or network unavailable",
      suggestions: [
        `Verify the backend is running on the expected port`,
        `Check if the server process is started: ps aux | grep redletters`,
        `Try restarting the backend with: python -m redletters`,
      ],
      suggestedFix:
        "Check if the backend server is running on the expected port.",
      timestamp,
      raw: error,
      contractDiagnostics,
    };
  }

  // ApiError from our client
  if (error instanceof ApiError) {
    const { category, likelyCause, suggestions } = categorizeHttpError(
      error.status,
      error.code,
      error.message,
    );

    return {
      method,
      url,
      status: error.status,
      statusText: error.code,
      responseSnippet: error.message,
      category,
      likelyCause,
      suggestions,
      suggestedFix: suggestions[0] || "Check the error details.",
      timestamp,
      raw: error.details,
      contractDiagnostics,
    };
  }

  // Error object with status (e.g., from raw fetch)
  if (error && typeof error === "object" && "status" in error) {
    const e = error as { status: number; code?: string; message?: string };
    const { category, likelyCause, suggestions } = categorizeHttpError(
      e.status,
      e.code || "unknown",
      e.message || "",
    );

    return {
      method,
      url,
      status: e.status,
      statusText: e.code || String(e.status),
      responseSnippet: e.message || "",
      category,
      likelyCause,
      suggestions,
      suggestedFix: suggestions[0] || "Check the error details.",
      timestamp,
      raw: error,
      contractDiagnostics,
    };
  }

  // Generic unknown error
  return {
    method,
    url,
    status: null,
    statusText: "Unknown Error",
    responseSnippet: String(error),
    category: "unknown",
    likelyCause: "An unexpected error occurred",
    suggestions: [
      "Check the browser console for more details",
      "Verify the backend is running and accessible",
      "Try refreshing the page",
    ],
    suggestedFix: "An unexpected error occurred. Check the console.",
    timestamp,
    raw: error,
    contractDiagnostics,
  };
}

/**
 * Categorize HTTP errors by status code.
 */
function categorizeHttpError(
  status: number,
  code: string,
  message: string,
): { category: ErrorCategory; likelyCause: string; suggestions: string[] } {
  if (status === 401) {
    return {
      category: "auth",
      likelyCause: "Authentication token is invalid or expired",
      suggestions: [
        "Refresh your authentication token",
        "Check that the token matches your backend configuration",
        "In browser dev mode: localStorage.setItem('redletters_auth_token', 'YOUR_TOKEN')",
      ],
    };
  }

  if (status === 404) {
    return {
      category: "not_found",
      likelyCause:
        "The requested endpoint does not exist on this backend version",
      suggestions: [
        "Verify you are running backend version 0.16.0 or newer",
        "Check the endpoint path is correct",
        "The backend may need to be upgraded: pip install -U redletters",
      ],
    };
  }

  if (status === 409) {
    return {
      category: "gate_blocked",
      likelyCause: "Textual variants require acknowledgement before proceeding",
      suggestions: [
        "Review and acknowledge pending variant readings",
        "Navigate to the Gate screen to make selections",
        "Use force=true only if you accept responsibility for unacknowledged variants",
      ],
    };
  }

  if (status === 503) {
    return {
      category: "service_unavailable",
      likelyCause: "The backend engine is not fully initialized",
      suggestions: [
        "Wait a moment for the engine to finish starting",
        "Check backend logs for initialization errors",
        "Restart the backend if the issue persists",
      ],
    };
  }

  if (status >= 500) {
    return {
      category: "server",
      likelyCause: "The server encountered an internal error",
      suggestions: [
        "Check the backend logs for error details",
        "The error may be transient - try again",
        "Report the issue if it persists: include the Copy Diagnostics payload",
      ],
    };
  }

  return {
    category: "unknown",
    likelyCause: `Request failed with status ${status}: ${code}`,
    suggestions: [
      "Check the error details above",
      "Verify your request parameters",
      "Consult the backend documentation",
    ],
  };
}

/**
 * Sprint 17: Validate API capabilities against GUI requirements.
 */
export function validateCapabilities(
  capabilities: ApiCapabilities,
): CapabilitiesValidation {
  // Check version compatibility
  const minRequired = capabilities.min_gui_version;
  if (minRequired && !isVersionCompatible(GUI_VERSION, minRequired)) {
    return {
      valid: false,
      error: `Backend requires GUI version ${minRequired} or newer, but you have ${GUI_VERSION}`,
      versionMismatch: {
        required: minRequired,
        current: GUI_VERSION,
      },
    };
  }

  // Check required endpoints
  const requiredEndpoints = [
    "translate",
    "sources",
    "sources_status",
    "gates_pending",
  ];
  const missingEndpoints: string[] = [];

  for (const endpoint of requiredEndpoints) {
    if (
      !capabilities.endpoints[endpoint as keyof typeof capabilities.endpoints]
    ) {
      missingEndpoints.push(endpoint);
    }
  }

  if (missingEndpoints.length > 0) {
    return {
      valid: false,
      error: `Backend is missing required endpoints: ${missingEndpoints.join(", ")}`,
      missingEndpoints,
    };
  }

  return { valid: true };
}

/**
 * Check if GUI version meets minimum required version.
 * Uses semver-style comparison (major.minor.patch).
 */
function isVersionCompatible(current: string, required: string): boolean {
  const parseVersion = (v: string): number[] =>
    v.split(".").map((n) => parseInt(n, 10) || 0);

  const curr = parseVersion(current);
  const req = parseVersion(required);

  for (let i = 0; i < 3; i++) {
    if ((curr[i] || 0) > (req[i] || 0)) return true;
    if ((curr[i] || 0) < (req[i] || 0)) return false;
  }
  return true; // Equal
}

export interface ApiClientConfig {
  baseUrl: string;
  token: string;
}

export class ApiClient {
  private _token: string;
  private _contract: ApiContract;

  constructor(config: ApiClientConfig) {
    this._contract = new ApiContract(config.baseUrl);
    this._token = config.token;
  }

  /**
   * Get the current auth token (for manual fetch calls).
   */
  get token(): string {
    return this._token;
  }

  /**
   * Update the auth token (e.g., after refresh).
   */
  setToken(token: string): void {
    this._token = token;
  }

  /**
   * Update the base URL (e.g., if port changes).
   */
  setBaseUrl(url: string): void {
    this._contract.setBaseUrl(url);
  }

  /**
   * Sprint 17: Get the base URL from contract.
   */
  get baseUrl(): string {
    return this._contract.baseUrl;
  }

  /**
   * Sprint 17: Get the contract for direct access to endpoint paths.
   */
  get contract(): ApiContract {
    return this._contract;
  }

  /**
   * Sprint 17: Get diagnostics snapshot for error reporting.
   */
  getContractDiagnostics(): ContractDiagnostics {
    return this._contract.getDiagnosticsSnapshot();
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const url = `${this._contract.baseUrl}${path}`;
    const headers: Record<string, string> = {
      Authorization: `Bearer ${this._token}`,
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
    return this.request<EngineStatus>("GET", this._contract.engineStatus());
  }

  /**
   * GET /v1/capabilities - Get detailed API capabilities.
   *
   * Sprint 16: Used for GUI↔backend compatibility handshake.
   * Sprint 17: Stores capabilities in contract for endpoint resolution.
   */
  async getCapabilities(): Promise<ApiCapabilities> {
    const caps = await this.request<ApiCapabilities>(
      "GET",
      this._contract.capabilitiesPath(),
    );
    // Store capabilities in contract for endpoint resolution
    this._contract.setCapabilities(caps);
    return caps;
  }

  // --- Job Management ---

  /**
   * POST /v1/jobs - Create a new job.
   */
  async createJob(request: JobCreateRequest): Promise<JobResponse> {
    return this.request<JobResponse>("POST", this._contract.jobs(), request);
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
    const path = this._contract.jobs();
    return this.request<JobResponse[]>(
      "GET",
      `${path}${query ? `?${query}` : ""}`,
    );
  }

  /**
   * GET /v1/jobs/{job_id} - Get job by ID.
   */
  async getJob(jobId: string): Promise<JobResponse> {
    return this.request<JobResponse>("GET", this._contract.jobById(jobId));
  }

  /**
   * GET /v1/jobs/{job_id}/receipt - Get job receipt.
   */
  async getReceipt(jobId: string): Promise<JobReceipt> {
    return this.request<JobReceipt>("GET", this._contract.jobReceipt(jobId));
  }

  /**
   * POST /v1/jobs/{job_id}/cancel - Cancel a job.
   */
  async cancelJob(jobId: string): Promise<JobResponse> {
    return this.request<JobResponse>("POST", this._contract.jobCancel(jobId));
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
    const path = this._contract.diagnosticsExport();
    return this.request<DiagnosticsReport>(
      "POST",
      `${path}${query ? `?${query}` : ""}`,
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
    const path = this._contract.engineShutdown();
    return this.request("POST", `${path}${query ? `?${query}` : ""}`);
  }

  // --- Translation (Sprint 5) ---

  /**
   * POST /translate - Translate a scripture passage.
   *
   * Returns either a TranslateResponse (success) or GateResponse (gate triggered).
   */
  async translate(request: TranslateRequest): Promise<TranslateResult> {
    return this.request<TranslateResult>(
      "POST",
      this._contract.translate(),
      request,
    );
  }

  /**
   * POST /acknowledge - Acknowledge a variant reading.
   *
   * Must be called before translate will proceed past a variant gate.
   */
  async acknowledge(request: AcknowledgeRequest): Promise<AcknowledgeResponse> {
    return this.request<AcknowledgeResponse>(
      "POST",
      this._contract.acknowledge(),
      request,
    );
  }

  /**
   * POST /acknowledge/multi - Acknowledge multiple variant readings at once (Sprint 7).
   *
   * Supports batch acknowledgement for passage-level or book-level acks.
   */
  async acknowledgeMulti(
    request: AcknowledgeMultiRequest,
  ): Promise<AcknowledgeMultiResponse> {
    return this.request<AcknowledgeMultiResponse>(
      "POST",
      this._contract.acknowledgeMulti(),
      request,
    );
  }

  // --- Source Management (Sprint 6) ---

  /**
   * GET /sources - List all configured sources.
   */
  async getSources(): Promise<SourcesListResponse> {
    return this.request<SourcesListResponse>("GET", this._contract.sources());
  }

  /**
   * GET /sources/status - Get installation status for all sources.
   */
  async getSourcesStatus(): Promise<SourcesStatusResponse> {
    return this.request<SourcesStatusResponse>(
      "GET",
      this._contract.sourcesStatus(),
    );
  }

  /**
   * POST /sources/install - Install a source.
   */
  async installSource(
    request: InstallSourceRequest,
  ): Promise<InstallSourceResponse> {
    return this.request<InstallSourceResponse>(
      "POST",
      this._contract.sourcesInstall(),
      request,
    );
  }

  /**
   * POST /sources/uninstall - Uninstall a source.
   */
  async uninstallSource(
    request: UninstallSourceRequest,
  ): Promise<UninstallSourceResponse> {
    return this.request<UninstallSourceResponse>(
      "POST",
      this._contract.sourcesUninstall(),
      request,
    );
  }

  /**
   * GET /sources/license - Get license info for a source.
   */
  async getLicenseInfo(sourceId: string): Promise<LicenseInfoResponse> {
    const params = new URLSearchParams({ source_id: sourceId });
    const path = this._contract.sourcesLicense();
    return this.request<LicenseInfoResponse>("GET", `${path}?${params}`);
  }

  // --- Variant Dossier (Sprint 8) ---

  /**
   * GET /variants/dossier - Get a variant dossier for a reference.
   *
   * Returns complete dossier with witness support, provenance,
   * and acknowledgement state.
   */
  async getDossier(
    reference: string,
    scope: DossierScope = "verse",
    sessionId?: string,
  ): Promise<DossierResponse> {
    const params = new URLSearchParams({ reference, scope });
    if (sessionId) {
      params.set("session_id", sessionId);
    }
    const path = this._contract.variantsDossier();
    return this.request<DossierResponse>("GET", `${path}?${params}`);
  }

  // --- Gate Pending Check (Sprint 15) ---

  /**
   * GET /v1/gates/pending - Check for pending gates at a reference.
   *
   * Uses the same gate resolver as ScholarlyRunner for consistency.
   * Returns list of pending variant acknowledgements.
   */
  async getPendingGates(
    reference: string,
    sessionId: string,
  ): Promise<PendingGatesResponse> {
    const params = new URLSearchParams({ reference, session_id: sessionId });
    const path = this._contract.gatesPending();
    return this.request<PendingGatesResponse>("GET", `${path}?${params}`);
  }

  // --- Scholarly Run (Sprint 14) ---

  /**
   * POST /v1/run/scholarly - Execute end-to-end scholarly run.
   *
   * Generates verified bundle with lockfile, apparatus, translation,
   * citations, quote, snapshot, and run_log.json.
   *
   * If pending gates exist and force=false, returns gate_blocked=true.
   */
  async runScholarly(
    request: ScholarlyRunRequest,
  ): Promise<ScholarlyRunResponse> {
    return this.request<ScholarlyRunResponse>(
      "POST",
      this._contract.runScholarly(),
      request,
    );
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
