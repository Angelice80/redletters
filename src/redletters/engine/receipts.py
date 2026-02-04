"""Receipt generation utilities.

Receipts are the system's epistemic disclosure mechanism. They show:
1. What sources were used (provenance)
2. What role each source plays (not all sources are equal)
3. Known limitations of each source

No scolding. No persuasion. Just provenance + constraint posture.
"""

from __future__ import annotations

from dataclasses import dataclass


# =============================================================================
# Source Role Registry
# =============================================================================
# Each source has a defined role and known limitations.
# This prevents treating inventory sources as authoritative meanings.


@dataclass(frozen=True)
class SourceRole:
    """Defines a source's role and epistemological status."""

    name: str
    license: str
    role: str  # What this source provides
    limitations: list[str]  # Known issues with this source


SOURCE_ROLES: dict[str, SourceRole] = {
    "strongs": SourceRole(
        name="Strong's Greek Dictionary",
        license="Public Domain",
        role="Sense inventory (non-authoritative)",
        limitations=[
            "Glosses reflect 19th-century compression of semantic ranges",
            "Definitions may import theological phrasing from later traditions",
            "Numbered references are convenient but semantically imprecise",
        ],
    ),
    "bdag": SourceRole(
        name="BDAG Greek-English Lexicon",
        license="Licensed (reference only)",
        role="Primary lexical authority for NT Greek",
        limitations=[
            "Sense divisions represent scholarly consensus, not absolute boundaries",
        ],
    ),
    "louw-nida": SourceRole(
        name="Louw-Nida Greek-English Lexicon",
        license="Licensed (reference only)",
        role="Semantic domain classification",
        limitations=[
            "Domain labels are categorization constraints, not semantic truths",
            "Taxonomy itself embeds interpretive choices",
        ],
    ),
    "morphgnt": SourceRole(
        name="MorphGNT SBLGNT",
        license="CC-BY-SA-3.0",
        role="Morphological analysis of base text",
        limitations=[
            "Some parsing decisions reflect editorial judgment",
        ],
    ),
    # v0.6.0: Basic glosses fallback
    "basic_glosses": SourceRole(
        name="Basic Gloss Fallback",
        license="Public Domain",
        role="Fallback glosses for common vocabulary",
        limitations=[
            "Limited coverage of rare vocabulary",
            "Single-gloss per lemma (no semantic range)",
            "Should be supplemented with scholarly lexica",
        ],
    ),
}


# v0.6.0: Dynamic sense pack registry
_sense_pack_roles: dict[str, SourceRole] = {}


def register_sense_pack_role(
    source_id: str,
    name: str,
    license: str,
    role: str = "Installed sense pack",
    limitations: list[str] | None = None,
) -> None:
    """Register a sense pack source role dynamically.

    v0.6.0: Allows sense packs to register their provenance metadata.

    Args:
        source_id: Citation key for the source
        name: Full bibliographic name
        license: License identifier
        role: Role description
        limitations: Known limitations (optional)
    """
    _sense_pack_roles[source_id.lower()] = SourceRole(
        name=name,
        license=license,
        role=role,
        limitations=limitations or [],
    )


def get_source_role(source_name: str) -> SourceRole | None:
    """Get the role definition for a source, or None if unknown.

    v0.6.0: Also checks dynamically registered sense pack sources.
    """
    # Normalize source name for lookup
    key = source_name.lower().replace(" ", "").replace("-", "").replace("'", "")

    # Check static roles first
    for k, v in SOURCE_ROLES.items():
        if k in key or key in k:
            return v

    # v0.6.0: Check dynamically registered sense pack roles
    for k, v in _sense_pack_roles.items():
        if k in key or key in k:
            return v

    return None


def format_source_receipt(source_name: str, include_limitations: bool = True) -> str:
    """
    Format a structured receipt line for a source.

    Example output:
        Source: Strong's (Public Domain)
        Role: Sense inventory (non-authoritative)
        Known limitation: Glosses reflect 19th-century compression...
    """
    role = get_source_role(source_name)
    if role is None:
        return f"Source: {source_name} (unknown provenance)"

    lines = [
        f"Source: {role.name} ({role.license})",
        f"Role: {role.role}",
    ]

    if include_limitations and role.limitations:
        # Show first limitation as primary warning
        lines.append(f"Known limitation: {role.limitations[0]}")

    return "\n".join(lines)


def format_receipt_summary(
    receipts: list[dict], include_source_roles: bool = False
) -> str:
    """
    Format receipts as human-readable summary.

    Args:
        receipts: List of receipt dictionaries
        include_source_roles: If True, add source role/limitation notes

    Returns:
        Formatted string summary
    """
    lines = []
    sources_seen: set[str] = set()

    for r in receipts:
        line = f"• {r['surface']} ({r['lemma']}): {r['chosen_gloss']}"
        if r.get("ambiguity_type"):
            line += f" [AMBIGUOUS: {r['ambiguity_type']}]"
        lines.append(line)

        # Add source line
        source_name = r["sense_source"]
        source_line = f"  └─ {source_name}: {r.get('definition', 'N/A')}"
        lines.append(source_line)

        # Track sources for role disclosure
        sources_seen.add(source_name)

        # Add alternates if present
        if r.get("alternate_glosses"):
            alt_line = f"     Alternates: {', '.join(r['alternate_glosses'][:3])}"
            lines.append(alt_line)

    # Add source role disclosures at the end
    if include_source_roles and sources_seen:
        lines.append("")
        lines.append("─── Source Notes ───")
        for source_name in sorted(sources_seen):
            role = get_source_role(source_name)
            if role:
                lines.append(f"• {role.name}: {role.role}")
                if role.limitations:
                    lines.append(f"  ⚠ {role.limitations[0]}")

    return "\n".join(lines)


def validate_receipt_completeness(receipt: dict) -> tuple[bool, list[str]]:
    """
    Validate that a receipt has all required fields.

    Returns:
        Tuple of (is_complete, list_of_missing_fields)
    """
    required_fields = [
        "surface",
        "lemma",
        "morph",
        "chosen_sense_id",
        "chosen_gloss",
        "sense_source",
        "sense_weight",
        "rationale",
    ]

    missing = [f for f in required_fields if f not in receipt or receipt[f] is None]

    return len(missing) == 0, missing


def receipt_to_bibtex_style(receipt: dict) -> str:
    """
    Format receipt in citation-like format for academic use.

    Example:
        μετανοεῖτε: "change-your-minds" (BDAG s.v. μετανοέω.1; weight=0.8)
    """
    return (
        f'{receipt["surface"]}: "{receipt["chosen_gloss"]}" '
        f"({receipt['sense_source']} s.v. {receipt['chosen_sense_id']}; "
        f"weight={receipt['sense_weight']:.2f})"
    )


def format_sense_pack_citation(citation: dict) -> str:
    """Format sense pack citation for scholarly use (v0.6.0).

    Args:
        citation: Dictionary with citation-grade fields:
            - source_id: Citation key
            - source_title: Full bibliographic title
            - edition: Edition string (optional)
            - publisher: Publisher name (optional)
            - year: Publication year (optional)
            - license: License identifier (optional)

    Returns:
        Formatted citation string

    Example:
        "LSJ (A Greek-English Lexicon, 9th ed., Clarendon Press, 1996)"
    """
    parts = [citation.get("source_id", "unknown")]

    details = []
    if citation.get("source_title"):
        details.append(citation["source_title"])
    if citation.get("edition"):
        details.append(f"{citation['edition']} ed.")
    if citation.get("publisher"):
        details.append(citation["publisher"])
    if citation.get("year"):
        details.append(str(citation["year"]))

    if details:
        parts.append(f"({', '.join(details)})")

    if citation.get("license"):
        parts.append(f"[{citation['license']}]")

    return " ".join(parts)


def format_sense_pack_provenance(sense_packs: list[dict]) -> str:
    """Format multiple sense pack citations for receipts (v0.6.0).

    Args:
        sense_packs: List of sense pack citation dicts

    Returns:
        Formatted provenance string
    """
    if not sense_packs:
        return "No sense packs used"

    lines = ["Sense Pack Sources:"]
    for sp in sense_packs:
        lines.append(f"  • {format_sense_pack_citation(sp)}")

    return "\n".join(lines)
