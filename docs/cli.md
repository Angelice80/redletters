# CLI Reference

The `redletters` CLI is the primary interface for scholarly work.

## General Usage

```bash
redletters <command> [subcommand] [options]
redletters --help
redletters --version
```

---

## Core Commands

### init

Initialize the database with demo data.

```bash
redletters init
```

Creates the database at `~/.greek2english/engine.db` and loads sample passages.
After init, you can immediately run `query` without installing additional packs.

### query

Query a scripture reference for candidate renderings.

```bash
redletters query "Matthew 3:2"
redletters query "Mark 1:15" --style ultra-literal
redletters query "John 3:16" --output receipts.json
```

**Options:**
- `-s, --style TEXT` - Filter by rendering style (ultra-literal, natural, meaning-first, jewish-context)
- `-o, --output PATH` - Save output to JSON file

### list-spans

List all red-letter speech spans in the database.

```bash
redletters list-spans
```

### serve

Start the REST API server.

```bash
redletters serve
redletters serve --host 127.0.0.1 --port 9000
```

**Options:**
- `--host TEXT` - Bind address (default: 127.0.0.1)
- `--port INTEGER` - Bind port (default: 8000)

> **Security Warning:** Using `--host 0.0.0.0` exposes the API to your entire network.
> Only do this on trusted networks. The API has no authentication by default.

---

## Translation Commands

### translate

Translate a passage with receipt-grade output (full provenance).

```bash
redletters translate "John 1:18"
redletters translate "John 1:18" --mode readable
redletters translate "John 1:18" --mode traceable
redletters translate "John 1:18" --translator fluent
redletters translate "John 1:18" --translator traceable --ledger
redletters translate "Matthew 5:3" --json
```

**Options:**
- `--mode [readable|traceable]` - Output mode (readable restricts claims to TYPE0-4)
- `--translator [literal|fluent|traceable]` - Translation backend
- `--ledger` - Include token-level evidence ledger
- `--json` - Output as JSON
- `--ack TEXT` - Acknowledge a variant inline (e.g., `--ack "Mark 16:9:0"`)
- `--session TEXT` - Session ID for acknowledgement tracking

---

## Source Pack Management

Source packs provide Greek texts, lexica, and comparative editions.

### sources list

List configured sources from `sources_catalog.yaml`.

```bash
redletters sources list
redletters sources list --json
```

### sources install

Install a source pack.

```bash
redletters sources install morphgnt-sblgnt
redletters sources install morphgnt-sblgnt --accept-eula
redletters sources install morphgnt-sblgnt --force
redletters sources install morphgnt-sblgnt --data-root ~/custom
```

**Options:**
- `--accept-eula` - Accept license terms for EULA-gated content
- `--force` - Reinstall even if already installed
- `--data-root PATH` - Override default data directory

### sources status

Show installation status of all sources.

```bash
redletters sources status
```

### sources info

Show detailed information about a specific source.

```bash
redletters sources info morphgnt-sblgnt
```

### sources validate

Validate the `sources_catalog.yaml` structure.

```bash
redletters sources validate
```

---

## Sense Pack Management

Sense packs provide lexical data (word meanings, glosses).

### packs list

List installed sense packs in precedence order.

```bash
redletters packs list
```

### packs validate

Validate a sense pack structure.

```bash
redletters packs validate ./my-sense-pack
redletters packs validate ./my-sense-pack --strict
```

### packs index

Create an index manifest for a pack.

```bash
redletters packs index ./my-sense-pack --output-manifest manifest.json
```

### packs lock

Generate a lockfile for reproducible environments (v0.11+).

```bash
redletters packs lock --out packs.lock
```

### packs sync

Sync installed packs to match a lockfile.

```bash
redletters packs sync packs.lock
```

---

## Variant Analysis

### variants build

Build variant apparatus for a passage.

```bash
redletters variants build "John 1:1"
redletters variants build "John 1" --scope chapter
redletters variants build "Matthew 5" --scope chapter --all-installed
redletters variants build "Mark 1" --scope chapter --all-installed --exclude pack-name
```

**Options:**
- `--scope [verse|chapter]` - Build scope
- `--all-installed` - Include all installed comparative packs
- `--exclude TEXT` - Exclude specific packs

### variants dossier

View full variant information with metadata.

```bash
redletters variants dossier "John 7:53"
redletters variants dossier "Mark 16:9" --json
```

### variants list

List built variants.

```bash
redletters variants list
redletters variants list --verse "John 1:1"
redletters variants list --significance high
```

---

## Gate Management

Gates require acknowledgement of significant variants before certain operations.

### gates pending

Show unacknowledged gates for a passage.

```bash
redletters gates pending "Mark 16:9"
redletters gates pending "Mark 16:9" --session my-session
```

### gates acknowledge

Acknowledge a specific variant.

```bash
redletters gates acknowledge "Mark 16:9" 0 --session my-session
redletters gates acknowledge "Mark 16:9" 0 --session my-session --reason "Reviewed manuscript evidence"
```

### gates list

List acknowledged gates for a session.

```bash
redletters gates list --session my-session
```

---

## Export Commands

### export apparatus

Export variant apparatus to JSONL.

```bash
redletters export apparatus "John 1" --out apparatus.jsonl
redletters export apparatus "Mark 16" --out apparatus.jsonl --force
```

The `--force` flag bypasses gate checks but marks output with `forced_responsibility: true`.

### export translation

Export translation data.

```bash
redletters export translation --out translation.jsonl
```

### export citations

Export citations with provenance.

```bash
redletters export citations --out citations.json
```

### export snapshot

Create a versioned snapshot combining multiple exports.

```bash
redletters export snapshot --out snapshot.json --include-citations --inputs apparatus.jsonl translation.jsonl
```

### export verify

Verify snapshot integrity.

```bash
redletters export verify snapshot.json
```

### quote

Generate a citeable quote (requires gate acknowledgement).

```bash
redletters quote "John 3:16" --out quote.json
redletters quote "Mark 16:9" --out quote.json --force --session my-session
```

---

## Validation

### validate output

Validate generated output files against schema contracts.

```bash
redletters validate output apparatus.jsonl
redletters validate output translation.jsonl --type translation
```

### validate schemas

List available schema versions.

```bash
redletters validate schemas
```

---

## Sense Analysis

### senses explain

Explain sense definitions for a Greek word.

```bash
redletters senses explain "logos"
```

### senses conflicts

Find conflicting definitions across packs.

```bash
redletters senses conflicts "agape"
```

### senses list-packs

List sense packs.

```bash
redletters senses list-packs
```

---

## Claims Analysis

### claims analyze

Analyze theological claims for textual uncertainty.

```bash
redletters claims analyze claims.json --out analysis.json
```

Input format:

```json
{
  "claims": [
    {
      "id": "claim-1",
      "text": "Jesus claimed divinity",
      "references": ["John 8:58", "John 10:30"]
    }
  ]
}
```

---

## Utility Commands

### licenses

Show license and provenance report for all data sources.

```bash
redletters licenses
```

### engine start

Start the engine service (advanced deployment).

```bash
redletters engine start --host 127.0.0.1 --port 47200
```

### engine status

Check engine service status.

```bash
redletters engine status
```

### engine reset

Reset engine data (destructive).

```bash
redletters engine reset --confirm-destroy
```

### diagnostics export

Export diagnostics bundle.

```bash
redletters diagnostics export --output diagnostics.zip
```

### auth

Manage auth tokens.

```bash
redletters auth show
redletters auth reset
redletters auth rotate
```

---

## Global Options

### --data-root

Override the default data directory for any command.

```bash
redletters --data-root ~/custom-location sources list
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `REDLETTERS_DATA_ROOT` | Override default data location (~/.greek2english/) |
| `REDLETTERS_LOG_LEVEL` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
