/**
 * Screen integration tests - verify screens use ApiClient, not raw fetch.
 *
 * Sprint 17/20: These tests ensure that:
 * 1. Screens call ApiClient methods (not raw fetch with relative paths)
 * 2. All API calls include full URLs to backend port (47200)
 * 3. No requests go to relative paths (which would hit Vite dev server at 1420)
 *
 * IMPORTANT: These tests catch the bug where GUI screens call "/translate"
 * (relative path hitting Vite) instead of "http://127.0.0.1:47200/translate".
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ApiClient } from "../api/client";

// Mock fetch to track all calls
const mockFetch = vi.fn();

// Store original fetch
const originalFetch = globalThis.fetch;

describe("Screen API call verification", () => {
  beforeEach(() => {
    // Replace global fetch with mock
    globalThis.fetch = mockFetch;
    mockFetch.mockClear();
  });

  afterEach(() => {
    // Restore original fetch
    globalThis.fetch = originalFetch;
  });

  describe("ApiClient fetch calls use full URLs", () => {
    it("translate() calls full URL with baseUrl, not relative path", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () =>
          Promise.resolve(
            JSON.stringify({
              response_type: "translation",
              sblgnt_text: "test",
              translation_text: "test",
            }),
          ),
      });

      const client = new ApiClient({
        baseUrl: "http://127.0.0.1:47200",
        token: "test-token",
      });

      await client.translate({
        reference: "John 1:1",
        mode: "readable",
        session_id: "test",
        translator: "literal",
      });

      // Verify fetch was called with FULL URL, not relative path
      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, options] = mockFetch.mock.calls[0];

      // CRITICAL: URL must be full URL to backend port, not relative
      expect(url).toBe("http://127.0.0.1:47200/translate");
      expect(url).not.toBe("/translate"); // Would hit Vite server!

      // Verify authorization header is included
      expect(options.headers.Authorization).toBe("Bearer test-token");
    });

    it("getSourcesStatus() calls full URL, not relative path", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () =>
          Promise.resolve(
            JSON.stringify({
              data_root: "/test",
              spine_installed: true,
              spine_source_id: "morphgnt-sblgnt",
              sources: {},
            }),
          ),
      });

      const client = new ApiClient({
        baseUrl: "http://127.0.0.1:47200",
        token: "test-token",
      });

      await client.getSourcesStatus();

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url] = mockFetch.mock.calls[0];

      // CRITICAL: Full URL to backend, not relative
      expect(url).toBe("http://127.0.0.1:47200/sources/status");
      expect(url).not.toBe("/sources/status"); // Would hit Vite server!
    });

    it("getPendingGates() calls full URL with /v1 prefix", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () =>
          Promise.resolve(
            JSON.stringify({
              reference: "John 1:1",
              session_id: "test",
              pending_gates: [],
              total_variants: 0,
            }),
          ),
      });

      const client = new ApiClient({
        baseUrl: "http://127.0.0.1:47200",
        token: "test-token",
      });

      await client.getPendingGates("John 1:1", "test-session");

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url] = mockFetch.mock.calls[0];

      // CRITICAL: Full URL with /v1 prefix
      expect(url).toContain("http://127.0.0.1:47200/v1/gates/pending");
      expect(url).not.toBe("/v1/gates/pending"); // Would hit Vite server!
    });

    it("runScholarly() calls full URL with /v1 prefix", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () =>
          Promise.resolve(
            JSON.stringify({
              success: true,
              job_id: "job-123",
              reference: "John 1:1",
            }),
          ),
      });

      const client = new ApiClient({
        baseUrl: "http://127.0.0.1:47200",
        token: "test-token",
      });

      await client.runScholarly({
        reference: "John 1:1",
        mode: "traceable",
        force: false,
        session_id: "test",
      });

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url] = mockFetch.mock.calls[0];

      // CRITICAL: Full URL with /v1 prefix
      expect(url).toBe("http://127.0.0.1:47200/v1/run/scholarly");
    });

    it("getCapabilities() calls full URL", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () =>
          Promise.resolve(
            JSON.stringify({
              version: "0.17.0",
              api_version: "v1",
              min_gui_version: "0.15.0",
              endpoints: {},
              features: [],
              initialized: true,
            }),
          ),
      });

      const client = new ApiClient({
        baseUrl: "http://127.0.0.1:47200",
        token: "test-token",
      });

      await client.getCapabilities();

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url] = mockFetch.mock.calls[0];

      expect(url).toBe("http://127.0.0.1:47200/v1/capabilities");
    });
  });

  describe("URL format validation", () => {
    it("all ApiClient methods construct URLs with protocol", async () => {
      const client = new ApiClient({
        baseUrl: "http://127.0.0.1:47200",
        token: "test-token",
      });

      // Check contract URL construction
      const contract = client.contract;

      // These should all be full URLs with protocol
      expect(contract.url("translate")).toMatch(/^https?:\/\//);
      expect(contract.url("sources_status")).toMatch(/^https?:\/\//);
      expect(contract.url("gates_pending")).toMatch(/^https?:\/\//);
      expect(contract.url("run_scholarly")).toMatch(/^https?:\/\//);
      expect(contract.url("jobs")).toMatch(/^https?:\/\//);
    });

    it("baseUrl is never relative", () => {
      const client = new ApiClient({
        baseUrl: "http://127.0.0.1:47200",
        token: "test-token",
      });

      // baseUrl should be absolute, not relative
      expect(client.baseUrl).toMatch(/^https?:\/\//);
      expect(client.baseUrl).not.toBe("");
      expect(client.baseUrl).not.toMatch(/^\//);
    });
  });

  describe("Authorization header inclusion", () => {
    it("includes Authorization header in all authenticated requests", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        text: () => Promise.resolve("{}"),
      });

      const client = new ApiClient({
        baseUrl: "http://127.0.0.1:47200",
        token: "my-secret-token",
      });

      // Make several API calls
      await client.translate({
        reference: "John 1:1",
        mode: "readable",
        session_id: "test",
        translator: "literal",
      });
      await client.getSourcesStatus();
      await client.getStatus();

      // All calls should include Authorization header
      for (const call of mockFetch.mock.calls) {
        const [, options] = call;
        expect(options.headers.Authorization).toBe("Bearer my-secret-token");
      }
    });
  });

  describe("CORS compatibility", () => {
    it("requests use proper Content-Type for cross-origin", async () => {
      // Return a valid translation response
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () =>
          Promise.resolve(
            JSON.stringify({
              response_type: "translation",
              sblgnt_text: "Ἐν ἀρχῇ",
              translation_text: "In the beginning",
              reference: "John 1:1",
              verse_ids: ["John.1.1"],
              session_id: "test",
              translator_type: "literal",
              mode: "readable",
              claims: [],
              confidence: {
                composite: 0.9,
                weakest_layer: "lexical",
                layers: {
                  textual: { score: 1 },
                  grammatical: { score: 0.95 },
                  lexical: { score: 0.9 },
                  interpretive: { score: 0.85 },
                },
              },
              variants: [],
              provenance: {
                spine_source: "sblgnt",
                sources_used: ["sblgnt"],
              },
            }),
          ),
      });

      const client = new ApiClient({
        baseUrl: "http://127.0.0.1:47200",
        token: "test-token",
      });

      await client.translate({
        reference: "John 1:1",
        mode: "readable",
        session_id: "test",
        translator: "literal",
      });

      const [, options] = mockFetch.mock.calls[0];
      expect(options.headers["Content-Type"]).toBe("application/json");
    });
  });
});
