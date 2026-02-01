# SPRINT-3-RECEIPT — Real Data + License-Aware Source Packs + Deterministic Translator

## Forensics

```
Python version: 3.8.10
OS: Darwin 21.6.0 (macOS)
Git SHA: 802659b2ab5f58329a97f3ee2f60a9888e068482
Timestamp: 2026-02-01
```

### Git Status at Completion

```
M pyproject.toml
M sources_catalog.yaml
M src/redletters/__main__.py
M src/redletters/api/models.py
M src/redletters/api/routes.py
M src/redletters/config.py
... (other pre-existing modifications)

?? src/redletters/sources/installer.py   # NEW: License-aware installer
?? tests/test_installer_integration.py   # NEW: Integration tests
```

## Commands Executed

### M — MEASURE

```bash
# Initial test baseline
$ pytest -q
466 passed, 409 warnings in 22.54s

# Current CLI state
$ python -m redletters sources --help
Commands: info, list, validate
# (install/status/uninstall NOT YET AVAILABLE)

# Translate behavior (pre-implementation)
$ python -m redletters translate "John 1:18"
Error: No spine data for John 1:18: No tokens found for John.1.18
```

### A — ASSESS (Tests)

```bash
# Final test suite
$ pytest -q
485 passed, 409 warnings in 21.16s

# New installer tests
$ pytest tests/test_installer_integration.py -v
19 passed in 0.43s

# Lint check (new code)
$ ruff check src/redletters/sources/ src/redletters/pipeline/ tests/test_installer_integration.py
All checks passed!
```

## CLI Demonstrations

### EULA Enforcement

```bash
$ python -m redletters sources install codex-sinaiticus
⚠ EULA Required

Source 'Codex Sinaiticus Transcription' requires EULA acceptance.
License: Academic use
Run with --accept-eula to acknowledge the license terms.
Exit code: 2
```

### Sources Status

```bash
$ python -m redletters sources status
Data Root: /Users/admin/.redletters/data
Manifest: /Users/admin/.redletters/data/installed_sources.json

                           Source Installation Status
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Source ID        ┃ Name              ┃ License       ┃ EULA? ┃ Status        ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━┩
│ morphgnt-sblgnt  │ MorphGNT-SBLGNT   │ CC-BY-SA-3.0  │ No    │ Not installed │
│ strongs-greek    │ Strongs Greek     │ CC0-1.0       │ No    │ Not installed │
│ ubs-dictionary   │ UBS Greek Dict    │ CC-BY-SA-4.0  │ No    │ Not installed │
│ westcott-hort    │ Westcott-Hort     │ Public Domain │ No    │ Not installed │
│ codex-sinaiticus │ Codex Sinaiticus  │ Academic use  │ Yes   │ Not installed │
│ open-greek-nt    │ Open Greek NT     │ MIT           │ No    │ Not installed │
└──────────────────┴───────────────────┴───────────────┴───────┴───────────────┘
```

### Literal Translator Without Spine

```bash
$ python -m redletters translate "John 1:18" --translator literal
Error: No spine data installed.

To use --translator literal, install spine data first:

  redletters sources install morphgnt-sblgnt
  # OR for open-license alternative:
  redletters sources install open-greek-nt
Exit code: 1
```

### Translate Help (Updated)

```bash
$ python -m redletters translate --help
Options:
  -m, --mode [readable|traceable]
  -s, --session TEXT
  --ack TEXT
  -o, --output PATH
  --scenario TEXT
  -t, --translator [fake|literal]    # NEW
  --data-root PATH                   # NEW
  --help
```

## Files Created/Modified

### New Files

| File | Purpose |
|------|---------|
| `src/redletters/sources/installer.py` | License-aware source pack installer |
| `tests/test_installer_integration.py` | Integration tests for installer |
| `docs/SPRINT-3-RECEIPT.md` | This receipt |

### Modified Files

| File | Changes |
|------|---------|
| `src/redletters/__main__.py` | Added install/status/uninstall commands, --translator flag |
| `src/redletters/sources/__init__.py` | Exported new classes |
| `src/redletters/sources/spine.py` | Added InstalledSpineProvider, SpineMissingError, get_installed_spine |
| `src/redletters/pipeline/__init__.py` | Exported LiteralTranslator |
| `src/redletters/pipeline/translator.py` | Added LiteralTranslator, BASIC_GLOSSES, get_translator |
| `src/redletters/pipeline/orchestrator.py` | Updated provenance to include license info |
| `tests/test_pipeline_source_pack.py` | Fixed provenance assertion |
| `tests/integration/test_source_pack_vertical_slice.py` | Fixed provenance assertion |

## Behavior Proofs

### 1. EULA Refusal Without Flag

```python
# From test_installer_integration.py::TestEULAEnforcement::test_eula_source_refused_without_flag
result = installer.install("codex-sinaiticus", accept_eula=False)
assert not result.success
assert result.eula_required
assert result.needs_eula
# PASSED
```

### 2. Permissive License Installs Freely

```python
# From test_installer_integration.py::TestLicenseDetection::test_permissive_licenses_detected
for license_id in ["CC0-1.0", "MIT", "CC-BY-SA-4.0", "Public Domain"]:
    assert not installer.requires_eula(pack)
# PASSED
```

### 3. Actionable Error When Spine Missing

```python
# From test_installer_integration.py::TestSpineMissingError::test_error_includes_install_instructions
error = SpineMissingError("morphgnt-sblgnt")
assert "morphgnt-sblgnt" in str(error)
assert "install" in str(error).lower()
assert "redletters sources install" in str(error)
# PASSED
```

### 4. Literal Translator Produces Glosses

```python
# From test_installer_integration.py::TestLiteralTranslator::test_basic_gloss_generation
result = translator.translate("Θεὸν οὐδεὶς", context)
assert "[" in result.translation_text  # Has glosses
assert len(result.claims) > 0
assert "test-source" in result.claims[0].content  # Has provenance
# PASSED
```

### 5. Provenance Includes Source/License

```python
# From test_installer_integration.py::TestTranslateWithFixtureSpine::test_provenance_includes_spine_source
result = translate_passage(...)
assert "sblgnt" in result.provenance.spine_source.lower()
# PASSED
```

### 6. Readable Mode Enforced (TYPE0-4 Only)

```python
# From test_installer_integration.py::TestLiteralTranslator::test_respects_readable_mode
for claim in result.claims:
    if claim.claim_type_hint is not None:
        assert claim.claim_type_hint <= 4
# PASSED
```

## Definition of Done Checklist

- [x] `redletters sources install` can install source packs
- [x] EULA sources refuse without `--accept-eula`
- [x] `redletters sources status` shows installation state
- [x] `redletters sources uninstall` removes installed sources
- [x] `--translator literal` flag available on translate command
- [x] LiteralTranslator produces token-level glosses
- [x] Missing spine triggers actionable error with instructions
- [x] Provenance includes source ID and license
- [x] All 485 tests pass
- [x] New code passes lint (ruff check)
- [x] No silent fallbacks that hide missing data

## Architecture Summary

### License-Aware Installation Flow

```
sources install <id> [--accept-eula]
        │
        ▼
┌───────────────────┐
│ SourceInstaller   │
│ - requires_eula() │
│ - _do_install()   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ EULA Check        │
│ CC-BY-SA → OK     │
│ Academic → REFUSE │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Install to        │
│ ~/.redletters/    │
│   data/<source>/  │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Update Manifest   │
│ installed_sources │
│   .json           │
└───────────────────┘
```

### Translation with Installed Spine

```
translate "John 1:18" --translator literal
        │
        ▼
┌───────────────────┐
│ Check installed   │
│ spine sources     │
└─────────┬─────────┘
          │ (not found)
          ▼
┌───────────────────┐
│ SpineMissingError │
│ + instructions    │
└───────────────────┘

          │ (found)
          ▼
┌───────────────────┐
│ InstalledSpine    │
│ Provider loads    │
│ verse data        │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ LiteralTranslator │
│ - token glosses   │
│ - TYPE0-4 claims  │
│ - provenance      │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ TranslateResponse │
│ with license info │
└───────────────────┘
```

## Next Steps (Sprint 4)

1. **Test with real MorphGNT data**: Install and validate full NT coverage
2. **OpenGNT integration**: Pin OpenGNT commit and add as alternative spine
3. **Lexicon integration**: Wire Strong's dictionary to enhance LiteralTranslator glosses
4. **Variant building from installed editions**: Build variants on-demand from installed comparative texts

---

**Receipt generated**: 2026-02-01
**Sprint**: 3 — Real Data + License-Aware Source Packs + Deterministic Translator
