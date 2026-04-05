# USPTO Open Data Portal Search Skill

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that provides natural-language access to all USPTO Open Data Portal APIs for patent and trademark data. Ask questions in plain English -- the skill handles API selection, query construction, and result formatting automatically.

## What It Does

Instead of learning multiple API syntaxes, you can ask things like:

- *"Find all patents assigned to Tesla"*
- *"Has patent 10,585,959 been challenged at PTAB?"*
- *"Show me the prosecution history for application 16/123,456"*
- *"Who currently owns patent 11,887,351?"*
- *"What rejections were issued during prosecution of patent 10,000,000?"*
- *"What is the status of trademark serial number 88/123,456?"*
- *"Search for petition decisions about revival"*
- *"What bulk datasets are available for patent grants?"*

The skill determines which API to query, builds the request, handles authentication and rate limiting, and presents results in a readable format.

## Features

The skill covers the full breadth of the USPTO Open Data Portal:

### Patent File Wrapper
- **Search** -- Find patents by assignee, inventor, keyword, CPC classification, examiner, or status
- **Metadata** -- Application status, filing dates, examiner info
- **Documents** -- Full prosecution file history (office actions, responses, drawings)
- **Continuity** -- Parent/child/divisional application chains
- **Patent Term Adjustment (PTA)** -- Days added/subtracted from patent term
- **Assignments** -- Ownership records and chain of title
- **Attorney of Record** -- Current correspondence information
- **Transactions** -- Complete transaction history for an application
- **Foreign Priority** -- Foreign priority claims and Paris Convention data

### PTAB (Patent Trial and Appeal Board)
- **Trial Proceedings** -- IPR, PGR, CBM, and derivation proceedings
- **Trial Decisions & Documents** -- Board decisions and supporting documents
- **Appeal Decisions** -- Ex parte appeal outcomes
- **Interference Decisions** -- Priority contests between applications

### Petition Decisions
- Search and retrieve petition decisions (revival, extensions of time, prioritized examination, etc.)

### Office Actions (DSAPI)
- **Rejections** -- Structured rejection data (101, 102, 103, 112) with examiner and art unit
- **Full Text** -- Complete office action text including examiner amendments
- **Citations** -- Prior art cited in office actions with NLP-parsed passage references

### Trademark Status & Document Retrieval (TSDR)
- **Case Status** -- Current trademark status, mark details, ownership
- **Documents** -- Prosecution documents, registration certificates
- **Batch Lookup** -- Multiple trademark statuses in one call

### Bulk Data
- **Dataset Discovery** -- Search and browse available bulk data products
- **Downloads** -- Patent grants, applications, classifications, assignments in XML/CSV/JSON

## Requirements

- Python 3.8+
- `requests`
- `python-dotenv`

## Quick Start

### 1. Get Your API Key(s)

**Required:** USPTO Open Data Portal (ODP) key

1. Go to [data.uspto.gov/myodp](https://data.uspto.gov/myodp)
2. Create a USPTO.gov account and verify with ID.me (one-time)
3. Copy your API key from the My ODP page

This key covers patent search, file wrapper data, PTAB (trials, appeals, interferences), petition decisions, office actions, and bulk datasets.

**Optional:** USPTO TSDR (trademark) key

Trademark searches via the TSDR API require a separate key (the USPTO did not consolidate TSDR under the ODP key). Register for one at [account.uspto.gov/api-manager](https://account.uspto.gov/api-manager) if you need trademark support. Leave blank to skip.

### 2. Run the Setup Wizard

```bash
python3 get_started.py
```

The wizard handles everything automatically:
- Creates a Python virtual environment and installs dependencies
- Prompts for your API key with a link to where you can get it
- Shows a masked preview so you can confirm what you entered
- Saves everything to a `.env` file (git-ignored, never committed)

You can re-run `get_started.py` anytime to update your key.

### 3. Try a Query

```bash
cd scripts/
python patent_search.py assignee "Tesla" --limit 10
```

## Installation as a Claude Skill

### Claude Code

Add the skill directory to your Claude Code configuration by running `/install-skill` from within Claude Code, or by adding the path to your skill settings manually. The skill activates automatically when Claude detects patent- or trademark-related queries.

## Module Reference

All scripts live in the `scripts/` directory and work both as importable modules and standalone CLI tools.

| Script | Purpose |
|--------|---------|
| `uspto_client.py` | Shared client: authentication, rate limiting, retries for all APIs |
| `patent_search.py` | Patent search by assignee, inventor, keyword, CPC, examiner, status |
| `file_wrapper.py` | File wrapper sub-resources: metadata, documents, continuity, PTA, assignments, attorney, transactions, foreign priority |
| `ptab_search.py` | PTAB trials (proceedings, decisions, documents), appeals, interferences |
| `petition_search.py` | Petition decision search and retrieval |
| `office_actions_search.py` | Office action rejections, full text, and citations (DSAPI) |
| `assignment_search.py` | Patent ownership and chain-of-title lookups |
| `tsdr_search.py` | Trademark status, documents, and batch lookups (TSDR API) |
| `bulk_data_search.py` | Bulk dataset discovery and download |
| `download_documents.py` | List and download prosecution file history PDFs |
| `format_results.py` | JSON-to-human-readable output formatting |

## CLI Examples

All commands are run from the `scripts/` directory.

### Patent Search

```bash
# Search by assignee
python patent_search.py assignee "Tesla" --limit 10

# Search by keyword with date filter
python patent_search.py keyword "autonomous vehicle" --date-from 2020-01-01

# Search by CPC classification
python patent_search.py cpc H04L
```

### File Wrapper

```bash
# Get full application data
python file_wrapper.py get 16123456

# List prosecution documents
python file_wrapper.py documents 16123456

# Get continuity (parent/child) data
python file_wrapper.py continuity 16123456
```

### PTAB

```bash
# Search trial proceedings by patent number
python ptab_search.py proceedings --patent-number 10000000

# Search appeal decisions
python ptab_search.py appeals --query "claim construction"
```

### Petition Decisions

```bash
# Search petition decisions
python petition_search.py search --query "revival"
```

### Office Actions

```bash
# Search rejections by art unit and type
python office_actions_search.py rejections --art-unit 3689 --type 103
```

### Assignments

```bash
# Get assignment chain of title
python assignment_search.py chain 10000000
```

### Trademarks (TSDR)

```bash
# Get trademark status by serial number
python tsdr_search.py status --serial 88123456
```

### Bulk Data

```bash
# Search available bulk datasets
python bulk_data_search.py search --query "patent grant"
```

### Document Download

```bash
# List key prosecution documents
python download_documents.py list 16123456 --key-only
```

## Architecture

### Client / Module Structure

All scripts share a common foundation through `uspto_client.py`:

```
                  ┌─────────────────┐
                  │  uspto_client.py │
                  │  (auth, rate     │
                  │   limits, retry) │
                  └────────┬────────┘
                           │
        ┌──────────┬───────┼───────┬──────────┐
        │          │       │       │          │
   patent_    file_    ptab_   office_    tsdr_
   search    wrapper  search  actions   search
                                         ...
        │          │       │       │          │
        └──────────┴───────┼───────┴──────────┘
                           │
                  ┌────────┴────────┐
                  │ format_results  │
                  │ (JSON → human-  │
                  │  readable text) │
                  └─────────────────┘
```

- **`USPTOClient`** in `uspto_client.py` handles authentication (API key via `X-Api-Key` or `USPTO-API-KEY` header depending on endpoint), rate limiting (token bucket per API family), and retry logic with exponential backoff.
- Each module imports `get_client()` to obtain a configured client instance.
- **`format_results.py`** converts raw API JSON into human-readable output for each data type.
- Utility functions `clean_patent_number()`, `clean_app_number()`, and `resolve_patent_to_app_number()` in the client handle format normalization so users can input numbers in any common format (`10,000,000`, `US10000000`, `16/123,456`, etc.).

### API Keys

`USPTO_ODP_API_KEY` from [data.uspto.gov/myodp](https://data.uspto.gov/myodp) covers all patent-side APIs (search, file wrapper, PTAB, petitions, office actions, bulk data).

`USPTO_TSDR_API_KEY` from [account.uspto.gov/api-manager](https://account.uspto.gov/api-manager) is required only for trademark searches via the TSDR API. The USPTO maintains TSDR on a separate key system.

### Rate Limits

Rate limiting is handled automatically with token bucket algorithms and exponential backoff:

| API Family | Limit | Handling |
|------------|-------|---------|
| ODP (Patent, PTAB, Petitions, Bulk Data) | 60 req/min | Auto-wait + retry |
| ODP PDF/ZIP Downloads | 4 req/min | Auto-wait + retry |
| DSAPI (Office Actions) | 60 req/min | Auto-wait + retry |
| TSDR (Trademarks) | 60 req/min | Auto-wait + retry |

## Project Structure

```
uspto-patent-search/
├── SKILL.md                    # Skill instructions (Claude reads this)
├── CLAUDE.md                   # Claude Code project guidance
├── get_started.py              # Interactive API key setup
├── requirements.txt            # Python dependencies
├── .env.example                # Template for API key configuration
├── .gitignore
├── README.md
├── LICENSE
├── references/
│   ├── odp-api-complete-reference.md
│   ├── odp-file-wrapper-api.md
│   ├── ptab-api.md
│   ├── office-actions-api.md
│   ├── assignment-api.md
│   └── setup-and-auth.md
├── scripts/
│   ├── uspto_client.py         # Shared client: auth, rate limiting, retries
│   ├── patent_search.py        # Patent search (assignee, keyword, CPC, etc.)
│   ├── file_wrapper.py         # File wrapper sub-resources
│   ├── ptab_search.py          # PTAB trials, appeals, interferences
│   ├── petition_search.py      # Petition decisions
│   ├── office_actions_search.py # Office action rejections, text, citations
│   ├── assignment_search.py    # Patent ownership lookups
│   ├── tsdr_search.py          # Trademark status & documents
│   ├── bulk_data_search.py     # Bulk dataset discovery & download
│   ├── download_documents.py   # Prosecution file history download
│   └── format_results.py       # Output formatting
└── evals/
    └── evals.json              # Test cases for skill evaluation
```

## Security

- API keys are loaded from a `.env` file (via `python-dotenv`) or environment variables -- never hardcoded
- Keys are never logged, printed, or included in error messages
- `.gitignore` excludes `.env` files to prevent accidental commits
- `.env.example` contains variable names only -- no real keys
- `get_started.py` masks key values in its output

## Contributing

Contributions welcome. If you find an API endpoint has changed or a new USPTO API becomes available, please open an issue or PR.

## License

See LICENSE.
