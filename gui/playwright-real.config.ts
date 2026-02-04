/**
 * Playwright config for real-backend smoke tests.
 *
 * Sprint 21: End-to-end validation against running backend.
 *
 * Usage:
 *   npx playwright test --config=playwright-real.config.ts
 *
 * Prerequisites:
 *   - Backend must be started first: make dev-backend
 *   - OR use CI mode which starts both via webServer
 */

import { defineConfig, devices } from "@playwright/test";

const BACKEND_PORT = 47200;
const GUI_PORT = 1420;

export default defineConfig({
  testDir: "./e2e",
  // Only run real-backend tests
  testMatch: "real-backend-*.spec.ts",

  fullyParallel: false, // Serial execution for real backend
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1, // Single worker for real backend tests

  reporter: [["html", { outputFolder: "playwright-report-real" }]],

  use: {
    baseURL: `http://localhost:${GUI_PORT}`,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  // Web server configuration
  // In CI, start both backend and GUI
  // Locally, assume they're already running (use reuseExistingServer)
  webServer: process.env.CI
    ? [
        {
          // Start backend first
          command: "cd .. && python -m redletters engine start --port 47200",
          url: `http://127.0.0.1:${BACKEND_PORT}/v1/engine/status`,
          reuseExistingServer: false,
          timeout: 30 * 1000,
        },
        {
          // Then start GUI
          command: "npm run dev",
          url: `http://localhost:${GUI_PORT}`,
          reuseExistingServer: false,
          timeout: 60 * 1000,
        },
      ]
    : {
        // Local dev: just start GUI, assume backend is running
        command: "npm run dev",
        url: `http://localhost:${GUI_PORT}`,
        reuseExistingServer: true,
        timeout: 60 * 1000,
      },

  // Longer timeout for real backend operations
  timeout: 120 * 1000,
  expect: {
    timeout: 30 * 1000,
  },
});
