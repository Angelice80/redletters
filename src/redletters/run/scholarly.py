"""Scholarly run orchestration (v0.13.0).

Provides deterministic end-to-end scholarly workflow execution:
1. Generate/verify lockfile
2. Build variants for reference
3. Check gates (refuse unless --force)
4. Run translation
5. Export all artifacts (apparatus, translation, citations, quote)
6. Generate snapshot
7. Create bundle with verification
8. Write run log

Design principles:
- Deterministic and transparent
- Refuses on pending gates unless --force
- Full provenance in run log
- Reuses existing primitives
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal

from redletters.export.identifiers import canonical_json, file_hash
from redletters.export.schema_versions import RUNLOG_SCHEMA_VERSION


# Tool version
TOOL_VERSION = "0.13.0"


@dataclass
class RunLogCommand:
    """Command parameters for the run."""

    reference: str
    output_dir: str
    mode: Literal["readable", "traceable"]
    include_schemas: bool = False
    create_zip: bool = False
    force: bool = False

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "reference": self.reference,
            "output_dir": self.output_dir,
            "mode": self.mode,
            "include_schemas": self.include_schemas,
            "create_zip": self.create_zip,
            "force": self.force,
        }


@dataclass
class RunLogFile:
    """A file created during the run."""

    path: str
    artifact_type: str
    sha256: str
    schema_version: str = ""

    def to_dict(self) -> dict:
        """Serialize to dict."""
        result = {
            "path": self.path,
            "artifact_type": self.artifact_type,
            "sha256": self.sha256,
        }
        if self.schema_version:
            result["schema_version"] = self.schema_version
        return result


@dataclass
class RunLogValidation:
    """A validation check performed."""

    check: str
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dict."""
        result = {
            "check": self.check,
            "passed": self.passed,
        }
        if self.errors:
            result["errors"] = self.errors
        if self.warnings:
            result["warnings"] = self.warnings
        return result


@dataclass
class RunLogGates:
    """Gate status information."""

    pending_count: int = 0
    pending_refs: list[str] = field(default_factory=list)
    forced: bool = False
    forced_responsibility: str = ""

    def to_dict(self) -> dict:
        """Serialize to dict."""
        result = {
            "pending_count": self.pending_count,
            "pending_refs": self.pending_refs,
        }
        if self.forced:
            result["forced"] = self.forced
            result["forced_responsibility"] = self.forced_responsibility
        return result


@dataclass
class RunLogPackSummary:
    """Summary of a single pack."""

    pack_id: str
    version: str
    role: str
    license: str = ""

    def to_dict(self) -> dict:
        """Serialize to dict."""
        result = {
            "pack_id": self.pack_id,
            "version": self.version,
            "role": self.role,
        }
        if self.license:
            result["license"] = self.license
        return result


@dataclass
class RunLogPacksSummary:
    """Summary of installed packs."""

    count: int = 0
    packs: list[RunLogPackSummary] = field(default_factory=list)
    lockfile_hash: str = ""

    def to_dict(self) -> dict:
        """Serialize to dict."""
        result = {
            "count": self.count,
            "packs": [p.to_dict() for p in self.packs],
        }
        if self.lockfile_hash:
            result["lockfile_hash"] = self.lockfile_hash
        return result


@dataclass
class RunLog:
    """Deterministic run log for scholarly runs."""

    schema_version: str
    tool_version: str
    command: RunLogCommand
    started_at: str
    completed_at: str
    reference: str
    mode: Literal["readable", "traceable"]
    verse_ids: list[str] = field(default_factory=list)
    packs_summary: RunLogPacksSummary | None = None
    files_created: list[RunLogFile] = field(default_factory=list)
    validations: list[RunLogValidation] = field(default_factory=list)
    gates: RunLogGates | None = None
    success: bool = False
    errors: list[str] = field(default_factory=list)
    content_hash: str = ""

    def to_dict(self) -> dict:
        """Serialize to dict (deterministic key order)."""
        result = {
            "schema_version": self.schema_version,
            "tool_version": self.tool_version,
            "command": self.command.to_dict(),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "reference": self.reference,
            "verse_ids": self.verse_ids,
            "mode": self.mode,
        }
        if self.packs_summary:
            result["packs_summary"] = self.packs_summary.to_dict()
        result["files_created"] = [f.to_dict() for f in self.files_created]
        result["validations"] = [v.to_dict() for v in self.validations]
        if self.gates:
            result["gates"] = self.gates.to_dict()
        result["success"] = self.success
        if self.errors:
            result["errors"] = self.errors
        if self.content_hash:
            result["content_hash"] = self.content_hash
        return result

    def to_json(self, pretty: bool = True) -> str:
        """Serialize to JSON string."""
        if pretty:
            return json.dumps(
                self.to_dict(),
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
        return canonical_json(self.to_dict())

    def compute_content_hash(self) -> str:
        """Compute deterministic hash of all file hashes."""
        sorted_files = sorted(self.files_created, key=lambda f: f.path)
        hash_concat = "".join(f.sha256 for f in sorted_files)
        return hashlib.sha256(hash_concat.encode("utf-8")).hexdigest()

    def save(self, path: Path) -> None:
        """Save run log to JSON file."""
        self.content_hash = self.compute_content_hash()
        path.write_text(self.to_json(pretty=True), encoding="utf-8")

    @classmethod
    def from_dict(cls, data: dict) -> "RunLog":
        """Deserialize from dict."""
        command = RunLogCommand(
            reference=data["command"]["reference"],
            output_dir=data["command"]["output_dir"],
            mode=data["command"]["mode"],
            include_schemas=data["command"].get("include_schemas", False),
            create_zip=data["command"].get("create_zip", False),
            force=data["command"].get("force", False),
        )

        packs_summary = None
        if "packs_summary" in data:
            ps = data["packs_summary"]
            packs_summary = RunLogPacksSummary(
                count=ps["count"],
                packs=[
                    RunLogPackSummary(
                        pack_id=p["pack_id"],
                        version=p["version"],
                        role=p["role"],
                        license=p.get("license", ""),
                    )
                    for p in ps["packs"]
                ],
                lockfile_hash=ps.get("lockfile_hash", ""),
            )

        gates = None
        if "gates" in data:
            g = data["gates"]
            gates = RunLogGates(
                pending_count=g.get("pending_count", 0),
                pending_refs=g.get("pending_refs", []),
                forced=g.get("forced", False),
                forced_responsibility=g.get("forced_responsibility", ""),
            )

        return cls(
            schema_version=data["schema_version"],
            tool_version=data["tool_version"],
            command=command,
            started_at=data["started_at"],
            completed_at=data["completed_at"],
            reference=data["reference"],
            verse_ids=data.get("verse_ids", []),
            mode=data["mode"],
            packs_summary=packs_summary,
            files_created=[
                RunLogFile(
                    path=f["path"],
                    artifact_type=f["artifact_type"],
                    sha256=f["sha256"],
                    schema_version=f.get("schema_version", ""),
                )
                for f in data.get("files_created", [])
            ],
            validations=[
                RunLogValidation(
                    check=v["check"],
                    passed=v["passed"],
                    errors=v.get("errors", []),
                    warnings=v.get("warnings", []),
                )
                for v in data.get("validations", [])
            ],
            gates=gates,
            success=data["success"],
            errors=data.get("errors", []),
            content_hash=data.get("content_hash", ""),
        )


@dataclass
class ScholarlyRunResult:
    """Result of a scholarly run."""

    success: bool
    run_log: RunLog | None = None
    output_dir: Path | None = None
    bundle_path: Path | None = None
    errors: list[str] = field(default_factory=list)
    gate_blocked: bool = False
    gate_refs: list[str] = field(default_factory=list)
    cancelled: bool = False  # Sprint 18: True if run was cancelled


class ScholarlyRunner:
    """Orchestrates end-to-end scholarly runs.

    Usage:
        runner = ScholarlyRunner(data_root="/path/to/data")
        result = runner.run(
            reference="John 1:1-18",
            output_dir=Path("out/run"),
            mode="traceable",
            include_schemas=True,
            create_zip=True,
        )

    The runner:
    1. Generates/verifies lockfile from installed packs
    2. Checks for pending gates (refuses unless force=True)
    3. Runs translation for the reference
    4. Exports all artifacts (apparatus, translation, citations, quote)
    5. Creates snapshot with file hashes
    6. Packages everything into a bundle
    7. Verifies the bundle integrity
    8. Writes deterministic run_log.json
    """

    def __init__(
        self,
        data_root: str | Path | None = None,
        session_id: str = "scholarly-run",
        progress_callback: Callable[[str, str | None], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ):
        """Initialize runner.

        Args:
            data_root: Override data root directory for packs
            session_id: Session ID for gate acknowledgements
            progress_callback: Optional callback for progress updates (Sprint 18).
                              Called with (stage_name, message) for each stage.
            cancel_check: Optional callback that returns True if cancellation requested.
                         Checked between stages for clean shutdown.
        """
        self.data_root = Path(data_root) if data_root else None
        self.session_id = session_id
        self._progress_callback = progress_callback
        self._cancel_check = cancel_check

    def _emit_progress(self, stage: str, message: str | None = None) -> None:
        """Emit progress update if callback is set."""
        if self._progress_callback:
            self._progress_callback(stage, message)

    def _check_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        if self._cancel_check:
            return self._cancel_check()
        return False

    def _make_cancelled_result(self) -> ScholarlyRunResult:
        """Create a cancelled result."""
        return ScholarlyRunResult(
            success=False,
            cancelled=True,
            errors=["Run cancelled by user"],
        )

    def run(
        self,
        reference: str,
        output_dir: Path,
        mode: Literal["readable", "traceable"] = "traceable",
        include_schemas: bool = False,
        create_zip: bool = False,
        force: bool = False,
    ) -> ScholarlyRunResult:
        """Execute a complete scholarly run.

        Args:
            reference: Scripture reference (e.g., "John 1:1-18")
            output_dir: Output directory for all artifacts
            mode: Translation mode (readable or traceable)
            include_schemas: Whether to include JSON schemas in bundle
            create_zip: Whether to create zip archive
            force: Whether to bypass pending gates (records responsibility)

        Returns:
            ScholarlyRunResult with success status and details
        """
        started_at = datetime.now(timezone.utc).isoformat()
        errors: list[str] = []
        files_created: list[RunLogFile] = []
        validations: list[RunLogValidation] = []

        # Create command record
        command = RunLogCommand(
            reference=reference,
            output_dir=str(output_dir),
            mode=mode,
            include_schemas=include_schemas,
            create_zip=create_zip,
            force=force,
        )

        # Create output directory
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Import dependencies
        from redletters.config import Settings
        from redletters.db.connection import get_connection
        from redletters.pipeline.passage_ref import normalize_reference, PassageRefError
        from redletters.sources.installer import SourceInstaller
        from redletters.sources.lockfile import LockfileGenerator
        from redletters.export.snapshot import SnapshotGenerator
        from redletters.export.bundle import BundleCreator, BundleVerifier
        from redletters.export.validator import OutputValidator

        # Create installer early (used for lockfile, spine check, and citations)
        installer = SourceInstaller(data_root=self.data_root)

        settings = Settings()
        conn = get_connection(settings.db_path)

        # 1. Parse reference
        try:
            normalized_ref, verse_ids = normalize_reference(reference)
        except PassageRefError as e:
            errors.append(f"Reference parse error: {e}")
            conn.close()
            return self._build_error_result(
                command, started_at, reference, mode, errors
            )

        # 2. Generate lockfile
        self._emit_progress("lockfile", "Generating lockfile from installed packs")
        lockfile_path = output_dir / "lockfile.json"
        try:
            lockfile_gen = LockfileGenerator(data_root=self.data_root)
            lockfile = lockfile_gen.save(lockfile_path)

            files_created.append(
                RunLogFile(
                    path="lockfile.json",
                    artifact_type="lockfile",
                    sha256=file_hash(str(lockfile_path)),
                    schema_version="1.0.0",
                )
            )

            packs_summary = RunLogPacksSummary(
                count=len(lockfile.packs),
                packs=[
                    RunLogPackSummary(
                        pack_id=p.pack_id,
                        version=p.version,
                        role=p.role,
                        license=p.license,
                    )
                    for p in lockfile.packs
                ],
                lockfile_hash=lockfile.lockfile_hash,
            )

            validations.append(
                RunLogValidation(
                    check="lockfile_generation",
                    passed=True,
                )
            )
        except Exception as e:
            errors.append(f"Lockfile generation failed: {e}")
            conn.close()
            return self._build_error_result(
                command, started_at, reference, mode, errors
            )

        # Check for cancellation after lockfile
        if self._check_cancelled():
            conn.close()
            return self._make_cancelled_result()

        # 3. Check for pending gates
        from redletters.gates.state import AcknowledgementStore
        from redletters.variants.store import VariantStore

        ack_store = AcknowledgementStore(conn)
        variant_store = VariantStore(conn)

        try:
            ack_store.init_schema()
        except Exception:
            pass

        try:
            variant_store.init_schema()
        except Exception:
            pass

        self._emit_progress("gates_check", "Checking for pending gates")
        ack_state = ack_store.load_session_state(self.session_id)

        # Check for significant variants that need acknowledgement
        pending_gates: list[str] = []
        for verse_id in verse_ids:
            variants = variant_store.get_variants_for_verse(verse_id)
            for v in variants:
                if v.is_significant and not ack_state.has_acknowledged_variant(v.ref):
                    pending_gates.append(v.ref)

        gates = RunLogGates(
            pending_count=len(pending_gates),
            pending_refs=pending_gates,
        )

        if pending_gates and not force:
            # Refuse to proceed - gate blocked
            conn.close()
            return ScholarlyRunResult(
                success=False,
                gate_blocked=True,
                gate_refs=pending_gates,
                errors=[
                    f"Blocked by {len(pending_gates)} pending gate(s): {', '.join(pending_gates[:5])}. "
                    "Use --force to proceed with responsibility recorded."
                ],
            )

        if pending_gates and force:
            gates.forced = True
            gates.forced_responsibility = (
                f"User bypassed {len(pending_gates)} pending gate(s) with --force at "
                f"{datetime.now(timezone.utc).isoformat()}. "
                f"Pending refs: {', '.join(pending_gates)}"
            )

        validations.append(
            RunLogValidation(
                check="gate_check",
                passed=len(pending_gates) == 0 or force,
                warnings=[f"Pending gate: {ref}" for ref in pending_gates]
                if pending_gates
                else [],
            )
        )

        # Check for cancellation after gates
        if self._check_cancelled():
            conn.close()
            return self._make_cancelled_result()

        # 4. Run translation
        self._emit_progress("translate", f"Translating {normalized_ref}")
        from redletters.pipeline import (
            translate_passage,
            GateResponsePayload,
            get_translator,
        )
        from redletters.sources import InstalledSpineProvider

        # Set up spine provider
        spine_provider = None

        for spine_id in ["morphgnt-sblgnt", "open-greek-nt"]:
            if installer.is_installed(spine_id):
                spine_provider = InstalledSpineProvider(
                    source_id=spine_id,
                    data_root=self.data_root,
                    require_installed=True,
                )
                break

        if spine_provider is None:
            errors.append(
                "No spine data installed. Install morphgnt-sblgnt or open-greek-nt first."
            )
            conn.close()
            return self._build_error_result(
                command,
                started_at,
                reference,
                mode,
                errors,
                packs_summary,
                gates,
                validations,
            )

        # Get translator
        translator_type = "traceable" if mode == "traceable" else "literal"
        translator_instance = get_translator(
            translator_type=translator_type,
            source_id=spine_provider.source_key
            if hasattr(spine_provider, "source_key")
            else "unknown",
            source_license="",
        )

        options = {"spine_provider": spine_provider}

        try:
            result = translate_passage(
                conn=conn,
                reference=reference,
                mode=mode,
                session_id=self.session_id,
                options=options,
                translator=translator_instance,
            )

            # Check if gate response (should not happen if we checked gates above)
            if isinstance(result, GateResponsePayload):
                errors.append(f"Unexpected gate response: {result.message}")
                conn.close()
                return self._build_error_result(
                    command,
                    started_at,
                    reference,
                    mode,
                    errors,
                    packs_summary,
                    gates,
                    validations,
                )

            validations.append(RunLogValidation(check="translation", passed=True))
        except Exception as e:
            errors.append(f"Translation failed: {e}")
            conn.close()
            return self._build_error_result(
                command,
                started_at,
                reference,
                mode,
                errors,
                packs_summary,
                gates,
                validations,
            )

        # Check for cancellation after translation
        if self._check_cancelled():
            conn.close()
            return self._make_cancelled_result()

        # 5. Export artifacts
        self._emit_progress("export_apparatus", "Exporting apparatus")
        from redletters.export.apparatus import ApparatusExporter
        from redletters.export.translation import TranslationExporter
        from redletters.export.citations import CitationsExporter
        from redletters.export.schema_versions import (
            EXPORT_SCHEMA_VERSION,
            CITATIONS_SCHEMA_VERSION,
            QUOTE_SCHEMA_VERSION,
        )

        # 5a. Export apparatus
        apparatus_path = output_dir / "apparatus.jsonl"
        try:
            apparatus_exporter = ApparatusExporter(variant_store)
            apparatus_exporter.export_to_file(
                reference=normalized_ref,
                output_path=apparatus_path,
            )
            files_created.append(
                RunLogFile(
                    path="apparatus.jsonl",
                    artifact_type="apparatus",
                    sha256=file_hash(str(apparatus_path)),
                    schema_version=EXPORT_SCHEMA_VERSION,
                )
            )
            validations.append(RunLogValidation(check="apparatus_export", passed=True))
        except Exception as e:
            errors.append(f"Apparatus export failed: {e}")
            validations.append(
                RunLogValidation(
                    check="apparatus_export", passed=False, errors=[str(e)]
                )
            )

        # 5b. Export translation (uses ledger from translate result)
        self._emit_progress("export_translation", "Exporting translation")
        translation_path = output_dir / "translation.jsonl"
        try:
            translation_exporter = TranslationExporter()
            # Get ledger from translate result (convert VerseLedger objects to dicts)
            raw_ledger = (
                result.ledger if hasattr(result, "ledger") and result.ledger else []
            )
            # Convert VerseLedger dataclass objects to dicts if needed
            ledger_data = [
                v.to_dict() if hasattr(v, "to_dict") else v for v in raw_ledger
            ]
            if ledger_data:
                translation_exporter.export_to_file(
                    ledger_data=ledger_data,
                    output_path=translation_path,
                    reference=normalized_ref,
                )
                files_created.append(
                    RunLogFile(
                        path="translation.jsonl",
                        artifact_type="translation",
                        sha256=file_hash(str(translation_path)),
                        schema_version=EXPORT_SCHEMA_VERSION,
                    )
                )
                validations.append(
                    RunLogValidation(check="translation_export", passed=True)
                )
            else:
                # No ledger data - create minimal translation file from result
                self._export_minimal_translation(
                    result=result,
                    output_path=translation_path,
                    reference=normalized_ref,
                )
                files_created.append(
                    RunLogFile(
                        path="translation.jsonl",
                        artifact_type="translation",
                        sha256=file_hash(str(translation_path)),
                        schema_version=EXPORT_SCHEMA_VERSION,
                    )
                )
                validations.append(
                    RunLogValidation(
                        check="translation_export",
                        passed=True,
                        warnings=["Used minimal translation export (no ledger data)"],
                    )
                )
        except Exception as e:
            errors.append(f"Translation export failed: {e}")
            validations.append(
                RunLogValidation(
                    check="translation_export", passed=False, errors=[str(e)]
                )
            )

        # 5c. Export citations
        self._emit_progress("export_citations", "Exporting citations")
        citations_path = output_dir / "citations.json"
        try:
            citations_exporter = CitationsExporter(
                conn=conn, data_root=str(self.data_root) if self.data_root else None
            )
            citations_exporter.export_to_file(output_path=citations_path, format="full")
            files_created.append(
                RunLogFile(
                    path="citations.json",
                    artifact_type="citations",
                    sha256=file_hash(str(citations_path)),
                    schema_version=CITATIONS_SCHEMA_VERSION,
                )
            )
            validations.append(RunLogValidation(check="citations_export", passed=True))
        except Exception as e:
            errors.append(f"Citations export failed: {e}")
            validations.append(
                RunLogValidation(
                    check="citations_export", passed=False, errors=[str(e)]
                )
            )

        # 5d. Export quote
        self._emit_progress("export_quote", "Exporting quote")
        quote_path = output_dir / "quote.json"
        try:
            self._export_quote(
                result=result,
                output_path=quote_path,
                reference=normalized_ref,
                mode=mode,
                force=force,
                pending_gates=pending_gates,
            )
            files_created.append(
                RunLogFile(
                    path="quote.json",
                    artifact_type="quote",
                    sha256=file_hash(str(quote_path)),
                    schema_version=QUOTE_SCHEMA_VERSION,
                )
            )
            validations.append(RunLogValidation(check="quote_export", passed=True))
        except Exception as e:
            errors.append(f"Quote export failed: {e}")
            validations.append(
                RunLogValidation(check="quote_export", passed=False, errors=[str(e)])
            )

        # 6. Validate outputs
        validator = OutputValidator()
        for fc in files_created:
            if fc.artifact_type in ("lockfile", "schema"):
                continue
            file_path = output_dir / fc.path
            val_result = validator.validate_file(
                file_path, artifact_type=fc.artifact_type
            )
            if not val_result.valid:
                validations.append(
                    RunLogValidation(
                        check=f"validate_{fc.artifact_type}",
                        passed=False,
                        errors=val_result.errors,
                        warnings=val_result.warnings,
                    )
                )
            else:
                validations.append(
                    RunLogValidation(
                        check=f"validate_{fc.artifact_type}",
                        passed=True,
                        warnings=val_result.warnings,
                    )
                )

        # 7. Generate snapshot
        self._emit_progress("snapshot", "Creating snapshot")
        snapshot_path = output_dir / "snapshot.json"
        try:
            export_files = [
                output_dir / fc.path
                for fc in files_created
                if fc.artifact_type not in ("lockfile", "snapshot")
            ]
            snapshot_gen = SnapshotGenerator(installer=installer)
            snapshot_gen.save(
                output_path=snapshot_path,
                export_files=export_files,
                lockfile_path=lockfile_path,
            )
            files_created.append(
                RunLogFile(
                    path="snapshot.json",
                    artifact_type="snapshot",
                    sha256=file_hash(str(snapshot_path)),
                    schema_version=EXPORT_SCHEMA_VERSION,
                )
            )
            validations.append(
                RunLogValidation(check="snapshot_generation", passed=True)
            )
        except Exception as e:
            errors.append(f"Snapshot generation failed: {e}")
            validations.append(
                RunLogValidation(
                    check="snapshot_generation", passed=False, errors=[str(e)]
                )
            )

        # Check for cancellation before bundle
        if self._check_cancelled():
            conn.close()
            return self._make_cancelled_result()

        # 8. Create bundle
        self._emit_progress("bundle", "Creating bundle")
        bundle_dir = output_dir / "bundle"
        try:
            input_paths = [
                output_dir / fc.path
                for fc in files_created
                if fc.artifact_type not in ("lockfile", "snapshot")
            ]
            bundle_creator = BundleCreator()
            bundle_result = bundle_creator.create(
                output_dir=bundle_dir,
                lockfile_path=lockfile_path,
                snapshot_path=snapshot_path,
                input_paths=input_paths,
                include_schemas=include_schemas,
                create_zip=create_zip,
                notes=f"Scholarly run for {normalized_ref} at {started_at}",
            )

            if bundle_result.success:
                validations.append(
                    RunLogValidation(check="bundle_creation", passed=True)
                )
            else:
                errors.extend(bundle_result.errors)
                validations.append(
                    RunLogValidation(
                        check="bundle_creation",
                        passed=False,
                        errors=bundle_result.errors,
                        warnings=bundle_result.warnings,
                    )
                )
        except Exception as e:
            errors.append(f"Bundle creation failed: {e}")
            validations.append(
                RunLogValidation(check="bundle_creation", passed=False, errors=[str(e)])
            )

        # 9. Verify bundle
        try:
            bundle_verifier = BundleVerifier()
            verify_result = bundle_verifier.verify(
                bundle_path=bundle_dir,
                check_snapshot=True,
                check_outputs=True,
            )

            if verify_result.valid:
                validations.append(
                    RunLogValidation(check="bundle_verification", passed=True)
                )
            else:
                errors.extend(verify_result.errors)
                validations.append(
                    RunLogValidation(
                        check="bundle_verification",
                        passed=False,
                        errors=verify_result.errors,
                        warnings=verify_result.warnings,
                    )
                )
        except Exception as e:
            errors.append(f"Bundle verification failed: {e}")
            validations.append(
                RunLogValidation(
                    check="bundle_verification", passed=False, errors=[str(e)]
                )
            )

        conn.close()

        # 10. Build and save run log
        self._emit_progress("finalize", "Writing run log")
        completed_at = datetime.now(timezone.utc).isoformat()
        success = len([e for e in errors if "failed" in e.lower()]) == 0

        run_log = RunLog(
            schema_version=RUNLOG_SCHEMA_VERSION,
            tool_version=TOOL_VERSION,
            command=command,
            started_at=started_at,
            completed_at=completed_at,
            reference=normalized_ref,
            verse_ids=verse_ids,
            mode=mode,
            packs_summary=packs_summary,
            files_created=files_created,
            validations=validations,
            gates=gates,
            success=success,
            errors=[e for e in errors if e],
        )

        run_log_path = output_dir / "run_log.json"
        run_log.save(run_log_path)

        files_created.append(
            RunLogFile(
                path="run_log.json",
                artifact_type="runlog",
                sha256=file_hash(str(run_log_path)),
                schema_version=RUNLOG_SCHEMA_VERSION,
            )
        )

        return ScholarlyRunResult(
            success=success,
            run_log=run_log,
            output_dir=output_dir,
            bundle_path=bundle_dir,
            errors=errors,
        )

    def _export_quote(
        self,
        result,
        output_path: Path,
        reference: str,
        mode: str,
        force: bool,
        pending_gates: list[str],
    ) -> None:
        """Export quote.json with translation and gate status."""
        from redletters.export.schema_versions import QUOTE_SCHEMA_VERSION
        from redletters.export.identifiers import content_hash

        quote_data = {
            "schema_version": QUOTE_SCHEMA_VERSION,
            "reference": reference,
            "mode": mode,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sblgnt_text": result.sblgnt_text,
            "translation_text": result.translation_text,
            "gate_status": {
                "gates_cleared": len(pending_gates) == 0 or force,
                "pending_count": len(pending_gates),
                "pending_refs": pending_gates,
                "forced": force and len(pending_gates) > 0,
            },
            "confidence": result.confidence.to_dict() if result.confidence else None,
            "verse_ids": result.verse_ids,
        }

        # Add forced_responsibility if applicable
        if force and pending_gates:
            quote_data["gate_status"]["forced_responsibility"] = (
                f"User bypassed {len(pending_gates)} pending gate(s) with --force. "
                f"Pending refs: {', '.join(pending_gates)}"
            )

        # Compute content hash
        quote_data["content_hash"] = content_hash(
            f"{reference}:{result.sblgnt_text}:{result.translation_text}"
        )

        output_path.write_text(
            json.dumps(quote_data, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )

    def _export_minimal_translation(
        self,
        result,
        output_path: Path,
        reference: str,
    ) -> None:
        """Export minimal translation when no ledger data is available.

        Creates a simple JSONL file with verse-level translation data.
        """
        from redletters.export.schema_versions import EXPORT_SCHEMA_VERSION

        with open(output_path, "w", encoding="utf-8") as f:
            for vid in result.verse_ids:
                # Find verse block if available
                verse_block = None
                if hasattr(result, "verse_blocks") and result.verse_blocks:
                    for vb in result.verse_blocks:
                        if vb.verse_id == vid:
                            verse_block = vb
                            break

                record = {
                    "schema_version": EXPORT_SCHEMA_VERSION,
                    "verse_id": vid,
                    "sblgnt_text": verse_block.sblgnt_text
                    if verse_block
                    else result.sblgnt_text,
                    "translation_text": verse_block.translation_text
                    if verse_block and verse_block.translation_text
                    else result.translation_text,
                    "tokens": verse_block.tokens if verse_block else result.tokens,
                    "confidence_summary": {
                        "composite": result.confidence.composite
                        if result.confidence
                        else 0.5,
                        "weakest_layer": result.confidence.weakest_layer
                        if result.confidence
                        else "unknown",
                    },
                }
                f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    def _build_error_result(
        self,
        command: RunLogCommand,
        started_at: str,
        reference: str,
        mode: str,
        errors: list[str],
        packs_summary: RunLogPacksSummary | None = None,
        gates: RunLogGates | None = None,
        validations: list[RunLogValidation] | None = None,
    ) -> ScholarlyRunResult:
        """Build error result with partial run log."""
        completed_at = datetime.now(timezone.utc).isoformat()

        run_log = RunLog(
            schema_version=RUNLOG_SCHEMA_VERSION,
            tool_version=TOOL_VERSION,
            command=command,
            started_at=started_at,
            completed_at=completed_at,
            reference=reference,
            verse_ids=[],
            mode=mode,
            packs_summary=packs_summary,
            files_created=[],
            validations=validations or [],
            gates=gates,
            success=False,
            errors=errors,
        )

        return ScholarlyRunResult(
            success=False,
            run_log=run_log,
            errors=errors,
        )
