# USPTO Patent Search Skill

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) / [Cowork](https://claude.ai) skill that provides a unified, natural-language interface to all major USPTO patent APIs. Ask questions in plain English — the skill handles API selection, query construction, and result formatting automatically.

## What It Does

Instead of learning multiple API syntaxes, you can ask things like:

- *"Find all patents assigned to a company called Atari or similar"*
- *"Has patent 10,585,959 been challenged at PTAB?"*
- *"Show me the prosecution history for application 16/123,456"*
- *"Who currently owns patent 11,887,351?"*
- *"What is the current status of application 16/123,456?"*
- *"What rejections were issued during prosecution of patent 10,000,000?"*
- *"What patents cite US 10,000,000?"*
- *"List the key prosecution documents for application 16/123,456"*
- *"Show me the parent and child applications for 16/538,307"*
- *"Show me the full text of the office action for patent 10,000,000"*
- *"What prior art was cited in the office actions for application 15/638,789?"*
- *"Download the file wrapper for application 16/123,456"*

The skill determines which API to query, builds the request, handles authentication and rate limiting, and presents results in a readable format.

## APIs Covered

| API | Source | Status | What It Provides |
|-----|--------|--------|-----------------|
| **PatentsView PatentSearch** | search.patentsview.org | Migrating to ODP March 20, 2026 | Inventor/assignee/keyword search, citation networks, analytics across granted patents |
| **ODP Patent File Wrapper** | api.uspto.gov | Stable | Application status, prosecution history documents, continuity data |
| **ODP PTAB** | api.uspto.gov | Stable | IPR, PGR, CBM trials, appeal decisions |
| **Office Action Rejection** | developer.uspto.gov | Migrating to ODP | Structured rejection data (101, 102, 103, 112) |
| **Office Action Text** | developer.uspto.gov | Migrating to ODP | Full text of office actions |
| **Enriched Citations** | developer.uspto.gov | v3 migrating to ODP; v1/v2 decommissioned | NLP-parsed prior art citations (Oct 2017 – April 2019 only) |
| **Patent Assignments** | api.uspto.gov (ODP) | Stable | Ownership transfers, chain of title, security interests |

## Prerequisites

- Python 3.8+
- Two free API keys (see Setup below). Note: obtaining a PatentsView key may be difficult — see [Migration Notice](#uspto-api-migration-march-20-2026).

## Setup

### 1. Get API Keys (both free)

**USPTO Open Data Portal key:**
1. Go to [data.uspto.gov/myodp](https://data.uspto.gov/myodp)
2. Create a USPTO.gov account and verify with ID.me (one-time)
3. Copy your API key from the My ODP page

**PatentsView key:**
1. The original key request page at patentsview.org has been removed. Try the [PatentsView support portal](https://patentsview-support.atlassian.net/servicedesk/customer/portal/1/group/1/create/18) instead.
2. If that link stops working, PatentsView is migrating to the USPTO Open Data Portal on March 20, 2026 — a single ODP key may cover both APIs after the migration.

### 2. Run the Setup Wizard

```bash
python3 get_started.py
```

That's it — the wizard handles everything automatically:
- Creates a Python virtual environment and installs dependencies
- Prompts for each API key with a link to where you can get it
- Shows a masked preview so you can confirm what you entered
- Saves everything to a `.env` file (git-ignored, never committed)

On first use, the wizard also launches automatically if keys are not yet configured. You can re-run it anytime to update a key.

**Alternative — set environment variables** manually in your shell profile (`~/.zshrc`, `~/.bashrc`, etc.):
```bash
export USPTO_ODP_API_KEY="your_odp_key_here"
export PATENTSVIEW_API_KEY="your_patentsview_key_here"
```

## Installation as a Claude Skill

### Claude Code

Add the skill directory to your Claude Code configuration by running `/install-skill` from within Claude Code, or by adding the path to your skill settings manually. The skill is activated automatically when Claude detects patent-related queries.

### Cowork

The skill can be installed through the Cowork plugin system. Place the skill directory where your Cowork session can access it.

## Project Structure

```
uspto-patent-search/
├── SKILL.md                           # Core skill instructions (Claude reads this)
├── CLAUDE.md                          # Claude Code project instructions
├── get_started.py                      # Interactive API key setup (writes .env)
├── requirements.txt                   # Python dependencies
├── .env.example                       # Template for API key configuration
├── .gitignore
├── README.md
├── references/
│   ├── patentsview-api.md             # PatentsView query language, fields, endpoints
│   ├── odp-file-wrapper-api.md        # ODP application search and document retrieval
│   ├── ptab-api.md                    # PTAB proceedings and decisions
│   ├── office-actions-api.md          # Office action rejections, citations, text (Lucene)
│   ├── assignment-api.md              # Patent assignment / ownership records
│   └── setup-and-auth.md             # Detailed setup instructions and troubleshooting
├── scripts/
│   ├── uspto_client.py                # Shared client: auth, rate limiting, retries
│   ├── patentsview_search.py          # PatentsView API search functions
│   ├── odp_search.py                  # ODP File Wrapper + PTAB queries
│   ├── office_actions_search.py       # Legacy Office Action APIs (Lucene queries)
│   ├── assignment_search.py           # Patent assignment / ownership lookups
│   ├── download_documents.py          # List and download prosecution file history
│   └── format_results.py             # JSON → human-readable output formatting
└── evals/
    └── evals.json                     # Test cases for skill evaluation
```

## How It Works

The skill uses a decision matrix to route natural language questions to the right API:

- **"Search by inventor or company"** → PatentsView (disambiguated name data, fuzzy name matching). *Note: some query operators are currently broken; the skill uses workarounds.*
- **"Application status or prosecution docs"** → ODP File Wrapper (real-time data, full file wrappers)
- **"PTAB challenges"** → ODP PTAB API (IPR/PGR/CBM proceedings and decisions)
- **"Office action rejections"** → Legacy OA APIs (structured 101/102/103/112 rejection data). *Migrating to ODP.*
- **"Full text of an office action"** → Legacy OA Text API (examiner's amendments, detailed reasoning). *Migrating to ODP.*
- **"What prior art was cited?"** → Enriched Citations API (NLP-parsed references with passage locations). *Data frozen as of April 2019.*
- **"Who owns this patent?"** → ODP Assignment data (complete chain of title)
- **"Download prosecution documents"** → ODP File Wrapper (PDF download with rate limiting)

For complex questions, the skill chains multiple API calls. For example, "tell me everything about patent X" triggers calls to PatentsView (basic info), Assignments (ownership), PTAB (challenges), and ODP (prosecution history).

## Scripts — Standalone Usage

The scripts also work standalone from the command line:

```bash
cd scripts/

# Search patents by assignee
python patentsview_search.py assignee "Tesla"

# Look up a specific patent
python patentsview_search.py patent 10000000

# Get citations for a patent
python patentsview_search.py citations 10000000

# Search by inventor
python patentsview_search.py inventor "Smith" --first "John"

# Search by keyword (title search)
python patentsview_search.py keyword "autonomous vehicle lidar"

# Search by CPC classification code
python patentsview_search.py cpc H04L

# Search by attorney or law firm
python patentsview_search.py attorney "Smith" --org "Fish & Richardson"

# Get application details from ODP
python odp_search.py get 16123456

# Get file wrapper documents
python odp_search.py documents 16123456

# Search PTAB proceedings
python odp_search.py ptab --patent-number 10000000

# Get patent term adjustment data
python odp_search.py pta 14643719

# Search office action rejections for a patent
python office_actions_search.py rejections --patent-number 10000000

# Get full text of office actions
python office_actions_search.py text --patent-number 10000000

# Search enriched citations (prior art cited in OAs)
python office_actions_search.py citations --app-number 15638789

# Get assignment chain
python assignment_search.py chain 10000000

# List key prosecution documents
python download_documents.py list 16123456 --key-only

# Download prosecution file history
python download_documents.py download 16123456
```

## Rate Limits

The scripts handle rate limiting automatically with token bucket algorithms and exponential backoff:

| API | Limit | Handling |
|-----|-------|---------|
| PatentsView | 45 req/min | Auto-wait + retry |
| ODP (File Wrapper, PTAB, Assignments) | 60 req/min (4/min for PDFs) | Auto-wait + retry |
| Legacy OA APIs | 60 req/min | Auto-wait + retry |

## Security

This project follows security best practices for open-source API key management:

- API keys are loaded from a **`.env` file** (via `python-dotenv`) or **environment variables** — never hardcoded
- Keys are **never logged, printed, or included in error messages**
- The `.gitignore` excludes `.env` files to prevent accidental commits
- The `.env.example` file contains variable names only — no real keys
- `get_started.py` masks key values in its output

If you fork this repo, ensure you never commit API keys. See `references/setup-and-auth.md` for detailed security guidance.

## Data Freshness

Different APIs have different update schedules:

| API | Update Frequency | Notes |
|-----|-----------------|-------|
| ODP File Wrapper | Daily | Stable — real-time application data |
| ODP PTAB | Near-real-time | Stable — syncs with PTAB case tracking system |
| ODP Assignments | Daily | Stable — all recorded assignments |
| PatentsView | Quarterly | Migrating March 20, 2026 — ~3 month lag for newest grants |
| Legacy OA Rejections | Daily | Migrating to ODP — June 2018 to ~180 days ago |
| Legacy OA Text | Daily | Migrating to ODP — office action full text |
| Enriched Citations | Frozen | v1/v2 decommissioned Jan 2026; v3 migrating to ODP — Oct 2017 – April 2019 only |

**Limitation — recently issued patents:** PatentsView is the primary API for broad keyword, inventor, and assignee searches across granted patents, but it updates quarterly with an approximately 3-month lag. Patents issued in the most recent ~3 months will not appear in PatentsView search results. The ODP File Wrapper API updates daily and can look up specific recent patents by application or patent number, but it does not support the same broad keyword-based discovery searches. There is currently no USPTO API that combines both real-time coverage and full-text search across all granted patents.

## USPTO API Migration (March 20, 2026)

The USPTO is consolidating all patent data APIs onto the [Open Data Portal](https://data.uspto.gov). Several migrations are happening on overlapping timelines, and some have already completed:

### PatentsView → Open Data Portal (March 20, 2026)

PatentsView will migrate from `search.patentsview.org` to the USPTO Open Data Portal on **March 20, 2026**. The USPTO has indicated that some PatentsView functions will experience temporary interruptions during the transition. It is not yet clear whether the current PatentSearch API query format, endpoints, or authentication will change after the migration.

Additionally, the PatentsView team has taken down their community forum and removed the API key request link from patentsview.org. New API keys may still be available via their [Atlassian support portal](https://patentsview-support.atlassian.net/servicedesk/customer/portal/1/group/1/create/18).

**What may break:** `patentsview_search.py` — base URL, query syntax, field names, and API key handling could all change.

### Legacy Office Action APIs → Open Data Portal (in progress)

The following APIs at `developer.uspto.gov` are being migrated to the new Open Data Portal:

| API | Status |
|-----|--------|
| Enriched Citation API v1/v2 | **Decommissioned** (January 30, 2026) |
| Office Action Citations API (beta) | **Decommissioned** (January 30, 2026) |
| Enriched Citation API v3 | Migrating to ODP |
| Office Action Rejection API | Migrating to ODP |
| Office Action Text Retrieval API | Migrating to ODP |

**What may break:** `office_actions_search.py` — the `developer.uspto.gov/ds-api` base URL and Lucene query syntax will likely change when these move to ODP.

### Known Limitations (current)

- **PatentsView query operators** (`_contains`, `_eq`, `_text_any`, `_gte`, etc.) are currently returning 500 errors. This may be related to the pending migration. The code works around this by using plain value matching and corporate name variant lists for fuzzy search. Year range filtering is temporarily unavailable.
- **Enriched Citations** data is frozen as of April 2019 and covers only office actions from October 2017 through April 2019. The v1/v2 APIs have been decommissioned; only v3 remains.

### Staying Updated

- Check [data.uspto.gov](https://data.uspto.gov) for ODP updates
- Check [search.patentsview.org/docs](https://search.patentsview.org/docs/) for PatentsView API status
- Check [developer.uspto.gov](https://developer.uspto.gov) for legacy API decommission notices

An updated version of this skill targeting the post-migration APIs is planned for release by March 20, 2026.

## Contributing

Contributions welcome. If you find an API endpoint has changed or a new USPTO API becomes available, please open an issue or PR.

## License

Apache 2.0
