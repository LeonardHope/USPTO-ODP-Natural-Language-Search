# USPTO Open Data Portal -- Patent File Wrapper API Reference

**Base URL:** `https://api.uspto.gov`
**Auth Header:** `X-Api-Key`
**Rate Limit:** 60 requests/minute (4/min for PDF/ZIP downloads)
**Methods:** GET, POST
**Data Coverage:** All US patent applications (real-time, updated daily)

Swagger docs: https://data.uspto.gov/swagger/index.html

## Table of Contents

1. [Authentication](#authentication)
2. [Application Search](#application-search)
3. [Application Details](#application-details)
4. [File Wrapper Documents](#file-wrapper-documents)
5. [Continuity Data](#continuity-data)
6. [Patent Term Adjustment](#patent-term-adjustment)
7. [Assignments](#assignments)
8. [Response Format](#response-format)

---

## Authentication

All requests require the `X-Api-Key` header with your ODP API key.

```
GET /api/v1/patent/applications/search?q=16123456
X-Api-Key: your_api_key_here
```

---

## Application Search

**Endpoint:** `GET /api/v1/patent/applications/search`

Search patent applications using free-text search.

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Free-text search across all fields |
| `start` | integer | Pagination offset (default: 0) |
| `rows` | integer | Results per page (default: 25) |

**Important:** Named filter parameters like `applicationNumberText`,
`patentNumber`, `inventorNameText`, etc. are NOT supported on the search
endpoint. All search terms must go in the `q` free-text parameter.

### Example
```
GET /api/v1/patent/applications/search?q=autonomous vehicle&rows=10
```

---

## Application Details

**Endpoint:** `GET /api/v1/patent/applications/{applicationNumber}`

Get full metadata for a specific application. This is a direct lookup
endpoint (not a search) — provide the application serial number directly.

### Response Structure

The response is a deeply nested object. Key data is inside `applicationMetaData`:

```json
{
  "applicationMetaData": {
    "applicationStatusCode": 150,
    "applicationStatusDescriptionText": "Patented Case",
    "applicationTypeCode": "UTL",
    "filingDate": "2020-01-15",
    "inventionTitle": "...",
    "patentNumber": "11234567",
    "grantDate": "2023-05-16",
    ...
  },
  "inventorBag": [...],
  "assignmentBag": [...],
  "continuityBag": [...],
  ...
}
```

### Example
```
GET /api/v1/patent/applications/16123456
```

---

## File Wrapper Documents

**Endpoint:** `GET /api/v1/patent/applications/{applicationNumber}/documents`

Get the list of prosecution history documents (the "file wrapper").

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `start` | integer | Pagination offset |
| `rows` | integer | Documents per page (default: 50) |

### Document Types (common)

| Code | Description |
|------|-------------|
| `CTNF` | Non-Final Rejection |
| `CTFR` | Final Rejection |
| `NOA` | Notice of Allowance |
| `CLM` | Claims |
| `SPEC` | Specification |
| `DRW` | Drawings |
| `IDS` | Information Disclosure Statement |
| `1449` | IDS Form 1449 |
| `892` | Examiner References (Form 892) |
| `AMD` | Amendment |
| `RCEX` | Request for Continued Examination |
| `PET` | Petition |
| `ISSUE` | Issue Notification |
| `ABR` | Appeal Brief |

### Individual Document

**Endpoint:** `GET /api/v1/patent/applications/{applicationNumber}/documents/{documentId}`

Returns metadata for a specific document. PDF download URL is in the
`downloadOptionBag` array.

### Example
```
GET /api/v1/patent/applications/16123456/documents?rows=100
```

---

## Continuity Data

**Endpoint:** `GET /api/v1/patent/applications/{applicationNumber}/continuity`

Get the family tree of related applications: continuations, continuations-in-part, divisionals, and provisionals.

### Response Structure

The response includes both parent and child application chains:

- **Parent applications** -- Applications this one claims priority from
  - `parentApplicationNumber`
  - `claimType` (continuation, CIP, divisional, provisional)
  - `filingDate`
  - `patentNumber` (if granted)

- **Child applications** -- Applications that claim priority from this one
  - `childApplicationNumber`
  - `claimType`
  - `filingDate`
  - `patentNumber` (if granted)

### Example
```
GET /api/v1/patent/applications/16123456/continuity
```

---

## Patent Term Adjustment

**Endpoint:** `GET /api/v1/patent/applications/{applicationNumber}/patent-term-adjustment`

Get PTA/PTE data showing adjustments to the patent term based on USPTO processing delays.

### Response Fields (typical)

- `totalPtaDays` -- Total patent term adjustment in days
- `aDelay` -- A delay days (failure to act within 14 months)
- `bDelay` -- B delay days (failure to issue within 3 years)
- `cDelay` -- C delay days (delays due to interference, appeal, etc.)
- `overlap` -- Overlap reduction days
- `applicantDelay` -- Applicant-caused delay reduction

### Example
```
GET /api/v1/patent/applications/16123456/patent-term-adjustment
```

---

## Assignments

**Endpoint:** `GET /api/v1/patent/applications/{applicationNumber}/assignment`

Get patent assignment (ownership transfer) records for an application.

See `references/assignment-api.md` for detailed field documentation.

### Example
```
GET /api/v1/patent/applications/14643719/assignment
```

---

## Response Format

### Search Results
```json
{
  "count": 297618,
  "patentFileWrapperDataBag": [
    {
      "applicationMetaData": {...},
      "eventDataBag": [...],
      ...
    }
  ],
  "requestIdentifier": "..."
}
```

The key response fields:
- `count` -- Total matching records
- `patentFileWrapperDataBag` -- Array of application records
- `requestIdentifier` -- Unique request ID

### Single Application
Returns the full application object directly (not wrapped in a bag).

### Error Responses
- `401` -- Invalid or missing API key
- `404` -- Application not found
- `429` -- Rate limit exceeded (wait and retry)
- `500` -- Server error (retry with backoff)

---

## Key Differences from PatentsView

| Aspect | ODP File Wrapper | PatentsView |
|--------|-----------------|-------------|
| Coverage | All applications (pending + granted) | Granted patents only |
| Update frequency | Daily | Quarterly |
| Prosecution docs | Yes (full file wrapper) | No |
| Continuity data | Yes | No |
| Assignments | Yes (per-application) | No |
| Name disambiguation | No | Yes |
| Analytics-friendly | Limited (free-text only) | Yes (structured queries) |
| Best for | Specific application lookup | Broad searches, analytics |
