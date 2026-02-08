import { describe, it, expect } from "vitest";
import {
  computeSummary,
  renderReportMarkdown,
  canonicalJsonStable,
  computePackListHash,
  type GateStep,
  type GateReport,
  type Fingerprint,
  type SourcePackInfo,
} from "./visualGateReport";

function makeStep(
  step: number,
  name: string,
  pass: boolean,
  screenshot = `${String(step).padStart(2, "0")}-${name}.png`,
): GateStep {
  return {
    step,
    name,
    screenshot,
    assertions: [
      {
        name: `${name}-check`,
        selector: `[data-testid="${name}"]`,
        expected: "visible",
        actual: pass ? "visible" : "hidden",
        pass,
      },
    ],
  };
}

const sampleFingerprint: Fingerprint = {
  gitCommit: "abc1234",
  baseUrl: "http://localhost:1420",
  requestParams: {
    ref: "John 3:16",
    translator: "literal",
    requestMode: "readable",
    viewMode: "readable",
  },
  compareParams: {
    compareA: { translator: "literal", mode: "readable" },
    compareB: { translator: "fluent", mode: "readable" },
  },
  installedPacks: {
    count: 2,
    packs: [
      { id: "na28", name: "NA28 Greek Text", version: "1.0.0" },
      { id: "senses", name: "Lexical Senses", version: "2.1.0" },
    ],
    packListHash: "abc123def456",
  },
  packInfoAvailable: true,
};

// ── computeSummary (existing) ─────────────────────────

describe("computeSummary", () => {
  it("returns UNKNOWN for empty steps", () => {
    const s = computeSummary([]);
    expect(s.gate).toBe("UNKNOWN");
    expect(s.totalSteps).toBe(0);
    expect(s.totalScreenshots).toBe(0);
    expect(s.missingScreenshotsCount).toBe(0);
  });

  it("returns PASS when all assertions pass and no screenshot opts", () => {
    const steps = [makeStep(1, "a", true), makeStep(2, "b", true)];
    const s = computeSummary(steps);
    expect(s.gate).toBe("PASS");
    expect(s.passedSteps).toBe(2);
    expect(s.failedSteps).toBe(0);
    expect(s.totalScreenshots).toBe(0);
    expect(s.missingScreenshotsCount).toBe(0);
  });

  it("returns FAIL when any assertion fails", () => {
    const steps = [makeStep(1, "a", true), makeStep(2, "b", false)];
    const s = computeSummary(steps);
    expect(s.gate).toBe("FAIL");
    expect(s.passedSteps).toBe(1);
    expect(s.failedSteps).toBe(1);
  });

  it("returns FAIL when screenshots are missing", () => {
    const steps = Array.from({ length: 8 }, (_, i) =>
      makeStep(i + 1, `step${i + 1}`, true),
    );
    const paths = steps.map((s) => `screenshots/${s.screenshot}`);
    const s = computeSummary(steps, {
      screenshotPaths: paths,
      existsFn: (p) => !p.includes("step3"),
    });
    expect(s.gate).toBe("FAIL");
    expect(s.totalScreenshots).toBe(8);
    expect(s.missingScreenshotsCount).toBe(1);
  });

  it("returns FAIL when fewer than 8 screenshots", () => {
    const steps = Array.from({ length: 5 }, (_, i) =>
      makeStep(i + 1, `step${i + 1}`, true),
    );
    const paths = steps.map((s) => `screenshots/${s.screenshot}`);
    const s = computeSummary(steps, {
      screenshotPaths: paths,
      existsFn: () => true,
    });
    expect(s.gate).toBe("FAIL");
    expect(s.totalScreenshots).toBe(5);
  });

  it("returns PASS when 8+ screenshots all exist", () => {
    const steps = Array.from({ length: 12 }, (_, i) =>
      makeStep(i + 1, `step${i + 1}`, true),
    );
    const paths = steps.map((s) => `screenshots/${s.screenshot}`);
    const s = computeSummary(steps, {
      screenshotPaths: paths,
      existsFn: () => true,
    });
    expect(s.gate).toBe("PASS");
    expect(s.totalScreenshots).toBe(12);
    expect(s.missingScreenshotsCount).toBe(0);
  });

  it("includes hasFingerprint=false and hasManifest=false by default", () => {
    const steps = [makeStep(1, "a", true)];
    const s = computeSummary(steps);
    expect(s.hasFingerprint).toBe(false);
    expect(s.hasManifest).toBe(false);
  });
});

// ── computeSummary RELEASE mode ───────────────────────

describe("computeSummary RELEASE mode", () => {
  function make12Steps() {
    return Array.from({ length: 12 }, (_, i) =>
      makeStep(i + 1, `step${i + 1}`, true),
    );
  }
  function make12Paths(steps: GateStep[]) {
    return steps.map((s) => `screenshots/${s.screenshot}`);
  }

  it("FAILS in RELEASE mode without fingerprint", () => {
    const steps = make12Steps();
    const s = computeSummary(steps, {
      screenshotPaths: make12Paths(steps),
      existsFn: () => true,
      laneMode: "RELEASE",
    });
    expect(s.gate).toBe("FAIL");
    expect(s.hasFingerprint).toBe(false);
  });

  it("FAILS in RELEASE mode without manifest", () => {
    const steps = make12Steps();
    const s = computeSummary(steps, {
      screenshotPaths: make12Paths(steps),
      existsFn: () => true,
      laneMode: "RELEASE",
      fingerprint: sampleFingerprint,
      hasManifest: false,
    });
    expect(s.gate).toBe("FAIL");
    expect(s.hasManifest).toBe(false);
  });

  it("FAILS in RELEASE mode when packInfoAvailable=false and no reason", () => {
    const badFp: Fingerprint = {
      ...sampleFingerprint,
      packInfoAvailable: false,
    };
    const steps = make12Steps();
    const s = computeSummary(steps, {
      screenshotPaths: make12Paths(steps),
      existsFn: () => true,
      laneMode: "RELEASE",
      fingerprint: badFp,
      hasManifest: true,
    });
    expect(s.gate).toBe("FAIL");
  });

  it("PASSES in RELEASE mode when packInfoAvailable=false WITH reason", () => {
    const fpWithReason: Fingerprint = {
      ...sampleFingerprint,
      packInfoAvailable: false,
      packInfoUnavailableReason: "Backend offline",
    };
    const steps = make12Steps();
    const s = computeSummary(steps, {
      screenshotPaths: make12Paths(steps),
      existsFn: () => true,
      laneMode: "RELEASE",
      fingerprint: fpWithReason,
      hasManifest: true,
    });
    expect(s.gate).toBe("PASS");
  });

  it("FAILS in RELEASE mode without compareParams", () => {
    const fpNoCompare: Fingerprint = {
      ...sampleFingerprint,
      compareParams: undefined,
    };
    const steps = make12Steps();
    const s = computeSummary(steps, {
      screenshotPaths: make12Paths(steps),
      existsFn: () => true,
      laneMode: "RELEASE",
      fingerprint: fpNoCompare,
      hasManifest: true,
    });
    expect(s.gate).toBe("FAIL");
  });

  it("PASSES in RELEASE mode with fingerprint + manifest + compareParams", () => {
    const steps = make12Steps();
    const s = computeSummary(steps, {
      screenshotPaths: make12Paths(steps),
      existsFn: () => true,
      laneMode: "RELEASE",
      fingerprint: sampleFingerprint,
      hasManifest: true,
    });
    expect(s.gate).toBe("PASS");
    expect(s.hasFingerprint).toBe(true);
    expect(s.hasManifest).toBe(true);
  });

  it("PASSES in SMOKE mode without fingerprint or manifest", () => {
    const steps = make12Steps();
    const s = computeSummary(steps, {
      screenshotPaths: make12Paths(steps),
      existsFn: () => true,
      laneMode: "SMOKE",
    });
    expect(s.gate).toBe("PASS");
  });
});

// ── canonicalJsonStable ───────────────────────────────

describe("canonicalJsonStable", () => {
  it("sorts object keys alphabetically", () => {
    const result = canonicalJsonStable({ z: 1, a: 2, m: 3 });
    expect(result).toBe('{"a":2,"m":3,"z":1}');
  });

  it("sorts nested object keys", () => {
    const result = canonicalJsonStable({ b: { d: 1, c: 2 }, a: 3 });
    expect(result).toBe('{"a":3,"b":{"c":2,"d":1}}');
  });

  it("preserves array order", () => {
    const result = canonicalJsonStable([3, 1, 2]);
    expect(result).toBe("[3,1,2]");
  });

  it("produces identical output for equivalent objects regardless of key order", () => {
    const a = { name: "pack1", id: "p1", version: "1.0" };
    const b = { version: "1.0", name: "pack1", id: "p1" };
    expect(canonicalJsonStable(a)).toBe(canonicalJsonStable(b));
  });

  it("handles null and primitives", () => {
    expect(canonicalJsonStable(null)).toBe("null");
    expect(canonicalJsonStable(42)).toBe("42");
    expect(canonicalJsonStable("hello")).toBe('"hello"');
  });
});

// ── computePackListHash ───────────────────────────────

describe("computePackListHash", () => {
  it("produces same hash regardless of input pack order", () => {
    const packs: SourcePackInfo[] = [
      { id: "b", name: "Pack B", version: "2.0" },
      { id: "a", name: "Pack A", version: "1.0" },
    ];
    const reversed = [...packs].reverse();
    const mockHash = (s: string) => `hash:${s}`;
    expect(computePackListHash(packs, mockHash)).toBe(
      computePackListHash(reversed, mockHash),
    );
  });

  it("calls hashFn with canonical JSON of id-sorted packs", () => {
    const packs: SourcePackInfo[] = [
      { id: "a", name: "Pack A", version: "1.0" },
    ];
    let called = "";
    const mockHash = (s: string) => {
      called = s;
      return "deadbeef";
    };
    const result = computePackListHash(packs, mockHash);
    expect(result).toBe("deadbeef");
    expect(called).toBe('[{"id":"a","name":"Pack A","version":"1.0"}]');
  });

  it("handles empty pack list", () => {
    const mockHash = (s: string) => `hash:${s}`;
    const result = computePackListHash([], mockHash);
    expect(result).toBe("hash:[]");
  });
});

// ── renderReportMarkdown ──────────────────────────────

describe("renderReportMarkdown", () => {
  it("includes screenshot artifacts section when paths present", () => {
    const report: GateReport = {
      timestamp: "2026-02-07T20:00:00Z",
      gitCommit: "abc1234",
      baseUrl: "http://localhost:1420",
      mcpNamespace: "mcp__puppeteer__",
      mcpTools: ["puppeteer_screenshot"],
      screenshotPaths: [
        "gui/_mcp_artifacts/latest/screenshots/01-load.png",
        "gui/_mcp_artifacts/latest/screenshots/02-click.png",
      ],
      steps: [makeStep(1, "load", true), makeStep(2, "click", true)],
      summary: computeSummary(
        [makeStep(1, "load", true), makeStep(2, "click", true)],
        {
          screenshotPaths: [
            "gui/_mcp_artifacts/latest/screenshots/01-load.png",
            "gui/_mcp_artifacts/latest/screenshots/02-click.png",
          ],
          existsFn: () => true,
        },
      ),
    };
    const md = renderReportMarkdown(report);
    expect(md).toContain("## Screenshot Artifacts");
    expect(md).toContain("01-load.png");
    expect(md).toContain("02-click.png");
    expect(md).toContain("2 on disk, 0 missing");
  });

  it("omits screenshot section when paths empty", () => {
    const report: GateReport = {
      timestamp: "2026-02-07T20:00:00Z",
      gitCommit: "abc1234",
      baseUrl: "http://localhost:1420",
      mcpNamespace: "mcp__puppeteer__",
      mcpTools: [],
      screenshotPaths: [],
      steps: [],
      summary: computeSummary([]),
    };
    const md = renderReportMarkdown(report);
    expect(md).not.toContain("## Screenshot Artifacts");
  });

  it("renders fingerprint section when present", () => {
    const report: GateReport = {
      timestamp: "2026-02-07T20:00:00Z",
      gitCommit: "abc1234",
      baseUrl: "http://localhost:1420",
      mcpNamespace: "mcp__puppeteer__",
      mcpTools: [],
      laneMode: "RELEASE",
      fingerprint: sampleFingerprint,
      screenshotPaths: [],
      steps: [],
      summary: computeSummary([], {
        fingerprint: sampleFingerprint,
        laneMode: "RELEASE",
      }),
    };
    const md = renderReportMarkdown(report);
    expect(md).toContain("## Fingerprint");
    expect(md).toContain("John 3:16");
    expect(md).toContain("NA28 Greek Text");
    expect(md).toContain("abc123def456");
    expect(md).toContain("### Request Parameters");
    expect(md).toContain("### Installed Source Packs");
    expect(md).toContain("Lane Mode | RELEASE");
    expect(md).toContain("Fingerprint | present");
  });

  it("renders compare parameters when present", () => {
    const report: GateReport = {
      timestamp: "2026-02-07T20:00:00Z",
      gitCommit: "abc1234",
      baseUrl: "http://localhost:1420",
      mcpNamespace: "mcp__puppeteer__",
      mcpTools: [],
      laneMode: "RELEASE",
      fingerprint: sampleFingerprint,
      screenshotPaths: [],
      steps: [],
      summary: computeSummary([]),
    };
    const md = renderReportMarkdown(report);
    expect(md).toContain("### Compare Parameters");
    expect(md).toContain("literal");
    expect(md).toContain("fluent");
  });

  it("omits compare section when compareParams absent", () => {
    const fpNoCompare = { ...sampleFingerprint, compareParams: undefined };
    const report: GateReport = {
      timestamp: "2026-02-07T20:00:00Z",
      gitCommit: "abc1234",
      baseUrl: "http://localhost:1420",
      mcpNamespace: "mcp__puppeteer__",
      mcpTools: [],
      fingerprint: fpNoCompare,
      screenshotPaths: [],
      steps: [],
      summary: computeSummary([]),
    };
    const md = renderReportMarkdown(report);
    expect(md).not.toContain("### Compare Parameters");
  });

  it("shows lane mode and manifest status", () => {
    const report: GateReport = {
      timestamp: "2026-02-07T20:00:00Z",
      gitCommit: "abc1234",
      baseUrl: "http://localhost:1420",
      mcpNamespace: "mcp__puppeteer__",
      mcpTools: [],
      screenshotPaths: [],
      steps: [],
      summary: computeSummary([]),
    };
    const md = renderReportMarkdown(report);
    expect(md).toContain("Lane Mode | SMOKE");
    expect(md).toContain("Fingerprint | missing");
    expect(md).toContain("Manifest | missing");
  });
});
