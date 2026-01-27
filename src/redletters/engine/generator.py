"""Candidate rendering generator."""

import sqlite3
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from redletters.engine.senses import SenseLookup, LexemeSense, load_collocations
from redletters.ingest.morphology import parse_morphology, get_morph_constraints


class RenderingStyle(str, Enum):
    """Supported rendering styles."""

    ULTRA_LITERAL = "ultra-literal"
    NATURAL = "natural"
    MEANING_FIRST = "meaning-first"
    JEWISH_CONTEXT = "jewish-context"


@dataclass
class TokenRendering:
    """Rendering for a single token."""

    token_id: int
    lemma: str
    surface: str
    chosen_sense: LexemeSense
    gloss: str
    morph_constraints: dict
    ambiguity_type: str | None = None
    alternate_glosses: list[str] | None = None


@dataclass
class CandidateRendering:
    """A complete candidate rendering for a passage."""

    style: RenderingStyle
    text: str
    token_renderings: list[TokenRendering]
    raw_score: float = 0.0


class CandidateGenerator:
    """Generates candidate renderings in multiple styles."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.sense_lookup = SenseLookup(conn)
        self.collocations = load_collocations(conn)

        # Style-specific transformers
        self.style_transformers: dict[RenderingStyle, Callable] = {
            RenderingStyle.ULTRA_LITERAL: self._transform_ultra_literal,
            RenderingStyle.NATURAL: self._transform_natural,
            RenderingStyle.MEANING_FIRST: self._transform_meaning_first,
            RenderingStyle.JEWISH_CONTEXT: self._transform_jewish_context,
        }

    def generate_all(self, tokens: list[dict]) -> list[CandidateRendering]:
        """
        Generate candidate renderings in all styles.

        Args:
            tokens: List of token dictionaries from query

        Returns:
            List of CandidateRendering objects (one per style)
        """
        candidates = []

        for style in RenderingStyle:
            token_renderings = []

            for i, token in enumerate(tokens):
                # Get adjacent lemmas for context
                adjacent = []
                if i > 0:
                    adjacent.append(tokens[i - 1]["lemma"])
                if i < len(tokens) - 1:
                    adjacent.append(tokens[i + 1]["lemma"])

                rendering = self._render_token(token, style, adjacent)
                token_renderings.append(rendering)

            # Assemble full text using style transformer
            text = self.style_transformers[style](token_renderings)

            candidates.append(
                CandidateRendering(
                    style=style, text=text, token_renderings=token_renderings
                )
            )

        return candidates

    def _render_token(
        self, token: dict, style: RenderingStyle, adjacent_lemmas: list[str]
    ) -> TokenRendering:
        """Render a single token in a given style."""
        lemma = token["lemma"]
        morph = parse_morphology(token["morph"])
        constraints = get_morph_constraints(morph)

        senses = self.sense_lookup.get_senses(lemma)

        # Choose sense based on style preference
        chosen_sense = self._select_sense_for_style(senses, style, adjacent_lemmas)

        # Determine ambiguity
        ambiguity_type = None
        alternate_glosses = None

        if len(senses) > 1:
            # Check if top senses have similar weights
            top_senses = [s for s in senses if s.weight >= chosen_sense.weight * 0.8]
            if len(top_senses) > 1:
                ambiguity_type = "lexical_polysemy"
                alternate_glosses = [s.gloss for s in top_senses if s != chosen_sense][
                    :3
                ]

        if morph.is_ambiguous:
            ambiguity_type = ambiguity_type or "morphological"
            if morph.ambiguity_notes:
                if alternate_glosses is None:
                    alternate_glosses = []
                alternate_glosses.extend(
                    [f"[morph: {n}]" for n in morph.ambiguity_notes]
                )

        # Generate gloss based on style
        gloss = self._apply_style_to_gloss(
            chosen_sense.gloss, style, constraints, morph
        )

        return TokenRendering(
            token_id=token["id"],
            lemma=lemma,
            surface=token["surface"],
            chosen_sense=chosen_sense,
            gloss=gloss,
            morph_constraints=constraints,
            ambiguity_type=ambiguity_type,
            alternate_glosses=alternate_glosses,
        )

    def _select_sense_for_style(
        self,
        senses: list[LexemeSense],
        style: RenderingStyle,
        adjacent_lemmas: list[str],
    ) -> LexemeSense:
        """Select the most appropriate sense for a style."""
        if not senses:
            raise ValueError("No senses available")

        # Style-based domain preferences
        domain_preferences = {
            RenderingStyle.ULTRA_LITERAL: ["etymological", "spatial", "temporal"],
            RenderingStyle.NATURAL: ["general", "cognitive", "behavioral"],
            RenderingStyle.MEANING_FIRST: ["cognitive", "relational", "behavioral"],
            RenderingStyle.JEWISH_CONTEXT: [
                "socio-religious",
                "circumlocution",
                "religious",
            ],
        }

        preferred_domains = domain_preferences.get(style, [])

        # Score each sense
        scored = []
        for sense in senses:
            score = sense.weight

            # Boost for preferred domain
            if sense.domain in preferred_domains:
                domain_idx = preferred_domains.index(sense.domain)
                score *= 1.0 + (0.2 * (len(preferred_domains) - domain_idx))

            # Contextual boost from collocations
            ctx_weight = self.sense_lookup.get_contextual_weight(
                sense, adjacent_lemmas, self.collocations
            )
            score *= (ctx_weight / sense.weight) if sense.weight > 0 else 1.0

            scored.append((score, sense))

        scored.sort(key=lambda x: -x[0])
        return scored[0][1]

    def _apply_style_to_gloss(
        self, base_gloss: str, style: RenderingStyle, constraints: dict, morph
    ) -> str:
        """Apply style-specific transformations to a gloss."""
        gloss = base_gloss

        if style == RenderingStyle.ULTRA_LITERAL:
            # Add hyphenation for multi-word glosses, imperative marking
            if constraints.get("force") == "command":
                gloss = gloss.capitalize() + "!"
            if " " in gloss:
                gloss = gloss.replace(" ", "-")

        elif style == RenderingStyle.NATURAL:
            # Keep it simple, add helping words
            if constraints.get("force") == "command" and morph.person == "second":
                gloss = gloss.capitalize() + "!"

        elif style == RenderingStyle.MEANING_FIRST:
            # Expand for clarity
            if constraints.get("aspect") == "completed_with_present_result":
                gloss = f"has {gloss}" if not gloss.startswith("has ") else gloss

        elif style == RenderingStyle.JEWISH_CONTEXT:
            # Historical/cultural framing
            pass  # Handled at sense selection level

        return gloss

    def _transform_ultra_literal(self, renderings: list[TokenRendering]) -> str:
        """Ultra-literal: preserve Greek word order, hyphenate compounds."""
        parts = []
        for r in renderings:
            parts.append(r.gloss)
        text = " ".join(parts)
        # Capitalize first word
        if text:
            text = text[0].upper() + text[1:]
        return text

    def _transform_natural(self, renderings: list[TokenRendering]) -> str:
        """Natural English: reorder for English syntax."""
        # Simple reordering heuristics
        parts = []
        i = 0
        while i < len(renderings):
            r = renderings[i]

            # Handle article + noun sequences
            if r.chosen_sense.domain == "article" and i + 1 < len(renderings):
                parts.append(r.gloss)
                i += 1
                continue

            # Handle genitive chains (X of-the Y -> the Y of X pattern)
            # This is simplified - real implementation would be more sophisticated
            parts.append(r.gloss)
            i += 1

        text = " ".join(parts)
        # Clean up punctuation
        text = text.replace(" !", "!")
        text = text.replace(" .", ".")
        text = text.replace("  ", " ")
        if text:
            text = text[0].upper() + text[1:]
        return text

    def _transform_meaning_first(self, renderings: list[TokenRendering]) -> str:
        """Meaning-first: prioritize semantic clarity over form."""
        parts = []
        for r in renderings:
            # Skip articles for smoother English
            if r.chosen_sense.domain == "article":
                continue
            gloss = r.gloss
            # Expand verb aspects
            if r.morph_constraints.get("aspect") == "completed_with_present_result":
                if not gloss.startswith("has "):
                    gloss = f"has {gloss}"
            parts.append(gloss)

        text = " ".join(parts)
        text = text.replace(" !", "!")
        if text:
            text = text[0].upper() + text[1:]
        return text

    def _transform_jewish_context(self, renderings: list[TokenRendering]) -> str:
        """Jewish-context: socio-historical framing."""
        parts = []
        for r in renderings:
            gloss = r.gloss

            # Handle "kingdom of heavens" -> "reign of Heaven" (Jewish circumlocution)
            # This would be more sophisticated with proper phrase detection
            parts.append(gloss)

        text = " ".join(parts)
        text = text.replace(" !", "!")
        if text:
            text = text[0].upper() + text[1:]
        return text
