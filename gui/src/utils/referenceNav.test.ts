import { describe, it, expect } from "vitest";
import {
  parseRef,
  formatRef,
  nextRef,
  prevRef,
  validateRef,
  getMaxVerse,
  getChapterCount,
  isAtChapterEnd,
  isAtChapterStart,
} from "./referenceNav";

describe("parseRef", () => {
  it("parses single verse", () => {
    expect(parseRef("John 1:1")).toEqual({
      book: "John",
      chapter: 1,
      verseStart: 1,
      verseEnd: 1,
    });
  });

  it("parses verse range with hyphen", () => {
    expect(parseRef("Matt 5:3-12")).toEqual({
      book: "Matt",
      chapter: 5,
      verseStart: 3,
      verseEnd: 12,
    });
  });

  it("parses numbered book", () => {
    expect(parseRef("1 John 3:16")).toEqual({
      book: "1 John",
      chapter: 3,
      verseStart: 16,
      verseEnd: 16,
    });
  });

  it("returns null for invalid input", () => {
    expect(parseRef("")).toBeNull();
    expect(parseRef("hello")).toBeNull();
    expect(parseRef("John")).toBeNull();
  });
});

describe("formatRef", () => {
  it("formats single verse", () => {
    expect(
      formatRef({ book: "John", chapter: 1, verseStart: 1, verseEnd: 1 }),
    ).toBe("John 1:1");
  });

  it("formats range", () => {
    expect(
      formatRef({ book: "Matt", chapter: 5, verseStart: 3, verseEnd: 12 }),
    ).toBe("Matt 5:3-12");
  });
});

describe("nextRef", () => {
  it("increments single verse", () => {
    expect(nextRef("John 1:1")).toBe("John 1:2");
  });

  it("shifts range by width", () => {
    expect(nextRef("John 1:1-3")).toBe("John 1:4-6");
  });

  it("returns null for unparseable", () => {
    expect(nextRef("bad ref")).toBeNull();
  });

  it("returns null at chapter end (John 21:25 is the last verse)", () => {
    expect(nextRef("John 21:25")).toBeNull();
  });

  it("returns null at chapter end for Mark 16:20", () => {
    expect(nextRef("Mark 16:20")).toBeNull();
  });

  it("clamps range end to max verse", () => {
    // John 1 has 51 verses; 49-51 is valid, next would be 52-54 but clamped
    // Actually 52 > 51, so nextRef from 50-51 should give null since start (52) > max (51)
    expect(nextRef("John 1:51")).toBeNull();
  });

  it("allows navigation within chapter bounds", () => {
    // John 1 has 51 verses
    expect(nextRef("John 1:49")).toBe("John 1:50");
  });

  it("clamps range end when range would exceed chapter", () => {
    // John 1 has 51 verses. At verse 49, next range 49-51 → next start=50
    // Wait, nextRef from "John 1:49-51" → start=52, which > 51, so null
    expect(nextRef("John 1:49-51")).toBeNull();
    // But "John 1:48-49" → start=50, end=51 (clamped to 51)
    expect(nextRef("John 1:48-49")).toBe("John 1:50-51");
  });

  it("works for unknown books (no boundary check)", () => {
    // Unknown book still navigates (no verse map)
    expect(nextRef("Foobar 1:1")).toBe("Foobar 1:2");
  });
});

describe("prevRef", () => {
  it("decrements single verse", () => {
    expect(prevRef("John 1:2")).toBe("John 1:1");
  });

  it("shifts range back by width", () => {
    expect(prevRef("John 1:4-6")).toBe("John 1:1-3");
  });

  it("returns null when below verse 1", () => {
    expect(prevRef("John 1:1")).toBeNull();
  });

  it("returns null for range at start", () => {
    expect(prevRef("John 1:1-3")).toBeNull();
  });
});

describe("validateRef", () => {
  it("valid ref returns null", () => {
    expect(validateRef("John 1:1")).toBeNull();
  });

  it("empty returns error", () => {
    expect(validateRef("")).toBeTruthy();
  });

  it("missing verse returns hint", () => {
    expect(validateRef("John 1")).toContain("chapter and verse");
  });

  it("rejects chapter beyond book bounds", () => {
    // John has 21 chapters
    const err = validateRef("John 28:1");
    expect(err).toContain("21 chapters");
  });

  it("rejects verse beyond chapter bounds", () => {
    // John 1 has 51 verses
    const err = validateRef("John 1:99");
    expect(err).toContain("51 verses");
  });

  it("accepts valid verse at chapter max", () => {
    // John 1 has 51 verses
    expect(validateRef("John 1:51")).toBeNull();
  });

  it("allows unknown books (no map data)", () => {
    // Unknown book can't be validated against map, so format-only
    expect(validateRef("Foobar 1:1")).toBeNull();
  });
});

describe("getMaxVerse", () => {
  it("returns verse count for known book/chapter", () => {
    expect(getMaxVerse("John", 1)).toBe(51);
    expect(getMaxVerse("John", 21)).toBe(25);
    expect(getMaxVerse("Matt", 1)).toBe(25);
    expect(getMaxVerse("Rev", 22)).toBe(21);
  });

  it("returns undefined for unknown book", () => {
    expect(getMaxVerse("Foobar", 1)).toBeUndefined();
  });

  it("returns undefined for out-of-range chapter", () => {
    expect(getMaxVerse("John", 0)).toBeUndefined();
    expect(getMaxVerse("John", 22)).toBeUndefined();
  });
});

describe("getChapterCount", () => {
  it("returns chapter count for known books", () => {
    expect(getChapterCount("John")).toBe(21);
    expect(getChapterCount("Matt")).toBe(28);
    expect(getChapterCount("Phlm")).toBe(1);
    expect(getChapterCount("Rev")).toBe(22);
  });

  it("returns undefined for unknown books", () => {
    expect(getChapterCount("Foobar")).toBeUndefined();
  });
});

describe("isAtChapterEnd", () => {
  it("returns true at last verse", () => {
    expect(isAtChapterEnd("John 21:25")).toBe(true);
  });

  it("returns false before last verse", () => {
    expect(isAtChapterEnd("John 21:24")).toBe(false);
  });

  it("returns null for unknown book", () => {
    expect(isAtChapterEnd("Foobar 1:1")).toBeNull();
  });

  it("returns null for unparseable", () => {
    expect(isAtChapterEnd("bad")).toBeNull();
  });
});

// S13: Verse map provenance & sanity tests
describe("NT verse map sanity", () => {
  // Canonical chapter counts for all 27 NT books (NA28/UBS5)
  const EXPECTED_CHAPTERS: Record<string, number> = {
    Matt: 28,
    Mark: 16,
    Luke: 24,
    John: 21,
    Acts: 28,
    Rom: 16,
    "1Cor": 16,
    "2Cor": 13,
    Gal: 6,
    Eph: 6,
    Phil: 4,
    Col: 4,
    "1Thess": 5,
    "2Thess": 3,
    "1Tim": 6,
    "2Tim": 4,
    Titus: 3,
    Phlm: 1,
    Heb: 13,
    Jas: 5,
    "1Pet": 5,
    "2Pet": 3,
    "1John": 5,
    "2John": 1,
    "3John": 1,
    Jude: 1,
    Rev: 22,
  };

  it("has correct chapter counts for all 27 NT books", () => {
    for (const [book, expected] of Object.entries(EXPECTED_CHAPTERS)) {
      expect(getChapterCount(book), `${book} chapter count`).toBe(expected);
    }
  });

  it("covers all 27 canonical NT books", () => {
    expect(Object.keys(EXPECTED_CHAPTERS)).toHaveLength(27);
  });

  // Abbreviation aliases should resolve to same data
  it("abbreviation aliases match full-name data", () => {
    const aliases: [string, string][] = [
      ["Matt", "Matthew"],
      ["Rom", "Romans"],
      ["1Cor", "1 Corinthians"],
      ["2Cor", "2 Corinthians"],
      ["Gal", "Galatians"],
      ["Eph", "Ephesians"],
      ["Phil", "Philippians"],
      ["Col", "Colossians"],
      ["1Thess", "1 Thessalonians"],
      ["2Thess", "2 Thessalonians"],
      ["1Tim", "1 Timothy"],
      ["2Tim", "2 Timothy"],
      ["Phlm", "Philemon"],
      ["Heb", "Hebrews"],
      ["Jas", "James"],
      ["1Pet", "1 Peter"],
      ["2Pet", "2 Peter"],
      ["Rev", "Revelation"],
    ];
    for (const [abbr, full] of aliases) {
      expect(getChapterCount(abbr), `${abbr} vs ${full}`).toBe(
        getChapterCount(full),
      );
      // Spot-check first chapter verse count matches
      expect(getMaxVerse(abbr, 1), `${abbr} ch1 vs ${full} ch1`).toBe(
        getMaxVerse(full, 1),
      );
    }
  });

  // End-of-book boundary: last verse of last chapter should be navigable
  it("end-of-book last verse is navigable and boundary-safe", () => {
    // Known last verses for selected books
    const lastVerses: [string, number, number][] = [
      ["Matt", 28, 20],
      ["Mark", 16, 20],
      ["Luke", 24, 53],
      ["John", 21, 25],
      ["Acts", 28, 31],
      ["Rev", 22, 21],
      ["Phlm", 1, 25],
      ["Jude", 1, 25],
    ];
    for (const [book, ch, verse] of lastVerses) {
      const ref = `${book} ${ch}:${verse}`;
      // Should be at chapter end
      expect(isAtChapterEnd(ref), `${ref} should be at chapter end`).toBe(true);
      // nextRef should return null (can't go past end)
      expect(nextRef(ref), `nextRef(${ref}) should be null`).toBeNull();
      // validateRef should pass
      expect(validateRef(ref), `validateRef(${ref}) should pass`).toBeNull();
    }
  });

  // First verse of first chapter should be navigable
  it("first verse of each book is valid and at chapter start", () => {
    for (const book of Object.keys(EXPECTED_CHAPTERS)) {
      const ref = `${book} 1:1`;
      expect(validateRef(ref), `validateRef(${ref})`).toBeNull();
      expect(isAtChapterStart(ref), `${ref} at start`).toBe(true);
      expect(prevRef(ref), `prevRef(${ref}) should be null`).toBeNull();
    }
  });

  // Verify every chapter has at least 1 verse and no unreasonable counts
  it("all chapters have reasonable verse counts (1-176)", () => {
    for (const [book, expectedCh] of Object.entries(EXPECTED_CHAPTERS)) {
      for (let ch = 1; ch <= expectedCh; ch++) {
        const maxV = getMaxVerse(book, ch);
        expect(maxV, `${book} ${ch} should have verse data`).toBeDefined();
        expect(maxV!, `${book} ${ch} >= 1 verse`).toBeGreaterThanOrEqual(1);
        // Psalm 119 has 176 verses (OT), NT max is ~80 (Luke 1)
        expect(maxV!, `${book} ${ch} <= 176 verses`).toBeLessThanOrEqual(176);
      }
    }
  });
});

describe("isAtChapterStart", () => {
  it("returns true at verse 1", () => {
    expect(isAtChapterStart("John 1:1")).toBe(true);
  });

  it("returns false at other verses", () => {
    expect(isAtChapterStart("John 1:2")).toBe(false);
  });

  it("returns null for unparseable", () => {
    expect(isAtChapterStart("bad")).toBeNull();
  });
});
