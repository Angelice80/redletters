/**
 * Real-backend scholarly job test.
 *
 * Sprint 21: End-to-end validation of async scholarly job flow.
 *
 * This test PROVES:
 * 1. Backend is in "full" mode (not engine_only)
 * 2. GUI can submit a scholarly run via the Export wizard
 * 3. Backend processes the job asynchronously (returns job_id)
 * 4. Job reaches terminal state (completed with success OR gate_blocked)
 *
 * Run with: npx playwright test --config=playwright-real.config.ts
 */

import {
  test,
  expect,
  type Page,
  type APIRequestContext,
} from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";

// Configuration
const BACKEND_URL = process.env.RL_BACKEND_URL ?? "http://127.0.0.1:47200";
const TOKEN_FILE = path.join(os.homedir(), ".greek2english", ".auth_token");

// Polling configuration
const POLL_INITIAL_MS = 250;
const POLL_MAX_MS = 1000;
const POLL_TIMEOUT_MS = 60_000;

/**
 * Get auth token from env var or backend's token file.
 * Fails fast with clear message if neither available.
 */
function getAuthToken(): string {
  // Prefer env var for CI
  if (process.env.RL_TEST_TOKEN) {
    return process.env.RL_TEST_TOKEN;
  }

  // Fall back to token file for local dev
  if (!fs.existsSync(TOKEN_FILE)) {
    throw new Error(
      `Auth token not found. Set RL_TEST_TOKEN env var or start backend first.\n` +
        `Token file checked: ${TOKEN_FILE}\n` +
        `Backend URL: ${BACKEND_URL}`,
    );
  }
  return fs.readFileSync(TOKEN_FILE, "utf-8").trim();
}

/**
 * Preflight check: Verify backend is in full mode (not engine_only).
 * Supports both backends with shape field and older backends without it.
 */
async function verifyBackendMode(
  request: APIRequestContext,
  authToken: string,
): Promise<void> {
  const response = await request.get(`${BACKEND_URL}/v1/engine/status`, {
    headers: { Authorization: `Bearer ${authToken}` },
  });

  if (!response.ok()) {
    const text = await response.text();
    throw new Error(
      `Backend status check failed (${response.status()}): ${text}\n` +
        `URL: ${BACKEND_URL}/v1/engine/status\n` +
        `Token present: ${!!authToken}`,
    );
  }

  const status = await response.json();
  const shape = status.shape;

  // If shape field exists, validate it
  if (shape) {
    if (shape.backend_mode !== "full") {
      throw new Error(
        `Backend is running in "${shape.backend_mode}" mode, but test requires "full" mode.\n` +
          `Start backend with: make dev-backend\n` +
          `Or: python -m redletters engine start`,
      );
    }

    if (!shape.has_translate || !shape.has_sources_status) {
      throw new Error(
        `Backend shape indicates missing GUI routes:\n` +
          `  has_translate: ${shape.has_translate}\n` +
          `  has_sources_status: ${shape.has_sources_status}\n` +
          `Start backend with full routes enabled.`,
      );
    }
    return;
  }

  // Fallback: Probe /translate endpoint to verify full mode
  const translateProbe = await request.post(`${BACKEND_URL}/translate`, {
    headers: {
      Authorization: `Bearer ${authToken}`,
      "Content-Type": "application/json",
    },
    data: { reference: "John 1:1", mode: "traceable", session_id: "probe" },
  });

  if (!translateProbe.ok()) {
    throw new Error(
      `Backend appears to be in engine_only mode (no /translate route).\n` +
        `Status: ${translateProbe.status()}\n` +
        `Start backend with: make dev-backend\n` +
        `Or: python -m redletters engine start`,
    );
  }
}

interface JobResult {
  job_id: string;
  state: string;
  result?: {
    success?: boolean;
    gate_blocked?: boolean;
    pending_gates?: string[];
    errors?: string[];
    output_dir?: string;
    bundle_path?: string;
  };
  error_message?: string;
}

/**
 * Poll job until terminal state with exponential backoff.
 */
async function pollJobUntilTerminal(
  request: APIRequestContext,
  jobId: string,
  authToken: string,
): Promise<JobResult> {
  const startTime = Date.now();
  let delay = POLL_INITIAL_MS;

  const terminalStates = new Set(["completed", "failed", "cancelled"]);

  while (Date.now() - startTime < POLL_TIMEOUT_MS) {
    const response = await request.get(`${BACKEND_URL}/v1/jobs/${jobId}`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });

    if (!response.ok()) {
      throw new Error(
        `Failed to fetch job ${jobId}: ${response.status()} ${await response.text()}`,
      );
    }

    const job = (await response.json()) as JobResult;

    if (terminalStates.has(job.state)) {
      return job;
    }

    // Exponential backoff
    await new Promise((r) => setTimeout(r, delay));
    delay = Math.min(delay * 1.5, POLL_MAX_MS);
  }

  throw new Error(
    `Job ${jobId} did not reach terminal state within ${POLL_TIMEOUT_MS}ms`,
  );
}

/**
 * Diagnostic dump on failure.
 */
function dumpDiagnostics(
  jobResult: JobResult | null,
  engineStatus: unknown,
): string {
  return (
    `\n=== DIAGNOSTICS ===\n` +
    `Backend URL: ${BACKEND_URL}\n` +
    `Token present: true (not shown)\n` +
    `Engine status: ${JSON.stringify(engineStatus, null, 2)}\n` +
    `Last job payload: ${JSON.stringify(jobResult, null, 2)}\n` +
    `==================\n`
  );
}

test.describe("Real Backend Scholarly Job Flow", () => {
  let authToken: string;

  test.beforeAll(() => {
    authToken = getAuthToken();
  });

  test.beforeEach(async ({ page }) => {
    // Inject auth token before navigation
    await page.addInitScript((token) => {
      window.localStorage.setItem("redletters_auth_token", token);
      window.localStorage.setItem("redletters_bootstrap_completed", "true");
    }, authToken);
  });

  test("scholarly job: submit -> completed|gate_blocked", async ({
    page,
    request,
  }) => {
    // ═══════════════════════════════════════════════════════════════════════
    // STEP 1: Preflight - Verify backend is in full mode
    // ═══════════════════════════════════════════════════════════════════════

    await verifyBackendMode(request, authToken);

    // Cache engine status for diagnostics
    const engineStatusResp = await request.get(
      `${BACKEND_URL}/v1/engine/status`,
      { headers: { Authorization: `Bearer ${authToken}` } },
    );
    const engineStatus = await engineStatusResp.json();

    // ═══════════════════════════════════════════════════════════════════════
    // STEP 2: Navigate to Export and fill wizard
    // ═══════════════════════════════════════════════════════════════════════

    await page.goto("/");

    // Wait for connection badge (proves SSE connection established)
    const connectionBadge = page.locator("[data-testid=connection-badge]");
    await expect(connectionBadge).toBeVisible({ timeout: 10000 });

    // Navigate to Export
    await page.getByRole("link", { name: /export/i }).click();
    await expect(page).toHaveURL(/\/export/);

    // Fill reference input (use John 1:1 - a deterministic short passage)
    const refInput = page.locator("[data-testid=export-reference]");
    await expect(refInput).toBeVisible();
    await refInput.fill("John 1:1");

    // Ensure mode is traceable (default, but be explicit)
    const modeSelect = page.locator("[data-testid=export-mode]");
    await modeSelect.selectOption("traceable");

    // ═══════════════════════════════════════════════════════════════════════
    // STEP 3: Check gates and proceed to export step
    // ═══════════════════════════════════════════════════════════════════════

    const checkGatesBtn = page.locator("[data-testid=export-check-gates]");
    await expect(checkGatesBtn).toBeVisible();
    await checkGatesBtn.click();

    // Wait for wizard to advance (either to gates step or export step)
    // The button will become "Run Scholarly Export" when we reach export step
    // Or we may need to handle gates first
    const runButton = page.locator("[data-testid=export-run]");

    // Wait up to 15s for either the run button to appear or gates to show
    await expect(
      runButton.or(page.getByText(/Gates Detected|Acknowledge Variants/i)),
    ).toBeVisible({ timeout: 15000 });

    // If gates are detected, we need to force through (for test purposes)
    const gatesDetected = await page
      .getByText(/Gates Detected/i)
      .isVisible()
      .catch(() => false);

    if (gatesDetected) {
      // Click "Force Export" and confirm
      await page.getByRole("button", { name: /Force Export/i }).click();
      const forceConfirm = page.locator("#force-confirm");
      if (await forceConfirm.isVisible()) {
        await forceConfirm.check();
      }
      await page.getByRole("button", { name: /Proceed Anyway/i }).click();
    }

    // Now the run button should be visible
    await expect(runButton).toBeVisible({ timeout: 5000 });

    // ═══════════════════════════════════════════════════════════════════════
    // STEP 4: Submit scholarly run and capture job_id from response
    // ═══════════════════════════════════════════════════════════════════════

    // Set up response listener before clicking
    const scholarlyResponsePromise = page.waitForResponse(
      (resp) =>
        resp.url().includes("/v1/run/scholarly") &&
        resp.request().method() === "POST",
      { timeout: 15000 },
    );

    await runButton.click();

    // Capture the scholarly response
    const scholarlyResponse = await scholarlyResponsePromise;
    expect(scholarlyResponse.status()).toBe(202);

    const scholarlyData = await scholarlyResponse.json();
    expect(scholarlyData.job_id).toBeTruthy();
    const jobId = scholarlyData.job_id as string;

    // Verify job_id format: job_YYYYMMDD_HHMMSS_xxxxxxxx
    expect(jobId).toMatch(/^job_\d{8}_\d{6}_[a-f0-9]+$/i);

    // ═══════════════════════════════════════════════════════════════════════
    // STEP 5: Poll job until terminal state
    // ═══════════════════════════════════════════════════════════════════════

    let jobResult: JobResult;
    try {
      jobResult = await pollJobUntilTerminal(request, jobId, authToken);
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : String(err);
      throw new Error(errMsg + dumpDiagnostics(null, engineStatus));
    }

    // ═══════════════════════════════════════════════════════════════════════
    // STEP 6: Assertions on terminal state
    // ═══════════════════════════════════════════════════════════════════════

    // State must be 'completed' (terminal success state)
    // Note: 'failed' and 'cancelled' are valid terminal states but indicate errors
    if (jobResult.state === "failed") {
      throw new Error(
        `Job failed with error: ${jobResult.error_message}` +
          dumpDiagnostics(jobResult, engineStatus),
      );
    }

    if (jobResult.state === "cancelled") {
      throw new Error(
        `Job was unexpectedly cancelled` +
          dumpDiagnostics(jobResult, engineStatus),
      );
    }

    expect(jobResult.state).toBe("completed");

    // Result must satisfy one of:
    // a) result.success === true (fully successful)
    // b) result.gate_blocked === true with pending_gates (blocked but valid)
    const result = jobResult.result;
    expect(result).toBeTruthy();

    const isSuccess = result?.success === true && !result?.gate_blocked;
    const isGateBlocked =
      result?.gate_blocked === true &&
      Array.isArray(result?.pending_gates) &&
      result.pending_gates.length > 0;

    if (!isSuccess && !isGateBlocked) {
      throw new Error(
        `Job completed but result is neither success nor gate_blocked:\n` +
          `  success: ${result?.success}\n` +
          `  gate_blocked: ${result?.gate_blocked}\n` +
          `  errors: ${JSON.stringify(result?.errors)}` +
          dumpDiagnostics(jobResult, engineStatus),
      );
    }

    // Log outcome for visibility
    if (isSuccess) {
      console.log(
        `[PASS] Job ${jobId} completed successfully. Output: ${result?.output_dir}`,
      );
    } else {
      console.log(
        `[PASS] Job ${jobId} gate_blocked with ${result?.pending_gates?.length} pending gates.`,
      );
    }

    // ═══════════════════════════════════════════════════════════════════════
    // STEP 7: Verify UI shows progress modal (optional but nice to have)
    // ═══════════════════════════════════════════════════════════════════════

    // The job has completed by now, so modal should show terminal state
    // Just verify no critical errors shown
    await expect(
      page.locator("[data-testid=api-error-panel]"),
    ).not.toBeVisible();
  });
});
