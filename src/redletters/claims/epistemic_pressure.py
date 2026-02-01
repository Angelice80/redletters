"""Epistemic pressure language detection.

Detects language patterns that assert unwarranted certainty, such as:
- "clearly", "obviously", "plainly" (certainty markers)
- "the text says", "the Greek means" (false objectivity)
- "it is clear that", "we can see that" (suppressed agency)

These patterns are forbidden in readable mode for TYPE2+ claims.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class PressureCategory(Enum):
    """Categories of epistemic pressure language."""

    CERTAINTY_MARKER = "certainty_marker"
    """Words asserting confidence: clearly, obviously, undoubtedly."""

    FALSE_OBJECTIVITY = "false_objectivity"
    """Phrases presenting interpretation as fact: 'the text says'."""

    SUPPRESSED_AGENCY = "suppressed_agency"
    """Passive constructions hiding the interpreter: 'it is clear that'."""

    UNIVERSAL_CLAIM = "universal_claim"
    """Overgeneralization: 'always', 'never', 'all Christians must'."""


@dataclass
class EpistemicPressureWarning:
    """A warning about detected epistemic pressure language."""

    pattern: str
    matched_text: str
    category: PressureCategory
    start_pos: int
    end_pos: int
    severity: str  # "block" or "warn"
    suggestion: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] '{self.matched_text}' ({self.category.value}): {self.suggestion}"


# Pattern definitions: (regex, category, severity, suggestion)
EPISTEMIC_PRESSURE_PATTERNS: list[tuple[str, PressureCategory, str, str]] = [
    # Certainty markers (block in readable mode)
    (
        r"\bclearly\b",
        PressureCategory.CERTAINTY_MARKER,
        "block",
        "Remove 'clearly' or qualify with 'one interpretation suggests'",
    ),
    (
        r"\bobviously\b",
        PressureCategory.CERTAINTY_MARKER,
        "block",
        "Remove 'obviously' - what is obvious to one may not be to another",
    ),
    (
        r"\bplainly\b",
        PressureCategory.CERTAINTY_MARKER,
        "block",
        "Remove 'plainly' or specify whose reading this represents",
    ),
    (
        r"\bundoubtedly\b",
        PressureCategory.CERTAINTY_MARKER,
        "block",
        "Remove 'undoubtedly' - doubt is often warranted in interpretation",
    ),
    (
        r"\bcertainly\b",
        PressureCategory.CERTAINTY_MARKER,
        "block",
        "Remove 'certainly' or use 'likely' or 'probably'",
    ),
    (
        r"\bself-evident\b",
        PressureCategory.CERTAINTY_MARKER,
        "block",
        "Remove 'self-evident' - interpretations require justification",
    ),
    (
        r"\bunquestionabl[ye]\b",
        PressureCategory.CERTAINTY_MARKER,
        "block",
        "Remove 'unquestionable' - questioning is central to scholarship",
    ),
    (
        r"\bindisputabl[ye]\b",
        PressureCategory.CERTAINTY_MARKER,
        "block",
        "Remove 'indisputable' - many interpretations are disputed",
    ),
    (
        r"\bwithout (a )?doubt\b",
        PressureCategory.CERTAINTY_MARKER,
        "block",
        "Remove 'without doubt' or acknowledge uncertainty",
    ),
    # False objectivity markers
    (
        r"\bthe text says\b",
        PressureCategory.FALSE_OBJECTIVITY,
        "block",
        "Texts don't 'say' - they are interpreted. Use 'the text can be read as'",
    ),
    (
        r"\bthe greek means\b",
        PressureCategory.FALSE_OBJECTIVITY,
        "block",
        "Greek has semantic ranges. Use 'this Greek term can mean'",
    ),
    (
        r"\bthe original meaning\b",
        PressureCategory.FALSE_OBJECTIVITY,
        "block",
        "Original meaning is reconstructed, not accessed. Use 'a plausible original sense'",
    ),
    (
        r"\bwhat paul meant\b",
        PressureCategory.FALSE_OBJECTIVITY,
        "warn",
        "Authorial intent is inferred. Consider 'what Paul may have meant'",
    ),
    (
        r"\bwhat jesus meant\b",
        PressureCategory.FALSE_OBJECTIVITY,
        "warn",
        "Authorial intent is inferred. Consider 'what Jesus may have meant'",
    ),
    (
        r"\bthe bible teaches\b",
        PressureCategory.FALSE_OBJECTIVITY,
        "block",
        "The Bible is interpreted, not self-teaching. Specify whose interpretation",
    ),
    (
        r"\bscripture clearly\b",
        PressureCategory.FALSE_OBJECTIVITY,
        "block",
        "Scripture requires interpretation. Use 'one reading of scripture suggests'",
    ),
    # Suppressed agency
    (
        r"\bit is clear that\b",
        PressureCategory.SUPPRESSED_AGENCY,
        "block",
        "Claim the interpretation: 'I/we interpret this as' or 'this tradition reads'",
    ),
    (
        r"\bwe can see that\b",
        PressureCategory.SUPPRESSED_AGENCY,
        "warn",
        "Make explicit who 'we' is and what interpretive lens is used",
    ),
    (
        r"\bthe passage teaches\b",
        PressureCategory.SUPPRESSED_AGENCY,
        "block",
        "Passages are interpreted, not self-teaching. Specify the interpretive tradition",
    ),
    (
        r"\bone can only conclude\b",
        PressureCategory.SUPPRESSED_AGENCY,
        "block",
        "Multiple conclusions are usually possible. Use 'one conclusion is'",
    ),
    (
        r"\bthere is no other way to read\b",
        PressureCategory.SUPPRESSED_AGENCY,
        "block",
        "Multiple readings usually exist. Acknowledge alternatives",
    ),
    (
        r"\bthe only interpretation\b",
        PressureCategory.SUPPRESSED_AGENCY,
        "block",
        "Rarely is there only one interpretation. Use 'a strong interpretation' or 'the dominant view'",
    ),
    # Universal claims (warn level)
    (
        r"\ball christians must\b",
        PressureCategory.UNIVERSAL_CLAIM,
        "warn",
        "Universal ethical claims require hermeneutical justification",
    ),
    (
        r"\beveryone should\b",
        PressureCategory.UNIVERSAL_CLAIM,
        "warn",
        "Universal prescriptions require careful justification",
    ),
    (
        r"\bthis always means\b",
        PressureCategory.UNIVERSAL_CLAIM,
        "warn",
        "Context-dependent terms rarely 'always' mean one thing",
    ),
    (
        r"\bnever means\b",
        PressureCategory.UNIVERSAL_CLAIM,
        "warn",
        "Absolutes are rarely warranted in lexical semantics",
    ),
]


class EpistemicPressureDetector:
    """Detects epistemic pressure language in claim text.

    Epistemic pressure language asserts unwarranted certainty or
    hides the interpretive nature of claims. This detector scans
    text for such patterns and returns warnings.

    Usage:
        detector = EpistemicPressureDetector()
        warnings = detector.detect("Clearly, this text means...")
        for w in warnings:
            print(w)
    """

    def __init__(
        self,
        custom_patterns: list[tuple[str, PressureCategory, str, str]] | None = None,
    ):
        """Initialize detector with optional custom patterns.

        Args:
            custom_patterns: Additional patterns in format
                (regex, category, severity, suggestion)
        """
        self._patterns = list(EPISTEMIC_PRESSURE_PATTERNS)
        if custom_patterns:
            self._patterns.extend(custom_patterns)

        # Compile patterns for efficiency
        self._compiled = [
            (re.compile(p, re.IGNORECASE), cat, sev, sug)
            for p, cat, sev, sug in self._patterns
        ]

    def detect(self, text: str) -> list[EpistemicPressureWarning]:
        """Detect epistemic pressure language in text.

        Args:
            text: The claim text to analyze

        Returns:
            List of warnings, empty if no pressure language found
        """
        warnings: list[EpistemicPressureWarning] = []

        for pattern, category, severity, suggestion in self._compiled:
            for match in pattern.finditer(text):
                warnings.append(
                    EpistemicPressureWarning(
                        pattern=pattern.pattern,
                        matched_text=match.group(),
                        category=category,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        severity=severity,
                        suggestion=suggestion,
                    )
                )

        # Sort by position
        warnings.sort(key=lambda w: w.start_pos)
        return warnings

    def has_blocking_warnings(self, text: str) -> bool:
        """Check if text contains any blocking-level warnings.

        Args:
            text: The claim text to analyze

        Returns:
            True if any 'block' severity warnings found
        """
        warnings = self.detect(text)
        return any(w.severity == "block" for w in warnings)

    def get_blocking_warnings(self, text: str) -> list[EpistemicPressureWarning]:
        """Get only blocking-level warnings.

        Args:
            text: The claim text to analyze

        Returns:
            List of warnings with severity='block'
        """
        return [w for w in self.detect(text) if w.severity == "block"]

    def suggest_rewrites(self, text: str) -> list[tuple[str, str, str]]:
        """Suggest rewrites for detected pressure language.

        Args:
            text: The claim text to analyze

        Returns:
            List of (original_phrase, category, suggestion) tuples
        """
        warnings = self.detect(text)
        return [(w.matched_text, w.category.value, w.suggestion) for w in warnings]

    @staticmethod
    def get_pattern_categories() -> dict[str, list[str]]:
        """Get all patterns grouped by category.

        Returns:
            Dict mapping category name to list of pattern descriptions
        """
        result: dict[str, list[str]] = {}
        for pattern, category, severity, suggestion in EPISTEMIC_PRESSURE_PATTERNS:
            cat_name = category.value
            if cat_name not in result:
                result[cat_name] = []
            result[cat_name].append(f"{pattern} [{severity}]")
        return result
