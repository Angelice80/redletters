"""Translator interface and implementations.

Provides a Protocol for translators and implementations:
- FakeTranslator: Deterministic output for testing
- LiteralTranslator: Token-level gloss from real data (Sprint 3)
- RealTranslator: LLM-backed translation (future)

Per ADR-009: Readable mode restricts claim types to TYPE0-4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


# Basic Greek-English gloss dictionary for common NT words
# Used by LiteralTranslator when lexicon data not available
BASIC_GLOSSES = {
    # Common nouns
    "θεός": "God",
    "κύριος": "Lord",
    "Ἰησοῦς": "Jesus",
    "Χριστός": "Christ",
    "πνεῦμα": "spirit",
    "λόγος": "word",
    "ἄνθρωπος": "man",
    "υἱός": "son",
    "πατήρ": "father",
    "μήτηρ": "mother",
    "ἀδελφός": "brother",
    "γυνή": "woman",
    "κόσμος": "world",
    "οὐρανός": "heaven",
    "γῆ": "earth",
    "ζωή": "life",
    "θάνατος": "death",
    "ἁμαρτία": "sin",
    "νόμος": "law",
    "χάρις": "grace",
    "πίστις": "faith",
    "ἀγάπη": "love",
    "ἐλπίς": "hope",
    "δόξα": "glory",
    "δύναμις": "power",
    "ἔργον": "work",
    "ἡμέρα": "day",
    "ὥρα": "hour",
    "καιρός": "time",
    "αἰών": "age",
    "βασιλεία": "kingdom",
    "ἐκκλησία": "church",
    "ἀλήθεια": "truth",
    "ὁδός": "way",
    "φῶς": "light",
    "σκοτία": "darkness",
    "εἰρήνη": "peace",
    "χαρά": "joy",
    "σάρξ": "flesh",
    "σῶμα": "body",
    "αἷμα": "blood",
    "καρδία": "heart",
    "ψυχή": "soul",
    "ὄνομα": "name",
    "λαός": "people",
    "ἔθνος": "nation",
    "πόλις": "city",
    "οἶκος": "house",
    "ναός": "temple",
    "ἱερόν": "sanctuary",
    "θρόνος": "throne",
    "κρίσις": "judgment",
    "διδάσκαλος": "teacher",
    "μαθητής": "disciple",
    "ἀπόστολος": "apostle",
    "προφήτης": "prophet",
    "ἄγγελος": "angel",
    "διάβολος": "devil",
    "ἐχθρός": "enemy",
    "φίλος": "friend",
    "δοῦλος": "servant",
    "ἀρχιερεύς": "high priest",
    "βασιλεύς": "king",
    # Common verbs
    "εἰμί": "be",
    "λέγω": "say",
    "ποιέω": "do",
    "ἔρχομαι": "come",
    "ἔχω": "have",
    "γίνομαι": "become",
    "δίδωμι": "give",
    "λαμβάνω": "receive",
    "ἀκούω": "hear",
    "ὁράω": "see",
    "γινώσκω": "know",
    "οἶδα": "know",
    "πιστεύω": "believe",
    "ἀγαπάω": "love",
    "θέλω": "will",
    "δύναμαι": "be able",
    "δεῖ": "it is necessary",
    "ζάω": "live",
    "ἀποθνῄσκω": "die",
    "ἐγείρω": "raise",
    "σῴζω": "save",
    "κρίνω": "judge",
    "ἀφίημι": "forgive",
    "βαπτίζω": "baptize",
    "διδάσκω": "teach",
    "κηρύσσω": "proclaim",
    "μαρτυρέω": "witness",
    "ἁμαρτάνω": "sin",
    "μετανοέω": "repent",
    "ζητέω": "seek",
    "εὑρίσκω": "find",
    "φοβέω": "fear",
    "χαίρω": "rejoice",
    "πορεύομαι": "go",
    "ἀποστέλλω": "send",
    "καλέω": "call",
    "γράφω": "write",
    "ἀναγινώσκω": "read",
    "εὐαγγελίζω": "evangelize",
    # Pronouns and particles
    "ἐγώ": "I",
    "σύ": "you",
    "αὐτός": "he/she/it",
    "οὗτος": "this",
    "ἐκεῖνος": "that",
    "ὅς": "who/which",
    "τίς": "who?",
    "τις": "someone",
    "πᾶς": "all/every",
    "ὅλος": "whole",
    "ἄλλος": "other",
    "ἕκαστος": "each",
    "οὐδείς": "no one",
    "μηδείς": "no one",
    # Prepositions
    "ἐν": "in",
    "εἰς": "into",
    "ἐκ": "out of",
    "ἀπό": "from",
    "πρός": "to/toward",
    "διά": "through",
    "ὑπό": "under/by",
    "ὑπέρ": "over/for",
    "μετά": "with/after",
    "παρά": "beside",
    "περί": "about",
    "κατά": "according to",
    "ἐπί": "upon",
    "σύν": "with",
    # Conjunctions and adverbs
    "καί": "and",
    "δέ": "but/and",
    "γάρ": "for",
    "ἀλλά": "but",
    "οὖν": "therefore",
    "ὅτι": "that/because",
    "ἵνα": "in order that",
    "εἰ": "if",
    "ἐάν": "if",
    "ὥστε": "so that",
    "οὐ": "not",
    "μή": "not",
    "νῦν": "now",
    "τότε": "then",
    "πάλιν": "again",
    "ἔτι": "still",
    "ἤδη": "already",
    "πώποτε": "ever",
    "οὐδέποτε": "never",
    # Articles
    "ὁ": "the",
    "ἡ": "the",
    "τό": "the",
    # Adjectives
    "ἅγιος": "holy",
    "ἀγαθός": "good",
    "κακός": "bad",
    "μέγας": "great",
    "μικρός": "small",
    "νέος": "new",
    "παλαιός": "old",
    "πρῶτος": "first",
    "ἔσχατος": "last",
    "δίκαιος": "righteous",
    "πιστός": "faithful",
    "ἀληθής": "true",
    "μόνος": "only",
    "μονογενής": "only-begotten",
    "αἰώνιος": "eternal",
}


def _normalize_for_lookup(text: str) -> str:
    """Normalize Greek text for dictionary lookup (strips accents)."""
    import unicodedata

    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", stripped)


# Build normalized lookup dictionary at module load time
BASIC_GLOSSES_NORMALIZED = {
    _normalize_for_lookup(k): v for k, v in BASIC_GLOSSES.items()
}


@dataclass
class TranslationContext:
    """Context provided to translator."""

    reference: str
    """Scripture reference."""

    mode: str
    """readable or traceable."""

    tokens: list[dict]
    """Token data with morphology."""

    variants: list[dict]
    """Variant data for the passage."""

    session_id: str
    """Session for acknowledgement tracking."""

    options: dict = field(default_factory=dict)
    """Additional options."""


@dataclass
class TranslationClaim:
    """A claim produced by the translator."""

    content: str
    """The claim text."""

    claim_type_hint: int | None = None
    """Optional hint for claim type (TYPE0-7)."""

    dependencies: list[dict] = field(default_factory=list)
    """Declared dependencies."""


@dataclass
class TranslationDraft:
    """Draft translation output from translator."""

    translation_text: str
    """The translated text."""

    claims: list[TranslationClaim]
    """Claims made during translation."""

    notes: list[str] = field(default_factory=list)
    """Translator notes/explanations."""

    style: str = "natural"
    """Translation style used."""


class Translator(Protocol):
    """Protocol for translation backends.

    Implementations:
    - FakeTranslator: Deterministic output for testing
    - RealTranslator: LLM-backed translation (future)
    """

    def translate(
        self,
        spine_text: str,
        context: TranslationContext,
    ) -> TranslationDraft:
        """Translate Greek text to English.

        Args:
            spine_text: SBLGNT Greek text
            context: Translation context with tokens, variants, etc.

        Returns:
            TranslationDraft with text and claims
        """
        ...


class FakeTranslator:
    """Deterministic translator for testing.

    Produces predictable output covering multiple claim types
    for enforcement testing. Does not require LLM.
    """

    def __init__(self, scenario: str = "default"):
        """Initialize with scenario selection.

        Scenarios:
        - default: Mixed claims (TYPE0-4)
        - high_inference: TYPE5-7 claims (test escalation)
        - epistemic_pressure: Claims with pressure language
        - clean: TYPE0-1 only (always passes readable mode)
        """
        self.scenario = scenario

    def translate(
        self,
        spine_text: str,
        context: TranslationContext,
    ) -> TranslationDraft:
        """Generate deterministic translation for testing."""
        if self.scenario == "high_inference":
            return self._high_inference_scenario(spine_text, context)
        elif self.scenario == "epistemic_pressure":
            return self._epistemic_pressure_scenario(spine_text, context)
        elif self.scenario == "clean":
            return self._clean_scenario(spine_text, context)
        else:
            return self._default_scenario(spine_text, context)

    def _default_scenario(
        self, spine_text: str, context: TranslationContext
    ) -> TranslationDraft:
        """Default scenario with mixed claim types."""
        # Generate simple gloss-based translation
        words = spine_text.split()
        translation = self._basic_gloss(context.tokens)

        claims = [
            # TYPE0: Descriptive (always allowed)
            TranslationClaim(
                content=f"The word '{words[0] if words else 'text'}' is a noun.",
                claim_type_hint=0,
                dependencies=[],
            ),
            # TYPE1: Lexical range (allowed with range display)
            TranslationClaim(
                content="The term can mean 'life', 'living being', or 'soul'.",
                claim_type_hint=1,
                dependencies=[
                    {
                        "dep_type": "lexicon",
                        "lemma": "ψυχή",
                        "sense_chosen": "life",
                        "sense_range": ["life", "soul", "living being"],
                    }
                ],
            ),
            # TYPE2: Grammatical (needs hypothesis markers in readable)
            TranslationClaim(
                content="This genitive likely indicates possession.",
                claim_type_hint=2,
                dependencies=[
                    {
                        "dep_type": "grammar",
                        "token_ref": f"{context.reference}:1",
                        "parse_choice": "possessive genitive",
                        "alternatives": ["subjective genitive", "objective genitive"],
                    }
                ],
            ),
            # TYPE3: Contextual (needs hypothesis markers in readable)
            TranslationClaim(
                content="In this context, the phrase probably refers to eternal life.",
                claim_type_hint=3,
                dependencies=[
                    {
                        "dep_type": "context",
                        "assumption": "Johannine usage of 'life'",
                        "evidence": "John's Gospel consistently uses life as eschatological",
                    }
                ],
            ),
        ]

        # Add variant dependency if variants present
        if context.variants:
            claims.append(
                TranslationClaim(
                    content="The translation follows the SBLGNT reading.",
                    claim_type_hint=0,
                    dependencies=[
                        {
                            "dep_type": "variant",
                            "variant_unit_ref": context.variants[0].get("ref", ""),
                            "reading_chosen": 0,
                            "rationale": "Following SBLGNT as canonical spine",
                        }
                    ],
                )
            )

        return TranslationDraft(
            translation_text=translation,
            claims=claims,
            notes=["FakeTranslator default scenario"],
            style="natural",
        )

    def _high_inference_scenario(
        self, spine_text: str, context: TranslationContext
    ) -> TranslationDraft:
        """Scenario with high-inference claims that require escalation."""
        translation = self._basic_gloss(context.tokens)

        claims = [
            # TYPE5: Moral (forbidden in readable)
            TranslationClaim(
                content="Christians should follow this command today.",
                claim_type_hint=5,
                dependencies=[
                    {
                        "dep_type": "hermeneutic",
                        "assumption": "Commands are universally applicable",
                        "evidence": "General Protestant hermeneutics",
                    }
                ],
            ),
            # TYPE6: Metaphysical (forbidden in readable)
            TranslationClaim(
                content="This proves the eternal nature of God.",
                claim_type_hint=6,
                dependencies=[
                    {
                        "dep_type": "tradition",
                        "assumption": "Classical theism",
                        "evidence": "Nicene theology",
                    }
                ],
            ),
            # TYPE7: Harmonized (forbidden in readable)
            TranslationClaim(
                content="When read with Romans 8, this teaches divine sovereignty.",
                claim_type_hint=7,
                dependencies=[
                    {
                        "dep_type": "cross_ref",
                        "ref": "Romans 8:28-30",
                        "choice": "Harmony with predestination",
                    }
                ],
            ),
        ]

        return TranslationDraft(
            translation_text=translation,
            claims=claims,
            notes=["FakeTranslator high-inference scenario (expect escalation gates)"],
            style="theological",
        )

    def _epistemic_pressure_scenario(
        self, spine_text: str, context: TranslationContext
    ) -> TranslationDraft:
        """Scenario with epistemic pressure language."""
        translation = self._basic_gloss(context.tokens)

        claims = [
            # Pressure: "clearly"
            TranslationClaim(
                content="Clearly, this text teaches the resurrection.",
                claim_type_hint=4,
                dependencies=[],
            ),
            # Pressure: "the text says"
            TranslationClaim(
                content="The text says that Jesus is Lord.",
                claim_type_hint=3,
                dependencies=[],
            ),
            # Pressure: "obviously"
            TranslationClaim(
                content="Obviously, the author meant this metaphorically.",
                claim_type_hint=3,
                dependencies=[],
            ),
            # Pressure: "undoubtedly"
            TranslationClaim(
                content="Undoubtedly, this is the correct interpretation.",
                claim_type_hint=4,
                dependencies=[],
            ),
        ]

        return TranslationDraft(
            translation_text=translation,
            claims=claims,
            notes=["FakeTranslator epistemic pressure scenario (expect warnings)"],
            style="assertive",
        )

    def _clean_scenario(
        self, spine_text: str, context: TranslationContext
    ) -> TranslationDraft:
        """Clean scenario with only TYPE0-1 claims."""
        translation = self._basic_gloss(context.tokens)

        claims = [
            TranslationClaim(
                content="The verb is in the present tense.",
                claim_type_hint=0,
                dependencies=[],
            ),
            TranslationClaim(
                content="The noun is nominative singular.",
                claim_type_hint=0,
                dependencies=[],
            ),
            TranslationClaim(
                content="The term can mean 'word', 'reason', or 'message'.",
                claim_type_hint=1,
                dependencies=[
                    {
                        "dep_type": "lexicon",
                        "lemma": "λόγος",
                        "sense_chosen": "word",
                        "sense_range": ["word", "reason", "message", "account"],
                    }
                ],
            ),
        ]

        return TranslationDraft(
            translation_text=translation,
            claims=claims,
            notes=["FakeTranslator clean scenario (TYPE0-1 only)"],
            style="descriptive",
        )

    def _basic_gloss(self, tokens: list[dict]) -> str:
        """Generate basic gloss from tokens."""
        if not tokens:
            return "[No tokens available]"

        glosses = []
        for token in tokens:
            # Use lemma as a simple gloss (real translator would do much more)
            lemma = token.get("lemma", token.get("surface", "?"))
            glosses.append(f"[{lemma}]")

        return " ".join(glosses)


class RealTranslator:
    """LLM-backed translator (stub for future implementation).

    This will integrate with whatever LLM/engine job system exists
    in the repo. For now, it delegates to FakeTranslator.
    """

    def __init__(self, enabled: bool = False):
        """Initialize translator.

        Args:
            enabled: If False, delegates to FakeTranslator
        """
        self.enabled = enabled
        self._fallback = FakeTranslator()

    def translate(
        self,
        spine_text: str,
        context: TranslationContext,
    ) -> TranslationDraft:
        """Translate using LLM or fallback to fake."""
        if not self.enabled:
            return self._fallback.translate(spine_text, context)

        # TODO: Implement actual LLM translation
        # This would:
        # 1. Prepare prompt with spine_text, context.tokens, context.variants
        # 2. Call LLM API or engine job system
        # 3. Parse response into TranslationDraft
        # 4. Extract claims and dependencies
        raise NotImplementedError("RealTranslator not yet implemented")


class LiteralTranslator:
    """Deterministic, non-LLM translator producing token-level glosses.

    Sprint 3: Provides usable output from real Greek text without AI inference.

    Features:
    - Token-level gloss with basic syntactic assembly
    - Respects readable mode constraints (no TYPE5+ claims)
    - Uses hedging language where inferential
    - Includes source provenance in output

    Output format:
    - Each token gets a gloss in [brackets]
    - Known words use dictionary glosses
    - Unknown words show lemma or surface form
    - Basic word order is Greek order (no rearrangement)
    """

    def __init__(
        self,
        source_id: str = "",
        source_license: str = "",
    ):
        """Initialize literal translator.

        Args:
            source_id: Source pack ID for provenance
            source_license: License string for provenance
        """
        self.source_id = source_id
        self.source_license = source_license

    def translate(
        self,
        spine_text: str,
        context: TranslationContext,
    ) -> TranslationDraft:
        """Translate Greek text to English using token-level glossing.

        Args:
            spine_text: Greek text (space-separated tokens)
            context: Translation context with tokens, mode, etc.

        Returns:
            TranslationDraft with literal glosses and claims
        """
        # Generate literal translation
        translation = self._literal_gloss(spine_text, context.tokens)

        # Build claims appropriate for mode
        claims = self._build_claims(context)

        # Build notes with provenance
        notes = self._build_notes(context)

        return TranslationDraft(
            translation_text=translation,
            claims=claims,
            notes=notes,
            style="literal",
        )

    def _literal_gloss(self, spine_text: str, tokens: list[dict]) -> str:
        """Generate literal gloss from tokens.

        Args:
            spine_text: Greek text
            tokens: Token data with lemmas

        Returns:
            English gloss string
        """
        if not tokens:
            # Fall back to word-by-word from spine text
            words = spine_text.split()
            glosses = []
            for word in words:
                # Try to find in basic glosses
                normalized = self._normalize_greek(word)
                gloss = BASIC_GLOSSES.get(normalized, word)
                glosses.append(f"[{gloss}]")
            return " ".join(glosses)

        glosses = []
        for token in tokens:
            gloss = self._gloss_token(token)
            glosses.append(gloss)

        return " ".join(glosses)

    def _gloss_token(self, token: dict) -> str:
        """Generate gloss for a single token.

        Args:
            token: Token dictionary with lemma, surface, pos, etc.

        Returns:
            Glossed token string like "[word]"
        """
        lemma = token.get("lemma", "")
        surface = token.get("surface_text", token.get("surface", token.get("word", "")))

        # Normalize lemma for lookup
        normalized_lemma = self._normalize_greek(lemma)

        # Try basic gloss dictionary (using normalized keys)
        if normalized_lemma in BASIC_GLOSSES_NORMALIZED:
            gloss = BASIC_GLOSSES_NORMALIZED[normalized_lemma]
        elif lemma:
            # Use lemma as gloss
            gloss = lemma
        else:
            # Use surface form
            gloss = surface

        # Add morphological markers for clarity
        pos = token.get("pos", "")
        parse = token.get("parse_code", token.get("morph", ""))

        # Check if it's a proper noun (keep Greek)
        if pos == "N" and parse and len(parse) >= 1:
            # Proper nouns might want to keep the Greek name
            if self._is_proper_noun(token):
                gloss = f"{gloss}/{surface}"

        return f"[{gloss}]"

    def _normalize_greek(self, text: str) -> str:
        """Normalize Greek text for dictionary lookup.

        Removes accents and breathing marks for lookup.
        """
        import unicodedata

        # Normalize to NFD to separate base chars from diacritics
        nfd = unicodedata.normalize("NFD", text)

        # Remove diacritical marks (category M)
        stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")

        # Normalize back to NFC
        return unicodedata.normalize("NFC", stripped)

    def _is_proper_noun(self, token: dict) -> bool:
        """Check if token is a proper noun."""
        pos = token.get("pos", "")
        lemma = token.get("lemma", "")

        # Check POS code
        if pos in ("NP", "PN"):
            return True

        # Check if lemma starts with uppercase (Greek proper nouns)
        if lemma and lemma[0].isupper():
            return True

        return False

    def _build_claims(self, context: TranslationContext) -> list[TranslationClaim]:
        """Build claims appropriate for the translation mode.

        Readable mode: TYPE0-4 only
        Traceable mode: All types allowed

        Args:
            context: Translation context

        Returns:
            List of TranslationClaims
        """
        claims = []

        # TYPE0: Descriptive (always allowed) - source acknowledgement
        claims.append(
            TranslationClaim(
                content=f"Translation based on Greek text from {self.source_id or 'unknown source'}.",
                claim_type_hint=0,
                dependencies=[],
            )
        )

        # TYPE1: Lexical range (for ambiguous terms)
        if context.tokens:
            for token in context.tokens[:3]:  # Limit to first few tokens
                lemma = token.get("lemma", "")
                if lemma and self._has_semantic_range(lemma):
                    senses = self._get_sense_range(lemma)
                    claims.append(
                        TranslationClaim(
                            content=f"'{lemma}' may mean: {', '.join(senses)}.",
                            claim_type_hint=1,
                            dependencies=[
                                {
                                    "dep_type": "lexicon",
                                    "lemma": lemma,
                                    "sense_chosen": senses[0] if senses else "",
                                    "sense_range": senses,
                                }
                            ],
                        )
                    )
                    break  # One lexical claim is enough

        # TYPE2: Grammatical (if there's ambiguity)
        if context.tokens:
            for token in context.tokens:
                parse = token.get("parse_code", "")
                if parse and self._has_grammar_ambiguity(token):
                    claims.append(
                        TranslationClaim(
                            content=f"The grammatical form likely indicates {self._describe_grammar(token)}.",
                            claim_type_hint=2,
                            dependencies=[
                                {
                                    "dep_type": "grammar",
                                    "token_ref": token.get("ref", ""),
                                    "parse_choice": parse,
                                    "alternatives": [],
                                    "rationale": "Based on morphological analysis",
                                }
                            ],
                        )
                    )
                    break  # One grammar claim is enough

        # Add provenance claim
        if self.source_license:
            claims.append(
                TranslationClaim(
                    content=f"Source text licensed under {self.source_license}.",
                    claim_type_hint=0,
                    dependencies=[],
                )
            )

        # Handle variant dependencies if present
        if context.variants:
            claims.append(
                TranslationClaim(
                    content="Translation follows the canonical spine reading.",
                    claim_type_hint=0,
                    dependencies=[
                        {
                            "dep_type": "variant",
                            "variant_unit_ref": context.variants[0].get(
                                "ref", context.reference
                            ),
                            "reading_chosen": 0,
                            "rationale": "SBLGNT canonical reading",
                        }
                    ],
                )
            )

        return claims

    def _has_semantic_range(self, lemma: str) -> bool:
        """Check if a lemma has notable semantic range."""
        # Words known to have significant semantic range
        broad_terms = {
            "λόγος",  # word/reason/speech
            "πίστις",  # faith/faithfulness
            "σάρξ",  # flesh/body
            "πνεῦμα",  # spirit/breath/wind
            "ψυχή",  # soul/life
            "δικαιοσύνη",  # righteousness/justice
            "νόμος",  # law/principle
            "κόσμος",  # world/order
            "ἀγάπη",  # love
            "χάρις",  # grace/favor
        }
        normalized = self._normalize_greek(lemma)
        return normalized in broad_terms

    def _get_sense_range(self, lemma: str) -> list[str]:
        """Get semantic range for a lemma."""
        ranges = {
            "λόγος": ["word", "speech", "reason", "message"],
            "πίστις": ["faith", "faithfulness", "trust", "belief"],
            "σάρξ": ["flesh", "body", "human nature"],
            "πνεῦμα": ["spirit", "Spirit", "breath", "wind"],
            "ψυχή": ["soul", "life", "self"],
            "δικαιοσύνη": ["righteousness", "justice", "justification"],
            "νόμος": ["law", "principle", "Torah"],
            "κόσμος": ["world", "creation", "order"],
            "ἀγάπη": ["love", "charity"],
            "χάρις": ["grace", "favor", "gift"],
        }
        normalized = self._normalize_greek(lemma)
        return ranges.get(normalized, [BASIC_GLOSSES.get(normalized, lemma)])

    def _has_grammar_ambiguity(self, token: dict) -> bool:
        """Check if token has grammatical ambiguity."""
        parse = token.get("parse_code", "")

        # Genitive case is often ambiguous
        if parse and len(parse) >= 5 and parse[4] == "G":
            return True

        # Middle/passive voice ambiguity
        if parse and len(parse) >= 3 and parse[2] == "E":
            return True

        return False

    def _describe_grammar(self, token: dict) -> str:
        """Generate grammar description for a token."""
        parse = token.get("parse_code", "")

        if not parse:
            return "unknown grammatical function"

        # Simple descriptions for common cases
        if len(parse) >= 5:
            case = parse[4] if len(parse) > 4 else ""
            if case == "G":
                return "a genitive relationship (possession, source, or description)"
            elif case == "D":
                return "an indirect object or instrumental function"
            elif case == "A":
                return "a direct object"
            elif case == "N":
                return "the subject or predicate"

        if len(parse) >= 3:
            voice = parse[2] if len(parse) > 2 else ""
            if voice == "E":
                return "either middle or passive voice (context determines)"

        return "standard grammatical function"

    def _build_notes(self, context: TranslationContext) -> list[str]:
        """Build translator notes with provenance."""
        notes = [
            "LiteralTranslator: deterministic token-level gloss",
        ]

        if self.source_id:
            notes.append(f"Source: {self.source_id}")

        if self.source_license:
            notes.append(f"License: {self.source_license}")

        notes.append(f"Mode: {context.mode}")

        if context.options.get("scenario"):
            notes.append(f"Scenario: {context.options['scenario']}")

        return notes


@dataclass
class FluentTranslationDraft(TranslationDraft):
    """Draft translation with transform log for FluentTranslator."""

    transform_log: list[str] = field(default_factory=list)
    """Log of all rules applied during transformation."""


class FluentTranslator:
    """Deterministic fluent translator for readable output.

    Sprint 5: Transforms literal gloss into more natural English
    using deterministic heuristics (no LLM, no network).

    Features:
    - Article handling: Drop Greek articles unless contextually needed
    - Postpositive reordering: Move δέ/γάρ/οὖν to sentence start
    - Genitive smoothing: "of X" → "X's" where natural
    - Bracket removal: Clean up literal translator's brackets
    - Transform log: Track all applied rules for traceability

    ADR-009 Compliance:
    - In readable mode, all claims are TYPE0-4
    - TYPE5+ claims are blocked entirely
    - TYPE2/TYPE3 claims get hypothesis markers

    Output is deterministic: same input always produces same output.
    """

    # Transform rules as (name, pattern, replacement)
    # Applied in order - order matters!
    FLUENT_RULES = [
        # Postpositive particles - move to sentence start
        ("POSTPOSITIVE_DE", r"(\[[^\]]+\]) \[but\]", r"But \1"),
        ("POSTPOSITIVE_GAR", r"(\[[^\]]+\]) \[for\]", r"For \1"),
        ("POSTPOSITIVE_OUN", r"(\[[^\]]+\]) \[therefore\]", r"Therefore \1"),
        # Article handling - drop leading articles in most cases
        ("ARTICLE_DROP_LEADING", r"^\[the\] ", ""),
        (
            "ARTICLE_DROP_AFTER_PREP",
            r"(\[(?:in|into|to|from|with|by)\]) \[the\]",
            r"\1",
        ),
        # Genitive smoothing - "of X" patterns
        ("GENITIVE_POSSESSIVE", r"\[of\] \[([^\]]+)\]'?s?", r"[\1's]"),
        # Bracket cleanup - remove brackets from final output
        ("BRACKET_CLEAN", r"\[([^\]]+)\]", r"\1"),
        # Capitalize first letter
        ("CAPITALIZE_FIRST", r"^([a-z])", lambda m: m.group(1).upper()),
    ]

    def __init__(
        self,
        source_id: str = "",
        source_license: str = "",
    ):
        """Initialize fluent translator.

        Args:
            source_id: Source pack ID for provenance
            source_license: License string for provenance
        """
        self.source_id = source_id
        self.source_license = source_license
        # Use LiteralTranslator as base for gloss generation
        self._literal = LiteralTranslator(
            source_id=source_id,
            source_license=source_license,
        )

    def translate(
        self,
        spine_text: str,
        context: TranslationContext,
    ) -> FluentTranslationDraft:
        """Translate Greek text to fluent English.

        First generates literal gloss, then applies fluent transformations.

        Args:
            spine_text: Greek text (space-separated tokens)
            context: Translation context with tokens, mode, etc.

        Returns:
            FluentTranslationDraft with fluent text and transform log
        """
        import re

        # Step 1: Get literal translation as base
        literal_draft = self._literal.translate(spine_text, context)
        literal_text = literal_draft.translation_text

        # Step 2: Apply fluent transformations
        fluent_text = literal_text
        transform_log: list[str] = []

        for rule_name, pattern, replacement in self.FLUENT_RULES:
            original = fluent_text
            if callable(replacement):
                fluent_text = re.sub(pattern, replacement, fluent_text)
            else:
                fluent_text = re.sub(pattern, replacement, fluent_text)

            if fluent_text != original:
                transform_log.append(f"{rule_name}: applied")

        # Step 3: Build claims appropriate for readable mode
        claims = self._build_fluent_claims(context, literal_draft.claims, transform_log)

        # Step 4: Build notes
        notes = [
            "FluentTranslator: deterministic fluent transformation",
            f"Source: {self.source_id or 'unknown'}",
            f"Mode: {context.mode}",
            f"Transforms applied: {len(transform_log)}",
        ]

        return FluentTranslationDraft(
            translation_text=fluent_text,
            claims=claims,
            notes=notes,
            style="fluent",
            transform_log=transform_log,
        )

    def _build_fluent_claims(
        self,
        context: TranslationContext,
        literal_claims: list[TranslationClaim],
        transform_log: list[str],
    ) -> list[TranslationClaim]:
        """Build claims for fluent translation.

        ADR-009: In readable mode, only TYPE0-4 claims are allowed.
        TYPE5+ claims are blocked entirely.

        Args:
            context: Translation context
            literal_claims: Claims from literal translator
            transform_log: Transform rules applied

        Returns:
            List of TranslationClaims appropriate for mode
        """
        claims: list[TranslationClaim] = []

        # TYPE0: Descriptive - always allowed
        claims.append(
            TranslationClaim(
                content="Fluent translation derived from literal gloss using deterministic rules.",
                claim_type_hint=0,
                dependencies=[],
            )
        )

        # Add transform log as TYPE0 claim
        if transform_log:
            claims.append(
                TranslationClaim(
                    content=f"Applied transformations: {', '.join(transform_log)}.",
                    claim_type_hint=0,
                    dependencies=[],
                )
            )

        # Filter and carry forward literal claims
        for claim in literal_claims:
            # Only pass TYPE0-4 claims
            if claim.claim_type_hint is not None and claim.claim_type_hint <= 4:
                # Add hypothesis markers for TYPE2-4 in readable mode
                if context.mode == "readable" and claim.claim_type_hint >= 2:
                    # Ensure hedging language is present
                    content = claim.content
                    if not any(
                        marker in content.lower()
                        for marker in ["likely", "probably", "may", "might", "perhaps"]
                    ):
                        content = f"Likely: {content}"
                    claims.append(
                        TranslationClaim(
                            content=content,
                            claim_type_hint=claim.claim_type_hint,
                            dependencies=claim.dependencies,
                        )
                    )
                else:
                    claims.append(claim)
            elif claim.claim_type_hint is None:
                # Unknown type, treat conservatively as TYPE3
                claims.append(
                    TranslationClaim(
                        content=f"[Unclassified] {claim.content}",
                        claim_type_hint=3,
                        dependencies=claim.dependencies,
                    )
                )
            # TYPE5+ claims are silently dropped in readable mode per ADR-009

        # Add provenance claim
        if self.source_license:
            claims.append(
                TranslationClaim(
                    content=f"Source text licensed under {self.source_license}.",
                    claim_type_hint=0,
                    dependencies=[],
                )
            )

        return claims


def get_translator(
    translator_type: str = "fake",
    source_id: str = "",
    source_license: str = "",
    scenario: str = "default",
) -> Translator:
    """Factory function to get appropriate translator.

    Args:
        translator_type: "fake", "literal", "fluent", "traceable", or "real"
        source_id: Source pack ID (for literal/fluent/traceable translator)
        source_license: License string (for literal/fluent/traceable translator)
        scenario: Scenario for FakeTranslator

    Returns:
        Translator instance
    """
    if translator_type == "literal":
        return LiteralTranslator(
            source_id=source_id,
            source_license=source_license,
        )
    elif translator_type == "fluent":
        return FluentTranslator(
            source_id=source_id,
            source_license=source_license,
        )
    elif translator_type == "traceable":
        # Import here to avoid circular dependency
        from redletters.pipeline.traceable_translator import TraceableTranslator

        return TraceableTranslator(
            source_id=source_id,
            source_license=source_license,
        )
    elif translator_type == "real":
        return RealTranslator(enabled=True)
    else:
        return FakeTranslator(scenario=scenario)
