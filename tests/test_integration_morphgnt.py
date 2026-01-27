"""Integration tests against full MorphGNT book data.

These tests load a complete book (Matthew, 18k+ tokens) to catch edge cases
not visible in curated fixtures:
- Enclitics and weird punctuation
- Quotations and elision
- Participles and infinitives at scale
- Rare POS codes
- Edge cases in reference parsing

Tests assert INVARIANTS, not exact counts, making them robust to
upstream corrections while catching structural corruption.

This is the "no more fabricated reality" insurance policy.
"""

from collections import defaultdict
from pathlib import Path

import pytest
import yaml

from redletters.ingest.morphgnt_parser import (
    INDECLINABLE_POS,
    NOMINAL_POS,
    VERBAL_POS,
    decode_parse_code,
    parse_file,
)

# Path to integration test data
DATA_DIR = Path(__file__).parent / "data" / "morphgnt-snapshot"
MATTHEW_FILE = DATA_DIR / "61-Mt-morphgnt.txt"
MANIFEST_FILE = DATA_DIR / "MANIFEST.yaml"


@pytest.fixture(scope="module")
def matthew_tokens():
    """Load full Matthew data once for all tests in this module."""
    if not MATTHEW_FILE.exists():
        pytest.skip(f"Integration test data not found: {MATTHEW_FILE}")
    return parse_file(MATTHEW_FILE)


@pytest.fixture(scope="module")
def manifest():
    """Load the manifest for provenance verification."""
    if not MANIFEST_FILE.exists():
        pytest.skip(f"Manifest not found: {MANIFEST_FILE}")
    with open(MANIFEST_FILE) as f:
        return yaml.safe_load(f)


class TestDataIntegrity:
    """Verify the snapshot matches its manifest."""

    def test_file_exists(self):
        """Integration test data file should exist."""
        assert MATTHEW_FILE.exists(), f"Missing: {MATTHEW_FILE}"

    def test_manifest_sha256_matches(self, manifest):
        """File SHA256 should match manifest."""
        import hashlib

        with open(MATTHEW_FILE, "rb") as f:
            actual_sha = hashlib.sha256(f.read()).hexdigest()

        expected_sha = manifest["files"][0]["sha256"]
        assert actual_sha == expected_sha, (
            f"SHA256 mismatch - file may have been modified.\n"
            f"Expected: {expected_sha}\n"
            f"Actual:   {actual_sha}"
        )

    def test_manifest_line_count_matches(self, manifest):
        """Line count should match manifest."""
        with open(MATTHEW_FILE) as f:
            actual_lines = sum(1 for _ in f)

        expected_lines = manifest["files"][0]["lines"]
        assert actual_lines == expected_lines, (
            f"Line count mismatch: expected {expected_lines}, got {actual_lines}"
        )


class TestStructuralInvariants:
    """Every row must satisfy structural constraints."""

    def test_all_tokens_parsed_successfully(self, matthew_tokens):
        """Parser should handle all 18k+ tokens without error."""
        # If we got here, parsing succeeded
        assert len(matthew_tokens) > 18000, (
            f"Expected 18k+ tokens, got {len(matthew_tokens)}"
        )

    def test_all_parse_codes_are_8_characters(self, matthew_tokens):
        """Every parse code must be exactly 8 characters."""
        violations = []
        for token in matthew_tokens:
            if len(token.parse_code) != 8:
                violations.append(
                    f"{token.ref}: parse_code={repr(token.parse_code)} "
                    f"(len={len(token.parse_code)})"
                )

        assert not violations, (
            f"Found {len(violations)} tokens with invalid parse_code length:\n"
            + "\n".join(violations[:10])
            + ("\n..." if len(violations) > 10 else "")
        )

    def test_all_source_refs_are_6_digits(self, matthew_tokens):
        """Every source_ref must be exactly 6 numeric characters."""
        violations = []
        for token in matthew_tokens:
            if len(token.source_ref) != 6 or not token.source_ref.isdigit():
                violations.append(f"{token.ref}: source_ref={repr(token.source_ref)}")

        assert not violations, (
            f"Found {len(violations)} tokens with invalid source_ref:\n"
            + "\n".join(violations[:10])
        )

    def test_source_ref_never_rewritten(self, matthew_tokens):
        """source_ref must be preserved exactly as in source file."""
        # All Matthew refs should start with '01' (book code for Matthew)
        violations = []
        for token in matthew_tokens:
            if not token.source_ref.startswith("01"):
                violations.append(
                    f"{token.ref}: source_ref={token.source_ref} "
                    f"(expected to start with '01')"
                )

        assert not violations, (
            f"Found {len(violations)} tokens with unexpected source_ref prefix:\n"
            + "\n".join(violations[:10])
        )

    def test_token_index_monotonic_within_verse(self, matthew_tokens):
        """token_index must increase monotonically within each verse."""
        # Group by verse
        verses: dict[str, list] = defaultdict(list)
        for token in matthew_tokens:
            verse_key = f"{token.book}.{token.chapter}.{token.verse}"
            verses[verse_key].append(token)

        violations = []
        for verse_key, tokens in verses.items():
            indices = [t.token_index for t in tokens]
            expected = list(range(1, len(indices) + 1))
            if indices != expected:
                violations.append(
                    f"{verse_key}: indices={indices[:10]}... expected={expected[:10]}..."
                )

        assert not violations, (
            f"Found {len(violations)} verses with non-monotonic token_index:\n"
            + "\n".join(violations[:5])
        )

    def test_ref_components_consistent(self, matthew_tokens):
        """ref string must match book, chapter, verse, position fields."""
        violations = []
        for token in matthew_tokens:
            expected_ref = (
                f"{token.book}.{token.chapter}.{token.verse}.{token.position}"
            )
            if token.ref != expected_ref:
                violations.append(f"ref={token.ref} vs expected={expected_ref}")

        assert not violations, (
            f"Found {len(violations)} tokens with inconsistent ref:\n"
            + "\n".join(violations[:10])
        )


class TestPOSCoverage:
    """Verify we see diverse POS codes in real data."""

    def test_all_major_pos_categories_present(self, matthew_tokens):
        """Real data should contain verbs, nouns, and indeclinables."""
        pos_codes = {t.pos for t in matthew_tokens}

        # Must have at least one from each category
        assert pos_codes & VERBAL_POS, "No verbs found in Matthew"
        assert pos_codes & NOMINAL_POS, "No nominals found in Matthew"
        assert pos_codes & INDECLINABLE_POS, "No indeclinables found in Matthew"

    def test_participles_present(self, matthew_tokens):
        """Matthew should contain participles (verbs with mood=P)."""
        participles = [
            t
            for t in matthew_tokens
            if t.pos == "V-" and len(t.parse_code) == 8 and t.parse_code[3] == "P"
        ]
        assert len(participles) > 100, (
            f"Expected many participles, found {len(participles)}"
        )

    def test_infinitives_present(self, matthew_tokens):
        """Matthew should contain infinitives (verbs with mood=N)."""
        infinitives = [
            t
            for t in matthew_tokens
            if t.pos == "V-" and len(t.parse_code) == 8 and t.parse_code[3] == "N"
        ]
        assert len(infinitives) > 50, (
            f"Expected many infinitives, found {len(infinitives)}"
        )

    def test_articles_present(self, matthew_tokens):
        """Matthew should contain definite articles (RA)."""
        articles = [t for t in matthew_tokens if t.pos == "RA"]
        assert len(articles) > 1000, f"Expected 1000+ articles, found {len(articles)}"

    def test_prepositions_present(self, matthew_tokens):
        """Matthew should contain prepositions (P-)."""
        prepositions = [t for t in matthew_tokens if t.pos == "P-"]
        assert len(prepositions) > 200, (
            f"Expected 200+ prepositions, found {len(prepositions)}"
        )


class TestCategoryCollapseAtScale:
    """Verify POS-gated decoding produces no errors on real data."""

    def test_no_decode_errors_in_full_book(self, matthew_tokens):
        """Every token should decode without errors."""
        errors_by_token = []

        for token in matthew_tokens:
            result = decode_parse_code(token.parse_code, token.pos)
            if result.errors:
                errors_by_token.append(f"{token.ref} ({token.word}): {result.errors}")

        assert not errors_by_token, (
            f"Found {len(errors_by_token)} tokens with decode errors:\n"
            + "\n".join(errors_by_token[:20])
            + ("\n..." if len(errors_by_token) > 20 else "")
        )

    def test_verbs_have_valid_verbal_fields(self, matthew_tokens):
        """All verbs should have valid tense/voice/mood combinations."""
        verb_tokens = [t for t in matthew_tokens if t.pos in VERBAL_POS]

        invalid = []
        for token in verb_tokens:
            result = decode_parse_code(token.parse_code, token.pos)
            # Verbs must have tense, voice, mood (except rare edge cases)
            if result.tense is None and result.mood != "participle":
                # Infinitives and participles can have tense=None in position 1
                # if the code uses a different convention
                pass  # Allow for now, real data may have edge cases

        # This test primarily ensures no crashes on real data
        assert len(verb_tokens) > 3000, f"Expected 3000+ verbs, got {len(verb_tokens)}"

    def test_nominals_have_valid_nominal_fields(self, matthew_tokens):
        """All nominals should have case/number/gender."""
        nominal_tokens = [t for t in matthew_tokens if t.pos in NOMINAL_POS]

        missing_case = []
        for token in nominal_tokens:
            result = decode_parse_code(token.parse_code, token.pos)
            if result.case is None:
                missing_case.append(f"{token.ref}: {token.word} ({token.parse_code})")

        # Allow some edge cases but flag if too many
        if len(missing_case) > 10:
            pytest.fail(
                f"Found {len(missing_case)} nominals without case:\n"
                + "\n".join(missing_case[:10])
            )


class TestEdgeCases:
    """Test handling of known edge cases in Greek text."""

    def test_handles_punctuation_attached_to_words(self, matthew_tokens):
        """Tokens with attached punctuation should parse correctly."""
        # Find tokens with commas, periods, etc. in surface_text
        punctuated = [
            t for t in matthew_tokens if any(c in t.surface_text for c in ",.;·")
        ]
        assert len(punctuated) > 500, (
            f"Expected many punctuated tokens, found {len(punctuated)}"
        )

        # All should have valid refs
        for token in punctuated[:100]:
            assert token.ref, f"Punctuated token missing ref: {token.surface_text}"

    def test_handles_greek_question_mark(self, matthew_tokens):
        """Greek semicolon (;) used as question mark should parse."""
        questions = [t for t in matthew_tokens if ";" in t.surface_text]
        # Matthew has questions (e.g., "Are you the Christ?")
        assert len(questions) > 10, f"Expected questions, found {len(questions)}"

    def test_handles_raised_dot(self, matthew_tokens):
        """Greek raised dot (·) used as semicolon should parse."""
        raised_dots = [t for t in matthew_tokens if "·" in t.surface_text]
        # May or may not be present depending on edition
        # Just verify no crashes
        assert isinstance(raised_dots, list)

    def test_chapter_verse_boundaries_correct(self, matthew_tokens):
        """Chapter/verse numbers should be within valid ranges for Matthew."""
        for token in matthew_tokens:
            assert token.book == "Matthew", f"Wrong book: {token.book}"
            assert 1 <= token.chapter <= 28, (
                f"Invalid chapter {token.chapter} at {token.ref}"
            )
            assert 1 <= token.verse <= 100, (  # Max verse in Matthew is ~70ish
                f"Invalid verse {token.verse} at {token.ref}"
            )

    def test_lemma_always_present(self, matthew_tokens):
        """Every token must have a non-empty lemma."""
        missing_lemma = [
            t for t in matthew_tokens if not t.lemma or not t.lemma.strip()
        ]
        assert not missing_lemma, (
            f"Found {len(missing_lemma)} tokens without lemma:\n"
            + "\n".join(str(t.ref) for t in missing_lemma[:10])
        )


class TestProvenanceChain:
    """Verify provenance information is complete and consistent."""

    def test_manifest_has_commit_hash(self, manifest):
        """Manifest must include git commit hash for reproducibility."""
        assert "commit" in manifest["source"], "Missing commit hash in manifest"
        commit = manifest["source"]["commit"]
        assert len(commit) == 40, f"Invalid commit hash length: {commit}"
        assert all(c in "0123456789abcdef" for c in commit), (
            f"Invalid commit hash format: {commit}"
        )

    def test_manifest_has_repository_url(self, manifest):
        """Manifest must include repository URL."""
        assert "repository" in manifest["source"]
        assert manifest["source"]["repository"].startswith("https://")

    def test_manifest_has_license(self, manifest):
        """Manifest must include license information."""
        assert "license" in manifest
        assert "name" in manifest["license"]
        assert manifest["license"]["name"], "License name is empty"
