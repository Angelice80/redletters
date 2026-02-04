/**
 * Real-backend smoke test for GUI golden path.
 *
 * Sprint 21: End-to-end validation against running backend.
 *
 * This test requires:
 * - Backend running on port 47200 (full mode)
 * - GUI running on port 1420
 * - Valid auth token
 *
 * Run with: npx playwright test --config=playwright-real.config.ts
 */

import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";

// Token file path (same as backend uses)
const TOKEN_FILE = path.join(os.homedir(), ".greek2english", ".auth_token");

/**
 * Get auth token from backend's token file.
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
  test.beforeEach(async ({ page }) => {
    // Inject auth token into localStorage before each test
    const token = getAuthToken();

    await page.addInitScript((authToken) => {
      window.localStorage.setItem("redletters_auth_token", authToken);
    }, token);
  });

  test("golden path: connection → sources → translate → output", async ({
    page,
  }) => {
    // Step 1: Load GUI and verify connection
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();

    // Wait for connection badge to show healthy state
    // The badge may show "Connected" or have a green indicator
    const connectionBadge = page.locator("[data-testid=connection-badge]");
    await expect(connectionBadge).toBeVisible({ timeout: 10000 });

    // Verify we're not seeing a critical error panel
    const errorPanel = page.locator("[data-testid=api-error-panel]");
    await expect(errorPanel).not.toBeVisible();

    // Step 2: Navigate to Sources
    await page.getByRole("link", { name: /sources/i }).click();
    await expect(page).toHaveURL(/\/sources/);

    // Wait for sources to load
    await expect(page.getByRole("heading", { name: "Sources" })).toBeVisible();

    // Check if spine is installed
    const spineStatus = page.getByText(/spine:/i);
    await expect(spineStatus).toBeVisible({ timeout: 10000 });

    // If spine shows "Not installed", click Install Spine button
    const notInstalled = page.getByText(/not installed/i);
    if (await notInstalled.isVisible().catch(() => false)) {
      // Look for Install Spine button
      const installButton = page.getByRole("button", {
        name: /install spine/i,
      });
      if (await installButton.isVisible().catch(() => false)) {
        await installButton.click();
        // Wait for installation to complete (may take time for git clone)
        await expect(page.getByText(/installed/i)).toBeVisible({
          timeout: 60000,
        });
      }
    }

    // Step 3: Navigate to Explore
    await page.getByRole("link", { name: /explore/i }).click();
    await expect(page).toHaveURL(/\/explore/);

    // Wait for explore page to load (shows empty state text)
    await expect(page.getByText("Explore Greek New Testament")).toBeVisible();

    // Step 4: Enter reference and translate
    const refInput = page.getByPlaceholder(/john|reference|verse/i);
    await expect(refInput).toBeVisible();
    await refInput.fill("John 1:1");

    // Click translate button
    const translateButton = page.getByRole("button", { name: /translate/i });
    await expect(translateButton).toBeEnabled();
    await translateButton.click();

    // Step 5: Verify output renders
    // Wait for Greek text to appear (SBLGNT section)
    const greekText = page.getByText(/ἐν ἀρχῇ/i);
    await expect(greekText).toBeVisible({ timeout: 30000 });

    // Verify translation text appears (should have "beginning" or "word")
    const translationSection = page.locator("text=/beginning|word/i");
    await expect(translationSection).toBeVisible();

    // Verify no error panel appeared
    const translateError = page.locator(
      "[data-testid=api-error-panel], [data-testid=backend-mismatch-panel]",
    );
    await expect(translateError).not.toBeVisible();

    // Step 6: Verify we can navigate to Jobs (bonus check)
    await page.getByRole("link", { name: /jobs/i }).click();
    await expect(page).toHaveURL(/\/jobs/);
    await expect(page.getByRole("heading", { name: "Jobs" })).toBeVisible();
  });
});
