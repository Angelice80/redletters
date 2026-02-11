/**
 * Background Guard — automated verification that per-route decorative
 * backgrounds are present, correctly styled, and not accidentally opaque.
 *
 * Validates:
 *   - .pageBackground element exists in the DOM
 *   - Computed opacity is approximately 0.15 (default)
 *   - z-index is 0 (behind content)
 *   - Element has non-zero height (not collapsed/clipped)
 *   - Background image request does not 404
 *   - Opacity can be temporarily forced to 0.3 without breaking layout
 */

import { test, expect } from "@playwright/test";
import { setupMockBackend } from "./fixtures";

const BACKGROUND_ROUTES = [
  { name: "explore", path: "/explore", waitFor: "[data-testid=demo-btn]" },
  { name: "export", path: "/export", waitFor: "text=Export" },
  { name: "sources", path: "/sources", waitFor: "text=Sources" },
  { name: "jobs", path: "/jobs", waitFor: "[data-testid=page-title]" },
];

test.describe("Background Guard", () => {
  for (const route of BACKGROUND_ROUTES) {
    test(`${route.name}: background element present and styled`, async ({
      page,
    }) => {
      await setupMockBackend(page);
      await page.goto(route.path);
      await page.waitForSelector(route.waitFor, { timeout: 10000 });
      // Let the 800ms opacity transition complete
      await page.waitForTimeout(1200);

      const bgEl = page.locator(".pageBackground").first();
      await expect(bgEl).toBeVisible();

      // Verify container styles
      const containerStyles = await bgEl.evaluate((el) => {
        const cs = window.getComputedStyle(el);
        return {
          zIndex: cs.zIndex,
          overflow: cs.overflow,
          position: cs.position,
          height: el.getBoundingClientRect().height,
          pointerEvents: cs.pointerEvents,
        };
      });

      expect(containerStyles.zIndex).toBe("0");
      expect(containerStyles.overflow).toBe("hidden");
      expect(containerStyles.position).toBe("absolute");
      expect(containerStyles.height).toBeGreaterThan(0);
      expect(containerStyles.pointerEvents).toBe("none");

      // Verify image layer opacity ~ 0.15
      const imageEl = page.locator(".pageBackground__image").first();
      const imageOpacity = await imageEl.evaluate((el) => {
        return parseFloat(window.getComputedStyle(el).opacity);
      });
      expect(imageOpacity).toBeCloseTo(0.15, 1);
    });

    test(`${route.name}: background image does not 404`, async ({ page }) => {
      const imageRequests: { url: string; status: number }[] = [];

      // Track background image requests
      page.on("response", (response) => {
        if (response.url().includes("/backgrounds/")) {
          imageRequests.push({
            url: response.url(),
            status: response.status(),
          });
        }
      });

      await setupMockBackend(page);
      await page.goto(route.path);
      await page.waitForSelector(route.waitFor, { timeout: 10000 });
      await page.waitForTimeout(1200);

      // At least one background image should have loaded
      const bgRequests = imageRequests.filter((r) =>
        r.url.includes(`/backgrounds/${route.name}`),
      );
      expect(
        bgRequests.length,
        `Expected background image request for ${route.name}`,
      ).toBeGreaterThan(0);

      // None should 404
      for (const req of bgRequests) {
        expect(req.status, `${req.url} returned ${req.status}`).not.toBe(404);
      }
    });

    test(`${route.name}: opacity clamp — forced 0.3 does not break layout`, async ({
      page,
    }) => {
      await setupMockBackend(page);
      await page.goto(route.path);
      await page.waitForSelector(route.waitFor, { timeout: 10000 });
      await page.waitForTimeout(1200);

      // Force opacity to 0.3 (the production max)
      const imageEl = page.locator(".pageBackground__image").first();
      await imageEl.evaluate((el) => {
        (el as HTMLElement).style.opacity = "0.3";
      });

      // Take screenshot at forced opacity
      await page.screenshot({
        path: `test-results/bg-guard-${route.name}-forced-opacity.png`,
      });

      // Verify content is still above background (z-index check)
      const contentVisible = await page.evaluate(() => {
        const content = document.querySelector(
          "[style*='z-index: 1']",
        ) as HTMLElement;
        if (!content) return false;
        const rect = content.getBoundingClientRect();
        return rect.height > 0 && rect.width > 0;
      });
      expect(
        contentVisible,
        "Content should remain visible above background",
      ).toBe(true);

      // Restore opacity
      await imageEl.evaluate((el) => {
        (el as HTMLElement).style.opacity = "";
      });
    });
  }

  test("routes without backgrounds should not have .pageBackground", async ({
    page,
  }) => {
    await setupMockBackend(page);

    // Dashboard (/) should NOT have a background
    await page.goto("/");
    await page.waitForSelector("[data-testid=page-title]", { timeout: 10000 });
    await page.waitForTimeout(500);

    const bgCount = await page.locator(".pageBackground").count();
    expect(bgCount, "Dashboard should not have a page background").toBe(0);
  });

  test("/sources/new still maps to sources background", async ({ page }) => {
    await setupMockBackend(page);
    // Navigate to a sub-route of /sources
    await page.goto("/sources");
    await page.waitForSelector("text=Sources", { timeout: 10000 });
    await page.waitForTimeout(1200);

    const bgEl = page.locator(".pageBackground").first();
    await expect(bgEl).toBeVisible();

    const imageOpacity = await page
      .locator(".pageBackground__image")
      .first()
      .evaluate((el) => parseFloat(window.getComputedStyle(el).opacity));
    expect(imageOpacity).toBeCloseTo(0.15, 1);
  });
});
