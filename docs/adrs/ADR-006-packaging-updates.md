# ADR-006: Packaging & Updates

**Status**: Accepted
**Date**: 2026-01-27
**Context**: Desktop GUI Architecture (Phase 5)
**Supersedes**: ADR-001 Decision 7 ("Desktop app — rejected")
**Related**: ADR-001 (CLI-first), ADR-005 (Security)

> **Supersession Details**:
> - **Original Decision**: ADR-001 Decision 7 rejected desktop packaging: "Desktop app — rejected (distribution complexity)"
> - **Original Rationale**: MVP needed fast iteration; desktop adds signing, updates, platform testing
> - **Why Revisited**: Entering Phase 5 (UI); Tauri significantly reduces GUI complexity; engine is now stable
> - **Impact**: CLI remains authoritative for scripting; desktop is a GUI layer atop the same engine
> - **Migration**: None required; this is additive, not replacing CLI

---

## Context

Red Letters ships as a desktop application for Windows and macOS. Two components must be distributed:

1. **GUI** (Tauri app): User-facing installer
2. **Engine**: Long-running processing daemon

Key distribution challenges:
- Engine must be bundled as standalone executable (no runtime dependencies for user)
- Both components must version-match
- Updates should be seamless (not lose user data)
- Signing/notarization required for modern OS trust

## Decision

### Bundle Engine with GUI Installer

**Choice**: Single installer contains both GUI and Engine as standalone executables.

```
Greek2English-1.2.0-macos.dmg
├── Greek2English.app/           # Tauri GUI
│   └── Contents/
│       ├── MacOS/
│       │   └── Greek2English    # Main executable
│       └── Resources/
│           └── engine/          # Bundled engine
│               ├── redletters   # Standalone engine binary
│               └── data/        # Bundled demo data
```

**Rationale**:
- Single download, single install
- Version coupling guaranteed
- No runtime installation required (Python, Node, etc.)
- Smaller total size (shared dependencies)

---

## Engine Packaging: Language-Specific Options

The engine packaging approach depends on the engine implementation language. **This decision is deferred until engine language is locked.**

### If Engine is Python (Current Implementation)

**Primary Option: PyInstaller**

```bash
pyinstaller --onedir --name redletters src/redletters/__main__.py
```

| Pros | Cons |
|------|------|
| Mature, well-documented | macOS notarization requires hardened runtime entitlements |
| Handles most dependencies | Some packages need `--hidden-import` |
| Good cross-platform | Output size ~30-50 MB |

**Known PyInstaller + macOS Gotchas**:
- Hardened runtime required for notarization (`--osx-entitlements-file`)
- Some dynamic imports (uvicorn, pydantic) need explicit `--hidden-import`
- Code signing must happen AFTER PyInstaller, not before
- `--onedir` preferred over `--onefile` for faster startup

**Alternative: Nuitka**

```bash
nuitka --standalone --onefile src/redletters/__main__.py
```

| Pros | Cons |
|------|------|
| Compiles to C, faster startup | Longer build times |
| Smaller binaries | Less documentation |
| Better obfuscation | Some edge cases with C extensions |

### If Engine is Rust (Future Consideration)

```bash
cargo build --release
```

| Pros | Cons |
|------|------|
| Single static binary | Rewrite required |
| No runtime, tiny size (~5-10 MB) | Learning curve |
| Easy cross-compilation | Different ecosystem |

### If Engine is Go

```bash
go build -ldflags="-s -w" -o redletters
```

Similar trade-offs to Rust.

### Recommendation

**For MVP**: Use PyInstaller with Python engine (already implemented).
**Acceptance Criteria for PyInstaller**:
- [ ] Builds without `--hidden-import` errors
- [ ] Passes macOS notarization
- [ ] Startup time < 3 seconds
- [ ] Total bundle size < 60 MB

**If PyInstaller proves problematic**: Evaluate Nuitka before considering language change.

---

## Size Budget (Python + PyInstaller Baseline)

| Component | Size (compressed) |
|-----------|-------------------|
| Tauri GUI | ~8 MB |
| Python runtime | ~25 MB |
| Dependencies (FastAPI, SQLAlchemy, etc.) | ~15 MB |
| Demo data | ~2 MB |
| **Total** | **~50 MB** |

*These are estimates. Actual sizes TBD after build pipeline is established.*

---

## Directory Structure

### macOS

```
/Applications/Greek2English.app/
├── Contents/
│   ├── MacOS/
│   │   └── Greek2English         # GUI binary
│   ├── Resources/
│   │   └── engine/
│   │       ├── redletters        # Standalone engine binary
│   │       ├── _internal/        # Runtime dependencies (if applicable)
│   │       └── demo_data/        # Bundled demo corpus
│   └── Info.plist

~/Library/Application Support/Greek2English/
├── config.toml                   # User configuration
├── engine.db                     # Job database
├── workspaces/                   # Job workspaces
└── logs/                         # Engine logs

~/Library/Caches/Greek2English/
└── sources/                      # Downloaded data (purgeable)

~/Library/Preferences/com.redletters.plist  # GUI preferences
```

### Windows

```
C:\Program Files\Greek2English\
├── Greek2English.exe             # GUI binary
├── engine\
│   ├── redletters.exe           # Standalone engine binary
│   ├── _internal\               # Runtime dependencies (if applicable)
│   └── demo_data\
└── Uninstall.exe

%APPDATA%\Greek2English\
├── config.toml
├── engine.db
├── workspaces\
└── logs\

%LOCALAPPDATA%\Greek2English\
└── sources\                      # Downloaded data
```

### Data Directory Definitions

| Directory | Purpose | Backed Up? | Portable? |
|-----------|---------|------------|-----------|
| App bundle | Executables, static data | No (reinstallable) | No |
| Config dir | User settings, database | Yes | Yes |
| Cache dir | Downloaded sources | No (re-downloadable) | No |
| Workspaces | Job working files | Optional | No |

---

## Engine Bundling (PyInstaller)

### Build Process

```bash
# Build standalone engine binary
pyinstaller \
    --onedir \
    --name redletters \
    --add-data "src/redletters/data:data" \
    --hidden-import uvicorn.logging \
    --hidden-import uvicorn.protocols.http \
    src/redletters/__main__.py
```

### Output Structure

```
dist/redletters/
├── redletters                    # Main binary
├── _internal/                    # Python runtime + dependencies
│   ├── libpython3.11.dylib
│   ├── sqlite3.cpython-311-darwin.so
│   └── ... (all dependencies)
└── data/
    └── demo_corpus.db            # Bundled demo data
```

### Size Budget

| Component | Size (compressed) |
|-----------|-------------------|
| Tauri GUI | ~8 MB |
| Python runtime | ~25 MB |
| Dependencies (FastAPI, SQLAlchemy, etc.) | ~15 MB |
| Demo data | ~2 MB |
| **Total** | **~50 MB** |

---

## Engine Auto-Restart on Upgrade

### Upgrade Scenario

```
1. User downloads Greek2English-1.3.0.dmg
2. Drags to /Applications (overwrites 1.2.0)
3. Engine 1.2.0 is still running
4. GUI 1.3.0 launches, detects version mismatch
5. GUI initiates engine restart
```

### Restart Protocol

```python
# GUI detects version mismatch
if engine_version < gui_required_version:
    # 1. Request graceful shutdown
    response = await fetch("/v1/engine/shutdown", method="POST", json={
        "reason": "upgrade",
        "grace_period_ms": 30000
    })

    # 2. Wait for shutdown (with timeout)
    await wait_for_shutdown(timeout=45)

    # 3. Start new engine
    spawn_engine(new_engine_path)

    # 4. Wait for ready
    await wait_for_ready(timeout=30)
```

### Job Handling During Upgrade

| Job State | Behavior |
|-----------|----------|
| `running` | Complete current phase, then stop |
| `queued` | Preserved in database, resume after restart |
| `draft` | Preserved in GUI memory (not saved yet) |

```python
# Engine graceful shutdown
async def shutdown(reason: str, grace_period_ms: int):
    # 1. Stop accepting new jobs
    job_queue.pause()

    # 2. Emit shutdown warning
    emit_event("engine.shutting_down", {
        "reason": reason,
        "grace_period_ms": grace_period_ms
    })

    # 3. Wait for current job phase to complete
    if current_job:
        await current_job.wait_for_checkpoint(timeout=grace_period_ms)

    # 4. Save state
    await save_all_state()

    # 5. Exit
    sys.exit(0)
```

---

## Compatibility Policy

### Versioning Scheme

```
MAJOR.MINOR.PATCH

Examples:
1.0.0 → 1.0.1  (patch: bug fixes, always compatible)
1.0.0 → 1.1.0  (minor: new features, backward compatible)
1.0.0 → 2.0.0  (major: breaking changes, migration required)
```

### Compatibility Matrix

| GUI Version | Engine Version | Compatibility |
|-------------|----------------|---------------|
| 1.x | 1.x | ✅ Full compatibility |
| 1.x | 0.x | ❌ Blocked (upgrade required) |
| 1.3 | 1.1 | ⚠️ GUI warns, read-only mode |
| 1.1 | 1.3 | ✅ Compatible (engine newer) |
| 2.x | 1.x | ❌ Blocked (major mismatch) |

### Version Check Flow

```typescript
// GUI startup
async function checkEngineVersion() {
    const status = await fetch("/v1/engine/status");
    const { engine_version, api_version } = await status.json();

    const guiMajor = parseMajor(GUI_VERSION);
    const engineMajor = parseMajor(engine_version);

    if (guiMajor !== engineMajor) {
        showBlockingUpgradeDialog();
        return;
    }

    const guiMinor = parseMinor(GUI_VERSION);
    const engineMinor = parseMinor(engine_version);

    if (guiMinor > engineMinor) {
        showWarning("Engine outdated. Some features may not work.");
    }
}
```

---

## Signing & Notarization

### macOS

#### Code Signing

```bash
# Sign all binaries
codesign --deep --force --verify --verbose \
    --sign "Developer ID Application: Red Letters (XXXXXXXXXX)" \
    --options runtime \
    --entitlements entitlements.plist \
    Greek2English.app
```

**Entitlements** (`entitlements.plist`):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "...">
<plist version="1.0">
<dict>
    <!-- Network access for localhost API -->
    <key>com.apple.security.network.client</key>
    <true/>

    <!-- Read/write user documents -->
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>

    <!-- Keychain access for auth token -->
    <key>com.apple.security.keychain</key>
    <true/>

    <!-- Hardened runtime (required for notarization) -->
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
</dict>
</plist>
```

#### Notarization

```bash
# Create DMG
hdiutil create -volname "Greek2English" \
    -srcfolder dist/ \
    -ov -format UDZO \
    Greek2English-1.2.0-macos.dmg

# Sign DMG
codesign --sign "Developer ID Application: ..." Greek2English-1.2.0-macos.dmg

# Submit for notarization
xcrun notarytool submit Greek2English-1.2.0-macos.dmg \
    --apple-id "$APPLE_ID" \
    --password "$APP_SPECIFIC_PASSWORD" \
    --team-id "$TEAM_ID" \
    --wait

# Staple ticket
xcrun stapler staple Greek2English-1.2.0-macos.dmg
```

### Windows

#### Code Signing

```powershell
# Sign with EV certificate (requires hardware token)
signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 `
    /n "Red Letters" `
    Greek2English.exe

# Also sign engine
signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 `
    /n "Red Letters" `
    engine\redletters.exe
```

#### Installer Signing

```powershell
# Sign MSI or NSIS installer
signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 `
    /n "Red Letters" `
    Greek2English-1.2.0-setup.exe
```

### Signing Implications

| Without Signing | With Signing |
|-----------------|--------------|
| macOS: "Unidentified developer" warning | Clean install experience |
| Windows: SmartScreen warning | Trusted publisher |
| Gatekeeper blocks | Passes Gatekeeper |
| Users must bypass security | Professional trust |

**Cost**: ~$99/year (Apple) + ~$300-500/year (Windows EV cert)

---

## Migration Strategy

### Data Migration Triggers

| From | To | Migration Required |
|------|----|--------------------|
| 1.0 | 1.1 | Schema migration (automatic) |
| 1.x | 2.0 | Full migration (export/import) |
| Fresh install | Any | Initial setup |

### Automatic Migration (Minor Versions)

```python
def migrate_on_startup():
    current_version = get_schema_version()
    target_version = CURRENT_SCHEMA_VERSION

    if current_version == target_version:
        return  # No migration needed

    if current_version > target_version:
        raise MigrationError("Database is from newer version. Upgrade app.")

    # Run migrations sequentially
    for version in range(current_version + 1, target_version + 1):
        log.info(f"Migrating schema to version {version}")
        run_migration(version)
        set_schema_version(version)

    log.info(f"Migration complete. Schema at version {target_version}")
```

### Major Version Migration (2.0)

For breaking changes:

1. **Export Command**:
   ```bash
   redletters migrate export --output ~/greek2english-backup/
   ```
   Creates:
   - `jobs.json` (all job metadata + receipts)
   - `config.toml` (user settings)
   - `sources/` (downloaded data)

2. **Import Command** (in new version):
   ```bash
   redletters migrate import --from ~/greek2english-backup/
   ```

3. **GUI Migration Wizard**:
   ```
   ┌─────────────────────────────────────────────────────────┐
   │ Greek2English 2.0 Migration                             │
   ├─────────────────────────────────────────────────────────┤
   │                                                         │
   │  We found data from version 1.x that needs migration.   │
   │                                                         │
   │  What would you like to do?                             │
   │                                                         │
   │  ○ Migrate my data (recommended)                        │
   │    Your jobs, settings, and sources will be imported.   │
   │                                                         │
   │  ○ Start fresh                                          │
   │    Begin with a clean installation.                     │
   │                                                         │
   │  ○ Keep old version                                     │
   │    Run 1.x and 2.0 side-by-side.                       │
   │                                                         │
   │                              [Continue]                 │
   └─────────────────────────────────────────────────────────┘
   ```

---

## Update Mechanism

### Phase 1: Manual Updates (MVP)

1. User downloads new installer from website
2. Runs installer (overwrites old version)
3. GUI detects version change on launch
4. Migration runs if needed

### Phase 2: Update Notifications (Post-MVP)

```python
# Check for updates on startup (opt-in)
async def check_for_updates():
    response = await fetch("https://api.redletters.app/v1/releases/latest")
    latest = response.json()

    if version_compare(latest["version"], CURRENT_VERSION) > 0:
        emit_notification({
            "title": "Update Available",
            "body": f"Version {latest['version']} is available. "
                    f"Download from {latest['url']}",
            "action": {"label": "Download", "url": latest["url"]}
        })
```

### Phase 3: Auto-Updates (Future)

Consider Tauri's built-in updater or Sparkle (macOS) / WinSparkle (Windows).

---

## Build & Release Pipeline

### CI/CD Workflow

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags: ['v*']

jobs:
  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Engine (PyInstaller)
        run: |
          pip install pyinstaller
          pyinstaller --onedir --name redletters ...

      - name: Build GUI (Tauri)
        run: |
          npm install
          npm run tauri build

      - name: Sign & Notarize
        env:
          APPLE_CERTIFICATE: ${{ secrets.APPLE_CERTIFICATE }}
          APPLE_ID: ${{ secrets.APPLE_ID }}
        run: ./scripts/sign-macos.sh

      - name: Upload Artifact
        uses: actions/upload-artifact@v4
        with:
          name: macos-dmg
          path: target/release/bundle/dmg/*.dmg

  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Engine (PyInstaller)
        run: |
          pip install pyinstaller
          pyinstaller --onedir --name redletters ...

      - name: Build GUI (Tauri)
        run: |
          npm install
          npm run tauri build

      - name: Sign
        env:
          WINDOWS_CERT: ${{ secrets.WINDOWS_CERT }}
        run: ./scripts/sign-windows.ps1

      - name: Upload Artifact
        uses: actions/upload-artifact@v4
        with:
          name: windows-installer
          path: target/release/bundle/msi/*.msi

  create-release:
    needs: [build-macos, build-windows]
    runs-on: ubuntu-latest
    steps:
      - name: Download Artifacts
        uses: actions/download-artifact@v4

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            macos-dmg/*.dmg
            windows-installer/*.msi
          generate_release_notes: true
```

---

## Consequences

### Positive
- Single installer simplifies distribution
- Bundled Python eliminates dependency issues
- Signed binaries build user trust
- Clean upgrade path with auto-restart

### Negative
- Larger download (~50 MB vs ~20 MB GUI-only)
- Signing requires paid certificates
- PyInstaller can be finicky with some packages

### Risks
- Python bundling may break on edge-case dependencies (test thoroughly)
- Notarization can be slow (plan for CI delays)
- Major version migrations may lose edge-case data (test migration paths)

---

## Related Documents

- [ADR-001](../ADR-001-architecture.md) — CLI-first architecture
- [ADR-005](./ADR-005-local-security-model.md) — Security model
- [Desktop App UX Spec](../specs/desktop-app-ux-architecture-spec.md) — First launch / update UX
