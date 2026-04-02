# USPTO Open Data Portal -- Complete API Reference

**Extracted from live Swagger specs at `https://data.uspto.gov/swagger/`**

---

## API Families Overview

The ODP Swagger UI exposes 6 API definitions in a dropdown selector:

| # | API Name | Spec File URL | Base URL |
|---|----------|--------------|----------|
| 1 | Open Data Portal API | `https://data.uspto.gov/swagger/swagger.yaml` | `https://api.uspto.gov` |
| 2 | TSDR API | `https://data.uspto.gov/swagger/tsdr-swagger.yaml` | `https://tsdrapi.uspto.gov` |
| 3 | Office Action Rejection API | `https://data.uspto.gov/swagger/oa-rejections.yaml` | `https://api.uspto.gov` |
| 4 | Office Action Text Retrieval API | `https://data.uspto.gov/swagger/oa-text-retrieval.yaml` | `https://api.uspto.gov` |
| 5 | Office Action Citations API | `https://data.uspto.gov/swagger/oa-citations.yaml` | `https://api.uspto.gov` |
| 6 | Enriched Citation API v3 | `https://data.uspto.gov/swagger/oa-enriched-citations.yaml` | `https://api.uspto.gov` |

The main ODP spec (swagger.yaml) references these sub-files via `$ref`:
- `./odp-common-base.yaml` -- All shared schemas (request/response types)
- `./trial-proceedings.yaml` -- PTAB Trial Proceedings endpoints
- `./trial-decisions.yaml` -- PTAB Trial Decisions endpoints
- `./trial-documents.yaml` -- PTAB Trial Documents endpoints
- `./trial-appeal-decisions.yaml` -- PTAB Appeals endpoints
- `./trial-interferences.yaml` -- PTAB Interferences endpoints

All specs are OpenAPI 3.0.1.

---

## Authentication

All ODP APIs (except TSDR) use the same auth scheme:

```
Header: X-API-KEY: <your_api_key>
```

TSDR API uses a different header:

```
Header: USPTO-API-KEY: <your_api_key>
```

Get your ODP key at: https://data.uspto.gov/myodp

Security scheme definition:
```yaml
securitySchemes:
  ApiKeyAuth:
    type: apiKey
    in: header
    name: X-API-KEY
```

---

## Rate Limits (from data.uspto.gov/apis/api-rate-limits)

Three API categories with separate limits:

### Meta Data Retrieval APIs
- Includes: Patent File Wrapper (Application Data, Continuity, Transactions, PTA, Attorney, Assignments, Foreign Priority, Associated Documents), Bulk Datasets Product Data, Final Petition Decisions (Search, Document Data, Download)
- Limit: **5 million calls per week** (combined across all meta data APIs)
- Resets: Sunday at midnight UTC

### Patent File Wrapper Documents API
- Limit: **1,200,000 calls per week**
- Resets: Sunday at midnight UTC

### Bulk Datasets Downloads API
- Same file: **20 downloads per year per API key** (except XML files which have a higher limit)
- Rate: **5 files per 10 seconds** from the same IP
- Files use signed redirect URLs that expire in 5 seconds

### General Throttling
- **Burst: 1** -- No parallel requests per API key. Wait for each call to complete.
- **Rate: 4 to 15 requests/second** depending on API call type
- Concurrent calls with the same key are blocked
- HTTP 429 on limit exceeded -- wait at least 5 seconds before retrying

---

## 1. PATENT FILE WRAPPER API (ODP Core)

Base URL: `https://api.uspto.gov`

### Complete Endpoint List

#### 1.1 Patent Application Search

**POST /api/v1/patent/applications/search**
Search patent applications by supplying JSON payload.

Request body (`PatentSearchRequest`):
```json
{
  "q": "applicationMetaData.applicationTypeLabelName:Utility",
  "filters": [
    {
      "name": "applicationMetaData.applicationStatusDescriptionText",
      "value": ["Patented Case"]
    }
  ],
  "rangeFilters": [
    {
      "field": "applicationMetaData.grantDate",
      "valueFrom": "2010-08-04",
      "valueTo": "2022-08-04"
    }
  ],
  "sort": [
    {
      "field": "applicationMetaData.filingDate",
      "order": "desc"
    }
  ],
  "fields": ["applicationNumberText", "applicationMetaData.filingDate"],
  "pagination": {
    "offset": 0,
    "limit": 25
  },
  "facets": ["applicationMetaData.applicationTypeLabelName"]
}
```

All fields in the request body are optional.

Response (`PatentDataResponse`):
```json
{
  "count": 297618,
  "patentFileWrapperDataBag": [ ... ],
  "requestIdentifier": "..."
}
```

---

**GET /api/v1/patent/applications/search**
Patent application search by supplying query parameters.

| Parameter | In | Type | Description | Example |
|-----------|----|------|-------------|---------|
| `q` | query | string | Boolean search (AND, OR, NOT), wildcards (*), exact phrases (""). Field-value syntax: `fieldName:value` | `applicationMetaData.applicationTypeLabelName:Utility` |
| `filters` | query | string | Single value: `fieldName value`. Multi value: `fieldName val1,val2` | `applicationMetaData.applicationTypeCode UTL,DES` |
| `rangeFilters` | query | string | Date range: `fieldName yyyy-MM-dd:yyyy-MM-dd`. Number range: `fieldName num1:num2` | `applicationMetaData.grantDate 2010-01-01:2011-01-01` |
| `sort` | query | string | Field followed by sort order | `applicationMetaData.filingDate asc` |
| `offset` | query | integer | Page offset (min 0, default 0) | `0` |
| `limit` | query | integer | Max results (min 1, default 25) | `25` |
| `fields` | query | string | Comma-separated field names to return | `applicationNumberText,applicationMetaData.filingDate` |
| `facets` | query | string | Comma-separated fields to aggregate | `applicationMetaData.applicationTypeLabelName` |

---

#### 1.2 Patent Application Download

**POST /api/v1/patent/applications/search/download**
Download patent data as JSON or CSV file.

Request body (`PatentDownloadRequest`): Same as `PatentSearchRequest` plus:
```json
{
  "format": "json"
}
```
`format` enum: `json`, `csv`

**GET /api/v1/patent/applications/search/download**
Download via query parameters (same params as search GET + `format`).

---

#### 1.3 Single Application Lookup

**GET /api/v1/patent/applications/{applicationNumberText}**
Full patent application data for a specific application number.

| Parameter | In | Type | Required | Description |
|-----------|----|------|----------|-------------|
| `applicationNumberText` | path | string | yes | Patent application number (e.g., `16330077`) |

---

#### 1.4 Application Sub-Resources

All use: **GET /api/v1/patent/applications/{applicationNumberText}/...**

| Endpoint Suffix | Description | Response Schema |
|----------------|-------------|-----------------|
| `/meta-data` | Patent application meta data | `ApplicationMetaData` |
| `/adjustment` | Patent term adjustment data | `PatentTermAdjustment` |
| `/assignment` | Patent assignment data | `Assignment` |
| `/attorney` | Attorney/agent data | `RecordAttorney` |
| `/continuity` | Continuity data (parent/child chains) | `ParentContinuityData`, `ChildContinuityData` |
| `/foreign-priority` | Foreign priority claims | `ForeignPriority` |
| `/transactions` | Transaction history | `EventData` |
| `/documents` | Prosecution history documents | `DocumentBag` |
| `/associated-documents` | Grant/publication XML metadata | `PGPubFileMetaData`, `GrantFileMetaData` |

All take `applicationNumberText` as path parameter (string, required).

---

#### 1.5 Status Codes

**POST /api/v1/patent/status-codes**
Search patent application status codes.

**GET /api/v1/patent/status-codes**
Search patent application status codes by query parameters.

Response: `StatusCodeSearchResponse`

---

### Key Request/Response Schemas

#### PatentSearchRequest
```yaml
type: object
properties:
  q:              # string -- opensearch query syntax
  filters:        # array of Filter objects
  rangeFilters:   # array of Range objects
  sort:           # array of Sort objects
  fields:         # array of strings
  pagination:     # Pagination object
  facets:         # array of strings
```

#### Filter
```yaml
type: object
properties:
  name:   # string -- field path (e.g., "applicationMetaData.applicationStatusDescriptionText")
  value:  # array of strings (e.g., ["Patented Case"])
```

#### Range
```yaml
type: object
properties:
  field:     # string -- field path (e.g., "applicationMetaData.grantDate")
  valueFrom: # string -- start value (dates: "yyyy-MM-dd")
  valueTo:   # string -- end value
```

#### Sort
```yaml
type: object
properties:
  field: # string -- field path
  order: # string -- enum: [Asc, asc, Desc, desc]
```

#### Pagination
```yaml
type: object
properties:
  offset: # integer, min 0, default 0
  limit:  # integer, min 1, default 25
```

#### ApplicationMetaData Fields
```
nationalStageIndicator, entityStatusData, publicationDateBag,
publicationSequenceNumberBag, publicationCategoryBag, docketNumber,
firstInventorToFileIndicator, firstApplicantName, firstInventorName,
applicationConfirmationNumber, applicationStatusDate,
applicationStatusDescriptionText, filingDate, effectiveFilingDate,
grantDate, groupArtUnitNumber, applicationTypeCode,
applicationTypeLabelName, applicationTypeCategory, inventionTitle,
patentNumber, applicationStatusCode, earliestPublicationNumber,
earliestPublicationDate, pctPublicationNumber, pctPublicationDate,
internationalRegistrationPublicationDate, internationalRegistrationNumber,
examinerNameText, class, subclass, uspcSymbolText, customerNumber,
cpcClassificationBag, applicantBag, inventorBag
```

#### PatentDataResponse
```yaml
type: object
properties:
  count:                     # integer -- total matching records
  patentFileWrapperDataBag:  # array of application objects
    # Each item contains:
    #   applicationNumberText: string
    #   applicationMetaData: ApplicationMetaData
    #   correspondenceAddressBag: array
    #   patentTermAdjustmentData: PatentTermAdjustment
    #   assignmentBag: array of Assignment
    #   recordAttorneyBag: array of RecordAttorney
    #   parentContinuityBag: array of ParentContinuityData
    #   childContinuityBag: array of ChildContinuityData
    #   foreignPriorityBag: array of ForeignPriority
    #   eventDataBag: array of EventData
    #   documentBag: DocumentBag
    #   pgpubDocumentMetaData: PGPubFileMetaData
    #   grantDocumentMetaData: GrantFileMetaData
  requestIdentifier: # string -- UUID
```

#### Error Responses (all endpoints)

| Code | Name | Example errorDetails |
|------|------|---------------------|
| 400 | Bad Request | "Invalid request, review patent data request filter section and try again" |
| 403 | Forbidden | (no details) |
| 404 | Not Found | "No matching records found, refine your search criteria and try again" |
| 413 | Payload Too Large | "Too many records found, try adding more filters to narrow search" |
| 500 | Internal Server Error | "Internal Server Error. Please contact Help Desk." |

All error responses include `code`, `error`, `errorDetails` (or `errorDetailed`), and `requestIdentifier`.

---

## 2. BULK DATASETS API

Base URL: `https://api.uspto.gov`

**GET /api/v1/datasets/products/search**
Search bulk dataset products by query parameters.

| Parameter | In | Type | Description |
|-----------|----|------|-------------|
| `q` | query | string | Search query |
| `offset` | query | integer | Pagination offset |
| `limit` | query | integer | Results per page |

Response: `BdssResponseBag`

**GET /api/v1/datasets/products/{productIdentifier}**
Get a specific bulk data product by its identifier (shortName).

| Parameter | In | Type | Required |
|-----------|----|------|----------|
| `productIdentifier` | path | string | yes |

Response: `BdssResponseProductBag`

**GET /api/v1/datasets/products/files/{productIdentifier}/{fileName}**
Download a bulk data product file.

| Parameter | In | Type | Required |
|-----------|----|------|----------|
| `productIdentifier` | path | string | yes |
| `fileName` | path | string | yes |

Response: Binary file (redirects to signed S3 URL).

---

## 3. PETITION DECISION API

Base URL: `https://api.uspto.gov`

**POST /api/v1/petition/decisions/search**
Search petition decisions by JSON payload.

Request body (`PetitionDecisionSearchRequest`): Same structure as `PatentSearchRequest` (q, filters, rangeFilters, sort, fields, pagination, facets) but uses petition-specific filter/range/sort schemas.

Response: `PetitionDecisionResponseBag`

**GET /api/v1/petition/decisions/search**
Search by query parameters (same params as patent search GET).

**POST /api/v1/petition/decisions/search/download**
Download petition results as JSON or CSV.

Request body (`PetitionDecisionDownloadRequest`): Same as search + `format` field.

**GET /api/v1/petition/decisions/search/download**
Download via query parameters.

**GET /api/v1/petition/decisions/{petitionDecisionRecordIdentifier}**
Get a specific petition decision by record identifier.

| Parameter | In | Type | Required |
|-----------|----|------|----------|
| `petitionDecisionRecordIdentifier` | path | string | yes |

Response: `PetitionDecisionIdentifierResponseBag`

---

## 4. PTAB TRIALS API

Base URL: `https://api.uspto.gov`

All PTAB search endpoints support the same GET query parameters (q, filters, rangeFilters, sort, offset, limit, fields, facets) and the same POST JSON body structure as the patent search.

### 4.1 Proceedings

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/patent/trials/proceedings/search` | Search trials proceedings using JSON |
| GET | `/api/v1/patent/trials/proceedings/search` | Search trials proceedings using query params |
| POST | `/api/v1/patent/trials/proceedings/search/download` | Download proceedings as JSON/CSV |
| GET | `/api/v1/patent/trials/proceedings/search/download` | Download proceedings via query params |
| GET | `/api/v1/patent/trials/proceedings/{trialNumber}` | Single proceeding by trial number |

Response: `ProceedingDataResponse` containing `patentTrialProceedingDataBag` array.

Each proceeding record includes: `trialNumber`, `lastModifiedDateTime`, `trialMetaData`, `patentOwnerData`, `regularPetitionerData`, `respondentData`, `derivationPetitionerData`.

### 4.2 Decisions

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/patent/trials/decisions/search` | Search trial decisions using JSON |
| GET | `/api/v1/patent/trials/decisions/search` | Search trial decisions using query params |
| POST | `/api/v1/patent/trials/decisions/search/download` | Download decisions as JSON/CSV |
| GET | `/api/v1/patent/trials/decisions/search/download` | Download decisions via query params |
| GET | `/api/v1/patent/trials/decisions/{documentIdentifier}` | Single decision by document ID |
| GET | `/api/v1/patent/trials/{trialNumber}/decisions` | All decisions for a trial |

Response: `DecisionDataResponse` containing `patentTrialDecisionDataBag` array.

### 4.3 Documents

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/patent/trials/documents/search` | Search trial documents using JSON |
| GET | `/api/v1/patent/trials/documents/search` | Search trial documents using query params |
| POST | `/api/v1/patent/trials/documents/search/download` | Download documents as JSON/CSV |
| GET | `/api/v1/patent/trials/documents/search/download` | Download documents via query params |
| GET | `/api/v1/patent/trials/documents/{documentIdentifier}` | Single document by document ID |
| GET | `/api/v1/patent/trials/{trialNumber}/documents` | All documents for a trial |

Response: `DocumentDataResponse` containing `patentTrialDocumentDataBag` array.

### 4.4 Appeals

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/patent/appeals/decisions/search` | Search appeal decisions using JSON |
| GET | `/api/v1/patent/appeals/decisions/search` | Search appeal decisions using query params |
| POST | `/api/v1/patent/appeals/decisions/search/download` | Download appeal decisions as JSON/CSV |
| GET | `/api/v1/patent/appeals/decisions/search/download` | Download appeal decisions via query params |
| GET | `/api/v1/patent/appeals/decisions/{documentIdentifier}` | Appeal decision by document ID |
| GET | `/api/v1/patent/appeals/{appealNumber}/decisions` | Appeal decisions by appeal number |

Response: `AppealDecisionDataResponse` containing `PatentAppealDataBag` array.

### 4.5 Interferences

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/patent/interferences/decisions/search` | Search interference decisions using JSON |
| GET | `/api/v1/patent/interferences/decisions/search` | Search interference decisions using query params |
| POST | `/api/v1/patent/interferences/decisions/search/download` | Download interference decisions as JSON/CSV |
| GET | `/api/v1/patent/interferences/decisions/search/download` | Download interference decisions via query params |
| GET | `/api/v1/patent/interferences/{interferenceNumber}/decisions` | Decisions by interference number |
| GET | `/api/v1/patent/interferences/decisions/{documentIdentifier}` | Decision by document ID |

Response: `InterferenceDecisionDataResponse`.

---

## 5. OFFICE ACTION DSAPI ENDPOINTS

Base URL: `https://api.uspto.gov`
Auth: `X-API-KEY` header
Query syntax: **Lucene/Solr** (not the same as ODP opensearch syntax)

These are the legacy Data Set API (DSAPI) endpoints migrated to ODP. They use `application/x-www-form-urlencoded` POST bodies (not JSON).

### 5.1 Office Action Text Retrieval

**GET /api/v1/patent/oa/oa_actions/v1/fields**
List all searchable field names in the oa_actions dataset.

**POST /api/v1/patent/oa/oa_actions/v1/records**
Search office action text records.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `criteria` | formData | string | yes | `*:*` | Lucene query syntax (`propertyName:value`) |
| `start` | formData | integer | no | 0 | Starting record number |
| `rows` | formData | integer | no | 100 | Number of rows to return |

### 5.2 Office Action Rejections

**GET /api/v1/patent/oa/oa_rejections/v2/fields**
List searchable fields.

**POST /api/v1/patent/oa/oa_rejections/v2/records**
Search rejection records. Same form parameters as above.

### 5.3 Office Action Citations

**GET /api/v1/patent/oa/oa_citations/v2/fields**
List searchable fields.

**POST /api/v1/patent/oa/oa_citations/v2/records**
Search citation records. Same form parameters as above.

### 5.4 Enriched Citations (AI-extracted)

**GET /api/v1/patent/oa/enriched_cited_reference_metadata/v3/fields**
List searchable fields.

**POST /api/v1/patent/oa/enriched_cited_reference_metadata/v3/records**
Search enriched citation records. Same form parameters as above.

### DSAPI Response Format

```json
{
  "response": {
    "numFound": 12345,
    "start": 0,
    "docs": [
      { "field1": "value1", "field2": "value2" }
    ]
  }
}
```

Note: The `docs` array contains `map[string]any` -- field names vary by dataset. Use the `/fields` endpoint to discover available fields.

---

## 6. TSDR (Trademark Status & Document Retrieval) API

Base URL: `https://tsdrapi.uspto.gov`
Auth: `USPTO-API-KEY` header (different from ODP!)
Spec: `https://data.uspto.gov/swagger/tsdr-swagger.yaml` (JSON format, 327KB)

### 6.1 Case Status

| Method | Path | Description |
|--------|------|-------------|
| GET | `/ts/cd/casestatus/{caseid}/info` | Trademark data as ST96 XML |
| GET | `/ts/cd/casestatus/{caseid}/v1/info` | Trademark data as ST96 XML (legacy v1) |
| GET | `/ts/cd/casestatus/{caseid}/content.pdf` | Case status as PDF |
| GET | `/ts/cd/casestatus/{caseid}/content.zip` | Case status as ZIP |
| GET | `/ts/cd/casestatus/{caseid}/content.html` | Case status as HTML |
| GET | `/ts/cd/casestatus/{caseid}/download.pdf` | Download case status PDF |
| GET | `/ts/cd/casestatus/{caseid}/download.zip` | Download case status ZIP |

`caseid` format: `sn88123456` (serial), `rn1234567` (registration), `ref12345678` (reference), `ir12345678` (Madrid/international).

### 6.2 Case Documents

| Method | Path | Description |
|--------|------|-------------|
| GET | `/ts/cd/casedocs/{caseid}/info` | All documents metadata (XML) |
| GET | `/ts/cd/casedocs/{caseid}/bundle` | Document bundle info (XML) |
| GET | `/ts/cd/casedocs/{caseid}/content.pdf` | All documents as PDF |
| GET | `/ts/cd/casedocs/{caseid}/content.zip` | All documents as ZIP |
| GET | `/ts/cd/casedocs/{caseid}/download.pdf` | Download all documents PDF |
| GET | `/ts/cd/casedocs/{caseid}/download.zip` | Download all documents ZIP |

### 6.3 Single Document

| Method | Path | Description |
|--------|------|-------------|
| GET | `/ts/cd/casedoc/{caseid}/{docid}/info` | Document metadata (XML) |
| GET | `/ts/cd/casedoc/{caseid}/{docid}/content.pdf` | Document as PDF |
| GET | `/ts/cd/casedoc/{caseid}/{docid}/content.zip` | Document as ZIP |
| GET | `/ts/cd/casedoc/{caseid}/{docid}/download.pdf` | Download document PDF |
| GET | `/ts/cd/casedoc/{caseid}/{docid}/download.zip` | Download document ZIP |
| GET | `/ts/cd/casedoc/{caseid}/{docid}/{pageid}/media` | Single page in native format |

### 6.4 Multi-Case & Updates

| Method | Path | Description |
|--------|------|-------------|
| GET | `/ts/cd/caseMultiStatus/{type}` | Batch lookup for multiple cases (JSON) |
| GET | `/last-update/info.xml` | Last update timestamp (XML) |
| GET | `/last-update/info.json` | Last update timestamp (JSON) |

Multi-status parameters:
- `type` (path): `sn`, `rn`, `ref`, or `ir`
- `ids` (query, required): Comma-separated identifiers
- `from` / `to` (query, optional): Number range

### 6.5 Document Bundles (query-based)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/ts/cd/casedocs/bundle.xml` | Bundle metadata (XML) |
| GET | `/ts/cd/casedocs/bundle.pdf` | Bundle as PDF |
| GET | `/ts/cd/casedocs/bundle.zip` | Bundle as ZIP |

---

## Complete Endpoint Count Summary

| API Family | Endpoints | Methods |
|-----------|-----------|---------|
| Patent File Wrapper (search + sub-resources) | 14 paths | 16 method+path combos (POST+GET on search) |
| Bulk Datasets | 3 paths | 3 GET |
| Petition Decisions | 3 paths | 6 (POST+GET on search + download) |
| PTAB Trials (proceedings + decisions + documents) | 12 paths | 22 (POST+GET on search + download, GET on lookups) |
| PTAB Appeals | 4 paths | 8 |
| PTAB Interferences | 4 paths | 8 |
| Office Action DSAPI (4 datasets x 2 endpoints) | 8 paths | 8 (GET fields + POST records) |
| TSDR | 25 paths | 25 GET |
| **TOTAL** | **~73 paths** | **~96 method+path combinations** |

---

## Query Syntax Reference

### ODP Search (patent, PTAB, petition endpoints)

The `q` parameter supports opensearch/boolean syntax:
- `Utility` -- free text across all fields
- `Utility AND Design` -- boolean AND
- `Utility OR Design` -- boolean OR
- `applicationMetaData.applicationTypeLabelName:Utility` -- field:value
- `applicationMetaData.filingDate:[2020-01-01 TO 2023-12-31]` -- field range
- Wildcards: `auto*` matches "automobile", "automatic", etc.
- Exact phrase: `"autonomous vehicle"`

### DSAPI / Office Action Search (Lucene syntax)

The `criteria` parameter uses Lucene/Solr syntax:
- `*:*` -- match all
- `propertyName:value` -- field:value
- `propertyName:[num1 TO num2]` -- range query
- Standard Lucene boolean operators apply

---

## Curl Examples

```bash
# Patent search (GET)
curl -X GET "https://api.uspto.gov/api/v1/patent/applications/search?q=autonomous+vehicle&limit=5" \
  -H "X-API-KEY: YOUR_KEY"

# Patent search (POST)
curl -X POST "https://api.uspto.gov/api/v1/patent/applications/search" \
  -H "X-API-KEY: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q":"applicationMetaData.applicationTypeLabelName:Utility","pagination":{"offset":0,"limit":5}}'

# Single application lookup
curl -X GET "https://api.uspto.gov/api/v1/patent/applications/14412875" \
  -H "X-API-KEY: YOUR_KEY"

# Application documents
curl -X GET "https://api.uspto.gov/api/v1/patent/applications/16123456/documents" \
  -H "X-API-KEY: YOUR_KEY"

# PTAB trial search
curl -X POST "https://api.uspto.gov/api/v1/patent/trials/proceedings/search" \
  -H "X-API-KEY: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q":"IPR2024*","pagination":{"offset":0,"limit":10}}'

# Office action rejections (DSAPI - form-encoded)
curl -X POST "https://api.uspto.gov/api/v1/patent/oa/oa_rejections/v2/records" \
  -H "X-API-KEY: YOUR_KEY" \
  -d "criteria=*:*&start=0&rows=10"

# TSDR trademark status
curl -X GET "https://tsdrapi.uspto.gov/ts/cd/casestatus/sn88123456/info" \
  -H "USPTO-API-KEY: YOUR_KEY"

# Download search results as CSV
curl -X POST "https://api.uspto.gov/api/v1/patent/applications/search/download" \
  -H "X-API-KEY: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q":"autonomous vehicle","format":"csv","pagination":{"offset":0,"limit":100}}'
```
