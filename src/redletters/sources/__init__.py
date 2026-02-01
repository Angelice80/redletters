"""Source Pack system for managing Greek text editions.

This package implements the Source Pack subsystem for Sprint 2/3:
- catalog.py: Load and validate sources_catalog.yaml
- resolver.py: Resolve pack and edition file paths
- spine.py: Spine provider interface for verse retrieval
- editions.py: Edition loader implementations
- installer.py: License-aware source pack installer (Sprint 3)

Per ADR-007: SBLGNT is the canonical spine (hub + default).
"""

from redletters.sources.catalog import (
    SourceCatalog,
    SourcePack,
    CatalogValidationError,
)
from redletters.sources.resolver import SourceResolver
from redletters.sources.spine import (
    SpineProvider,
    SBLGNTSpine,
    FixtureSpine,
    InstalledSpineProvider,
    SpineMissingError,
    get_installed_spine,
)
from redletters.sources.editions import EditionLoader, MorphGNTLoader, FixtureLoader
from redletters.sources.installer import (
    SourceInstaller,
    InstalledManifest,
    InstalledSource,
    InstallResult,
)

__all__ = [
    "SourceCatalog",
    "SourcePack",
    "CatalogValidationError",
    "SourceResolver",
    "SpineProvider",
    "SBLGNTSpine",
    "FixtureSpine",
    "InstalledSpineProvider",
    "SpineMissingError",
    "get_installed_spine",
    "EditionLoader",
    "MorphGNTLoader",
    "FixtureLoader",
    "SourceInstaller",
    "InstalledManifest",
    "InstalledSource",
    "InstallResult",
]
