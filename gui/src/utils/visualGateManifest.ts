/**
 * Release MANIFEST for tamper-evident evidence packs.
 *
 * Provides types and helpers to create SHA256-based file
 * manifests for gate release artifacts. Each release directory
 * gets a MANIFEST.json (machine-readable) and optional
 * MANIFEST.txt (human-readable) that list every file with
 * its size and SHA-256 hash.
 *
 * Filesystem and crypto operations are dependency-injected
 * (gui tsconfig does not include @types/node).
 */

// ── Types ──────────────────────────────────────────────

export interface ManifestFileEntry {
  relativePath: string;
  bytes: number;
  sha256: string;
}

export interface Manifest {
  createdAt: string;
  gitCommit: string;
  baseUrl: string;
  fingerprintHash: string;
  files: ManifestFileEntry[];
}

// ── Dependency injection interfaces ────────────────────

export interface ManifestFsReader {
  readFile: (path: string) => Uint8Array;
  listFiles: (dir: string) => string[];
}

export type HashFn = (data: Uint8Array) => string;

// ── Builders ───────────────────────────────────────────

/**
 * Build a manifest for a release directory.
 * Reads every file in the directory and computes SHA-256 hashes.
 * Files are listed in sorted order for determinism.
 */
export function buildManifest(
  releaseDir: string,
  opts: {
    gitCommit: string;
    baseUrl: string;
    fingerprintHash: string;
    createdAt: string;
  },
  fs: ManifestFsReader,
  hashFn: HashFn,
): Manifest {
  const allFiles = fs.listFiles(releaseDir);
  const files: ManifestFileEntry[] = [];

  for (const relPath of allFiles.sort()) {
    const absPath = `${releaseDir}/${relPath}`;
    const data = fs.readFile(absPath);
    files.push({
      relativePath: relPath,
      bytes: data.length,
      sha256: hashFn(data),
    });
  }

  return {
    createdAt: opts.createdAt,
    gitCommit: opts.gitCommit,
    baseUrl: opts.baseUrl,
    fingerprintHash: opts.fingerprintHash,
    files,
  };
}

// ── Renderers ──────────────────────────────────────────

/** Render a human-readable MANIFEST.txt from a Manifest. */
export function renderManifestText(manifest: Manifest): string {
  const lines: string[] = [
    `# Release MANIFEST`,
    `# Created: ${manifest.createdAt}`,
    `# Git Commit: ${manifest.gitCommit}`,
    `# Base URL: ${manifest.baseUrl}`,
    `# Fingerprint Hash: ${manifest.fingerprintHash}`,
    `#`,
    `# SHA256  Bytes  Path`,
    `# ------  -----  ----`,
  ];

  for (const f of manifest.files) {
    lines.push(
      `${f.sha256}  ${String(f.bytes).padStart(8)}  ${f.relativePath}`,
    );
  }

  return lines.join("\n") + "\n";
}

// ── Verification ───────────────────────────────────────

export interface ManifestVerification {
  totalFiles: number;
  matchedFiles: number;
  mismatchedFiles: string[];
  missingFiles: string[];
}

/**
 * Verify a manifest against files on disk.
 * Returns verification result with any mismatched or missing files.
 */
export function verifyManifest(
  manifest: Manifest,
  releaseDir: string,
  fs: ManifestFsReader,
  hashFn: HashFn,
): ManifestVerification {
  const missingFiles: string[] = [];
  const mismatchedFiles: string[] = [];
  let matchedFiles = 0;

  for (const entry of manifest.files) {
    const absPath = `${releaseDir}/${entry.relativePath}`;
    let data: Uint8Array;
    try {
      data = fs.readFile(absPath);
    } catch {
      missingFiles.push(entry.relativePath);
      continue;
    }
    const hash = hashFn(data);
    if (hash === entry.sha256 && data.length === entry.bytes) {
      matchedFiles++;
    } else {
      mismatchedFiles.push(entry.relativePath);
    }
  }

  return {
    totalFiles: manifest.files.length,
    matchedFiles,
    mismatchedFiles,
    missingFiles,
  };
}
