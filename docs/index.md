# Red Letters Documentation

Welcome to the Red Letters Source Reader documentation.

## Quick Navigation

| Document | Description |
|----------|-------------|
| [CLI Reference](cli.md) | Complete command-line interface documentation |
| [GUI Guide](gui.md) | Desktop application usage |
| [API Reference](API.md) | REST API endpoints and schemas |
| [Key Concepts](concepts.md) | Receipts, gates, confidence layers, claims taxonomy |
| [Sources & Licensing](sources-and-licensing.md) | Data sources, EULA, attribution requirements |
| [Troubleshooting](troubleshooting.md) | Common problems and solutions |

## Project Documentation

| Document | Description |
|----------|-------------|
| [Goals & Principles](GOALS.md) | Enforceable constraints and non-goals |
| [Progress](PROGRESS.md) | Development history by sprint |
| [Architecture Decisions](adrs/) | ADR records |

## Naming Conventions

This project uses different names in different contexts:

| Context | Name | Why |
|---------|------|-----|
| GitHub repository | `greek2english` | Descriptive project slug |
| CLI command | `redletters` | User-facing tool name (Jesus' words in red) |
| Data directory | `~/.greek2english/` | Matches repo name for discoverability |
| Environment variables | `REDLETTERS_*` | Matches CLI for consistency |

This is intentional: the repository name describes the *function* (Greek to English),
while the CLI name reflects the *focus* (red-letter passages).

## Getting Help

- **README**: [../README.md](../README.md) - Quick start and installation
- **Issues**: Report bugs or request features on GitHub
- **API Docs**: When running `redletters serve`, visit http://localhost:8000/docs
