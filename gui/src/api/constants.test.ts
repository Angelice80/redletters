/**
 * Tests for connection constants and utilities.
 *
 * Sprint 22: Tests for URL builder and auto-detect backend.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  DEFAULT_PORT,
  FALLBACK_PORTS,
  ENGINE_START_COMMAND,
  CONNECTION_TIMEOUT_MS,
  buildBaseUrl,
  detectBackendPort,
} from "./constants";

describe("constants", () => {
  it("exports correct default port", () => {
    expect(DEFAULT_PORT).toBe(47200);
  });

  it("exports fallback ports in order of preference", () => {
    expect(FALLBACK_PORTS).toEqual([47200, 8000, 5000]);
    // First port should be the default
    expect(FALLBACK_PORTS[0]).toBe(DEFAULT_PORT);
  });

  it("exports correct engine start command", () => {
    expect(ENGINE_START_COMMAND).toBe("redletters engine start");
    // Should NOT contain 'serve'
    expect(ENGINE_START_COMMAND).not.toContain("serve");
  });

  it("exports reasonable connection timeout", () => {
    expect(CONNECTION_TIMEOUT_MS).toBe(2000);
    // Should be between 1-5 seconds
    expect(CONNECTION_TIMEOUT_MS).toBeGreaterThanOrEqual(1000);
    expect(CONNECTION_TIMEOUT_MS).toBeLessThanOrEqual(5000);
  });
});

describe("buildBaseUrl", () => {
  it("builds URL with default host", () => {
    expect(buildBaseUrl(47200)).toBe("http://127.0.0.1:47200");
  });

  it("builds URL with custom host", () => {
    expect(buildBaseUrl(8000, "localhost")).toBe("http://localhost:8000");
  });

  it("builds URL with various ports", () => {
    expect(buildBaseUrl(80)).toBe("http://127.0.0.1:80");
    expect(buildBaseUrl(443)).toBe("http://127.0.0.1:443");
    expect(buildBaseUrl(3000)).toBe("http://127.0.0.1:3000");
  });
});

describe("detectBackendPort", () => {
  const mockFetch = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", mockFetch);
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns null when no backends are reachable", async () => {
    mockFetch.mockRejectedValue(new Error("Connection refused"));

    const result = await detectBackendPort([47200], 100);

    expect(result).toBeNull();
    expect(mockFetch).toHaveBeenCalledWith(
      "http://127.0.0.1:47200/",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("returns port when backend responds with 200", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ version: "1.0.0" }),
    });

    const result = await detectBackendPort([47200], 100);

    expect(result).toEqual({
      port: 47200,
      requiresAuth: false,
      version: "1.0.0",
    });
  });

  it("returns port with requiresAuth when backend returns 401", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 401,
    });

    const result = await detectBackendPort([47200], 100);

    expect(result).toEqual({
      port: 47200,
      requiresAuth: true,
    });
  });

  it("tries ports in order until one responds", async () => {
    mockFetch
      .mockRejectedValueOnce(new Error("Connection refused")) // 47200 fails
      .mockResolvedValueOnce({
        // 8000 succeeds
        ok: true,
        status: 200,
        json: async () => ({ version: "2.0.0" }),
      });

    const result = await detectBackendPort([47200, 8000], 100);

    expect(result).toEqual({
      port: 8000,
      requiresAuth: false,
      version: "2.0.0",
    });
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("handles non-JSON response gracefully", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => {
        throw new Error("Invalid JSON");
      },
    });

    const result = await detectBackendPort([47200], 100);

    expect(result).toEqual({
      port: 47200,
      requiresAuth: false,
    });
  });

  it("skips ports with unexpected status codes", async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: false, status: 500 }) // 47200 error
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
      }); // 8000 ok

    const result = await detectBackendPort([47200, 8000], 100);

    expect(result).toEqual({
      port: 8000,
      requiresAuth: false,
    });
  });

  it("uses AbortController for timeout", async () => {
    // Check that AbortSignal is passed to fetch
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({}),
    });

    await detectBackendPort([47200], 100);

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        signal: expect.any(AbortSignal),
      }),
    );
  });
});
