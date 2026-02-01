"""Deterministic ranking heuristic for candidate renderings."""

from __future__ import annotations

import sqlite3
from redletters.engine.generator import CandidateRendering
from redletters.config import Settings


class RenderingRanker:
    """
    Ranks candidate renderings using a deterministic, explainable heuristic.

    Score formula:
        score = (morph_fit × W1) + (sense_weight × W2) + (collocation × W3) - (uncommon_penalty × W4)

    All weights and calculations are transparent and reproducible.
    """

    def __init__(self, conn: sqlite3.Connection, settings: Settings | None = None):
        self.conn = conn
        self.settings = settings or Settings()

    def rank(
        self, candidates: list[CandidateRendering], tokens: list[dict]
    ) -> list[dict]:
        """
        Rank candidates and return sorted list with scores.

        Args:
            candidates: List of CandidateRendering objects
            tokens: Original tokens for context

        Returns:
            List of dicts with rendering info + scores, highest first
        """
        scored = []

        for candidate in candidates:
            score, breakdown = self._calculate_score(candidate, tokens)
            candidate.raw_score = score

            scored.append(
                {
                    "style": candidate.style.value,
                    "text": candidate.text,
                    "score": round(score, 3),
                    "score_breakdown": breakdown,
                    "receipts": self._generate_receipts(candidate),
                }
            )

        # Sort by score descending
        scored.sort(key=lambda x: -x["score"])
        return scored

    def _calculate_score(
        self, candidate: CandidateRendering, tokens: list[dict]
    ) -> tuple[float, dict]:
        """
        Calculate composite score for a candidate.

        Returns:
            Tuple of (final_score, breakdown_dict)
        """
        morph_fit = 0.0
        sense_weight = 0.0
        collocation_bonus = 0.0
        uncommon_penalty = 0.0

        n_tokens = len(candidate.token_renderings)
        if n_tokens == 0:
            return 0.0, {}

        for tr in candidate.token_renderings:
            # Morphology fit: 1.0 if constraints satisfied, penalize ambiguity
            token_morph_fit = 1.0
            if tr.ambiguity_type == "morphological":
                token_morph_fit = 0.8  # Slight penalty for morphological ambiguity
            morph_fit += token_morph_fit

            # Sense weight: use the chosen sense's weight
            sense_weight += tr.chosen_sense.weight

            # Collocation bonus already factored into sense selection
            # Add small bonus if sense domain matches common patterns
            if tr.chosen_sense.domain in ("cognitive", "religious", "spatial"):
                collocation_bonus += 0.1

            # Uncommon penalty: penalize low-weight senses
            if tr.chosen_sense.weight < 0.5:
                uncommon_penalty += 0.5 - tr.chosen_sense.weight

        # Normalize by token count
        morph_fit /= n_tokens
        sense_weight /= n_tokens
        collocation_bonus /= n_tokens
        uncommon_penalty /= n_tokens

        # Calculate final score
        s = self.settings
        final_score = (
            (morph_fit * s.morph_fit_weight)
            + (sense_weight * s.sense_weight_weight)
            + (collocation_bonus * s.collocation_weight)
            - (uncommon_penalty * s.uncommon_penalty_weight)
        )

        breakdown = {
            "morph_fit": round(morph_fit, 3),
            "sense_weight": round(sense_weight, 3),
            "collocation_bonus": round(collocation_bonus, 3),
            "uncommon_penalty": round(uncommon_penalty, 3),
            "weights_used": {
                "morph_fit": s.morph_fit_weight,
                "sense_weight": s.sense_weight_weight,
                "collocation": s.collocation_weight,
                "uncommon_penalty": s.uncommon_penalty_weight,
            },
        }

        return final_score, breakdown

    def _generate_receipts(self, candidate: CandidateRendering) -> list[dict]:
        """Generate interpretive receipts for each token rendering."""
        receipts = []

        for tr in candidate.token_renderings:
            receipt = {
                "surface": tr.surface,
                "lemma": tr.lemma,
                "morph": tr.morph_constraints,
                "chosen_sense_id": tr.chosen_sense.sense_id,
                "chosen_gloss": tr.gloss,
                "sense_source": tr.chosen_sense.source,
                "sense_weight": tr.chosen_sense.weight,
                "sense_domain": tr.chosen_sense.domain,
                "rationale": self._generate_rationale(tr, candidate.style.value),
            }

            if tr.ambiguity_type:
                receipt["ambiguity_type"] = tr.ambiguity_type
            if tr.alternate_glosses:
                receipt["alternate_glosses"] = tr.alternate_glosses
            if tr.chosen_sense.definition:
                receipt["definition"] = tr.chosen_sense.definition

            receipts.append(receipt)

        return receipts

    def _generate_rationale(self, tr, style: str) -> str:
        """Generate human-readable rationale for a choice."""
        parts = []

        # Explain sense selection
        parts.append(
            f"Selected '{tr.chosen_sense.gloss}' (weight={tr.chosen_sense.weight:.2f})"
        )

        if tr.chosen_sense.domain:
            parts.append(f"domain: {tr.chosen_sense.domain}")

        parts.append(f"source: {tr.chosen_sense.source}")

        # Style-specific note
        style_notes = {
            "ultra-literal": "preserving Greek form/order",
            "natural": "idiomatic English rendering",
            "meaning-first": "prioritizing semantic clarity",
            "jewish-context": "socio-historical Jewish framing",
        }
        if style in style_notes:
            parts.append(f"style: {style_notes[style]}")

        if tr.ambiguity_type:
            parts.append(f"NOTE: {tr.ambiguity_type} ambiguity present")

        return "; ".join(parts)
