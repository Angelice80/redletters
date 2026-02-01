"""Morphology code parsing utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from redletters.config import (
    MORPH_PARTS_OF_SPEECH,
    MORPH_TENSES,
    MORPH_VOICES,
    MORPH_MOODS,
    MORPH_PERSONS,
    MORPH_NUMBERS,
    MORPH_CASES,
    MORPH_GENDERS,
)


@dataclass
class ParsedMorphology:
    """Parsed morphology information."""

    raw: str
    part_of_speech: str | None = None
    tense: str | None = None
    voice: str | None = None
    mood: str | None = None
    person: str | None = None
    number: str | None = None
    case: str | None = None
    gender: str | None = None
    is_ambiguous: bool = False
    ambiguity_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "raw": self.raw,
            "part_of_speech": self.part_of_speech,
            "tense": self.tense,
            "voice": self.voice,
            "mood": self.mood,
            "person": self.person,
            "number": self.number,
            "case": self.case,
            "gender": self.gender,
            "is_ambiguous": self.is_ambiguous,
            "ambiguity_notes": self.ambiguity_notes if self.ambiguity_notes else None,
        }


def parse_morphology(code: str) -> ParsedMorphology:
    """
    Parse a Robinson-Pierpont style morphology code.

    Format examples:
    - V-PAI-3S: Verb, Present Active Indicative, 3rd Singular
    - N-NSF: Noun, Nominative Singular Feminine
    - T-NSF: Article (The), Nominative Singular Feminine
    - CONJ: Conjunction
    - PREP: Preposition

    Args:
        code: Morphology code string

    Returns:
        ParsedMorphology with parsed components
    """
    result = ParsedMorphology(raw=code)
    ambiguity_notes = []

    # Handle simple codes first
    if code in ("CONJ", "PREP", "ADV", "PRT"):
        result.part_of_speech = code.lower()
        return result

    parts = code.split("-")
    if not parts:
        return result

    # Part of speech is always first character
    pos_code = parts[0][0] if parts[0] else None
    result.part_of_speech = MORPH_PARTS_OF_SPEECH.get(pos_code, pos_code)

    if result.part_of_speech == "verb" and len(parts) >= 2:
        # Verb parsing: V-TAV-PN format
        # T=Tense, A=Voice, V=Mood
        tvm = parts[1] if len(parts) > 1 else ""

        if len(tvm) >= 1:
            result.tense = MORPH_TENSES.get(tvm[0], tvm[0])
        if len(tvm) >= 2:
            voice_code = tvm[1]
            result.voice = MORPH_VOICES.get(voice_code, voice_code)
            # Check for middle/passive ambiguity
            if voice_code == "E" or (
                voice_code in ("M", "P") and result.tense in ("aorist", "future")
            ):
                result.is_ambiguous = True
                ambiguity_notes.append("voice: middle/passive ambiguous in this form")
        if len(tvm) >= 3:
            result.mood = MORPH_MOODS.get(tvm[2], tvm[2])

        # Person and number in third part
        if len(parts) >= 3:
            pn = parts[2]
            if len(pn) >= 1:
                result.person = MORPH_PERSONS.get(pn[0], pn[0])
            if len(pn) >= 2:
                result.number = MORPH_NUMBERS.get(pn[1], pn[1])

    elif result.part_of_speech in ("noun", "adjective", "article", "pronoun"):
        # Nominal parsing: N-CGN format (Case, Gender, Number) or N-CNG
        if len(parts) >= 2:
            cgn = parts[1]
            if len(cgn) >= 1:
                result.case = MORPH_CASES.get(cgn[0], cgn[0])
            if len(cgn) >= 2:
                result.number = MORPH_NUMBERS.get(cgn[1], cgn[1])
            if len(cgn) >= 3:
                result.gender = MORPH_GENDERS.get(cgn[2], cgn[2])

    if ambiguity_notes:
        result.ambiguity_notes = ambiguity_notes

    return result


def get_morph_constraints(morph: ParsedMorphology) -> dict:
    """
    Get grammatical constraints for rendering from morphology.

    Returns dict with rendering requirements based on morphology.
    """
    constraints = {}

    if morph.mood == "imperative":
        constraints["force"] = "command"
        constraints["subject"] = "implied_you"
    elif morph.mood == "indicative":
        constraints["force"] = "assertion"
    elif morph.mood == "subjunctive":
        constraints["force"] = "possibility"
    elif morph.mood == "optative":
        constraints["force"] = "wish"

    if morph.tense == "perfect":
        constraints["aspect"] = "completed_with_present_result"
    elif morph.tense == "aorist":
        constraints["aspect"] = "simple_past_or_undefined"
    elif morph.tense == "present":
        constraints["aspect"] = "ongoing_or_general"
    elif morph.tense == "imperfect":
        constraints["aspect"] = "past_ongoing"

    if morph.voice == "passive":
        constraints["voice"] = "passive"
    elif morph.voice == "middle":
        constraints["voice"] = "middle_reflexive_or_intensive"
    elif morph.voice == "middle/passive":
        constraints["voice"] = "ambiguous_middle_passive"
        constraints["voice_ambiguity"] = True

    return constraints
