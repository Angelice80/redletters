"""Tests for receipt generation and validation."""

from redletters.engine.receipts import (
    format_receipt_summary,
    validate_receipt_completeness,
    receipt_to_bibtex_style,
)


class TestReceiptValidation:
    """Tests for receipt completeness validation."""

    def test_complete_receipt_passes(self):
        receipt = {
            "surface": "μετανοεῖτε",
            "lemma": "μετανοέω",
            "morph": {"mood": "imperative"},
            "chosen_sense_id": "metanoeo.1",
            "chosen_gloss": "change-your-minds",
            "sense_source": "BDAG",
            "sense_weight": 0.8,
            "rationale": "test rationale",
        }

        is_complete, missing = validate_receipt_completeness(receipt)
        assert is_complete
        assert len(missing) == 0

    def test_incomplete_receipt_fails(self):
        receipt = {
            "surface": "μετανοεῖτε",
            "lemma": "μετανοέω",
            # Missing many fields
        }

        is_complete, missing = validate_receipt_completeness(receipt)
        assert not is_complete
        assert "morph" in missing
        assert "chosen_sense_id" in missing


class TestReceiptFormatting:
    """Tests for receipt formatting utilities."""

    def test_bibtex_style_format(self):
        receipt = {
            "surface": "μετανοεῖτε",
            "chosen_gloss": "change-your-minds",
            "sense_source": "BDAG",
            "chosen_sense_id": "metanoeo.1",
            "sense_weight": 0.80,
        }

        formatted = receipt_to_bibtex_style(receipt)

        assert "μετανοεῖτε" in formatted
        assert "change-your-minds" in formatted
        assert "BDAG" in formatted
        assert "metanoeo.1" in formatted
        assert "0.80" in formatted

    def test_summary_format(self):
        receipts = [
            {
                "surface": "μετανοεῖτε",
                "lemma": "μετανοέω",
                "chosen_gloss": "change-your-minds",
                "sense_source": "BDAG",
                "definition": "to change one's mind",
            }
        ]

        summary = format_receipt_summary(receipts)

        assert "μετανοεῖτε" in summary
        assert "μετανοέω" in summary
        assert "change-your-minds" in summary
