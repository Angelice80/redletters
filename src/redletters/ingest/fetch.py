"""Fetch external data sources at runtime.

Per ADR-002: Data is fetched at install time, not bundled in the repo.
This avoids license composition issues and forces explicit license acceptance.
"""

import hashlib
import shutil
import tarfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

# Default data directory (can be overridden)
DEFAULT_DATA_DIR = Path.home() / ".redletters" / "data"


@dataclass
class SourceSpec:
    """Specification for an external data source."""

    name: str
    version: str
    license: str
    url: str
    archive_type: str | None  # "zip", "tar.gz", or None for raw file
    extract_path: str | None  # path within archive to extract
    notes: str | None = None


# Known data sources with their licenses
SOURCES = {
    "morphgnt-sblgnt": SourceSpec(
        name="MorphGNT-SBLGNT",
        version="6.12",
        license="CC-BY-SA-3.0",
        url="https://github.com/morphgnt/sblgnt/archive/refs/heads/master.zip",
        archive_type="zip",
        extract_path="sblgnt-master",
        notes="Morphological analysis CC-BY-SA; SBLGNT text CC-BY-4.0",
    ),
    "strongs-greek": SourceSpec(
        name="Strongs-Greek",
        version="2016-06",
        license="CC0-1.0",
        url="https://raw.githubusercontent.com/morphgnt/strongs-dictionary-xml/master/strongsgreek.xml",
        archive_type=None,
        extract_path=None,
        notes="Public domain (CC0)",
    ),
    # UBS data requires manual acceptance - we provide instructions
    "ubs-dictionary": SourceSpec(
        name="UBS-Dictionary",
        version="2023",
        license="CC-BY-SA-4.0",
        url="https://github.com/ubsicap/ubs-open-license/archive/refs/heads/main.zip",
        archive_type="zip",
        extract_path="ubs-open-license-main",
        notes="Louw-Nida derived; share-alike license",
    ),
}


def get_data_dir() -> Path:
    """Get the data directory, creating if needed."""
    data_dir = DEFAULT_DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def fetch_source(
    source_key: str,
    data_dir: Path | None = None,
    force: bool = False,
) -> dict:
    """
    Fetch a data source from its canonical URL.

    Args:
        source_key: Key from SOURCES dict
        data_dir: Directory to store data (default: ~/.redletters/data)
        force: Re-download even if already present

    Returns:
        Dict with source metadata including local path and sha256

    Raises:
        ValueError: If source_key not recognized
        URLError: If download fails
    """
    if source_key not in SOURCES:
        raise ValueError(f"Unknown source: {source_key}. Known: {list(SOURCES.keys())}")

    spec = SOURCES[source_key]
    data_dir = data_dir or get_data_dir()
    source_dir = data_dir / source_key

    # Check if already downloaded
    marker_file = source_dir / ".fetched"
    if marker_file.exists() and not force:
        with open(marker_file) as f:
            metadata = {}
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    metadata[k] = v
            metadata["path"] = source_dir
            metadata["already_cached"] = True
            return metadata

    # Clean and create directory
    if source_dir.exists():
        shutil.rmtree(source_dir)
    source_dir.mkdir(parents=True)

    # Download
    print(f"Fetching {spec.name} from {spec.url}...")
    request = Request(spec.url, headers={"User-Agent": "RedLetters/0.1"})

    try:
        with urlopen(request, timeout=60) as response:
            if spec.archive_type:
                # Download archive to temp file
                archive_path = source_dir / f"archive.{spec.archive_type}"
                with open(archive_path, "wb") as f:
                    shutil.copyfileobj(response, f)

                # Compute hash of archive
                sha256 = compute_sha256(archive_path)

                # Extract
                if spec.archive_type == "zip":
                    with zipfile.ZipFile(archive_path, "r") as zf:
                        zf.extractall(source_dir)
                elif spec.archive_type in ("tar.gz", "tgz"):
                    with tarfile.open(archive_path, "r:gz") as tf:
                        tf.extractall(source_dir)

                # Remove archive after extraction
                archive_path.unlink()
            else:
                # Raw file download
                file_name = spec.url.split("/")[-1]
                file_path = source_dir / file_name
                with open(file_path, "wb") as f:
                    shutil.copyfileobj(response, f)
                sha256 = compute_sha256(file_path)

    except URLError as e:
        shutil.rmtree(source_dir, ignore_errors=True)
        raise URLError(f"Failed to fetch {spec.name}: {e}") from e

    # Write marker with metadata
    retrieved_at = datetime.now(timezone.utc).isoformat()
    with open(marker_file, "w") as f:
        f.write(f"name={spec.name}\n")
        f.write(f"version={spec.version}\n")
        f.write(f"license={spec.license}\n")
        f.write(f"url={spec.url}\n")
        f.write(f"retrieved_at={retrieved_at}\n")
        f.write(f"sha256={sha256}\n")
        if spec.notes:
            f.write(f"notes={spec.notes}\n")

    print(f"  Downloaded to {source_dir}")
    print(f"  License: {spec.license}")
    print(f"  SHA256: {sha256[:16]}...")

    return {
        "name": spec.name,
        "version": spec.version,
        "license": spec.license,
        "url": spec.url,
        "retrieved_at": retrieved_at,
        "sha256": sha256,
        "notes": spec.notes,
        "path": source_dir,
        "already_cached": False,
    }


def fetch_all(data_dir: Path | None = None, force: bool = False) -> list[dict]:
    """Fetch all known data sources."""
    results = []
    for key in SOURCES:
        try:
            result = fetch_source(key, data_dir, force)
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


def print_license_report(data_dir: Path | None = None) -> None:
    """Print a license/provenance report for all fetched sources."""
    data_dir = data_dir or get_data_dir()

    print("\n" + "=" * 60)
    print("RED LETTERS - DATA SOURCE PROVENANCE REPORT")
    print("=" * 60)

    any_found = False
    for key, spec in SOURCES.items():
        source_dir = data_dir / key
        marker_file = source_dir / ".fetched"

        if marker_file.exists():
            any_found = True
            print(f"\n[{spec.name}]")
            with open(marker_file) as f:
                for line in f:
                    if line.strip():
                        print(f"  {line.strip()}")
        else:
            print(f"\n[{spec.name}]")
            print("  Status: NOT FETCHED")
            print(f"  License: {spec.license}")
            print(f"  URL: {spec.url}")

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
