"""
Utility functions for Adobe Helper

This module contains helper functions used throughout the library.
"""

import hashlib
import json
import random
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

from adobe.constants import PDF_MAGIC_BYTES
from adobe.urls import USER_AGENTS


def validate_pdf_file(file_path: Path) -> bool:
    """
    Validate that a file is a valid PDF

    Args:
        file_path: Path to the file to validate

    Returns:
        True if the file is a valid PDF, False otherwise
    """
    if not file_path.exists():
        return False

    if not file_path.is_file():
        return False

    # Check file extension
    if not file_path.name.lower().endswith(".pdf"):
        return False

    # Check PDF magic bytes
    try:
        with open(file_path, "rb") as f:
            header = f.read(5)
            return header == PDF_MAGIC_BYTES
    except OSError:
        return False


def calculate_file_checksum(file_path: Path) -> str:
    """
    Calculate MD5 checksum of a file

    Args:
        file_path: Path to the file

    Returns:
        Hexadecimal MD5 checksum string
    """
    md5_hash = hashlib.md5()

    with open(file_path, "rb") as f:
        # Read in chunks to handle large files
        for chunk in iter(lambda: f.read(8192), b""):
            md5_hash.update(chunk)

    return md5_hash.hexdigest()


def get_random_user_agent() -> str:
    """
    Get a random user agent string for session rotation

    Returns:
        Random user agent string
    """
    return random.choice(USER_AGENTS)


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing/replacing invalid characters

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for filesystem
    """
    # Replace invalid characters with underscore
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")

    # Remove leading/trailing spaces and dots
    filename = filename.strip(". ")

    # Ensure filename is not empty
    if not filename:
        filename = "unnamed"

    return filename


def generate_output_filename(input_path: Path, output_format: str = "docx") -> Path:
    """
    Generate output filename from input PDF path

    Args:
        input_path: Path to input PDF file
        output_format: Output format extension (without dot)

    Returns:
        Path to output file
    """
    # Get the directory and base name
    directory = input_path.parent
    base_name = input_path.stem

    # Create output filename
    output_name = f"{base_name}.{output_format}"

    return directory / output_name


def ensure_directory_exists(directory: Path) -> None:
    """
    Ensure a directory exists, creating it if necessary

    Args:
        directory: Path to directory
    """
    directory.mkdir(parents=True, exist_ok=True)


def human_readable_time(seconds: float) -> str:
    """
    Convert seconds to human-readable time format

    Args:
        seconds: Time in seconds

    Returns:
        Formatted time string (e.g., "2m 30s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60

    if minutes < 60:
        return f"{minutes}m {remaining_seconds:.0f}s"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    return f"{hours}h {remaining_minutes}m"


def extract_csrf_token(html: str) -> str | None:
    """
    Extract CSRF token from HTML response

    Args:
        html: HTML content

    Returns:
        CSRF token if found, None otherwise
    """
    # Try to find CSRF token in meta tags
    import re

    # Pattern for meta tag: <meta name="csrf-token" content="...">
    meta_pattern = r'<meta\s+name=["\']csrf-token["\']\s+content=["\'](.*?)["\']'
    match = re.search(meta_pattern, html, re.IGNORECASE)

    if match:
        return match.group(1)

    # Pattern for hidden input: <input type="hidden" name="csrf_token" value="...">
    input_pattern = (
        r'<input\s+type=["\']hidden["\']\s+name=["\']csrf[_-]?token["\']\s+value=["\'](.*?)["\']'
    )
    match = re.search(input_pattern, html, re.IGNORECASE)

    if match:
        return match.group(1)

    # Pattern for JavaScript variable: var csrfToken = "...";
    js_pattern = r'var\s+csrf[_-]?token\s*=\s*["\']([^"\']+)["\']'
    match = re.search(js_pattern, html, re.IGNORECASE)

    if match:
        return match.group(1)

    return None


def extract_session_id(cookies: dict[str, str]) -> str | None:
    """
    Extract session ID from cookies

    Args:
        cookies: Dictionary of cookies

    Returns:
        Session ID if found, None otherwise
    """
    # Common session cookie names
    session_keys = ["sessionid", "session_id", "JSESSIONID", "PHPSESSID", "session"]

    for key in session_keys:
        # Case-insensitive search
        for cookie_name, cookie_value in cookies.items():
            if cookie_name.lower() == key.lower():
                return cookie_value

    return None


def extract_asset_result(status_payload: dict) -> dict | None:
    """Return the asset_result section from a job status payload."""

    asset_result = (
        status_payload.get("asset_result")
        or status_payload.get("assetResult")
        or status_payload.get("assetResultList")
    )
    if isinstance(asset_result, list) and asset_result:
        first = asset_result[0]
        return first if isinstance(first, dict) else None
    if isinstance(asset_result, dict):
        return asset_result
    return None


def load_json_file(path: Path) -> dict:
    """Load a JSON file, returning an empty dict on failure."""

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def write_json_file(path: Path, payload: dict) -> None:
    """Write a JSON payload to disk with indentation."""

    ensure_directory_exists(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def generate_request_id(prefix: str = "cr") -> str:
    """Generate an Adobe-style request ID."""

    token = uuid.uuid4()
    return f"{prefix}-{token}"


def chunk_bytes(data: bytes, chunk_size: int) -> Iterator[bytes]:
    """Yield consecutive chunks from a bytes object."""

    for index in range(0, len(data), chunk_size):
        yield data[index : index + chunk_size]


def now_seconds() -> float:
    """Return the current time in seconds as a float."""

    return time.time()


def extract_tenant_id_from_token(access_token: str) -> str | None:
    """
    Extract tenant ID from Adobe IMS JWT access token

    Adobe JWT tokens contain a 'client_id' or 'user_id' field that can serve
    as the tenant identifier for API endpoints.

    Args:
        access_token: Adobe IMS JWT access token

    Returns:
        Tenant ID if found, None otherwise
    """
    if not access_token or not isinstance(access_token, str):
        return None

    try:
        import base64

        # JWT tokens have 3 parts separated by dots: header.payload.signature
        parts = access_token.split(".")
        if len(parts) != 3:
            return None

        # Decode the payload (second part)
        # Add padding if needed for base64 decoding
        payload_b64 = parts[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding

        payload_json = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_json)

        # Try to extract tenant-like identifiers
        # Adobe uses different fields: client_id, user_id, sub, etc.
        tenant_candidates = [
            payload.get("client_id"),
            payload.get("user_id"),
            payload.get("sub"),
            payload.get("tenant_id"),
            payload.get("org_id"),
        ]

        for candidate in tenant_candidates:
            if candidate and isinstance(candidate, str) and candidate.strip():
                return str(candidate.strip())

        return None

    except (ValueError, json.JSONDecodeError, KeyError):
        return None


def extract_tenant_from_ims_response(ims_response: dict) -> str | None:
    """
    Extract tenant ID from IMS authentication response

    Args:
        ims_response: IMS response dictionary

    Returns:
        Tenant ID if found, None otherwise
    """
    if not isinstance(ims_response, dict):
        return None

    # Try direct fields
    tenant_candidates = [
        ims_response.get("tenant_id"),
        ims_response.get("org_id"),
        ims_response.get("client_id"),
        ims_response.get("user_id"),
    ]

    for candidate in tenant_candidates:
        if candidate and isinstance(candidate, str) and candidate.strip():
            return str(candidate.strip())

    # Try extracting from access token
    access_token = ims_response.get("access_token")
    if access_token:
        tenant = extract_tenant_id_from_token(access_token)
        if tenant:
            return tenant

    return None
