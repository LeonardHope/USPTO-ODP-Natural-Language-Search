# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude skill (`uspto-patent-search`) that provides natural-language access to all major USPTO patent APIs. Users ask questions in plain English; SKILL.md contains a decision matrix that routes intent to the correct API and Python script function.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Interactive API key setup (writes .env)
python get_started.py

# Verify API keys are configured
cd scripts/ && python uspto_client.py

# Run scripts standalone (from scripts/ directory)
python patentsview_search.py assignee "Tesla"        # formatted output by default
python patentsview_search.py assignee "Tesla" --json  # raw JSON output
python patentsview_search.py patent 10000000
python patentsview_search.py citations 10000000
python patentsview_search.py inventor "Smith" --first "John" --year-from 2020
python patentsview_search.py keyword "autonomous vehicle lidar" --all
python patentsview_search.py cpc H04L
python patentsview_search.py attorney "Smith" --org "Fish & Richardson"
python odp_search.py get 16123456
python odp_search.py documents 16123456
python odp_search.py ptab --patent-number 10000000
python odp_search.py pta 14643719
python office_actions_search.py rejections --art-unit 3689 --type 103
python assignment_search.py chain 10000000
python download_documents.py list 16123456 --key-only
python download_documents.py download 16123456 --codes CTNF

# Run evals (skill-creator workflow)
# Uses evals/evals.json — 7 test cases covering common API workflows
```

**Dependencies:** Python 3.8+ with `requests` and `python-dotenv` (`pip install -r requirements.txt`).

## Architecture

### API Routing

The skill covers 7 API families across 5 scripts:

| API | Script | Auth Header | Base URL |
|-----|--------|-------------|----------|
| PatentsView | `patentsview_search.py` | `PATENTSVIEW_API_KEY` | search.patentsview.org |
| ODP File Wrapper | `odp_search.py` | `USPTO_ODP_API_KEY` | api.uspto.gov |
| ODP PTAB | `odp_search.py` | `USPTO_ODP_API_KEY` | api.uspto.gov |
| Legacy Office Actions | `office_actions_search.py` | `USPTO_ODP_API_KEY` | developer.uspto.gov (Lucene queries) |
| Assignments | `assignment_search.py` | `USPTO_ODP_API_KEY` | api.uspto.gov (ODP) |
| Document Download | `download_documents.py` | `USPTO_ODP_API_KEY` | api.uspto.gov |

All scripts import `USPTOClient` from `uspto_client.py`, which centralizes auth, rate limiting (token bucket per API), and retry logic with exponential backoff.

### Key Patterns

- **`uspto_client.py`** is the shared foundation -- every script calls `get_client()` to get a configured `USPTOClient` instance. Auth is via `X-Api-Key` header, keys loaded from `.env` file (via `python-dotenv`) or environment variables.
- **`format_results.py`** converts raw JSON responses to human-readable output. All scripts use it for CLI output.
- **PatentsView** uses JSON query operators with plain value matching (e.g. `{"field": "value"}`). Comparison operators (`_eq`, `_contains`, `_text_any`) are currently broken (500 errors). **Legacy OA APIs** use Lucene query syntax. These are fundamentally different query languages.
- **Fuzzy matching** is the default for assignee searches: tries common corporate name suffixes (Inc., LLC, Corp.) as an OR list since `_contains` is broken.
- **`references/`** docs are read on-demand by Claude for field names and query syntax -- they are not consumed by scripts at runtime.

### Multi-API Chaining

Complex queries chain calls across APIs sequentially. Example: "tell me everything about patent X" triggers PatentsView (basic info + citations) -> ODP (prosecution history) -> PTAB (challenges) -> Assignments (ownership).

## Design Decisions

- **`.env` file or environment variables** for API keys (`USPTO_ODP_API_KEY`, `PATENTSVIEW_API_KEY`). `get_started.py` provides interactive first-run setup. `.env` is git-ignored. Repo is intended for public GitHub distribution.
- **Patent/application number formats** are cleaned automatically by scripts -- accept `10,000,000`, `US10000000`, `16/123,456`, etc.
- **Rate limits** are handled transparently: PatentsView 45/min, ODP 60/min (4/min for PDFs), Legacy 60/min.
- **Legacy OA APIs** are being migrated to ODP in early 2026. Base URLs in `uspto_client.py` are configurable for this transition.
