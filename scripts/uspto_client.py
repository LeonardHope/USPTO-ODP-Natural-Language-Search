"""
USPTO API Client - Shared authentication, rate limiting, and retry logic.

This module provides a unified client for all USPTO APIs:
- PatentsView PatentSearch API
- USPTO Open Data Portal (ODP) APIs
- Legacy Developer Portal APIs (Office Actions, Assignments)

API keys are loaded from a .env file in the project root (via python-dotenv)
or from environment variables. They are never logged, printed, or stored in
source code.

Environment variables / .env keys:
    USPTO_ODP_API_KEY       - Key for Open Data Portal APIs
    PATENTSVIEW_API_KEY     - Key for PatentsView PatentSearch API
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
    """Unified client for all USPTO APIs.

    Handles authentication, rate limiting, and retries for:
    - PatentsView (search.patentsview.org)
    - Open Data Portal (data.uspto.gov)
    - Legacy Developer APIs (developer.uspto.gov)
    """

    # Base URLs
    PATENTSVIEW_BASE = "https://search.patentsview.org/api/v1"
    ODP_BASE = "https://api.uspto.gov"
    LEGACY_BASE = "https://developer.uspto.gov/ds-api"

    # Rate limits per API (requests per minute)
    RATE_LIMITS = {
        "patentsview": 45,
        "odp": 60,
        "odp_download": 4,  # PDF/ZIP downloads are heavily rate-limited
        "legacy": 60,
    }

    def __init__(self):
        self.odp_key = os.environ.get("USPTO_ODP_API_KEY", "")
        self.pv_key = os.environ.get("PATENTSVIEW_API_KEY", "")

        self._limiters = {
            name: RateLimiter(limit) for name, limit in self.RATE_LIMITS.items()
        }
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "User-Agent": "uspto-patent-search-skill/1.0",
        })

    # ── Credential checks ──────────────────────────────────────────────

    def require_patentsview_key(self):
        if not self.pv_key:
            raise APIError(
                "[SETUP_REQUIRED] PATENTSVIEW_API_KEY is not set.\n"
                "Run: python3 get_started.py   (from the project root)\n"
                "Or get a free key at: https://patentsview.org/apis/keyrequest"
            )

    def require_odp_key(self):
        if not self.odp_key:
            raise APIError(
                "[SETUP_REQUIRED] USPTO_ODP_API_KEY is not set.\n"
                "Run: python3 get_started.py   (from the project root)\n"
                "Or get a free key at: https://data.uspto.gov/apis/getting-started"
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
        max_retries: int = 3,
        timeout: int = 30,
    ) -> dict:
        """Make an authenticated, rate-limited request with retry logic.

        Args:
            api: One of 'patentsview', 'odp', 'legacy', 'assignment'
            method: 'GET' or 'POST'
            url: Full request URL
            params: Query parameters
            json_body: JSON request body (for POST with JSON)
            data: Form-encoded body (for POST with form data)
            max_retries: Number of retries on transient errors
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON response as dict

        Raises:
            APIError: If the request fails after all retries
        """
        # Set auth header based on API
        headers = {}
        if api == "patentsview":
            self.require_patentsview_key()
            headers["X-Api-Key"] = self.pv_key
        elif api in ("odp", "odp_download", "legacy"):
            self.require_odp_key()
            headers["X-Api-Key"] = self.odp_key

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
                    headers=headers,
                    timeout=timeout,
                )

                if resp.status_code == 200:
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

    # ── PatentsView convenience methods ─────────────────────────────────

    def patentsview_get(self, endpoint: str, q: dict, f: list = None,
                        s: list = None, o: dict = None) -> dict:
        """Query the PatentsView API.

        Args:
            endpoint: e.g. 'patent', 'inventor', 'assignee', 'patent/us_patent_citation'
            q: Query dict using PatentsView operators (_eq, _contains, _text_any, etc.)
            f: List of fields to return
            s: Sort specification, e.g. [{"patent_date": "desc"}]
            o: Options dict, e.g. {"size": 25}

        Returns:
            API response dict with results
        """
        url = f"{self.PATENTSVIEW_BASE}/{endpoint}/"
        params = {"q": json.dumps(q)}
        if f:
            params["f"] = json.dumps(f)
        if s:
            params["s"] = json.dumps(s)
        if o:
            params["o"] = json.dumps(o)
        return self._request("patentsview", "GET", url, params=params)

    def patentsview_post(self, endpoint: str, body: dict) -> dict:
        """POST to PatentsView API (for complex queries)."""
        url = f"{self.PATENTSVIEW_BASE}/{endpoint}/"
        return self._request("patentsview", "POST", url, json_body=body)

    # ── ODP convenience methods ─────────────────────────────────────────

    def odp_get(self, path: str, params: dict = None) -> dict:
        """Query the Open Data Portal API.

        Args:
            path: API path, e.g. '/api/v1/patent/application/16123456'
            params: Query parameters
        """
        url = f"{self.ODP_BASE}{path}"
        return self._request("odp", "GET", url, params=params)

    def odp_post(self, path: str, json_body: dict = None, data: dict = None) -> dict:
        """POST to Open Data Portal API."""
        url = f"{self.ODP_BASE}{path}"
        return self._request("odp", "POST", url, json_body=json_body, data=data)

    # ── Legacy Developer API convenience methods ────────────────────────

    def legacy_post(self, dataset: str, version: str, criteria: str,
                    start: int = 0, rows: int = 100) -> dict:
        """Query a Legacy Developer Portal API using Lucene syntax.

        Args:
            dataset: e.g. 'oa_actions', 'oa_rejections', 'enriched_cited_reference_metadata'
            version: e.g. 'v1', 'v2', '1'
            criteria: Lucene query string, e.g. 'patent_number:7123456'
            start: Starting record offset
            rows: Number of records to return (max varies by API)
        """
        url = f"{self.LEGACY_BASE}/{dataset}/{version}/records"
        form_data = {
            "criteria": criteria,
            "start": str(start),
            "rows": str(rows),
        }
        return self._request("legacy", "POST", url, data=form_data)

    def legacy_get_fields(self, dataset: str, version: str) -> dict:
        """Get available searchable fields for a Legacy API dataset."""
        url = f"{self.LEGACY_BASE}/{dataset}/{version}/fields"
        return self._request("legacy", "GET", url)

    # ── File download ──────────────────────────────────────────────────

    def download_file(self, url: str, dest_path: str, max_retries: int = 3,
                      timeout: int = 120) -> bool:
        """Download a file from the ODP API with authentication and rate limiting.

        Uses the odp_download rate limiter (4 req/min) for PDF/ZIP downloads.

        Args:
            url: Full download URL
            dest_path: Local file path to write to
            max_retries: Number of retries on transient errors
            timeout: Request timeout in seconds

        Returns:
            True if download succeeded

        Raises:
            APIError: If the download fails after all retries
        """
        self.require_odp_key()
        headers = {
            "X-Api-Key": self.odp_key,
            "Accept": "application/pdf",
        }
        limiter = self._limiters.get("odp_download")

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
        return {
            "odp_key_set": bool(self.odp_key),
            "patentsview_key_set": bool(self.pv_key),
        }


def _run_setup_wizard():
    """Launch the interactive setup wizard to configure API keys."""
    import subprocess
    setup_script = _PROJECT_ROOT / "get_started.py"
    if not setup_script.exists():
        return False
    print("\nAPI keys not configured. Launching setup wizard...\n")
    # Use the system python (not venv) so the wizard can bootstrap the venv itself
    result = subprocess.run([sys.executable, str(setup_script)])
    if result.returncode == 0:
        # Reload .env after wizard completes
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=_PROJECT_ROOT / ".env", override=True)
        except ImportError:
            pass
        return True
    return False


def resolve_patent_to_app_number(patent_number: str) -> str:
    """Resolve a patent number to its application number via ODP search.

    Args:
        patent_number: Granted patent number (e.g. '9876543', 'US10,000,000')

    Returns:
        Application number string, or None if not found
    """
    client = get_client()
    clean = patent_number.replace(",", "").replace("US", "").strip()
    try:
        result = client.odp_get(
            "/api/v1/patent/applications/search",
            params={"q": clean, "rows": 5}
        )
        apps = result.get("patentFileWrapperDataBag", result.get("results", []))
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


def get_client() -> USPTOClient:
    """Get a configured USPTOClient instance.

    On first use, if API keys are missing and stdin is interactive,
    automatically launches the setup wizard.
    """
    client = USPTOClient()
    status = client.check_keys()
    if not all(status.values()) and sys.stdin.isatty():
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
    if not all(status.values()):
        print("\n[SETUP_REQUIRED] Run: python3 get_started.py")
        sys.exit(1)
