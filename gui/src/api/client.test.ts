/**
 * Tests for API client error normalization and capability validation.
 *
 * Sprint 17: Ensures error handling and compatibility checks work correctly.
 */

import { describe, it, expect } from "vitest";
import { ApiError, normalizeApiError, validateCapabilities } from "./client";
import type { ApiCapabilities } from "./types";

describe("normalizeApiError", () => {
  it("normalizes network error (fetch failed)", () => {
    const error = new TypeError("Failed to fetch");
    const result = normalizeApiError("GET", "/v1/test", error);

    expect(result.category).toBe("network");
    expect(result.status).toBeNull();
    expect(result.method).toBe("GET");
    expect(result.url).toBe("/v1/test");
    expect(result.likelyCause).toContain("Connection refused");
    expect(result.suggestions.length).toBeGreaterThan(0);
  });

  it("normalizes 401 auth error", () => {
    const error = new ApiError(401, "unauthorized", "Invalid token");
    const result = normalizeApiError("POST", "/translate", error);

    expect(result.category).toBe("auth");
    expect(result.status).toBe(401);
    expect(result.likelyCause).toContain("token");
    expect(result.suggestions).toContainEqual(
      expect.stringContaining("Refresh"),
    );
  });

  it("normalizes 404 not found error", () => {
    const error = new ApiError(404, "not_found", "Endpoint not found");
    const result = normalizeApiError("GET", "/v1/unknown", error);

    expect(result.category).toBe("not_found");
    expect(result.status).toBe(404);
    expect(result.likelyCause).toContain("endpoint");
    expect(result.suggestions).toContainEqual(
      expect.stringContaining("0.16.0"),
    );
  });

  it("normalizes 409 gate blocked error", () => {
    const error = new ApiError(409, "gate_blocked", "Variants need ack");
    const result = normalizeApiError("POST", "/v1/run/scholarly", error);

    expect(result.category).toBe("gate_blocked");
    expect(result.status).toBe(409);
    expect(result.likelyCause).toContain("acknowledgement");
    expect(result.suggestions).toContainEqual(
      expect.stringContaining("acknowledge"),
    );
  });

  it("normalizes 503 service unavailable error", () => {
    const error = new ApiError(503, "unavailable", "Engine not initialized");
    const result = normalizeApiError("GET", "/v1/engine/status", error);

    expect(result.category).toBe("service_unavailable");
    expect(result.status).toBe(503);
    expect(result.likelyCause).toContain("initialized");
    expect(result.suggestions).toContainEqual(expect.stringContaining("Wait"));
  });

  it("normalizes 500 server error", () => {
    const error = new ApiError(500, "internal_error", "Something broke");
    const result = normalizeApiError("POST", "/translate", error);

    expect(result.category).toBe("server");
    expect(result.status).toBe(500);
    expect(result.likelyCause).toContain("internal");
    expect(result.suggestions).toContainEqual(expect.stringContaining("logs"));
  });

  it("normalizes unknown error", () => {
    const error = { unexpected: "shape" };
    const result = normalizeApiError("GET", "/v1/test", error);

    expect(result.category).toBe("unknown");
    expect(result.status).toBeNull();
    expect(result.timestamp).toBeDefined();
  });

  it("includes timestamp in all errors", () => {
    const error = new ApiError(400, "bad_request", "Bad input");
    const result = normalizeApiError("POST", "/test", error);

    expect(result.timestamp).toBeDefined();
    // Should be ISO format
    expect(() => new Date(result.timestamp)).not.toThrow();
  });
});

describe("validateCapabilities", () => {
  const baseCapabilities: ApiCapabilities = {
    version: "0.17.0",
    api_version: "v1",
    min_gui_version: "0.15.0",
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
    features: ["translation", "sources", "variants"],
    initialized: true,
  };

  it("validates compatible capabilities", () => {
    const result = validateCapabilities(baseCapabilities);

    expect(result.valid).toBe(true);
    expect(result.error).toBeUndefined();
    expect(result.missingEndpoints).toBeUndefined();
    expect(result.versionMismatch).toBeUndefined();
  });

  it("detects version mismatch (GUI too old)", () => {
    const caps: ApiCapabilities = {
      ...baseCapabilities,
      min_gui_version: "99.0.0", // Future version requirement
    };
    const result = validateCapabilities(caps);

    expect(result.valid).toBe(false);
    expect(result.versionMismatch).toBeDefined();
    expect(result.versionMismatch!.required).toBe("99.0.0");
    expect(result.error).toContain("99.0.0");
  });

  it("detects missing required endpoints", () => {
    const caps: ApiCapabilities = {
      ...baseCapabilities,
      endpoints: {
        ...baseCapabilities.endpoints,
        translate: "", // Missing
        sources: "", // Missing
      },
    };
    const result = validateCapabilities(caps);

    expect(result.valid).toBe(false);
    expect(result.missingEndpoints).toBeDefined();
    expect(result.missingEndpoints).toContain("translate");
    expect(result.missingEndpoints).toContain("sources");
  });

  it("accepts exact version match", () => {
    const caps: ApiCapabilities = {
      ...baseCapabilities,
      min_gui_version: "0.17.0", // Exact match with GUI_VERSION
    };
    const result = validateCapabilities(caps);

    expect(result.valid).toBe(true);
  });

  it("accepts older min_gui_version requirement", () => {
    const caps: ApiCapabilities = {
      ...baseCapabilities,
      min_gui_version: "0.10.0", // Older than current GUI
    };
    const result = validateCapabilities(caps);

    expect(result.valid).toBe(true);
  });
});

describe("ApiErrorDetail structure", () => {
  it("has all required fields for display", () => {
    const error = new ApiError(500, "test_error", "Test message");
    const detail = normalizeApiError("POST", "/api/test", error);

    // Required for ApiErrorPanel display
    expect(detail).toHaveProperty("method");
    expect(detail).toHaveProperty("url");
    expect(detail).toHaveProperty("status");
    expect(detail).toHaveProperty("statusText");
    expect(detail).toHaveProperty("responseSnippet");
    expect(detail).toHaveProperty("suggestedFix");
    expect(detail).toHaveProperty("timestamp");
    expect(detail).toHaveProperty("category");
    expect(detail).toHaveProperty("likelyCause");
    expect(detail).toHaveProperty("suggestions");
  });

  it("suggestions array is never empty", () => {
    const testCases = [
      new TypeError("Failed to fetch"),
      new ApiError(401, "auth", "Unauthorized"),
      new ApiError(404, "not_found", "Not found"),
      new ApiError(500, "server", "Server error"),
      { random: "object" },
    ];

    for (const error of testCases) {
      const detail = normalizeApiError("GET", "/test", error);
      expect(detail.suggestions.length).toBeGreaterThan(0);
    }
  });

  // Sprint 17: contractDiagnostics support
  it("includes contractDiagnostics when provided", () => {
    const error = new ApiError(404, "not_found", "Endpoint not found");
    const contractDiags = {
      baseUrl: "http://127.0.0.1:47200",
      hasCapabilities: true,
      capabilities: {
        version: "0.17.0",
        api_version: "v1",
        min_gui_version: "0.15.0",
        features: ["translation"],
        initialized: true,
      },
      resolvedEndpoints: {
        translate: "/translate",
        sources: "/sources",
      },
    };

    const detail = normalizeApiError("GET", "/unknown", error, contractDiags);

    expect(detail.contractDiagnostics).toBeDefined();
    expect(detail.contractDiagnostics?.baseUrl).toBe("http://127.0.0.1:47200");
    expect(detail.contractDiagnostics?.hasCapabilities).toBe(true);
    expect(detail.contractDiagnostics?.capabilities?.version).toBe("0.17.0");
  });

  it("contractDiagnostics is undefined when not provided", () => {
    const error = new ApiError(500, "error", "Server error");
    const detail = normalizeApiError("POST", "/api/test", error);

    expect(detail.contractDiagnostics).toBeUndefined();
  });
});
