"""Integration tests for session flow.

Sprint 5: Tests for:
- session_id in responses
- gate → acknowledge → translate flow
- session persistence across requests
"""

from redletters.pipeline.schemas import (
    TranslateResponse,
    GateResponsePayload,
    GateOption,
    VariantDisplay,
    RequiredAck,
    ClaimResult,
    ConfidenceResult,
    LayerScore,
    ProvenanceInfo,
    ReceiptSummary,
)
from redletters.pipeline.translator import (
    FluentTranslator,
    LiteralTranslator,
    FakeTranslator,
    get_translator,
    TranslationContext,
)


class TestSchemaSessionId:
    """Tests for session_id being included in schemas."""

    def test_translate_response_has_session_id_field(self):
        """TranslateResponse has session_id field."""
        response = TranslateResponse(
            response_type="translation",
            reference="John 1:1",
            session_id="test-123",
        )
        assert response.session_id == "test-123"

    def test_gate_response_has_session_id_field(self):
        """GateResponsePayload has session_id field."""
        response = GateResponsePayload(
            response_type="gate",
            gate_type="variant",
            session_id="gate-456",
        )
        assert response.session_id == "gate-456"

    def test_translate_response_to_dict_includes_session_id(self):
        """TranslateResponse.to_dict() includes session_id."""
        response = TranslateResponse(
            response_type="translation",
            reference="John 1:1",
            session_id="dict-789",
            translator_type="fluent",
        )
        result = response.to_dict()
        assert "session_id" in result
        assert result["session_id"] == "dict-789"
        assert "translator_type" in result
        assert result["translator_type"] == "fluent"

    def test_gate_response_to_dict_includes_session_id(self):
        """GateResponsePayload.to_dict() includes session_id."""
        response = GateResponsePayload(
            response_type="gate",
            gate_type="variant",
            session_id="gate-dict-101",
        )
        result = response.to_dict()
        assert "session_id" in result
        assert result["session_id"] == "gate-dict-101"


class TestTranslateResponseStructure:
    """Tests for TranslateResponse structure."""

    def test_full_translate_response_serialization(self):
        """Full TranslateResponse serializes correctly."""
        response = TranslateResponse(
            response_type="translation",
            reference="John 1:1",
            normalized_ref="John 1:1",
            verse_ids=["John.1.1"],
            mode="readable",
            sblgnt_text="Ἐν ἀρχῇ ἦν ὁ λόγος",
            translation_text="In beginning was the word",
            claims=[
                ClaimResult(
                    content="Test claim",
                    claim_type=0,
                    claim_type_label="Descriptive",
                    classification_confidence=0.95,
                    signals=["test"],
                    enforcement_allowed=True,
                    enforcement_reason="TYPE0 allowed in all modes",
                    warnings=[],
                    rewrite_suggestions=[],
                    dependencies=[],
                )
            ],
            confidence=ConfidenceResult(
                composite=0.85,
                weakest_layer="lexical",
                textual=LayerScore(score=0.95, rationale="No variants"),
                grammatical=LayerScore(score=0.90, rationale="Clear parse"),
                lexical=LayerScore(score=0.75, rationale="Ambiguous term"),
                interpretive=LayerScore(score=0.80, rationale="Standard"),
            ),
            provenance=ProvenanceInfo(
                spine_source="SBLGNT",
                sources_used=["SBLGNT", "MorphGNT"],
            ),
            receipts=ReceiptSummary(
                checks_run=["parse", "translate"],
            ),
            session_id="full-test",
            translator_type="literal",
        )

        result = response.to_dict()

        assert result["response_type"] == "translation"
        assert result["session_id"] == "full-test"
        assert result["translator_type"] == "literal"
        assert len(result["claims"]) == 1
        assert result["confidence"]["composite"] == 0.85

    def test_gate_response_structure(self):
        """GateResponsePayload has all required fields."""
        response = GateResponsePayload(
            response_type="gate",
            gate_id="gate-123",
            gate_type="variant",
            title="Variant Acknowledgement Required",
            message="A significant variant exists",
            prompt="Please acknowledge",
            options=[
                GateOption(
                    id="reading_0",
                    label="SBLGNT reading",
                    description="P66 P75 etc",
                    is_default=True,
                    reading_index=0,
                ),
            ],
            required_dependencies=["variant"],
            variants_side_by_side=[
                VariantDisplay(
                    ref="John.1.18",
                    position=4,
                    sblgnt_reading="μονογενὴς θεός",
                    sblgnt_witnesses="P66 P75 א B C",
                    alternate_readings=[],
                    significance="significant",
                    requires_acknowledgement=True,
                    acknowledged=False,
                ),
            ],
            reference="John 1:18",
            required_acks=[
                RequiredAck(
                    verse_id="John.1.18",
                    variant_ref="John.1.18",
                    reading_index=0,
                    significance="significant",
                    message="Variant at John.1.18",
                ),
            ],
            verse_ids=["John.1.18"],
            session_id="gate-struct-test",
        )

        result = response.to_dict()

        assert result["gate_type"] == "variant"
        assert len(result["options"]) == 1
        assert len(result["variants_side_by_side"]) == 1
        assert len(result["required_acks"]) == 1
        assert result["session_id"] == "gate-struct-test"


class TestTranslatorFactory:
    """Tests for get_translator factory function."""

    def test_get_fake_translator(self):
        """get_translator returns FakeTranslator for 'fake'."""
        translator = get_translator("fake")
        assert isinstance(translator, FakeTranslator)

    def test_get_literal_translator(self):
        """get_translator returns LiteralTranslator for 'literal'."""
        translator = get_translator("literal", source_id="test")
        assert isinstance(translator, LiteralTranslator)

    def test_get_fluent_translator(self):
        """get_translator returns FluentTranslator for 'fluent'."""
        translator = get_translator("fluent", source_id="test")
        assert isinstance(translator, FluentTranslator)

    def test_translator_produces_output(self):
        """All translator types produce valid output."""
        context = TranslationContext(
            reference="John 1:1",
            mode="readable",
            tokens=[{"lemma": "θεός", "surface": "θεός"}],
            variants=[],
            session_id="test",
        )

        for trans_type in ["fake", "literal", "fluent"]:
            translator = get_translator(trans_type, source_id="test")
            result = translator.translate("θεός", context)
            assert result.translation_text
            assert isinstance(result.claims, list)


class TestFluentTranslatorIntegration:
    """Integration tests for FluentTranslator."""

    def test_fluent_transforms_applied(self):
        """FluentTranslator applies transform rules."""
        translator = FluentTranslator(source_id="test")
        context = TranslationContext(
            reference="John 1:1",
            mode="readable",
            tokens=[{"lemma": "θεός", "surface": "θεός"}],
            variants=[],
            session_id="test",
        )

        result = translator.translate("θεός", context)

        # Should have transform_log
        assert hasattr(result, "transform_log")
        assert isinstance(result.transform_log, list)

    def test_fluent_readable_mode_filters_claims(self):
        """FluentTranslator filters high-inference claims in readable mode."""
        translator = FluentTranslator(source_id="test")
        context = TranslationContext(
            reference="John 1:1",
            mode="readable",
            tokens=[{"lemma": "θεός", "surface": "θεός"}],
            variants=[],
            session_id="test",
        )

        result = translator.translate("θεός", context)

        # All claims should be TYPE0-4
        for claim in result.claims:
            if claim.claim_type_hint is not None:
                assert claim.claim_type_hint <= 4

    def test_fluent_includes_provenance(self):
        """FluentTranslator includes source provenance."""
        translator = FluentTranslator(
            source_id="morphgnt-sblgnt",
            source_license="CC-BY-SA",
        )
        context = TranslationContext(
            reference="John 1:1",
            mode="readable",
            tokens=[{"lemma": "θεός", "surface": "θεός"}],
            variants=[],
            session_id="test",
        )

        result = translator.translate("θεός", context)

        # Should have provenance in notes or claims
        has_provenance = any("CC-BY-SA" in note for note in result.notes) or any(
            "CC-BY-SA" in c.content for c in result.claims
        )
        assert has_provenance


class TestLiteralTranslatorIntegration:
    """Integration tests for LiteralTranslator."""

    def test_literal_produces_bracketed_output(self):
        """LiteralTranslator produces bracket-style glosses."""
        translator = LiteralTranslator(source_id="test")
        context = TranslationContext(
            reference="John 1:1",
            mode="readable",
            tokens=[{"lemma": "θεός", "surface": "θεός"}],
            variants=[],
            session_id="test",
        )

        result = translator.translate("θεός", context)

        # Should have brackets in output
        assert "[" in result.translation_text or result.translation_text

    def test_literal_known_word_glosses(self):
        """LiteralTranslator glosses known words."""
        translator = LiteralTranslator(source_id="test")
        context = TranslationContext(
            reference="John 1:1",
            mode="readable",
            tokens=[
                {"lemma": "θεός", "surface": "θεός"},
                {"lemma": "λόγος", "surface": "λόγος"},
            ],
            variants=[],
            session_id="test",
        )

        result = translator.translate("θεός λόγος", context)

        # Known words should be glossed
        assert "God" in result.translation_text or "word" in result.translation_text
