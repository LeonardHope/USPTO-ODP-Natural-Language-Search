# USPTO Patent Assignment Data Reference (via ODP)

**Endpoint:** `https://api.uspto.gov/api/v1/patent/applications/{applicationNumber}/assignment`
**Auth Header:** `X-Api-Key` (ODP key)
**Rate Limit:** 60 requests/minute
**Data Coverage:** All recorded patent assignments

**Note:** The old Assignment Search API (`assignment-api.uspto.gov`) has been
decommissioned. Assignment data is now accessed via the ODP File Wrapper API
on a per-application basis. Broad searches by assignee name, date range, etc.
are no longer supported via API — only per-application lookups.

Assignment Center web UI: https://assignmentcenter.uspto.gov/search/patent

## Table of Contents

1. [Overview](#overview)
2. [How to Access Assignment Data](#how-to-access-assignment-data)
3. [Response Structure](#response-structure)
4. [Response Fields](#response-fields)
5. [Examples](#examples)
6. [Use Cases](#use-cases)

---

## Overview

Patent assignment records document ownership transfers. Every time a patent
or application is sold, assigned, licensed, or has a security interest
recorded, that transaction is recorded in the USPTO assignment database.

This is the definitive source for "chain of title" — tracing who has owned
a patent from the original inventor to the current owner.

---

## How to Access Assignment Data

Assignment data is accessed through the ODP File Wrapper API. The endpoint
only supports per-application lookups — there is no broad search endpoint.

**To get assignments for a known application number:**
```
GET /api/v1/patent/applications/{applicationNumber}/assignment
X-Api-Key: your_odp_key
```

**To get assignments for a patent number:**
1. First resolve the patent to an application number via ODP search:
   `GET /api/v1/patent/applications/search?q={patentNumber}`
2. Extract `applicationNumberText` from the response
3. Then fetch assignments using the application number endpoint above

The `assignment_search.py` script handles this resolution automatically.

---

## Response Structure

```json
{
  "count": 1,
  "patentFileWrapperDataBag": [
    {
      "applicationNumberText": "14643719",
      "assignmentBag": [
        {
          "conveyanceText": "ASSIGNMENT OF ASSIGNOR'S INTEREST",
          "assignmentRecordedDate": "2015-03-10",
          "assigneeBag": [...],
          "assignorBag": [...],
          ...
        }
      ]
    }
  ]
}
```

The key structure is:
- `patentFileWrapperDataBag[]` — wrapper array (typically one entry per application)
  - `applicationNumberText` — the application number
  - `assignmentBag[]` — array of assignment records for that application

---

## Response Fields

### Assignment Record (inside `assignmentBag[]`)

| Field | Description |
|-------|-------------|
| `conveyanceText` | Type of transfer (see common types below) |
| `assignmentRecordedDate` | Date the assignment was recorded at USPTO |
| `assignmentReceivedDate` | Date the assignment was received |
| `assignmentMailedDate` | Date the assignment confirmation was mailed |
| `reelAndFrameNumber` | Recording identification (e.g. "035130/0327") |
| `reelNumber` | Reel number |
| `frameNumber` | Frame number |
| `pageTotalQuantity` | Number of pages in the recorded document |
| `attorneyDocketNumber` | Attorney docket number |
| `imageAvailableStatusCode` | Whether document image is available |
| `assignmentDocumentLocationURI` | URL to download the assignment document |

### Assignee Record (inside `assigneeBag[]`)

| Field | Description |
|-------|-------------|
| `assigneeNameText` | Name of party receiving rights |
| `assigneeAddress.addressLineOneText` | Street address |
| `assigneeAddress.cityName` | City |
| `assigneeAddress.geographicRegionName` | State/province |
| `assigneeAddress.postalCode` | ZIP/postal code |
| `assigneeAddress.countryName` | Country |

### Assignor Record (inside `assignorBag[]`)

| Field | Description |
|-------|-------------|
| `assignorName` | Name of party transferring rights |
| `executionDate` | Date the assignment was signed |

### Correspondence Address

| Field | Description |
|-------|-------------|
| `correspondenceAddress.correspondentNameText` | Contact name |
| `correspondenceAddress.addressLineOneText` | Address line 1 |
| `correspondenceAddress.addressLineTwoText` | Address line 2 |

### Common Conveyance Types

| Conveyance | Meaning |
|------------|---------|
| `ASSIGNMENT OF ASSIGNOR'S INTEREST` | Standard patent assignment |
| `SECURITY INTEREST` | Patent used as loan collateral |
| `RELEASE OF SECURITY INTEREST` | Security interest released |
| `CHANGE OF NAME` | Company name change |
| `MERGER` | Corporate merger |
| `LICENSE` | License grant (sometimes recorded) |
| `NUNC PRO TUNC ASSIGNMENT` | Retroactive assignment |
| `CORRECTIVE ASSIGNMENT` | Fix to a prior recording |

---

## Examples

### Get ownership chain for a patent (via script)
```bash
python assignment_search.py chain 10000000
```

### Get assignments for an application (direct API call)
```
GET /api/v1/patent/applications/14643719/assignment
X-Api-Key: your_key
```

### Search company assignments (via script)
```bash
python assignment_search.py company "Apple Inc"
```

This searches ODP for applications mentioning the company, then
fetches assignment records for each match.

---

## Limitations of ODP Assignment Endpoint

The old `assignment-api.uspto.gov` supported broad searches by assignee name,
date range, conveyance type, and free text. The ODP endpoint does not:

| Feature | Old API | ODP |
|---------|---------|-----|
| Search by patent number | Yes | Yes (via resolution) |
| Search by application number | Yes | Yes (direct) |
| Search by assignee name | Yes | No (workaround via ODP search) |
| Search by assignor name | Yes | No |
| Search by date range | Yes | No |
| Search by conveyance type | Yes | No |
| Free-text search | Yes | No |

The `assignment_search.py` script provides workaround functions that search
ODP for applications matching a company name, then fetch assignment records
for each result. This is less comprehensive but functional.

---

## Use Cases for Patent Lawyers

### 1. Chain of Title Analysis
Before litigation or licensing, verify the complete ownership chain from
inventor to current owner. Look for gaps, incorrect assignments, or
missing parties.

Search by patent number and review all assignments chronologically.

### 2. Due Diligence for Patent Acquisition
When a client is buying patents, verify:
- Current ownership is clean
- No unreleased security interests
- No conflicting assignments
- All inventors properly assigned their rights

### 3. Merger & Acquisition Support
Track patent portfolio transfers during M&A:
- Search by assignor (selling company) to see what they've transferred
- Search by assignee (buying company) to see what they've acquired
- Check for bulk assignments (many patents in one reel/frame)

### 4. Security Interest Monitoring
Track patents used as loan collateral:
- Search for `SECURITY INTEREST` conveyances involving a company
- Check for corresponding `RELEASE OF SECURITY INTEREST` records
- Unreleased security interests can affect patent enforceability

### 5. Competitive Intelligence
Monitor a competitor's patent activity:
- New acquisitions (as assignee)
- Patent sales or divestitures (as assignor)
- Licensing activity (if recorded)
- Security interests (financial health indicator)
