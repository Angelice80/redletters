/**
 * Real-backend smoke test for GUI golden path.
 *
 * Sprint 21: End-to-end validation against running backend.
 *
 * POLICY: This is ONE golden-path test. Keep it focused.
 * If it grows beyond connection→capabilities→translate→verify, split it.
 *
 * This test PROVES:
 * 1. Auth token injection works (from backend's token file)
 * 2. Capabilities are fetched and contract resolves endpoints
 * 3. A real translation request works end-to-end
 * 4. Output renders correctly (Greek + English)
 *
 * Run with: npx playwright test --config=playwright-real.config.ts
 */

import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";

const BACKEND_PORT = 47200;
const TOKEN_FILE = path.join(os.homedir(), ".greek2english", ".auth_token");

/**
 * Get auth token from backend's token file.
 * Fails fast with clear message if backend not started.
 */
function getAuthToken(): string {
  if (!fs.existsSync(TOKEN_FILE)) {
    throw new Error(
      `Auth token file not found at ${TOKEN_FILE}. ` +
        "Start the backend first: make dev-backend",
    );
  }
  return fs.readFileSync(TOKEN_FILE, "utf-8").trim();
}

test.describe("Real Backend Golden Path", () => {
  let authToken: string;

  test.beforeAll(() => {
    // Fail fast if no token - don't waste time on doomed tests
    authToken = getAuthToken();
  });

  test.beforeEach(async ({ page }) => {
    // PROOF 1: Auth token injection works
    await page.addInitScript((token) => {
      window.localStorage.setItem("redletters_auth_token", token);
      window.localStorage.setItem("redletters_bootstrap_completed", "true");
    }, authToken);
  });

  test("golden path: capabilities → translate → verify output", async ({
    page,
  }) => {
    // ═══════════════════════════════════════════════════════════════════
    // PROOF 2: Capabilities fetched and contract resolves endpoints
    // ═══════════════════════════════════════════════════════════════════

    // Intercept capabilities request to verify it happens
    let capabilitiesFetched = false;
    let capabilitiesData: unknown = null;

    await page.route(`**/v1/capabilities`, async (route) => {
      capabilitiesFetched = true;
      const response = await route.fetch();
      capabilitiesData = await response.json();
      await route.fulfill({ response });
    });

    // Load app - this triggers capabilities fetch
    await page.goto("/");

    // Wait for connection badge (proves SSE connection established)
    const connectionBadge = page.locator("[data-testid=connection-badge]");
    await expect(connectionBadge).toBeVisible({ timeout: 10000 });

    // ASSERT: Capabilities were fetched
    expect(capabilitiesFetched).toBe(true);
    expect(capabilitiesData).toBeTruthy();

    // Verify no bootstrap wizard (token worked)
    const wizardHeading = page.getByRole("heading", { name: /welcome/i });
    await expect(wizardHeading).not.toBeVisible();

    // Verify no critical error panel
    await expect(
      page.locator("[data-testid=api-error-panel]"),
    ).not.toBeVisible();

    // ═══════════════════════════════════════════════════════════════════
    // PROOF 3: Real translation request works end-to-end
    // ═══════════════════════════════════════════════════════════════════

    // Navigate to Explore
    await page.getByRole("link", { name: /explore/i }).click();
    await expect(page).toHaveURL(/\/explore/);
    await expect(page.getByText("Explore Greek New Testament")).toBeVisible();

    // Track translate request
    let translateRequested = false;
    let translateEndpoint = "";

    await page.route(`**:${BACKEND_PORT}/translate**`, async (route) => {
      translateRequested = true;
      translateEndpoint = route.request().url();
      await route.continue();
    });

    // Enter reference and translate
    const refInput = page.getByPlaceholder(/john|reference|verse/i);
    await refInput.fill("John 1:1");

    const translateButton = page.getByRole("button", { name: /translate/i });
    await translateButton.click();

    // ═══════════════════════════════════════════════════════════════════
    // PROOF 4: Output renders correctly
    // ═══════════════════════════════════════════════════════════════════

    // Wait for Greek text (SBLGNT)
    const greekText = page.getByText(/ἐν ἀρχῇ/i);
    await expect(greekText).toBeVisible({ timeout: 30000 });

    // Verify English translation appears
    const translationText = page.locator("text=/beginning|word/i");
    await expect(translationText).toBeVisible();

    // ASSERT: Translate was called via contract-resolved endpoint
    expect(translateRequested).toBe(true);
    expect(translateEndpoint).toContain(`:${BACKEND_PORT}/translate`);

    // Verify no error panels after translation
    await expect(
      page.locator(
        "[data-testid=api-error-panel], [data-testid=backend-mismatch-panel]",
      ),
    ).not.toBeVisible();

    // ═══════════════════════════════════════════════════════════════════
    // BONUS: Verify Jobs page accessible (proves full backend mode)
    // ═══════════════════════════════════════════════════════════════════

    await page.getByRole("link", { name: /jobs/i }).click();
    await expect(page).toHaveURL(/\/jobs/);
    await expect(page.getByRole("heading", { name: "Jobs" })).toBeVisible();
  });
});
