"""Tests for epistemic inflation prevention in dossier output.

Sprint 11 (v0.3): Ensures dossier output uses neutral, descriptive language
without value judgments about textual priority or originality.

Non-negotiable: No hidden theology in core engine.
"""

from __future__ import annotations

import json
import pytest

from redletters.variants.dossier import (
    determine_evidence_class,
    SupportSummary,
    TypeSummary,
    DossierReading,
    DossierVariant,
    DossierReason,
    DossierAcknowledgement,
    WitnessSummary,
    Dossier,
    DossierSpine,
    DossierProvenance,
)


# Forbidden phrases that indicate epistemic inflation
FORBIDDEN_PHRASES = [
    "more likely original",
    "probably original",
    "best reading",
    "superior reading",
    "preferred reading",
    "authentic reading",
    "most likely",
    "certainly original",
    "obviously correct",
    "clearly authentic",
    "authoritative",
    "definitive reading",
    "correct text",
    "true reading",
    "original text",  # As a value judgment - descriptive use like "original hand" is OK
    "better supported",
    "stronger evidence",
    "weaker evidence",
    "more reliable",
    "less reliable",
    "more trustworthy",
    "earlier is better",
    "older is better",
]


class TestEvidenceClassLabels:
    """Test that evidence class labels are purely descriptive."""

    def test_edition_level_evidence_is_descriptive(self):
        """Edition-level evidence label is factual, not evaluative."""
        summary = SupportSummary(
            total_count=1,
            by_type={"edition": TypeSummary(count=1, sigla=["WH"])},
            earliest_century=19,
            provenance_packs=["westcott-hort-john"],
        )
        label = determine_evidence_class(summary)
        assert label == "edition-level evidence"
        assert "better" not in label.lower()
        assert "original" not in label.lower()
        assert "preferred" not in label.lower()

    def test_manuscript_level_evidence_is_descriptive(self):
        """Manuscript-level evidence label is factual, not evaluative."""
        summary = SupportSummary(
            total_count=3,
            by_type={"manuscript": TypeSummary(count=3, sigla=["P66", "P75", "01"])},
            earliest_century=2,
            provenance_packs=["some-pack"],
        )
        label = determine_evidence_class(summary)
        assert label == "manuscript-level evidence"
        assert "superior" not in label.lower()
        assert "reliable" not in label.lower()

    def test_tradition_aggregate_is_descriptive(self):
        """Tradition aggregate label is factual, not evaluative."""
        summary = SupportSummary(
            total_count=1,
            by_type={"tradition": TypeSummary(count=1, sigla=["Byz"])},
            earliest_century=9,
            provenance_packs=["byzantine-john"],
        )
        label = determine_evidence_class(summary)
        assert label == "tradition aggregate"
        assert "inferior" not in label.lower()
        assert "secondary" not in label.lower()

    def test_no_recorded_support_is_descriptive(self):
        """No recorded support label is factual, not evaluative."""
        summary = SupportSummary(
            total_count=0,
            by_type={},
            earliest_century=None,
            provenance_packs=[],
        )
        label = determine_evidence_class(summary)
        assert label == "no recorded support"
        assert "questionable" not in label.lower()
        assert "invalid" not in label.lower()

    def test_mixed_evidence_is_descriptive(self):
        """Mixed evidence label is factual, not evaluative."""
        summary = SupportSummary(
            total_count=2,
            by_type={
                "edition": TypeSummary(count=1, sigla=["NA28"]),
                "tradition": TypeSummary(count=1, sigla=["Byz"]),
            },
            earliest_century=19,
            provenance_packs=["some-pack"],
        )
        label = determine_evidence_class(summary)
        # Should be "manuscript-level evidence" if MS present, else "mixed evidence"
        assert label in ("mixed evidence", "manuscript-level evidence")
        for forbidden in FORBIDDEN_PHRASES:
            assert forbidden.lower() not in label.lower()


class TestDossierSerialization:
    """Test that dossier JSON output contains no epistemic inflation."""

    def test_dossier_reading_no_forbidden_phrases(self):
        """DossierReading serialization contains no value judgments."""
        reading = DossierReading(
            index=0,
            text="ἐν ἀρχῇ",
            is_spine=True,
            witnesses=[],
            witness_summary=WitnessSummary(),
            source_packs=["westcott-hort-john"],
            support_summary=SupportSummary(
                total_count=1,
                by_type={"edition": TypeSummary(count=1, sigla=["WH"])},
                earliest_century=19,
                provenance_packs=["westcott-hort-john"],
            ),
            evidence_class="edition-level evidence",
        )

        serialized = json.dumps(reading.to_dict(), indent=2)

        for forbidden in FORBIDDEN_PHRASES:
            assert forbidden.lower() not in serialized.lower(), (
                f"Found forbidden phrase '{forbidden}' in DossierReading output"
            )

    def test_dossier_variant_no_forbidden_phrases(self):
        """DossierVariant serialization contains no value judgments."""
        variant = DossierVariant(
            ref="John.1.1:0",
            position=0,
            classification="SUBSTITUTION",
            significance="TYPE3",
            gating_requirement="requires_acknowledgement",
            reason=DossierReason(
                code="SPELLING_VARIANT",
                summary="Minor orthographic difference",
                detail="Spelling variation in article",
            ),
            readings=[
                DossierReading(
                    index=0,
                    text="ἐν ἀρχῇ",
                    is_spine=True,
                    witnesses=[],
                    witness_summary=WitnessSummary(),
                    source_packs=["sblgnt"],
                    evidence_class="edition-level evidence",
                )
            ],
            acknowledgement=DossierAcknowledgement(
                required=True,
                acknowledged=False,
            ),
        )

        serialized = json.dumps(variant.to_dict(), indent=2)

        for forbidden in FORBIDDEN_PHRASES:
            assert forbidden.lower() not in serialized.lower(), (
                f"Found forbidden phrase '{forbidden}' in DossierVariant output"
            )

    def test_full_dossier_no_forbidden_phrases(self):
        """Complete Dossier serialization contains no value judgments."""
        dossier = Dossier(
            reference="John.1.1",
            scope="verse",
            generated_at="2026-02-01T12:00:00Z",
            spine=DossierSpine(
                source_id="morphgnt-sblgnt",
                text="ἐν ἀρχῇ ἦν ὁ λόγος",
                is_default=True,
            ),
            variants=[
                DossierVariant(
                    ref="John.1.1:0",
                    position=0,
                    classification="SUBSTITUTION",
                    significance="TYPE2",
                    gating_requirement="none",
                    reason=DossierReason(
                        code="MINOR",
                        summary="Minor spelling difference",
                    ),
                    readings=[
                        DossierReading(
                            index=0,
                            text="ἐν ἀρχῇ",
                            is_spine=True,
                            witnesses=[],
                            witness_summary=WitnessSummary(),
                            source_packs=["sblgnt"],
                            evidence_class="edition-level evidence",
                        )
                    ],
                    acknowledgement=DossierAcknowledgement(
                        required=False, acknowledged=False
                    ),
                )
            ],
            provenance=DossierProvenance(
                spine_source="morphgnt-sblgnt",
                comparative_packs=["westcott-hort-john"],
                build_timestamp="2026-02-01T12:00:00Z",
            ),
            witness_density_note="Limited manuscript data available",
        )

        serialized = json.dumps(dossier.to_dict(), indent=2)

        for forbidden in FORBIDDEN_PHRASES:
            assert forbidden.lower() not in serialized.lower(), (
                f"Found forbidden phrase '{forbidden}' in Dossier output"
            )


class TestDossierReasonCodes:
    """Test that reason codes and summaries use neutral language."""

    @pytest.mark.parametrize(
        "code,summary",
        [
            ("ORTHOGRAPHIC", "Spelling variation"),
            ("GRAMMATICAL", "Grammatical form differs"),
            ("LEXICAL", "Different word used"),
            ("WORD_ORDER", "Word order differs"),
            ("ADDITION", "Text added"),
            ("OMISSION", "Text omitted"),
            ("SUBSTITUTION", "Text substituted"),
        ],
    )
    def test_reason_summaries_are_neutral(self, code: str, summary: str):
        """Reason summaries describe what differs, not which is better."""
        reason = DossierReason(code=code, summary=summary)
        serialized = json.dumps(reason.to_dict())

        for forbidden in FORBIDDEN_PHRASES:
            assert forbidden.lower() not in serialized.lower(), (
                f"Found forbidden phrase '{forbidden}' in reason: {code}"
            )


class TestEvidenceClassNoEpistemicHierarchy:
    """Test that evidence class determination has no implicit hierarchy."""

    def test_manuscript_not_inherently_superior(self):
        """Manuscript evidence is not labeled as inherently superior to editions."""
        ms_summary = SupportSummary(
            total_count=1,
            by_type={"manuscript": TypeSummary(count=1, sigla=["P66"])},
            earliest_century=2,
            provenance_packs=["some-pack"],
        )
        ed_summary = SupportSummary(
            total_count=1,
            by_type={"edition": TypeSummary(count=1, sigla=["NA28"])},
            earliest_century=21,
            provenance_packs=["some-pack"],
        )

        ms_label = determine_evidence_class(ms_summary)
        ed_label = determine_evidence_class(ed_summary)

        # Both should be neutral descriptors
        assert "better" not in ms_label
        assert "worse" not in ed_label
        assert "inferior" not in ed_label
        assert "superior" not in ms_label

    def test_earlier_century_not_privileged_in_label(self):
        """Earlier attestation doesn't get privileged language in labels."""
        early_summary = SupportSummary(
            total_count=1,
            by_type={"manuscript": TypeSummary(count=1, sigla=["P52"])},
            earliest_century=2,
            provenance_packs=["some-pack"],
        )
        late_summary = SupportSummary(
            total_count=1,
            by_type={"manuscript": TypeSummary(count=1, sigla=["GA 2464"])},
            earliest_century=9,
            provenance_packs=["some-pack"],
        )

        early_label = determine_evidence_class(early_summary)
        late_label = determine_evidence_class(late_summary)

        # Both should get the same neutral label
        assert early_label == late_label
        assert "better" not in early_label
        assert "more authoritative" not in early_label


class TestAllEvidenceClassValues:
    """Test all possible evidence class return values are neutral."""

    ALL_EVIDENCE_CLASSES = [
        "edition-level evidence",
        "manuscript-level evidence",
        "tradition aggregate",
        "mixed evidence",
        "secondary evidence",
        "no recorded support",
    ]

    @pytest.mark.parametrize("evidence_class", ALL_EVIDENCE_CLASSES)
    def test_evidence_class_is_neutral(self, evidence_class: str):
        """Each evidence class value uses neutral language."""
        for forbidden in FORBIDDEN_PHRASES:
            assert forbidden.lower() not in evidence_class.lower(), (
                f"Evidence class '{evidence_class}' contains forbidden phrase '{forbidden}'"
            )

        # Additional checks for implicit hierarchy words
        assert "superior" not in evidence_class.lower()
        assert "inferior" not in evidence_class.lower()
        assert "better" not in evidence_class.lower()
        assert "worse" not in evidence_class.lower()
        assert "best" not in evidence_class.lower()
        assert "worst" not in evidence_class.lower()
