# BMad Knowledge Base - Red Letters Project

## Project Overview

**Red Letters Source Reader** is a transparent, multi-reading Greek New Testament tool that generates 3-5 plausible renderings for Jesus' sayings with explicit interpretive receipts.

### Core Principles
1. **No hidden theology**: Every translation choice is documented with linguistic rationale
2. **Multiple readings**: Shows the ambiguity inherent in translation
3. **Greek-first**: All analysis starts from the Greek text
4. **Extensible**: Plugin architecture for lexica, variants, and witness traditions

## Architecture

### Module Structure
```
redletters/
├── ingest/          # Data loading & normalization
├── engine/          # Core rendering logic
│   ├── query.py     # Reference parsing
│   ├── senses.py    # Lexeme lookup
│   ├── generator.py # Candidate generation
│   ├── ranker.py    # Deterministic ranking
│   └── receipts.py  # Receipt generation
├── api/             # FastAPI endpoints
├── plugins/         # Extension interfaces
└── db/              # SQLite utilities
```

### Key Concepts

#### Receipts
Every rendering includes traceable "receipts" documenting:
- Lemma (dictionary form)
- Morphology code
- Sense selection with source
- Rationale for choice
- Ambiguity flags

#### Rendering Styles
| Style | Description |
|-------|-------------|
| ultra-literal | Word-for-word, preserving Greek syntax |
| natural | Idiomatic English word order |
| meaning-first | Prioritizes semantic clarity |
| jewish-context | Socio-historical Jewish framing |

#### Plugin Interfaces
- **SenseProvider**: Custom lexicon data sources
- **VariantProvider**: Textual variant apparatus (future)
- **WitnessOverlay**: Syriac and other tradition data (future)

## Data Sources

### Currently Implemented
- Hardcoded demo data (Matthew 3:2, 4:17, Mark 1:15, Matthew 5:3, 6:9-10)

### Planned Integrations
- **MorphGNT**: Morphologically tagged Greek NT
- **SBLGNT**: SBL Greek New Testament text
- **BDAG**: Bauer-Danker Greek Lexicon
- **Louw-Nida**: Semantic domain lexicon
- **NA28**: Nestle-Aland critical apparatus
- **Peshitta**: Syriac witness

## Development Standards

### Testing
- Minimum 80% coverage
- TDD approach (tests first)
- Acceptance tests in docs/BMAD-SPEC.md

### Code Style
- Python 3.11+ with type hints
- Pydantic for API models
- Click + Rich for CLI
- SQLite for data storage

### Documentation
- ADRs for architectural decisions
- Receipts for all translation choices
- Provenance for all data sources
