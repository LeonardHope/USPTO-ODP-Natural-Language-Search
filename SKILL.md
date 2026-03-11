---
name: uspto-patent-search
description: >
  Search all USPTO patent databases using plain English. This skill provides a unified
  interface to the PatentsView API, USPTO Open Data Portal (file wrappers, PTAB, bulk data),
  Legacy Office Action APIs (rejections, citations, full text), and Patent Assignment records.

  Use this skill whenever the user wants to search for patents, look up patent applications,
  check prosecution history, find PTAB proceedings, trace patent ownership, analyze office
  action rejections, search by inventor or company name, explore citation networks, or do
  anything involving USPTO patent data. Also trigger when the user mentions patent numbers,
  application numbers, assignees, prior art, IPR, PGR, 101/102/103 rejections, or any
  patent-related search task.

  The user does NOT need to know API syntax, endpoint names, or query formats. They can
  ask questions in plain English like "find all patents assigned to Atari or similar"
  or "has patent 10,000,000 been challenged at PTAB?" and this skill handles the translation
  to the correct API calls.
---

# USPTO Patent Search Skill

## Overview

This skill gives you access to every major USPTO API through natural language. The user
asks a question in plain English, and your job is to figure out which API to query, build
the right request, run it, and present the results clearly.

You have 6 API families available, each with Python scripts ready to use:

| API | Script | Best For |
|-----|--------|----------|
| PatentsView | `patentsview_search.py` | Inventor/assignee/keyword search, analytics, citations |
| ODP File Wrapper | `odp_search.py` | Application status, prosecution history, documents |
| ODP PTAB | `odp_search.py` | IPR/PGR/CBM trials, appeal decisions |
| ODP Document Download | `download_documents.py` | List & download prosecution PDFs (office actions, amendments, IDS) |
| Legacy Office Actions | `office_actions_search.py` | Rejections (101/102/103), examiner citations, OA text |
| Assignments | `assignment_search.py` | Ownership chain, transfers, security interests |

---

## Setup

Before running any queries, check that the user has their API keys configured:

```bash
cd scripts/
python uspto_client.py
```

If the output contains `[SETUP_REQUIRED]`, guide the user through setup:

**Quickest option — interactive setup script:**
```bash
python get_started.py
```
This creates a Python virtual environment (`.venv`), installs dependencies, prompts for each API key, masks the values, and saves them to a `.env` file in the project root.

**Alternative — set environment variables directly:**
```bash
export USPTO_ODP_API_KEY="their_key"
export PATENTSVIEW_API_KEY="their_key"  # optional
```

**Where to get the keys:**
- **ODP key (required)**: Register at https://data.uspto.gov/myodp (free, requires ID.me verification)
- **PatentsView key (optional)**: Try https://patentsview-support.atlassian.net/servicedesk/customer/portal/1/group/1/create/18 — the original key request page has been removed. PatentsView is migrating to ODP on March 20, 2026. Without this key, inventor/assignee/keyword/patent number searches fall back to ODP automatically. CPC search, attorney search, and citation network lookups are unavailable without it.

---

## How to Handle User Requests

This is the core of the skill. Follow these steps for every request:

### Step 1: Parse the Natural Language

Break down what the user is asking for. Identify:
- **Entity**: What are they looking for? (patents, applications, proceedings, assignments, rejections)
- **Filters**: By whom? (inventor, assignee, examiner) When? (date range) What about? (keywords, CPC codes)
- **Relationships**: Citations? Continuity? Ownership chain? PTAB challenges?
- **Scope**: Single patent lookup vs. broad search vs. analytics

### Step 2: Choose the Right API

Use this decision matrix. Check conditions top to bottom — use the first match:

| User wants to... | Key signals in request | Use this API | Script function |
|---|---|---|---|
| Check status of a specific application | application number (16/xxx, etc.) | ODP File Wrapper | `odp_search.get_application()` |
| Get prosecution history / file wrapper docs | "office actions", "prosecution", "file wrapper", "IDS" | ODP File Wrapper | `odp_search.get_application_documents()` |
| See parent/child application relationships | "continuation", "divisional", "family", "priority" | ODP File Wrapper | `odp_search.get_continuity()` |
| Check patent term adjustment | "PTA", "term adjustment", "patent term" | ODP File Wrapper | `odp_search.get_patent_term_adjustment()` |
| Find PTAB proceedings | "IPR", "PGR", "CBM", "PTAB", "challenged", "invalidated" | ODP PTAB | `odp_search.search_ptab_proceedings()` |
| Read PTAB decisions | "PTAB decision", "final written decision", "institution" | ODP PTAB | `odp_search.search_ptab_decisions()` |
| Check 101/102/103/112 rejections | "rejection", "101", "102", "103", "112", "Alice", "obviousness" | Legacy OA | `office_actions_search.search_rejections()` |
| Read office action text | "office action text", "examiner's reasoning" | Legacy OA | `office_actions_search.search_office_action_text()` |
| See what prior art was cited | "cited references", "prior art cited", "citations in OA" | Legacy OA | `office_actions_search.search_enriched_citations()` |
| Find who owns a patent | "owner", "assigned to", "chain of title", "assignment" | Assignments | `assignment_search.get_assignment_chain()` |
| Track patent acquisitions/sales | "bought", "sold", "transferred", "acquired" | Assignments | `assignment_search.search_patent_assignments()` |
| Search by inventor name | person name + "inventor", "invented by", "patents by" | PatentsView (ODP fallback) | `patentsview_search.search_by_inventor()` |
| Search by company/assignee | company name + "patents", "assigned to", "portfolio" | PatentsView (ODP fallback) | `patentsview_search.search_by_assignee()` |
| Search by keyword/technology | technology terms, "patents about", "related to" | PatentsView (ODP fallback) | `patentsview_search.search_by_keyword()` |
| Search by CPC/classification | CPC code, technology class, "class H04L" | PatentsView only | `patentsview_search.search_by_cpc()` |
| Look up a specific granted patent | patent number only, basic info | PatentsView (ODP fallback) | `patentsview_search.search_by_patent_number()` |
| Find patent citations | "cites", "cited by", "citation network", "prior art" | PatentsView only | `patentsview_search.get_patent_citations()` |
| Find who cites a patent | "cited by", "how influential", "impact" | PatentsView only | `patentsview_search.get_cited_by()` |
| Search by attorney/firm | law firm name, attorney name | PatentsView only | `patentsview_search.search_by_attorney()` |
| Analytics / comparisons / rankings | "most patents", "top", "compare", "trend", "how many" | PatentsView | Combine multiple calls |
| List documents in file wrapper | "list documents", "what's in the file wrapper", "show prosecution docs" | ODP Document Download | `download_documents.list_documents()` |
| Download prosecution documents | "download", "save", "get the PDFs", "pull the file history" | ODP Document Download | `download_documents.download_documents()` |
| Download specific document types | "download office actions", "get the IDS filings", specific doc codes | ODP Document Download | `download_documents.download_documents(codes=[...])` |
| Search pending applications broadly | "pending", "published applications" | ODP File Wrapper | `odp_search.search_applications()` |

**When the user's request spans multiple APIs**, run them sequentially. For example:
- "Tell me everything about patent 10,000,000" → PatentsView (basic info + citations) + ODP (prosecution history) + PTAB (any challenges) + Assignments (ownership)
- "Find Tesla's patents and check if any have been challenged" → PatentsView (assignee search) + PTAB (check each result)

### Step 3: Handle Fuzzy / Ambiguous Queries

Users will not give you exact names or numbers. Handle this gracefully:

**Company names**: Fuzzy matching tries common corporate name variations (Inc., LLC, Corp., etc.) as an OR list since `_contains` is currently broken:
```python
# Fuzzy mode (default) — tries "Atari", "Atari, Inc.", "Atari Inc.", etc.
search_by_assignee("Atari", fuzzy=True)
# If sparse results, try the assignee lookup endpoint for disambiguation
get_assignee_details("Atari")
```

**Inventor names**: Uses exact match on last name (and optionally first name). If only a last name is given, search by last name alone. If results are too broad, ask the user for a first name or other filter.

**Patent numbers**: Strip formatting automatically. Accept any of these: `10,000,000`, `US10000000`, `10000000`, `US 10,000,000`.

**Application numbers**: Accept `16/123,456` or `16123456` — the scripts clean these automatically.

**Ambiguous entities**: If the user says "Apple patents", that clearly means Apple Inc. But if they say "Tesla", ask whether they mean Tesla Inc. or Nikola Tesla the inventor — unless context makes it obvious.

### Step 4: Run the Query

Import and call the appropriate script function. All scripts are in the `scripts/` directory relative to this skill. For example:

```python
import os, sys
skill_dir = os.path.dirname(os.path.abspath(__file__))  # or use the known skill installation path
sys.path.insert(0, os.path.join(skill_dir, "scripts"))
from patentsview_search import search_by_assignee
result = search_by_assignee("Atari", fuzzy=True)
```

Or run via command line from the skill's root directory:
```bash
cd scripts/
python patentsview_search.py assignee "Atari"
```

### Step 5: Present Results Clearly

Never dump raw JSON at the user. Use the formatters in `format_results.py`:

```python
from format_results import format_patent_list
print(format_patent_list(result, source="patentsview"))
```

Or format results yourself following these principles:
- Lead with the answer to the user's question, not the data
- Show the most important fields first (patent number, title, date, assignee)
- For lists, show a numbered summary with key details
- For single patents, show a clean detail view
- Note the total count and whether there are more results available
- Mention data freshness (e.g., "PatentsView updates quarterly with ~3 month lag")

### Step 6: When Results Are Sparse

If you get few or no results:
1. Try a broader search (shorter name substring, fewer filters)
2. Try a different API (PatentsView vs ODP may index differently)
3. Check for typos or alternative spellings
4. Tell the user what you tried and suggest refinements

---

## Reference Documentation

Read these when you need detailed API syntax, field names, or endpoint specifics:

| Document | Read when... |
|----------|-------------|
| `references/patentsview-api.md` | Building PatentsView queries, need field names or operators |
| `references/odp-file-wrapper-api.md` | Querying ODP application data or documents |
| `references/ptab-api.md` | Searching PTAB proceedings or decisions |
| `references/office-actions-api.md` | Querying office action rejections, text, or citations (Lucene syntax) |
| `references/assignment-api.md` | Looking up patent assignments or ownership |
| `references/setup-and-auth.md` | Helping users set up API keys or troubleshoot auth |

---

## Multi-Step Query Patterns

Some questions require chaining calls across APIs. Here are common patterns:

### Full Patent Profile
User: "Tell me everything about patent 10,000,000"
1. `patentsview_search.search_by_patent_number("10000000")` → basic info
2. `patentsview_search.get_patent_citations("10000000")` → what it cites
3. `patentsview_search.get_cited_by("10000000")` → who cites it
4. `odp_search.search_applications(patent_number="10000000")` → get app number
5. `odp_search.get_application_documents(app_number)` → prosecution history
6. `odp_search.search_ptab_proceedings(patent_number="10000000")` → PTAB
7. `assignment_search.get_assignment_chain("10000000")` → ownership

### Competitor Portfolio Analysis
User: "How does Samsung's patent portfolio compare to LG's in display technology?"
1. `search_by_assignee("Samsung")` with CPC filter for display tech
2. `search_by_assignee("LG")` with same CPC filter
3. Compare counts, trends over time, citation metrics

### Download Prosecution File History
User: "Download the file history for application 16/123,456" or "Save the office actions for patent 11,887,351"
1. If user gave a patent number, resolve to application number: `odp_search.get_application_by_patent_number("11887351")`
2. List available documents: `download_documents.list_documents(app_number, key_only=True)`
3. Show the user what will be downloaded and confirm
4. Download: `download_documents.download_documents(app_number)`
   - Default: key prosecution docs only (office actions, amendments, IDS, etc.)
   - `--all` flag or user says "everything": downloads all documents
   - `--codes CTNF,CTFR` or user says "just the office actions": specific types
5. Report what was downloaded and where the files are saved (`downloads/{appNumber}/`)

**Note:** PDF downloads are rate-limited to 4/minute. The script handles this automatically with progress output. Re-running a download skips files that already exist.

### Pre-Litigation Check
User: "We're thinking of asserting patent 9,876,543. What should I know?"
1. PatentsView: basic info, citation count (is it well-cited?)
2. Assignments: clean chain of title?
3. PTAB: any prior challenges?
4. OA Rejections: how many rejections during prosecution?
5. Continuity: any related family members?

---

## Error Handling

If a script raises an `APIError`:
- **Missing API key**: Tell the user which key is missing and how to set it. Note: only the ODP key is required — PatentsView is optional.
- **Rate limit (429)**: The scripts retry automatically; if persistent, suggest waiting
- **Not found (404)**: Check the number format; suggest trying without formatting
- **Server error (5xx)**: The scripts retry; if persistent, the API may be down

**PatentsView fallback behavior**: The PatentsView API key is optional. When it's missing or PatentsView returns errors, inventor/assignee/keyword/patent number searches automatically fall back to the ODP free-text search API. ODP results may have different fields (e.g., no citation counts), but the formatters handle both sources transparently. CPC search, attorney search, and citation network queries require PatentsView and will return a descriptive message if the key is unavailable.

**Migration note (March 20, 2026)**: PatentsView is migrating to the Open Data Portal. If PatentsView stops working entirely, all functions with ODP fallbacks will continue working seamlessly.

---

## Security Reminders

- API keys are loaded from `.env` or environment variables — never hardcode them in source
- Never print or log API keys in output
- Never include keys in error messages shown to the user
- The `.env` file is git-ignored and must never be committed
- If sharing the project, only share `.env.example` (which contains no keys)
