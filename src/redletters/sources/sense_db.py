"""Sense pack database operations for v0.6.0.

Handles:
- Schema extension for sense packs with citation-grade provenance
- Loading sense data from installed packs into the database
- Querying senses with provenance information
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from redletters.sources.sense_pack import (
    SensePackLoader,
    SensePackManifest,
)


# Schema for sense pack tracking (v0.6.0)
SENSE_PACK_SCHEMA_SQL = """
-- installed_sense_packs: Track installed sense packs with citation-grade metadata
CREATE TABLE IF NOT EXISTS installed_sense_packs (
    id INTEGER PRIMARY KEY,
    pack_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    license TEXT NOT NULL,
    source_id TEXT NOT NULL,           -- Citation key
    source_title TEXT NOT NULL,        -- Full bibliographic title
    edition TEXT,                      -- Edition string
    publisher TEXT,                    -- Publisher name
    year INTEGER,                      -- Publication year
    license_url TEXT,                  -- Link to license text
    source_url TEXT,                   -- Link to original source
    notes TEXT,
    installed_at TEXT NOT NULL,
    install_path TEXT NOT NULL,
    sense_count INTEGER DEFAULT 0,
    pack_hash TEXT,
    priority INTEGER DEFAULT 0        -- Lower = higher priority for precedence
);

-- pack_senses: Senses from installed sense packs
-- Linked to installed_sense_packs for provenance
CREATE TABLE IF NOT EXISTS pack_senses (
    id INTEGER PRIMARY KEY,
    pack_id TEXT NOT NULL,
    lemma TEXT NOT NULL,
    sense_id TEXT NOT NULL,
    gloss TEXT NOT NULL,
    definition TEXT,
    domain TEXT,
    weight REAL DEFAULT 1.0,
    UNIQUE(pack_id, lemma, sense_id),
    FOREIGN KEY (pack_id) REFERENCES installed_sense_packs(pack_id)
);

-- Indexes for efficient sense lookup
CREATE INDEX IF NOT EXISTS idx_pack_senses_lemma ON pack_senses(lemma);
CREATE INDEX IF NOT EXISTS idx_pack_senses_pack ON pack_senses(pack_id);
"""


def init_sense_pack_schema(conn: sqlite3.Connection) -> None:
    """Initialize sense pack schema.

    Args:
        conn: Database connection
    """
    conn.executescript(SENSE_PACK_SCHEMA_SQL)
    conn.commit()


@dataclass
class InstalledSensePack:
    """Record of an installed sense pack with citation metadata."""

    pack_id: str
    name: str
    version: str
    license: str
    source_id: str
    source_title: str
    edition: str = ""
    publisher: str = ""
    year: int | None = None
    license_url: str = ""
    source_url: str = ""
    notes: str = ""
    installed_at: str = ""
    install_path: str = ""
    sense_count: int = 0
    pack_hash: str = ""
    priority: int = 0

    @classmethod
    def from_manifest(
        cls,
        manifest: SensePackManifest,
        install_path: str,
        pack_hash: str = "",
        priority: int = 0,
    ) -> "InstalledSensePack":
        """Create from manifest."""
        return cls(
            pack_id=manifest.pack_id,
            name=manifest.name,
            version=manifest.version,
            license=manifest.license,
            source_id=manifest.source_id,
            source_title=manifest.source_title,
            edition=manifest.edition,
            publisher=manifest.publisher,
            year=manifest.year,
            license_url=manifest.license_url,
            source_url=manifest.source_url,
            notes=manifest.notes,
            installed_at=datetime.utcnow().isoformat(),
            install_path=install_path,
            sense_count=manifest.sense_count,
            pack_hash=pack_hash,
            priority=priority,
        )

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "pack_id": self.pack_id,
            "name": self.name,
            "version": self.version,
            "license": self.license,
            "source_id": self.source_id,
            "source_title": self.source_title,
            "edition": self.edition,
            "publisher": self.publisher,
            "year": self.year,
            "license_url": self.license_url,
            "source_url": self.source_url,
            "notes": self.notes,
            "installed_at": self.installed_at,
            "install_path": self.install_path,
            "sense_count": self.sense_count,
            "pack_hash": self.pack_hash,
            "priority": self.priority,
        }

    def citation_dict(self) -> dict:
        """Return citation-grade provenance for receipts."""
        result = {
            "source_id": self.source_id,
            "source_title": self.source_title,
            "license": self.license,
        }
        if self.edition:
            result["edition"] = self.edition
        if self.publisher:
            result["publisher"] = self.publisher
        if self.year:
            result["year"] = self.year
        if self.license_url:
            result["license_url"] = self.license_url
        return result


class SensePackDB:
    """Database operations for sense packs.

    Usage:
        db = SensePackDB(conn)
        db.ensure_schema()

        # Install a sense pack
        loader = SensePackLoader(pack_path)
        loader.load()
        db.install_pack(loader, install_path, pack_hash)

        # Query senses
        senses = db.get_senses_for_lemma("λόγος")
    """

    def __init__(self, conn: sqlite3.Connection):
        """Initialize with database connection.

        Args:
            conn: SQLite connection
        """
        self._conn = conn

    def ensure_schema(self) -> None:
        """Ensure sense pack schema exists."""
        init_sense_pack_schema(self._conn)

    def is_pack_installed(self, pack_id: str) -> bool:
        """Check if a sense pack is installed.

        Args:
            pack_id: Pack identifier

        Returns:
            True if installed
        """
        cursor = self._conn.execute(
            "SELECT 1 FROM installed_sense_packs WHERE pack_id = ?",
            (pack_id,),
        )
        return cursor.fetchone() is not None

    def get_installed_pack(self, pack_id: str) -> InstalledSensePack | None:
        """Get installed pack metadata.

        Args:
            pack_id: Pack identifier

        Returns:
            InstalledSensePack or None
        """
        cursor = self._conn.execute(
            """
            SELECT pack_id, name, version, license, source_id, source_title,
                   edition, publisher, year, license_url, source_url, notes,
                   installed_at, install_path, sense_count, pack_hash, priority
            FROM installed_sense_packs
            WHERE pack_id = ?
            """,
            (pack_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        return InstalledSensePack(
            pack_id=row[0],
            name=row[1],
            version=row[2],
            license=row[3],
            source_id=row[4],
            source_title=row[5],
            edition=row[6] or "",
            publisher=row[7] or "",
            year=row[8],
            license_url=row[9] or "",
            source_url=row[10] or "",
            notes=row[11] or "",
            installed_at=row[12],
            install_path=row[13],
            sense_count=row[14],
            pack_hash=row[15] or "",
            priority=row[16],
        )

    def get_all_installed_packs(self) -> list[InstalledSensePack]:
        """Get all installed sense packs.

        Returns:
            List of InstalledSensePack, ordered by priority
        """
        cursor = self._conn.execute(
            """
            SELECT pack_id, name, version, license, source_id, source_title,
                   edition, publisher, year, license_url, source_url, notes,
                   installed_at, install_path, sense_count, pack_hash, priority
            FROM installed_sense_packs
            ORDER BY priority ASC, installed_at ASC
            """
        )

        packs = []
        for row in cursor:
            packs.append(
                InstalledSensePack(
                    pack_id=row[0],
                    name=row[1],
                    version=row[2],
                    license=row[3],
                    source_id=row[4],
                    source_title=row[5],
                    edition=row[6] or "",
                    publisher=row[7] or "",
                    year=row[8],
                    license_url=row[9] or "",
                    source_url=row[10] or "",
                    notes=row[11] or "",
                    installed_at=row[12],
                    install_path=row[13],
                    sense_count=row[14],
                    pack_hash=row[15] or "",
                    priority=row[16],
                )
            )
        return packs

    def install_pack(
        self,
        loader: SensePackLoader,
        install_path: str,
        pack_hash: str = "",
        priority: int | None = None,
    ) -> InstalledSensePack:
        """Install a sense pack into the database.

        Args:
            loader: Loaded SensePackLoader
            install_path: Path where pack is installed
            pack_hash: Hash of pack contents
            priority: Precedence priority (auto-assigned if None)

        Returns:
            InstalledSensePack record
        """
        if not loader.is_loaded:
            loader.load()

        manifest = loader.manifest
        if manifest is None:
            raise ValueError("Loader has no manifest")

        # Auto-assign priority based on install order
        if priority is None:
            cursor = self._conn.execute(
                "SELECT MAX(priority) FROM installed_sense_packs"
            )
            row = cursor.fetchone()
            priority = (row[0] or 0) + 1

        # Remove existing pack data if reinstalling
        if self.is_pack_installed(manifest.pack_id):
            self.uninstall_pack(manifest.pack_id)

        # Insert pack metadata
        self._conn.execute(
            """
            INSERT INTO installed_sense_packs
            (pack_id, name, version, license, source_id, source_title,
             edition, publisher, year, license_url, source_url, notes,
             installed_at, install_path, sense_count, pack_hash, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                manifest.pack_id,
                manifest.name,
                manifest.version,
                manifest.license,
                manifest.source_id,
                manifest.source_title,
                manifest.edition,
                manifest.publisher,
                manifest.year,
                manifest.license_url,
                manifest.source_url,
                manifest.notes,
                datetime.utcnow().isoformat(),
                install_path,
                len(loader),
                pack_hash,
                priority,
            ),
        )

        # Insert senses
        sense_count = 0
        for sense in loader.iter_senses():
            self._conn.execute(
                """
                INSERT OR REPLACE INTO pack_senses
                (pack_id, lemma, sense_id, gloss, definition, domain, weight)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    manifest.pack_id,
                    sense.lemma,
                    sense.sense_id,
                    sense.gloss,
                    sense.definition,
                    sense.domain,
                    sense.weight,
                ),
            )
            sense_count += 1

        # Update sense count
        self._conn.execute(
            "UPDATE installed_sense_packs SET sense_count = ? WHERE pack_id = ?",
            (sense_count, manifest.pack_id),
        )

        self._conn.commit()

        return InstalledSensePack.from_manifest(
            manifest, install_path, pack_hash, priority
        )

    def uninstall_pack(self, pack_id: str) -> bool:
        """Uninstall a sense pack from the database.

        Args:
            pack_id: Pack identifier

        Returns:
            True if uninstalled, False if not found
        """
        if not self.is_pack_installed(pack_id):
            return False

        # Delete senses
        self._conn.execute(
            "DELETE FROM pack_senses WHERE pack_id = ?",
            (pack_id,),
        )

        # Delete pack metadata
        self._conn.execute(
            "DELETE FROM installed_sense_packs WHERE pack_id = ?",
            (pack_id,),
        )

        self._conn.commit()
        return True

    def get_senses_for_lemma(
        self,
        lemma: str,
        pack_ids: list[str] | None = None,
    ) -> list[dict]:
        """Get senses for a lemma with provenance.

        Args:
            lemma: Greek lemma
            pack_ids: Optional list of pack IDs to search (in order)

        Returns:
            List of sense dicts with provenance
        """
        if pack_ids is None:
            # Use all installed packs in priority order
            packs = self.get_all_installed_packs()
            pack_ids = [p.pack_id for p in packs]

        if not pack_ids:
            return []

        # Query senses from packs in specified order
        senses = []
        seen_sense_ids = set()

        for pack_id in pack_ids:
            cursor = self._conn.execute(
                """
                SELECT ps.lemma, ps.sense_id, ps.gloss, ps.definition, ps.domain, ps.weight,
                       isp.source_id, isp.source_title, isp.license, isp.edition,
                       isp.publisher, isp.year, isp.license_url
                FROM pack_senses ps
                JOIN installed_sense_packs isp ON ps.pack_id = isp.pack_id
                WHERE ps.lemma = ? AND ps.pack_id = ?
                ORDER BY ps.weight DESC
                """,
                (lemma, pack_id),
            )

            for row in cursor:
                full_sense_id = f"{row[0]}:{row[1]}"
                if full_sense_id in seen_sense_ids:
                    continue
                seen_sense_ids.add(full_sense_id)

                sense_dict = {
                    "lemma": row[0],
                    "sense_id": row[1],
                    "gloss": row[2],
                    "definition": row[3],
                    "domain": row[4],
                    "weight": row[5],
                    "source_id": row[6],
                    "source_title": row[7],
                    "license": row[8],
                }

                # Add optional citation fields
                if row[9]:  # edition
                    sense_dict["edition"] = row[9]
                if row[10]:  # publisher
                    sense_dict["publisher"] = row[10]
                if row[11]:  # year
                    sense_dict["year"] = row[11]
                if row[12]:  # license_url
                    sense_dict["license_url"] = row[12]

                senses.append(sense_dict)

        return senses

    def get_primary_gloss(
        self,
        lemma: str,
        pack_ids: list[str] | None = None,
    ) -> dict | None:
        """Get highest-weighted gloss for a lemma with provenance.

        Args:
            lemma: Greek lemma
            pack_ids: Optional pack IDs to search

        Returns:
            Sense dict or None
        """
        senses = self.get_senses_for_lemma(lemma, pack_ids)
        if not senses:
            return None

        # Sort by weight and return highest
        senses.sort(key=lambda s: -s.get("weight", 0))
        return senses[0]

    def get_pack_status(self) -> list[dict]:
        """Get status of all installed sense packs.

        Returns:
            List of status dicts for display
        """
        packs = self.get_all_installed_packs()
        return [
            {
                "pack_id": p.pack_id,
                "name": p.name,
                "version": p.version,
                "license": p.license,
                "source_id": p.source_id,
                "source_title": p.source_title,
                "sense_count": p.sense_count,
                "installed_at": p.installed_at,
                "priority": p.priority,
            }
            for p in packs
        ]
