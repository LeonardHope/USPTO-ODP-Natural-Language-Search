"""
USPTO Office Actions APIs - Search module.

Provides functions for querying office action data using the ODP DSAPI
endpoints. These APIs use Lucene/Solr query syntax and form-encoded POST
bodies.

APIs covered:
- Office Action Text Retrieval (v1): Full text of office actions
- Office Action Rejection (v2): Structured rejection data (101, 102, 103, 112)
- Office Action Citations (v2): Citation references from office actions
- Enriched Citation (v3): NLP-parsed citation references from office actions

Base URL: https://api.uspto.gov/api/v1/patent/oa/
Auth: USPTO_ODP_API_KEY env var, sent as X-API-KEY header
Rate limit: See https://data.uspto.gov/apis/api-rate-limits

Data coverage:
- Rejections: June 1, 2018 to ~180 days before current date
- Enriched Citations: October 1, 2017 to April 2019 (frozen dataset)
- Office Action Text: Varies
- Office Action Citations: Varies

Lucene query syntax quick reference:
  field:value           Exact match
  field:"phrase"        Phrase match
  field:[a TO b]        Range query (inclusive)
  field:{a TO b}        Range query (exclusive)
  field:val*            Wildcard
  field:val?            Single character wildcard
  a AND b              Boolean AND
  a OR b               Boolean OR
  NOT a                Boolean NOT
  (a OR b) AND c       Grouping
"""

import json
import sys
import argparse

from uspto_client import get_client, APIError, resolve_patent_to_app_number
from format_results import format_rejection_results


# ── Dataset constants ───────────────────────────────────────────────────
# Migrated from developer.uspto.gov/ds-api/ to api.uspto.gov/api/v1/patent/oa/

DATASETS = {
    "rejections": {"path": "/api/v1/patent/oa/oa_rejections/v2"},
    "actions": {"path": "/api/v1/patent/oa/oa_actions/v1"},
    "citations": {"path": "/api/v1/patent/oa/oa_citations/v2"},
    "enriched_citations": {"path": "/api/v1/patent/oa/enriched_cited_reference_metadata/v3"},
}


def _dsapi_post(dataset_key: str, criteria: str, start: int = 0, rows: int = 100) -> dict:
    """Query a DSAPI endpoint using Lucene syntax.

    Args:
        dataset_key: One of 'rejections', 'actions', 'citations', 'enriched_citations'
        criteria: Lucene query string
        start: Starting record offset
        rows: Number of records to return

    Returns:
        API response dict
    """
    client = get_client()
    ds = DATASETS[dataset_key]
    form_data = {
        "criteria": criteria,
        "start": str(start),
        "rows": str(rows),
    }
    return client.odp_post(f"{ds['path']}/records", data=form_data)


def _dsapi_get_fields(dataset_key: str) -> dict:
    """Get available searchable fields for a DSAPI dataset."""
    client = get_client()
    ds = DATASETS[dataset_key]
    return client.odp_get(f"{ds['path']}/fields")


# ── Office Action Rejections ────────────────────────────────────────────

def search_rejections(application_number: str = None,
                      patent_number: str = None,
                      rejection_type: str = None,
                      art_unit: str = None,
                      criteria: str = None,
                      start: int = 0, rows: int = 100) -> dict:
    """Search office action rejections.

    Rejection types include: 101 (subject matter eligibility),
    102 (novelty), 103 (obviousness), 112 (written description/enablement),
    and double patenting.

    Note: The oa_rejections API does not have examiner name or patent number
    fields. Search by application number or art unit instead.

    Args:
        application_number: Application serial number
        patent_number: Patent number — resolved to app number via ODP search
        rejection_type: Filter by rejection basis: '101', '102', '103', '112', 'DP'
        art_unit: Art unit number
        criteria: Raw Lucene query (overrides other params if provided)
        start: Pagination offset
        rows: Number of records (max 100)

    Returns:
        API response with rejection records
    """
    if criteria is None:
        parts = []
        if application_number:
            clean = application_number.replace("/", "").replace(",", "").strip()
            parts.append(f"patentApplicationNumber:{clean}")
        if patent_number:
            app_num = resolve_patent_to_app_number(patent_number)
            if app_num:
                parts.append(f"patentApplicationNumber:{app_num}")
            else:
                raise APIError(f"Could not resolve patent {patent_number} to an application number.")
        if rejection_type:
            type_map = {
                "101": "hasRej101:1 OR aliceIndicator:true OR mayoIndicator:true OR rejection_101:1",
                "102": "hasRej102:1",
                "103": "hasRej103:1",
                "112": "hasRej112:1",
                "DP": "hasRejDP:1",
            }
            if rejection_type in type_map:
                parts.append(f"({type_map[rejection_type]})")
        if art_unit:
            parts.append(f"groupArtUnitNumber:{art_unit}")

        if not parts:
            raise APIError("At least one search parameter is required for rejection search.")
        criteria = " AND ".join(parts)

    return _dsapi_post("rejections", criteria, start=start, rows=rows)


def get_rejection_fields() -> dict:
    """Get the list of searchable fields for the rejections API."""
    return _dsapi_get_fields("rejections")


# ── Office Action Text ──────────────────────────────────────────────────

def search_office_action_text(application_number: str = None,
                              patent_number: str = None,
                              criteria: str = None,
                              start: int = 0, rows: int = 100) -> dict:
    """Search office action full text.

    Returns the complete text of office actions for matching applications.

    Args:
        application_number: Application serial number
        patent_number: Patent number
        criteria: Raw Lucene query (overrides other params)
        start: Pagination offset
        rows: Number of records
    """
    if criteria is None:
        parts = []
        if application_number:
            clean = application_number.replace("/", "").replace(",", "").strip()
            parts.append(f"patentApplicationNumber:{clean}")
        if patent_number:
            clean = patent_number.replace(",", "").replace("US", "").strip()
            parts.append(f"patentNumber:{clean}")
        if not parts:
            raise APIError("At least one search parameter is required.")
        criteria = " AND ".join(parts)

    return _dsapi_post("actions", criteria, start=start, rows=rows)


def get_office_action_fields() -> dict:
    """Get searchable fields for the office action text API."""
    return _dsapi_get_fields("actions")


# ── Office Action Citations ────────────────────────────────────────────

def search_office_action_citations(application_number: str = None,
                                   patent_number: str = None,
                                   criteria: str = None,
                                   start: int = 0, rows: int = 100) -> dict:
    """Search office action citation records.

    Args:
        application_number: Application serial number
        patent_number: Patent number
        criteria: Raw Lucene query (overrides other params)
        start: Pagination offset
        rows: Number of records
    """
    if criteria is None:
        parts = []
        if application_number:
            clean = application_number.replace("/", "").replace(",", "").strip()
            parts.append(f"patentApplicationNumber:{clean}")
        if patent_number:
            clean = patent_number.replace(",", "").replace("US", "").strip()
            parts.append(f"patentNumber:{clean}")
        if not parts:
            raise APIError("At least one search parameter is required.")
        criteria = " AND ".join(parts)

    return _dsapi_post("citations", criteria, start=start, rows=rows)


def get_office_action_citation_fields() -> dict:
    """Get searchable fields for the office action citations API."""
    return _dsapi_get_fields("citations")


# ── Enriched Citations ──────────────────────────────────────────────────

def search_enriched_citations(application_number: str = None,
                              patent_number: str = None,
                              cited_reference: str = None,
                              criteria: str = None,
                              start: int = 0, rows: int = 100) -> dict:
    """Search enriched citation data from office actions.

    Returns NLP-parsed citation references showing which prior art
    was cited against which claims, with context.

    Note: This dataset covers October 1, 2017 to April 2019 only (frozen).

    Args:
        application_number: Application serial number
        patent_number: Patent number
        cited_reference: Cited reference patent number or publication
        criteria: Raw Lucene query (overrides other params)
        start: Pagination offset
        rows: Number of records

    Returns:
        API response with enriched citation records
    """
    if criteria is None:
        parts = []
        if application_number:
            clean = application_number.replace("/", "").replace(",", "").strip()
            parts.append(f"patentApplicationNumber:{clean}")
        if patent_number:
            app_num = resolve_patent_to_app_number(patent_number)
            if app_num:
                parts.append(f"patentApplicationNumber:{app_num}")
            else:
                raise APIError(f"Could not resolve patent {patent_number} to an application number.")
        if cited_reference:
            parts.append(f"citedDocumentIdentifier:{cited_reference}")
        if not parts:
            raise APIError("At least one search parameter is required.")
        criteria = " AND ".join(parts)

    return _dsapi_post("enriched_citations", criteria, start=start, rows=rows)


def get_enriched_citation_fields() -> dict:
    """Get searchable fields for the enriched citations API."""
    return _dsapi_get_fields("enriched_citations")


# ── CLI interface ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Search USPTO Office Action APIs")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of formatted text")
    sub = parser.add_subparsers(dest="command")

    # rejections
    p_rej = sub.add_parser("rejections", help="Search office action rejections")
    p_rej.add_argument("--app-number", help="Application number")
    p_rej.add_argument("--patent-number", help="Patent number (resolved to app number)")
    p_rej.add_argument("--type", choices=["101", "102", "103", "112", "DP"],
                       help="Rejection type")
    p_rej.add_argument("--art-unit", help="Art unit")
    p_rej.add_argument("--criteria", help="Raw Lucene query")
    p_rej.add_argument("--size", type=int, default=100)

    # office action text
    p_text = sub.add_parser("text", help="Get office action full text")
    p_text.add_argument("--app-number", help="Application number")
    p_text.add_argument("--patent-number", help="Patent number")
    p_text.add_argument("--criteria", help="Raw Lucene query")
    p_text.add_argument("--size", type=int, default=100)

    # office action citations
    p_oacite = sub.add_parser("oa-citations", help="Search office action citations")
    p_oacite.add_argument("--app-number", help="Application number")
    p_oacite.add_argument("--patent-number", help="Patent number")
    p_oacite.add_argument("--criteria", help="Raw Lucene query")
    p_oacite.add_argument("--size", type=int, default=100)

    # enriched citations
    p_cite = sub.add_parser("citations", help="Search enriched citations")
    p_cite.add_argument("--app-number", help="Application number")
    p_cite.add_argument("--patent-number", help="Patent number")
    p_cite.add_argument("--cited-ref", help="Cited reference number")
    p_cite.add_argument("--criteria", help="Raw Lucene query")
    p_cite.add_argument("--size", type=int, default=100)

    # field listing
    p_fields = sub.add_parser("fields", help="List searchable fields")
    p_fields.add_argument("api", choices=["rejections", "text", "oa-citations", "citations"],
                          help="Which API to list fields for")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "rejections":
            result = search_rejections(
                application_number=args.app_number,
                patent_number=args.patent_number,
                rejection_type=args.type,
                art_unit=args.art_unit,
                criteria=args.criteria,
                rows=args.size,
            )
        elif args.command == "text":
            result = search_office_action_text(
                application_number=args.app_number,
                patent_number=args.patent_number,
                criteria=args.criteria,
                rows=args.size,
            )
        elif args.command == "oa-citations":
            result = search_office_action_citations(
                application_number=args.app_number,
                patent_number=args.patent_number,
                criteria=args.criteria,
                rows=args.size,
            )
        elif args.command == "citations":
            result = search_enriched_citations(
                application_number=args.app_number,
                patent_number=args.patent_number,
                cited_reference=args.cited_ref,
                criteria=args.criteria,
                rows=args.size,
            )
        elif args.command == "fields":
            api_map = {
                "rejections": get_rejection_fields,
                "text": get_office_action_fields,
                "oa-citations": get_office_action_citation_fields,
                "citations": get_enriched_citation_fields,
            }
            result = api_map[args.api]()
        else:
            parser.print_help()
            return

        if args.json:
            print(json.dumps(result, indent=2))
        elif args.command == "rejections":
            print(format_rejection_results(result))
        else:
            print(json.dumps(result, indent=2))

    except APIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
