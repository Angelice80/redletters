"""Lexicon provider protocol and implementations.

Sprint 10: License-aware gloss lookup with provenance tracking.

Provides:
- LexiconProvider: Protocol for gloss lookup
- BasicGlossProvider: Wraps existing BASIC_GLOSSES dictionary
- normalize_greek: Shared utility for accent stripping
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Protocol


def normalize_greek(text: str) -> str:
    """Normalize Greek text for dictionary lookup.

    Strips accents, breathing marks, and other diacriticals for
    consistent lookup in gloss dictionaries.

    Args:
        text: Greek text with diacriticals

    Returns:
        Normalized text without diacriticals
    """
    # Normalize to NFD to separate base chars from diacritics
    nfd = unicodedata.normalize("NFD", text)

    # Remove diacritical marks (category Mn = Mark, nonspacing)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")

    # Normalize back to NFC
    return unicodedata.normalize("NFC", stripped)


@dataclass
class GlossResult:
    """Result from lexicon lookup.

    Contains the gloss with provenance and alternatives.
    """

    gloss: str
    """English translation."""

    source: str
    """Provider source_id for provenance tracking."""

    confidence: float
    """0.0-1.0: How confident in this gloss being correct."""

    alternatives: list[str] = field(default_factory=list)
    """Other possible glosses (semantic range)."""

    def to_dict(self) -> dict:
        """Serialize for JSON output."""
        return {
            "gloss": self.gloss,
            "source": self.source,
            "confidence": round(self.confidence, 3),
            "alternatives": self.alternatives,
        }


class LexiconProvider(Protocol):
    """Abstract interface for gloss lookup.

    Implementations must provide source_id and license_info for
    provenance tracking, and a lookup method for gloss retrieval.
    """

    @property
    def source_id(self) -> str:
        """Unique identifier for provenance tracking."""
        ...

    @property
    def license_info(self) -> str:
        """License/attribution string."""
        ...

    def lookup(self, key: str) -> GlossResult | None:
        """Lookup gloss by normalized token or lemma.

        Args:
            key: Greek text (normalized or with diacriticals)

        Returns:
            GlossResult if found, None if not found (caller should try fallback)
        """
        ...


# Basic glosses from existing LiteralTranslator (reproduced here for independence)
# These are CC0/Public Domain - no licensing issues
_BASIC_GLOSSES = {
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

# Build normalized lookup dictionary at module load time
_BASIC_GLOSSES_NORMALIZED: dict[str, str] = {
    normalize_greek(k): v for k, v in _BASIC_GLOSSES.items()
}

# Semantic range data for words with notable ambiguity
_SEMANTIC_RANGES: dict[str, list[str]] = {
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
    "ζωή": ["life", "way of life"],
    "θάνατος": ["death", "mortality"],
    "δόξα": ["glory", "honor", "brightness"],
    "δύναμις": ["power", "miracle", "ability"],
}


class BasicGlossProvider:
    """Open-license basic gloss provider using BASIC_GLOSSES dictionary.

    Explicitly labeled as 'basic_glosses' for provenance.
    CC0 / Public Domain - no licensing restrictions.
    """

    @property
    def source_id(self) -> str:
        """Unique identifier for provenance tracking."""
        return "basic_glosses"

    @property
    def license_info(self) -> str:
        """License/attribution string."""
        return "CC0 / Public Domain - Red Letters Project"

    def lookup(self, key: str) -> GlossResult | None:
        """Lookup gloss by token or lemma.

        Normalizes the key (strips accents) for lookup.

        Args:
            key: Greek text (with or without diacriticals)

        Returns:
            GlossResult if found, None otherwise
        """
        normalized = normalize_greek(key)

        if normalized not in _BASIC_GLOSSES_NORMALIZED:
            return None

        gloss = _BASIC_GLOSSES_NORMALIZED[normalized]

        # Check if this word has semantic range data
        alternatives = _SEMANTIC_RANGES.get(normalized, [])
        # Remove primary gloss from alternatives if present
        alternatives = [a for a in alternatives if a != gloss]

        # Confidence: 0.7 for basic glosses (general, may not capture nuance)
        # Higher confidence if word has no semantic range (single meaning)
        confidence = 0.8 if not alternatives else 0.7

        return GlossResult(
            gloss=gloss,
            source=self.source_id,
            confidence=confidence,
            alternatives=alternatives,
        )

    def has_semantic_range(self, key: str) -> bool:
        """Check if a word has notable semantic range.

        Args:
            key: Greek text

        Returns:
            True if word has multiple documented senses
        """
        normalized = normalize_greek(key)
        return normalized in _SEMANTIC_RANGES

    def get_semantic_range(self, key: str) -> list[str]:
        """Get full semantic range for a word.

        Args:
            key: Greek text

        Returns:
            List of possible meanings (empty if not found)
        """
        normalized = normalize_greek(key)
        return _SEMANTIC_RANGES.get(normalized, [])


class ChainedLexiconProvider:
    """Chains multiple lexicon providers with fallback.

    Tries each provider in order until one returns a result.
    Useful for combining BasicGlossProvider with future sources.
    """

    def __init__(self, providers: list[LexiconProvider]):
        """Initialize with ordered list of providers.

        Args:
            providers: List of providers to try in order
        """
        self._providers = providers

    @property
    def source_id(self) -> str:
        """Combined source ID."""
        return "chained:" + ",".join(p.source_id for p in self._providers)

    @property
    def license_info(self) -> str:
        """Combined license info."""
        return " | ".join(p.license_info for p in self._providers)

    def lookup(self, key: str) -> GlossResult | None:
        """Lookup gloss trying each provider in order.

        Args:
            key: Greek text

        Returns:
            First successful GlossResult, or None if all fail
        """
        for provider in self._providers:
            result = provider.lookup(key)
            if result is not None:
                return result
        return None

    def lookup_all(self, key: str) -> list[GlossResult]:
        """Lookup gloss from all providers that have the word.

        Args:
            key: Greek text

        Returns:
            List of GlossResults from all providers
        """
        results = []
        for provider in self._providers:
            result = provider.lookup(key)
            if result is not None:
                results.append(result)
        return results


def get_default_provider() -> BasicGlossProvider:
    """Get the default lexicon provider.

    Returns:
        BasicGlossProvider instance
    """
    return BasicGlossProvider()
