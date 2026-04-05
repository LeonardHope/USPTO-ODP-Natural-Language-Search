"""
USPTO API Client - Shared authentication, rate limiting, and retry logic.

This module provides a unified client for all USPTO Open Data Portal APIs:
- Patent File Wrapper API (search, sub-resources)
- PTAB Trials, Appeals, Interferences APIs
- Petition Decisions API
- Office Action DSAPI (Rejections, Citations, Text, Enriched Citations)
- Bulk Datasets API
- TSDR (Trademark Status & Document Retrieval) API

API keys are loaded from a .env file in the project root (via python-dotenv)
or from environment variables. They are never logged, printed, or stored in
source code.

Environment variables / .env keys:
    USPTO_ODP_API_KEY       - Key for all ODP and TSDR APIs
"""

import os
import sys
import time
import json
import logging
from collections import deque
from pathlib import Path

# Load .env from project root (one level above scripts/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")
except ImportError:
    pass  # python-dotenv not installed; fall back to env vars only

try:
    import requests
except ImportError:
    print("Error: 'requests' library is required. Install with: pip install -r requirements.txt")
    sys.exit(1)

logger = logging.getLogger("uspto_client")


class RateLimiter:
    """Token bucket rate limiter tracking calls within a sliding window."""

    def __init__(self, max_calls: int, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window = window_seconds
        self.calls: deque = deque()

    def wait_if_needed(self):
        """Block until a request slot is available."""
        now = time.time()
        # Remove calls outside the window
        while self.calls and self.calls[0] < now - self.window:
            self.calls.popleft()
        if len(self.calls) >= self.max_calls:
            sleep_time = self.calls[0] + self.window - now + 0.1
            if sleep_time > 0:
                logger.info(f"Rate limit reached. Waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)
        self.calls.append(time.time())


class APIError(Exception):
    """Raised when an API request fails after retries."""

    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class USPTOClient:
    """Unified client for all USPTO Open Data Portal APIs.

    Handles authentication, rate limiting, and retries for:
    - Open Data Portal (api.uspto.gov) — Patent File Wrapper, PTAB, Petitions,
      Office Actions, Bulk Data
    - TSDR (tsdrapi.uspto.gov) — Trademark Status & Document Retrieval
    """

    # Base URLs
    ODP_BASE = "https://api.uspto.gov"
    TSDR_BASE = "https://tsdrapi.uspto.gov"

    # Rate limits — ODP uses burst:1 (no parallel requests) and weekly caps.
    # We enforce per-minute limits that stay well within the weekly caps.
    RATE_LIMITS = {
        "odp": 30,            # Meta data calls — conservative to stay within burst:1
        "odp_download": 4,    # PDF/ZIP downloads are heavily rate-limited
        "tsdr": 30,           # TSDR API
    }

    def __init__(self):
        self.odp_key = os.environ.get("USPTO_ODP_API_KEY", "")
        # TSDR uses a separate API key registered at account.uspto.gov.
        # Falls back to the ODP key if not set (for users whose ODP key
        # has been activated for TSDR).
        self.tsdr_key = os.environ.get("USPTO_TSDR_API_KEY", "") or self.odp_key

        self._limiters = {
            name: RateLimiter(limit) for name, limit in self.RATE_LIMITS.items()
        }
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "User-Agent": "uspto-odp-search-skill/2.0",
        })

    # ── Credential checks ──────────────────────────────────────────────

    def require_odp_key(self):
        if not self.odp_key:
            raise APIError(
                "[SETUP_REQUIRED] USPTO_ODP_API_KEY is not set.\n"
                "Run: python3 get_started.py   (from the project root)\n"
                "Or get a free key at: https://data.uspto.gov/apis/getting-started"
            )

    def require_tsdr_key(self):
        if not self.tsdr_key:
            raise APIError(
                "[SETUP_REQUIRED] USPTO_TSDR_API_KEY is not set.\n"
                "TSDR requires a separate API key from the ODP key.\n"
                "Register for one at: https://account.uspto.gov/api-manager\n"
                "Then add USPTO_TSDR_API_KEY=your_key to your .env file."
            )

    # ── Core request method ─────────────────────────────────────────────

    def _request(
        self,
        api: str,
        method: str,
        url: str,
        params: dict = None,
        json_body: dict = None,
        data: dict = None,
        headers: dict = None,
        max_retries: int = 3,
        timeout: int = 30,
    ) -> dict:
        """Make an authenticated, rate-limited request with retry logic.

        Args:
            api: One of 'odp', 'odp_download', 'tsdr'
            method: 'GET' or 'POST'
            url: Full request URL
            params: Query parameters
            json_body: JSON request body (for POST with JSON)
            data: Form-encoded body (for POST with form data)
            headers: Additional headers to merge
            max_retries: Number of retries on transient errors
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON response as dict

        Raises:
            APIError: If the request fails after all retries
        """
        # Set auth header based on API
        req_headers = {}
        if api == "tsdr":
            self.require_tsdr_key()
            req_headers["USPTO-API-KEY"] = self.tsdr_key
        else:
            self.require_odp_key()
            req_headers["X-API-KEY"] = self.odp_key
        if headers:
            req_headers.update(headers)

        limiter = self._limiters.get(api)

        last_error = None
        for attempt in range(max_retries):
            if limiter:
                limiter.wait_if_needed()

            try:
                resp = self._session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_body,
                    data=data,
                    headers=req_headers,
                    timeout=timeout,
                )

                if resp.status_code == 200:
                    content_type = resp.headers.get("Content-Type", "")
                    if "xml" in content_type:
                        return {"raw_xml": resp.text, "status_code": 200}
                    try:
                        return resp.json()
                    except json.JSONDecodeError:
                        return {"raw_text": resp.text}

                if resp.status_code == 429:
                    wait = 2 ** attempt * 5
                    logger.warning(f"Rate limited (429). Retrying in {wait}s...")
                    time.sleep(wait)
                    continue

                if resp.status_code >= 500:
                    wait = 2 ** attempt * 2
                    logger.warning(
                        f"Server error ({resp.status_code}). Retrying in {wait}s..."
                    )
                    time.sleep(wait)
                    continue

                # Client errors (4xx except 429) — don't retry
                raise APIError(
                    f"API returned {resp.status_code}: {resp.text[:500]}",
                    status_code=resp.status_code,
                    response_body=resp.text[:2000],
                )

            except requests.exceptions.Timeout:
                last_error = f"Request timed out after {timeout}s"
                logger.warning(f"{last_error}. Attempt {attempt + 1}/{max_retries}")
            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error: {e}"
                logger.warning(f"{last_error}. Attempt {attempt + 1}/{max_retries}")
            except APIError:
                raise

            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

        raise APIError(f"Request failed after {max_retries} attempts. Last error: {last_error}")

    # ── ODP convenience methods ─────────────────────────────────────────

    def odp_get(self, path: str, params: dict = None) -> dict:
        """Query the Open Data Portal API (GET).

        Args:
            path: API path, e.g. '/api/v1/patent/applications/16123456'
            params: Query parameters
        """
        url = f"{self.ODP_BASE}{path}"
        return self._request("odp", "GET", url, params=params)

    def odp_post(self, path: str, json_body: dict = None, data: dict = None) -> dict:
        """POST to Open Data Portal API.

        Args:
            path: API path
            json_body: JSON request body
            data: Form-encoded body (for DSAPI endpoints)
        """
        url = f"{self.ODP_BASE}{path}"
        return self._request("odp", "POST", url, json_body=json_body, data=data)

    # ── TSDR convenience methods ────────────────────────────────────────

    def tsdr_get(self, path: str, params: dict = None) -> dict:
        """Query the TSDR (Trademark) API.

        Args:
            path: API path, e.g. '/ts/cd/casestatus/sn88123456/info'
            params: Query parameters
        """
        url = f"{self.TSDR_BASE}{path}"
        return self._request("tsdr", "GET", url, params=params)

    # ── File download ──────────────────────────────────────────────────

    def download_file(self, url: str, dest_path: str, api: str = "odp_download",
                      max_retries: int = 3, timeout: int = 120) -> bool:
        """Download a file with authentication and rate limiting.

        Uses the odp_download rate limiter (4 req/min) for PDF/ZIP downloads.

        Args:
            url: Full download URL
            dest_path: Local file path to write to
            api: Rate limiter to use ('odp_download' or 'tsdr')
            max_retries: Number of retries on transient errors
            timeout: Request timeout in seconds

        Returns:
            True if download succeeded

        Raises:
            APIError: If the download fails after all retries
        """
        headers = {"Accept": "application/pdf"}
        if api == "tsdr":
            self.require_tsdr_key()
            headers["USPTO-API-KEY"] = self.tsdr_key
        else:
            self.require_odp_key()
            headers["X-API-KEY"] = self.odp_key
        limiter = self._limiters.get(api, self._limiters.get("odp_download"))

        last_error = None
        for attempt in range(max_retries):
            if limiter:
                limiter.wait_if_needed()

            try:
                resp = self._session.get(
                    url, headers=headers, timeout=timeout, stream=True
                )

                if resp.status_code == 200:
                    with open(dest_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                    return True

                if resp.status_code == 429:
                    wait = 2 ** attempt * 5
                    logger.warning(f"Rate limited (429). Retrying in {wait}s...")
                    time.sleep(wait)
                    continue

                if resp.status_code >= 500:
                    wait = 2 ** attempt * 2
                    logger.warning(
                        f"Server error ({resp.status_code}). Retrying in {wait}s..."
                    )
                    time.sleep(wait)
                    continue

                raise APIError(
                    f"Download failed with {resp.status_code}: {resp.text[:500]}",
                    status_code=resp.status_code,
                    response_body=resp.text[:2000],
                )

            except requests.exceptions.Timeout:
                last_error = f"Download timed out after {timeout}s"
                logger.warning(f"{last_error}. Attempt {attempt + 1}/{max_retries}")
            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error: {e}"
                logger.warning(f"{last_error}. Attempt {attempt + 1}/{max_retries}")
            except APIError:
                raise

            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

        raise APIError(f"Download failed after {max_retries} attempts. Last error: {last_error}")

    # ── Utility ─────────────────────────────────────────────────────────

    def check_keys(self) -> dict:
        """Check which API keys are configured (without revealing them).

        Returns:
            Dict with boolean flags for each key.
        """
        tsdr_explicit = bool(os.environ.get("USPTO_TSDR_API_KEY", ""))
        return {
            "odp_key_set": bool(self.odp_key),
            "tsdr_key_set": tsdr_explicit or bool(self.odp_key),
            "tsdr_key_explicit": tsdr_explicit,
        }


def _run_setup_wizard():
    """Launch the interactive setup wizard to configure API keys."""
    import subprocess
    setup_script = _PROJECT_ROOT / "get_started.py"
    if not setup_script.exists():
        return False
    print("\nAPI keys not configured. Launching setup wizard...\n")
    result = subprocess.run([sys.executable, str(setup_script)])
    if result.returncode == 0:
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=_PROJECT_ROOT / ".env", override=True)
        except ImportError:
            pass
        return True
    return False


def clean_patent_number(patent_number: str) -> str:
    """Clean a patent number to digits only (or with prefix for design/reissue).

    Accepts: '10,000,000', 'US10000000', 'US 10,000,000', 'RE49000', 'D900000'
    Returns: '10000000', 'RE49000', 'D900000'
    """
    s = patent_number.strip()
    if s.upper().startswith("US"):
        s = s[2:].strip()
    s = s.replace(",", "")
    return s


def clean_app_number(application_number: str) -> str:
    """Clean an application number to digits only.

    Accepts: '16/123,456', '16123456', '16,123,456'
    Returns: '16123456'
    """
    return application_number.replace("/", "").replace(",", "").replace(" ", "").strip()


def resolve_patent_to_app_number(patent_number: str) -> str:
    """Resolve a patent number to its application number via ODP search.

    Args:
        patent_number: Granted patent number (e.g. '9876543', 'US10,000,000')

    Returns:
        Application number string, or None if not found
    """
    client = get_client()
    clean = clean_patent_number(patent_number)
    try:
        result = client.odp_get(
            "/api/v1/patent/applications/search",
            params={"q": clean, "limit": 5}
        )
        apps = result.get("patentFileWrapperDataBag", [])
        for app in apps:
            meta = app.get("applicationMetaData", {})
            if meta.get("patentNumber") == clean:
                return app.get("applicationNumberText", "")
        if apps:
            logger.warning(
                f"No exact patent number match for '{clean}'; "
                f"using first search result (app {apps[0].get('applicationNumberText', '?')})"
            )
            return apps[0].get("applicationNumberText", "")
    except APIError:
        pass
    return None


def get_client() -> 'USPTOClient':
    """Get a configured USPTOClient instance.

    On first use, if the ODP key is missing and stdin is interactive,
    automatically launches the setup wizard.
    """
    client = USPTOClient()
    status = client.check_keys()
    if not status["odp_key_set"] and sys.stdin.isatty():
        if _run_setup_wizard():
            client = USPTOClient()  # recreate with new keys
    return client


if __name__ == "__main__":
    client = get_client()
    status = client.check_keys()
    print("API Key Status:")
    for key, is_set in status.items():
        icon = "OK" if is_set else "MISSING"
        print(f"  {key}: {icon}")
    if not status["odp_key_set"]:
        print("\n[SETUP_REQUIRED] Run: python3 get_started.py")
        sys.exit(1)
