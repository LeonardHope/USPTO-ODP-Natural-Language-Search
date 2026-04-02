"""
USPTO Petition Decisions API - Search module.

Provides functions for searching and retrieving petition decisions from the
USPTO Open Data Portal. Petitions are requests to the USPTO for actions
outside normal prosecution (e.g., revival of abandoned applications,
extensions of time, requests for prioritized examination).

API Base: https://api.uspto.gov
Auth: USPTO_ODP_API_KEY env var, sent as X-API-KEY header
Rate limit: 60 requests/minute

Endpoints:
- POST /api/v1/petition/decisions/search — Search petition decisions (JSON body)
- GET  /api/v1/petition/decisions/search — Search via query parameters
- POST /api/v1/petition/decisions/search/download — Download results (JSON/CSV)
- GET  /api/v1/petition/decisions/search/download — Download via query params
- GET  /api/v1/petition/decisions/{petitionDecisionRecordIdentifier} — Single record

Response format:
    {"count": N, "petitionDecisionDataBag": [...]}
"""

import json
import logging
import sys
import argparse

from uspto_client import get_client, APIError, clean_patent_number, clean_app_number

logger = logging.getLogger("petition_search")


# ── Petition Decision Search ──────────────────────────────────────────────

def search_petition_decisions(query: str = None,
                              application_number: str = None,
                              patent_number: str = None,
                              offset: int = 0,
                              limit: int = 25) -> dict:
    """Search petition decisions on the Open Data Portal.

    Uses the free-text `q` parameter to search across all petition decision
    fields. Multiple search terms (query, application number, patent number)
    are combined into a single query string.

    Args:
        query: Free-text search across all fields
        application_number: Application serial number (e.g. '16123456')
        patent_number: Granted patent number (e.g. '10000000')
        offset: Pagination offset
        limit: Results per page (max 25)

    Returns:
        API response with matching petition decisions:
        {"count": N, "petitionDecisionDataBag": [...]}
    """
    client = get_client()
    params = {"offset": offset, "limit": limit}

    # Build free-text search query from available parameters
    search_terms = []
    if query:
        search_terms.append(query)
    if application_number:
        search_terms.append(clean_app_number(application_number))
    if patent_number:
        search_terms.append(clean_patent_number(patent_number))

    if search_terms:
        params["q"] = " ".join(search_terms)

    try:
        return client.odp_get("/api/v1/petition/decisions/search", params=params)
    except APIError as e:
        if e.status_code == 404:
            return {"count": 0, "petitionDecisionDataBag": []}
        raise


def get_petition_decision(record_id: str) -> dict:
    """Get a single petition decision by its record identifier.

    Args:
        record_id: Petition decision record identifier

    Returns:
        Petition decision record with full details
    """
    client = get_client()
    return client.odp_get(f"/api/v1/petition/decisions/{record_id}")


def download_petition_decisions(query: str = None,
                                format: str = "json") -> dict:
    """Download petition decision search results.

    Triggers a download of matching petition decisions in the specified
    format. Useful for bulk export of results.

    Args:
        query: Free-text search query
        format: Output format — 'json' or 'csv'

    Returns:
        Downloaded data in the requested format
    """
    client = get_client()
    params = {}
    if query:
        params["q"] = query
    if format:
        params["format"] = format

    return client.odp_get("/api/v1/petition/decisions/search/download", params=params)


# ── CLI interface ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Search USPTO Petition Decisions")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of formatted text")
    sub = parser.add_subparsers(dest="command")

    # search
    p_search = sub.add_parser("search", help="Search petition decisions")
    p_search.add_argument("--query", "-q", help="Free-text search")
    p_search.add_argument("--app-number", help="Application number")
    p_search.add_argument("--patent-number", help="Patent number")
    p_search.add_argument("--limit", type=int, default=25,
                          help="Results per page")

    # get single record
    p_get = sub.add_parser("get", help="Get a single petition decision")
    p_get.add_argument("record_id", help="Petition decision record identifier")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "search":
            result = search_petition_decisions(
                query=args.query,
                application_number=args.app_number,
                patent_number=args.patent_number,
                limit=args.limit,
            )
        elif args.command == "get":
            result = get_petition_decision(args.record_id)
        else:
            parser.print_help()
            return

        if args.json:
            print(json.dumps(result, indent=2))
        elif args.command == "search":
            from format_results import format_petition_results
            print(format_petition_results(result))
        else:
            print(json.dumps(result, indent=2))

    except APIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
