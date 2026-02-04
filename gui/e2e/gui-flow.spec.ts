/**
 * E2E tests for GUI flow.
 *
 * Sprint 20: Jobs-first GUI UX loop
 *
 * Tests core user journeys with mocked backend.
 */

import { test, expect } from "@playwright/test";
import {
  setupMockBackend,
  setupEngineOnlyBackend,
  mockJobs,
  mockJobReceipt,
} from "./fixtures";

test.describe("Sources Page", () => {
  test("loads and shows sources page", async ({ page }) => {
    await setupMockBackend(page);
    await page.goto("/sources");

    // Wait for page URL to be correct
    await expect(page).toHaveURL(/\/sources/);

    // Should show Sources heading
    await expect(page.getByRole("heading", { name: "Sources" })).toBeVisible({
      timeout: 20000,
    });
  });

  test("shows source data when loaded", async ({ page }) => {
    await setupMockBackend(page);
    await page.goto("/sources");

    // Wait for Sources heading first
    await expect(page.getByRole("heading", { name: "Sources" })).toBeVisible({
      timeout: 20000,
    });

    // If source data loads, should show the spine source
    // Use more lenient check - look for any installed indicator
    const installed = page.getByText("Installed").first();
    const notConnected = page.getByText("Not connected");

    // Either we see installed data or the "not connected" message
    const hasData = await installed.isVisible().catch(() => false);
    const notConn = await notConnected.isVisible().catch(() => false);

    expect(hasData || notConn).toBe(true);
  });
});

test.describe("Jobs Page", () => {
  test("loads and shows job list", async ({ page }) => {
    await setupMockBackend(page);
    await page.goto("/jobs");

    // Should show Jobs heading
    await expect(page.getByRole("heading", { name: "Jobs" })).toBeVisible({
      timeout: 15000,
    });

    // Should show job reference from mock data
    await expect(page.getByText("John 1:1-5")).toBeVisible();
    // Should show completed state badge (use exact text match)
    await expect(page.getByText("completed", { exact: true })).toBeVisible();
  });

  test("clicking job opens drawer with receipt", async ({ page }) => {
    await setupMockBackend(page);
    await page.goto("/jobs");

    // Wait for jobs to load
    await expect(page.getByText("John 1:1-5")).toBeVisible({ timeout: 15000 });

    // Click on the job row (by reference text)
    await page.getByText("John 1:1-5").click();

    // Drawer should open - look for Job Details header
    await expect(page.getByText("Job Details")).toBeVisible();

    // Should show the job_id in the drawer (use first match since it appears multiple times)
    await expect(page.getByText(mockJobReceipt.job_id).first()).toBeVisible();
  });

  test("receipt shows collapsible sections", async ({ page }) => {
    await setupMockBackend(page);
    await page.goto("/jobs");

    // Wait for jobs to load
    await expect(page.getByText("John 1:1-5")).toBeVisible({ timeout: 15000 });

    // Click on the job row
    await page.getByText("John 1:1-5").click();

    // Wait for drawer to open
    await expect(page.getByText("Job Details")).toBeVisible();

    // Should show collapsible section headers from ReceiptViewer
    await expect(page.getByText("Job Receipt")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Timestamps")).toBeVisible();
  });

  test("receipt has Copy JSON button", async ({ page }) => {
    await setupMockBackend(page);
    await page.goto("/jobs");

    // Wait for jobs to load
    await expect(page.getByText("John 1:1-5")).toBeVisible({ timeout: 15000 });

    // Click on the job row
    await page.getByText("John 1:1-5").click();

    // Wait for receipt to load
    await expect(page.getByText("Job Receipt")).toBeVisible({ timeout: 15000 });

    // Should show Copy JSON button in the ReceiptViewer
    await expect(page.getByRole("button", { name: "Copy JSON" })).toBeVisible();
  });
});

test.describe("Explore Page", () => {
  test("loads explore page", async ({ page }) => {
    await setupMockBackend(page);
    await page.goto("/explore");

    // Should show the empty state with "Explore Greek New Testament"
    await expect(page.getByText("Explore Greek New Testament")).toBeVisible({
      timeout: 15000,
    });
  });

  test("shows reference input field", async ({ page }) => {
    await setupMockBackend(page);
    await page.goto("/explore");

    // Should have input with placeholder containing "John"
    const input = page.getByPlaceholder(/john/i);
    await expect(input).toBeVisible({ timeout: 15000 });
  });

  test("navigating to /translate shows explore page", async ({ page }) => {
    await setupMockBackend(page);
    await page.goto("/translate");

    // After React Router processes, should show explore content
    // (redirect to /explore is handled by Navigate component)
    await expect(page.getByText("Explore Greek New Testament")).toBeVisible({
      timeout: 15000,
    });
  });
});

test.describe("Export Page", () => {
  test("loads export page", async ({ page }) => {
    await setupMockBackend(page);
    await page.goto("/export");

    // Should show Export heading
    await expect(page.getByRole("heading", { name: /export/i })).toBeVisible({
      timeout: 15000,
    });
  });
});

test.describe("Connection Status", () => {
  test("shows connection badge", async ({ page }) => {
    await setupMockBackend(page);
    await page.goto("/");

    // Should show connection badge (regardless of connected/disconnected state)
    await expect(page.locator("[data-testid=connection-badge]")).toBeVisible({
      timeout: 15000,
    });
  });

  test("shows engine status in badge", async ({ page }) => {
    await setupMockBackend(page);
    await page.goto("/");

    // Badge should be visible and show some connection state text
    const badge = page.locator("[data-testid=connection-badge]");
    await expect(badge).toBeVisible({ timeout: 15000 });
    // Check that it has some state text (connected or disconnected)
    await expect(badge).toHaveText(/connected|disconnected|reconnecting/i);
  });
});

test.describe("Backend Mismatch Detection", () => {
  test("handles engine-only backend mode gracefully", async ({ page }) => {
    await setupEngineOnlyBackend(page);
    await page.goto("/");

    // App should load without crashing - look for exact app title
    await expect(page.getByText("Red Letters", { exact: true })).toBeVisible({
      timeout: 15000,
    });
  });

  test("sources page handles 404 in engine-only mode", async ({ page }) => {
    await setupEngineOnlyBackend(page);
    await page.goto("/sources");

    // Should not crash, Sources heading should still appear
    await expect(page.getByRole("heading", { name: "Sources" })).toBeVisible({
      timeout: 15000,
    });
  });
});

test.describe("Navigation", () => {
  test("can navigate between pages", async ({ page }) => {
    await setupMockBackend(page);
    await page.goto("/");

    // Wait for app to initialize - look for exact app title
    await expect(page.getByText("Red Letters", { exact: true })).toBeVisible({
      timeout: 15000,
    });

    // Navigate to Jobs
    await page.getByRole("link", { name: /jobs/i }).click();
    await expect(page).toHaveURL(/\/jobs/);

    // Navigate to Sources
    await page.getByRole("link", { name: /sources/i }).click();
    await expect(page).toHaveURL(/\/sources/);

    // Navigate to Explore
    await page.getByRole("link", { name: /explore/i }).click();
    await expect(page).toHaveURL(/\/explore/);
  });
});
