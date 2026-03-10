"""
USPTO Open Data Portal (ODP) - Patent File Wrapper and PTAB search module.

Provides functions for searching patent applications, retrieving prosecution
history documents, and querying PTAB proceedings via the ODP APIs.

API Base: https://api.uspto.gov (migrated from data.uspto.gov in early 2026)
Auth: USPTO_ODP_API_KEY env var, sent as X-Api-Key header
Rate limit: 60 requests/minute (4/min for PDF/ZIP downloads)

The ODP File Wrapper API provides access to:
- Patent application search and metadata
- Prosecution history documents (office actions, responses, IDS)
- Continuity data (parent/child application relationships)
- Patent term adjustment/extension data

The PTAB API provides access to:
- Trial proceedings (IPR, PGR, CBM)
- Appeal proceedings
- Interference proceedings
- Decision documents

Search endpoints:
- Application search: /api/v1/patent/applications/search (q= free-text string)
- Direct app lookup: /api/v1/patent/applications/{appNumber}
- PTAB proceedings: /api/v1/patent/trials/proceedings/search
"""

import json
import sys
import argparse
from typing import Optional

from uspto_client import get_client, APIError
from format_results import format_patent_list, format_ptab_results


# ── File Wrapper Search ─────────────────────────────────────────────────

def search_applications(query: str = None, application_number: str = None,
                        patent_number: str = None, inventor_name: str = None,
                        assignee_name: str = None, title: str = None,
                        filing_date_from: str = None, filing_date_to: str = None,
                        status: str = None, start: int = 0,
                        rows: int = 25) -> dict:
    """Search patent applications on the Open Data Portal.

    The search endpoint at api.uspto.gov uses a free-text `q` parameter.
    All search terms are combined into a single query string.

    Args:
        query: Free-text search across all fields
        application_number: Application serial number (e.g. '16123456')
        patent_number: Granted patent number
        inventor_name: Inventor name (partial match supported)
        assignee_name: Assignee/applicant organization name
        title: Words in the invention title
        filing_date_from: Currently unsupported on new endpoint
        filing_date_to: Currently unsupported on new endpoint
        status: Currently unsupported on new endpoint
        start: Pagination offset
        rows: Results per page

    Returns:
        API response with matching applications
    """
    client = get_client()
    params = {"start": start, "rows": rows}

    # Build free-text search query from available parameters
    search_terms = []
    if query:
        search_terms.append(query)
    if application_number:
        clean = application_number.replace("/", "").replace(",", "").strip()
        search_terms.append(clean)
    if patent_number:
        clean = patent_number.replace(",", "").replace("US", "").strip()
        search_terms.append(clean)
    if inventor_name:
        search_terms.append(inventor_name)
    if assignee_name:
        search_terms.append(assignee_name)
    if title:
        search_terms.append(title)

    if search_terms:
        params["q"] = " ".join(search_terms)

    return client.odp_get("/api/v1/patent/applications/search", params=params)


def get_application(application_number: str) -> dict:
    """Get full metadata for a specific patent application.

    Args:
        application_number: Application serial number (e.g. '16123456' or '16/123,456')

    Returns:
        Application metadata including status, dates, parties, classification
    """
    client = get_client()
    clean = application_number.replace("/", "").replace(",", "").strip()
    return client.odp_get(f"/api/v1/patent/applications/{clean}")


def get_application_by_patent_number(patent_number: str) -> dict:
    """Search for an application by its granted patent number.

    Uses the ODP free-text search to find the application, then
    returns the full application data.

    Args:
        patent_number: Granted patent number (e.g. '11887351')

    Returns:
        Application data dict, or empty dict if not found
    """
    clean = patent_number.replace(",", "").replace("US", "").strip()
    result = search_applications(query=clean, rows=5)
    # Filter results to find the one matching the patent number
    for app in result.get("patentFileWrapperDataBag", []):
        meta = app.get("applicationMetaData", {})
        if meta.get("patentNumber") == clean:
            return app
    return {}


def get_application_documents(application_number: str, start: int = 0,
                              rows: int = 50) -> dict:
    """Get prosecution history documents for an application.

    Returns a list of documents in the file wrapper: office actions,
    applicant responses, IDS filings, petitions, etc.

    Args:
        application_number: Application serial number
        start: Pagination offset
        rows: Documents per page
    """
    client = get_client()
    clean = application_number.replace("/", "").replace(",", "").strip()
    params = {"start": start, "rows": rows}
    return client.odp_get(f"/api/v1/patent/applications/{clean}/documents", params=params)


def get_document(application_number: str, document_id: str) -> dict:
    """Get metadata for a specific document in the file wrapper.

    Args:
        application_number: Application serial number
        document_id: Document identifier from the documents list
    """
    client = get_client()
    clean = application_number.replace("/", "").replace(",", "").strip()
    return client.odp_get(
        f"/api/v1/patent/applications/{clean}/documents/{document_id}"
    )


def get_continuity(application_number: str) -> dict:
    """Get continuity data (parent/child application relationships).

    Shows continuation, continuation-in-part, divisional, and
    provisional relationships.

    Args:
        application_number: Application serial number
    """
    client = get_client()
    clean = application_number.replace("/", "").replace(",", "").strip()
    return client.odp_get(f"/api/v1/patent/applications/{clean}/continuity")


def get_patent_term_adjustment(application_number: str) -> dict:
    """Get patent term adjustment (PTA) data for an application.

    Note: The PTA endpoint may not be available via the API (returns 403).
    This is a known limitation of the ODP API.

    Args:
        application_number: Application serial number
    """
    client = get_client()
    clean = application_number.replace("/", "").replace(",", "").strip()
    try:
        return client.odp_get(f"/api/v1/patent/applications/{clean}/patent-term-adjustment")
    except APIError as e:
        if e.status_code == 403:
            return {
                "error": "Patent term adjustment data is not currently available via the API.",
                "suggestion": "Check the USPTO Patent Center UI at https://patentcenter.uspto.gov",
                "applicationNumber": clean,
            }
        raise


# ── PTAB Search ─────────────────────────────────────────────────────────

def search_ptab_proceedings(query: str = None, patent_number: str = None,
                            party_name: str = None, trial_number: str = None,
                            proceeding_type: str = None,
                            start: int = 0, rows: int = 25) -> dict:
    """Search PTAB (Patent Trial and Appeal Board) proceedings.

    Covers IPR (Inter Partes Review), PGR (Post-Grant Review),
    CBM (Covered Business Method), and appeal proceedings.

    The ODP PTAB API uses a free-text `q` parameter with `limit`/`offset`
    pagination. Named filter params like `patentNumber` are silently ignored.

    Args:
        query: Free-text search across proceeding data
        patent_number: Patent number involved in the proceeding
        party_name: Name of a party (petitioner or patent owner)
        trial_number: PTAB trial number (e.g. 'IPR2020-00001')
        proceeding_type: Type filter: 'IPR', 'PGR', 'CBM', 'DER'
        start: Pagination offset
        rows: Results per page

    Returns:
        API response with matching PTAB proceedings
    """
    client = get_client()
    params = {"offset": start, "limit": rows}

    # Build the q parameter — the API uses free-text search
    q_parts = []
    if query:
        q_parts.append(query)
    if patent_number:
        clean = patent_number.replace(",", "").replace("US", "").strip()
        q_parts.append(clean)
    if party_name:
        q_parts.append(party_name)
    if trial_number:
        q_parts.append(trial_number)
    if proceeding_type:
        q_parts.append(proceeding_type)

    if q_parts:
        params["q"] = " ".join(q_parts)

    try:
        return client.odp_get("/api/v1/patent/trials/proceedings/search", params=params)
    except APIError as e:
        if e.status_code == 404:
            # No matching proceedings found — return empty result
            return {"count": 0, "patentTrialProceedingDataBag": []}
        raise


def get_ptab_proceeding(trial_number: str) -> dict:
    """Get full details for a specific PTAB proceeding.

    Args:
        trial_number: PTAB trial number (e.g. 'IPR2020-00001')
    """
    client = get_client()
    return client.odp_get(f"/api/v1/patent/trials/proceedings/{trial_number}")


def search_ptab_decisions(query: str = None, patent_number: str = None,
                          start: int = 0, rows: int = 25) -> dict:
    """Search PTAB decision documents by text content.

    Args:
        query: Full-text search within decision documents
        patent_number: Patent number to find decisions for
        start: Pagination offset
        rows: Results per page
    """
    client = get_client()
    params = {"offset": start, "limit": rows}

    q_parts = []
    if query:
        q_parts.append(query)
    if patent_number:
        clean = patent_number.replace(",", "").replace("US", "").strip()
        q_parts.append(clean)

    if q_parts:
        params["q"] = " ".join(q_parts)

    try:
        return client.odp_get("/api/v1/patent/trials/decisions/search", params=params)
    except APIError as e:
        if e.status_code == 404:
            return {"count": 0, "patentTrialDecisionDataBag": []}
        raise


# ── Bulk Data ───────────────────────────────────────────────────────────

def search_bulk_data(query: str = None, product_type: str = None,
                     start: int = 0, rows: int = 25) -> dict:
    """Search available USPTO bulk data products.

    Args:
        query: Search text for bulk data products
        product_type: Filter by product type
        start: Pagination offset
        rows: Results per page
    """
    client = get_client()
    params = {"start": start, "rows": rows}
    if query:
        params["searchText"] = query
    if product_type:
        params["productType"] = product_type
    return client.odp_get("/api/v1/bulk-data/products", params=params)


# ── CLI interface ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Search USPTO Open Data Portal")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of formatted text")
    sub = parser.add_subparsers(dest="command")

    # application search
    p_app = sub.add_parser("search", help="Search patent applications")
    p_app.add_argument("--query", "-q", help="Free-text search")
    p_app.add_argument("--app-number", help="Application number")
    p_app.add_argument("--patent-number", help="Patent number")
    p_app.add_argument("--inventor", help="Inventor name")
    p_app.add_argument("--assignee", help="Assignee name")
    p_app.add_argument("--title", help="Title keywords")
    p_app.add_argument("--size", type=int, default=25)

    # get application details
    p_get = sub.add_parser("get", help="Get application details")
    p_get.add_argument("app_number", help="Application number")

    # get documents
    p_docs = sub.add_parser("documents", help="Get file wrapper documents")
    p_docs.add_argument("app_number", help="Application number")
    p_docs.add_argument("--size", type=int, default=50)

    # continuity
    p_cont = sub.add_parser("continuity", help="Get continuity data")
    p_cont.add_argument("app_number", help="Application number")

    # PTAB search
    p_ptab = sub.add_parser("ptab", help="Search PTAB proceedings")
    p_ptab.add_argument("--query", "-q", help="Free-text search")
    p_ptab.add_argument("--patent-number", help="Patent number")
    p_ptab.add_argument("--party", help="Party name")
    p_ptab.add_argument("--trial", help="Trial number")
    p_ptab.add_argument("--type", choices=["IPR", "PGR", "CBM", "DER"])
    p_ptab.add_argument("--size", type=int, default=25)

    # PTAB decisions
    p_dec = sub.add_parser("decisions", help="Search PTAB decisions")
    p_dec.add_argument("--query", "-q", help="Search in decision text")
    p_dec.add_argument("--patent-number", help="Patent number")
    p_dec.add_argument("--size", type=int, default=25)

    # patent term adjustment
    p_pta = sub.add_parser("pta", help="Get patent term adjustment data")
    p_pta.add_argument("app_number", help="Application number")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "search":
            result = search_applications(
                query=args.query, application_number=args.app_number,
                patent_number=args.patent_number, inventor_name=args.inventor,
                assignee_name=args.assignee, title=args.title, rows=args.size
            )
        elif args.command == "get":
            result = get_application(args.app_number)
        elif args.command == "documents":
            result = get_application_documents(args.app_number, rows=args.size)
        elif args.command == "continuity":
            result = get_continuity(args.app_number)
        elif args.command == "ptab":
            result = search_ptab_proceedings(
                query=args.query, patent_number=args.patent_number,
                party_name=args.party, trial_number=args.trial,
                proceeding_type=args.type, rows=args.size
            )
        elif args.command == "decisions":
            result = search_ptab_decisions(
                query=args.query, patent_number=args.patent_number, rows=args.size
            )
        elif args.command == "pta":
            result = get_patent_term_adjustment(args.app_number)
        else:
            parser.print_help()
            return

        if args.json:
            print(json.dumps(result, indent=2))
        elif args.command in ("ptab", "decisions"):
            print(format_ptab_results(result))
        elif args.command == "search":
            print(format_patent_list(result, source="odp"))
        else:
            print(json.dumps(result, indent=2))

    except APIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
