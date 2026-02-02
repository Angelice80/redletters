"""Translation dataset export for scholarly reproducibility.

v0.5.0: Export token ledger and renderings to JSONL format.

Each line contains a verse's translation data with:
- Token-level ledger (gloss, morph, confidence)
- Renderings with receipts
- Provenance
- Schema version
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from redletters.export import EXPORT_SCHEMA_VERSION
from redletters.export.identifiers import (
    token_id,
    canonical_json,
)


@dataclass
class TranslationRow:
    """Single row in translation export (one verse)."""

    verse_id: str
    normalized_ref: str
    spine_text: str
    tokens: list[dict]
    renderings: list[dict]
    confidence_summary: dict
    provenance: dict
    schema_version: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "verse_id": self.verse_id,
            "normalized_ref": self.normalized_ref,
            "spine_text": self.spine_text,
            "tokens": self.tokens,
            "renderings": self.renderings,
            "confidence_summary": self.confidence_summary,
            "provenance": self.provenance,
            "schema_version": self.schema_version,
        }

    def to_jsonl(self) -> str:
        """Convert to canonical JSONL line."""
        return canonical_json(self.to_dict())


def _build_token_dict(verse_ref: str, token_data: dict, position: int) -> dict:
    """Build token dictionary with stable ID."""
    tid = token_id(verse_ref, position)

    # Extract confidence layers
    confidence = token_data.get("confidence", {})

    return {
        "token_id": tid,
        "position": position,
        "surface": token_data.get("surface", ""),
        "normalized": token_data.get("normalized", ""),
        "lemma": token_data.get("lemma"),
        "morph": token_data.get("morph"),
        "gloss": token_data.get("gloss", ""),
        "gloss_source": token_data.get("gloss_source", ""),
        "confidence": {
            "textual": confidence.get("textual", 1.0),
            "grammatical": confidence.get("grammatical", 1.0),
            "lexical": confidence.get("lexical", 1.0),
            "interpretive": confidence.get("interpretive", 1.0),
        },
        "notes": token_data.get("notes", []),
    }


def _ledger_to_row(verse_ledger: dict) -> TranslationRow:
    """Convert VerseLedger dict to TranslationRow."""
    verse_id_val = verse_ledger.get("verse_id", "")
    normalized_ref = verse_ledger.get("normalized_ref", verse_id_val)

    # Build tokens with stable IDs
    tokens = []
    raw_tokens = verse_ledger.get("tokens", [])
    for i, tok in enumerate(raw_tokens):
        pos = tok.get("position", i)
        tokens.append(_build_token_dict(verse_id_val, tok, pos))

    # Build spine text from tokens
    spine_text = " ".join(t.get("surface", "") for t in raw_tokens)

    # Get provenance (v0.6.0: includes sense_packs_used)
    prov = verse_ledger.get("provenance", {})
    provenance = {
        "spine_source_id": prov.get("spine_source_id", ""),
        "comparative_sources_used": prov.get("comparative_sources_used", []),
        "evidence_class_summary": prov.get("evidence_class_summary", {}),
    }
    # v0.6.0: Include sense pack citation metadata if present
    if prov.get("sense_packs_used"):
        provenance["sense_packs_used"] = prov["sense_packs_used"]

    # Calculate confidence summary (v0.8.0: includes composite + bucket)
    from redletters.confidence.scoring import bucket_confidence

    if tokens:
        avg_t = sum(t["confidence"]["textual"] for t in tokens) / len(tokens)
        avg_g = sum(t["confidence"]["grammatical"] for t in tokens) / len(tokens)
        avg_l = sum(t["confidence"]["lexical"] for t in tokens) / len(tokens)
        avg_i = sum(t["confidence"]["interpretive"] for t in tokens) / len(tokens)
        # Composite = geometric mean
        composite = (avg_t * avg_g * avg_l * avg_i) ** 0.25
        confidence_summary = {
            "textual": round(avg_t, 3),
            "grammatical": round(avg_g, 3),
            "lexical": round(avg_l, 3),
            "interpretive": round(avg_i, 3),
            "composite": round(composite, 3),
            "bucket": bucket_confidence(composite),
        }
    else:
        confidence_summary = {
            "textual": 1.0,
            "grammatical": 1.0,
            "lexical": 1.0,
            "interpretive": 1.0,
            "composite": 1.0,
            "bucket": "high",
        }

    # Renderings (if available in ledger)
    renderings = verse_ledger.get("renderings", [])

    return TranslationRow(
        verse_id=verse_id_val,
        normalized_ref=normalized_ref,
        spine_text=spine_text,
        tokens=tokens,
        renderings=renderings,
        confidence_summary=confidence_summary,
        provenance=provenance,
        schema_version=EXPORT_SCHEMA_VERSION,
    )


class TranslationExporter:
    """Export translation ledger to JSONL format.

    Usage:
        exporter = TranslationExporter()
        exporter.export_to_file(ledger_data, "translation.jsonl")
    """

    def __init__(self):
        """Initialize exporter."""
        pass

    def iter_rows(self, ledger_data: list[dict]) -> Iterator[TranslationRow]:
        """Iterate over translation rows from ledger data.

        Args:
            ledger_data: List of VerseLedger dictionaries

        Yields:
            TranslationRow objects
        """
        for verse_ledger in ledger_data:
            yield _ledger_to_row(verse_ledger)

    def export_to_file(
        self,
        ledger_data: list[dict],
        output_path: str | Path,
        reference: str = "",
    ) -> dict:
        """Export translation to JSONL file.

        Args:
            ledger_data: List of VerseLedger dictionaries
            output_path: Output file path
            reference: Original reference string (for metadata)

        Returns:
            Export metadata dict
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        row_count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for row in self.iter_rows(ledger_data):
                f.write(row.to_jsonl() + "\n")
                row_count += 1

        return {
            "type": "translation",
            "reference": reference,
            "output_path": str(output_path),
            "row_count": row_count,
            "schema_version": EXPORT_SCHEMA_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

    def export_to_list(self, ledger_data: list[dict]) -> list[dict]:
        """Export translation to list of dicts (for testing).

        Args:
            ledger_data: List of VerseLedger dictionaries

        Returns:
            List of row dictionaries
        """
        return [row.to_dict() for row in self.iter_rows(ledger_data)]

    @staticmethod
    def from_translate_response(response_dict: dict) -> list[dict]:
        """Extract ledger data from translate response.

        Args:
            response_dict: TranslateResponse as dictionary

        Returns:
            List of VerseLedger dictionaries
        """
        ledger = response_dict.get("ledger", [])
        if not ledger:
            # Try to build minimal ledger from tokens
            tokens = response_dict.get("tokens", [])
            verse_ids = response_dict.get("verse_ids", [])
            if tokens and verse_ids:
                # Group tokens by verse
                verse_ledgers = []
                for vid in verse_ids:
                    verse_tokens = [
                        t
                        for t in tokens
                        if f"{t.get('book', '')}.{t.get('chapter', '')}.{t.get('verse', '')}"
                        == vid
                    ]
                    if verse_tokens:
                        verse_ledgers.append(
                            {
                                "verse_id": vid,
                                "normalized_ref": vid.replace(".", " ").replace(
                                    " ", ":", 1
                                ),
                                "tokens": [
                                    {
                                        "position": t.get("position", i),
                                        "surface": t.get("surface", ""),
                                        "normalized": t.get("surface", "").lower(),
                                        "lemma": t.get("lemma"),
                                        "morph": t.get("morph"),
                                        "gloss": "",
                                        "gloss_source": "",
                                        "confidence": {
                                            "textual": 1.0,
                                            "grammatical": 1.0,
                                            "lexical": 1.0,
                                            "interpretive": 1.0,
                                        },
                                    }
                                    for i, t in enumerate(verse_tokens)
                                ],
                                "provenance": {},
                            }
                        )
                return verse_ledgers
        return ledger
