"""Receipt generation utilities."""


def format_receipt_summary(receipts: list[dict]) -> str:
    """
    Format receipts as human-readable summary.

    Args:
        receipts: List of receipt dictionaries

    Returns:
        Formatted string summary
    """
    lines = []

    for r in receipts:
        line = f"• {r['surface']} ({r['lemma']}): {r['chosen_gloss']}"
        if r.get("ambiguity_type"):
            line += f" [AMBIGUOUS: {r['ambiguity_type']}]"
        lines.append(line)

        # Add source line
        source_line = f"  └─ {r['sense_source']}: {r.get('definition', 'N/A')}"
        lines.append(source_line)

        # Add alternates if present
        if r.get("alternate_glosses"):
            alt_line = f"     Alternates: {', '.join(r['alternate_glosses'][:3])}"
            lines.append(alt_line)

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
