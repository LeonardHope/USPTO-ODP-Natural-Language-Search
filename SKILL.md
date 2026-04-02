---
name: uspto-odp-search
description: >
  Search all USPTO patent and trademark databases using plain English. This skill
  provides a unified interface to the USPTO Open Data Portal (ODP) APIs covering
  patent application search, file wrapper prosecution history, PTAB trials and
  appeals, office action rejections, patent assignments, petition decisions,
  trademark status (TSDR), and bulk data downloads.

  Use this skill whenever the user wants to search for patents, look up patent
  applications, check prosecution history, find PTAB proceedings or appeal
  decisions, trace patent ownership, analyze office action rejections, search by
  inventor or company name, look up CPC classifications, find an examiner's cases,
  check trademark status, retrieve trademark documents, search petition decisions,
  download bulk USPTO data, or do anything involving USPTO patent or trademark data.

  Trigger on: patent numbers, application numbers, assignees, inventors, prior art,
  IPR, PGR, CBM, PTAB, 101/102/103/112 rejections, Alice, obviousness, patent term
  adjustment, continuity, divisional, continuation, file wrapper, office action,
  IDS, CPC codes, art unit, examiner name, petition, trademark, TSDR, serial number,
  registration number, mark, service mark, trademark status, bulk data, assignment,
  chain of title, ownership, or any patent/trademark-related search task.

  The user does NOT need to know API syntax, endpoint names, or query formats. They
  can ask questions in plain English like "find all patents assigned to Atari" or
  "has patent 10,000,000 been challenged at PTAB?" or "what is the status of
  trademark serial number 88123456?" and this skill handles the translation to
  the correct API calls.
---

# USPTO Open Data Portal Search Skill

## Overview

This skill gives you access to every major USPTO API through natural language. The user asks a question in plain English, and your job is to figure out which API to query, build the right request, run it, and present the results clearly.

All APIs are accessed through the USPTO Open Data Portal (ODP) platform using a single API key. You have 11 Python modules in the `scripts/` directory:

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `patent_search.py` | Patent application search (keyword, assignee, inventor, CPC, patent number, examiner, status) | `search_by_assignee()`, `search_by_inventor()`, `search_by_keyword()`, `search_by_patent_number()`, `search_by_application_number()`, `search_by_cpc()`, `search_by_examiner()`, `search_by_status()`, `search_patents()`, `download_search_results()` |
| `file_wrapper.py` | File wrapper sub-resources for specific applications | `get_application()`, `get_application_by_patent_number()`, `get_application_documents()`, `get_continuity()`, `get_patent_term_adjustment()`, `get_assignment()`, `get_attorney()`, `get_transactions()`, `get_foreign_priority()`, `get_associated_documents()`, `get_meta_data()`, `get_status_codes()` |
| `ptab_search.py` | PTAB trials, appeals, interferences | `search_proceedings()`, `get_proceeding()`, `search_trial_decisions()`, `search_trial_documents()`, `search_appeal_decisions()`, `search_interference_decisions()` |
| `petition_search.py` | Final petition decisions | `search_petition_decisions()`, `get_petition_decision()`, `download_petition_decisions()` |
| `office_actions_search.py` | Office action rejections, text, citations, enriched citations (DSAPI/Lucene) | `search_rejections()`, `search_office_action_text()`, `search_office_action_citations()`, `search_enriched_citations()` |
| `assignment_search.py` | Patent ownership/assignment chain | `get_assignment_chain()`, `search_patent_assignments()`, `get_assignments_by_company()`, `get_assignments_for_application()` |
| `tsdr_search.py` | Trademark status and document retrieval (TSDR API) | `get_trademark_status()`, `get_trademark_documents()`, `get_trademark_document()`, `download_trademark_document()`, `get_multi_status()`, `get_last_update()` |
| `bulk_data_search.py` | Bulk dataset product search and download | `search_bulk_datasets()`, `get_bulk_dataset()`, `download_bulk_file()` |
| `download_documents.py` | File wrapper document listing and PDF download | `list_documents()`, `download_documents()`, `fetch_all_documents()` |
| `format_results.py` | Output formatting | `format_patent_list()`, `format_patent_detail()`, `format_ptab_results()`, `format_assignment_results()`, `format_rejection_results()`, `format_petition_results()` |
| `uspto_client.py` | Shared client with auth, rate limiting, retry logic | `get_client()`, `USPTOClient` |

---

## Setup

Only one API key is needed for everything, including trademarks.

```bash
cd scripts/
python uspto_client.py
```

If the output contains `[SETUP_REQUIRED]`, guide the user through setup:

**Quickest option -- interactive setup script:**
```bash
python get_started.py
```
This creates a Python virtual environment (`.venv`), installs dependencies, prompts for the API key, masks the value, and saves it to a `.env` file in the project root.

**Alternative -- set environment variable directly:**
```bash
export USPTO_ODP_API_KEY="their_key"
```

**Where to get the key:**
- Register at https://data.uspto.gov/myodp (free, requires ID.me verification)
- This single key covers all ODP APIs: patent search, file wrapper, PTAB, assignments, office actions, petition decisions, bulk data, and TSDR trademarks

---

## How to Handle User Requests

Follow these steps for every request.

### Step 1: Parse the Natural Language

Break down what the user is asking for. Identify:
- **Entity**: What are they looking for? (patents, applications, proceedings, assignments, rejections, trademarks, bulk data)
- **Filters**: By whom? (inventor, assignee, examiner) When? (date range) What about? (keywords, CPC codes)
- **Relationships**: Continuity? Ownership chain? PTAB challenges? Rejections?
- **Scope**: Single patent/trademark lookup vs. broad search vs. analytics

### Step 2: Choose the Right API

Use this decision matrix. Check conditions top to bottom -- use the first match.

#### Patent Application Search (`patent_search.py`)

| User wants to... | Key signals in request | Script function |
|---|---|---|
| Search by company/assignee | company name + "patents", "assigned to", "portfolio" | `search_by_assignee(name, date_from=, date_to=, limit=)` |
| Search by inventor name | person name + "inventor", "invented by", "patents by" | `search_by_inventor(last_name, first_name=, date_from=, date_to=, limit=)` |
| Search by keyword/technology | technology terms, "patents about", "related to" | `search_by_keyword(keywords, date_from=, date_to=, limit=)` |
| Look up a specific granted patent | patent number only, basic info | `search_by_patent_number(patent_number)` |
| Look up a specific application | application number (16/xxx, etc.) | `search_by_application_number(application_number)` |
| Search by CPC/classification | CPC code, technology class, "class H04L" | `search_by_cpc(cpc_code, date_from=, date_to=, limit=)` |
| Search by examiner | examiner name, "examiner Smith" | `search_by_examiner(examiner_name, limit=)` |
| Search by application status | "pending", "patented", "abandoned" | `search_by_status(status, limit=)` |
| Advanced/custom search | complex filters, range queries, specific fields | `search_patents(q=, filters=, range_filters=, sort=, fields=, offset=, limit=)` |
| Download search results in bulk | "export", "download results", "CSV" | `download_search_results(q=, filters=, range_filters=, format=)` |

#### File Wrapper Sub-Resources (`file_wrapper.py`)

| User wants to... | Key signals in request | Script function |
|---|---|---|
| Get full data for a specific application | application number + "everything", "details", "full record" | `get_application(application_number)` |
| Resolve patent number to application data | patent number + need app-level data | `get_application_by_patent_number(patent_number)` |
| Get application metadata (status, dates, parties) | "status", "who filed", "filing date", "classification" | `get_meta_data(application_number)` |
| Get prosecution history / file wrapper docs | "office actions", "prosecution", "file wrapper", "IDS" | `get_application_documents(application_number, offset=, limit=)` |
| See parent/child application relationships | "continuation", "divisional", "family", "priority", "parent", "child" | `get_continuity(application_number)` |
| Check patent term adjustment | "PTA", "term adjustment", "patent term" | `get_patent_term_adjustment(application_number)` |
| Get assignment records for an application | "assignment", "owner" + application number | `get_assignment(application_number)` |
| Get attorney/agent of record | "attorney", "agent", "law firm", "who represents" | `get_attorney(application_number)` |
| Get transaction/event history | "transactions", "events", "history", "timeline" | `get_transactions(application_number)` |
| Get foreign priority claims | "foreign priority", "Paris Convention", "PCT" | `get_foreign_priority(application_number)` |
| Get associated document metadata | "publication", "grant XML", "associated documents" | `get_associated_documents(application_number)` |
| Look up status codes | "status code", "what does status X mean" | `get_status_codes(query=)` |

#### PTAB Trials, Appeals, and Interferences (`ptab_search.py`)

| User wants to... | Key signals in request | Script function |
|---|---|---|
| Find PTAB trial proceedings | "IPR", "PGR", "CBM", "PTAB", "challenged", "invalidated", "trial" | `search_proceedings(query=, patent_number=, party_name=, trial_number=, proceeding_type=)` |
| Get details for a specific trial | trial number (e.g. "IPR2020-00001") | `get_proceeding(trial_number)` |
| Read PTAB trial decisions | "PTAB decision", "final written decision", "institution decision" | `search_trial_decisions(query=, patent_number=, trial_number=)` |
| Find PTAB trial documents/filings | "PTAB filings", "exhibits", "petitioner brief" | `search_trial_documents(query=, trial_number=)` |
| Search appeal decisions | "appeal", "BPAI", "appeal decision", "ex parte appeal" | `search_appeal_decisions(query=, appeal_number=)` |
| Search interference decisions | "interference", "priority of invention" | `search_interference_decisions(query=, interference_number=)` |

#### Office Actions (`office_actions_search.py`)

| User wants to... | Key signals in request | Script function |
|---|---|---|
| Check 101/102/103/112 rejections | "rejection", "101", "102", "103", "112", "Alice", "obviousness", "anticipation" | `search_rejections(application_number=, patent_number=, rejection_type=, art_unit=, criteria=)` |
| Read office action text | "office action text", "examiner's reasoning", "what did the examiner say" | `search_office_action_text(application_number=, patent_number=, criteria=)` |
| See what prior art was cited in OAs | "cited references", "prior art cited", "citations in office action" | `search_office_action_citations(application_number=, patent_number=, criteria=)` |
| Get enriched/parsed citations | "enriched citations", "which claims cited against", "citation context" | `search_enriched_citations(application_number=, patent_number=, cited_reference=, criteria=)` |

#### Patent Assignments (`assignment_search.py`)

| User wants to... | Key signals in request | Script function |
|---|---|---|
| Find who owns a patent | "owner", "assigned to", "chain of title", "who owns" | `get_assignment_chain(patent_number)` |
| Get assignments for an application | application number + "assignment", "ownership" | `get_assignments_for_application(application_number)` |
| Track patent acquisitions/sales | "bought", "sold", "transferred", "acquired" | `search_patent_assignments(patent_number=, application_number=)` |
| Find assignments involving a company | company name + "assignments", "acquisitions", "transfers" | `get_assignments_by_company(company_name, as_assignee=, as_assignor=)` |

#### Petition Decisions (`petition_search.py`)

| User wants to... | Key signals in request | Script function |
|---|---|---|
| Search petition decisions | "petition", "revival", "extension of time", "petition decision" | `search_petition_decisions(query=, application_number=, patent_number=)` |
| Get a specific petition decision | petition decision record ID | `get_petition_decision(record_id)` |
| Download petition decision results | "download petitions", "export petition data" | `download_petition_decisions(query=, format=)` |

#### Trademark Status & Documents (`tsdr_search.py`)

| User wants to... | Key signals in request | Script function |
|---|---|---|
| Check trademark status | "trademark status", "mark status", serial/registration number, "TSDR" | `get_trademark_status(serial_number=, registration_number=, case_id=)` |
| List trademark case documents | "trademark documents", "trademark file", "office actions for mark" | `get_trademark_documents(case_id)` |
| Get single trademark document info | specific document ID from a trademark case | `get_trademark_document(case_id, doc_id)` |
| Download trademark document PDF | "download trademark document", "get trademark PDF" | `download_trademark_document(case_id, doc_id, dest_path)` |
| Batch trademark status lookup | multiple serial/registration numbers at once | `get_multi_status(case_type, ids)` |
| Check TSDR data freshness | "when was TSDR updated", "data freshness" | `get_last_update()` |

#### Bulk Data Products (`bulk_data_search.py`)

| User wants to... | Key signals in request | Script function |
|---|---|---|
| Find available bulk datasets | "bulk data", "bulk download", "dataset", "data dump" | `search_bulk_datasets(query=, offset=, limit=)` |
| Get details on a specific dataset | product ID, dataset name | `get_bulk_dataset(product_id)` |
| Download a bulk data file | "download dataset", specific product + file name | `download_bulk_file(product_id, file_name, dest_path)` |

#### File Wrapper Document Download (`download_documents.py`)

| User wants to... | Key signals in request | Script function |
|---|---|---|
| List documents in file wrapper | "list documents", "what's in the file wrapper", "show prosecution docs" | `list_documents(app_number, key_only=False, codes=None)` |
| Download prosecution documents | "download", "save", "get the PDFs", "pull the file history" | `download_documents(app_number, output_dir=, key_only=True, codes=None, download_all=False)` |
| Download specific document types | "download office actions", "get the IDS filings", specific doc codes | `download_documents(app_number, codes=["CTNF","CTFR"])` |

### Step 3: Handle Fuzzy / Ambiguous Queries

Users will not give you exact names or numbers. Handle this gracefully:

**Company names**: The ODP search uses free-text matching, so pass the company name directly. If results are sparse, try common variations (with/without "Inc.", "LLC", "Corp.", etc.) as separate searches:
```python
from patent_search import search_by_assignee
result = search_by_assignee("Atari")
# If sparse, also try: search_by_assignee("Atari, Inc.")
```

**Inventor names**: Uses quoted full name for exact matching when both first and last names are provided. If only a last name is given, results may be broad -- ask the user for a first name or other filter to narrow down:
```python
from patent_search import search_by_inventor
result = search_by_inventor("Tesla", first_name="Nikola")
```

**Patent numbers**: Strip formatting automatically. Accept any of these: `10,000,000`, `US10000000`, `10000000`, `US 10,000,000`. The `clean_patent_number()` utility in `uspto_client.py` handles this.

**Application numbers**: Accept `16/123,456` or `16123456` -- the `clean_app_number()` utility handles cleanup.

**Trademark identifiers**: TSDR accepts serial numbers (prefix `sn`), registration numbers (prefix `rn`), reference numbers (prefix `ref`), and international registration numbers (prefix `ir`). The `_format_case_id()` helper in `tsdr_search.py` handles formatting:
```python
from tsdr_search import get_trademark_status
# Any of these work:
result = get_trademark_status(serial_number="88123456")
result = get_trademark_status(registration_number="1234567")
result = get_trademark_status(case_id="sn88123456")
```

**Ambiguous entities**: If the user says "Apple patents", that clearly means Apple Inc. But if they say "Tesla", ask whether they mean Tesla Inc. or Nikola Tesla the inventor -- unless context makes it obvious.

**Patent vs. trademark**: If the user says "check the status of 88123456", the 8-digit number starting with 88 is likely a trademark serial number. Standard patent application numbers are formatted as XX/XXX,XXX. Use context clues to determine which API to call.

### Step 4: Run the Query

Import and call the appropriate script function. All scripts are in the `scripts/` directory relative to this skill. For example:

```python
import os, sys
skill_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(skill_dir, "scripts"))
from patent_search import search_by_assignee
result = search_by_assignee("Atari")
```

Or run via command line from the skill's root directory:
```bash
cd scripts/
python patent_search.py assignee "Atari"
python patent_search.py patent 10000000
python patent_search.py inventor "Smith" --first "John"
python patent_search.py keyword "autonomous vehicle lidar"
python patent_search.py cpc H04L
python patent_search.py examiner "Smith"
python file_wrapper.py get 16123456
python file_wrapper.py documents 16123456
python file_wrapper.py continuity 16123456
python file_wrapper.py pta 14643719
python ptab_search.py proceedings --patent-number 10000000
python ptab_search.py appeals --query "software"
python office_actions_search.py rejections --art-unit 3689 --type 103
python assignment_search.py chain 10000000
python petition_search.py search --app-number 16123456
python tsdr_search.py status --serial 88123456
python bulk_data_search.py search --query "patent grants"
python download_documents.py list 16123456 --key-only
python download_documents.py download 16123456 --codes CTNF
```

### Step 5: Present Results Clearly

Never dump raw JSON at the user. Use the formatters in `format_results.py`:

```python
from format_results import format_patent_list, format_patent_detail
print(format_patent_list(result))
print(format_patent_detail(result))
```

Available formatters:
- `format_patent_list(response)` -- numbered list of patent applications
- `format_patent_detail(patent)` -- detailed view of a single patent
- `format_ptab_results(response)` -- PTAB proceedings and decisions
- `format_assignment_results(response)` -- assignment/ownership records
- `format_rejection_results(response)` -- office action rejection data
- `format_petition_results(response)` -- petition decision records

Or format results yourself following these principles:
- Lead with the answer to the user's question, not the data
- Show the most important fields first (patent number, title, date, assignee)
- For lists, show a numbered summary with key details
- For single patents, show a clean detail view
- Note the total count and whether there are more results available
- For TSDR responses that return XML, parse and summarize the key status fields

### Step 6: When Results Are Sparse

If you get few or no results:
1. Try a broader search (shorter name substring, fewer filters)
2. Check for typos or alternative spellings
3. For company names, try with/without corporate suffixes
4. For patent numbers, verify the format was cleaned correctly
5. Tell the user what you tried and suggest refinements

---

## Multi-Step Query Patterns

Some questions require chaining calls across multiple modules. Here are common patterns:

### Full Patent Profile
User: "Tell me everything about patent 10,000,000"
1. `patent_search.search_by_patent_number("10000000")` -- basic info, title, status
2. `file_wrapper.get_application_by_patent_number("10000000")` -- get app number
3. `file_wrapper.get_application_documents(app_number)` -- prosecution history
4. `file_wrapper.get_continuity(app_number)` -- patent family
5. `ptab_search.search_proceedings(patent_number="10000000")` -- PTAB challenges
6. `assignment_search.get_assignment_chain("10000000")` -- ownership chain
7. `office_actions_search.search_rejections(patent_number="10000000")` -- rejection history

### Competitor Portfolio Analysis
User: "How does Samsung's patent portfolio compare to LG's in display technology?"
1. `patent_search.search_by_assignee("Samsung")` with CPC filter for display tech
2. `patent_search.search_by_assignee("LG")` with same CPC filter
3. Compare counts, filing dates, technology areas
4. Optionally: `patent_search.search_by_cpc("G09G")` for display-related CPC codes

### Download Prosecution File History
User: "Download the file history for application 16/123,456" or "Save the office actions for patent 11,887,351"
1. If user gave a patent number, resolve to application number: `file_wrapper.get_application_by_patent_number("11887351")`
2. List available documents: `download_documents.list_documents(app_number, key_only=True)`
3. Show the user what will be downloaded and confirm
4. Download: `download_documents.download_documents(app_number)`
   - Default: key prosecution docs only (office actions, amendments, IDS, etc.)
   - `download_all=True` or user says "everything": downloads all documents
   - `codes=["CTNF","CTFR"]` or user says "just the office actions": specific types
5. Report what was downloaded and where the files are saved (`downloads/{appNumber}/`)

**Note:** PDF downloads are rate-limited to 4/minute. The script handles this automatically with progress output. Re-running a download skips files that already exist.

### Pre-Litigation Check
User: "We're thinking of asserting patent 9,876,543. What should I know?"
1. `patent_search.search_by_patent_number("9876543")` -- basic info, is it granted?
2. `assignment_search.get_assignment_chain("9876543")` -- clean chain of title?
3. `ptab_search.search_proceedings(patent_number="9876543")` -- any prior challenges?
4. `office_actions_search.search_rejections(patent_number="9876543")` -- how many rejections during prosecution?
5. `file_wrapper.get_continuity(app_number)` -- any related family members?
6. `file_wrapper.get_patent_term_adjustment(app_number)` -- when does it expire?

### Trademark Status Check
User: "What is the status of trademark serial number 88123456?"
1. `tsdr_search.get_trademark_status(serial_number="88123456")` -- current status
2. `tsdr_search.get_trademark_documents(case_id="sn88123456")` -- case documents

### Batch Trademark Lookup
User: "Check the status of these registration numbers: 1234567, 2345678, 3456789"
1. `tsdr_search.get_multi_status(case_type="rn", ids=["1234567", "2345678", "3456789"])`

### Rejection Analysis
User: "What 101 rejections has art unit 3689 issued recently?"
1. `office_actions_search.search_rejections(art_unit="3689", rejection_type="101")`
2. Present summary of rejection patterns, Alice/Mayo indicators

### Bulk Data Discovery
User: "Where can I download all patent grant XML data?"
1. `bulk_data_search.search_bulk_datasets(query="patent grant XML")`
2. Show available products, formats, and descriptions
3. If user wants to download: `bulk_data_search.download_bulk_file(product_id, file_name, dest_path)`

---

## Error Handling

If a script raises an `APIError`:
- **Missing API key**: Tell the user to set `USPTO_ODP_API_KEY`. Direct them to https://data.uspto.gov/myodp to register (free, requires ID.me verification).
- **Rate limit (429)**: The scripts retry automatically with exponential backoff; if persistent, suggest waiting a minute.
- **Not found (404)**: Check the number format; suggest trying without formatting. For TSDR, verify the case ID prefix (sn/rn/ref/ir) is correct.
- **Forbidden (403)**: Some sub-resource endpoints (like patent term adjustment) may return 403. The scripts handle this gracefully and suggest checking Patent Center UI instead.
- **Server error (5xx)**: The scripts retry automatically; if persistent, the API may be down.

**Office action API note**: The DSAPI endpoints for rejections and citations use Lucene query syntax, which is different from the ODP search endpoints. If a Lucene query fails, check field names using `get_rejection_fields()` or `get_office_action_fields()`.

**TSDR XML responses**: Many TSDR endpoints return ST96 XML rather than JSON. The client wraps these in `{"raw_xml": text}`. Parse and summarize the key fields for the user rather than displaying raw XML.

---

## Security Reminders

- API keys are loaded from `.env` or environment variables -- never hardcode them in source
- Never print or log API keys in output
- Never include keys in error messages shown to the user
- The `.env` file is git-ignored and must never be committed
- If sharing the project, only share `.env.example` (which contains no keys)
- Only one key is needed: `USPTO_ODP_API_KEY` -- it covers all APIs including TSDR
