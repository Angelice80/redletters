/**
 * Lightweight reference navigation utilities for the Explore screen.
 *
 * Parses simple scripture references like "John 1:1", "Matt 5:3-12"
 * and provides prev/next verse navigation with boundary safety.
 */

// Match: "Book Chapter:Verse" or "Book Chapter:Start-End"
const REF_PATTERN = /^(\d?\s*[A-Za-z]+)\s+(\d+):(\d+)(?:\s*[-–]\s*(\d+))?$/;

/**
 * NT verse-count map: book name → chapter verse counts.
 * Canonical verse counts per chapter for all 27 NT books.
 * Supports common abbreviations (Matt, 1Cor, etc.) and full names.
 *
 * Source: NA28/UBS5 chapter-verse counts (standard critical text).
 * Cross-checked against SBLGNT verse divisions.
 * Last verified: 2025-01 (Sprint 23).
 */
const NT_VERSE_MAP: Record<string, number[]> = {
  // Gospels
  Matt: [
    25, 23, 17, 25, 48, 34, 29, 34, 38, 42, 30, 50, 58, 36, 39, 28, 27, 35, 30,
    34, 46, 46, 39, 51, 46, 75, 66, 20,
  ],
  Matthew: [
    25, 23, 17, 25, 48, 34, 29, 34, 38, 42, 30, 50, 58, 36, 39, 28, 27, 35, 30,
    34, 46, 46, 39, 51, 46, 75, 66, 20,
  ],
  Mark: [45, 28, 35, 41, 43, 56, 37, 38, 50, 52, 33, 44, 37, 72, 47, 20],
  Luke: [
    80, 52, 38, 44, 39, 49, 50, 56, 62, 42, 54, 59, 35, 35, 32, 31, 37, 43, 48,
    47, 38, 71, 56, 53,
  ],
  John: [
    51, 25, 36, 54, 47, 71, 53, 59, 41, 42, 57, 50, 38, 31, 27, 33, 26, 40, 42,
    31, 25,
  ],
  // Acts
  Acts: [
    26, 47, 26, 37, 42, 15, 60, 40, 43, 48, 30, 25, 52, 28, 41, 40, 34, 28, 41,
    38, 40, 30, 35, 27, 27, 32, 44, 31,
  ],
  // Pauline epistles
  Rom: [32, 29, 31, 25, 21, 23, 25, 39, 33, 21, 36, 21, 14, 23, 33, 27],
  Romans: [32, 29, 31, 25, 21, 23, 25, 39, 33, 21, 36, 21, 14, 23, 33, 27],
  "1Cor": [31, 16, 23, 21, 13, 20, 40, 13, 27, 33, 34, 31, 13, 40, 58, 24],
  "1 Cor": [31, 16, 23, 21, 13, 20, 40, 13, 27, 33, 34, 31, 13, 40, 58, 24],
  "1 Corinthians": [
    31, 16, 23, 21, 13, 20, 40, 13, 27, 33, 34, 31, 13, 40, 58, 24,
  ],
  "2Cor": [24, 17, 18, 18, 21, 18, 16, 24, 15, 18, 33, 21, 14],
  "2 Cor": [24, 17, 18, 18, 21, 18, 16, 24, 15, 18, 33, 21, 14],
  "2 Corinthians": [24, 17, 18, 18, 21, 18, 16, 24, 15, 18, 33, 21, 14],
  Gal: [24, 21, 29, 31, 26, 18],
  Galatians: [24, 21, 29, 31, 26, 18],
  Eph: [23, 22, 21, 32, 33, 24],
  Ephesians: [23, 22, 21, 32, 33, 24],
  Phil: [30, 30, 21, 23],
  Philippians: [30, 30, 21, 23],
  Col: [29, 23, 25, 18],
  Colossians: [29, 23, 25, 18],
  "1Thess": [10, 20, 13, 18, 28],
  "1 Thess": [10, 20, 13, 18, 28],
  "1 Thessalonians": [10, 20, 13, 18, 28],
  "2Thess": [12, 17, 18],
  "2 Thess": [12, 17, 18],
  "2 Thessalonians": [12, 17, 18],
  "1Tim": [20, 15, 16, 16, 25, 21],
  "1 Tim": [20, 15, 16, 16, 25, 21],
  "1 Timothy": [20, 15, 16, 16, 25, 21],
  "2Tim": [18, 26, 17, 22],
  "2 Tim": [18, 26, 17, 22],
  "2 Timothy": [18, 26, 17, 22],
  Titus: [16, 15, 15],
  Phlm: [25],
  Philemon: [25],
  // General epistles
  Heb: [14, 18, 19, 16, 14, 20, 28, 13, 28, 39, 40, 29, 25],
  Hebrews: [14, 18, 19, 16, 14, 20, 28, 13, 28, 39, 40, 29, 25],
  Jas: [27, 26, 18, 17, 20],
  James: [27, 26, 18, 17, 20],
  "1Pet": [25, 25, 22, 19, 14],
  "1 Pet": [25, 25, 22, 19, 14],
  "1 Peter": [25, 25, 22, 19, 14],
  "2Pet": [21, 22, 18],
  "2 Pet": [21, 22, 18],
  "2 Peter": [21, 22, 18],
  "1John": [10, 29, 24, 21, 21],
  "1 John": [10, 29, 24, 21, 21],
  "2John": [13],
  "2 John": [13],
  "3John": [15],
  "3 John": [15],
  Jude: [25],
  // Revelation
  Rev: [
    20, 29, 22, 11, 14, 17, 17, 13, 21, 11, 19, 17, 18, 20, 8, 21, 18, 24, 21,
    15, 27, 21,
  ],
  Revelation: [
    20, 29, 22, 11, 14, 17, 17, 13, 21, 11, 19, 17, 18, 20, 8, 21, 18, 24, 21,
    15, 27, 21,
  ],
};

/**
 * Look up the max verse count for a given book + chapter.
 * Returns undefined if the book or chapter is unknown.
 */
export function getMaxVerse(book: string, chapter: number): number | undefined {
  const chapters = NT_VERSE_MAP[book];
  if (!chapters) return undefined;
  if (chapter < 1 || chapter > chapters.length) return undefined;
  return chapters[chapter - 1];
}

/**
 * Look up the total chapter count for a book.
 */
export function getChapterCount(book: string): number | undefined {
  const chapters = NT_VERSE_MAP[book];
  return chapters?.length;
}

export interface ParsedRef {
  book: string;
  chapter: number;
  verseStart: number;
  verseEnd: number; // same as verseStart for single verse
}

/**
 * Parse a human reference string into components.
 * Returns null if the reference doesn't match the expected pattern.
 */
export function parseRef(ref: string): ParsedRef | null {
  const trimmed = ref.trim();
  const match = trimmed.match(REF_PATTERN);
  if (!match) return null;

  const book = match[1].trim();
  const chapter = parseInt(match[2], 10);
  const verseStart = parseInt(match[3], 10);
  const verseEnd = match[4] ? parseInt(match[4], 10) : verseStart;

  if (isNaN(chapter) || isNaN(verseStart) || isNaN(verseEnd)) return null;
  if (chapter < 1 || verseStart < 1 || verseEnd < verseStart) return null;

  return { book, chapter, verseStart, verseEnd };
}

/**
 * Format a ParsedRef back into a human reference string.
 */
export function formatRef(parsed: ParsedRef): string {
  if (parsed.verseStart === parsed.verseEnd) {
    return `${parsed.book} ${parsed.chapter}:${parsed.verseStart}`;
  }
  return `${parsed.book} ${parsed.chapter}:${parsed.verseStart}-${parsed.verseEnd}`;
}

/**
 * Navigate to the next verse(s) from the current reference.
 * For a single verse (John 1:1), returns John 1:2.
 * For a range (John 1:1-3), shifts by range width: John 1:4-6.
 * Returns null if navigation would exceed chapter verse count (when known).
 */
export function nextRef(ref: string): string | null {
  const parsed = parseRef(ref);
  if (!parsed) return null;

  const rangeWidth = parsed.verseEnd - parsed.verseStart;
  const newStart = parsed.verseEnd + 1;
  const newEnd = newStart + rangeWidth;

  // Check chapter boundary if we have verse map data
  const maxVerse = getMaxVerse(parsed.book, parsed.chapter);
  if (maxVerse !== undefined && newStart > maxVerse) {
    return null; // At chapter end
  }

  // Clamp end to max verse if known
  const clampedEnd =
    maxVerse !== undefined ? Math.min(newEnd, maxVerse) : newEnd;

  return formatRef({
    ...parsed,
    verseStart: newStart,
    verseEnd: clampedEnd,
  });
}

/**
 * Navigate to the previous verse(s) from the current reference.
 * For a single verse (John 1:2), returns John 1:1.
 * For a range (John 1:4-6), shifts back by range width: John 1:1-3.
 * Returns null if it would go below verse 1.
 */
export function prevRef(ref: string): string | null {
  const parsed = parseRef(ref);
  if (!parsed) return null;

  const rangeWidth = parsed.verseEnd - parsed.verseStart;
  const newStart = parsed.verseStart - rangeWidth - 1;

  if (newStart < 1) return null;

  return formatRef({
    ...parsed,
    verseStart: newStart,
    verseEnd: newStart + rangeWidth,
  });
}

/**
 * Check if a reference is at the last verse of its chapter (when known).
 */
export function isAtChapterEnd(ref: string): boolean | null {
  const parsed = parseRef(ref);
  if (!parsed) return null;
  const maxVerse = getMaxVerse(parsed.book, parsed.chapter);
  if (maxVerse === undefined) return null; // Unknown
  return parsed.verseEnd >= maxVerse;
}

/**
 * Check if a reference is at verse 1 of its chapter.
 */
export function isAtChapterStart(ref: string): boolean | null {
  const parsed = parseRef(ref);
  if (!parsed) return null;
  return parsed.verseStart === 1;
}

/**
 * Validate a reference string. Returns an error message or null if valid.
 * Checks format, and optionally validates against known NT book/chapter/verse bounds.
 */
export function validateRef(ref: string): string | null {
  const trimmed = ref.trim();
  if (!trimmed) return "Enter a scripture reference";

  const parsed = parseRef(trimmed);
  if (!parsed) {
    // Give a specific hint
    if (!/\d+:\d+/.test(trimmed)) {
      return "Include chapter and verse (e.g., John 1:1)";
    }
    return "Invalid reference format. Try: Book Chapter:Verse (e.g., John 1:1)";
  }

  // Validate against NT verse map if book is known
  const chapterCount = getChapterCount(parsed.book);
  if (chapterCount !== undefined) {
    if (parsed.chapter > chapterCount) {
      return `${parsed.book} has ${chapterCount} chapter${chapterCount > 1 ? "s" : ""} (requested ch. ${parsed.chapter})`;
    }
    const maxVerse = getMaxVerse(parsed.book, parsed.chapter);
    if (maxVerse !== undefined && parsed.verseStart > maxVerse) {
      return `${parsed.book} ${parsed.chapter} has ${maxVerse} verses (requested v. ${parsed.verseStart})`;
    }
  }

  return null;
}
