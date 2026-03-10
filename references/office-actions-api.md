# USPTO Office Actions APIs Reference (Legacy)

**Base URL:** `https://developer.uspto.gov/ds-api`
**Auth Header:** `X-Api-Key` (ODP key works)
**Rate Limit:** 60 requests/minute
**Query Syntax:** Apache Lucene
**Methods:** POST (search), GET (field listing)

**Migration Notice:** These APIs are scheduled for migration to the Open Data
Portal (data.uspto.gov) in early 2026. Endpoint URLs may change.

## Table of Contents

1. [APIs Overview](#apis-overview)
2. [Lucene Query Syntax](#lucene-query-syntax)
3. [Office Action Rejection API (v2)](#office-action-rejection-api-v2)
4. [Office Action Text Retrieval API (v1)](#office-action-text-retrieval-api-v1)
5. [Enriched Citation API (v3)](#enriched-citation-api-v3)
6. [Examples](#examples)

---

## APIs Overview

| API | Dataset | Version | Coverage | Description |
|-----|---------|---------|----------|-------------|
| Rejection | `oa_rejections` | `v2` | June 2018 – ~180 days ago | Structured rejection data |
| Text | `oa_actions` | `v1` | Varies | Full text of office actions |
| Citations | `enriched_cited_reference_metadata` | `1` | Oct 2017 – April 2019 | NLP-parsed citation references (frozen) |

All three use the same request format:

```
POST /ds-api/{dataset}/{version}/records
Content-Type: application/x-www-form-urlencoded
X-Api-Key: your_key

criteria=your_lucene_query&start=0&rows=100
```

To list searchable fields:
```
GET /ds-api/{dataset}/{version}/fields
```

---

## Lucene Query Syntax

These APIs use Apache Lucene query syntax (v3.6.2).

### Basic Queries
```
field:value                    Exact term match
field:"multi word phrase"      Phrase match
field:val*                     Wildcard (any chars)
field:val?                     Wildcard (single char)
```

### Range Queries
```
field:[2020 TO 2024]           Inclusive range
field:{2020 TO 2024}           Exclusive range
field:[2020 TO *]              Open-ended range
```

### Boolean Operators
```
field1:val1 AND field2:val2    Both must match
field1:val1 OR field2:val2     Either can match
NOT field:value                Negate
(a OR b) AND c                 Grouping
```

### Special Characters
Escape these with backslash: `+ - && || ! ( ) { } [ ] ^ " ~ * ? : \ /`

Full syntax reference: https://lucene.apache.org/core/3_6_2/queryparsersyntax.html

---

## Office Action Rejection API (v2)

**Dataset:** `oa_rejections`
**Version:** `v2`
**Coverage:** Office actions mailed June 1, 2018 through ~180 days before current date
**Bulk data:** Historical rejections 2007-2025 available as ZIP download

### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `patentApplicationNumber` | string | Application serial number |
| `actionTypeCategory` | string | Office action type category |
| `submissionDate` | date | Office action submission date |
| `groupArtUnitNumber` | string | Art unit number |
| `nationalClass` | string | USPC class |
| `nationalSubclass` | string | USPC subclass |
| `legalSectionCode` | string | Legal section code |
| `claimNumberArrayDocument` | string | Claim numbers in the action |
| `allowedClaimIndicator` | boolean | Whether claims were allowed |
| `paragraphNumber` | string | Form paragraph number |

**Note:** This API does NOT have a `patentNumber` field. To search by
patent number, first resolve the patent to an application number via ODP,
then search by `patentApplicationNumber`.

### Rejection Type Fields

| Field | Type | Description |
|-------|------|-------------|
| `hasRej101` | boolean | 35 USC 101 rejection |
| `hasRej102` | boolean | 35 USC 102 rejection (novelty) |
| `hasRej103` | boolean | 35 USC 103 rejection (obviousness) |
| `hasRej112` | boolean | 35 USC 112 rejection |
| `hasRejDP` | boolean | Double patenting rejection |
| `aliceIndicator` | boolean | Alice Corp. (101 abstract idea) |
| `mayoIndicator` | boolean | Mayo (101 natural phenomenon) |
| `bilskiIndicator` | boolean | Bilski (101 abstract idea) |
| `myriadIndicator` | boolean | Myriad (101 natural product) |

### 103 Citation Count Fields

| Field | Type | Description |
|-------|------|-------------|
| `cite103EQ1` | boolean | Exactly 1 reference cited for 103 |
| `cite103GT3` | boolean | More than 3 references cited for 103 |
| `cite103Max` | string | Maximum number of 103 references |

---

## Office Action Text Retrieval API (v1)

**Dataset:** `oa_actions`
**Version:** `v1`

Returns the complete text of office actions. Useful for:
- Reading the examiner's reasoning
- Extracting claim-by-claim analysis
- Finding specific language or legal standards cited

### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `patentApplicationNumber` | string | Application number |
| `patentNumber` | string | Patent number (if granted) |
| `inventionTitle` | string | Title of the invention |
| `legacyDocumentCodeIdentifier` | string | Document code |
| `applicationTypeCategory` | string | Application type |
| `bodyText` | text | Full text of the office action |
| `submissionDate` | date | Submission date |
| `groupArtUnitNumber` | string | Art unit number |
| `examinerEmployeeNumber` | string | Examiner employee ID |
| `techCenter` | string | Technology center |

### Section-Level Fields (nested under `sections.`)

| Field | Type | Description |
|-------|------|-------------|
| `sections.section101RejectionText` | text | 101 rejection text |
| `sections.section102RejectionText` | text | 102 rejection text |
| `sections.section103RejectionText` | text | 103 rejection text |
| `sections.section112RejectionText` | text | 112 rejection text |
| `sections.summaryText` | text | Summary text |
| `sections.detailCitationText` | text | Detailed citation text |
| `sections.withdrawalRejectionText` | text | Withdrawal of rejections |
| `sections.terminalDisclaimerStatusText` | text | Terminal disclaimer status |

---

## Enriched Citation API (v3)

**Dataset:** `enriched_cited_reference_metadata`
**Version:** `1`
**Coverage:** Office actions from October 1, 2017 to April 2019 (frozen — no longer updated)

Returns NLP-parsed citation data showing which prior art references were
cited against which claims, with extracted metadata.

### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `patentApplicationNumber` | string | Application number |
| `citedDocumentIdentifier` | string | Cited patent/publication number |
| `citationCategoryCode` | string | Citation category (102 or 103) |
| `relatedClaimNumberText` | string | Claims rejected over this reference |
| `officeActionCategory` | string | Office action type (NON-FINAL, FINAL) |
| `officeActionDate` | date | Office action date |
| `passageLocationText` | string | Location of relevant passage in cited reference |
| `inventorNameText` | string | Inventor name |
| `groupArtUnitNumber` | string | Art unit number |
| `examinerCitedReferenceIndicator` | boolean | Whether examiner cited this reference |
| `applicantCitedExaminerReferenceIndicator` | boolean | Whether applicant cited examiner's reference |

**Note:** This API does NOT have a `patentNumber` field. To search by
patent number, first resolve the patent to an application number via ODP,
then search by `patentApplicationNumber`.

---

## Examples

### Find all 103 rejections for an application
```
POST /ds-api/oa_rejections/v2/records

criteria=patentApplicationNumber:16123456 AND hasRej103:1
&start=0&rows=100
```

### Find Alice Corp. 101 rejections in a specific art unit
```
criteria=groupArtUnitNumber:3689 AND aliceIndicator:1
```

### Get office action text for a patent
```
POST /ds-api/oa_actions/v1/records

criteria=patentNumber:10000000
&start=0&rows=10
```

### Find citations against a specific application
```
POST /ds-api/enriched_cited_reference_metadata/1/records

criteria=patentApplicationNumber:16123456
&start=0&rows=100
```

### Find where a specific reference was cited
```
criteria=citedDocumentIdentifier:US7654321
```

### Find rejections by art unit with 103
```
criteria=groupArtUnitNumber:3689 AND hasRej103:1
&start=0&rows=50
```

### Date range query for rejections
```
criteria=submissionDate:[2023-01-01 TO 2023-12-31] AND hasRej102:1
```

---

## Response Format

```json
{
  "response": {
    "numFound": 42,
    "start": 0,
    "docs": [
      {
        "patentApplicationNumber": "16123456",
        "actionTypeCategory": "NON-FINAL",
        "submissionDate": "2023-06-15",
        "hasRej103": true,
        ...
      }
    ]
  }
}
```

Note: The `docs` array contains the actual records. `numFound` gives the total
count of matching records for pagination.
