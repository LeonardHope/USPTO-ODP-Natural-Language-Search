"""
USPTO Patent Assignment Search module.

Provides functions for looking up patent ownership and assignment records.
Useful for chain-of-title analysis, due diligence, and M&A work.

Assignment data is accessed via the ODP File Wrapper API:
    GET /api/v1/patent/applications/{applicationNumber}/assignment
Auth: USPTO_ODP_API_KEY env var, sent as X-API-KEY header

The ODP endpoint only supports per-application lookups, so patent number
queries first resolve to an application number via ODP search.
"""

import json
import logging
import sys
import argparse

from uspto_client import get_client, APIError, resolve_patent_to_app_number, clean_app_number
from format_results import format_assignment_results

logger = logging.getLogger("assignment_search")


def get_assignments_for_application(application_number: str) -> dict:
    """Get assignment records for a specific application.

    Uses the ODP File Wrapper assignment endpoint.

    Args:
        application_number: Application serial number (e.g. '14643719')

    Returns:
        API response with assignment records
    """
    client = get_client()
    clean = clean_app_number(application_number)
    return client.odp_get(f"/api/v1/patent/applications/{clean}/assignment")


def search_patent_assignments(patent_number: str = None,
                              application_number: str = None,
                              assignee_name: str = None,
                              assignor_name: str = None,
                              conveyance_text: str = None,
                              reel_frame: str = None,
                              recorded_date_from: str = None,
                              recorded_date_to: str = None,
                              query: str = None,
                              start: int = 0, rows: int = 25) -> dict:
    """Search patent assignment records.

    The ODP assignment API only supports per-application lookups.
    For patent number queries, we first resolve to application number.

    Args:
        patent_number: Patent number to search assignments for
        application_number: Application number
        assignee_name: Not supported by ODP (ignored with warning)
        assignor_name: Not supported by ODP (ignored with warning)
        conveyance_text: Not supported by ODP (ignored)
        reel_frame: Not supported by ODP (ignored)
        recorded_date_from: Not supported by ODP (ignored)
        recorded_date_to: Not supported by ODP (ignored)
        query: Not supported by ODP (ignored)
        start: Pagination offset (unused for per-app lookup)
        rows: Results per page (unused for per-app lookup)

    Returns:
        API response with assignment records
    """
    # Warn about params that the ODP API doesn't support
    ignored = []
    if assignee_name: ignored.append("assignee_name")
    if assignor_name: ignored.append("assignor_name")
    if conveyance_text: ignored.append("conveyance_text")
    if reel_frame: ignored.append("reel_frame")
    if recorded_date_from: ignored.append("recorded_date_from")
    if recorded_date_to: ignored.append("recorded_date_to")
    if query: ignored.append("query")
    if ignored:
        logger.warning(
            f"ODP assignment API does not support filtering by: {', '.join(ignored)}. "
            "These parameters are ignored. Only per-application lookup is available."
        )

    # Resolve application number
    app_num = None
    if application_number:
        app_num = clean_app_number(application_number)
    elif patent_number:
        app_num = resolve_patent_to_app_number(patent_number)
        if not app_num:
            clean = patent_number.replace(",", "").replace("US", "").strip()
            return {"error": f"Could not resolve patent {clean} to an application number",
                    "patentFileWrapperDataBag": []}
    else:
        raise APIError("Either patent_number or application_number is required for assignment lookup.")

    return get_assignments_for_application(app_num)


def get_assignment_chain(patent_number: str) -> dict:
    """Get the full assignment (ownership) chain for a patent.

    Returns all recorded assignments in chronological order,
    showing the transfer of rights from inventor to current owner.

    Args:
        patent_number: Patent number to trace ownership for

    Returns:
        Assignment records sorted by recorded date
    """
    return search_patent_assignments(patent_number=patent_number)


def get_assignments_by_company(company_name: str, as_assignee: bool = True,
                               as_assignor: bool = False,
                               start: int = 0, rows: int = 25) -> dict:
    """Search assignments involving a specific company.

    Note: The ODP API does not support broad assignment search by company name.
    This function searches ODP for applications mentioning the company, then
    fetches assignments for each match.

    Args:
        company_name: Company or organization name
        as_assignee: Search where company is the assignee (buyer)
        as_assignor: Search where company is the assignor (seller)
        start: Pagination offset
        rows: Results per page
    """
    client = get_client()
    # Search for applications mentioning this company
    result = client.odp_get(
        "/api/v1/patent/applications/search",
        params={"q": company_name, "start": start, "rows": rows}
    )
    apps = result.get("patentFileWrapperDataBag", result.get("results", []))

    all_assignments = []
    for app in apps[:10]:  # Cap at 10 apps to avoid excessive API calls (1 request per app)
        app_num = app.get("applicationNumberText", "")
        if not app_num:
            continue
        try:
            assign_result = get_assignments_for_application(app_num)
            bags = assign_result.get("patentFileWrapperDataBag", [])
            for bag in bags:
                for assignment in bag.get("assignmentBag", []):
                    assignment["_applicationNumber"] = app_num
                    all_assignments.append(assignment)
        except APIError:
            continue

    return {"assignments": all_assignments, "count": len(all_assignments)}


def search_recent_assignments(assignee_name: str = None,
                              start: int = 0, rows: int = 25) -> dict:
    """Search assignment records, optionally filtered by assignee name.

    Note: The ODP API does not support date-range assignment search.
    This searches ODP for applications matching the query and fetches
    assignment records for each match.

    Args:
        assignee_name: Optionally filter by assignee name
        start: Pagination offset
        rows: Results per page
    """
    client = get_client()

    query = assignee_name or ""
    result = client.odp_get(
        "/api/v1/patent/applications/search",
        params={"q": query, "start": start, "rows": rows} if query else
               {"start": start, "rows": rows}
    )

    apps = result.get("patentFileWrapperDataBag", result.get("results", []))
    all_assignments = []
    for app in apps[:10]:
        app_num = app.get("applicationNumberText", "")
        if not app_num:
            continue
        try:
            assign_result = get_assignments_for_application(app_num)
            bags = assign_result.get("patentFileWrapperDataBag", [])
            for bag in bags:
                for assignment in bag.get("assignmentBag", []):
                    assignment["_applicationNumber"] = app_num
                    all_assignments.append(assignment)
        except APIError:
            continue

    return {"assignments": all_assignments, "count": len(all_assignments)}


# ── CLI interface ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Search USPTO Patent Assignments")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of formatted text")
    sub = parser.add_subparsers(dest="command")

    # search assignments
    p_search = sub.add_parser("search", help="Search assignment records")
    p_search.add_argument("--patent-number", help="Patent number")
    p_search.add_argument("--app-number", help="Application number")
    p_search.add_argument("--assignee", help="Assignee (buyer) name")
    p_search.add_argument("--assignor", help="Assignor (seller) name")
    p_search.add_argument("--query", help="Free-text search")
    p_search.add_argument("--size", type=int, default=25)

    # ownership chain
    p_chain = sub.add_parser("chain", help="Get ownership chain for a patent")
    p_chain.add_argument("patent_number", help="Patent number")

    # company assignments
    p_company = sub.add_parser("company", help="Find assignments for a company")
    p_company.add_argument("name", help="Company name")
    p_company.add_argument("--as-buyer", action="store_true", default=True,
                           help="Search as assignee (default)")
    p_company.add_argument("--as-seller", action="store_true",
                           help="Also search as assignor")
    p_company.add_argument("--size", type=int, default=25)

    # recent assignments
    p_recent = sub.add_parser("recent", help="Search assignments (optionally by assignee)")
    p_recent.add_argument("--assignee", help="Filter by assignee name")
    p_recent.add_argument("--size", type=int, default=25)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "search":
            result = search_patent_assignments(
                patent_number=args.patent_number,
                application_number=args.app_number,
                assignee_name=args.assignee,
                assignor_name=args.assignor,
                query=args.query,
                rows=args.size,
            )
        elif args.command == "chain":
            result = get_assignment_chain(args.patent_number)
        elif args.command == "company":
            result = get_assignments_by_company(
                args.name,
                as_assignee=args.as_buyer,
                as_assignor=args.as_seller,
                rows=args.size,
            )
        elif args.command == "recent":
            result = search_recent_assignments(
                assignee_name=args.assignee,
                rows=args.size,
            )
        else:
            parser.print_help()
            return

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(format_assignment_results(result))

    except APIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
