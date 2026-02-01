"""Path resolution for source packs and edition files.

Design assumptions:
- Data root defaults to ~/.redletters/data (REDLETTERS_DATA_ROOT env override)
- Source files live under {data_root}/{source_key}/
- For tests, fixtures live under tests/fixtures/ in repo
- Supports both fetched data and local fixtures
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from redletters.sources.catalog import SourceCatalog, SourcePack


@dataclass
class ResolvedSource:
    """A resolved source with verified paths."""

    pack: SourcePack
    root_path: Path
    files: list[Path]
    exists: bool
    missing_files: list[str]

    @property
    def is_complete(self) -> bool:
        """True if all expected files exist."""
        return self.exists and not self.missing_files


class SourceResolver:
    """Resolves source pack paths to filesystem locations.

    Search order:
    1. pack.root_path if set (explicit override)
    2. REDLETTERS_DATA_ROOT env var + source_key
    3. ~/.redletters/data/{source_key}
    4. {repo_root}/tests/fixtures/{source_key} (for fixture packs)
    5. {repo_root}/tests/data/{source_key} (for test data)
    """

    def __init__(
        self,
        catalog: SourceCatalog | None = None,
        data_root: Path | str | None = None,
        repo_root: Path | str | None = None,
    ):
        """Initialize resolver.

        Args:
            catalog: Source catalog (loaded if not provided)
            data_root: Override data root path
            repo_root: Override repo root path
        """
        self.catalog = catalog or SourceCatalog.load()
        self.data_root = self._resolve_data_root(data_root)
        self.repo_root = self._resolve_repo_root(repo_root)

    def _resolve_data_root(self, override: Path | str | None) -> Path:
        """Resolve data root directory."""
        if override:
            return Path(override)

        env_root = os.environ.get("REDLETTERS_DATA_ROOT")
        if env_root:
            return Path(env_root)

        return Path.home() / ".redletters" / "data"

    def _resolve_repo_root(self, override: Path | str | None) -> Path:
        """Resolve repository root directory."""
        if override:
            return Path(override)

        # Walk up from package location
        current = Path(__file__).resolve().parent
        for _ in range(10):
            if (current / ".git").exists() or (current / "pyproject.toml").exists():
                return current
            current = current.parent

        return Path.cwd()

    def resolve(self, source_key: str) -> ResolvedSource:
        """Resolve a source pack to filesystem paths.

        Args:
            source_key: Source identifier from catalog

        Returns:
            ResolvedSource with paths and existence status

        Raises:
            KeyError: If source_key not in catalog
        """
        pack = self.catalog.get(source_key)
        if not pack:
            raise KeyError(f"Source not in catalog: {source_key}")

        # Try multiple locations
        candidates = self._get_candidate_paths(pack)

        for candidate_root in candidates:
            if not candidate_root.exists():
                continue

            # Check if files exist
            files = []
            missing = []

            if pack.files:
                for file_rel in pack.files:
                    file_path = candidate_root / file_rel
                    if file_path.exists():
                        files.append(file_path)
                    else:
                        missing.append(file_rel)
            else:
                # No specific files listed; just check root exists
                pass

            # Return first location with files (or just root if no files listed)
            if files or (not pack.files and candidate_root.exists()):
                return ResolvedSource(
                    pack=pack,
                    root_path=candidate_root,
                    files=files,
                    exists=True,
                    missing_files=missing,
                )

        # Nothing found
        return ResolvedSource(
            pack=pack,
            root_path=candidates[0] if candidates else self.data_root / source_key,
            files=[],
            exists=False,
            missing_files=pack.files,
        )

    def _get_candidate_paths(self, pack: SourcePack) -> list[Path]:
        """Get ordered list of candidate paths to check."""
        candidates = []

        # 1. Explicit root_path override
        if pack.root_path:
            path = Path(pack.root_path)
            if not path.is_absolute():
                path = self.repo_root / path
            candidates.append(path)

        # 2. Data root
        candidates.append(self.data_root / pack.key)

        # 3. Fixtures directory (for tests)
        candidates.append(self.repo_root / "tests" / "fixtures" / pack.key)

        # 4. Test data directory
        candidates.append(self.repo_root / "tests" / "data" / pack.key)

        # 5. Also check for -snapshot suffix (MorphGNT convention)
        if "morphgnt" in pack.key.lower():
            candidates.append(self.repo_root / "tests" / "data" / "morphgnt-snapshot")

        return candidates

    def resolve_spine(self) -> ResolvedSource | None:
        """Resolve the canonical spine source.

        Returns:
            ResolvedSource for spine, or None if not defined
        """
        spine = self.catalog.spine
        if not spine:
            return None
        return self.resolve(spine.key)

    def resolve_all_comparative(self) -> list[ResolvedSource]:
        """Resolve all comparative edition sources.

        Returns:
            List of ResolvedSource for comparative editions
        """
        results = []
        for source in self.catalog.comparative_editions:
            results.append(self.resolve(source.key))
        return results

    def get_fixture_path(self, filename: str) -> Path | None:
        """Get path to a fixture file.

        Args:
            filename: Fixture filename

        Returns:
            Path if found, None otherwise
        """
        fixture_dir = self.repo_root / "tests" / "fixtures"
        path = fixture_dir / filename
        return path if path.exists() else None

    def ensure_data_root(self) -> Path:
        """Ensure data root directory exists."""
        self.data_root.mkdir(parents=True, exist_ok=True)
        return self.data_root
