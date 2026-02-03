# Red Letters Source Reader

A transparent Greek New Testament tool that generates **multiple plausible English
renderings** with explicit interpretive receipts.

**Current Version:** v0.17.0

> **Important:** This tool produces *plausible renderings*, not "The One True
> Translation." Every output shows that translation involves interpretive choices.
> See [Concepts](docs/concepts.md) for details.

---

## Why Red Letters?

- **No hidden theology**: Every translation choice is documented with rationale
- **Multiple readings**: Shows the ambiguity inherent in translation
- **Greek-first**: All analysis starts from the Greek text (SBLGNT canonical spine)
- **Uncertainty propagation**: Confidence scores (textual, grammatical, lexical, interpretive) flow through all outputs
- **Friction is intentional**: Exports require acknowledgement of significant variants
- **Deterministic**: No ML, no randomization - fully auditable and reproducible

See [Goals & Principles](docs/GOALS.md) for enforceable constraints.

---

## Installation

**Requirements:** Python 3.8+

```bash
git clone https://github.com/your-org/greek2english.git
cd greek2english
pip install -e .
```

Verify:

```bash
redletters --version
redletters --help
```

---

## Quick Start

```bash
# 1. Initialize database with demo data
redletters init

# 2. Query a verse
redletters query "Matthew 3:2"

# 3. See all available passages
redletters list-spans
```

Output shows multiple renderings:

```
Reference: Matthew 3:2
Greek: metanoeite eggiken gar he basileia ton ouranon

Renderings:
  1. [ultra-literal] Change-your-minds! Has-drawn-near for the kingdom of-the heavens.
  2. [natural] Change your minds! The kingdom of heaven has drawn near.
  3. [meaning-first] Transform your thinking! God's reign is approaching.
```

Each rendering includes receipts documenting why each word was translated that way.

---

## Example Workflow

### 1. Explore a passage

```bash
redletters query "John 1:18"
```

### 2. Get full receipts

```bash
redletters translate "John 1:18" --mode traceable --ledger
```

### 3. Check for variants

```bash
redletters variants dossier "John 1:18"
```

### 4. Acknowledge and export

```bash
# If variants exist, acknowledge them first
redletters gates pending "John 1:18"
redletters gates acknowledge "John 1:18" 0 --session my-session

# Then export
redletters quote "John 1:18" --out quote.json
```

---

## Starting the Engine

```bash
redletters serve
```

The Engine Spine provides a unified API for translation, source management, and scholarly exports.

- **Default Port**: 47200 (localhost only)
- **Swagger UI**: http://127.0.0.1:47200/docs
- **ReDoc**: http://127.0.0.1:47200/redoc

> **Security Note:** The engine binds to 127.0.0.1 only (per ADR-005). It requires
> a Bearer token for authentication. The GUI handles token management automatically.

---

## GUI (Desktop Application)

For a visual interface, start the GUI:

```bash
# Terminal 1: Start the backend
redletters serve

# Terminal 2: Start the GUI
cd gui
npm install  # first time only
npm run dev
```

Open http://localhost:5173 in your browser, or build the desktop app with `npm run tauri:build`.

See [GUI Guide](docs/gui.md) for full documentation.

---

## Naming Conventions

| Context | Name | Why |
|---------|------|-----|
| Repository | `greek2english` | Describes the function |
| CLI command | `redletters` | Reflects the focus (Jesus' words) |
| Data directory | `~/.greek2english/` | Matches repo for discoverability |
| Environment variables | `REDLETTERS_*` | Matches CLI for consistency |

---

## Documentation

| Document | Description |
|----------|-------------|
| [CLI Reference](docs/cli.md) | Complete command documentation |
| [GUI Guide](docs/gui.md) | Desktop application usage |
| [API Reference](docs/API.md) | REST endpoints and schemas |
| [Key Concepts](docs/concepts.md) | Receipts, gates, confidence, claims |
| [Sources & Licensing](docs/sources-and-licensing.md) | Data provenance and attribution |
| [Troubleshooting](docs/troubleshooting.md) | Common problems and solutions |
| [Goals & Principles](docs/GOALS.md) | Project constraints and non-goals |

---

## Installing Source Packs

The demo data from `init` allows basic exploration. For full scholarly work,
install source packs:

```bash
# List available sources
redletters sources list

# Install the canonical Greek text
redletters sources install morphgnt-sblgnt

# Some sources require license acceptance
redletters sources install ubs-dictionary --accept-eula
```

See [Sources & Licensing](docs/sources-and-licensing.md) for what each pack
provides and license requirements.

---

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/
```

---

## License

MIT

---

## Further Reading

- [docs/PROGRESS.md](docs/PROGRESS.md) - Development history
- [docs/schemas/](docs/schemas/) - JSON Schema definitions
- [docs/adrs/](docs/adrs/) - Architecture decision records
