"""Citation export for installed packs (v0.7.0).

Exports bibliographic metadata for all installed packs in CSL-JSON format
for scholarly citation and reproducibility.

CSL-JSON format:
- Standard format for citation managers (Zotero, Mendeley, etc.)
- Machine-readable bibliography
- Deterministic output (sorted by role, then pack_id, then version)
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from redletters.export.identifiers import content_hash
from redletters.export.schema_versions import CITATIONS_SCHEMA_VERSION


@dataclass
class CitationEntry:
    """A single citation entry in CSL-JSON format.

    Based on CSL-JSON schema: https://citeproc-js.readthedocs.io/en/latest/csl-json/markup.html
    """

    id: str
    """Unique identifier for the citation (pack_id)."""

    type: str
    """CSL type (book, dataset, software, etc.)."""

    title: str
    """Title of the work."""

    # Optional fields
    author: list[dict] = field(default_factory=list)
    """Authors in CSL format: [{family, given}, ...]."""

    edition: str = ""
    """Edition string."""

    publisher: str = ""
    """Publisher name."""

    issued: dict | None = None
    """Publication date in CSL format: {date-parts: [[year, month, day]]}."""

    URL: str = ""
    """Source URL."""

    license: str = ""
    """License identifier (custom field for Red Letters)."""

    license_url: str = ""
    """License URL (custom field)."""

    version: str = ""
    """Version string (custom field)."""

    pack_role: str = ""
    """Pack role (custom field)."""

    def to_csl_dict(self) -> dict:
        """Convert to CSL-JSON dictionary."""
        result = {
            "id": self.id,
            "type": self.type,
            "title": self.title,
        }

        if self.author:
            result["author"] = self.author
        if self.edition:
            result["edition"] = self.edition
        if self.publisher:
            result["publisher"] = self.publisher
        if self.issued:
            result["issued"] = self.issued
        if self.URL:
            result["URL"] = self.URL
        if self.license:
            result["note"] = f"License: {self.license}"
            # Also add as custom field
            result["x-license"] = self.license
        if self.license_url:
            result["x-license-url"] = self.license_url
        if self.version:
            result["version"] = self.version
        if self.pack_role:
            result["x-pack-role"] = self.pack_role

        return result


@dataclass
class CitationsExport:
    """Complete citations export."""

    schema_version: str
    """Export schema version."""

    export_timestamp: str
    """ISO timestamp of export."""

    entries: list[CitationEntry]
    """Citation entries."""

    content_hash: str = ""
    """Hash of entries for verification."""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "schema_version": self.schema_version,
            "export_timestamp": self.export_timestamp,
            "entries": [e.to_csl_dict() for e in self.entries],
            "entries_count": len(self.entries),
            "content_hash": self.content_hash,
        }

    def to_csl_json(self) -> list[dict]:
        """Convert to pure CSL-JSON array (no metadata wrapper)."""
        return [e.to_csl_dict() for e in self.entries]


class CitationsExporter:
    """Exports citations for installed packs.

    Usage:
        exporter = CitationsExporter(conn)
        result = exporter.export()
        result.to_dict()  # Full export with metadata
        result.to_csl_json()  # Pure CSL-JSON array
    """

    def __init__(
        self,
        conn: sqlite3.Connection | None = None,
        data_root: str | None = None,
    ):
        """Initialize exporter.

        Args:
            conn: Database connection (for sense packs)
            data_root: Override data root for source packs
        """
        self._conn = conn
        self._data_root = data_root

    def _get_source_packs(self) -> list[dict]:
        """Get installed source packs from SourceInstaller."""
        try:
            from redletters.sources.installer import SourceInstaller

            installer = SourceInstaller(data_root=self._data_root)
            status = installer.status()

            packs = []
            for source_id, info in status.get("sources", {}).items():
                if not info.get("installed"):
                    continue

                installed = installer.get_installed(source_id)
                if installed:
                    packs.append(
                        {
                            "pack_id": source_id,
                            "name": installed.name or source_id,
                            "version": installed.version or "",
                            "license": installed.license or "",
                            "role": getattr(installed, "role", "source_text"),
                            # Source packs don't have detailed citation metadata
                            "source_id": source_id,
                            "source_title": installed.name or "",
                            "edition": "",
                            "publisher": "",
                            "year": None,
                            "license_url": "",
                            "source_url": getattr(installed, "repo", "") or "",
                        }
                    )
            return packs
        except Exception:
            return []

    def _get_sense_packs(self) -> list[dict]:
        """Get installed sense packs from database."""
        if self._conn is None:
            return []

        try:
            from redletters.sources.sense_db import SensePackDB

            db = SensePackDB(self._conn)
            db.ensure_schema()

            packs = []
            for pack in db.get_all_installed_packs():
                packs.append(
                    {
                        "pack_id": pack.pack_id,
                        "name": pack.name,
                        "version": pack.version,
                        "license": pack.license,
                        "role": "sense_pack",
                        "source_id": pack.source_id,
                        "source_title": pack.source_title,
                        "edition": pack.edition,
                        "publisher": pack.publisher,
                        "year": pack.year,
                        "license_url": pack.license_url,
                        "source_url": pack.source_url
                        if hasattr(pack, "source_url")
                        else "",
                    }
                )
            return packs
        except Exception:
            return []

    def _pack_to_citation(self, pack: dict) -> CitationEntry:
        """Convert pack info to citation entry."""
        # Determine CSL type based on role
        role = pack.get("role", "")
        if role == "sense_pack":
            csl_type = "book"  # Lexicons are typically books
        elif role in ("source_text", "spine"):
            csl_type = "dataset"  # Text editions
        elif role == "comparative":
            csl_type = "dataset"
        else:
            csl_type = "dataset"

        # Build issued date if year available
        issued = None
        year = pack.get("year")
        if year:
            issued = {"date-parts": [[year]]}

        return CitationEntry(
            id=pack["pack_id"],
            type=csl_type,
            title=pack.get("source_title") or pack.get("name") or pack["pack_id"],
            edition=pack.get("edition", ""),
            publisher=pack.get("publisher", ""),
            issued=issued,
            URL=pack.get("source_url", ""),
            license=pack.get("license", ""),
            license_url=pack.get("license_url", ""),
            version=pack.get("version", ""),
            pack_role=role,
        )

    def export(self) -> CitationsExport:
        """Export citations for all installed packs.

        Returns:
            CitationsExport with all citation entries
        """
        # Collect all packs
        all_packs = []
        all_packs.extend(self._get_source_packs())
        all_packs.extend(self._get_sense_packs())

        # Deduplicate by pack_id (prefer sense pack metadata if available)
        seen = {}
        for pack in all_packs:
            pack_id = pack["pack_id"]
            if pack_id not in seen:
                seen[pack_id] = pack
            elif pack.get("role") == "sense_pack":
                # Sense packs have richer citation metadata
                seen[pack_id] = pack

        # Sort deterministically: by role, then pack_id, then version
        sorted_packs = sorted(
            seen.values(),
            key=lambda p: (p.get("role", ""), p["pack_id"], p.get("version", "")),
        )

        # Convert to citations
        entries = [self._pack_to_citation(p) for p in sorted_packs]

        # Compute content hash (for verification)
        entries_data = [e.to_csl_dict() for e in entries]
        hash_val = content_hash(entries_data)

        return CitationsExport(
            schema_version=CITATIONS_SCHEMA_VERSION,
            export_timestamp=datetime.now(timezone.utc).isoformat(),
            entries=entries,
            content_hash=hash_val,
        )

    def export_to_file(
        self,
        output_path: str | Path,
        format: str = "csljson",
    ) -> dict:
        """Export citations to file.

        Args:
            output_path: Output file path
            format: Output format ("csljson" or "full")

        Returns:
            Dict with export metadata
        """
        result = self.export()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "csljson":
            # Pure CSL-JSON array (standard format)
            data = result.to_csl_json()
        else:
            # Full format with metadata wrapper
            data = result.to_dict()

        # Write with canonical serialization for reproducibility
        output_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )

        return {
            "output_path": str(output_path),
            "format": format,
            "entries_count": len(result.entries),
            "schema_version": result.schema_version,
            "content_hash": result.content_hash,
        }
