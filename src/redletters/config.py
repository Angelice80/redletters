"""Configuration settings for Red Letters."""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class Settings:
    """Application settings."""

    # Database
    db_path: Path = field(
        default_factory=lambda: Path.home() / ".redletters" / "redletters.db"
    )

    # Rendering
    default_styles: list[str] = field(
        default_factory=lambda: [
            "ultra-literal",
            "natural",
            "meaning-first",
            "jewish-context",
        ]
    )
    max_renderings: int = 5
    min_score_threshold: float = 0.3

    # Ranking weights
    morph_fit_weight: float = 0.4
    sense_weight_weight: float = 0.35
    collocation_weight: float = 0.15
    uncommon_penalty_weight: float = 0.1

    # Plugin paths
    plugin_dir: Path = field(
        default_factory=lambda: Path.home() / ".redletters" / "plugins"
    )


# Morphology code mappings
MORPH_PARTS_OF_SPEECH = {
    "V": "verb",
    "N": "noun",
    "A": "adjective",
    "D": "adverb",
    "P": "preposition",
    "C": "conjunction",
    "T": "article",
    "R": "pronoun",
    "I": "interjection",
    "X": "particle",
}

MORPH_TENSES = {
    "P": "present",
    "I": "imperfect",
    "F": "future",
    "A": "aorist",
    "X": "perfect",
    "Y": "pluperfect",
}

MORPH_VOICES = {
    "A": "active",
    "M": "middle",
    "P": "passive",
    "E": "middle/passive",  # ambiguous
}

MORPH_MOODS = {
    "I": "indicative",
    "S": "subjunctive",
    "O": "optative",
    "M": "imperative",
    "N": "infinitive",
    "P": "participle",
}

MORPH_PERSONS = {"1": "first", "2": "second", "3": "third"}
MORPH_NUMBERS = {"S": "singular", "P": "plural"}
MORPH_CASES = {
    "N": "nominative",
    "G": "genitive",
    "D": "dative",
    "A": "accusative",
    "V": "vocative",
}
MORPH_GENDERS = {"M": "masculine", "F": "feminine", "N": "neuter"}
