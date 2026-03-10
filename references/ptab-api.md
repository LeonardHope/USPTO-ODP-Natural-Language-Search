# USPTO PTAB API Reference (hosted on ODP)

**Base URL:** `https://api.uspto.gov`
**Auth Header:** `X-Api-Key` (ODP key)
**Rate Limit:** 60 requests/minute
**Data Coverage:** All public PTAB proceedings since September 2012
**Portal:** https://data.uspto.gov/ptab

## Table of Contents

1. [Overview](#overview)
2. [Proceeding Types](#proceeding-types)
3. [Endpoints](#endpoints)
4. [Search Parameters](#search-parameters)
5. [Response Structure](#response-structure)
6. [Response Fields](#response-fields)
7. [Examples](#examples)

---

## Overview

The PTAB (Patent Trial and Appeal Board) API provides access to post-grant proceedings including:
- Inter Partes Review (IPR)
- Post-Grant Review (PGR)
- Covered Business Method review (CBM)
- Derivation proceedings (DER)
- Ex parte appeals
- Interferences

Data syncs in near-real-time with the Patent Trial and Appeal Case Tracking System.

---

## Proceeding Types

| Code | Type | Description |
|------|------|-------------|
| `IPR` | Inter Partes Review | Challenge patent validity based on prior art (patents/printed pubs) |
| `PGR` | Post-Grant Review | Broader validity challenge within 9 months of grant |
| `CBM` | Covered Business Method | Challenge CBM patent validity (program ended 2020) |
| `DER` | Derivation | Dispute over who invented first |

Trial numbers follow the format: `TYPE-YEAR-NNNNN` (e.g., `IPR2020-00001`)

---

## Endpoints

### Search Proceedings
`GET /api/v1/patent/trials/proceedings/search`

Search across all PTAB proceedings. Uses `q` free-text parameter with
`offset`/`limit` pagination.

**Note:** Named filter parameters like `patentNumber` and `partyName` are
silently ignored by this endpoint. All search terms must go in the `q`
free-text parameter.

### Get Proceeding Details
`GET /api/v1/patent/trials/proceedings/{trialNumber}`

Get full details for a specific proceeding.

### Search Decisions
`GET /api/v1/patent/trials/decisions/search`

Full-text search within PTAB decision documents. Same `q`/`offset`/`limit`
pattern as proceedings search.

---

## Search Parameters

The search endpoints use free-text search via the `q` parameter. Named
filter parameters are NOT supported — all search terms go in `q`.

### Proceedings Search

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Free-text search (patent number, party name, trial number, etc.) |
| `offset` | integer | Pagination offset (default: 0) |
| `limit` | integer | Results per page (default: 25) |

### Decisions Search

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Free-text search in decision content |
| `offset` | integer | Pagination offset (default: 0) |
| `limit` | integer | Results per page (default: 25) |

---

## Response Structure

### Proceedings Search Response

```json
{
  "count": 1,
  "requestIdentifier": "...",
  "patentTrialProceedingDataBag": [
    {
      "trialNumber": "IPR2026-00286",
      "patentOwnerData": {
        "patentNumber": "10585959",
        "grantDate": "2020-03-10",
        "technologyCenterNumber": "2100",
        "groupArtUnitNumber": "2166",
        "applicationNumberText": "16553900",
        "inventorName": "Robert Osann JR."
      },
      "trialMetaData": {
        "trialTypeCode": "IPR",
        "trialStatusCategory": "Pending",
        "petitionFilingDate": "2026-03-06",
        "trialLastModifiedDate": "2026-03-06",
        "fileDownloadURI": "https://api.uspto.gov/..."
      },
      "regularPetitionerData": {
        "realPartyInInterestName": "Google LLC",
        "counselName": "Hunt, Elisabethet al"
      }
    }
  ]
}
```

### Decisions Search Response

```json
{
  "count": 5,
  "requestIdentifier": "...",
  "patentTrialDecisionDataBag": [...]
}
```

---

## Response Fields

### Proceeding Record (inside `patentTrialProceedingDataBag[]`)

- `trialNumber` — PTAB trial number (e.g. "IPR2026-00286")
- `lastModifiedDateTime` — Last modification timestamp

**Patent Owner Data** (`patentOwnerData`):
- `patentNumber` — Patent at issue
- `grantDate` — Patent grant date
- `technologyCenterNumber` — USPTO technology center
- `groupArtUnitNumber` — Art unit
- `applicationNumberText` — Related application number
- `inventorName` — Inventor name

**Trial Metadata** (`trialMetaData`):
- `trialTypeCode` — IPR, PGR, CBM, DER
- `trialStatusCategory` — Current status (Pending, Instituted, FWD, Terminated, etc.)
- `petitionFilingDate` — Petition filing date
- `trialLastModifiedDate` — Last modification date
- `fileDownloadURI` — URL to download trial files (ZIP)

**Petitioner Data** (`regularPetitionerData`):
- `realPartyInInterestName` — Real party in interest
- `counselName` — Petitioner's counsel

---

## Examples

### Find all proceedings for a patent
```
GET /api/v1/patent/trials/proceedings/search?q=10585959&limit=25
```

### Search by party name
```
GET /api/v1/patent/trials/proceedings/search?q=Samsung&limit=25
```

### Full-text search in PTAB decisions
```
GET /api/v1/patent/trials/decisions/search?q=claim construction broadest reasonable interpretation
```

### Get details for a specific trial
```
GET /api/v1/patent/trials/proceedings/IPR2020-00001
```

### Search for IPR proceedings involving a company
```
GET /api/v1/patent/trials/proceedings/search?q=Qualcomm IPR&limit=25
```

---

## Common Proceeding Statuses

| Status | Meaning |
|--------|---------|
| `Pending` | Petition filed, awaiting institution decision |
| `Instituted` | PTAB agreed to review |
| `FWD Coverage` | Final Written Decision issued |
| `Terminated` | Proceeding ended (settlement, dismissal, etc.) |
| `Denied` | Institution denied |
| `Settled` | Parties reached settlement |

---

## Use Cases for Patent Lawyers

1. **Pre-litigation research**: Check if a patent has survived PTAB challenges
2. **Validity assessment**: Review final written decisions for claim-by-claim analysis
3. **Competitive intelligence**: Monitor a competitor's patents for challenges
4. **Due diligence**: Check PTAB history before patent acquisition
5. **Strategy**: Analyze success rates by technology area or patent owner
