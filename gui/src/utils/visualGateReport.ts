/**
 * Visual Gate Report types and helpers.
 *
 * Used by Claude (via Puppeteer MCP) to produce structured
 * on-disk evidence packs after a visual gate run.
 *
 * This module is consumed by Node scripts that write report
 * files; it is NOT imported by the runtime GUI bundle.
 */

// ── Types ──────────────────────────────────────────────

export interface GateAssertion {
  name: string;
  selector: string | null;
  expected: string;
  actual: string;
  pass: boolean;
}

export interface GateStep {
  step: number;
  name: string;
  screenshot: string;
  assertions: GateAssertion[];
}

// ── Fingerprint types ──────────────────────────────────

export interface SourcePackInfo {
  id: string;
  name: string;
  version: string;
}

export interface RequestParams {
  ref: string;
  translator: string;
  requestMode: string;
  viewMode: string;
}

export interface CompareParams {
  compareA: { translator: string; mode: string };
  compareB: { translator: string; mode: string };
}

export interface Fingerprint {
  gitCommit: string;
  appVersion?: string;
  buildVersion?: string;
  baseUrl: string;
  requestParams: RequestParams;
  compareParams?: CompareParams;
  installedPacks: {
    count: number;
    packs: SourcePackInfo[];
    packListHash: string;
  };
  packInfoAvailable: boolean;
  packInfoUnavailableReason?: string;
}

export type LaneMode = "SMOKE" | "RELEASE";

// ── Summary & Report ───────────────────────────────────

export interface GateSummary {
  totalSteps: number;
  passedSteps: number;
  failedSteps: number;
  totalAssertions: number;
  passedAssertions: number;
  failedAssertions: number;
  totalScreenshots: number;
  missingScreenshotsCount: number;
  hasFingerprint: boolean;
  hasManifest: boolean;
  gate: "PASS" | "FAIL" | "UNKNOWN";
}

export interface GateReport {
  timestamp: string;
  gitCommit: string;
  baseUrl: string;
  mcpNamespace: string;
  mcpTools: string[];
  laneMode?: LaneMode;
  fingerprint?: Fingerprint;
  steps: GateStep[];
  screenshotPaths: string[];
  summary: GateSummary;
}

export interface IndexEntry {
  timestamp: string;
  gitCommit: string;
  gate: "PASS" | "FAIL" | "UNKNOWN";
  releasePath: string;
  totalSteps: number;
  passedAssertions: number;
  totalAssertions: number;
}

// ── Helpers ────────────────────────────────────────────

/**
 * Produce canonical JSON with sorted keys for deterministic hashing.
 * Arrays preserve order; object keys are sorted recursively.
 */
export function canonicalJsonStable(obj: unknown): string {
  return JSON.stringify(obj, (_key, value) => {
    if (value !== null && typeof value === "object" && !Array.isArray(value)) {
      const sorted: Record<string, unknown> = {};
      for (const k of Object.keys(value as Record<string, unknown>).sort()) {
        sorted[k] = (value as Record<string, unknown>)[k];
      }
      return sorted;
    }
    return value;
  });
}

/**
 * Compute a stable hash of the source pack list.
 * Packs are sorted by id before hashing.
 * hashFn must produce a hex-encoded SHA-256 digest from a string.
 */
export function computePackListHash(
  packs: SourcePackInfo[],
  hashFn: (data: string) => string,
): string {
  const sorted = [...packs].sort((a, b) => a.id.localeCompare(b.id));
  return hashFn(canonicalJsonStable(sorted));
}

// ── Summary computation ────────────────────────────────

export interface ComputeSummaryOpts {
  screenshotPaths?: string[];
  existsFn?: (path: string) => boolean;
  laneMode?: LaneMode;
  fingerprint?: Fingerprint;
  hasManifest?: boolean;
}

/** Compute summary from completed steps with optional screenshot verification. */
export function computeSummary(
  steps: GateStep[],
  opts: ComputeSummaryOpts = {},
): GateSummary {
  let passedSteps = 0;
  let failedSteps = 0;
  let totalAssertions = 0;
  let passedAssertions = 0;
  let failedAssertions = 0;

  for (const step of steps) {
    const stepPassed = step.assertions.every((a) => a.pass);
    if (stepPassed) passedSteps++;
    else failedSteps++;
    for (const a of step.assertions) {
      totalAssertions++;
      if (a.pass) passedAssertions++;
      else failedAssertions++;
    }
  }

  const paths = opts.screenshotPaths ?? [];
  const existsFn = opts.existsFn ?? (() => true);
  const totalScreenshots = paths.length;
  const missingScreenshotsCount = paths.filter((p) => !existsFn(p)).length;

  const laneMode = opts.laneMode ?? "SMOKE";
  const hasFingerprint = opts.fingerprint != null;
  const hasManifest = opts.hasManifest ?? false;

  const hasAssertionFailure = failedAssertions > 0;
  const hasNoSteps = steps.length === 0;
  const hasMissingScreenshots = missingScreenshotsCount > 0;
  const hasTooFewScreenshots = totalScreenshots > 0 && totalScreenshots < 8;

  // RELEASE mode additional requirements
  const releaseMissingFingerprint = laneMode === "RELEASE" && !hasFingerprint;
  const releaseMissingManifest = laneMode === "RELEASE" && !hasManifest;
  const releasePackInfoUnavailable =
    laneMode === "RELEASE" &&
    hasFingerprint &&
    !opts.fingerprint!.packInfoAvailable &&
    !opts.fingerprint!.packInfoUnavailableReason;
  const releaseMissingCompare =
    laneMode === "RELEASE" &&
    hasFingerprint &&
    !opts.fingerprint!.compareParams;

  const gate: GateSummary["gate"] = hasNoSteps
    ? "UNKNOWN"
    : hasAssertionFailure ||
        hasMissingScreenshots ||
        hasTooFewScreenshots ||
        releaseMissingFingerprint ||
        releaseMissingManifest ||
        releasePackInfoUnavailable ||
        releaseMissingCompare
      ? "FAIL"
      : "PASS";

  return {
    totalSteps: steps.length,
    passedSteps,
    failedSteps,
    totalAssertions,
    passedAssertions,
    failedAssertions,
    totalScreenshots,
    missingScreenshotsCount,
    hasFingerprint,
    hasManifest,
    gate,
  };
}

// ── Markdown rendering ─────────────────────────────────

/** Generate Markdown report text from a GateReport. */
export function renderReportMarkdown(report: GateReport): string {
  const { summary } = report;
  const icon =
    summary.gate === "PASS" ? "PASS" : summary.gate === "FAIL" ? "FAIL" : "???";
  const lines: string[] = [
    `# Visual Gate Report — ${icon}`,
    "",
    `| Field | Value |`,
    `|-------|-------|`,
    `| Timestamp | ${report.timestamp} |`,
    `| Git Commit | \`${report.gitCommit}\` |`,
    `| Base URL | ${report.baseUrl} |`,
    `| MCP Namespace | \`${report.mcpNamespace}\` |`,
    `| Lane Mode | ${report.laneMode ?? "SMOKE"} |`,
    `| Gate Result | **${summary.gate}** |`,
    `| Steps | ${summary.passedSteps}/${summary.totalSteps} passed |`,
    `| Assertions | ${summary.passedAssertions}/${summary.totalAssertions} passed |`,
    `| Screenshots | ${summary.totalScreenshots} on disk, ${summary.missingScreenshotsCount} missing |`,
    `| Fingerprint | ${summary.hasFingerprint ? "present" : "missing"} |`,
    `| Manifest | ${summary.hasManifest ? "present" : "missing"} |`,
    "",
  ];

  // Fingerprint section
  if (report.fingerprint) {
    const fp = report.fingerprint;
    lines.push("## Fingerprint");
    lines.push("");
    lines.push("| Field | Value |");
    lines.push("|-------|-------|");
    lines.push(`| Git Commit | \`${fp.gitCommit}\` |`);
    if (fp.appVersion) lines.push(`| App Version | ${fp.appVersion} |`);
    if (fp.buildVersion) lines.push(`| Build Version | ${fp.buildVersion} |`);
    lines.push(`| Base URL | ${fp.baseUrl} |`);
    lines.push(`| Pack Info Available | ${fp.packInfoAvailable} |`);
    if (fp.packInfoUnavailableReason) {
      lines.push(`| Pack Info Reason | ${fp.packInfoUnavailableReason} |`);
    }
    lines.push(`| Installed Packs | ${fp.installedPacks.count} packs |`);
    lines.push(`| Pack List Hash | \`${fp.installedPacks.packListHash}\` |`);
    lines.push("");

    lines.push("### Request Parameters");
    lines.push("");
    lines.push("| Param | Value |");
    lines.push("|-------|-------|");
    lines.push(`| Reference | ${fp.requestParams.ref} |`);
    lines.push(`| Translator | ${fp.requestParams.translator} |`);
    lines.push(`| Request Mode | ${fp.requestParams.requestMode} |`);
    lines.push(`| View Mode | ${fp.requestParams.viewMode} |`);
    lines.push("");

    if (fp.compareParams) {
      lines.push("### Compare Parameters");
      lines.push("");
      lines.push("| Side | Translator | Mode |");
      lines.push("|------|-----------|------|");
      lines.push(
        `| A | ${fp.compareParams.compareA.translator} | ${fp.compareParams.compareA.mode} |`,
      );
      lines.push(
        `| B | ${fp.compareParams.compareB.translator} | ${fp.compareParams.compareB.mode} |`,
      );
      lines.push("");
    }

    if (fp.installedPacks.packs.length > 0) {
      lines.push("### Installed Source Packs");
      lines.push("");
      lines.push("| ID | Name | Version |");
      lines.push("|----|------|---------|");
      for (const p of fp.installedPacks.packs) {
        lines.push(`| ${p.id} | ${p.name} | ${p.version} |`);
      }
      lines.push("");
    }
  }

  lines.push("## Steps");
  lines.push("");

  for (const step of report.steps) {
    const stepOk = step.assertions.every((a) => a.pass);
    lines.push(
      `### Step ${String(step.step).padStart(2, "0")}: ${step.name} — ${stepOk ? "PASS" : "FAIL"}`,
    );
    lines.push("");
    lines.push(`Screenshot: \`${step.screenshot}\``);
    lines.push("");
    if (step.assertions.length > 0) {
      lines.push("| Assertion | Expected | Actual | Result |");
      lines.push("|-----------|----------|--------|--------|");
      for (const a of step.assertions) {
        lines.push(
          `| ${a.name} | ${a.expected} | ${a.actual} | ${a.pass ? "PASS" : "FAIL"} |`,
        );
      }
      lines.push("");
    }
  }

  if (report.screenshotPaths.length > 0) {
    lines.push("## Screenshot Artifacts");
    lines.push("");
    for (const p of report.screenshotPaths) {
      lines.push(`- \`${p}\``);
    }
    lines.push("");
  }

  return lines.join("\n");
}
