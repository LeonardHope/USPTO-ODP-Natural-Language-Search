"""
USPTO Bulk Datasets API - Search module.

Provides functions for discovering and downloading bulk data products
from the USPTO Open Data Portal. Bulk datasets include patent grants,
applications, classifications, assignments, and other data in various
formats (XML, CSV, JSON).

API Base: https://api.uspto.gov
Auth: USPTO_ODP_API_KEY env var, sent as X-API-KEY header
Rate limit: 60 requests/minute (4/min for file downloads)

Endpoints:
- GET /api/v1/datasets/products/search?q=&offset=0&limit=25 — Search products
- GET /api/v1/datasets/products/{productIdentifier}          — Get product details
- GET /api/v1/datasets/products/files/{productIdentifier}/{fileName} — Download file

The download endpoint redirects to a signed S3 URL for the actual file.
Response format: BdssResponseBag with product data.
"""

import json
import logging
import sys
import argparse
from pathlib import Path

from uspto_client import get_client, APIError, clean_patent_number, clean_app_number

logger = logging.getLogger("bulk_data_search")


# ── Bulk Dataset Search ───────────────────────────────────────────────────

def search_bulk_datasets(query: str = None,
                         offset: int = 0,
                         limit: int = 25) -> dict:
    """Search available USPTO bulk data products.

    Searches the bulk data product catalog. Products include patent grants,
    applications, classifications, assignments, and other datasets available
    for bulk download.

    Args:
        query: Free-text search across product names and descriptions
        offset: Pagination offset
        limit: Results per page

    Returns:
        API response with matching bulk data products
    """
    client = get_client()
    params = {"offset": offset, "limit": limit}
    if query:
        params["q"] = query

    try:
        return client.odp_get("/api/v1/datasets/products/search", params=params)
    except APIError as e:
        if e.status_code == 404:
            return {"count": 0, "products": []}
        raise


def get_bulk_dataset(product_id: str) -> dict:
    """Get details for a specific bulk data product.

    Retrieves full metadata for a product identified by its shortName,
    including available files, formats, update frequency, and descriptions.

    Args:
        product_id: Product shortName identifier (e.g. 'PTGRXML')

    Returns:
        Product metadata including available files and descriptions
    """
    client = get_client()
    return client.odp_get(f"/api/v1/datasets/products/{product_id}")


def download_bulk_file(product_id: str, file_name: str,
                       dest_path: str) -> bool:
    """Download a specific file from a bulk data product.

    The API endpoint redirects to a signed S3 URL. The client follows
    the redirect and downloads the file with rate limiting.

    Args:
        product_id: Product shortName identifier
        file_name: Name of the file to download (from product's file list)
        dest_path: Local file path to save the download to

    Returns:
        True if download succeeded

    Raises:
        APIError: If the download fails
    """
    client = get_client()
    url = (
        f"{client.ODP_BASE}/api/v1/datasets/products/files"
        f"/{product_id}/{file_name}"
    )

    # Ensure destination directory exists
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)

    return client.download_file(url, dest_path)


# ── CLI interface ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Search and download USPTO Bulk Data products"
    )
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of formatted text")
    sub = parser.add_subparsers(dest="command")

    # search
    p_search = sub.add_parser("search", help="Search bulk data products")
    p_search.add_argument("--query", "-q", help="Free-text search")
    p_search.add_argument("--limit", type=int, default=25,
                          help="Results per page")

    # get product details
    p_get = sub.add_parser("get", help="Get details for a bulk data product")
    p_get.add_argument("product_id", help="Product shortName identifier")

    # download file
    p_dl = sub.add_parser("download", help="Download a file from a bulk data product")
    p_dl.add_argument("product_id", help="Product shortName identifier")
    p_dl.add_argument("file_name", help="File name to download")
    p_dl.add_argument("-o", "--output", default=None,
                      help="Output file path (default: ./{file_name})")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "search":
            result = search_bulk_datasets(
                query=args.query,
                limit=args.limit,
            )
        elif args.command == "get":
            result = get_bulk_dataset(args.product_id)
        elif args.command == "download":
            dest = args.output or args.file_name
            print(f"Downloading {args.file_name} from {args.product_id}...")
            download_bulk_file(args.product_id, args.file_name, dest)
            size_kb = Path(dest).stat().st_size / 1024
            print(f"Saved: {dest} ({size_kb:.0f} KB)")
            return
        else:
            parser.print_help()
            return

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if args.command == "search":
                count = result.get("count", 0)
                products = (result.get("bulkDataProductBag", [])
                            or result.get("products", []))
                print(f"Bulk Data Products: {count} result(s)\n")
                for i, prod in enumerate(products, 1):
                    name = (prod.get("productIdentifier", "")
                            or prod.get("shortName", ""))
                    title = (prod.get("productTitleText", "")
                             or prod.get("title", ""))
                    desc = (prod.get("productDescriptionText", "")
                            or prod.get("description", ""))
                    print(f"  {i}. {name}: {title}")
                    if desc:
                        print(f"     {desc[:120]}")
                    print()
            else:
                print(json.dumps(result, indent=2))

    except APIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
