/**
 * E2E test fixtures - Mock API responses for Playwright tests.
 *
 * Sprint 20: Jobs-first GUI UX loop
 */

import type { Page, Route } from "@playwright/test";

// Mock data structures
export const mockCapabilities = {
  version: "0.20.0",
  api_version: "1.0",
  min_gui_version: "0.17.0",
  endpoints: {
    engine_status: "/v1/engine/status",
    stream: "/v1/stream",
    jobs: "/v1/jobs",
    gates_pending: "/v1/gates/pending",
    run_scholarly: "/v1/run/scholarly",
    translate: "/translate",
    acknowledge: "/acknowledge",
    sources: "/sources",
    sources_status: "/sources/status",
    variants_dossier: "/variants/dossier",
  },
  features: ["translate", "scholarly_run", "gates"],
  initialized: true,
};

export const mockEngineStatus = {
  version: "0.20.0",
  build_hash: "abc123",
  api_version: "1.0",
  capabilities: ["translate", "scholarly_run"],
  mode: "normal",
  health: "healthy",
  uptime_seconds: 120,
  active_jobs: 0,
  queue_depth: 0,
  shape: {
    backend_mode: "full",
    has_translate: true,
    has_sources_status: true,
    has_acknowledge: true,
    has_variants_dossier: true,
  },
};

export const mockEngineStatusEngineOnly = {
  ...mockEngineStatus,
  shape: {
    backend_mode: "engine_only",
    has_translate: false,
    has_sources_status: false,
    has_acknowledge: false,
    has_variants_dossier: false,
  },
};

export const mockSourcesStatus = {
  data_root: "/data",
  manifest_path: "/data/manifest.json",
  spine_installed: true,
  spine_source_id: "sblgnt",
  sources: {
    sblgnt: {
      source_id: "sblgnt",
      name: "SBL Greek New Testament",
      role: "canonical_spine",
      license: "CC BY 4.0",
      requires_eula: false,
      installed: true,
      install_path: "/data/sblgnt",
      installed_at: "2025-01-01T00:00:00Z",
      version: "1.0.0",
      eula_accepted: null,
    },
  },
};

export const mockJobs = [
  {
    job_id: "job-001",
    state: "completed",
    created_at: "2025-01-15T10:00:00Z",
    started_at: "2025-01-15T10:00:01Z",
    completed_at: "2025-01-15T10:00:30Z",
    config: {
      job_type: "scholarly",
      reference: "John 1:1-5",
      mode: "traceable",
    },
    result: {
      success: true,
      output_dir: "/output/scholarly-001",
      bundle_path: "/output/bundle.zip",
    },
  },
];

export const mockJobReceipt = {
  schema_version: "1.0.0",
  job_id: "job-001",
  run_id: "run-001",
  receipt_status: "completed",
  timestamps: {
    created: "2025-01-15T10:00:00Z",
    started: "2025-01-15T10:00:01Z",
    completed: "2025-01-15T10:00:30Z",
  },
  config_snapshot: {
    reference: "John 1:1-5",
    mode: "traceable",
  },
  source_pins: {
    sblgnt: "v1.0.0",
  },
  outputs: [
    {
      path: "/output/translation.json",
      size_bytes: 12345,
      sha256:
        "abc123def456abc123def456abc123def456abc123def456abc123def456abcd",
    },
  ],
  inputs_summary: {},
};

export const mockTranslateResponse = {
  response_type: "translation",
  reference: "John 1:1",
  normalized_ref: "John.1.1",
  verse_ids: ["John.1.1"],
  mode: "traceable",
  sblgnt_text: "Ἐν ἀρχῇ ἦν ὁ λόγος",
  translation_text: "In the beginning was the Word",
  verse_blocks: [],
  variants: [],
  claims: [],
  confidence: null,
  provenance: {
    spine_source: "sblgnt",
    spine_marker: "SBLGNT",
    sources_used: ["sblgnt"],
    variant_unit_ids: [],
    witness_summaries: [],
  },
  receipts: {
    checks_run: [],
    gates_satisfied: [],
    gates_pending: [],
    enforcement_results: [],
    timestamp: "2025-01-15T10:00:00Z",
  },
  tokens: [],
  session_id: "session-001",
  translator_type: "traceable",
  ledger: null,
};

/**
 * Set up full mock backend routes.
 * Also injects auth token into localStorage before navigation.
 */
export async function setupMockBackend(page: Page): Promise<void> {
  // Inject auth token before any navigation
  await page.addInitScript(() => {
    window.localStorage.setItem("redletters_auth_token", "test-token-123");
    // Also mark bootstrap as completed to skip wizard
    window.localStorage.setItem("redletters_bootstrap_completed", "true");
  });

  await page.route("**/v1/capabilities", async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockCapabilities),
    });
  });

  await page.route("**/v1/engine/status", async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockEngineStatus),
    });
  });

  // Only mock API requests (port 47200), not page navigation
  await page.route("**/sources/status", async (route: Route) => {
    // Skip page navigation requests (HTML pages)
    if (!route.request().url().includes(":47200")) {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockSourcesStatus),
    });
  });

  await page.route("**/sources", async (route: Route) => {
    // Skip page navigation requests (HTML pages)
    if (!route.request().url().includes(":47200")) {
      await route.continue();
      return;
    }
    if (route.request().url().includes("/status")) return;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockSourcesStatus),
    });
  });

  await page.route("**/v1/jobs", async (route: Route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockJobs),
      });
    } else {
      await route.continue();
    }
  });

  await page.route("**/v1/jobs/*/receipt", async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockJobReceipt),
    });
  });

  await page.route("**/translate", async (route: Route) => {
    // Skip page navigation requests (HTML pages)
    if (!route.request().url().includes(":47200")) {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockTranslateResponse),
    });
  });

  // SSE stream - return empty keepalive
  await page.route("**/v1/stream**", async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      headers: {
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
      body: 'event: heartbeat\nid: 1\ndata: {"event_type":"engine.heartbeat","sequence_number":1,"timestamp_utc":"2025-01-15T10:00:00Z","uptime_ms":60000,"health":"healthy","active_jobs":0,"queue_depth":0}\n\n',
    });
  });
}

/**
 * Set up engine-only backend (missing GUI routes).
 * Also injects auth token into localStorage before navigation.
 */
export async function setupEngineOnlyBackend(page: Page): Promise<void> {
  // Inject auth token before any navigation
  await page.addInitScript(() => {
    window.localStorage.setItem("redletters_auth_token", "test-token-123");
    window.localStorage.setItem("redletters_bootstrap_completed", "true");
  });

  await page.route("**/v1/capabilities", async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockCapabilities),
    });
  });

  await page.route("**/v1/engine/status", async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockEngineStatusEngineOnly),
    });
  });

  // Return 404 for GUI routes
  await page.route("**/sources/status", async (route: Route) => {
    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({
        error: "Not Found",
        code: "not_found",
        message: "Route not found",
      }),
    });
  });

  await page.route("**/translate", async (route: Route) => {
    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({
        error: "Not Found",
        code: "not_found",
        message: "Route not found",
      }),
    });
  });

  await page.route("**/v1/stream**", async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      headers: {
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
      body: 'event: heartbeat\nid: 1\ndata: {"event_type":"engine.heartbeat","sequence_number":1,"timestamp_utc":"2025-01-15T10:00:00Z","uptime_ms":60000,"health":"healthy","active_jobs":0,"queue_depth":0}\n\n',
    });
  });
}
