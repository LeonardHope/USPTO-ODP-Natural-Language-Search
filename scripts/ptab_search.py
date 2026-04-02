"""
USPTO PTAB (Patent Trial and Appeal Board) Search module.

Provides comprehensive access to PTAB data covering trial proceedings,
trial decisions, trial documents, appeal decisions, and interference
decisions via the USPTO Open Data Portal API.

API Base: https://api.uspto.gov
Auth: USPTO_ODP_API_KEY env var, sent as X-API-KEY header
Rate limit: 60 requests/minute

PTAB Trials endpoints:
- Proceedings: /api/v1/patent/trials/proceedings/search
- Decisions:   /api/v1/patent/trials/decisions/search
- Documents:   /api/v1/patent/trials/documents/search

PTAB Appeals endpoints:
- Decisions:   /api/v1/patent/appeals/decisions/search

PTAB Interferences endpoints:
- Decisions:   /api/v1/patent/interferences/decisions/search

All search endpoints support both GET (query params) and POST (JSON body)
with the standard PatentSearchRequest structure:
  GET params: q, filters, rangeFilters, sort, offset, limit, fields, facets
  POST body:  q, filters, rangeFilters, sort, fields, pagination:{offset,limit}, facets
"""

import json
import logging
import sys
import argparse

from uspto_client import get_client, APIError, clean_patent_number
from format_results import format_ptab_results

logger = logging.getLogger("ptab_search")


# ── Trial Proceedings ──────────────────────────────────────────────────

def search_proceedings(query: str = None, patent_number: str = None,
                       party_name: str = None, trial_number: str = None,
                       proceeding_type: str = None,
                       offset: int = 0, limit: int = 25) -> dict:
    """Search PTAB trial proceedings.

    Covers IPR (Inter Partes Review), PGR (Post-Grant Review),
    CBM (Covered Business Method), and DER (Derivation) proceedings.

    All search terms are combined into a single free-text query string
    since the API uses a `q` parameter for full-text search.

    Args:
        query: Free-text search across proceeding data
        patent_number: Patent number involved in the proceeding
        party_name: Name of a party (petitioner or patent owner)
        trial_number: PTAB trial number (e.g. 'IPR2020-00001')
        proceeding_type: Type filter: 'IPR', 'PGR', 'CBM', 'DER'
        offset: Pagination offset
        limit: Results per page

    Returns:
        API response with matching proceedings
    """
    client = get_client()
    params = {"offset": offset, "limit": limit}

    q_parts = []
    if query:
        q_parts.append(query)
    if patent_number:
        q_parts.append(clean_patent_number(patent_number))
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
            return {"count": 0, "patentTrialProceedingDataBag": []}
        raise


def get_proceeding(trial_number: str) -> dict:
    """Get full details for a specific PTAB trial proceeding.

    Args:
        trial_number: PTAB trial number (e.g. 'IPR2020-00001')

    Returns:
        Proceeding metadata including parties, patent, status, and dates
    """
    client = get_client()
    return client.odp_get(f"/api/v1/patent/trials/proceedings/{trial_number}")


# ── Trial Decisions ────────────────────────────────────────────────────

def search_trial_decisions(query: str = None, patent_number: str = None,
                           trial_number: str = None,
                           offset: int = 0, limit: int = 25) -> dict:
    """Search PTAB trial decision documents.

    Args:
        query: Free-text search within decision data
        patent_number: Patent number to find decisions for
        trial_number: Trial number to find decisions for
        offset: Pagination offset
        limit: Results per page

    Returns:
        API response with matching trial decisions
    """
    client = get_client()
    params = {"offset": offset, "limit": limit}

    q_parts = []
    if query:
        q_parts.append(query)
    if patent_number:
        q_parts.append(clean_patent_number(patent_number))
    if trial_number:
        q_parts.append(trial_number)

    if q_parts:
        params["q"] = " ".join(q_parts)

    try:
        return client.odp_get("/api/v1/patent/trials/decisions/search", params=params)
    except APIError as e:
        if e.status_code == 404:
            return {"count": 0, "patentTrialDecisionDataBag": []}
        raise


def get_trial_decision(document_id: str) -> dict:
    """Get a specific PTAB trial decision by document identifier.

    Args:
        document_id: Decision document identifier

    Returns:
        Decision metadata and content
    """
    client = get_client()
    return client.odp_get(f"/api/v1/patent/trials/decisions/{document_id}")


def get_decisions_for_trial(trial_number: str) -> dict:
    """Get all decisions associated with a specific trial.

    Args:
        trial_number: PTAB trial number (e.g. 'IPR2020-00001')

    Returns:
        All decision records for the specified trial
    """
    client = get_client()
    return client.odp_get(f"/api/v1/patent/trials/{trial_number}/decisions")


# ── Trial Documents ────────────────────────────────────────────────────

def search_trial_documents(query: str = None, trial_number: str = None,
                           offset: int = 0, limit: int = 25) -> dict:
    """Search PTAB trial documents (filings, exhibits, orders).

    Args:
        query: Free-text search within document data
        trial_number: Trial number to find documents for
        offset: Pagination offset
        limit: Results per page

    Returns:
        API response with matching trial documents
    """
    client = get_client()
    params = {"offset": offset, "limit": limit}

    q_parts = []
    if query:
        q_parts.append(query)
    if trial_number:
        q_parts.append(trial_number)

    if q_parts:
        params["q"] = " ".join(q_parts)

    try:
        return client.odp_get("/api/v1/patent/trials/documents/search", params=params)
    except APIError as e:
        if e.status_code == 404:
            return {"count": 0, "patentTrialDocumentDataBag": []}
        raise


def get_trial_document(document_id: str) -> dict:
    """Get a specific PTAB trial document by document identifier.

    Args:
        document_id: Document identifier

    Returns:
        Document metadata
    """
    client = get_client()
    return client.odp_get(f"/api/v1/patent/trials/documents/{document_id}")


def get_documents_for_trial(trial_number: str) -> dict:
    """Get all documents filed in a specific trial.

    Args:
        trial_number: PTAB trial number (e.g. 'IPR2020-00001')

    Returns:
        All document records for the specified trial
    """
    client = get_client()
    return client.odp_get(f"/api/v1/patent/trials/{trial_number}/documents")


# ── Appeal Decisions ───────────────────────────────────────────────────

def search_appeal_decisions(query: str = None, appeal_number: str = None,
                            offset: int = 0, limit: int = 25) -> dict:
    """Search PTAB appeal decision documents.

    Args:
        query: Free-text search within appeal decision data
        appeal_number: Appeal number to find decisions for
        offset: Pagination offset
        limit: Results per page

    Returns:
        API response with matching appeal decisions
    """
    client = get_client()
    params = {"offset": offset, "limit": limit}

    q_parts = []
    if query:
        q_parts.append(query)
    if appeal_number:
        q_parts.append(appeal_number)

    if q_parts:
        params["q"] = " ".join(q_parts)

    try:
        return client.odp_get("/api/v1/patent/appeals/decisions/search", params=params)
    except APIError as e:
        if e.status_code == 404:
            return {"count": 0, "patentAppealDataBag": []}
        raise


def get_appeal_decision(document_id: str) -> dict:
    """Get a specific PTAB appeal decision by document identifier.

    Args:
        document_id: Decision document identifier

    Returns:
        Appeal decision metadata and content
    """
    client = get_client()
    return client.odp_get(f"/api/v1/patent/appeals/decisions/{document_id}")


def get_decisions_for_appeal(appeal_number: str) -> dict:
    """Get all decisions for a specific appeal.

    Args:
        appeal_number: PTAB appeal number

    Returns:
        All decision records for the specified appeal
    """
    client = get_client()
    return client.odp_get(f"/api/v1/patent/appeals/{appeal_number}/decisions")


# ── Interference Decisions ─────────────────────────────────────────────

def search_interference_decisions(query: str = None,
                                  interference_number: str = None,
                                  offset: int = 0, limit: int = 25) -> dict:
    """Search PTAB interference decision documents.

    Interferences determine priority of invention between competing
    patent applications (largely replaced by derivation proceedings
    under AIA, but historical records remain searchable).

    Args:
        query: Free-text search within interference decision data
        interference_number: Interference number to find decisions for
        offset: Pagination offset
        limit: Results per page

    Returns:
        API response with matching interference decisions
    """
    client = get_client()
    params = {"offset": offset, "limit": limit}

    q_parts = []
    if query:
        q_parts.append(query)
    if interference_number:
        q_parts.append(interference_number)

    if q_parts:
        params["q"] = " ".join(q_parts)

    try:
        return client.odp_get(
            "/api/v1/patent/interferences/decisions/search", params=params
        )
    except APIError as e:
        if e.status_code == 404:
            return {"count": 0, "patentTrialDecisionDataBag": []}
        raise


def get_interference_decision(document_id: str) -> dict:
    """Get a specific interference decision by document identifier.

    Args:
        document_id: Decision document identifier

    Returns:
        Interference decision metadata and content
    """
    client = get_client()
    return client.odp_get(
        f"/api/v1/patent/interferences/decisions/{document_id}"
    )


def get_decisions_for_interference(interference_number: str) -> dict:
    """Get all decisions for a specific interference proceeding.

    Args:
        interference_number: PTAB interference number

    Returns:
        All decision records for the specified interference
    """
    client = get_client()
    return client.odp_get(
        f"/api/v1/patent/interferences/{interference_number}/decisions"
    )


# ── CLI interface ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Search USPTO PTAB Records")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of formatted text")
    sub = parser.add_subparsers(dest="command")

    # proceedings
    p_proc = sub.add_parser("proceedings", help="Search PTAB trial proceedings")
    p_proc.add_argument("--query", "-q", help="Free-text search")
    p_proc.add_argument("--patent-number", help="Patent number")
    p_proc.add_argument("--party", help="Party name")
    p_proc.add_argument("--trial", help="Trial number (e.g. IPR2020-00001)")
    p_proc.add_argument("--type", choices=["IPR", "PGR", "CBM", "DER"],
                         help="Proceeding type")
    p_proc.add_argument("--limit", type=int, default=25)

    # trial decisions
    p_dec = sub.add_parser("decisions", help="Search PTAB trial decisions")
    p_dec.add_argument("--query", "-q", help="Free-text search")
    p_dec.add_argument("--patent-number", help="Patent number")
    p_dec.add_argument("--trial", help="Trial number")
    p_dec.add_argument("--limit", type=int, default=25)

    # trial documents
    p_doc = sub.add_parser("documents", help="Search PTAB trial documents")
    p_doc.add_argument("--query", "-q", help="Free-text search")
    p_doc.add_argument("--trial", help="Trial number")
    p_doc.add_argument("--limit", type=int, default=25)

    # appeal decisions
    p_app = sub.add_parser("appeals", help="Search PTAB appeal decisions")
    p_app.add_argument("--query", "-q", help="Free-text search")
    p_app.add_argument("--appeal", help="Appeal number")
    p_app.add_argument("--limit", type=int, default=25)

    # interference decisions
    p_int = sub.add_parser("interferences",
                           help="Search PTAB interference decisions")
    p_int.add_argument("--query", "-q", help="Free-text search")
    p_int.add_argument("--interference", help="Interference number")
    p_int.add_argument("--limit", type=int, default=25)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "proceedings":
            result = search_proceedings(
                query=args.query, patent_number=args.patent_number,
                party_name=args.party, trial_number=args.trial,
                proceeding_type=args.type, limit=args.limit,
            )
        elif args.command == "decisions":
            result = search_trial_decisions(
                query=args.query, patent_number=args.patent_number,
                trial_number=args.trial, limit=args.limit,
            )
        elif args.command == "documents":
            result = search_trial_documents(
                query=args.query, trial_number=args.trial,
                limit=args.limit,
            )
        elif args.command == "appeals":
            result = search_appeal_decisions(
                query=args.query, appeal_number=args.appeal,
                limit=args.limit,
            )
        elif args.command == "interferences":
            result = search_interference_decisions(
                query=args.query,
                interference_number=args.interference,
                limit=args.limit,
            )
        else:
            parser.print_help()
            return

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(format_ptab_results(result))

    except APIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
