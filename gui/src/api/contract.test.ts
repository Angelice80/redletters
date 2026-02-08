/**
 * Tests for ApiContract endpoint resolution.
 *
 * Sprint 17: Ensures endpoint paths are correctly derived from capabilities
 * and fall back to defaults when capabilities unavailable.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { ApiContract, DEFAULT_ENDPOINTS, createApiContract } from "./contract";
import type { ApiCapabilities } from "./types";

describe("ApiContract", () => {
  let contract: ApiContract;

  beforeEach(() => {
    contract = new ApiContract("http://127.0.0.1:47200");
  });

  describe("base URL management", () => {
    it("stores and returns base URL", () => {
      expect(contract.baseUrl).toBe("http://127.0.0.1:47200");
    });

    it("strips trailing slash from base URL", () => {
      const c = new ApiContract("http://127.0.0.1:47200/");
      expect(c.baseUrl).toBe("http://127.0.0.1:47200");
    });

    it("allows updating base URL", () => {
      contract.setBaseUrl("http://localhost:8080");
      expect(contract.baseUrl).toBe("http://localhost:8080");
    });

    it("strips trailing slash when updating", () => {
      contract.setBaseUrl("http://localhost:8080/");
      expect(contract.baseUrl).toBe("http://localhost:8080");
    });
  });

  describe("fallback to defaults (no capabilities)", () => {
    it("uses default translate path", () => {
      expect(contract.translate()).toBe("/translate");
    });

    it("uses default sources path", () => {
      expect(contract.sources()).toBe("/sources");
    });

    it("uses default sources_status path", () => {
      expect(contract.sourcesStatus()).toBe("/sources/status");
    });

    it("uses default gates_pending path", () => {
      expect(contract.gatesPending()).toBe("/v1/gates/pending");
    });

    it("uses default run_scholarly path", () => {
      expect(contract.runScholarly()).toBe("/v1/run/scholarly");
    });

    it("uses default jobs path", () => {
      expect(contract.jobs()).toBe("/v1/jobs");
    });

    it("uses default engine_status path", () => {
      expect(contract.engineStatus()).toBe("/v1/engine/status");
    });

    it("hasCapabilities returns false", () => {
      expect(contract.hasCapabilities).toBe(false);
    });

    it("capabilities is null", () => {
      expect(contract.capabilities).toBeNull();
    });
  });

  describe("endpoint resolution from capabilities", () => {
    const mockCapabilities: ApiCapabilities = {
      version: "0.17.0",
      api_version: "v1",
      min_gui_version: "0.15.0",
      endpoints: {
        engine_status: "/custom/engine/status",
        stream: "/custom/stream",
        jobs: "/custom/jobs",
        gates_pending: "/custom/gates/pending",
        run_scholarly: "/custom/run/scholarly",
        translate: "/custom/translate",
        acknowledge: "/custom/acknowledge",
        sources: "/custom/sources",
        sources_status: "/custom/sources/status",
        variants_dossier: "/custom/variants/dossier",
      },
      features: ["translation", "sources"],
      initialized: true,
    };

    beforeEach(() => {
      contract.setCapabilities(mockCapabilities);
    });

    it("uses capabilities translate path", () => {
      expect(contract.translate()).toBe("/custom/translate");
    });

    it("uses capabilities sources path", () => {
      expect(contract.sources()).toBe("/custom/sources");
    });

    it("uses capabilities gates_pending path", () => {
      expect(contract.gatesPending()).toBe("/custom/gates/pending");
    });

    it("uses capabilities run_scholarly path", () => {
      expect(contract.runScholarly()).toBe("/custom/run/scholarly");
    });

    it("hasCapabilities returns true", () => {
      expect(contract.hasCapabilities).toBe(true);
    });

    it("capabilities returns stored object", () => {
      expect(contract.capabilities).toBe(mockCapabilities);
    });

    it("clearCapabilities reverts to defaults", () => {
      contract.clearCapabilities();
      expect(contract.hasCapabilities).toBe(false);
      expect(contract.translate()).toBe("/translate");
    });
  });

  describe("full URL composition", () => {
    it("composes full URL for endpoint", () => {
      expect(contract.url("translate")).toBe(
        "http://127.0.0.1:47200/translate",
      );
    });

    it("composes URL with path suffix", () => {
      expect(contract.url("jobs", "/abc123")).toBe(
        "http://127.0.0.1:47200/v1/jobs/abc123",
      );
    });

    it("composes URL with query parameters (URLSearchParams)", () => {
      const params = new URLSearchParams({ reference: "John 1:1" });
      expect(contract.urlWithParams("gates_pending", params)).toBe(
        "http://127.0.0.1:47200/v1/gates/pending?reference=John+1%3A1",
      );
    });

    it("composes URL with query parameters (object)", () => {
      expect(
        contract.urlWithParams("gates_pending", { reference: "John 1:1" }),
      ).toBe("http://127.0.0.1:47200/v1/gates/pending?reference=John+1%3A1");
    });
  });

  describe("job-specific endpoints", () => {
    it("composes job by ID path", () => {
      expect(contract.jobById("job-123")).toBe("/v1/jobs/job-123");
    });

    it("composes job receipt path", () => {
      expect(contract.jobReceipt("job-123")).toBe("/v1/jobs/job-123/receipt");
    });

    it("composes job cancel path", () => {
      expect(contract.jobCancel("job-123")).toBe("/v1/jobs/job-123/cancel");
    });
  });

  describe("diagnostics snapshot", () => {
    it("returns snapshot without capabilities", () => {
      const snapshot = contract.getDiagnosticsSnapshot();

      expect(snapshot.baseUrl).toBe("http://127.0.0.1:47200");
      expect(snapshot.hasCapabilities).toBe(false);
      expect(snapshot.capabilities).toBeNull();
      expect(snapshot.resolvedEndpoints).toHaveProperty("translate");
      expect(snapshot.resolvedEndpoints!.translate).toBe("/translate");
    });

    it("returns snapshot with capabilities", () => {
      contract.setCapabilities({
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
        features: ["translation"],
        initialized: true,
      });

      const snapshot = contract.getDiagnosticsSnapshot();

      expect(snapshot.hasCapabilities).toBe(true);
      expect(snapshot.capabilities).not.toBeNull();
      expect(snapshot.capabilities?.version).toBe("0.17.0");
      expect(snapshot.capabilities?.features).toContain("translation");
    });
  });
});

describe("DEFAULT_ENDPOINTS", () => {
  it("has all required engine spine endpoints", () => {
    expect(DEFAULT_ENDPOINTS.engine_status).toBe("/v1/engine/status");
    expect(DEFAULT_ENDPOINTS.capabilities).toBe("/v1/capabilities");
    expect(DEFAULT_ENDPOINTS.stream).toBe("/v1/stream");
    expect(DEFAULT_ENDPOINTS.jobs).toBe("/v1/jobs");
    expect(DEFAULT_ENDPOINTS.gates_pending).toBe("/v1/gates/pending");
    expect(DEFAULT_ENDPOINTS.run_scholarly).toBe("/v1/run/scholarly");
  });

  it("has all required API endpoints", () => {
    expect(DEFAULT_ENDPOINTS.translate).toBe("/translate");
    expect(DEFAULT_ENDPOINTS.acknowledge).toBe("/acknowledge");
    expect(DEFAULT_ENDPOINTS.sources).toBe("/sources");
    expect(DEFAULT_ENDPOINTS.sources_status).toBe("/sources/status");
    expect(DEFAULT_ENDPOINTS.variants_dossier).toBe("/variants/dossier");
  });
});

describe("createApiContract", () => {
  it("creates contract with default port", () => {
    const contract = createApiContract();
    expect(contract.baseUrl).toBe("http://127.0.0.1:47200");
  });

  it("creates contract with custom port", () => {
    const contract = createApiContract(8080);
    expect(contract.baseUrl).toBe("http://127.0.0.1:8080");
  });
});

/**
 * These tests verify that GUI endpoint paths match the backend routes.
 *
 * Backend route locations:
 * - /translate: src/redletters/api/routes.py (line ~198)
 * - /sources/status: src/redletters/api/routes.py (line ~351)
 * - /v1/gates/pending: src/redletters/engine_spine/routes.py (line ~430)
 * - /v1/capabilities: src/redletters/engine_spine/routes.py (line ~49)
 */
describe("endpoint paths match backend", () => {
  let contract: ApiContract;

  beforeEach(() => {
    contract = new ApiContract("http://127.0.0.1:47200");
  });

  it("translate endpoint path matches api/routes.py @router.post('/translate')", () => {
    // Backend: src/redletters/api/routes.py - @router.post("/translate")
    expect(contract.translate()).toBe("/translate");
    expect(contract.url("translate")).toBe("http://127.0.0.1:47200/translate");
  });

  it("sources_status path matches api/routes.py @router.get('/sources/status')", () => {
    // Backend: src/redletters/api/routes.py - @router.get("/sources/status")
    expect(contract.sourcesStatus()).toBe("/sources/status");
    expect(contract.url("sources_status")).toBe(
      "http://127.0.0.1:47200/sources/status",
    );
  });

  it("gates_pending path matches engine_spine/routes.py @router.get('/gates/pending') with /v1 prefix", () => {
    // Backend: src/redletters/engine_spine/routes.py - router prefix="/v1", @router.get("/gates/pending")
    expect(contract.gatesPending()).toBe("/v1/gates/pending");
    expect(contract.url("gates_pending")).toBe(
      "http://127.0.0.1:47200/v1/gates/pending",
    );
  });

  it("capabilities path matches engine_spine/routes.py @router.get('/capabilities') with /v1 prefix", () => {
    // Backend: src/redletters/engine_spine/routes.py - router prefix="/v1", @router.get("/capabilities")
    expect(contract.capabilitiesPath()).toBe("/v1/capabilities");
  });

  it("run_scholarly path matches engine_spine/routes.py @router.post('/run/scholarly') with /v1 prefix", () => {
    // Backend: src/redletters/engine_spine/routes.py - router prefix="/v1", @router.post("/run/scholarly")
    expect(contract.runScholarly()).toBe("/v1/run/scholarly");
  });
});

describe("SSE stream URL construction", () => {
  let contract: ApiContract;

  beforeEach(() => {
    contract = new ApiContract("http://127.0.0.1:47200");
  });

  it("constructs global stream URL", () => {
    expect(contract.globalStreamUrl()).toBe("http://127.0.0.1:47200/v1/stream");
  });

  it("constructs job-specific stream URL with encoded job_id", () => {
    expect(contract.jobStreamUrl("job-123")).toBe(
      "http://127.0.0.1:47200/v1/stream?job_id=job-123",
    );
  });

  it("URL-encodes special characters in job_id", () => {
    expect(contract.jobStreamUrl("job/with?special&chars")).toBe(
      "http://127.0.0.1:47200/v1/stream?job_id=job%2Fwith%3Fspecial%26chars",
    );
  });
});

describe("all DEFAULT_ENDPOINTS use absolute paths", () => {
  it("all endpoints start with /", () => {
    for (const [, path] of Object.entries(DEFAULT_ENDPOINTS)) {
      expect(path).toMatch(/^\//);
    }
  });

  it("no endpoints contain relative paths or full URLs", () => {
    for (const [, path] of Object.entries(DEFAULT_ENDPOINTS)) {
      expect(path).not.toMatch(/^https?:\/\//);
      expect(path).not.toMatch(/^\.\./);
      expect(path).not.toMatch(/^[^/]/);
    }
  });
});
