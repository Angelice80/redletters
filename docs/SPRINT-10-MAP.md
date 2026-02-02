# Sprint 10 MAP: Traceable Ledger Mode

**Goal**: Token-level evidence "receipt-grade" translation ledger with UI/CLI wiring
**Status**: PLANNING
**Dependencies**: Sprint 9 (complete), ADR-007..010 (intact)

---

## 1. Ledger Schema Design

### 1.1 VerseLedger (top-level per-verse structure)

```python
@dataclass
class VerseLedger:
    verse_id: str                          # Internal verse identifier
    normalized_ref: str                    # Human-readable reference (e.g., "John 1:18")
    tokens: list[TokenLedger]              # Ordered token-level analysis
    translation_segments: list[SegmentLedger]  # Optional phrase-level mappings
    provenance: LedgerProvenance           # Source attribution
```

### 1.2 TokenLedger (per-token analysis)

```python
@dataclass
class TokenLedger:
    position: int                          # 0-indexed token position in verse
    surface: str                           # Original Greek surface form (with accents)
    normalized: str                        # Accent-stripped for lookup
    lemma: str | None                      # Dictionary headword (if available)
    morph: str | None                      # Morphological parse code (if available)
    gloss: str                             # English gloss from lexicon
    gloss_source: str                      # Provenance of gloss (e.g., "basic_glosses", "morphgnt")
    notes: list[str]                       # Linguistic notes (elision, crasis, article handling)
    confidence: TokenConfidence            # Four-layer confidence per ADR-010
```

### 1.3 TokenConfidence (reuses ADR-010 layers)

```python
@dataclass
class TokenConfidence:
    textual: float                         # 0.0-1.0: Manuscript agreement for this token
    grammatical: float                     # 0.0-1.0: Parse ambiguity level
    lexical: float                         # 0.0-1.0: Semantic range breadth
    interpretive: float                    # 0.0-1.0: Inference distance (tied to ClaimType)
    explanations: dict[str, str]           # Human-readable explanations per layer
```

### 1.4 SegmentLedger (optional phrase alignment)

```python
@dataclass
class SegmentLedger:
    token_range: tuple[int, int]           # Start/end positions (inclusive)
    greek_phrase: str                      # Concatenated Greek tokens
    english_phrase: str                    # Translated segment
    alignment_type: str                    # "literal" | "reordered" | "smoothed"
    transformation_notes: list[str]        # Applied transformations
```

### 1.5 LedgerProvenance (source attribution)

```python
@dataclass
class LedgerProvenance:
    spine_source_id: str                   # Always SBLGNT per ADR-007
    comparative_sources_used: list[str]    # Pack IDs used in variant analysis
    evidence_class_summary: EvidenceClassSummary  # Counts by type from dossier
```

### 1.6 EvidenceClassSummary (from Sprint 9 dossier)

```python
@dataclass
class EvidenceClassSummary:
    manuscript_count: int                  # MANUSCRIPT type witnesses
    edition_count: int                     # EDITION type witnesses
    tradition_count: int                   # TRADITION type witnesses
    other_count: int                       # OTHER type witnesses
    # NOTE: These remain explicit per non-negotiables; no collapsed "support score"
```

### 1.7 Integration with TranslateResponse

```python
# Extend existing TranslateResponse
@dataclass
class TranslateResponse:
    # ... existing fields unchanged ...

    # NEW: Traceable mode only
    ledger: list[VerseLedger] | None       # Populated only when mode="traceable"
```

---

## 2. Lexicon Provider Strategy

### 2.1 LexiconProvider Protocol

```python
from typing import Protocol

class LexiconProvider(Protocol):
    """Abstract interface for gloss lookup."""

    @property
    def source_id(self) -> str:
        """Unique identifier for provenance tracking."""
        ...

    @property
    def license_info(self) -> str:
        """License/attribution string."""
        ...

    def lookup(self, key: str) -> GlossResult | None:
        """
        Lookup gloss by normalized token or lemma.
        Returns None if not found (caller should try fallback).
        """
        ...

@dataclass
class GlossResult:
    gloss: str                             # English translation
    source: str                            # Provider source_id
    confidence: float                      # 0.0-1.0: How confident in this gloss
    alternatives: list[str]                # Other possible glosses (semantic range)
```

### 2.2 BasicGlossProvider (Reuse Existing)

**Implementation**: Wrap `LiteralTranslator.BASIC_GLOSSES_NORMALIZED`

```python
class BasicGlossProvider:
    """
    Open-license basic gloss provider using existing BASIC_GLOSSES dictionary.
    Explicitly labeled as "basic_glosses" for provenance.
    """
    source_id = "basic_glosses"
    license_info = "CC0 / Public Domain - Red Letters Project"

    def lookup(self, key: str) -> GlossResult | None:
        # Use existing _normalize_greek() from LiteralTranslator
        normalized = normalize_greek(key)
        if normalized in BASIC_GLOSSES_NORMALIZED:
            return GlossResult(
                gloss=BASIC_GLOSSES_NORMALIZED[normalized],
                source=self.source_id,
                confidence=0.7,  # Basic glosses are general
                alternatives=[]
            )
        return None
```

### 2.3 MorphGNTLexiconProvider (Future Enhancement)

**Requirement**: Only if MorphGNT pack includes lemma→gloss mappings
**License**: Must be verified via installer/EULA mechanics (already handled)

```python
class MorphGNTLexiconProvider:
    """
    Lexicon provider using MorphGNT lemma data if available.
    License compliance handled by SourcePack installer.
    """
    source_id = "morphgnt"
    license_info = "MorphGNT License (see pack metadata)"

    def lookup(self, key: str) -> GlossResult | None:
        # Query installed MorphGNT pack for lemma glosses
        ...
```

### 2.4 Licensing Notes

| Provider | License Status | Handling |
|----------|---------------|----------|
| BasicGlossProvider | CC0/PD | Open use, no restrictions |
| MorphGNTLexiconProvider | MorphGNT terms | Via pack installer EULA |
| Future closed lexicons | TBD | Require explicit EULA acceptance |

**Non-Negotiable**: DO NOT pull in closed-license lexicons without installer/EULA flow.

---

## 3. TraceableTranslator Design

### 3.1 Translator Registration

```python
# Extend TranslatorType enum
class TranslatorType(str, Enum):
    LITERAL = "literal"
    FLUENT = "fluent"
    TRACEABLE = "traceable"  # NEW
    FAKE = "fake"
    REAL = "real"
```

### 3.2 TraceableTranslator Implementation

```python
class TraceableTranslator:
    """
    Produces fluent-ish English with complete token-level ledger.
    Deterministic output for reproducibility.
    """

    def __init__(self, lexicon_providers: list[LexiconProvider]):
        self.lexicon_providers = lexicon_providers
        self.literal_translator = LiteralTranslator()
        self.fluent_translator = FluentTranslator()

    def translate(
        self,
        tokens: list[GreekToken],
        mode: str,
        variant_context: VariantContext | None = None
    ) -> TraceableTranslationResult:
        """
        1. Build TokenLedger for each token
        2. Produce fluent translation using existing pipeline
        3. Generate SegmentLedger alignment
        4. Enforce mode constraints (TYPE5+ forbidden in readable)
        """
        ...
```

### 3.3 Mode Enforcement

| Mode | Allowed Claims | Ledger Output |
|------|---------------|---------------|
| readable | TYPE0-4 only | Not returned (None) |
| traceable | TYPE0-7 with full dependencies | Full VerseLedger |

**Non-Negotiable**: TYPE5+ claims NEVER appear in readable mode (per ADR-009)

### 3.4 Orchestrator Integration

```python
# In orchestrator.py - translate_passage()

if request.translator_type == "traceable":
    translator = TraceableTranslator(lexicon_providers)
    result = translator.translate(tokens, request.mode, variant_context)

    if request.mode == "traceable":
        response.ledger = result.ledger
    # else: ledger is None (readable mode)
```

---

## 4. UI Plan: Traceable View

### 4.1 Translate Screen Enhancement

**Location**: `gui/src/screens/Translate.tsx`

**New Component**: `LedgerPanel.tsx`

```tsx
interface LedgerPanelProps {
  ledger: VerseLedger;
  expanded: boolean;
  onToggle: () => void;
}

// Collapsible panel per verse when mode=traceable
const LedgerPanel: React.FC<LedgerPanelProps> = ({ ledger, expanded, onToggle }) => {
  return (
    <Collapsible open={expanded} onOpenChange={onToggle}>
      <CollapsibleTrigger>
        Ledger: {ledger.normalized_ref}
      </CollapsibleTrigger>
      <CollapsibleContent>
        <TokenTable tokens={ledger.tokens} />
        <ProvenanceBadges provenance={ledger.provenance} />
      </CollapsibleContent>
    </Collapsible>
  );
};
```

### 4.2 TokenTable Component

```tsx
interface TokenTableProps {
  tokens: TokenLedger[];
}

const TokenTable: React.FC<TokenTableProps> = ({ tokens }) => {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>#</TableHead>
          <TableHead>Surface</TableHead>
          <TableHead>Lemma</TableHead>
          <TableHead>Morph</TableHead>
          <TableHead>Gloss</TableHead>
          <TableHead>Confidence</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {tokens.map((token, idx) => (
          <TokenRow key={idx} token={token} />
        ))}
      </TableBody>
    </Table>
  );
};
```

### 4.3 ConfidenceBars Component (Reuse ADR-010 Style)

```tsx
// Reuse existing confidence presentation pattern
const ConfidenceBars: React.FC<{ confidence: TokenConfidence }> = ({ confidence }) => {
  return (
    <div className="confidence-bars">
      <ConfidenceBar label="Textual" value={confidence.textual} />
      <ConfidenceBar label="Grammatical" value={confidence.grammatical} />
      <ConfidenceBar label="Lexical" value={confidence.lexical} />
      <ConfidenceBar label="Interpretive" value={confidence.interpretive} />
    </div>
  );
};
```

### 4.4 ProvenanceBadges Component

```tsx
const ProvenanceBadges: React.FC<{ provenance: LedgerProvenance }> = ({ provenance }) => {
  return (
    <div className="provenance-badges">
      <Badge variant="primary">Spine: {provenance.spine_source_id}</Badge>
      {provenance.comparative_sources_used.map(id => (
        <Badge key={id} variant="secondary">{id}</Badge>
      ))}
      <EvidenceClassSummaryBadge summary={provenance.evidence_class_summary} />
    </div>
  );
};
```

### 4.5 Screen Integration

```tsx
// In Translate.tsx
{mode === 'traceable' && response?.ledger && (
  <div className="ledger-section">
    {response.ledger.map((verseLedger, idx) => (
      <LedgerPanel
        key={verseLedger.verse_id}
        ledger={verseLedger}
        expanded={expandedLedgers.includes(idx)}
        onToggle={() => toggleLedger(idx)}
      />
    ))}
  </div>
)}
```

### 4.6 Dossier Panel (Unchanged)

Per non-negotiables: DossierPanel behavior remains unchanged from Sprint 9.

---

## 5. CLI Plan: Traceable Output

### 5.1 New CLI Options

```bash
# Human-readable output (default)
redletters translate "John 1:18" --mode traceable --translator traceable

# JSON output with ledger
redletters translate "John 1:18" --mode traceable --translator traceable --json

# Explicit ledger flag (for human output)
redletters translate "John 1:18" --mode traceable --translator traceable --ledger
```

### 5.2 Click Option Definitions

```python
@click.option('--translator',
    type=click.Choice(['literal', 'fluent', 'traceable', 'fake', 'real']),
    default='fluent',
    help='Translator type to use')

@click.option('--ledger/--no-ledger',
    default=False,
    help='Show token ledger in human output (traceable mode only)')

@click.option('--json', 'output_json',
    is_flag=True,
    help='Output as JSON (includes ledger in traceable mode)')
```

### 5.3 Human Output Format (--ledger)

```
John 1:18 (Traceable Mode)
==========================

Translation:
  No one has ever seen God; the only God, who is at the Father's side,
  he has made him known.

Token Ledger:
  # | Surface  | Lemma    | Morph      | Gloss          | Conf (T/G/L/I)
  --|----------|----------|------------|----------------|----------------
  1 | Θεὸν     | θεός     | N-ASM      | God            | .95/.90/.85/.80
  2 | οὐδεὶς   | οὐδείς   | A-NSM      | no one         | .92/.88/.90/.75
  ...

Provenance:
  Spine: sblgnt
  Comparative: morphgnt, na28-variants
  Evidence: 3 manuscripts, 2 editions, 1 tradition
```

### 5.4 JSON Output Format

```json
{
  "reference": "John 1:18",
  "mode": "traceable",
  "translation": "No one has ever seen God...",
  "ledger": [
    {
      "verse_id": "john-1-18",
      "normalized_ref": "John 1:18",
      "tokens": [
        {
          "position": 0,
          "surface": "Θεὸν",
          "normalized": "θεον",
          "lemma": "θεός",
          "morph": "N-ASM",
          "gloss": "God",
          "gloss_source": "basic_glosses",
          "notes": [],
          "confidence": {
            "textual": 0.95,
            "grammatical": 0.90,
            "lexical": 0.85,
            "interpretive": 0.80,
            "explanations": {
              "textual": "Strong manuscript consensus",
              "grammatical": "Unambiguous accusative",
              "lexical": "Core meaning clear",
              "interpretive": "Referent identification minimal"
            }
          }
        }
      ],
      "provenance": {
        "spine_source_id": "sblgnt",
        "comparative_sources_used": ["morphgnt"],
        "evidence_class_summary": {
          "manuscript_count": 3,
          "edition_count": 2,
          "tradition_count": 1,
          "other_count": 0
        }
      }
    }
  ],
  "variants": [...],
  "confidence": {...},
  "claims": [...]
}
```

---

## 6. Test Plan

### 6.1 Unit Tests

| Test | File | Purpose |
|------|------|---------|
| `test_lexicon_provider_normalization` | `test_lexicon.py` | Verify accent stripping and lookup |
| `test_lexicon_provider_fallback` | `test_lexicon.py` | Multiple providers, fallback chain |
| `test_ledger_schema_validation` | `test_ledger_schemas.py` | Pydantic validation of all ledger types |
| `test_token_confidence_layers` | `test_ledger_schemas.py` | Four-layer confidence in TokenLedger |
| `test_evidence_class_summary` | `test_ledger_schemas.py` | Summary counts explicit (not collapsed) |

### 6.2 Integration Tests

| Test | File | Purpose |
|------|------|---------|
| `test_traceable_returns_ledger` | `test_traceable_translator.py` | Traceable mode includes ledger |
| `test_readable_no_ledger` | `test_traceable_translator.py` | Readable mode returns None ledger |
| `test_ledger_token_count` | `test_traceable_translator.py` | Token count matches fixture verse |
| `test_gate_still_blocks` | `test_traceable_gates.py` | Major/significant variants require ack |
| `test_acknowledge_returns_ledger` | `test_traceable_gates.py` | Post-ack includes ledger |
| `test_evidence_class_explicit` | `test_traceable_translator.py` | Summary not collapsed to single score |
| `test_type5_blocked_readable` | `test_traceable_translator.py` | ADR-009 enforcement in readable mode |

### 6.3 CLI Tests

| Test | File | Purpose |
|------|------|---------|
| `test_cli_traceable_json` | `test_cli_traceable.py` | --json includes ledger |
| `test_cli_traceable_ledger_flag` | `test_cli_traceable.py` | --ledger shows human table |
| `test_cli_traceable_default_no_ledger` | `test_cli_traceable.py` | Default human output hides ledger |

### 6.4 GUI Tests (Manual + E2E)

| Test | Type | Purpose |
|------|------|---------|
| Ledger panel renders | Manual | Verify collapsible panel appears |
| Token table displays | Manual | All columns populated correctly |
| Confidence bars match | Manual | Reuse ADR-010 presentation style |
| Provenance badges show | Manual | Spine + comparative pack IDs visible |
| Dossier unchanged | Manual | No regression in dossier panel |

---

## 7. Implementation Order (ACT Phase)

### Phase 1: Schemas + Types (B1)
1. Create `src/redletters/ledger/schemas.py`
2. Define all dataclasses: VerseLedger, TokenLedger, TokenConfidence, SegmentLedger, LedgerProvenance, EvidenceClassSummary
3. Extend TranslateResponse with optional `ledger` field
4. Add unit tests for schema validation

### Phase 2: Lexicon Provider (B2)
1. Create `src/redletters/lexicon/provider.py` with Protocol
2. Implement BasicGlossProvider wrapping existing BASIC_GLOSSES
3. Extract and reuse `_normalize_greek()` as shared utility
4. Add unit tests for lookup and normalization

### Phase 3: TraceableTranslator (B3)
1. Create `src/redletters/pipeline/traceable_translator.py`
2. Register TranslatorType.TRACEABLE
3. Implement token-level analysis with ledger generation
4. Wire into orchestrator with mode enforcement
5. Add integration tests

### Phase 4: GUI Ledger Panel (B4)
1. Create `gui/src/components/LedgerPanel.tsx`
2. Create `gui/src/components/TokenTable.tsx`
3. Create `gui/src/components/ConfidenceBars.tsx` (or reuse existing)
4. Create `gui/src/components/ProvenanceBadges.tsx`
5. Integrate into Translate.tsx
6. Manual testing

### Phase 5: CLI Flags + JSON (B5)
1. Add --translator option to translate command
2. Add --ledger flag
3. Add --json output mode
4. Implement human ledger table formatting
5. Add CLI tests

### Phase 6: Receipt + Validation
1. Run full test suite (must pass)
2. Run ruff (must be clean)
3. Create SPRINT-10-RECEIPT.md
4. Manual runbook execution

---

## 8. ADR Confirmations (Non-Negotiables Checklist)

| ADR | Requirement | Validation Method |
|-----|-------------|-------------------|
| ADR-007 | SBLGNT canonical spine | `spine_source_id` always "sblgnt" |
| ADR-008 | Variants side-by-side; major/significant require ack | Gate tests unchanged |
| ADR-009 | TYPE5+ forbidden in readable | test_type5_blocked_readable |
| ADR-010 | Layered confidence always visible | TokenConfidence has all 4 layers |
| Evidence explicit | manuscript/edition/tradition counts | EvidenceClassSummary not collapsed |
| redletters.* warnings | Must be errors | Ruff + pytest warning filter |
| Backward compat | Existing CLI/API/GUI flows work | Full test suite regression |

---

## 9. Files to Create/Modify

### New Files
- `src/redletters/ledger/__init__.py`
- `src/redletters/ledger/schemas.py`
- `src/redletters/lexicon/__init__.py`
- `src/redletters/lexicon/provider.py`
- `src/redletters/pipeline/traceable_translator.py`
- `gui/src/components/LedgerPanel.tsx`
- `gui/src/components/TokenTable.tsx`
- `gui/src/components/ProvenanceBadges.tsx`
- `tests/test_ledger_schemas.py`
- `tests/test_lexicon.py`
- `tests/test_traceable_translator.py`
- `tests/test_cli_traceable.py`
- `docs/SPRINT-10-RECEIPT.md`

### Modified Files
- `src/redletters/pipeline/schemas.py` - Add ledger field to TranslateResponse
- `src/redletters/pipeline/orchestrator.py` - Wire TraceableTranslator
- `src/redletters/pipeline/translator.py` - Export normalize_greek utility
- `src/redletters/engine_spine/cli.py` - Add --translator, --ledger, --json
- `gui/src/screens/Translate.tsx` - Integrate LedgerPanel
- `gui/src/api/types.ts` - Add ledger types

---

## 10. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Schema complexity | Medium | Start minimal, iterate |
| Lexicon licensing | High | Use only BasicGlossProvider initially |
| Performance (large verses) | Low | Ledger is per-verse, not per-chapter |
| UI complexity | Medium | Reuse existing confidence presentation |
| Test coverage gaps | Medium | TDD approach, fixture-based tests |

---

**MAP Status**: COMPLETE
**Next Step**: Begin ACT Phase 1 (Schemas + Types)
