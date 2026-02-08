import { describe, it, expect } from "vitest";
import {
  buildManifest,
  renderManifestText,
  verifyManifest,
  type ManifestFsReader,
  type HashFn,
  type Manifest,
} from "./visualGateManifest";

// ── Test fixtures ─────────────────────────────────────

const encoder = new TextEncoder();

function mockFs(files: Record<string, string>): ManifestFsReader {
  return {
    readFile: (path: string) => {
      const key = Object.keys(files).find((k) => path.endsWith(k));
      if (!key) throw new Error(`File not found: ${path}`);
      return encoder.encode(files[key]);
    },
    listFiles: () => Object.keys(files),
  };
}

const mockHashFn: HashFn = (data: Uint8Array) => `sha256:${data.length}`;

// ── buildManifest ─────────────────────────────────────

describe("buildManifest", () => {
  it("creates manifest with sorted file entries", () => {
    const fs = mockFs({
      "screenshots/01.png": "PNG_DATA_HERE",
      "report.json": '{"test":true}',
      "report.md": "# Report",
    });

    const m = buildManifest(
      "releases/test",
      {
        gitCommit: "abc1234",
        baseUrl: "http://localhost:1420",
        fingerprintHash: "fp_hash_abc",
        createdAt: "2026-02-07T12:00:00Z",
      },
      fs,
      mockHashFn,
    );

    expect(m.files).toHaveLength(3);
    // Files sorted by relativePath
    expect(m.files[0].relativePath).toBe("report.json");
    expect(m.files[1].relativePath).toBe("report.md");
    expect(m.files[2].relativePath).toBe("screenshots/01.png");
    expect(m.gitCommit).toBe("abc1234");
    expect(m.baseUrl).toBe("http://localhost:1420");
    expect(m.fingerprintHash).toBe("fp_hash_abc");
    expect(m.createdAt).toBe("2026-02-07T12:00:00Z");
  });

  it("records byte sizes and hashes for each file", () => {
    const fs = mockFs({
      "data.txt": "Hello",
    });

    const m = buildManifest(
      "releases/test",
      {
        gitCommit: "abc1234",
        baseUrl: "http://localhost:1420",
        fingerprintHash: "fp",
        createdAt: "2026-02-07T12:00:00Z",
      },
      fs,
      mockHashFn,
    );

    expect(m.files[0].bytes).toBe(5); // "Hello" = 5 bytes
    expect(m.files[0].sha256).toBe("sha256:5");
  });

  it("handles empty directory", () => {
    const fs: ManifestFsReader = {
      readFile: () => new Uint8Array(0),
      listFiles: () => [],
    };

    const m = buildManifest(
      "releases/empty",
      {
        gitCommit: "abc1234",
        baseUrl: "http://localhost:1420",
        fingerprintHash: "fp",
        createdAt: "2026-02-07T12:00:00Z",
      },
      fs,
      mockHashFn,
    );

    expect(m.files).toHaveLength(0);
  });
});

// ── renderManifestText ────────────────────────────────

describe("renderManifestText", () => {
  it("renders human-readable text with header and entries", () => {
    const m: Manifest = {
      createdAt: "2026-02-07T12:00:00Z",
      gitCommit: "abc1234",
      baseUrl: "http://localhost:1420",
      fingerprintHash: "fp_hash_abc",
      files: [
        { relativePath: "report.json", bytes: 1234, sha256: "aaa111" },
        { relativePath: "screenshots/01.png", bytes: 56789, sha256: "bbb222" },
      ],
    };
    const txt = renderManifestText(m);
    expect(txt).toContain("# Release MANIFEST");
    expect(txt).toContain("abc1234");
    expect(txt).toContain("fp_hash_abc");
    expect(txt).toContain("aaa111");
    expect(txt).toContain("report.json");
    expect(txt).toContain("bbb222");
    expect(txt).toContain("screenshots/01.png");
    expect(txt).toContain("1234");
    expect(txt).toContain("56789");
  });

  it("renders empty file list", () => {
    const m: Manifest = {
      createdAt: "2026-02-07T12:00:00Z",
      gitCommit: "abc1234",
      baseUrl: "http://localhost:1420",
      fingerprintHash: "fp",
      files: [],
    };
    const txt = renderManifestText(m);
    expect(txt).toContain("# Release MANIFEST");
    // Only header lines, no file entries
    const lines = txt.trim().split("\n");
    expect(lines.every((l) => l.startsWith("#"))).toBe(true);
  });
});

// ── verifyManifest ────────────────────────────────────

describe("verifyManifest", () => {
  it("returns all matched when files match", () => {
    const fs = mockFs({
      "report.json": "data",
      "screenshot.png": "img",
    });

    const manifest: Manifest = {
      createdAt: "2026-02-07T12:00:00Z",
      gitCommit: "abc1234",
      baseUrl: "http://localhost:1420",
      fingerprintHash: "fp",
      files: [
        { relativePath: "report.json", bytes: 4, sha256: "sha256:4" },
        { relativePath: "screenshot.png", bytes: 3, sha256: "sha256:3" },
      ],
    };

    const result = verifyManifest(manifest, "releases/test", fs, mockHashFn);
    expect(result.totalFiles).toBe(2);
    expect(result.matchedFiles).toBe(2);
    expect(result.mismatchedFiles).toEqual([]);
    expect(result.missingFiles).toEqual([]);
  });

  it("detects missing files", () => {
    const fs: ManifestFsReader = {
      readFile: () => {
        throw new Error("not found");
      },
      listFiles: () => [],
    };

    const manifest: Manifest = {
      createdAt: "2026-02-07T12:00:00Z",
      gitCommit: "abc1234",
      baseUrl: "http://localhost:1420",
      fingerprintHash: "fp",
      files: [{ relativePath: "missing.json", bytes: 10, sha256: "sha256:10" }],
    };

    const result = verifyManifest(manifest, "releases/test", fs, mockHashFn);
    expect(result.missingFiles).toEqual(["missing.json"]);
    expect(result.matchedFiles).toBe(0);
  });

  it("detects hash mismatches", () => {
    const fs = mockFs({
      "report.json": "modified-content",
    });

    const manifest: Manifest = {
      createdAt: "2026-02-07T12:00:00Z",
      gitCommit: "abc1234",
      baseUrl: "http://localhost:1420",
      fingerprintHash: "fp",
      files: [
        {
          relativePath: "report.json",
          bytes: 99,
          sha256: "sha256:99",
        },
      ],
    };

    const result = verifyManifest(manifest, "releases/test", fs, mockHashFn);
    expect(result.mismatchedFiles).toEqual(["report.json"]);
    expect(result.matchedFiles).toBe(0);
  });
});
