"""Parse Strong's Greek Dictionary XML into lexicon entries.

CRITICAL EPISTEMIC NOTE:
These entries are SENSE INVENTORIES, not authoritative meanings.
They represent "the buckets this source uses" — candidate partitions
of usage that can inform ranking without collapsing meaning.

Strong's is CC0 (public domain) so there are no share-alike obligations,
but we still track provenance for transparency.
"""

from __future__ import annotations

import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StrongsEntry:
    """A single entry from Strong's Greek Dictionary."""

    strongs_id: str  # e.g., "G3340"
    lemma: str  # Greek headword
    translit: str | None  # transliteration
    gloss: str  # short definition
    definition: str | None  # fuller explanation
    derivation: str | None  # etymological notes

    def to_db_tuple(self, source_id: int) -> tuple:
        """Convert to tuple for lexicon_entries insertion."""
        # sense_id uses Strong's number
        sense_id = f"strongs.{self.strongs_id}"
        return (
            self.lemma,
            sense_id,
            self.gloss,
            self.definition,
            None,  # domain (Strong's doesn't have semantic domains)
            source_id,
        )


def normalize_greek(text: str) -> str:
    """Normalize Greek text to NFC form."""
    return unicodedata.normalize("NFC", text)


def clean_text(text: str | None) -> str | None:
    """Clean and normalize text content."""
    if text is None:
        return None
    # Remove extra whitespace
    text = " ".join(text.split())
    return text if text else None


def parse_strongs_xml(file_path: Path) -> list[StrongsEntry]:
    """
    Parse Strong's Greek Dictionary XML file.

    Expected format (morphgnt/strongs-dictionary-xml):
    <entries>
      <entry>
        <strongs>G0001</strongs>
        <greek unicode="Α" translit="A">Α</greek>
        <pronunciation strongs="al'-fah"/>
        <strongs_derivation>...</strongs_derivation>
        <strongs_def>...</strongs_def>
      </entry>
      ...
    </entries>
    """
    entries = []

    tree = ET.parse(file_path)
    root = tree.getroot()

    for entry_elem in root.findall(".//entry"):
        # Get Strong's number
        strongs_elem = entry_elem.find("strongs")
        if strongs_elem is None or not strongs_elem.text:
            continue
        strongs_id = strongs_elem.text.strip()

        # Get Greek lemma
        greek_elem = entry_elem.find("greek")
        if greek_elem is None:
            continue
        lemma = greek_elem.get("unicode", greek_elem.text or "")
        lemma = normalize_greek(lemma.strip()) if lemma else ""
        if not lemma:
            continue

        # Get transliteration
        translit = greek_elem.get("translit")

        # Get definition (short gloss from strongs_def)
        def_elem = entry_elem.find("strongs_def")
        definition_text = ""
        if def_elem is not None:
            # Get all text content including from child elements
            definition_text = "".join(def_elem.itertext())
        definition_text = clean_text(definition_text) or ""

        # Extract short gloss (first part before semicolon or period)
        gloss = definition_text
        for sep in [";", ".", ":"]:
            if sep in gloss:
                gloss = gloss.split(sep)[0].strip()
                break
        # Limit gloss length
        if len(gloss) > 100:
            gloss = gloss[:97] + "..."

        # Get derivation/etymology
        deriv_elem = entry_elem.find("strongs_derivation")
        derivation = None
        if deriv_elem is not None:
            derivation = clean_text("".join(deriv_elem.itertext()))

        entries.append(
            StrongsEntry(
                strongs_id=strongs_id,
                lemma=lemma,
                translit=translit,
                gloss=gloss if gloss else f"[{strongs_id}]",
                definition=definition_text if definition_text else None,
                derivation=derivation,
            )
        )

    return entries


def parse_strongs_directory(source_dir: Path) -> list[StrongsEntry]:
    """
    Find and parse Strong's XML in a source directory.

    Handles both direct file and archive-extracted structures.
    """
    # Look for the XML file
    xml_files = list(source_dir.glob("**/*.xml"))
    strongs_file = None

    for f in xml_files:
        if "strongs" in f.name.lower() and "greek" in f.name.lower():
            strongs_file = f
            break

    if not strongs_file:
        # Try common filename
        for name in ["strongsgreek.xml", "strongs_greek.xml"]:
            candidate = source_dir / name
            if candidate.exists():
                strongs_file = candidate
                break

    if not strongs_file:
        raise FileNotFoundError(f"No Strong's Greek XML found in {source_dir}")

    print(f"  Parsing {strongs_file.name}...")
    entries = parse_strongs_xml(strongs_file)
    print(f"    {len(entries)} entries")

    return entries


def build_lemma_index(entries: list[StrongsEntry]) -> dict[str, list[StrongsEntry]]:
    """Build an index from lemma to all matching entries."""
    index: dict[str, list[StrongsEntry]] = {}
    for entry in entries:
        if entry.lemma not in index:
            index[entry.lemma] = []
        index[entry.lemma].append(entry)
    return index
