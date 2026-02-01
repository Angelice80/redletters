# STORY-009: Receipt Generation & Finalization

**Epic**: Desktop App Architecture
**ADRs**: ADR-001 (Receipts as first-class), ADR-004
**Priority**: P0 (Receipt-grade is the differentiator)
**Depends On**: STORY-004 (Job Schema)
**Estimate**: 2 days

---

## User Story

**As a** user who needs audit trails,
**I want** every job to produce an immutable receipt,
**So that** I can prove exactly what inputs, configuration, and sources produced my output.

---

## Acceptance Criteria

### AC-1: Receipt Generation for Completed Jobs
- [ ] On job completion, generate `receipt.json` in workspace
- [ ] Receipt contains all fields from ADR-001 receipt structure
- [ ] Receipt hash (SHA-256 of receipt JSON) stored in database
- [ ] Receipt marked as `final` (immutable)

### AC-2: Receipt Generation for Failed Jobs
- [ ] On job failure, generate partial receipt
- [ ] Receipt status = `partial`
- [ ] Includes: timestamps, environment, config, error details
- [ ] Includes: what WAS completed before failure
- [ ] Does NOT claim outputs that weren't written

### AC-3: Receipt Generation for Cancelled Jobs
- [ ] On job cancellation, generate partial receipt
- [ ] Receipt status = `cancelled`
- [ ] Includes: reason, timestamp, partial outputs (if any)

### AC-4: Immutability Enforcement
- [ ] Receipt JSON written once, never modified
- [ ] Receipt file is read-only (chmod 444)
- [ ] Database stores receipt_hash for verification
- [ ] `GET /v1/jobs/{id}/receipt` returns cached receipt (no regeneration)

### AC-5: Receipt Export
- [ ] `GET /v1/jobs/{id}/receipt` returns JSON
- [ ] Response includes `Content-Disposition` for download
- [ ] Receipt validates against schema
- [ ] Future: Markdown/PDF export (not this story)

### AC-6: Correlation IDs
- [ ] Each job has a unique `run_id` (used for correlation)
- [ ] `run_id` format: `run_<timestamp>_<random>`
- [ ] All events for a job include `run_id`
- [ ] Receipt includes `run_id` for tracing

---

## Technical Design

### Receipt Schema

```python
class ReceiptTimestamps(BaseModel):
    created: datetime
    started: datetime | None
    completed: datetime | None

class ReceiptEnvironment(BaseModel):
    engine_version: str
    build_hash: str
    os: str
    platform: str

class SourcePin(BaseModel):
    source: str
    version: str
    sha256: str

class ReceiptSummary(BaseModel):
    status: Literal["success", "partial", "cancelled", "failed"]
    verses_total: int | None
    verses_processed: int
    renderings_per_verse: int | None
    warnings_count: int
    errors_count: int
    error_code: str | None = None
    error_message: str | None = None

class Receipt(BaseModel):
    receipt_version: str = "1.0"
    receipt_status: Literal["final", "partial", "cancelled"]
    run_id: str
    job_id: str

    timestamps: ReceiptTimestamps
    environment: ReceiptEnvironment
    source_pins: list[SourcePin]
    config_snapshot: dict
    inputs: list[dict]
    outputs: list[dict]  # path, size, sha256
    summary: ReceiptSummary

    receipt_hash: str  # SHA-256 of this receipt (excluding this field)
```

### Receipt Generation

```python
import hashlib
import json
from pathlib import Path

async def generate_receipt(job: Job) -> Receipt:
    receipt = Receipt(
        receipt_version="1.0",
        receipt_status=determine_status(job),
        run_id=job.run_id,
        job_id=job.job_id,

        timestamps=ReceiptTimestamps(
            created=job.created_at,
            started=job.started_at,
            completed=job.completed_at,
        ),
        environment=get_environment_info(),
        source_pins=await get_source_pins(),
        config_snapshot=json.loads(job.config_json),
        inputs=json.loads(job.input_spec_json),
        outputs=await collect_outputs(job),
        summary=build_summary(job),

        receipt_hash="",  # Placeholder
    )

    # Compute hash of receipt (excluding receipt_hash field)
    receipt_dict = receipt.model_dump()
    del receipt_dict["receipt_hash"]
    receipt_json = json.dumps(receipt_dict, sort_keys=True)
    receipt.receipt_hash = f"sha256:{hashlib.sha256(receipt_json.encode()).hexdigest()}"

    return receipt


async def finalize_receipt(job: Job, receipt: Receipt):
    """Write receipt to workspace and database."""
    workspace = Path(job.workspace_path)
    receipt_path = workspace / "receipt.json"

    # Write to file
    receipt_path.write_text(receipt.model_dump_json(indent=2))

    # Make immutable
    receipt_path.chmod(0o444)

    # Store in database
    await db.execute("""
        UPDATE jobs
        SET receipt_json = ?, receipt_hash = ?
        WHERE job_id = ?
    """, [receipt.model_dump_json(), receipt.receipt_hash, job.job_id])
```

### Files Changed/Created

- `src/redletters/engine/receipt.py` — Receipt generation and finalization
- `src/redletters/engine/api/receipt.py` — Receipt endpoint
- `src/redletters/engine/schemas/receipt.py` — Pydantic models

---

## Test Plan

| Test | Type | Description |
|------|------|-------------|
| `test_completed_job_generates_receipt` | Integration | Happy path |
| `test_failed_job_generates_partial_receipt` | Integration | Error case |
| `test_cancelled_job_generates_cancelled_receipt` | Integration | Cancel case |
| `test_receipt_hash_is_deterministic` | Unit | Same job → same hash |
| `test_receipt_is_immutable` | Integration | File permissions |
| `test_get_receipt_endpoint` | Integration | API response |
| `test_receipt_includes_all_fields` | Unit | Schema compliance |
| `test_correlation_id_in_receipt` | Unit | run_id present |
| `test_receipt_validates_against_schema` | Unit | JSON Schema validation |

---

## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Tests written and passing
- [ ] Receipt generated for completed/failed/cancelled jobs
- [ ] Receipt file is read-only
- [ ] Receipt hash stored in database
- [ ] API endpoint returns receipt
- [ ] Documentation updated with receipt schema
