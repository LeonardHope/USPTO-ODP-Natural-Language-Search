# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude skill for natural-language access to all USPTO Open Data Portal APIs. Users ask questions about patents and trademarks in plain English; SKILL.md contains a decision matrix that routes intent to the correct API and Python script.

## Commands

```bash
# Install dependencies (or use get_started.py which creates a venv automatically)
pip install -r requirements.txt

# Interactive API key setup (writes .env, creates venv, installs deps)
python get_started.py

# Verify API keys are configured
cd scripts/ && python uspto_client.py

# Run scripts standalone (from scripts/ directory)
python patent_search.py assignee "Tesla" --limit 10
python patent_search.py keyword "autonomous vehicle" --date-from 2020-01-01
python patent_search.py cpc H04L
python patent_search.py inventor "Smith" --first "John"
python patent_search.py examiner "Chen"
python patent_search.py patent 10000000
python file_wrapper.py get 16123456
python file_wrapper.py documents 16123456
python file_wrapper.py continuity 16123456
python file_wrapper.py pta 14643719
python file_wrapper.py attorney 16123456
python file_wrapper.py assignment 16123456
python file_wrapper.py transactions 16123456
python file_wrapper.py foreign-priority 16123456
python ptab_search.py proceedings --patent-number 10000000
python ptab_search.py appeals --query "claim construction"
python ptab_search.py interferences --query "priority"
python petition_search.py search --query "revival"
python office_actions_search.py rejections --art-unit 3689 --type 103
python office_actions_search.py text --patent-number 10000000
python office_actions_search.py citations --app-number 15638789
python assignment_search.py chain 10000000
python tsdr_search.py status --serial 88123456
python tsdr_search.py docs --serial 88123456
python bulk_data_search.py search --query "patent grant"
python download_documents.py list 16123456 --key-only
python download_documents.py download 16123456 --codes CTNF

# Add --json flag to any script for raw JSON output instead of formatted text
```

**Dependencies:** Python 3.8+ with `requests` and `python-dotenv` (`pip install -r requirements.txt`).

## Architecture

### API Keys

Only **`USPTO_ODP_API_KEY`** is needed. One key covers all APIs:

- ODP Patent APIs (File Wrapper, PTAB, Petitions, Bulk Data) -- uses `X-API-KEY` header
- DSAPI Office Action APIs -- uses `X-API-KEY` header
- TSDR Trademark API -- uses `USPTO-API-KEY` header (different header name, same key value)

The key is obtained from [data.uspto.gov/myodp](https://data.uspto.gov/myodp). It is loaded from `.env` (via `python-dotenv`) or environment variables.

### API Routing

The skill covers 9 API families across 10 scripts:

| API Family | Script | Base URL |
|------------|--------|----------|
| Patent Search (ODP) | `patent_search.py` | api.uspto.gov |
| File Wrapper Sub-Resources | `file_wrapper.py` | api.uspto.gov |
| PTAB Trials, Appeals, Interferences | `ptab_search.py` | api.uspto.gov |
| Petition Decisions | `petition_search.py` | api.uspto.gov |
| Office Action Rejections (DSAPI) | `office_actions_search.py` | api.uspto.gov |
| Office Action Text (DSAPI) | `office_actions_search.py` | api.uspto.gov |
| Office Action Citations (DSAPI) | `office_actions_search.py` | api.uspto.gov |
| Assignments | `assignment_search.py` | api.uspto.gov |
| TSDR (Trademarks) | `tsdr_search.py` | tsdrapi.uspto.gov |
| Bulk Datasets | `bulk_data_search.py` | api.uspto.gov |
| Document Download | `download_documents.py` | api.uspto.gov |

### Key Patterns

- **`uspto_client.py`** is the shared foundation. Every script calls `get_client()` to get a configured `USPTOClient` instance. Auth headers, rate limiting (token bucket per API family), and retry logic with exponential backoff are all centralized here.
- **`format_results.py`** converts raw JSON responses to human-readable output. Handles all response formats across API families. Uses `response.get("error")` (truthy check) for error detection.
- **Utility functions** in `uspto_client.py`:
  - `clean_patent_number(num)` -- normalizes patent numbers (strips `US`, commas, slashes)
  - `clean_app_number(num)` -- normalizes application numbers
  - `resolve_patent_to_app_number(patent_num)` -- looks up the application number for a granted patent via ODP search
- **`references/`** docs are read on-demand by Claude for field names and query syntax. They are not consumed by scripts at runtime.

### Multi-API Chaining

Complex queries chain calls across APIs sequentially. Example: "tell me everything about patent X" triggers Patent Search (basic info) -> File Wrapper (prosecution history, continuity) -> PTAB (challenges) -> Assignments (ownership). The SKILL.md decision matrix guides which APIs to call for each type of question.

## Design Decisions

- **`.env` file or environment variables** for API keys. `get_started.py` provides interactive first-run setup. `.env` is git-ignored. Repo is intended for public distribution.
- **Single API key** -- `USPTO_ODP_API_KEY` covers everything. No optional keys, no fallback logic needed.
- **Patent/application number formats** are cleaned automatically by `clean_patent_number()` and `clean_app_number()`. Accept `10,000,000`, `US10000000`, `16/123,456`, etc.
- **Rate limits** are handled transparently: ODP 60/min (4/min for PDFs), DSAPI 60/min, TSDR 60/min.
- **DSAPI endpoints** (`api.uspto.gov/api/v1/patent/oa/`) use **Lucene/Solr query syntax** (e.g., `patentApplicationNumber:15638789 AND hasRej103:1`). ODP search endpoints use **opensearch-style** JSON bodies with `q`, `filters`, `rangeFilters`, and `sort` parameters. These are fundamentally different query languages -- do not mix them.
- **TSDR responses** are often XML rather than JSON. The client's `_request` method returns `{"raw_xml": text}` for XML content types. The `tsdr_search.py` script handles XML parsing.
