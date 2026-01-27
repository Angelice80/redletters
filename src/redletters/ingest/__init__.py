"""Data ingestion module.

Public API:
    MorphGNT parsing:
        parse_file(path) -> list[MorphGNTToken]
        parse_file_with_delimiter(path) -> tuple[list[MorphGNTToken], str]
        parse_directory(path) -> list[MorphGNTToken]

    Data fetching:
        fetch_source(key) -> dict with provenance
        fetch_all() -> list of fetch results

    Loading:
        load_source(conn, key) -> LoadReport
        load_all(conn) -> list[LoadReport]
"""

from redletters.ingest.morphgnt_parser import (
    MorphGNTToken,
    parse_file,
    parse_file_with_delimiter,
    parse_directory,
)
from redletters.ingest.fetch import (
    fetch_source,
    fetch_all,
    CatalogNotFoundError,
    UnsupportedURLError,
)
from redletters.ingest.loader import (
    load_source,
    load_all,
    LoadReport,
    LoaderError,
    SHAMismatchError,
)

__all__ = [
    # MorphGNT parsing
    "MorphGNTToken",
    "parse_file",
    "parse_file_with_delimiter",
    "parse_directory",
    # Fetching
    "fetch_source",
    "fetch_all",
    "CatalogNotFoundError",
    "UnsupportedURLError",
    # Loading
    "load_source",
    "load_all",
    "LoadReport",
    "LoaderError",
    "SHAMismatchError",
]
