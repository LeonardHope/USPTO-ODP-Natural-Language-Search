"""
USPTO Trademark Status & Document Retrieval (TSDR) API - Search module.

Provides functions for retrieving trademark case status, documents, and
metadata from the USPTO TSDR system.

API Base: https://tsdrapi.uspto.gov
Auth: USPTO_ODP_API_KEY env var, sent as USPTO-API-KEY header (note: different
      header name than ODP APIs which use X-API-KEY). The client's tsdr_get()
      method handles this automatically.

Case ID formats:
    sn88123456   — Serial number
    rn1234567    — Registration number
    ref12345678  — Reference number
    ir12345678   — International registration number

Endpoints:
- GET /ts/cd/casestatus/{caseid}/info           — Case status (ST96 XML)
- GET /ts/cd/casestatus/{caseid}/content.pdf     — Case status as PDF
- GET /ts/cd/casedocs/{caseid}/info              — All document metadata (XML)
- GET /ts/cd/casedocs/{caseid}/bundle            — Bundle info
- GET /ts/cd/casedoc/{caseid}/{docid}/info       — Single document metadata
- GET /ts/cd/casedoc/{caseid}/{docid}/download.pdf — Download single document
- GET /ts/cd/caseMultiStatus/{type}?ids=id1,id2  — Batch status lookup
- GET /last-update/info.json                      — Last database update

Note: Many TSDR responses are XML. The client's _request method returns
{"raw_xml": text} for XML content types.
"""

import json
import logging
import sys
import argparse
from pathlib import Path

from uspto_client import get_client, APIError, clean_patent_number, clean_app_number

logger = logging.getLogger("tsdr_search")


# ── Helper ─────────────────────────────────────────────────────────────────

def _format_case_id(serial_number: str = None,
                    registration_number: str = None,
                    case_id: str = None) -> str:
    """Construct a TSDR case ID from various input formats.

    The TSDR API requires case IDs in a specific format with a two-letter
    prefix indicating the ID type: sn (serial), rn (registration),
    ref (reference), or ir (international registration).

    Args:
        serial_number: Trademark serial number (e.g. '88123456').
            Will be prefixed with 'sn'.
        registration_number: Trademark registration number (e.g. '1234567').
            Will be prefixed with 'rn'.
        case_id: Pre-formatted case ID (e.g. 'sn88123456'). Used as-is.

    Returns:
        Formatted case ID string (e.g. 'sn88123456')

    Raises:
        APIError: If no identifier is provided
    """
    if case_id:
        return case_id.strip()
    if serial_number:
        clean = serial_number.replace(",", "").replace(" ", "").strip()
        return f"sn{clean}"
    if registration_number:
        clean = registration_number.replace(",", "").replace(" ", "").strip()
        return f"rn{clean}"
    raise APIError(
        "At least one identifier is required: serial_number, "
        "registration_number, or case_id"
    )


# ── Case Status ────────────────────────────────────────────────────────────

def get_trademark_status(serial_number: str = None,
                         registration_number: str = None,
                         case_id: str = None) -> dict:
    """Get trademark case status information.

    Retrieves the current status of a trademark application or registration
    from the TSDR system. The response is ST96 XML, which the client returns
    as {"raw_xml": text, "status_code": 200}.

    Args:
        serial_number: Trademark serial number (e.g. '88123456')
        registration_number: Trademark registration number (e.g. '1234567')
        case_id: Pre-formatted case ID (e.g. 'sn88123456', 'rn1234567')

    Returns:
        API response with case status data (typically XML wrapped in dict)
    """
    client = get_client()
    cid = _format_case_id(serial_number, registration_number, case_id)
    return client.tsdr_get(f"/ts/cd/casestatus/{cid}/info")


def get_trademark_documents(case_id: str) -> dict:
    """List all documents for a trademark case.

    Returns metadata for all documents in the case file, including
    office actions, responses, amendments, and evidence submissions.

    Args:
        case_id: Formatted case ID (e.g. 'sn88123456')

    Returns:
        API response with document metadata list (XML wrapped in dict)
    """
    client = get_client()
    cid = case_id.strip()
    return client.tsdr_get(f"/ts/cd/casedocs/{cid}/info")


def get_trademark_document(case_id: str, doc_id: str) -> dict:
    """Get metadata for a single trademark document.

    Args:
        case_id: Formatted case ID (e.g. 'sn88123456')
        doc_id: Document identifier from the documents list

    Returns:
        API response with single document metadata
    """
    client = get_client()
    cid = case_id.strip()
    did = doc_id.strip()
    return client.tsdr_get(f"/ts/cd/casedoc/{cid}/{did}/info")


def download_trademark_document(case_id: str, doc_id: str,
                                dest_path: str) -> bool:
    """Download a trademark document PDF.

    Downloads a single document from the trademark case file to the
    specified local path.

    Args:
        case_id: Formatted case ID (e.g. 'sn88123456')
        doc_id: Document identifier
        dest_path: Local file path to save the PDF to

    Returns:
        True if download succeeded

    Raises:
        APIError: If the download fails
    """
    client = get_client()
    cid = case_id.strip()
    did = doc_id.strip()
    url = f"{client.TSDR_BASE}/ts/cd/casedoc/{cid}/{did}/download.pdf"

    # Ensure destination directory exists
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)

    return client.download_file(url, dest_path, api="tsdr")


def get_multi_status(case_type: str, ids: list) -> dict:
    """Batch lookup of multiple trademark case statuses.

    Retrieves status for multiple cases in a single API call.
    More efficient than individual lookups when checking several
    trademarks at once.

    Args:
        case_type: ID type — 'sn' (serial), 'rn' (registration),
            'ref' (reference), or 'ir' (international registration)
        ids: List of ID strings (without prefix). For example,
            case_type='sn' with ids=['88123456', '88654321']

    Returns:
        API response with status for all requested cases
    """
    client = get_client()
    valid_types = {"sn", "rn", "ref", "ir"}
    if case_type not in valid_types:
        raise APIError(
            f"Invalid case_type '{case_type}'. Must be one of: {', '.join(sorted(valid_types))}"
        )

    id_str = ",".join(i.strip() for i in ids)
    return client.tsdr_get(
        f"/ts/cd/caseMultiStatus/{case_type}",
        params={"ids": id_str}
    )


def get_last_update() -> dict:
    """Get the timestamp of the last TSDR database update.

    Useful for checking data freshness before making queries.

    Returns:
        JSON response with last update timestamp
    """
    client = get_client()
    return client.tsdr_get("/last-update/info.json")


# ── CLI interface ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Search USPTO Trademark Status & Document Retrieval (TSDR)"
    )
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of formatted text")
    sub = parser.add_subparsers(dest="command")

    # status
    p_status = sub.add_parser("status", help="Get trademark case status")
    p_status.add_argument("--serial", help="Trademark serial number")
    p_status.add_argument("--registration", help="Trademark registration number")
    p_status.add_argument("--case-id", help="Pre-formatted case ID (e.g. sn88123456)")

    # documents
    p_docs = sub.add_parser("documents", help="List documents for a trademark case")
    p_docs.add_argument("case_id", help="Case ID (e.g. sn88123456)")

    # last-update
    sub.add_parser("last-update", help="Check TSDR database freshness")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "status":
            result = get_trademark_status(
                serial_number=args.serial,
                registration_number=args.registration,
                case_id=args.case_id,
            )
        elif args.command == "documents":
            result = get_trademark_documents(args.case_id)
        elif args.command == "last-update":
            result = get_last_update()
        else:
            parser.print_help()
            return

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            # TSDR responses are often XML; display raw content
            if "raw_xml" in result:
                print(result["raw_xml"])
            else:
                print(json.dumps(result, indent=2))

    except APIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
