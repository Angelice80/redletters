# Red Letters Documentation

Welcome to the Red Letters Source Reader documentation.

> **Remember:** This tool produces *plausible renderings*, not definitive translations.
> Every output shows that translation involves interpretive choices.

---

## Quick Navigation

| Document | Description |
|----------|-------------|
| [CLI Reference](cli.md) | Complete command-line interface documentation |
| [GUI Guide](gui.md) | Desktop application usage |
| [API Reference](API.md) | REST API endpoints and schemas |
| [Key Concepts](concepts.md) | Receipts, gates, confidence layers, command taxonomy |
| [Sources & Licensing](sources-and-licensing.md) | Data sources, EULA, attribution requirements |
| [Troubleshooting](troubleshooting.md) | Common problems and solutions |

## Project Documentation

| Document | Description |
|----------|-------------|
| [Goals & Principles](GOALS.md) | Enforceable constraints and non-goals |
| [Progress](PROGRESS.md) | Development history by sprint |
| [Architecture Decisions](adrs/) | ADR records |

---

## Naming Conventions (Codename vs Product Name)

This project intentionally uses different names in different contexts. This is
not an accident – it reflects different aspects of the project:

| Context | Name | Rationale |
|---------|------|-----------|
| **GitHub repository** | `greek2english` | Descriptive slug for the *function* – converting Greek NT text to English renderings |
| **CLI command** | `redletters` | User-facing *brand* name – reflects the focus on red-letter passages (Jesus' words) |
| **Data directory** | `~/.greek2english/` | Matches repo name for discoverability when debugging |
| **Environment variables** | `REDLETTERS_*` | Matches CLI for consistency in user-facing config |

### Why Two Names?

- **Repository name** (`greek2english`) is *technical* – it describes what the code does
- **CLI name** (`redletters`) is *user-facing* – it reflects the scholarly focus

This pattern is common in open source: the Go programming language lives in
`golang/go`, Docker's CLI is `docker` but the repo is `moby/moby`, etc.

### Data Location

All user data lives under `~/.greek2english/`:

```
~/.greek2english/
├── engine.db          # SQLite database
├── packs/             # Installed source/sense packs
├── workspaces/        # Job outputs
├── logs/              # Engine logs
├── config.toml        # User configuration
└── .auth_token        # API auth token (or in OS keychain)
```

Override with `REDLETTERS_DATA_ROOT` environment variable or `--data-root` flag.

---

## Quick Start Commands

### For CLI Usage

```bash
redletters init                    # Initialize with demo data
redletters query "Matthew 3:2"     # Query a verse
redletters translate "John 1:1" --mode traceable --ledger
```

### For GUI Usage

```bash
redletters gui                         # Start backend + open GUI (one command)
redletters gui --dev                   # With hot reload for development
```

### For API Scripting

```bash
redletters serve --port 8000           # Start legacy REST API
curl "http://localhost:8000/api/v1/query?ref=Matthew%203:2"
```

---

## Getting Help

- **README**: [../README.md](../README.md) – Quick start and installation
- **Troubleshooting**: [troubleshooting.md](troubleshooting.md) – Common problems
- **Issues**: Report bugs or request features on GitHub
- **API Docs**: When running `redletters serve`, visit http://localhost:8000/docs

---

## Security Notes

### Local-Only Binding

The engine binds to `127.0.0.1` only by default. This is a security requirement
(see [ADR-005](adrs/ADR-005-local-security-model.md)).

### Never Use `--host 0.0.0.0` on Untrusted Networks

The `serve` command supports `--host 0.0.0.0` for special cases, but this exposes
the API to your entire network **without authentication**. Only use this:

- On isolated development VMs
- Behind a reverse proxy with proper auth
- On air-gapped networks

See [CLI Reference: serve](cli.md#serve-legacy) for details.
