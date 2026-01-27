"""Tests for receipt generation and validation."""

from redletters.engine.receipts import (
    format_receipt_summary,
    receipt_to_bibtex_style,
    validate_receipt_completeness,
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


class TestSourceRoleDisclosure:
    """Tests for source role and limitation disclosures."""

    def test_strongs_has_known_role(self):
        """Strong's should be recognized with appropriate role."""
        from redletters.engine.receipts import get_source_role

        role = get_source_role("Strong's")

        assert role is not None
        assert "inventory" in role.role.lower()
        assert "non-authoritative" in role.role.lower()
        assert len(role.limitations) > 0

    def test_strongs_limitation_mentions_19th_century(self):
        """Strong's limitations should mention historical context."""
        from redletters.engine.receipts import get_source_role

        role = get_source_role("Strong's")

        assert role is not None
        limitation_text = " ".join(role.limitations).lower()
        assert "19th" in limitation_text or "compression" in limitation_text

    def test_source_receipt_format(self):
        """Source receipt should include role and limitation."""
        from redletters.engine.receipts import format_source_receipt

        receipt = format_source_receipt("Strong's")

        assert "Source:" in receipt
        assert "Role:" in receipt
        assert "limitation" in receipt.lower()

    def test_summary_with_source_roles(self):
        """Summary with source roles should include disclosures."""
        receipts = [
            {
                "surface": "μετανοέω",
                "lemma": "μετανοέω",
                "chosen_gloss": "repent",
                "sense_source": "Strong's",
                "definition": "to change one's mind",
            }
        ]

        summary = format_receipt_summary(receipts, include_source_roles=True)

        assert "Source Notes" in summary
        # Should include warning about Strong's limitations
        assert "inventory" in summary.lower() or "19th" in summary.lower()

    def test_unknown_source_handled_gracefully(self):
        """Unknown sources should not crash."""
        from redletters.engine.receipts import format_source_receipt, get_source_role

        role = get_source_role("Unknown Lexicon 2050")
        assert role is None

        receipt = format_source_receipt("Unknown Lexicon 2050")
        assert "unknown provenance" in receipt.lower()
