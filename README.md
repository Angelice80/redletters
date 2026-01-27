# Red Letters Source Reader

A transparent, multi-reading Greek New Testament tool that generates **3-5 plausible renderings**
for Jesus' sayings with explicit interpretive receipts.

## Philosophy

- **No hidden theology**: Every translation choice is documented with linguistic rationale
- **Multiple readings**: Shows the ambiguity inherent in translation
- **Greek-first**: All analysis starts from the Greek text
- **Extensible**: Plugin architecture for lexica, variants, and witness traditions

## Quick Start

```bash
# Install
pip install -e .

# Initialize database with demo data
redletters init

# Query a verse
redletters query "Matthew 3:2"

# Start API server
redletters serve
```

## CLI Commands

```bash
# Show all red-letter spans in demo data
redletters list-spans

# Query with specific rendering style
redletters query "Mark 1:15" --style ultra-literal

# Export receipts to JSON file
redletters query "Matthew 3:2" --output receipts.json
```

## API Endpoints

```
GET  /api/v1/query?ref=Matthew+3:2
GET  /api/v1/query?ref=Mark+1:15&style=natural
GET  /api/v1/spans
GET  /api/v1/health
```

## Rendering Styles

| Style | Description |
|-------|-------------|
| `ultra-literal` | Word-for-word, preserving Greek syntax |
| `natural` | Idiomatic English word order |
| `meaning-first` | Prioritizes semantic clarity |
| `jewish-context` | Socio-historical Jewish framing |

## Output Format

```json
{
  "reference": "Matthew 3:2",
  "greek_text": "μετανοεῖτε· ἤγγικεν γὰρ ἡ βασιλεία τῶν οὐρανῶν",
  "renderings": [
    {
      "style": "ultra-literal",
      "text": "Change-your-minds! Has-drawn-near for the kingdom of-the heavens.",
      "score": 0.92,
      "receipts": [...]
    }
  ]
}
```

## Architecture

```
redletters/
├── ingest/          # Data loading & normalization
├── engine/          # Core rendering logic
│   ├── query.py     # Reference parsing
│   ├── senses.py    # Lexeme lookup
│   ├── generator.py # Candidate generation
│   └── ranker.py    # Deterministic ranking
├── api/             # FastAPI endpoints
├── plugins/         # Extension interfaces
└── db/              # SQLite utilities
```

## Plugin System

The system supports plugins for:
- **Sense Providers**: Custom lexicon data sources
- **Variant Providers**: Textual variant apparatus (future)
- **Witness Overlays**: Syriac and other tradition data (future)

## License

MIT
