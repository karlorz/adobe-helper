"""
URL constants for Adobe Helper

This module contains all API endpoints and URLs used by the library.
Note: Many of these URLs are placeholders and will be updated after
network analysis during actual PDF upload on Adobe's website.
"""

import json
import logging
import os
from pathlib import Path

from adobe.constants import DEFAULT_SESSION_DIR

# Base URLs
ADOBE_BASE_URL = "https://www.adobe.com"
ADOBE_ACROBAT_BASE = "https://acroipm2.adobe.com"
ADOBE_IMS_BASE = "https://adobeid-na1.services.adobe.com"

# Public-facing pages
PDF_TO_WORD_PAGE = f"{ADOBE_BASE_URL}/acrobat/online/pdf-to-word.html"
PDF_TO_EXCEL_PAGE = f"{ADOBE_BASE_URL}/acrobat/online/pdf-to-excel.html"
PDF_TO_PPT_PAGE = f"{ADOBE_BASE_URL}/acrobat/online/pdf-to-ppt.html"

# Unity Workflow System
UNITY_WORKFLOW_BASE = f"{ADOBE_BASE_URL}/unitylibs/core/workflow"
UNITY_WORKFLOW_JS = f"{UNITY_WORKFLOW_BASE}/workflow.js"
UNITY_WORKFLOW_ACROBAT = f"{UNITY_WORKFLOW_BASE}/workflow-acrobat"
UNITY_TARGET_CONFIG = f"{UNITY_WORKFLOW_ACROBAT}/target-config.json"
UNITY_ACTION_BINDER = f"{UNITY_WORKFLOW_ACROBAT}/action-binder.js"

# Acrobat Web Services
ACROBAT_WEB_BASE = f"{ADOBE_ACROBAT_BASE}/acrobat-web"
ACROBAT_MACHINE_BASE = f"{ACROBAT_WEB_BASE}/machine"
ACROBAT_UNITY_DC = f"{ACROBAT_MACHINE_BASE}/unity-dc-frictionless"

# API Endpoints (to be discovered through network analysis)
# These are hypothetical and will be updated after actual testing
API_BASE = f"{ADOBE_BASE_URL}/dc-api"
API_UPLOAD = f"{API_BASE}/upload"
API_CONVERT = f"{API_BASE}/convert"
API_STATUS = f"{API_BASE}/status"
API_DOWNLOAD = f"{API_BASE}/download"

# IMS (Identity Management Services)
IMS_AUTH = f"{ADOBE_IMS_BASE}/ims/authorize/v2"
IMS_TOKEN = f"{ADOBE_IMS_BASE}/ims/token/v3"
IMS_PROFILE = f"{ADOBE_IMS_BASE}/ims/profile/v1"
IMS_CHECK_TOKEN = f"{ADOBE_IMS_BASE}/ims/check/v6/token"

IMS_GUEST_CLIENT_ID = "dc-prod-virgoweb"
IMS_GUEST_SCOPE = (
    "AdobeID,openid,DCAPI,additional_info.account_type,additional_info.optionalAgreements,"
    "agreement_send,agreement_sign,sign_library_write,sign_user_read,sign_user_write,"
    "agreement_read,agreement_write,widget_read,widget_write,workflow_read,workflow_write,"
    "sign_library_read,sign_user_login,sao.ACOM_ESIGN_TRIAL,ee.dcweb"
)
IMS_JSL_VERSION = "v1-v0.49.0-1-g118f48c"
IMS_REFERER = PDF_TO_WORD_PAGE
IMS_ORIGIN = "https://www.adobe.com"

# Headers
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Alternative user agents for session rotation
USER_AGENTS = [
    # macOS Chrome
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36",
    # Windows Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36",
    # Linux Chrome
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36",
]

# Common headers
COMMON_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
}

# Headers required when performing the initial navigation request to the
# public PDF-to-Word page. Adobe's edge infrastructure expects a modern
# browser fingerprint when the Chrome user agent is advertised; without
# these Client Hints the server responds with an HTTP/2 protocol error.
SESSION_INIT_HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9," "image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "sec-ch-ua": '"Chromium";v="120", "Not=A?Brand";v="8", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}


logger = logging.getLogger(__name__)

_ENDPOINT_ENV_VARS = {
    "upload": "ADOBE_HELPER_UPLOAD_URL",
    "conversion": "ADOBE_HELPER_CONVERSION_URL",
    "status": "ADOBE_HELPER_STATUS_URL",
    "download": "ADOBE_HELPER_DOWNLOAD_URL",
}

_CONFIG_ENV_VAR = "ADOBE_HELPER_ENDPOINTS_FILE"
_DISCOVERY_FILENAME = "discovered_endpoints.json"


def _extract_endpoint_url(entry) -> str | None:
    """Extract a URL string from a discovery entry."""

    if isinstance(entry, str) and entry.strip():
        return entry.strip()

    if isinstance(entry, dict):
        url = entry.get("url")
        if isinstance(url, str) and url.strip():
            return url.strip()

    return None


def _load_endpoints_from_file(config_path: Path) -> dict[str, str]:
    """Load endpoint URLs from the discovery JSON file."""

    try:
        with config_path.open("r", encoding="utf-8") as file:
            content = json.load(file)
    except FileNotFoundError:
        logger.debug("Endpoint discovery file not found: %s", config_path)
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read endpoint discovery file %s: %s", config_path, exc)
        return {}

    data = content.get("endpoints") if isinstance(content, dict) else None
    if not isinstance(data, dict):
        logger.warning(
            "Endpoint discovery file %s does not contain an 'endpoints' mapping",
            config_path,
        )
        return {}

    extracted: dict[str, str] = {}

    for key in ("upload", "conversion", "status", "download"):
        value = _extract_endpoint_url(data.get(key))
        if value:
            extracted[key] = value

    if extracted:
        logger.info("Loaded API endpoints from %s", config_path)

    return extracted


def _candidate_endpoint_files(explicit_path: str | Path | None = None) -> list[Path]:
    """Return candidate paths for the discovery JSON file."""

    candidates: list[Path] = []

    if explicit_path:
        candidates.append(Path(explicit_path).expanduser())

    env_path = os.environ.get(_CONFIG_ENV_VAR)
    if env_path:
        candidates.append(Path(env_path).expanduser())

    candidates.append(Path.cwd() / _DISCOVERY_FILENAME)
    package_root = Path(__file__).resolve().parent.parent
    candidates.append(package_root / _DISCOVERY_FILENAME)
    home_config = Path.home() / DEFAULT_SESSION_DIR / _DISCOVERY_FILENAME
    candidates.append(home_config)

    unique_candidates: list[Path] = []
    seen: set[Path | str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            resolved = candidate
        if resolved not in seen:
            seen.add(resolved)
            unique_candidates.append(candidate)

    return unique_candidates


def _load_configured_endpoints(config_path: str | Path | None = None) -> dict[str, str]:
    for candidate in _candidate_endpoint_files(config_path):
        if candidate.is_file():
            loaded = _load_endpoints_from_file(candidate)
            if loaded:
                return loaded
    return {}


def _load_env_overrides() -> dict[str, str]:
    overrides: dict[str, str] = {}

    for key, env_var in _ENDPOINT_ENV_VARS.items():
        value = os.environ.get(env_var)
        if isinstance(value, str) and value.strip():
            overrides[key] = value.strip()

    if overrides:
        logger.info("Loaded API endpoint overrides from environment variables")

    return overrides


def get_api_endpoints(config_path: str | Path | None = None) -> dict[str, str]:
    """Return API endpoint URLs with optional overrides."""

    endpoints = {
        "upload": API_UPLOAD,
        "conversion": API_CONVERT,
        "status": API_STATUS,
        "download": API_DOWNLOAD,
    }

    endpoints.update(_load_configured_endpoints(config_path))
    endpoints.update(_load_env_overrides())

    return endpoints
