# Task: Analyze Data Source

## Purpose
Thoroughly analyze a data source before integration to understand format, coverage, and requirements.

## Steps

1. **Source Identification**
   - Name and version of data source
   - URL/location
   - License terms
   - Citation requirements

2. **Format Analysis**
   - File format (TSV, XML, JSON, etc.)
   - Character encoding
   - Field structure
   - Sample records

3. **Schema Mapping**
   - Map source fields to Red Letters schema
   - Identify gaps (fields we need but source lacks)
   - Identify extras (fields source has we don't use)

4. **Coverage Assessment**
   - What books/chapters/verses covered?
   - What lemmas/senses included?
   - Any known gaps or limitations?

5. **Quality Assessment**
   - Data quality observations
   - Known issues or errata
   - Normalization requirements (Unicode, etc.)

6. **Provenance Requirements**
   - How to cite this source in receipts
   - Attribution requirements
   - Version tracking needs

7. **Edge Cases**
   - Unusual entries to handle
   - Missing data patterns
   - Encoding issues

## Output
Data source analysis document with:
- Source metadata
- Schema mapping table
- Coverage summary
- Quality notes
- Integration recommendations
