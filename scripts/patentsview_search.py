"""
PatentsView PatentSearch API - Search module.

Provides natural-language-friendly functions for searching the PatentsView API.
Handles query construction, fuzzy matching, and pagination.

API: https://search.patentsview.org/api/v1/
Auth: PATENTSVIEW_API_KEY env var, sent as X-Api-Key header
Rate limit: 45 requests/minute
Data coverage: Granted US patents (updated quarterly, ~3 month lag)

Query format (as of 2026):
  Plain value exact match:  {"field": "value"}
  List = OR match:          {"field": ["val1", "val2"]}
  Logical operators:        {"_and": [cond1, cond2]}, {"_or": [cond1, cond2]}
  Text search on titles:    {"patent_title": "search terms"}

  NOTE: Comparison operators (_eq, _contains, _begins, _text_any, etc.)
  are currently returning 500 errors. All queries use plain value matching.

  Field names for nested entities require dot-notation prefixes:
    assignees.assignee_organization, inventors.inventor_name_last, etc.
  The API always returns full nested arrays regardless of requested fields.
"""

import json
import sys
import argparse
import logging
from typing import Optional

from uspto_client import get_client, APIError
from format_results import format_patent_list, format_patent_detail, format_citation_list

logger = logging.getLogger("patentsview_search")


# ── Default field sets ──────────────────────────────────────────────────
# The API returns full nested arrays (assignees[], inventors[], etc.)
# automatically. These field lists only control top-level patent fields.

PATENT_SUMMARY_FIELDS = [
    "patent_id",
    "patent_title",
    "patent_date",
    "patent_year",
    "patent_type",
    "patent_num_times_cited_by_us_patents",
]

PATENT_DETAIL_FIELDS = PATENT_SUMMARY_FIELDS + [
    "patent_abstract",
    "patent_num_us_patents_cited",
    "patent_processing_days",
]


# ── Fuzzy assignee name matching ───────────────────────────────────────

def _assignee_name_variants(name: str) -> list:
    """Generate common corporate name variations for fuzzy matching.

    Since _contains is broken, we try exact matches against common suffixes.
    """
    name = name.strip()
    # Start with the exact name
    variants = [name]

    # If the name already has a suffix, also try without it
    suffixes = [", Inc.", " Inc.", " Inc", " Incorporated",
                ", LLC", " LLC",
                " Corp.", " Corp", " Corporation",
                ", Ltd.", " Ltd.", " Limited",
                " Co.", " Company", " L.P."]
    name_lower = name.lower()
    for suffix in suffixes:
        if name_lower.endswith(suffix.lower()):
            base = name[:len(name) - len(suffix)].strip()
            if base and base not in variants:
                variants.insert(0, base)
            break

    # If the name looks like a bare name (no suffix), add common suffixes
    has_suffix = any(name_lower.endswith(s.lower()) for s in suffixes)
    if not has_suffix:
        for suffix in [", Inc.", " Inc.", " Incorporated", " LLC", " Corp.", " Corporation"]:
            variant = name + suffix
            if variant not in variants:
                variants.append(variant)

    return variants


def _search_assignee_entity(name: str) -> list:
    """Search the /assignee/ endpoint to find exact organization names.

    NOTE: The /assignee/ entity endpoint uses unprefixed field names
    (assignee_organization), NOT dot-notation (assignees.assignee_organization).

    Returns a list of matching assignee organization names.
    """
    client = get_client()
    try:
        result = client.patentsview_get(
            endpoint="assignee",
            q={"assignee_organization": name},
            f=["assignee_organization", "assignee_num_patents"],
            o={"size": 10},
        )
        assignees = result.get("assignees", [])
        return [a["assignee_organization"] for a in assignees
                if a.get("assignee_organization")]
    except APIError:
        return []


# ── Search functions ────────────────────────────────────────────────────

def search_patents(query: dict, fields: list = None, sort: list = None,
                   size: int = 25, after: str = None) -> dict:
    """Run a patent search with the given query.

    Args:
        query: PatentsView query dict using plain value matching
        fields: Fields to return (defaults to summary set)
        sort: Sort spec, e.g. [{"patent_date": "desc"}]
        size: Results per page (max 1000)
        after: Cursor for pagination

    Returns:
        Full API response with patents, count, total_hits
    """
    client = get_client()
    options = {"size": min(size, 1000)}
    if after:
        options["after"] = after
    return client.patentsview_get(
        endpoint="patent",
        q=query,
        f=fields or PATENT_SUMMARY_FIELDS,
        s=sort or [{"patent_date": "desc"}],
        o=options,
    )


def search_by_assignee(name: str, fuzzy: bool = True,
                       year_from: int = None, year_to: int = None,
                       size: int = 25) -> dict:
    """Search patents by assignee (company/organization) name.

    Since _contains is broken, fuzzy matching works by trying common
    corporate name variations (Inc., LLC, Corp., etc.) as an OR list.

    Falls back to ODP free-text search when PatentsView returns no results
    (PatentsView has assignee data gaps for some patents).

    Args:
        name: Company or organization name
        fuzzy: If True, try name variations; if False, exact match only
        year_from: Filter patents granted on or after this year
        year_to: Filter patents granted on or before this year
        size: Number of results to return
    """
    if fuzzy:
        variants = _assignee_name_variants(name)
        if len(variants) == 1:
            q = {"assignees.assignee_organization": variants[0]}
        else:
            q = {"assignees.assignee_organization": variants}
    else:
        q = {"assignees.assignee_organization": name}

    # NOTE: Date range operators (_gte, _lte) are currently broken.
    # Year filtering is not available until operators are restored.
    if year_from or year_to:
        logger.warning(
            "Year filtering is currently unavailable — PatentsView comparison "
            "operators are returning errors. Returning unfiltered results."
        )

    result = search_patents(q, size=size)

    # Fallback: if PatentsView returned no results, try ODP free-text search
    if result.get("total_hits", 0) == 0:
        logger.info(
            f"PatentsView returned 0 results for assignee '{name}'. "
            "Falling back to ODP search."
        )
        try:
            return _odp_assignee_fallback(name, size=size)
        except Exception as e:
            logger.warning(f"ODP fallback failed: {e}")

    return result


def _odp_assignee_fallback(name: str, size: int = 25) -> dict:
    """Search ODP for patents by assignee name as a fallback.

    ODP assignment records often have assignee data that PatentsView lacks.
    Returns results in a format compatible with format_patent_list(source='odp').
    """
    from odp_search import search_applications
    odp_result = search_applications(query=name, rows=size)
    # Mark source as ODP so the formatter handles it correctly
    odp_result["_source"] = "odp"
    return odp_result


def search_by_inventor(last_name: str, first_name: str = None,
                       fuzzy: bool = True, year_from: int = None,
                       year_to: int = None, size: int = 25) -> dict:
    """Search patents by inventor name.

    Args:
        last_name: Inventor's last name (exact match)
        first_name: Inventor's first name (optional, exact match)
        fuzzy: Ignored (kept for API compatibility — _contains is broken)
        year_from: Currently unavailable (operators broken)
        year_to: Currently unavailable (operators broken)
        size: Number of results
    """
    conditions = [{"inventors.inventor_name_last": last_name}]

    if first_name:
        conditions.append({"inventors.inventor_name_first": first_name})

    if year_from or year_to:
        logger.warning(
            "Year filtering is currently unavailable — PatentsView comparison "
            "operators are returning errors. Returning unfiltered results."
        )

    q = {"_and": conditions} if len(conditions) > 1 else conditions[0]
    return search_patents(q, size=size)


def search_by_keyword(keywords: str, search_in: str = "title",
                      match_all: bool = False, year_from: int = None,
                      year_to: int = None, size: int = 25) -> dict:
    """Search patents by keyword in title.

    NOTE: With operators broken, only patent_title supports text search
    via plain value matching. Abstract and claims search is unavailable.

    Args:
        keywords: Search terms
        search_in: Ignored (only title search works currently)
        match_all: Ignored (plain value matching only)
        year_from: Currently unavailable (operators broken)
        year_to: Currently unavailable (operators broken)
        size: Number of results
    """
    if search_in not in ("title", "title_and_abstract"):
        logger.warning(
            "Only title search is currently available. Abstract/claims search "
            "requires operators that are returning errors. Searching title only."
        )

    q = {"patent_title": keywords}

    if year_from or year_to:
        logger.warning(
            "Year filtering is currently unavailable — PatentsView comparison "
            "operators are returning errors. Returning unfiltered results."
        )

    return search_patents(q, fields=PATENT_DETAIL_FIELDS, size=size)


def search_by_cpc(cpc_code: str, year_from: int = None,
                  year_to: int = None, size: int = 25) -> dict:
    """Search patents by CPC classification code.

    Args:
        cpc_code: CPC class, subclass, or group (e.g. 'H04L', 'G06N')
        year_from: Currently unavailable (operators broken)
        year_to: Currently unavailable (operators broken)
        size: Number of results
    """
    # Determine the appropriate field based on code length
    if len(cpc_code) <= 4:
        field = "cpc_current.cpc_subclass_id"
    else:
        field = "cpc_current.cpc_group_id"

    q = {field: cpc_code}

    if year_from or year_to:
        logger.warning(
            "Year filtering is currently unavailable — PatentsView comparison "
            "operators are returning errors. Returning unfiltered results."
        )

    return search_patents(q, size=size)


def search_by_patent_number(patent_number: str) -> dict:
    """Get a specific patent by its patent number.

    Args:
        patent_number: US patent number (e.g. '10000000', 'RE49000')
    """
    # Strip common formatting
    clean = patent_number.replace(",", "").replace("US", "").strip()
    q = {"patent_id": clean}
    return search_patents(q, fields=PATENT_DETAIL_FIELDS, size=1)


def search_by_attorney(last_name: str, first_name: str = None,
                       organization: str = None, size: int = 25) -> dict:
    """Search patents by attorney or law firm.

    Args:
        last_name: Attorney's last name
        first_name: Attorney's first name (optional)
        organization: Law firm name (optional)
        size: Number of results
    """
    conditions = [{"attorneys.attorney_name_last": last_name}]
    if first_name:
        conditions.append({"attorneys.attorney_name_first": first_name})
    if organization:
        conditions.append({"attorneys.attorney_organization": organization})

    q = {"_and": conditions} if len(conditions) > 1 else conditions[0]
    return search_patents(q, size=size)


def get_patent_citations(patent_number: str, size: int = 100) -> dict:
    """Get US patent citations for a given patent.

    Args:
        patent_number: The citing patent's number
        size: Number of citations to return
    """
    client = get_client()
    clean = patent_number.replace(",", "").replace("US", "").strip()
    return client.patentsview_get(
        endpoint="patent/us_patent_citation",
        q={"patent_id": clean},
        f=["patent_id", "citation_patent_id", "citation_category", "citation_date"],
        o={"size": min(size, 1000)},
    )


def get_cited_by(patent_number: str, size: int = 100) -> dict:
    """Find patents that cite a given patent.

    Args:
        patent_number: The cited patent's number
        size: Number of results to return
    """
    client = get_client()
    clean = patent_number.replace(",", "").replace("US", "").strip()
    return client.patentsview_get(
        endpoint="patent/us_patent_citation",
        q={"citation_patent_id": clean},
        f=["patent_id", "citation_patent_id", "citation_category", "citation_date"],
        o={"size": min(size, 1000)},
    )


def get_inventor_details(inventor_id: str) -> dict:
    """Look up a disambiguated inventor by their PatentsView ID."""
    client = get_client()
    return client.patentsview_get(
        endpoint="inventor",
        q={"inventor_id": inventor_id},
        f=[
            "inventor_id",
            "inventor_name_first",
            "inventor_name_last",
            "inventor_city",
            "inventor_state",
            "inventor_country",
            "inventor_num_patents",
            "inventor_first_seen_date",
            "inventor_last_seen_date",
        ],
    )


def get_assignee_details(assignee_name: str) -> dict:
    """Look up an assignee (company) by name.

    Uses name variants for fuzzy matching since _contains is broken.
    NOTE: The /assignee/ entity endpoint uses unprefixed field names.
    """
    client = get_client()
    variants = _assignee_name_variants(assignee_name)
    if len(variants) == 1:
        q = {"assignee_organization": variants[0]}
    else:
        q = {"assignee_organization": variants}
    return client.patentsview_get(
        endpoint="assignee",
        q=q,
        f=[
            "assignee_id",
            "assignee_organization",
            "assignee_type",
            "assignee_lastknown_city",
            "assignee_lastknown_state",
            "assignee_lastknown_country",
            "assignee_num_patents",
        ],
        o={"size": 10},
    )


def search_publications(query: dict, fields: list = None, size: int = 25) -> dict:
    """Search pre-grant patent publications (published applications).

    Args:
        query: PatentsView query dict
        fields: Fields to return
        size: Results per page
    """
    client = get_client()
    default_fields = [
        "document_number",
        "publication_title",
        "publication_date",
        "publication_year",
    ]
    return client.patentsview_get(
        endpoint="publication",
        q=query,
        f=fields or default_fields,
        s=[{"publication_date": "desc"}],
        o={"size": min(size, 1000)},
    )


# ── CLI interface ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Search PatentsView API")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of formatted text")
    sub = parser.add_subparsers(dest="command")

    # assignee subcommand
    p_assignee = sub.add_parser("assignee", help="Search by assignee name")
    p_assignee.add_argument("name", help="Company/organization name")
    p_assignee.add_argument("--exact", action="store_true", help="Exact match only")
    p_assignee.add_argument("--year-from", type=int)
    p_assignee.add_argument("--year-to", type=int)
    p_assignee.add_argument("--size", type=int, default=25)

    # inventor subcommand
    p_inventor = sub.add_parser("inventor", help="Search by inventor name")
    p_inventor.add_argument("last_name", help="Last name")
    p_inventor.add_argument("--first", help="First name")
    p_inventor.add_argument("--exact", action="store_true")
    p_inventor.add_argument("--year-from", type=int)
    p_inventor.add_argument("--year-to", type=int)
    p_inventor.add_argument("--size", type=int, default=25)

    # keyword subcommand
    p_keyword = sub.add_parser("keyword", help="Search by keywords")
    p_keyword.add_argument("keywords", help="Space-separated keywords")
    p_keyword.add_argument("--in", dest="search_in", default="title",
                           choices=["title"],
                           help="Search field (only title works currently)")
    p_keyword.add_argument("--all", action="store_true", help="(Currently ignored)")
    p_keyword.add_argument("--year-from", type=int)
    p_keyword.add_argument("--year-to", type=int)
    p_keyword.add_argument("--size", type=int, default=25)

    # patent number subcommand
    p_number = sub.add_parser("patent", help="Look up by patent number")
    p_number.add_argument("number", help="Patent number")

    # citations subcommand
    p_cite = sub.add_parser("citations", help="Get citations for a patent")
    p_cite.add_argument("number", help="Patent number")
    p_cite.add_argument("--cited-by", action="store_true",
                        help="Find patents that cite this one")

    # CPC subcommand
    p_cpc = sub.add_parser("cpc", help="Search by CPC classification code")
    p_cpc.add_argument("code", help="CPC code (e.g. H04L, G06N)")
    p_cpc.add_argument("--year-from", type=int)
    p_cpc.add_argument("--year-to", type=int)
    p_cpc.add_argument("--size", type=int, default=25)

    # attorney subcommand
    p_atty = sub.add_parser("attorney", help="Search by attorney or law firm")
    p_atty.add_argument("last_name", help="Attorney last name")
    p_atty.add_argument("--first", help="Attorney first name")
    p_atty.add_argument("--org", help="Law firm / organization name")
    p_atty.add_argument("--size", type=int, default=25)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "assignee":
            result = search_by_assignee(args.name, fuzzy=not args.exact,
                                        year_from=args.year_from,
                                        year_to=args.year_to, size=args.size)
        elif args.command == "inventor":
            result = search_by_inventor(args.last_name, first_name=args.first,
                                        fuzzy=not args.exact,
                                        year_from=args.year_from,
                                        year_to=args.year_to, size=args.size)
        elif args.command == "keyword":
            result = search_by_keyword(args.keywords, search_in=args.search_in,
                                       match_all=args.all,
                                       year_from=args.year_from,
                                       year_to=args.year_to, size=args.size)
        elif args.command == "patent":
            result = search_by_patent_number(args.number)
        elif args.command == "citations":
            if args.cited_by:
                result = get_cited_by(args.number)
            else:
                result = get_patent_citations(args.number)
        elif args.command == "cpc":
            result = search_by_cpc(args.code, year_from=args.year_from,
                                   year_to=args.year_to, size=args.size)
        elif args.command == "attorney":
            result = search_by_attorney(args.last_name, first_name=args.first,
                                        organization=args.org, size=args.size)
        else:
            parser.print_help()
            return

        if args.json:
            print(json.dumps(result, indent=2))
        elif args.command == "patent":
            print(format_patent_detail(result, source="patentsview"))
        elif args.command == "citations":
            direction = "cited_by" if args.cited_by else "forward"
            print(format_citation_list(result, direction=direction))
        else:
            # Detect if result came from ODP fallback
            source = result.pop("_source", "patentsview") if isinstance(result, dict) else "patentsview"
            print(format_patent_list(result, source=source))

    except APIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
