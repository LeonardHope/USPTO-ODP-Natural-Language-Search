# PatentsView PatentSearch API Reference

**Base URL:** `https://search.patentsview.org/api/v1`
**Auth Header:** `X-Api-Key`
**Rate Limit:** 45 requests/minute
**Methods:** GET, POST
**Data Coverage:** Granted US patents, updated quarterly (~3 month lag)

Interactive explorer: https://search.patentsview.org/swagger-ui

## Table of Contents

1. [Query Language](#query-language)
2. [Parameters](#parameters)
3. [Endpoints](#endpoints)
4. [Field Reference](#field-reference)
5. [Examples](#examples)

---

## Query Language

All queries use the `q` parameter with a JSON object.

### Current Query Status (as of March 2026)

**IMPORTANT:** Comparison operators (`_eq`, `_contains`, `_begins`, `_text_any`, `_text_all`, `_text_phrase`, `_gt`, `_gte`, `_lt`, `_lte`) are currently returning 500 errors from the API. Only **plain value matching** and **logical operators** work.

### Working Query Formats

| Format | Description | Example |
|--------|-------------|---------|
| Plain value | Exact match | `{"patent_id": "10000000"}` |
| List (OR) | Match any value in list | `{"assignees.assignee_organization": ["Tesla, Inc.", "Tesla"]}` |
| `_and` | All conditions true | `{"_and": [cond1, cond2]}` |
| `_or` | Any condition true | `{"_or": [cond1, cond2]}` |
| Text field | Text search (title) | `{"patent_title": "lidar autonomous"}` |

### Dot-Notation Field Names

Nested entity fields require dot-notation prefixes when used in queries:

| Entity | Query prefix | Example |
|--------|-------------|---------|
| Assignees | `assignees.` | `{"assignees.assignee_organization": "Tesla, Inc."}` |
| Inventors | `inventors.` | `{"inventors.inventor_name_last": "Musk"}` |
| CPC (current) | `cpc_current.` | `{"cpc_current.cpc_subclass_id": "G06N"}` |
| Attorneys | `attorneys.` | `{"attorneys.attorney_name_last": "Smith"}` |

Top-level patent fields do NOT need a prefix: `patent_id`, `patent_title`, `patent_date`, etc.

### Broken Operators (Reference Only)

These operators are documented in the API spec but currently return 500 errors:

| Operator | Description | Status |
|----------|-------------|--------|
| `_eq` | Exact match | 500 error |
| `_neq` | Not equal | 500 error |
| `_gt`, `_gte` | Greater than / greater or equal | 500 error |
| `_lt`, `_lte` | Less than / less or equal | 500 error |
| `_begins` | Starts with | 500 error |
| `_contains` | Contains substring | 500 error |
| `_text_any` | Full-text: any word matches | 500 error |
| `_text_all` | Full-text: all words must match | 500 error |
| `_text_phrase` | Full-text: exact phrase match | 500 error |
| `_not` | Negate condition | 500 error |

---

## Parameters

Every request takes up to 4 parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `q` | Yes | Query JSON object (see query formats above) |
| `f` | No | Field list: JSON array of field names to return |
| `s` | No | Sort: JSON array, e.g. `[{"patent_date": "desc"}]` |
| `o` | No | Options: `{"size": 25, "after": "cursor_value"}` |

### Options (`o`) detail:
- `size` — Results per page (default: 100, max: 1,000)
- `after` — Cursor for pagination (from previous response)
- `exclude_withdrawn` — Boolean (default: true)
- `pad_patent_id` — Pad patent IDs to 8 chars (default: false)

### Response Structure

The API returns nested arrays for entity data regardless of requested fields:

```json
{
  "patents": [
    {
      "patent_id": "10000000",
      "patent_title": "...",
      "assignees": [
        {"assignee_organization": "Tesla, Inc.", "assignee_type": "3", ...}
      ],
      "inventors": [
        {"inventor_name_first": "Elon", "inventor_name_last": "Musk", ...}
      ],
      "cpc_current": [
        {"cpc_subclass_id": "G06N", "cpc_group_id": "G06N3/08", ...}
      ]
    }
  ],
  "count": 25,
  "total_hits": 1432
}
```

---

## Endpoints

### Granted Patents

| Endpoint | Response Key | Description |
|----------|-------------|-------------|
| `/patent/` | `patents` | Core patent search |
| `/patent/us_patent_citation/` | `us_patent_citations` | US patent citations |
| `/patent/us_application_citation/` | `us_application_citations` | Pre-grant pub citations |
| `/patent/foreign_citation/` | `foreign_citations` | Foreign document citations |
| `/patent/other_reference/` | `other_references` | Non-patent literature refs |
| `/patent/rel_app_text/` | `rel_app_texts` | Related application text |

### Pre-grant Publications

| Endpoint | Response Key | Description |
|----------|-------------|-------------|
| `/publication/` | `publications` | Published application search |
| `/publication/rel_app_text/` | `rel_app_texts` | Related application text |

### Entity Lookups

| Endpoint | Response Key | Description |
|----------|-------------|-------------|
| `/inventor/` | `inventors` | Disambiguated inventor profiles |
| `/assignee/` | `assignees` | Assignee/company profiles |
| `/patent/attorney/` | `attorneys` | Attorney/firm profiles |
| `/location/` | `locations` | Geographic locations |

### Classification

| Endpoint | Response Key | Description |
|----------|-------------|-------------|
| `/cpc_class/` | `cpc_classes` | CPC class lookup |
| `/cpc_subclass/` | `cpc_subclasses` | CPC subclass lookup |
| `/cpc_group/` | `cpc_groups` | CPC group lookup |
| `/uspc_mainclass/` | `uspc_mainclasses` | USPC main class |
| `/uspc_subclass/` | `uspc_subclasses` | USPC subclass |
| `/wipo/` | `wipos` | WIPO field lookup |

### Full Text (separate endpoints)

| Endpoint | Response Key | Description |
|----------|-------------|-------------|
| `/g_brf_sum_text/` | `patent_id`, `summary_text` | Brief summary (granted) |
| `/g_claim/` | `patent_id`, `claim_text` | Claims (granted) |
| `/g_detail_desc_text/` | `patent_id`, `description_text` | Detailed description (granted) |
| `/g_draw_desc_text/` | `patent_id`, `draw_desc_text` | Drawing descriptions (granted) |
| `/pg_brf_sum_text/` | `document_number`, `summary_text` | Brief summary (pre-grant) |
| `/pg_claim/` | `document_number`, `claim_text` | Claims (pre-grant) |
| `/pg_detail_desc_text/` | `document_number`, `description_text` | Detailed description (pre-grant) |

---

## Field Reference

### Patent Core Fields (top-level, no prefix needed)
- `patent_id` (string) — Patent number
- `patent_title` (text) — Title (supports text search via plain value)
- `patent_date` (date) — Grant date (YYYY-MM-DD)
- `patent_year` (integer) — Grant year
- `patent_type` (string) — utility, design, plant, reissue, etc.
- `patent_abstract` (text) — Abstract
- `withdrawn` (boolean) — Whether patent was withdrawn
- `patent_num_us_patents_cited` (integer) — Forward citations count
- `patent_num_times_cited_by_us_patents` (integer) — Backward citations count
- `patent_processing_days` (integer) — Days from filing to grant

### Inventor Fields (nested under `inventors[]`, query with `inventors.` prefix)
- `inventor_name_first`, `inventor_name_last` (text)
- `inventor_city`, `inventor_state`, `inventor_country` (string)
- `inventor_id` (string) — Disambiguated ID

### Assignee Fields (nested under `assignees[]`, query with `assignees.` prefix)
- `assignee_organization` (text) — Company name
- `assignee_type` (string) — Type code
- `assignee_city`, `assignee_state`, `assignee_country` (string)

### Application Fields (nested under patent)
- `application_id` (string) — Application number
- `filing_date` (date)
- `filing_type` (string)
- `series_code` (string)

### CPC Fields (nested under `cpc_current[]`, query with `cpc_current.` prefix)
- `cpc_subclass_id` (string) — e.g. "H04L" (was `cpc_subclass`)
- `cpc_group_id` (string) — e.g. "H04L9/00" (was `cpc_group`)
- `cpc_type` (string) — inventional or additional

### Attorney Fields (nested under `attorneys[]`, query with `attorneys.` prefix)
- `attorney_name_first`, `attorney_name_last` (text)
- `attorney_organization` (text) — Law firm name

### Examiner Fields (nested)
- `examiner_first_name`, `examiner_last_name` (text)
- `examiner_id` (string)
- `art_group` (string) — Art unit

### Citation Fields (from citation endpoints)
- `citation_patent_id` (string) — Cited patent
- `citation_category` (string) — cited by examiner, applicant, etc.
- `citation_date` (date)
- `citation_sequence` (integer)

### Inventor Profile Fields (from /inventor/ endpoint)
- `inventor_num_patents` (integer)
- `inventor_num_assignees` (integer)
- `inventor_years_active` (integer)
- `inventor_first_seen_date`, `inventor_last_seen_date` (date)
- `inventor_gender_code` (string) — F/M/U

### Assignee Profile Fields (from /assignee/ endpoint)
- `assignee_num_patents` (integer)
- `assignee_num_inventors` (integer)
- `assignee_years_active` (integer)
- `assignee_first_seen_date`, `assignee_last_seen_date` (date)

---

## Examples

### Search by assignee (exact match)
```
GET /api/v1/patent/?q={"assignees.assignee_organization":"Tesla, Inc."}&f=["patent_id","patent_title","patent_date"]&s=[{"patent_date":"desc"}]&o={"size":10}
```

### Search by assignee (fuzzy — OR list of name variants)
```
GET /api/v1/patent/?q={"assignees.assignee_organization":["Tesla","Tesla, Inc.","Tesla Inc.","Tesla LLC","Tesla Corp."]}&f=["patent_id","patent_title","patent_date"]&o={"size":10}
```

### Search by inventor
```
GET /api/v1/patent/?q={"_and":[{"inventors.inventor_name_last":"Katz"},{"inventors.inventor_name_first":"James"}]}&f=["patent_id","patent_title"]
```

### Keyword search (title)
```
GET /api/v1/patent/?q={"patent_title":"autonomous vehicle lidar"}&f=["patent_id","patent_title","patent_abstract"]&o={"size":25}
```

### Get citations for a patent
```
GET /api/v1/patent/us_patent_citation/?q={"patent_id":"10000000"}&f=["patent_id","citation_patent_id","citation_category","citation_date"]
```

### Find patents citing a specific patent
```
GET /api/v1/patent/us_patent_citation/?q={"citation_patent_id":"7654321"}&f=["patent_id","citation_patent_id","citation_date"]
```

### Look up an inventor profile
```
GET /api/v1/inventor/?q={"inventors.inventor_name_last":"Doe"}&f=["inventor_id","inventor_name_first","inventor_name_last","inventor_num_patents"]
```

### CPC classification search
```
GET /api/v1/patent/?q={"cpc_current.cpc_subclass_id":"G06N"}&f=["patent_id","patent_title"]&o={"size":50}
```

### Search pre-grant publications
```
GET /api/v1/publication/?q={"publication_title":"autonomous driving lidar"}&f=["document_number","publication_title","publication_date"]
```

---

## Response Format

All responses follow this structure:

```json
{
  "patents": [...],         // Array of results (key name matches endpoint)
  "count": 25,              // Records in this response
  "total_hits": 1432        // Total matching records
}
```

Patent records contain nested arrays for related entities:
```json
{
  "patent_id": "10000000",
  "patent_title": "...",
  "assignees": [{"assignee_organization": "...", ...}],
  "inventors": [{"inventor_name_first": "...", "inventor_name_last": "...", ...}],
  "cpc_current": [{"cpc_subclass_id": "G06N", "cpc_group_id": "G06N3/08", ...}]
}
```

For pagination, use the last record's sort values as the `after` cursor in the next request's `o` parameter.
