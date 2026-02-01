"""Pipeline orchestration for translate_passage vertical slice."""

from redletters.pipeline.schemas import (
    TranslateRequest,
    TranslateResponse,
    GateResponsePayload,
    ClaimResult,
    ConfidenceResult,
    VariantDisplay,
    ProvenanceInfo,
    ReceiptSummary,
)
from redletters.pipeline.orchestrator import translate_passage
from redletters.pipeline.translator import (
    Translator,
    FakeTranslator,
    LiteralTranslator,
    FluentTranslator,
    RealTranslator,
    get_translator,
)

__all__ = [
    "TranslateRequest",
    "TranslateResponse",
    "GateResponsePayload",
    "ClaimResult",
    "ConfidenceResult",
    "VariantDisplay",
    "ProvenanceInfo",
    "ReceiptSummary",
    "translate_passage",
    "Translator",
    "FakeTranslator",
    "LiteralTranslator",
    "FluentTranslator",
    "RealTranslator",
    "get_translator",
]
