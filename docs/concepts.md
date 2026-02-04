# Key Concepts

This document explains the core concepts that make Red Letters different from
traditional translation tools.

## Important Disclaimer

**Red Letters produces plausible renderings, not "The One True Translation."**

Every output represents one of several defensible ways to render the Greek into
English. The tool is designed to show that translation involves interpretive
choices, not to hide those choices behind a single "correct" answer.

---

## Renderings vs Translations

A **rendering** is one of several plausible English expressions of the Greek text.
Red Letters generates 3-5 renderings per passage in different styles, explicitly
demonstrating that translation involves choices.

| Rendering Style | Description | Best For |
|-----------------|-------------|----------|
| `ultra-literal` | Word-for-word, preserving Greek syntax | Linguistic study |
| `natural` | Idiomatic English word order | General reading |
| `meaning-first` | Prioritizes semantic clarity | Comprehension |
| `jewish-context` | Socio-historical Jewish framing | Cultural study |

Each style makes different trade-offs. None is "more correct" than another.

---

## Receipts

Every rendering includes **receipts** - documentation of each translation decision.
This is the core transparency feature.

A receipt contains:

| Field | Description |
|-------|-------------|
| **Surface form** | The Greek word as it appears in the text |
| **Lemma** | Dictionary form of the word |
| **Morphology** | Tense, mood, voice, case, number, gender |
| **Chosen gloss** | The English word(s) selected |
| **Sense source** | Which lexicon provided the definition (BDAG, LSJ, etc.) |
| **Confidence** | Four-layer score (see below) |
| **Rationale** | Why this gloss was chosen over alternatives |
| **Alternate glosses** | Other defensible choices that weren't selected |

Receipts make translation auditable. You can trace exactly why "metanoeo"
became "change your mind" rather than "repent" and evaluate that decision yourself.

---

## Confidence Layers

Every claim carries four confidence dimensions:

| Layer | What It Measures | Example Uncertainty |
|-------|------------------|---------------------|
| **Textual** | Certainty about the Greek text itself | Manuscript variants at Mark 16:9 |
| **Grammatical** | Certainty about parsing | Ambiguous voice (middle/passive) |
| **Lexical** | Certainty about word meaning | "Logos" has 10+ senses |
| **Interpretive** | Certainty about contextual meaning | Irony, idiom, cultural reference |

### Confidence Buckets

Scores map to human-readable buckets:

| Bucket | Score Range | Meaning |
|--------|-------------|---------|
| **High** | >= 0.8 | Strong consensus, minimal ambiguity |
| **Medium** | >= 0.6 | Some uncertainty, multiple defensible options |
| **Low** | < 0.6 | Significant uncertainty, requires caution |

These thresholds are deterministic and tested. See `test_confidence_bucketing.py`.

---

## Gates

**Gates** are checkpoints that require acknowledgement before certain operations.
They exist where significant scholarly uncertainty affects the passage.

### When Gates Appear

- Significant textual variants that affect meaning
- Multiple competing manuscript readings
- Passages with ongoing scholarly debate

### Gate Friction

Gates implement intentional friction:

1. Export and quote commands fail with `PendingGatesError` if unacknowledged gates exist
2. You must review the variant evidence before proceeding
3. Using `--force` bypasses checks but marks output with `forced_responsibility: true`

This prevents casual certainty claims. You cannot export "John says X" without
first seeing that manuscripts disagree about what John says.

### Acknowledging Gates

```bash
# See what's pending
redletters gates pending "Mark 16:9"

# Review the variant dossier
redletters variants dossier "Mark 16:9"

# Acknowledge after review
redletters gates acknowledge "Mark 16:9" 0 --session my-session --reason "Reviewed attestation"
```

---

## Claims Taxonomy

Translation claims are classified by epistemic weight:

| Type | Category | Example | Certainty |
|------|----------|---------|-----------|
| TYPE0 | Direct textual | "The Greek word is logos" | Highest |
| TYPE1 | Morphological | "This is an imperative verb" | High |
| TYPE2 | Lexical | "logos can mean 'word' or 'reason'" | Medium-High |
| TYPE3 | Syntactic | "This phrase modifies the subject" | Medium |
| TYPE4 | Contextual | "In this context, 'reason' fits better" | Medium-Low |
| TYPE5 | Theological | "This implies X doctrine" | Lowest |

### Mode Restrictions

- **Readable mode**: Restricts output to TYPE0-4 claims (no theological claims)
- **Traceable mode**: Includes all claim types with explicit labeling

This prevents the tool from making theological claims that go beyond
the linguistic evidence.

---

## Translation Modes

### Readable Mode

Produces flowing English suitable for reading:

- Claims restricted to TYPE0-4 (no theological claims)
- Rendering optimized for comprehension
- Receipts available but not foregrounded

### Traceable Mode

Provides full provenance chain:

- All claim types included with explicit labels
- Token-level evidence ledger
- Every decision documented and auditable
- Best for scholarly analysis

---

## Deterministic Output

Red Letters uses no machine learning or randomization. Given the same:

- Input passage
- Installed packs
- Configuration

The output is identical every time. This makes results:

- **Auditable**: You can verify why output changed
- **Reproducible**: Share configs to get identical results
- **Debuggable**: No hidden stochastic behavior

Use `redletters packs lock` to capture your exact environment for reproducibility.

---

## Command Comparison

| Command | Purpose | Requires Gates? |
|---------|---------|-----------------|
| `query` | Quick lookup with multiple renderings | No |
| `translate` | Receipt-grade output with full provenance | Depends on mode |
| `quote` | Generate citeable output | Yes (or --force) |
| `export` | Machine-readable bulk export | Yes (or --force) |

### When to Use Each

- **query**: Exploring a passage, seeing rendering options
- **translate**: Studying a passage in depth, examining choices
- **quote**: Creating citations for publication
- **export**: Building datasets, feeding other tools

---

## Further Reading

- [Goals & Principles](GOALS.md) - Enforceable constraints and non-goals
- [CLI Reference](cli.md) - Full command documentation
- [Sources & Licensing](sources-and-licensing.md) - Data provenance
