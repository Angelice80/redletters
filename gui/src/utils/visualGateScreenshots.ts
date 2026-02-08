/**
 * Screenshot persistence helpers for the visual gate.
 *
 * Node-only module — NOT imported by the runtime GUI bundle.
 * Used during MCP visual gate runs to save base64 screenshots as PNG files.
 *
 * Filesystem operations are injected to avoid direct Node imports
 * (gui tsconfig does not include @types/node).
 */

// ── Artifact layout constants ────────────────────────

export const ARTIFACTS_ROOT = "gui/_mcp_artifacts";
export const LATEST_DIR = `${ARTIFACTS_ROOT}/latest`;
export const RELEASES_DIR = `${ARTIFACTS_ROOT}/releases`;
export const SCREENSHOTS_SUBDIR = "screenshots";

/** Build the latest screenshots directory path. */
export function latestScreenshotsDir(): string {
  return `${LATEST_DIR}/${SCREENSHOTS_SUBDIR}`;
}

/** Build a release screenshots directory path. */
export function releaseScreenshotsDir(releaseSlug: string): string {
  return `${RELEASES_DIR}/${releaseSlug}/${SCREENSHOTS_SUBDIR}`;
}

/** Build a release slug from timestamp + short SHA. */
export function buildReleaseSlug(
  isoTimestamp: string,
  shortSha: string,
): string {
  const d = new Date(isoTimestamp);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}_${hh}${mi}_${shortSha}`;
}

// ── Filesystem helpers (dependency-injected) ─────────

export interface FsWriter {
  writeFile: (path: string, data: Uint8Array) => void;
  mkdir: (dir: string) => void;
  exists: (path: string) => boolean;
}

/** Strip the data-URI prefix from a base64 PNG string. */
export function stripBase64Prefix(base64: string): string {
  return base64.replace(/^data:image\/png;base64,/, "");
}

/** Decode a base64 string to bytes. */
export function base64ToBytes(base64: string): Uint8Array {
  const raw = stripBase64Prefix(base64);
  const binary = atob(raw);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

/**
 * Write a base64-encoded PNG screenshot to disk.
 * Creates parent directories if they don't exist.
 */
export function writePngFromBase64(
  filePath: string,
  base64: string,
  fs: FsWriter,
): void {
  // Ensure parent directory exists
  const lastSlash = filePath.lastIndexOf("/");
  if (lastSlash > 0) {
    const dir = filePath.substring(0, lastSlash);
    if (!fs.exists(dir)) {
      fs.mkdir(dir);
    }
  }
  const bytes = base64ToBytes(base64);
  fs.writeFile(filePath, bytes);
}

// ── Release pack copy ────────────────────────────────

export interface FsCopier {
  readFile: (path: string) => Uint8Array;
  writeFile: (path: string, data: Uint8Array) => void;
  mkdir: (dir: string) => void;
  exists: (path: string) => boolean;
}

export interface CopyResult {
  copiedCount: number;
  copiedPaths: string[];
  failedPaths: string[];
}

/**
 * Copy all screenshots referenced in screenshotPaths into
 * `releases/<slug>/screenshots/`, preserving filenames.
 *
 * Source paths may be absolute or repo-relative. Files are
 * flattened into the release screenshots directory (only the
 * basename is kept).
 */
export function copyScreenshotsToRelease(
  screenshotPaths: string[],
  releaseSlug: string,
  fs: FsCopier,
): CopyResult {
  const destDir = releaseScreenshotsDir(releaseSlug);
  if (!fs.exists(destDir)) {
    fs.mkdir(destDir);
  }

  const copiedPaths: string[] = [];
  const failedPaths: string[] = [];

  for (const srcPath of screenshotPaths) {
    const basename = srcPath.substring(srcPath.lastIndexOf("/") + 1);
    const destPath = `${destDir}/${basename}`;
    try {
      const data = fs.readFile(srcPath);
      fs.writeFile(destPath, data);
      copiedPaths.push(destPath);
    } catch {
      failedPaths.push(srcPath);
    }
  }

  return {
    copiedCount: copiedPaths.length,
    copiedPaths,
    failedPaths,
  };
}

// ── Release pack completeness verification ───────────

export interface PackCompleteness {
  complete: boolean;
  expectedCount: number;
  presentCount: number;
  missingFilenames: string[];
}

/**
 * Verify that every screenshotPath from the report has a
 * corresponding file in `releases/<slug>/screenshots/`.
 *
 * Compares by basename only (source paths may differ from
 * the flattened release layout).
 */
export function verifyReleasePackCompleteness(
  screenshotPaths: string[],
  releaseSlug: string,
  existsFn: (path: string) => boolean,
): PackCompleteness {
  const destDir = releaseScreenshotsDir(releaseSlug);
  const missingFilenames: string[] = [];
  let presentCount = 0;

  for (const srcPath of screenshotPaths) {
    const basename = srcPath.substring(srcPath.lastIndexOf("/") + 1);
    const destPath = `${destDir}/${basename}`;
    if (existsFn(destPath)) {
      presentCount++;
    } else {
      missingFilenames.push(basename);
    }
  }

  return {
    complete: missingFilenames.length === 0 && screenshotPaths.length > 0,
    expectedCount: screenshotPaths.length,
    presentCount,
    missingFilenames,
  };
}

// ── Screenshot path verification ─────────────────────

export interface ScreenshotVerification {
  totalScreenshots: number;
  missingScreenshotsCount: number;
  missingPaths: string[];
  presentPaths: string[];
}

/** Verify that all screenshot paths exist on disk. */
export function verifyScreenshotPaths(
  paths: string[],
  existsFn: (path: string) => boolean,
): ScreenshotVerification {
  const missingPaths: string[] = [];
  const presentPaths: string[] = [];
  for (const p of paths) {
    if (existsFn(p)) {
      presentPaths.push(p);
    } else {
      missingPaths.push(p);
    }
  }
  return {
    totalScreenshots: paths.length,
    missingScreenshotsCount: missingPaths.length,
    missingPaths,
    presentPaths,
  };
}
