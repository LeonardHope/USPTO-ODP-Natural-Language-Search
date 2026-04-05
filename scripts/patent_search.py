"""
USPTO Open Data Portal (ODP) - Patent Search module.

Provides comprehensive patent search functions using the USPTO Open Data
Portal API. Supports search by assignee, inventor, keyword, patent number,
application number, CPC classification, examiner, and application status.

API Base: https://api.uspto.gov
Auth: USPTO_ODP_API_KEY env var, sent as X-API-KEY header
Rate limit: 60 requests/minute (4/min for PDF/ZIP downloads)

Search endpoints:
- POST /api/v1/patent/applications/search  (JSON body)
- GET  /api/v1/patent/applications/search  (query params)
- GET  /api/v1/patent/applications/{applicationNumberText}
- POST /api/v1/patent/applications/search/download
"""

import json
import logging
import sys
import argparse

from uspto_client import get_client, APIError, clean_patent_number, clean_app_number
from format_results import format_patent_list, format_patent_detail

logger = logging.getLogger("patent_search")


# ── Generic Search ─────────────────────────────────────────────────────

def search_patents(q=None, filters=None, range_filters=None, sort=None,
                   fields=None, offset=0, limit=25):
    """Generic patent search using the ODP POST search endpoint.

    Builds a PatentSearchRequest JSON body and sends it to the search
    endpoint. All parameters are optional; omit them to browse recent
    applications.

    Args:
        q: Free text or field:value opensearch syntax query string
        filters: List of filter dicts, e.g.
            [{"name": "applicationMetaData.cpcClassificationBag", "value": ["H04L"]}]
        range_filters: List of range filter dicts, e.g.
            [{"field": "applicationMetaData.grantDate",
              "valueFrom": "2020-01-01", "valueTo": "2025-12-31"}]
        sort: List of sort dicts, e.g.
            [{"field": "applicationMetaData.grantDate", "order": "desc"}]
        fields: List of field paths to return
        offset: Pagination offset (default 0)
        limit: Results per page (default 25, max varies by endpoint)

    Returns:
        Raw API response dict with keys: count, patentFileWrapperDataBag,
        requestIdentifier
    """
    client = get_client()

    body = {}
    if q:
        body["q"] = q
    if filters:
        body["filters"] = filters
    if range_filters:
        body["rangeFilters"] = range_filters
    if sort:
        body["sort"] = sort
    if fields:
        body["fields"] = fields
    body["pagination"] = {"offset": offset, "limit": limit}

    logger.debug("POST search body: %s", json.dumps(body, indent=2))
    return client.odp_post("/api/v1/patent/applications/search", json_body=body)


# ── Search by Assignee ─────────────────────────────────────────────────

def search_by_assignee(name, date_from=None, date_to=None, limit=25):
    """Search patents by applicant/assignee name.

    Uses free-text search with the assignee name. Optionally filters
    by filing date range.

    Note: "Filed after 2020" uses filingDate. For grant date filtering,
    pass a custom range_filter via search_patents() directly.

    Args:
        name: Applicant or assignee organization name
        date_from: Start of filing date range (yyyy-MM-dd), optional
        date_to: End of filing date range (yyyy-MM-dd), optional
        limit: Maximum results to return (default 25)

    Returns:
        Raw API response dict
    """
    range_filters = None
    if date_from or date_to:
        # ODP requires both valueFrom and valueTo in rangeFilters
        rf = {
            "field": "applicationMetaData.filingDate",
            "valueFrom": date_from or "1900-01-01",
            "valueTo": date_to or "2099-12-31",
        }
        range_filters = [rf]

    return search_patents(q=name, range_filters=range_filters, limit=limit)


# ── Search by Inventor ─────────────────────────────────────────────────

def search_by_inventor(last_name, first_name=None, date_from=None,
                       date_to=None, limit=25):
    """Search patents by inventor name.

    Constructs a quoted full name query for exact matching when both
    first and last names are provided, or a simple last name query
    for broader matching.

    Args:
        last_name: Inventor last name (required)
        first_name: Inventor first name (optional, for exact matching)
        date_from: Start of filing date range (yyyy-MM-dd), optional
        date_to: End of filing date range (yyyy-MM-dd), optional
        limit: Maximum results to return (default 25)

    Returns:
        Raw API response dict
    """
    if first_name:
        q = f'"{first_name} {last_name}"'
    else:
        q = last_name

    range_filters = None
    if date_from or date_to:
        # ODP requires both valueFrom and valueTo in rangeFilters
        rf = {
            "field": "applicationMetaData.filingDate",
            "valueFrom": date_from or "1900-01-01",
            "valueTo": date_to or "2099-12-31",
        }
        range_filters = [rf]

    return search_patents(q=q, range_filters=range_filters, limit=limit)


# ── Search by Keyword ──────────────────────────────────────────────────

def search_by_keyword(keywords, date_from=None, date_to=None, limit=25):
    """Free-text keyword search across all patent fields.

    Searches invention titles, abstracts, and other indexed text fields
    for the given keywords.

    Args:
        keywords: Free-text search string (e.g. "autonomous vehicle lidar")
        date_from: Start of filing date range (yyyy-MM-dd), optional
        date_to: End of filing date range (yyyy-MM-dd), optional
        limit: Maximum results to return (default 25)

    Returns:
        Raw API response dict
    """
    range_filters = None
    if date_from or date_to:
        # ODP requires both valueFrom and valueTo in rangeFilters
        rf = {
            "field": "applicationMetaData.filingDate",
            "valueFrom": date_from or "1900-01-01",
            "valueTo": date_to or "2099-12-31",
        }
        range_filters = [rf]

    return search_patents(q=keywords, range_filters=range_filters, limit=limit)


# ── Search by Patent Number ───────────────────────────────────────────

def search_by_patent_number(patent_number):
    """Look up a patent by its granted patent number.

    Cleans the patent number, searches for it, and verifies the match
    against the patentNumber field in the results.

    Args:
        patent_number: Patent number in any format (e.g. '10,000,000',
            'US10000000', 'RE49000', 'D900000')

    Returns:
        Matching application dict, or empty dict if not found
    """
    clean = clean_patent_number(patent_number)
    logger.debug("Searching for patent number: %s", clean)

    try:
        result = search_patents(q=clean, limit=10)
    except APIError as e:
        if e.status_code == 404:
            return {}
        raise

    # Verify the match against the patentNumber field
    for app in result.get("patentFileWrapperDataBag", []):
        meta = app.get("applicationMetaData", {})
        if meta.get("patentNumber") == clean:
            return app

    # If no exact match, return the first result with a warning
    apps = result.get("patentFileWrapperDataBag", [])
    if apps:
        logger.warning(
            "No exact patent number match for '%s'; "
            "returning first search result (app %s)",
            clean, apps[0].get("applicationNumberText", "?")
        )
        return apps[0]

    return {}


# ── Search by Application Number ──────────────────────────────────────

def search_by_application_number(application_number):
    """Look up a patent application by its application number.

    Uses a direct GET request to the application endpoint for an
    exact lookup by application serial number.

    Args:
        application_number: Application serial number in any format
            (e.g. '16/123,456', '16123456')

    Returns:
        Application data dict, or empty dict if not found
    """
    client = get_client()
    clean = clean_app_number(application_number)
    logger.debug("Looking up application number: %s", clean)

    try:
        return client.odp_get(f"/api/v1/patent/applications/{clean}")
    except APIError as e:
        if e.status_code == 404:
            return {}
        raise


# ── Search by CPC Classification ─────────────────────────────────────

def search_by_cpc(cpc_code, date_from=None, date_to=None, limit=25):
    """Search patents by CPC (Cooperative Patent Classification) code.

    Note: The ODP search API does not currently support filtering by CPC
    classification directly. This function searches for the CPC code as
    free text, which may return patents that reference the CPC code in
    their metadata. For precise CPC filtering, use the ODP Bulk Data
    products which include CPC classification data.

    Args:
        cpc_code: CPC classification code (e.g. 'H04L', 'G06F 3/01')
        date_from: Start of filing date range (yyyy-MM-dd), optional
        date_to: End of filing date range (yyyy-MM-dd), optional
        limit: Maximum results to return (default 25)

    Returns:
        Raw API response dict (may be empty if CPC code is not indexed
        as searchable text in ODP)
    """
    logger.warning(
        "CPC classification search is limited on ODP. The cpcClassificationBag "
        "field is not directly searchable. Results may be incomplete."
    )

    range_filters = None
    if date_from or date_to:
        # ODP requires both valueFrom and valueTo in rangeFilters
        rf = {
            "field": "applicationMetaData.filingDate",
            "valueFrom": date_from or "1900-01-01",
            "valueTo": date_to or "2099-12-31",
        }
        range_filters = [rf]

    return search_patents(q=cpc_code, range_filters=range_filters, limit=limit)


# ── Search by Examiner ────────────────────────────────────────────────

def search_by_examiner(examiner_name, limit=25):
    """Search patents by examiner name.

    Uses field-scoped query syntax to search the examiner name field.

    Args:
        examiner_name: Examiner name (partial or full)
        limit: Maximum results to return (default 25)

    Returns:
        Raw API response dict
    """
    q = f"applicationMetaData.examinerNameText:{examiner_name}"
    return search_patents(q=q, limit=limit)


# ── Search by Application Status ──────────────────────────────────────

def search_by_status(status, limit=25):
    """Search patents by application status description.

    Uses a filter on the applicationStatusDescriptionText field to
    find applications with a specific status.

    Args:
        status: Application status text (e.g. 'Patented Case',
            'Docketed New Case - Ready for Examination')
        limit: Maximum results to return (default 25)

    Returns:
        Raw API response dict
    """
    filters = [
        {"name": "applicationMetaData.applicationStatusDescriptionText",
         "value": [status]}
    ]
    return search_patents(filters=filters, limit=limit)


# ── Download Search Results ───────────────────────────────────────────

def download_search_results(q=None, filters=None, range_filters=None,
                            format="json"):
    """Download search results in bulk via the download endpoint.

    Posts a search request to the download endpoint, which returns
    results in the specified format for offline processing.

    Args:
        q: Free text or field:value opensearch syntax query string
        filters: List of filter dicts (same format as search_patents)
        range_filters: List of range filter dicts (same format as search_patents)
        format: Download format — 'json' or 'csv' (default 'json')

    Returns:
        Download response from the API
    """
    client = get_client()

    body = {}
    if q:
        body["q"] = q
    if filters:
        body["filters"] = filters
    if range_filters:
        body["rangeFilters"] = range_filters

    params_str = f"?format={format}" if format != "json" else ""
    return client.odp_post(
        f"/api/v1/patent/applications/search/download{params_str}",
        json_body=body
    )


# ── CLI interface ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Search USPTO patents via the Open Data Portal API"
    )
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of formatted text")
    sub = parser.add_subparsers(dest="command")

    # assignee search
    p_assignee = sub.add_parser("assignee", help="Search by assignee name")
    p_assignee.add_argument("name", help="Assignee/applicant name")
    p_assignee.add_argument("--limit", type=int, default=25)
    p_assignee.add_argument("--date-from", help="Grant date start (yyyy-MM-dd)")
    p_assignee.add_argument("--date-to", help="Grant date end (yyyy-MM-dd)")

    # inventor search
    p_inventor = sub.add_parser("inventor", help="Search by inventor name")
    p_inventor.add_argument("last_name", help="Inventor last name")
    p_inventor.add_argument("--first", help="Inventor first name")
    p_inventor.add_argument("--limit", type=int, default=25)
    p_inventor.add_argument("--date-from", help="Grant date start (yyyy-MM-dd)")
    p_inventor.add_argument("--date-to", help="Grant date end (yyyy-MM-dd)")

    # keyword search
    p_keyword = sub.add_parser("keyword", help="Free-text keyword search")
    p_keyword.add_argument("keywords", help="Search keywords")
    p_keyword.add_argument("--limit", type=int, default=25)
    p_keyword.add_argument("--date-from", help="Grant date start (yyyy-MM-dd)")
    p_keyword.add_argument("--date-to", help="Grant date end (yyyy-MM-dd)")

    # patent number lookup
    p_patent = sub.add_parser("patent", help="Look up by patent number")
    p_patent.add_argument("patent_number", help="Patent number")

    # application number lookup
    p_app = sub.add_parser("application", help="Look up by application number")
    p_app.add_argument("application_number", help="Application number")

    # CPC search
    p_cpc = sub.add_parser("cpc", help="Search by CPC classification")
    p_cpc.add_argument("cpc_code", help="CPC code (e.g. H04L)")
    p_cpc.add_argument("--limit", type=int, default=25)
    p_cpc.add_argument("--date-from", help="Grant date start (yyyy-MM-dd)")
    p_cpc.add_argument("--date-to", help="Grant date end (yyyy-MM-dd)")

    # examiner search
    p_examiner = sub.add_parser("examiner", help="Search by examiner name")
    p_examiner.add_argument("name", help="Examiner name")
    p_examiner.add_argument("--limit", type=int, default=25)

    # status search
    p_status = sub.add_parser("status", help="Search by application status")
    p_status.add_argument("status", help="Application status text")
    p_status.add_argument("--limit", type=int, default=25)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "assignee":
            result = search_by_assignee(
                args.name,
                date_from=args.date_from,
                date_to=args.date_to,
                limit=args.limit,
            )
        elif args.command == "inventor":
            result = search_by_inventor(
                args.last_name,
                first_name=args.first,
                date_from=args.date_from,
                date_to=args.date_to,
                limit=args.limit,
            )
        elif args.command == "keyword":
            result = search_by_keyword(
                args.keywords,
                date_from=args.date_from,
                date_to=args.date_to,
                limit=args.limit,
            )
        elif args.command == "patent":
            result = search_by_patent_number(args.patent_number)
        elif args.command == "application":
            result = search_by_application_number(args.application_number)
        elif args.command == "cpc":
            result = search_by_cpc(
                args.cpc_code,
                date_from=args.date_from,
                date_to=args.date_to,
                limit=args.limit,
            )
        elif args.command == "examiner":
            result = search_by_examiner(args.name, limit=args.limit)
        elif args.command == "status":
            result = search_by_status(args.status, limit=args.limit)
        else:
            parser.print_help()
            return

        if args.json:
            print(json.dumps(result, indent=2))
        elif args.command in ("patent", "application"):
            print(format_patent_detail(result, source="odp"))
        else:
            print(format_patent_list(result, source="odp"))

    except APIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
