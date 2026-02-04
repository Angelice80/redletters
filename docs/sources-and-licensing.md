# Sources and Licensing

Red Letters aggregates data from multiple sources with different licenses.
This document explains what's included, what requires acceptance, and
attribution requirements.

## Summary

| Source Type | License | Requires `--accept-eula`? | Redistributable? |
|-------------|---------|---------------------------|------------------|
| Demo data (bundled) | MIT | No | Yes |
| MorphGNT-SBLGNT | CC-BY-SA-3.0 | No | Yes, with attribution |
| Strong's Greek | CC0 (Public Domain) | No | Yes |
| UBS Dictionary | CC-BY-SA-4.0 | Yes | Yes, with attribution + share-alike |
| Westcott-Hort | Public Domain | No | Yes |
| Byzantine Textform | Public Domain | No | Yes |

---

## Bundled Demo Data

When you run `redletters init`, the database is populated with demo data that
allows immediate querying without installing any packs.

- **License**: MIT (same as this project)
- **Content**: Sample passages with basic sense data
- **Purpose**: Quick start, testing, development
- **Limitations**: Incomplete coverage, simplified receipts

The demo data is sufficient to verify installation and explore the interface,
but scholarly work requires installing additional source packs.

---

## Source Packs

### MorphGNT-SBLGNT (Canonical Spine)

The SBL Greek New Testament with morphological analysis.

- **License**: CC-BY-SA-3.0
- **Attribution**: "Morphological analysis by MorphGNT; SBLGNT text (c) 2010 SBL and Logos Bible Software"
- **Role**: Canonical text spine - all token positions reference this edition
- **Install**: `redletters sources install morphgnt-sblgnt`

### Strong's Greek Dictionary

Public domain concordance data.

- **License**: CC0 (Public Domain)
- **Attribution**: None required
- **Role**: Secondary lexicon for concordance links
- **Install**: `redletters sources install strongs-greek`

### UBS Greek Dictionary

Louw-Nida derived semantic domains.

- **License**: CC-BY-SA-4.0
- **Attribution**: Required (see license)
- **Share-alike**: Derivative works must use compatible license
- **Role**: Semantic domain classification
- **Install**: `redletters sources install ubs-dictionary --accept-eula`

The `--accept-eula` flag acknowledges that you've reviewed and accepted the
CC-BY-SA-4.0 terms, particularly the share-alike requirement.

### Westcott-Hort (Public Domain)

1881 critical edition, useful for variant comparison.

- **License**: Public Domain
- **Attribution**: None required
- **Role**: Comparative text layer
- **Install**: Available as local pack (`data/packs/westcott-hort-john`)

### Byzantine Textform

Robinson-Pierpont majority text readings.

- **License**: Public Domain
- **Attribution**: None required
- **Role**: Comparative text layer (represents majority manuscript tradition)
- **Install**: Available as local pack (`data/packs/byzantine-john`)

---

## The `--accept-eula` Flag

Some sources require explicit license acceptance before installation.

**What it means:**
- You've read the license terms
- You agree to comply with attribution requirements
- You understand any redistribution restrictions

**When it's required:**
- CC-BY-SA licensed content (share-alike obligation)
- Content with specific attribution formats
- Content from organizations requiring acceptance

**What it doesn't mean:**
- It's not a payment or registration
- It doesn't send data anywhere
- It's a local acknowledgement recorded in your installation

---

## Viewing License Information

Check installed source licenses:

```bash
redletters licenses
```

This shows:
- License type for each installed source
- Attribution requirements
- Share-alike obligations
- Retrieval timestamps

---

## Attribution in Exports

When you export data, attribution metadata is included:

```json
{
  "provenance": {
    "sources": [
      {
        "name": "MorphGNT-SBLGNT",
        "version": "6.12",
        "license": "CC-BY-SA-3.0",
        "attribution": "Morphological analysis by MorphGNT"
      }
    ]
  }
}
```

If you publish or redistribute exported data, you must include this attribution
per the source licenses.

---

## "Free" Means Free-to-Access

All data sources used by Red Letters are free to access - there are no paywalls
or subscriptions. However, "free" does not mean "no obligations":

| Free to... | Obligation |
|------------|------------|
| Download | None |
| Use personally | None |
| Use in research | Attribution (for CC-BY-* sources) |
| Redistribute | Attribution + share-alike (for CC-BY-SA sources) |
| Commercial use | Check specific license |

When in doubt, run `redletters licenses` and read the linked license text.

---

## Reproducibility

For reproducible scholarly work:

1. Generate a lockfile: `redletters packs lock --out packs.lock`
2. Include the lockfile with your research
3. Others can reproduce your environment: `redletters packs sync packs.lock`

The lockfile captures exact versions and commit hashes, ensuring identical data.

---

## Further Reading

- [Sources Catalog](../sources_catalog.yaml) - Full source definitions
- [ADR-007: Canonical Spine](adrs/ADR-007-canonical-spine-sblgnt.md) - Why SBLGNT is the base text
- [CLI Reference](cli.md) - Source management commands
