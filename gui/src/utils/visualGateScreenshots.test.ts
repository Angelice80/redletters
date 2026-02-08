import { describe, it, expect } from "vitest";
import {
  stripBase64Prefix,
  base64ToBytes,
  writePngFromBase64,
  verifyScreenshotPaths,
  copyScreenshotsToRelease,
  verifyReleasePackCompleteness,
  buildReleaseSlug,
  latestScreenshotsDir,
  releaseScreenshotsDir,
  ARTIFACTS_ROOT,
  LATEST_DIR,
  RELEASES_DIR,
} from "./visualGateScreenshots";

describe("constants", () => {
  it("uses consistent artifact paths", () => {
    expect(ARTIFACTS_ROOT).toBe("gui/_mcp_artifacts");
    expect(LATEST_DIR).toBe("gui/_mcp_artifacts/latest");
    expect(RELEASES_DIR).toBe("gui/_mcp_artifacts/releases");
  });

  it("latestScreenshotsDir returns correct path", () => {
    expect(latestScreenshotsDir()).toBe(
      "gui/_mcp_artifacts/latest/screenshots",
    );
  });

  it("releaseScreenshotsDir returns correct path", () => {
    expect(releaseScreenshotsDir("2026-02-07_1505_abc1234")).toBe(
      "gui/_mcp_artifacts/releases/2026-02-07_1505_abc1234/screenshots",
    );
  });
});

describe("buildReleaseSlug", () => {
  it("formats timestamp and SHA correctly", () => {
    const slug = buildReleaseSlug("2026-02-07T15:05:00Z", "d767359");
    // Note: getHours() returns local time, so we check format only
    expect(slug).toMatch(/^2026-02-07_\d{4}_d767359$/);
  });
});

describe("stripBase64Prefix", () => {
  it("strips data URI prefix", () => {
    expect(stripBase64Prefix("data:image/png;base64,ABC123")).toBe("ABC123");
  });

  it("returns raw base64 unchanged", () => {
    expect(stripBase64Prefix("ABC123")).toBe("ABC123");
  });
});

describe("base64ToBytes", () => {
  it("decodes base64 to Uint8Array", () => {
    // "Hello" in base64 is "SGVsbG8="
    const bytes = base64ToBytes("SGVsbG8=");
    expect(bytes).toBeInstanceOf(Uint8Array);
    expect(bytes.length).toBe(5);
    expect(String.fromCharCode(...bytes)).toBe("Hello");
  });

  it("handles data URI prefix", () => {
    const bytes = base64ToBytes("data:image/png;base64,SGVsbG8=");
    expect(String.fromCharCode(...bytes)).toBe("Hello");
  });
});

describe("writePngFromBase64", () => {
  it("writes decoded bytes to file and creates directory", () => {
    const written: { path: string; data: Uint8Array }[] = [];
    const createdDirs: string[] = [];
    const fs = {
      writeFile: (path: string, data: Uint8Array) => {
        written.push({ path, data });
      },
      mkdir: (dir: string) => {
        createdDirs.push(dir);
      },
      exists: () => false,
    };

    writePngFromBase64("screenshots/01-test.png", "SGVsbG8=", fs);

    expect(createdDirs).toEqual(["screenshots"]);
    expect(written.length).toBe(1);
    expect(written[0].path).toBe("screenshots/01-test.png");
    expect(String.fromCharCode(...written[0].data)).toBe("Hello");
  });

  it("skips mkdir when directory exists", () => {
    const createdDirs: string[] = [];
    const fs = {
      writeFile: () => {},
      mkdir: (dir: string) => {
        createdDirs.push(dir);
      },
      exists: () => true,
    };

    writePngFromBase64("screenshots/01-test.png", "SGVsbG8=", fs);

    expect(createdDirs).toEqual([]);
  });
});

describe("verifyScreenshotPaths", () => {
  it("returns all present when all exist", () => {
    const result = verifyScreenshotPaths(
      ["a.png", "b.png", "c.png"],
      () => true,
    );
    expect(result.totalScreenshots).toBe(3);
    expect(result.missingScreenshotsCount).toBe(0);
    expect(result.missingPaths).toEqual([]);
    expect(result.presentPaths).toEqual(["a.png", "b.png", "c.png"]);
  });

  it("detects missing files", () => {
    const result = verifyScreenshotPaths(
      ["a.png", "b.png", "c.png"],
      (p) => p !== "b.png",
    );
    expect(result.totalScreenshots).toBe(3);
    expect(result.missingScreenshotsCount).toBe(1);
    expect(result.missingPaths).toEqual(["b.png"]);
    expect(result.presentPaths).toEqual(["a.png", "c.png"]);
  });

  it("handles empty paths array", () => {
    const result = verifyScreenshotPaths([], () => true);
    expect(result.totalScreenshots).toBe(0);
    expect(result.missingScreenshotsCount).toBe(0);
  });
});

// ── copyScreenshotsToRelease ─────────────────────────

describe("copyScreenshotsToRelease", () => {
  const encoder = new TextEncoder();

  function mockCopierFs(
    files: Record<string, Uint8Array>,
    existingDirs: Set<string> = new Set(),
  ) {
    const written: { path: string; data: Uint8Array }[] = [];
    const createdDirs: string[] = [];
    return {
      fs: {
        readFile: (path: string) => {
          const data = files[path];
          if (!data) throw new Error(`File not found: ${path}`);
          return data;
        },
        writeFile: (path: string, data: Uint8Array) => {
          written.push({ path, data });
        },
        mkdir: (dir: string) => {
          createdDirs.push(dir);
          existingDirs.add(dir);
        },
        exists: (path: string) => existingDirs.has(path),
      },
      written,
      createdDirs,
    };
  }

  it("copies all screenshots to release screenshots dir", () => {
    const pngData = encoder.encode("fake-png");
    const { fs, written } = mockCopierFs({
      "gui/_mcp_artifacts/latest/screenshots/01-load.png": pngData,
      "gui/_mcp_artifacts/latest/screenshots/02-click.png": pngData,
    });
    const result = copyScreenshotsToRelease(
      [
        "gui/_mcp_artifacts/latest/screenshots/01-load.png",
        "gui/_mcp_artifacts/latest/screenshots/02-click.png",
      ],
      "2026-02-07_1505_abc1234",
      fs,
    );
    expect(result.copiedCount).toBe(2);
    expect(result.failedPaths).toEqual([]);
    expect(written[0].path).toBe(
      "gui/_mcp_artifacts/releases/2026-02-07_1505_abc1234/screenshots/01-load.png",
    );
    expect(written[1].path).toBe(
      "gui/_mcp_artifacts/releases/2026-02-07_1505_abc1234/screenshots/02-click.png",
    );
  });

  it("creates screenshots dir if not exists", () => {
    const pngData = encoder.encode("fake-png");
    const { fs, createdDirs } = mockCopierFs({
      "gui/_mcp_artifacts/latest/screenshots/01-load.png": pngData,
    });
    copyScreenshotsToRelease(
      ["gui/_mcp_artifacts/latest/screenshots/01-load.png"],
      "2026-02-07_1505_abc1234",
      fs,
    );
    expect(createdDirs).toContain(
      "gui/_mcp_artifacts/releases/2026-02-07_1505_abc1234/screenshots",
    );
  });

  it("reports failed copies when source missing", () => {
    const { fs } = mockCopierFs({});
    const result = copyScreenshotsToRelease(
      ["gui/_mcp_artifacts/latest/screenshots/missing.png"],
      "2026-02-07_1505_abc1234",
      fs,
    );
    expect(result.copiedCount).toBe(0);
    expect(result.failedPaths).toEqual([
      "gui/_mcp_artifacts/latest/screenshots/missing.png",
    ]);
  });

  it("handles empty screenshotPaths", () => {
    const { fs } = mockCopierFs({});
    const result = copyScreenshotsToRelease([], "2026-02-07_1505_abc1234", fs);
    expect(result.copiedCount).toBe(0);
    expect(result.copiedPaths).toEqual([]);
    expect(result.failedPaths).toEqual([]);
  });
});

// ── verifyReleasePackCompleteness ────────────────────

describe("verifyReleasePackCompleteness", () => {
  it("returns complete when all screenshots present in release dir", () => {
    const existsFn = (p: string) =>
      p.startsWith(
        "gui/_mcp_artifacts/releases/2026-02-07_1505_abc1234/screenshots/",
      );
    const result = verifyReleasePackCompleteness(
      [
        "gui/_mcp_artifacts/latest/screenshots/01-load.png",
        "gui/_mcp_artifacts/latest/screenshots/02-click.png",
      ],
      "2026-02-07_1505_abc1234",
      existsFn,
    );
    expect(result.complete).toBe(true);
    expect(result.expectedCount).toBe(2);
    expect(result.presentCount).toBe(2);
    expect(result.missingFilenames).toEqual([]);
  });

  it("returns incomplete when screenshots missing from release dir", () => {
    const existsFn = (p: string) => p.endsWith("01-load.png");
    const result = verifyReleasePackCompleteness(
      [
        "gui/_mcp_artifacts/latest/screenshots/01-load.png",
        "gui/_mcp_artifacts/latest/screenshots/02-click.png",
      ],
      "2026-02-07_1505_abc1234",
      existsFn,
    );
    expect(result.complete).toBe(false);
    expect(result.presentCount).toBe(1);
    expect(result.missingFilenames).toEqual(["02-click.png"]);
  });

  it("returns incomplete for empty screenshotPaths", () => {
    const result = verifyReleasePackCompleteness(
      [],
      "2026-02-07_1505_abc1234",
      () => true,
    );
    expect(result.complete).toBe(false);
    expect(result.expectedCount).toBe(0);
  });
});
