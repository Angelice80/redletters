"""Fetch external data sources at runtime.

Per ADR-002: Data is fetched at install time, not bundled in the repo.
This avoids license composition issues and forces explicit license acceptance.

Supports two fetch modes:
1. PINNED MODE (preferred): Uses sources_catalog.yaml with commit-pinned raw URLs
2. ARCHIVE MODE (legacy): Downloads zip/tar archives from URLs

All fetches produce a .fetched marker with stable key ordering for provenance.
"""

import hashlib
import re
import shutil
import tarfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen, Request
from urllib.error import URLError

import yaml

# Default data directory (can be overridden)
DEFAULT_DATA_DIR = Path.home() / ".redletters" / "data"

# Marker keys in stable order (always written, even if empty)
MARKER_KEYS = [
    "name",
    "version",
    "license",
    "url",
    "retrieved_at",
    "sha256",
    "git_commit",
    "git_tag",
    "files",
    "notes",
]

# Sentinel files to find repo root (in order of preference)
REPO_ROOT_SENTINELS = ["sources_catalog.yaml", "pyproject.toml", ".git"]

# Regex for 40-char hex SHA
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)

# Regex to parse GitHub repo URL (HTTPS only)
GITHUB_REPO_PATTERN = re.compile(
    r"https?://github\.com/(?P<owner>[^/]+)/(?P<project>[^/]+?)(?:\.git)?/?$"
)

# Regex to detect SSH-style GitHub URLs (not supported, but should give clear error)
GITHUB_SSH_PATTERNS = [
    re.compile(r"^git@github\.com:(?P<owner>[^/]+)/(?P<project>.+?)(?:\.git)?$"),
    re.compile(r"^ssh://git@github\.com/(?P<owner>[^/]+)/(?P<project>.+?)(?:\.git)?$"),
]


class CatalogNotFoundError(Exception):
    """Raised when sources_catalog.yaml cannot be found."""

    pass


def find_repo_root(start: Path | None = None) -> Path:
    """Find repository root by walking upward looking for sentinel files.

    Sentinel precedence (checked in order at each directory level):
    1. sources_catalog.yaml (preferred - explicit catalog)
    2. pyproject.toml (Python project root)
    3. .git (repository root)

    In mono-repos with nested projects, returns the NEAREST directory
    containing any sentinel, preferring sources_catalog.yaml at each level.

    Args:
        start: Starting directory (default: directory containing this file)

    Returns:
        Path to repo root

    Raises:
        CatalogNotFoundError: If no sentinel found after walking to filesystem root
    """
    if start is None:
        start = Path(__file__).resolve().parent
    else:
        start = Path(start).resolve()

    current = start
    searched = []

    while current != current.parent:  # Stop at filesystem root
        searched.append(str(current))
        for sentinel in REPO_ROOT_SENTINELS:
            if (current / sentinel).exists():
                return current
        current = current.parent

    raise CatalogNotFoundError(
        f"Cannot find repo root.\n"
        f"\n"
        f"Started from: {start}\n"
        f"\n"
        f"Searched for sentinels {REPO_ROOT_SENTINELS} in:\n"
        + "\n".join(f"  - {p}" for p in searched[:10])
        + ("\n  ... (truncated)" if len(searched) > 10 else "")
        + "\n\n"
        "Resolution options:\n"
        "  1. Run from within the repository\n"
        "  2. Create a sources_catalog.yaml in your project root\n"
        "  3. Pass catalog_path explicitly to the function/CLI"
    )


class UnsupportedURLError(Exception):
    """Raised when a URL format is recognized but not supported."""

    pass


def parse_github_repo_url(url: str) -> tuple[str, str] | None:
    """Parse owner and project from a GitHub repo URL.

    Args:
        url: GitHub URL like https://github.com/owner/project

    Returns:
        Tuple of (owner, project) or None if not a valid GitHub URL

    Raises:
        UnsupportedURLError: If URL is SSH format (recognized but not supported)

    Supported formats:
        - https://github.com/owner/repo
        - https://github.com/owner/repo/
        - https://github.com/owner/repo.git
        - http://github.com/owner/repo (will use HTTPS for raw.githubusercontent.com)

    NOT supported (will raise UnsupportedURLError):
        - git@github.com:owner/repo.git
        - ssh://git@github.com/owner/repo.git
    """
    if not url:
        return None

    # Check for SSH formats first (give explicit error)
    for pattern in GITHUB_SSH_PATTERNS:
        match = pattern.match(url)
        if match:
            owner, project = match.group("owner"), match.group("project")
            raise UnsupportedURLError(
                f"SSH URL format not supported: {url}\n"
                f"Please use HTTPS format instead:\n"
                f"  https://github.com/{owner}/{project}"
            )

    # Try HTTPS format
    match = GITHUB_REPO_PATTERN.match(url.rstrip("/"))
    if match:
        return match.group("owner"), match.group("project")
    return None


def is_full_sha(ref: str | None) -> bool:
    """Check if ref is a full 40-character SHA hash."""
    if not ref:
        return False
    return bool(SHA_PATTERN.match(ref))


@dataclass
class SourceSpec:
    """Specification for an external data source.

    Supports two modes:
    - Pinned mode: repo + commit + files (owner/project derived from repo)
    - Archive mode: url + archive_type + extract_path (legacy)
    """

    name: str
    version: str
    license: str

    # Archive mode (legacy)
    url: str | None = None
    archive_type: str | None = None  # "zip", "tar.gz", or None for raw file
    extract_path: str | None = None  # path within archive to extract

    # Pinned mode (preferred) - repo is canonical, owner/project derived
    repo: str | None = None
    git_commit: str | None = None
    git_tag: str | None = None
    files: list[str] = field(default_factory=list)

    notes: str | None = None

    def _owner_project(self) -> tuple[str, str] | None:
        """Derive owner/project from repo URL."""
        return parse_github_repo_url(self.repo) if self.repo else None

    @property
    def owner(self) -> str | None:
        """Get owner from repo URL."""
        parsed = self._owner_project()
        return parsed[0] if parsed else None

    @property
    def project(self) -> str | None:
        """Get project from repo URL."""
        parsed = self._owner_project()
        return parsed[1] if parsed else None

    def is_pinned(self) -> bool:
        """Check if this spec uses pinned mode (full SHA commit + files + valid repo)."""
        if not (self.git_commit and self.files and self.repo):
            return False
        # Must have valid GitHub URL we can parse
        if not self._owner_project():
            return False
        # Commit must be a full SHA (not abbreviated, not a branch/tag name)
        return is_full_sha(self.git_commit)

    def is_floating(self) -> bool:
        """Check if this spec uses a floating reference.

        Floating refs include:
        - No commit specified
        - Branch names (master, main, etc.)
        - Tag names (even "stable" tags can be moved)
        - Abbreviated SHAs (can be ambiguous)

        Only full 40-char SHA commits are considered non-floating.
        """
        if not self.git_commit:
            return True
        # Only full SHAs are non-floating
        return not is_full_sha(self.git_commit)


# Legacy SOURCES dict - will be populated from catalog
SOURCES: dict[str, SourceSpec] = {}


def load_sources_catalog(
    path: Path | None = None,
    allow_missing: bool = False,
) -> dict:
    """Load sources catalog from YAML file.

    Args:
        path: Path to catalog file. If None, searches for repo root.
        allow_missing: If True, return {} when catalog not found.
                      If False (default), raise CatalogNotFoundError.

    Returns:
        Dict of source_key -> source config

    Raises:
        CatalogNotFoundError: If catalog not found and allow_missing=False
    """
    if path is None:
        try:
            repo_root = find_repo_root()
            path = repo_root / "sources_catalog.yaml"
        except CatalogNotFoundError:
            if allow_missing:
                return {}
            raise

    if not path.exists():
        if allow_missing:
            return {}
        raise CatalogNotFoundError(
            f"Catalog not found at {path}\n"
            "Create sources_catalog.yaml or pass catalog_path explicitly."
        )

    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def catalog_to_source_spec(key: str, config: dict) -> SourceSpec:
    """Convert catalog entry to SourceSpec.

    Note: owner/project are derived from repo URL, not stored separately.
    """
    return SourceSpec(
        name=config.get("name", key),
        version=config.get("version", ""),
        license=config.get("license", ""),
        url=config.get("url"),
        archive_type=config.get("archive_type"),
        extract_path=config.get("extract_path"),
        repo=config.get("repo"),
        git_commit=config.get("commit", config.get("git_commit")),
        git_tag=config.get("git_tag", ""),
        files=config.get("files", []),
        notes=config.get("notes"),
    )


def get_source_spec(source_key: str, catalog_path: Path | None = None) -> SourceSpec:
    """Get SourceSpec from catalog or legacy SOURCES dict.

    Catalog takes precedence over legacy SOURCES.
    """
    catalog = load_sources_catalog(catalog_path)

    if source_key in catalog:
        return catalog_to_source_spec(source_key, catalog[source_key])

    if source_key in SOURCES:
        return SOURCES[source_key]

    raise ValueError(f"Unknown source: {source_key}. Check sources_catalog.yaml")


def list_available_sources(catalog_path: Path | None = None) -> list[str]:
    """List all available source keys."""
    catalog = load_sources_catalog(catalog_path, allow_missing=True)
    return list(catalog.keys()) + [k for k in SOURCES if k not in catalog]


def raw_github_url(owner: str, project: str, commit: str, file_path: str) -> str:
    """Build raw GitHub URL for a specific commit and file.

    No API calls - deterministic URL construction.
    File path is URL-encoded to handle spaces and special characters.
    """
    # URL-encode the file path (but preserve /)
    encoded_path = "/".join(quote(part, safe="") for part in file_path.split("/"))
    return (
        f"https://raw.githubusercontent.com/{owner}/{project}/{commit}/{encoded_path}"
    )


def get_data_dir() -> Path:
    """Get the data directory, creating if needed."""
    data_dir = DEFAULT_DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def sha256_file(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def normalize_path_for_manifest(path: str) -> str:
    """Normalize path for cross-platform manifest stability.

    - Uses forward slashes (POSIX style)
    - Strips leading ./
    """
    normalized = path.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def sha256_of_manifest(file_hashes: list[tuple[str, str]]) -> str:
    """Compute SHA256 of a file manifest (stable across machines).

    Args:
        file_hashes: List of (relative_path, sha256) tuples

    Returns:
        SHA256 hex digest of the manifest

    Note:
        - Paths are normalized to POSIX style for cross-platform stability
        - List is sorted by normalized path
    """
    sha256 = hashlib.sha256()
    # Normalize paths and sort for determinism
    normalized = [(normalize_path_for_manifest(p), h) for p, h in file_hashes]
    for path, hash_val in sorted(normalized):
        sha256.update(f"{path}:{hash_val}\n".encode("utf-8"))
    return sha256.hexdigest()


def _atomic_replace_with_retry(src: Path, dst: Path, max_retries: int = 3) -> None:
    """Atomically replace dst with src, with retry for Windows file locking.

    On Windows, file operations can fail if AV scanners, indexers, or other
    processes have the file open. This adds small retries to handle transient locks.

    Args:
        src: Source file path
        dst: Destination file path
        max_retries: Maximum number of retry attempts

    Raises:
        OSError: If replace fails after all retries
    """
    import sys
    import time

    for attempt in range(max_retries):
        try:
            src.replace(dst)
            return
        except OSError as e:
            # On Windows, EACCES (13) or EBUSY (16) indicate file locking
            # On POSIX these errors shouldn't happen for replace, so fail fast
            if sys.platform != "win32" or attempt == max_retries - 1:
                raise
            # Only retry on Windows permission/busy errors
            if e.errno not in (13, 16):  # EACCES, EBUSY
                raise
            # Exponential backoff: 50ms, 100ms, 200ms
            time.sleep(0.05 * (2**attempt))


def download_to(url: str, out_path: Path, timeout: int = 60) -> None:
    """Download a URL to a file path atomically.

    Writes to a .tmp file first, then renames to avoid partial files.
    Includes retry logic for Windows file locking issues.
    """
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    request = Request(url, headers={"User-Agent": "RedLetters/0.1"})

    try:
        with urlopen(request, timeout=timeout) as response:
            with open(tmp_path, "wb") as f:
                shutil.copyfileobj(response, f)
        # Atomic rename with retry for Windows file locking
        _atomic_replace_with_retry(tmp_path, out_path)
    except Exception:
        # Clean up partial file on failure
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def write_marker(path: Path, meta: dict) -> None:
    """Write .fetched marker with stable key ordering.

    Always writes all MARKER_KEYS, even if empty.
    This ensures consistent marker format for provenance tracking.
    """
    with path.open("w", encoding="utf-8") as f:
        for key in MARKER_KEYS:
            value = meta.get(key, "")
            # Handle None values
            if value is None:
                value = ""
            # Handle list values (files)
            if isinstance(value, list):
                value = ",".join(value)
            f.write(f"{key}={value}\n")


def read_marker(path: Path) -> dict:
    """Read .fetched marker into dict."""
    meta = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    key, value = line.split("=", 1)
                    meta[key] = value
    return meta


def is_path_safe(member_path: str, target_dir: Path) -> bool:
    """Check if archive member path is safe (no path traversal or absolute paths).

    Prevents zip-slip attacks where archives contain:
    - Paths like ../../evil (traversal)
    - Absolute paths like /etc/passwd or C:\\Windows\\...
    - Paths that resolve outside target_dir

    Note: Symlink detection is handled separately in is_member_symlink()
    because it requires archive-specific member info.

    Args:
        member_path: Path from archive member
        target_dir: Directory files will be extracted to

    Returns:
        True if path is safe, False otherwise
    """
    # Reject absolute paths explicitly
    if member_path.startswith("/") or member_path.startswith("\\"):
        return False
    # Windows absolute paths (C:\, D:\, etc.)
    if len(member_path) >= 2 and member_path[1] == ":":
        return False

    # Reject paths with .. components (even if they resolve safely)
    # This catches edge cases and makes intent clear
    normalized = member_path.replace("\\", "/")
    if ".." in normalized.split("/"):
        return False

    # Final check: resolved path must be under target_dir
    full_path = (target_dir / member_path).resolve()
    try:
        full_path.relative_to(target_dir.resolve())
        return True
    except ValueError:
        return False


def is_zip_member_symlink(info: zipfile.ZipInfo) -> bool:
    """Check if a ZipInfo entry is a symbolic link.

    Symlinks in zip archives are identified by Unix external attributes.
    Mode 0o120000 is the Unix symlink flag.
    """
    # Unix external attributes are in the high 16 bits
    unix_mode = info.external_attr >> 16
    # S_IFLNK = 0o120000 (symlink)
    return (unix_mode & 0o170000) == 0o120000


def is_tar_member_symlink(member: tarfile.TarInfo) -> bool:
    """Check if a TarInfo entry is a symbolic link."""
    return member.issym() or member.islnk()


def fetch_pinned(
    spec: SourceSpec,
    target_dir: Path,
    force: bool = False,
) -> dict:
    """Fetch using pinned mode (commit-specific raw URLs).

    No GitHub API calls. Fully deterministic.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).isoformat()

    file_hashes = []
    files_fetched = []

    for rel_path in spec.files:
        url = raw_github_url(spec.owner, spec.project, spec.git_commit, rel_path)
        out_path = target_dir / rel_path

        # Security: verify path doesn't escape target_dir
        if not is_path_safe(rel_path, target_dir):
            raise ValueError(f"Unsafe path in files list: {rel_path}")

        # Create parent directories if needed
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Skip if already exists and not forcing
        if out_path.exists() and not force:
            print(f"  Skipping {rel_path} (already exists)")
        else:
            print(f"  Fetching {rel_path}...")
            try:
                download_to(url, out_path)
            except URLError as e:
                raise URLError(f"Failed to fetch {rel_path} from {url}: {e}") from e

        file_hash = sha256_file(out_path)
        file_hashes.append((rel_path, file_hash))
        files_fetched.append(rel_path)

    # Compute manifest SHA256 (stable hash of all file hashes)
    sha256 = sha256_of_manifest(file_hashes)

    return {
        "name": spec.name,
        "version": spec.version,
        "license": spec.license,
        "url": spec.repo or "",
        "retrieved_at": retrieved_at,
        "sha256": sha256,
        "git_commit": spec.git_commit or "",
        "git_tag": spec.git_tag or "",
        "files": files_fetched,
        "notes": spec.notes or "",
    }


def fetch_archive(
    spec: SourceSpec,
    target_dir: Path,
    force: bool = False,
) -> dict:
    """Fetch using archive mode (zip/tar download).

    Legacy mode - use pinned mode when possible.

    Security protections:
    - Path traversal (zip-slip) attacks blocked
    - Absolute paths rejected
    - Symlinks in archives rejected (classic bypass vector)

    Args:
        spec: Source specification
        target_dir: Directory to extract to
        force: Re-download even if cached

    Returns:
        Metadata dict with provenance info

    Raises:
        ValueError: If archive contains unsafe paths or symlinks
        URLError: If download fails
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).isoformat()

    print(f"Fetching {spec.name} from {spec.url}...")
    request = Request(spec.url, headers={"User-Agent": "RedLetters/0.1"})

    try:
        with urlopen(request, timeout=60) as response:
            if spec.archive_type:
                # Download archive to temp file
                archive_path = target_dir / f"archive.{spec.archive_type}"
                tmp_archive = archive_path.with_suffix(archive_path.suffix + ".tmp")

                with open(tmp_archive, "wb") as f:
                    shutil.copyfileobj(response, f)
                tmp_archive.replace(archive_path)

                # Compute hash of archive
                sha256 = sha256_file(archive_path)

                # Extract with full security validation
                if spec.archive_type == "zip":
                    with zipfile.ZipFile(archive_path, "r") as zf:
                        for info in zf.infolist():
                            # Check for path traversal
                            if not is_path_safe(info.filename, target_dir):
                                raise ValueError(
                                    f"Unsafe path in archive: {info.filename}"
                                )
                            # Check for symlinks (classic zip-slip bypass)
                            if is_zip_member_symlink(info):
                                raise ValueError(
                                    f"Symlinks not supported in archives: {info.filename}"
                                )
                        zf.extractall(target_dir)
                elif spec.archive_type in ("tar.gz", "tgz"):
                    with tarfile.open(archive_path, "r:gz") as tf:
                        for member in tf.getmembers():
                            # Check for path traversal
                            if not is_path_safe(member.name, target_dir):
                                raise ValueError(
                                    f"Unsafe path in archive: {member.name}"
                                )
                            # Check for symlinks (classic tar-slip bypass)
                            if is_tar_member_symlink(member):
                                raise ValueError(
                                    f"Symlinks not supported in archives: {member.name}"
                                )
                        tf.extractall(target_dir)

                # Remove archive after extraction
                archive_path.unlink()
            else:
                # Raw file download
                file_name = spec.url.split("/")[-1]
                file_path = target_dir / file_name
                download_to(spec.url, file_path)
                sha256 = sha256_file(file_path)

    except URLError as e:
        shutil.rmtree(target_dir, ignore_errors=True)
        raise URLError(f"Failed to fetch {spec.name}: {e}") from e

    return {
        "name": spec.name,
        "version": spec.version,
        "license": spec.license,
        "url": spec.url or "",
        "retrieved_at": retrieved_at,
        "sha256": sha256,
        "git_commit": spec.git_commit or "",
        "git_tag": spec.git_tag or "",
        "files": [],
        "notes": spec.notes or "",
    }


def fetch_source(
    source_key: str,
    data_dir: Path | None = None,
    force: bool = False,
    allow_floating: bool = False,
    allow_archive: bool = False,
    catalog_path: Path | None = None,
) -> dict:
    """
    Fetch a data source from its canonical URL.

    Args:
        source_key: Key from sources catalog
        data_dir: Directory to store data (default: ~/.redletters/data)
        force: Re-download even if already present
        allow_floating: Allow floating refs (master, HEAD, tags) - default rejects
        allow_archive: Allow archive mode (zip/tar) - default prefers pinned mode.
                      Set True to explicitly allow legacy archive fetching.
                      In CI, keep False to prevent quiet regression to archive mode.
        catalog_path: Override path to sources_catalog.yaml

    Returns:
        Dict with source metadata including local path and sha256

    Raises:
        ValueError: If source_key not recognized, floating ref without allow_floating,
                   or archive mode without allow_archive
        URLError: If download fails
        CatalogNotFoundError: If catalog cannot be found
    """
    spec = get_source_spec(source_key, catalog_path)

    # Reject floating fetches by default
    if spec.is_floating() and not allow_floating:
        reason = "no commit specified"
        if spec.git_commit:
            if not is_full_sha(spec.git_commit):
                reason = f"'{spec.git_commit}' is not a full 40-char SHA"
        raise ValueError(
            f"Source {source_key} uses floating ref ({reason}). "
            f"Pin a full commit SHA in sources_catalog.yaml, or use --allow-floating."
        )

    data_dir = data_dir or get_data_dir()
    target_dir = data_dir / source_key

    # Check if already downloaded
    marker_file = target_dir / ".fetched"
    if marker_file.exists() and not force:
        meta = read_marker(marker_file)
        meta["path"] = target_dir
        meta["already_cached"] = True
        return meta

    # Clean directory if forcing
    if target_dir.exists() and force:
        shutil.rmtree(target_dir)

    # Choose fetch mode
    if spec.is_pinned():
        print(f"Fetching {spec.name} (pinned @ {spec.git_commit[:12]}...)")
        meta = fetch_pinned(spec, target_dir, force)
    elif spec.url:
        # Archive mode requires explicit opt-in to prevent silent regressions
        if not allow_archive:
            raise ValueError(
                f"Source {source_key} would use archive mode (not pinned).\n"
                f"Archive mode is less reproducible than pinned mode.\n"
                f"\n"
                f"Options:\n"
                f"  1. Update sources_catalog.yaml to use pinned mode (recommended):\n"
                f"     - Add 'repo', 'commit' (full 40-char SHA), and 'files' fields\n"
                f"  2. Use --allow-archive flag to explicitly allow archive mode"
            )
        print(f"Fetching {spec.name} (archive mode)")
        meta = fetch_archive(spec, target_dir, force)
    else:
        raise ValueError(f"Source {source_key} has no fetch URL or pinned files")

    # Write marker
    write_marker(marker_file, meta)

    print(f"  Downloaded to {target_dir}")
    print(f"  License: {spec.license}")
    print(f"  SHA256: {meta['sha256'][:16]}...")
    if meta.get("git_commit"):
        print(f"  Commit: {meta['git_commit'][:12]}...")

    meta["path"] = target_dir
    meta["already_cached"] = False
    return meta


def fetch_all(
    data_dir: Path | None = None,
    force: bool = False,
    allow_floating: bool = False,
    allow_archive: bool = False,
    catalog_path: Path | None = None,
) -> list[dict]:
    """Fetch all known data sources.

    Args:
        data_dir: Directory to store data (default: ~/.redletters/data)
        force: Re-download even if already present
        allow_floating: Allow floating refs (master, HEAD, tags)
        allow_archive: Allow archive mode (zip/tar) for non-pinned sources
        catalog_path: Override path to sources_catalog.yaml

    Returns:
        List of metadata dicts for each source
    """
    results = []
    for key in list_available_sources(catalog_path):
        try:
            result = fetch_source(
                key,
                data_dir,
                force,
                allow_floating=allow_floating,
                allow_archive=allow_archive,
                catalog_path=catalog_path,
            )
            results.append(result)
        except Exception as e:
            print(f"  Warning: Failed to fetch {key}: {e}")
            results.append({"name": key, "error": str(e)})
    return results


def get_source_path(source_key: str, data_dir: Path | None = None) -> Path | None:
    """Get the local path for a fetched source, or None if not fetched."""
    data_dir = data_dir or get_data_dir()
    source_dir = data_dir / source_key
    marker_file = source_dir / ".fetched"
    if marker_file.exists():
        return source_dir
    return None


def print_license_report(
    data_dir: Path | None = None, catalog_path: Path | None = None
) -> None:
    """Print a license/provenance report for all fetched sources."""
    data_dir = data_dir or get_data_dir()

    print("\n" + "=" * 60)
    print("RED LETTERS - DATA SOURCE PROVENANCE REPORT")
    print("=" * 60)

    any_found = False
    for key in list_available_sources(catalog_path):
        spec = get_source_spec(key, catalog_path)
        source_dir = data_dir / key
        marker_file = source_dir / ".fetched"

        print(f"\n[{spec.name}]")
        if marker_file.exists():
            any_found = True
            meta = read_marker(marker_file)
            for k in MARKER_KEYS:
                v = meta.get(k, "")
                if v:  # Only print non-empty values
                    print(f"  {k}={v}")
        else:
            print("  Status: NOT FETCHED")
            print(f"  License: {spec.license}")
            if spec.repo:
                print(f"  Repo: {spec.repo}")
            if spec.is_pinned():
                print(f"  Pinned commit: {spec.git_commit}")

    if not any_found:
        print("\nNo data sources fetched yet.")
        print("Run: redletters data fetch")

    print("\n" + "-" * 60)
    print("LICENSE OBLIGATIONS:")
    print("-" * 60)
    print("- CC-BY-SA content requires attribution and share-alike")
    print("- If distributing derived data, use compatible license")
    print("- See ADR-002 for full license analysis")
    print("=" * 60 + "\n")
