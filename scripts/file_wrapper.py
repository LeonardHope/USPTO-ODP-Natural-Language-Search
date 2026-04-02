"""
USPTO Open Data Portal - Patent File Wrapper Sub-Resources.

Provides functions for retrieving detailed data about specific patent
applications: metadata, documents, continuity, assignments, attorney info,
transactions, foreign priority, patent term adjustment, and associated docs.

These complement the search functions in patent_search.py — use patent_search
to find applications, then these functions to drill into the details.

API Base: https://api.uspto.gov
Auth: USPTO_ODP_API_KEY env var, sent as X-API-KEY header
Endpoints: GET /api/v1/patent/applications/{applicationNumberText}/...
"""

import json
import sys
import argparse

from uspto_client import get_client, APIError, clean_app_number, clean_patent_number


# ── Application Lookup ─────────────────────────────────────────────────

def get_application(application_number: str) -> dict:
    """Get full data for a specific patent application.

    Returns all available data including metadata, assignments, attorneys,
    continuity, foreign priority, transactions, and documents.

    Args:
        application_number: Application serial number (e.g. '16123456' or '16/123,456')

    Returns:
        Complete application data
    """
    client = get_client()
    clean = clean_app_number(application_number)
    return client.odp_get(f"/api/v1/patent/applications/{clean}")


def get_application_by_patent_number(patent_number: str) -> dict:
    """Look up an application by its granted patent number.

    Searches ODP for the patent number and returns the full application data.

    Args:
        patent_number: Granted patent number (e.g. '11887351')

    Returns:
        Application data dict, or empty dict if not found
    """
    client = get_client()
    clean = clean_patent_number(patent_number)
    try:
        result = client.odp_get(
            "/api/v1/patent/applications/search",
            params={"q": clean, "limit": 5}
        )
        for app in result.get("patentFileWrapperDataBag", []):
            meta = app.get("applicationMetaData", {})
            if meta.get("patentNumber") == clean:
                return app
    except APIError:
        pass
    return {}


# ── Sub-Resources ─────────────────────────────────────────────────────

def get_meta_data(application_number: str) -> dict:
    """Get application metadata (status, dates, parties, classification).

    Args:
        application_number: Application serial number
    """
    client = get_client()
    clean = clean_app_number(application_number)
    return client.odp_get(f"/api/v1/patent/applications/{clean}/meta-data")


def get_application_documents(application_number: str, offset: int = 0,
                              limit: int = 50) -> dict:
    """Get prosecution history documents for an application.

    Returns office actions, applicant responses, IDS filings, petitions, etc.

    Args:
        application_number: Application serial number
        offset: Pagination offset
        limit: Documents per page
    """
    client = get_client()
    clean = clean_app_number(application_number)
    params = {"offset": offset, "limit": limit}
    return client.odp_get(f"/api/v1/patent/applications/{clean}/documents", params=params)


def get_continuity(application_number: str) -> dict:
    """Get continuity data (parent/child application relationships).

    Shows continuation, continuation-in-part, divisional, and
    provisional relationships.

    Args:
        application_number: Application serial number
    """
    client = get_client()
    clean = clean_app_number(application_number)
    return client.odp_get(f"/api/v1/patent/applications/{clean}/continuity")


def get_patent_term_adjustment(application_number: str) -> dict:
    """Get patent term adjustment (PTA) data for an application.

    Args:
        application_number: Application serial number
    """
    client = get_client()
    clean = clean_app_number(application_number)
    try:
        return client.odp_get(f"/api/v1/patent/applications/{clean}/adjustment")
    except APIError as e:
        if e.status_code == 403:
            return {
                "error": "Patent term adjustment data is not currently available via the API.",
                "suggestion": "Check the USPTO Patent Center UI at https://patentcenter.uspto.gov",
                "applicationNumber": clean,
            }
        raise


def get_assignment(application_number: str) -> dict:
    """Get assignment (ownership) records for an application.

    Args:
        application_number: Application serial number
    """
    client = get_client()
    clean = clean_app_number(application_number)
    return client.odp_get(f"/api/v1/patent/applications/{clean}/assignment")


def get_attorney(application_number: str) -> dict:
    """Get attorney/agent of record for an application.

    Args:
        application_number: Application serial number
    """
    client = get_client()
    clean = clean_app_number(application_number)
    return client.odp_get(f"/api/v1/patent/applications/{clean}/attorney")


def get_transactions(application_number: str) -> dict:
    """Get transaction (event) history for an application.

    Args:
        application_number: Application serial number
    """
    client = get_client()
    clean = clean_app_number(application_number)
    return client.odp_get(f"/api/v1/patent/applications/{clean}/transactions")


def get_foreign_priority(application_number: str) -> dict:
    """Get foreign priority claims for an application.

    Args:
        application_number: Application serial number
    """
    client = get_client()
    clean = clean_app_number(application_number)
    return client.odp_get(f"/api/v1/patent/applications/{clean}/foreign-priority")


def get_associated_documents(application_number: str) -> dict:
    """Get associated document metadata (grant/publication XML info).

    Args:
        application_number: Application serial number
    """
    client = get_client()
    clean = clean_app_number(application_number)
    return client.odp_get(f"/api/v1/patent/applications/{clean}/associated-documents")


def get_status_codes(query: str = None) -> dict:
    """Search patent application status codes.

    Args:
        query: Optional search text for status codes
    """
    client = get_client()
    params = {}
    if query:
        params["q"] = query
    return client.odp_get("/api/v1/patent/status-codes", params=params)


# ── CLI interface ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="USPTO Patent File Wrapper sub-resource lookups"
    )
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("get", help="Get full application data").add_argument(
        "app_number", help="Application number")
    sub.add_parser("meta", help="Get application metadata").add_argument(
        "app_number", help="Application number")
    p_docs = sub.add_parser("documents", help="Get file wrapper documents")
    p_docs.add_argument("app_number", help="Application number")
    p_docs.add_argument("--limit", type=int, default=50)
    sub.add_parser("continuity", help="Get continuity data").add_argument(
        "app_number", help="Application number")
    sub.add_parser("pta", help="Get patent term adjustment").add_argument(
        "app_number", help="Application number")
    sub.add_parser("assignment", help="Get assignment records").add_argument(
        "app_number", help="Application number")
    sub.add_parser("attorney", help="Get attorney of record").add_argument(
        "app_number", help="Application number")
    sub.add_parser("transactions", help="Get transaction history").add_argument(
        "app_number", help="Application number")
    sub.add_parser("foreign-priority", help="Get foreign priority claims").add_argument(
        "app_number", help="Application number")
    sub.add_parser("associated-docs", help="Get associated document metadata").add_argument(
        "app_number", help="Application number")
    p_status = sub.add_parser("status-codes", help="Search status codes")
    p_status.add_argument("--query", "-q", help="Search text")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    dispatch = {
        "get": lambda: get_application(args.app_number),
        "meta": lambda: get_meta_data(args.app_number),
        "documents": lambda: get_application_documents(args.app_number, limit=args.limit),
        "continuity": lambda: get_continuity(args.app_number),
        "pta": lambda: get_patent_term_adjustment(args.app_number),
        "assignment": lambda: get_assignment(args.app_number),
        "attorney": lambda: get_attorney(args.app_number),
        "transactions": lambda: get_transactions(args.app_number),
        "foreign-priority": lambda: get_foreign_priority(args.app_number),
        "associated-docs": lambda: get_associated_documents(args.app_number),
        "status-codes": lambda: get_status_codes(query=args.query),
    }

    try:
        result = dispatch[args.command]()
        print(json.dumps(result, indent=2))
    except APIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
