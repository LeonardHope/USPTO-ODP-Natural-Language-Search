"""
USPTO File Wrapper Document Downloader.

Lists and downloads prosecution history documents (office actions, amendments,
IDS filings, etc.) from the USPTO Open Data Portal (ODP) API.

Usage:
    python download_documents.py list 16123456
    python download_documents.py list 16123456 --key-only
    python download_documents.py download 16123456
    python download_documents.py download 16123456 --all
    python download_documents.py download 16123456 --codes CTNF,CTFR
    python download_documents.py download 16123456 -o ./my-downloads

API Base: https://api.uspto.gov
Auth: USPTO_ODP_API_KEY env var, sent as X-Api-Key header
Rate limit: 4 requests/minute for PDF downloads
"""

import json
import os
import sys
import argparse
from pathlib import Path

from uspto_client import get_client, APIError


# Key prosecution document codes — filters out routine filings and receipts
KEY_DOC_CODES = {
    # Office actions
    "CTNF",   # Non-final rejection
    "CTFR",   # Final rejection
    "NOA",    # Notice of allowance
    "NFOA",   # Non-final office action (alternate code)
    "FOA",    # Final office action (alternate code)
    "EX.CLA", # Examiner's claim amendments
    # Applicant responses
    "A...",   # Amendment (various) — API literally returns "A..." as the code
    "AMD",    # Amendment
    "REM",    # Remarks
    "CLM",    # Claims
    "AMSB",   # Amendment after final / RCE submission
    "AP.PRE", # Applicant pre-interview communication
    # RCE
    "RCEX",   # Request for continued examination
    # IDS and references
    "IDS",    # Information disclosure statement
    "1449",   # IDS form
    "892",    # Examiner's cited references
    # Filing docs
    "SPEC",   # Specification
    "ABST",   # Abstract
    "DRW",    # Drawings
    # Publication and issue
    "NTC.PUB", # Publication notice
    "ISSUE",  # Issue notification
    # Appeal
    "ABR",    # Appeal brief
    "ABRD",   # Appeal board decision
    "N.APL",  # Notice of appeal
    # Restriction / election
    "RESTR",  # Restriction requirement
    "ELRES",  # Election response
    # Petition
    "PET",    # Petition
    "PET.D",  # Petition decision
}

# Human-readable names for common document codes
DOC_CODE_NAMES = {
    "CTNF": "Non-Final Rejection",
    "CTFR": "Final Rejection",
    "NOA": "Notice of Allowance",
    "NFOA": "Non-Final Office Action",
    "FOA": "Final Office Action",
    "CLM": "Claims",
    "SPEC": "Specification",
    "ABST": "Abstract",
    "DRW": "Drawings",
    "AMD": "Amendment",
    "AMSB": "Amendment/RCE Submission",
    "REM": "Remarks",
    "RCEX": "Request for Continued Examination",
    "IDS": "Information Disclosure Statement",
    "1449": "IDS Form 1449",
    "892": "Examiner References (Form 892)",
    "NTC.PUB": "Publication Notice",
    "ISSUE": "Issue Notification",
    "ABR": "Appeal Brief",
    "ABRD": "Appeal Board Decision",
    "N.APL": "Notice of Appeal",
    "RESTR": "Restriction Requirement",
    "ELRES": "Election Response",
    "PET": "Petition",
    "PET.D": "Petition Decision",
    "EX.CLA": "Examiner's Claim Amendments",
    "AP.PRE": "Applicant Pre-Interview Communication",
}


def _clean_app_number(app_number: str) -> str:
    """Clean application number to digits only."""
    return app_number.replace("/", "").replace(",", "").replace(" ", "").strip()


def _get_doc_field(doc: dict, *field_names, default=""):
    """Try multiple field names and return the first non-empty value."""
    for name in field_names:
        val = doc.get(name, "")
        if val:
            return val
    return default


def _parse_doc(doc: dict) -> dict:
    """Extract normalized fields from a document record.

    ODP document records may use different field naming conventions.
    This normalizes them into a consistent dict.
    """
    doc_id = _get_doc_field(doc, "documentIdentifier", "documentId", "id")
    doc_code = _get_doc_field(doc, "documentCode", "documentCodeDescriptionText",
                               "code", "docCode")
    doc_desc = _get_doc_field(doc, "documentDescription", "documentCodeDescriptionText",
                               "officialDocumentCodeDescriptionText", "description")
    date = _get_doc_field(doc, "officialDate", "mailRoomDate", "mailDate",
                           "documentDate", "date")
    direction = _get_doc_field(doc, "directionCategory", "direction")
    page_count = doc.get("pageCount", doc.get("numberOfPages", ""))

    # Extract PDF download URL from downloadOptionBag
    download_url = ""
    for option in doc.get("downloadOptionBag", []):
        if option.get("mimeTypeIdentifier") == "PDF":
            download_url = option.get("downloadUrl", "")
            if not page_count:
                page_count = option.get("pageTotalQuantity", "")
            break

    # If doc_desc is same as doc_code, try to get a better name
    if doc_desc == doc_code:
        doc_desc = DOC_CODE_NAMES.get(doc_code, doc_code)

    return {
        "id": doc_id,
        "code": doc_code,
        "description": doc_desc or DOC_CODE_NAMES.get(doc_code, doc_code),
        "date": date,
        "direction": direction,
        "page_count": page_count,
        "download_url": download_url,
        "raw": doc,
    }


def fetch_all_documents(app_number: str) -> list:
    """Fetch all documents for an application, handling pagination.

    Args:
        app_number: Application number (will be cleaned)

    Returns:
        List of raw document dicts from the API
    """
    client = get_client()
    clean = _clean_app_number(app_number)
    all_docs = []
    start = 0
    rows = 100

    while True:
        params = {"start": start, "rows": rows}
        result = client.odp_get(
            f"/api/v1/patent/applications/{clean}/documents", params=params
        )

        # Handle various response formats
        docs = []
        if isinstance(result, list):
            docs = result
        elif isinstance(result, dict):
            docs = (result.get("documentBag", [])
                    or result.get("documents", [])
                    or result.get("results", [])
                    or result.get("patentFileWrapperDocumentBag", []))
            if not docs and "count" not in result and "totalCount" not in result:
                # Unexpected response format — try to find a list of documents.
                # This is a best-effort fallback; log a warning so issues are visible.
                for key in result:
                    if isinstance(result[key], list) and len(result[key]) > 0:
                        print(f"  Warning: unexpected response format, extracting docs from '{key}'")
                        docs = result[key]
                        break

        all_docs.extend(docs)

        # Check if we got all documents
        total = None
        if isinstance(result, dict):
            total = result.get("count", result.get("totalCount"))

        if total is not None and start + rows < total:
            start += rows
        else:
            break

    return all_docs


def filter_documents(docs: list, key_only: bool = False,
                     codes: list = None) -> list:
    """Filter documents by type.

    Args:
        docs: List of parsed document dicts
        key_only: If True, only return key prosecution documents
        codes: If provided, only return documents matching these codes

    Returns:
        Filtered list of document dicts
    """
    if codes:
        code_set = {c.upper() for c in codes}
        return [d for d in docs if d["code"].upper() in code_set]

    if key_only:
        return [d for d in docs if d["code"] in KEY_DOC_CODES]

    return docs


def list_documents(app_number: str, key_only: bool = False,
                   codes: list = None, as_json: bool = False) -> str:
    """List documents for an application.

    Args:
        app_number: Application number
        key_only: If True, only show key prosecution documents
        codes: If provided, only show specific document codes
        as_json: If True, return raw JSON

    Returns:
        Formatted string listing documents
    """
    raw_docs = fetch_all_documents(app_number)
    parsed = [_parse_doc(d) for d in raw_docs]
    filtered = filter_documents(parsed, key_only=key_only, codes=codes)

    if as_json:
        return json.dumps([d["raw"] for d in filtered], indent=2)

    clean = _clean_app_number(app_number)
    lines = []
    filter_label = ""
    if key_only:
        filter_label = " (key prosecution documents only)"
    elif codes:
        filter_label = f" (filtered: {', '.join(codes)})"

    lines.append(f"Documents for application {clean}{filter_label}")
    lines.append(f"Total: {len(filtered)} of {len(parsed)} documents\n")

    for i, doc in enumerate(filtered, 1):
        desc = doc["description"] or doc["code"]
        date_str = f"  {doc['date']}" if doc["date"] else ""
        direction = f"  [{doc['direction']}]" if doc["direction"] else ""
        pages = f"  ({doc['page_count']} pages)" if doc["page_count"] else ""
        lines.append(f"  {i:3d}. [{doc['code']:8s}]{date_str}{direction}  {desc}{pages}")

    return "\n".join(lines)


def download_documents(app_number: str, output_dir: str = None,
                       key_only: bool = True, all_docs: bool = False,
                       codes: list = None) -> dict:
    """Download prosecution documents for an application.

    Args:
        app_number: Application number
        output_dir: Output directory (default: downloads/{appNumber}/)
        key_only: If True (default), only download key prosecution docs
        all_docs: If True, download all documents
        codes: If provided, only download documents matching these codes

    Returns:
        Dict with download summary: total, downloaded, skipped, failed
    """
    client = get_client()
    clean = _clean_app_number(app_number)

    # Determine output directory
    if output_dir:
        dest = Path(output_dir)
    else:
        dest = Path("downloads") / clean
    dest.mkdir(parents=True, exist_ok=True)

    # Fetch and filter documents
    raw_docs = fetch_all_documents(app_number)
    parsed = [_parse_doc(d) for d in raw_docs]

    if codes:
        filtered = filter_documents(parsed, codes=codes)
    elif all_docs:
        filtered = parsed
    else:
        filtered = filter_documents(parsed, key_only=key_only)

    total = len(filtered)
    downloaded = 0
    skipped = 0
    failed = 0
    errors = []

    print(f"Downloading {total} documents for application {clean}")
    print(f"Output directory: {dest.resolve()}\n")

    for i, doc in enumerate(filtered, 1):
        # Build filename: date_code_id.pdf
        # Strip time portion from ISO timestamps (keep YYYY-MM-DD only)
        date_part = doc["date"][:10] if doc["date"] else "unknown-date"
        code_part = doc["code"] if doc["code"] else "UNKNOWN"
        id_part = doc["id"] if doc["id"] else f"doc{i}"
        filename = f"{date_part}_{code_part}_{id_part}.pdf"
        # Sanitize filename
        filename = "".join(c if c.isalnum() or c in "-_." else "_" for c in filename)
        filepath = dest / filename

        desc = doc["description"] or doc["code"]

        # Skip if already downloaded
        if filepath.exists() and filepath.stat().st_size > 0:
            print(f"  [{i}/{total}] Skipping {desc} ({doc['date']}) — already exists")
            skipped += 1
            continue

        print(f"  [{i}/{total}] Downloading {desc} ({doc['date']})...")

        # Use download URL from API response, fall back to constructed URL
        download_url = doc.get("download_url", "")
        if not download_url:
            download_url = (
                f"{client.ODP_BASE}/api/v1/download/applications/{clean}"
                f"/{doc['id']}.pdf"
            )

        try:
            client.download_file(download_url, str(filepath))
            size_kb = filepath.stat().st_size / 1024
            print(f"           Saved: {filename} ({size_kb:.0f} KB)")
            downloaded += 1
        except APIError as e:
            print(f"           FAILED: {e}")
            errors.append({"document": desc, "date": doc["date"], "error": str(e)})
            failed += 1
            # Clean up partial file
            if filepath.exists():
                filepath.unlink()

    print(f"\nDone: {downloaded} downloaded, {skipped} skipped, {failed} failed")

    return {
        "total": total,
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
        "output_dir": str(dest.resolve()),
    }


def main():
    parser = argparse.ArgumentParser(
        description="List and download USPTO prosecution file wrapper documents"
    )
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of formatted text")
    sub = parser.add_subparsers(dest="command")

    # list subcommand
    p_list = sub.add_parser("list", help="List available documents")
    p_list.add_argument("app_number", help="Application number (e.g. 16123456)")
    p_list.add_argument("--key-only", action="store_true",
                        help="Show only key prosecution documents")
    p_list.add_argument("--codes",
                        help="Comma-separated document codes to filter (e.g. CTNF,CTFR)")

    # download subcommand
    p_dl = sub.add_parser("download", help="Download documents")
    p_dl.add_argument("app_number", help="Application number (e.g. 16123456)")
    p_dl.add_argument("--all", action="store_true", dest="all_docs",
                      help="Download all documents (default: key docs only)")
    p_dl.add_argument("--codes",
                      help="Comma-separated document codes (e.g. CTNF,CTFR)")
    p_dl.add_argument("-o", "--output-dir",
                      help="Output directory (default: downloads/{appNumber}/)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "list":
            codes = args.codes.split(",") if args.codes else None
            output = list_documents(
                args.app_number,
                key_only=args.key_only,
                codes=codes,
                as_json=args.json,
            )
            print(output)

        elif args.command == "download":
            codes = args.codes.split(",") if args.codes else None
            result = download_documents(
                args.app_number,
                output_dir=args.output_dir,
                all_docs=args.all_docs,
                codes=codes,
            )
            if args.json:
                print(json.dumps(result, indent=2))

    except APIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
