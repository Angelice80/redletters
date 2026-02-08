# Red Letters Source Reader

A transparent Greek New Testament tool that generates **multiple plausible English
renderings** with explicit interpretive receipts.

> **Important:** This tool produces *plausible renderings*, not "The One True
> Translation." Every output shows that translation involves interpretive choices.
> See [Key Concepts](docs/concepts.md) for details.

---

## Why Red Letters?

- **No hidden theology** – Every translation choice is documented with rationale
- **Multiple readings** – Shows the ambiguity inherent in translation
- **Greek-first** – All analysis starts from the Greek text (SBLGNT canonical spine)
- **Uncertainty propagation** – Confidence scores (textual, grammatical, lexical, interpretive) flow through all outputs
- **Friction is intentional** – Exports require acknowledgement of significant variants
- **Deterministic** – No ML, no randomization – fully auditable and reproducible

---

## Installation

```bash
git clone https://github.com/your-org/greek2english.git
cd greek2english
pip install -e .
redletters --version
```

---

## Quick Start (60 seconds)

```bash
# 1. Initialize with demo data
redletters init

# 2. Query a verse (works immediately – no packs required)
redletters query "Matthew 3:2"

# 3. See available passages
redletters list-spans
```

The demo data lets you explore immediately. For full scholarly work, install
source packs – see [Sources & Licensing](docs/sources-and-licensing.md).

---

## Example Workflow

```bash
# 1. Explore a passage
redletters query "John 1:18"

# 2. Get full translation with receipts
redletters translate "John 1:18" --mode traceable --ledger

# 3. Check for textual variants
redletters variants dossier "John 1:18"

# 4. Acknowledge variants and export
redletters gates pending "John 1:18"
redletters gates acknowledge "John 1:18" 0 --session my-export
redletters quote "John 1:18" --out quote.json
```

---

## Starting the GUI

```bash
redletters gui                # Start backend + open GUI in browser
redletters gui --dev          # Start backend + GUI dev server
```

That's it. One command starts everything.

For server-only modes:

```bash
redletters serve              # localhost:8000 (legacy API)
redletters engine start       # localhost:47200 (modern API)
```

> **Security Warning:** Never use `--host 0.0.0.0` on untrusted networks.
> This exposes the API to your entire network without authentication.
> See [CLI Reference](docs/cli.md#serve-legacy) for details.

---

## Naming Conventions

This project uses different names in different contexts – intentionally:

| Context | Name | Why |
|---------|------|-----|
| Repository | `greek2english` | Describes the function |
| CLI command | `redletters` | Reflects the focus (Jesus' words) |
| Data directory | `~/.greek2english/` | Matches repo for discoverability |
| Environment variables | `REDLETTERS_*` | Matches CLI for consistency |

The repository name describes the *function* (Greek to English), while the
CLI name reflects the *focus* (red-letter passages). See [docs/index.md](docs/index.md)
for the full rationale.

---

## Documentation

| Document | Description |
|----------|-------------|
| [CLI Reference](docs/cli.md) | Complete command documentation |
| [GUI Guide](docs/gui.md) | Desktop application usage |
| [API Reference](docs/API.md) | REST endpoints and schemas |
| [Key Concepts](docs/concepts.md) | Receipts, gates, confidence, command taxonomy |
| [Sources & Licensing](docs/sources-and-licensing.md) | Data provenance and attribution |
| [Troubleshooting](docs/troubleshooting.md) | Common problems and solutions |
| [Goals & Principles](docs/GOALS.md) | Project constraints and non-goals |

---

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src/ tests/
```

---

## License

MIT
