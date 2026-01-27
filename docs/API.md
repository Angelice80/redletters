# API Reference

## Base URL

```
http://localhost:8000/api/v1
```

## Starting the Server

```bash
redletters serve
# or
redletters serve --host 0.0.0.0 --port 8080
```

Interactive documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Endpoints

### GET /api/v1/health

Health check endpoint.

**Response**

```json
{
  "status": "ok",
  "version": "0.1.0",
  "db_connected": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| status | string | `"ok"` or `"degraded"` |
| version | string | API version |
| db_connected | boolean | Database connectivity status |

---

### GET /api/v1/query

Query a scripture reference and get candidate renderings.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| ref | string | Yes | Scripture reference (e.g., "Matthew 3:2") |
| style | string | No | Filter by rendering style |

**Supported Styles**
- `ultra-literal`
- `natural`
- `meaning-first`
- `jewish-context`

**Example Request**

```bash
curl "http://localhost:8000/api/v1/query?ref=Matthew%203:2"
```

**Example Response**

```json
{
  "reference": "Matthew 3:2",
  "parsed_ref": {
    "book": "Matthew",
    "chapter": 3,
    "verse": 2
  },
  "greek_text": "μετανοεῖτε ἤγγικεν γὰρ ἡ βασιλεία τῶν οὐρανῶν",
  "token_count": 7,
  "renderings": [
    {
      "style": "natural",
      "text": "Change one's mind! draw near (spatially) for the reign the heaven",
      "score": 0.72,
      "score_breakdown": {
        "morph_fit": 1.0,
        "sense_weight": 0.876,
        "collocation_bonus": 0.057,
        "uncommon_penalty": 0.0,
        "weights_used": {
          "morph_fit": 0.4,
          "sense_weight": 0.35,
          "collocation": 0.15,
          "uncommon_penalty": 0.1
        }
      },
      "receipts": [
        {
          "surface": "μετανοεῖτε",
          "lemma": "μετανοέω",
          "morph": {
            "force": "command",
            "subject": "implied_you",
            "aspect": "ongoing_or_general"
          },
          "chosen_sense_id": "metanoeo.1",
          "chosen_gloss": "Change one's mind!",
          "sense_source": "BDAG",
          "sense_weight": 0.8,
          "sense_domain": "cognitive",
          "rationale": "Selected 'change one's mind' (weight=0.80); domain: cognitive; source: BDAG; style: idiomatic English rendering; NOTE: lexical_polysemy ambiguity present",
          "ambiguity_type": "lexical_polysemy",
          "alternate_glosses": ["repent", "turn around"],
          "definition": "to change one's way of thinking, with focus on cognitive reorientation"
        }
      ]
    }
  ]
}
```

**Response Schema**

| Field | Type | Description |
|-------|------|-------------|
| reference | string | Original reference string |
| parsed_ref | object | Parsed reference components |
| parsed_ref.book | string | Book name |
| parsed_ref.chapter | integer | Chapter number |
| parsed_ref.verse | integer | Verse number |
| greek_text | string | Greek text (Unicode) |
| token_count | integer | Number of tokens |
| renderings | array | Candidate renderings (3-5) |

**Rendering Object**

| Field | Type | Description |
|-------|------|-------------|
| style | string | Rendering style name |
| text | string | Full rendered English text |
| score | float | Composite ranking score (0-1) |
| score_breakdown | object | Score calculation details |
| receipts | array | Token-level interpretive receipts |

**Receipt Object**

| Field | Type | Description |
|-------|------|-------------|
| surface | string | Greek surface form |
| lemma | string | Dictionary form |
| morph | object | Morphological constraints |
| chosen_sense_id | string | Selected sense identifier |
| chosen_gloss | string | English gloss used |
| sense_source | string | Lexicon source (BDAG, LSJ, etc.) |
| sense_weight | float | Default sense weight |
| sense_domain | string | Semantic domain |
| rationale | string | Explanation for choice |
| ambiguity_type | string? | Type of ambiguity if present |
| alternate_glosses | array? | Other possible glosses |
| definition | string? | Full definition |

**Error Responses**

| Status | Description |
|--------|-------------|
| 400 | Invalid reference format |
| 404 | No tokens found for reference |

```json
{
  "detail": "Cannot parse reference: invalid"
}
```

---

### GET /api/v1/spans

List all red-letter speech spans in the database.

**Example Request**

```bash
curl "http://localhost:8000/api/v1/spans"
```

**Example Response**

```json
[
  {
    "book": "Matthew",
    "chapter": 3,
    "verse_start": 2,
    "verse_end": 2,
    "speaker": "John the Baptist",
    "confidence": 1.0,
    "source": "narrative context"
  },
  {
    "book": "Matthew",
    "chapter": 4,
    "verse_start": 17,
    "verse_end": 17,
    "speaker": "Jesus",
    "confidence": 1.0,
    "source": "narrative context"
  }
]
```

**Span Object**

| Field | Type | Description |
|-------|------|-------------|
| book | string | Book name |
| chapter | integer | Chapter number |
| verse_start | integer | Starting verse |
| verse_end | integer | Ending verse |
| speaker | string | Speaker attribution |
| confidence | float | Editorial confidence (0-1) |
| source | string | Source/tradition |

---

### GET /api/v1/tokens

Get raw token data for a reference (debugging endpoint).

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| ref | string | Yes | Scripture reference |

**Example Request**

```bash
curl "http://localhost:8000/api/v1/tokens?ref=Matthew%203:2"
```

**Example Response**

```json
{
  "reference": "Matthew 3:2",
  "tokens": [
    {
      "id": 1,
      "book": "Matthew",
      "chapter": 3,
      "verse": 2,
      "position": 1,
      "surface": "μετανοεῖτε",
      "lemma": "μετανοέω",
      "morph": "V-PAM-2P",
      "is_red_letter": true
    }
  ]
}
```

---

## CLI Reference

### Initialize Database

```bash
redletters init
```

Creates the database at `~/.redletters/redletters.db` and loads demo data.

### Query a Reference

```bash
# Basic query
redletters query "Matthew 3:2"

# Filter by style
redletters query "Mark 1:15" --style ultra-literal

# Export to JSON
redletters query "Matthew 3:2" --output results.json
```

### List Speech Spans

```bash
redletters list-spans
```

### Start API Server

```bash
# Default (localhost:8000)
redletters serve

# Custom host/port
redletters serve --host 0.0.0.0 --port 8080
```

---

## Morphology Code Reference

The system uses Robinson-Pierpont style morphology codes.

### Verbs

Format: `V-{tense}{voice}{mood}-{person}{number}`

**Tenses**
| Code | Meaning |
|------|---------|
| P | Present |
| I | Imperfect |
| F | Future |
| A | Aorist |
| X | Perfect |
| Y | Pluperfect |

**Voices**
| Code | Meaning |
|------|---------|
| A | Active |
| M | Middle |
| P | Passive |
| E | Middle/Passive (ambiguous) |

**Moods**
| Code | Meaning |
|------|---------|
| I | Indicative |
| S | Subjunctive |
| O | Optative |
| M | Imperative |
| N | Infinitive |
| P | Participle |

**Example**: `V-PAM-2P` = Verb, Present Active Imperative, 2nd Person Plural

### Nouns/Adjectives

Format: `{part}-{case}{number}{gender}`

**Cases**
| Code | Meaning |
|------|---------|
| N | Nominative |
| G | Genitive |
| D | Dative |
| A | Accusative |
| V | Vocative |

**Numbers**
| Code | Meaning |
|------|---------|
| S | Singular |
| P | Plural |

**Genders**
| Code | Meaning |
|------|---------|
| M | Masculine |
| F | Feminine |
| N | Neuter |

**Example**: `N-NSF` = Noun, Nominative Singular Feminine

---

## Score Breakdown Reference

The ranking score is calculated as:

```
score = (morph_fit × 0.40) + (sense_weight × 0.35) + (collocation × 0.15) - (uncommon_penalty × 0.10)
```

| Component | Weight | Description |
|-----------|--------|-------------|
| morph_fit | 0.40 | 1.0 if morphology is unambiguous, 0.8 if ambiguous |
| sense_weight | 0.35 | Average lexicon weight of chosen senses |
| collocation | 0.15 | Bonus for common word pairings |
| uncommon_penalty | 0.10 | Penalty for low-frequency sense selections |

---

## Related Documentation

- [BMAD-SPEC.md](./BMAD-SPEC.md) — Full project specification
- [ADR-001-architecture.md](./ADR-001-architecture.md) — Architecture decisions
- [PROGRESS.md](./PROGRESS.md) — Development log
