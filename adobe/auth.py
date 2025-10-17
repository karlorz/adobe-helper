"""
Session and authentication management for Adobe Helper

This module handles session initialization, token management, and
authentication with Adobe's online services.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from secrets import token_hex

import httpx

from adobe.constants import (
    DEFAULT_SESSION_DIR,
    SESSION_EXPIRY_HOURS,
    SESSION_FILE,
    SESSION_INIT_TIMEOUT,
)
from adobe.exceptions import AuthenticationError
from adobe.models import SessionInfo
from adobe.urls import (
    DEFAULT_USER_AGENT,
    IMS_CHECK_TOKEN,
    IMS_GUEST_CLIENT_ID,
    IMS_GUEST_SCOPE,
    IMS_JSL_VERSION,
    IMS_ORIGIN,
    IMS_REFERER,
    PDF_TO_WORD_PAGE,
    SESSION_INIT_HEADERS,
)
from adobe.utils import extract_csrf_token, extract_session_id

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages sessions with Adobe's online conversion services

    Handles session initialization, token extraction, cookie management,
    and session persistence.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        session_dir: Path | None = None,
        auto_save: bool = True,
    ):
        """
        Initialize the session manager

        Args:
            client: HTTPX async client instance
            session_dir: Directory to store session data (default: ~/.adobe-helper)
            auto_save: Automatically save session data to disk
        """
        self.client = client
        self.session_dir = Path.home() / DEFAULT_SESSION_DIR if session_dir is None else session_dir
        self.auto_save = auto_save

        # Ensure session directory exists
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Session state
        self.session_info: SessionInfo | None = None
        self.csrf_token: str | None = None
        self.session_id: str | None = None
        self.access_token: str | None = None
        self.access_token_expires_at: datetime | None = None

    async def initialize(self) -> SessionInfo:
        """
        Initialize a new session by visiting Adobe's PDF-to-Word page

        Returns:
            SessionInfo with session details

        Raises:
            AuthenticationError: If session initialization fails
        """
        logger.info("Initializing Adobe session...")

        try:
            # Visit the main page to establish session
            # Merge navigation-specific headers with the active user agent;
            # httpx lowercases header names internally, so lookups must use
            # lowercase keys when reading from the client defaults.
            current_user_agent = self.client.headers.get("user-agent", DEFAULT_USER_AGENT)
            response = await self.client.get(
                PDF_TO_WORD_PAGE,
                headers={
                    **SESSION_INIT_HEADERS,
                    "User-Agent": current_user_agent,
                },
                timeout=SESSION_INIT_TIMEOUT,
                follow_redirects=True,
            )

            response.raise_for_status()

            # Extract tokens and session info
            html_content = response.text
            self.csrf_token = extract_csrf_token(html_content)

            # Extract cookies
            cookies = {cookie.name: cookie.value for cookie in self.client.cookies.jar}
            self.session_id = extract_session_id(cookies)

            # Fetch Adobe IMS guest access token for API calls
            await self._fetch_guest_access_token()

            # Create session info
            self.session_info = SessionInfo(
                session_id=self.session_id,
                csrf_token=self.csrf_token,
                cookies=cookies,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=SESSION_EXPIRY_HOURS),
                conversion_count=0,
                is_anonymous=True,
                access_token=self.access_token,
                access_token_expires_at=self.access_token_expires_at,
            )

            logger.info(
                f"Session initialized successfully (ID: {self.session_id[:8] if self.session_id else 'N/A'}...)"
            )

            # Auto-save if enabled
            if self.auto_save:
                self.save_session()

            return self.session_info

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during session initialization: {e}")
            raise AuthenticationError(
                "Failed to initialize session",
                details={"status_code": e.response.status_code, "url": str(e.request.url)},
            ) from e

        except httpx.RequestError as e:
            logger.error(f"Network error during session initialization: {e}")
            raise AuthenticationError(
                "Network error during session initialization", details={"error": str(e)}
            ) from e

    async def _fetch_guest_access_token(self) -> None:
        """Fetch a guest access token from Adobe IMS."""

        payload: dict[str, object] | None = None

        for attempt in range(2):
            device_id = token_hex(16)
            timestamp = str(int(datetime.now().timestamp() * 1000))

            data = {
                "client_id": IMS_GUEST_CLIENT_ID,
                "scope": IMS_GUEST_SCOPE,
                "response_type": "token",
                "redirect_uri": IMS_REFERER,
                "state": timestamp,
                "device_id": device_id,
                "device_name": self.client.headers.get("user-agent", DEFAULT_USER_AGENT),
                "existing_token": "",
                "guest_allowed": "true",
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "User-Agent": self.client.headers.get("user-agent", DEFAULT_USER_AGENT),
                "Referer": IMS_REFERER,
                "Origin": IMS_ORIGIN,
                "sec-ch-ua-platform": '"macOS"',
                "sec-ch-ua": '"Chromium";v="120", "Not=A?Brand";v="8", "Google Chrome";v="120"',
                "sec-ch-ua-mobile": "?0",
            }

            params = {
                "jslVersion": IMS_JSL_VERSION,
                "authId": device_id,
            }

            try:
                response = await self.client.post(
                    IMS_CHECK_TOKEN,
                    data=data,
                    headers=headers,
                    params=params,
                    timeout=SESSION_INIT_TIMEOUT,
                )

                if response.status_code == 403 and attempt == 0:
                    logger.warning("IMS returned 403; refreshing session context before retry")
                    await self._refresh_session_context()
                    continue

                response.raise_for_status()
                payload = response.json()
                break

            except httpx.HTTPStatusError as exc:
                logger.error(
                    "Failed to fetch guest access token: HTTP %s",
                    exc.response.status_code,
                )
                raise AuthenticationError(
                    "Failed to obtain authentication token",
                    details={
                        "status_code": exc.response.status_code,
                        "response": exc.response.text[:500],
                    },
                ) from exc
            except httpx.RequestError as exc:
                logger.error("Network error fetching guest access token: %s", exc)
                raise AuthenticationError(
                    "Network error obtaining authentication token",
                    details={"error": str(exc)},
                ) from exc

        if payload is None:
            raise AuthenticationError(
                "Authentication token missing from IMS response",
                details={"status_code": 403},
            )

        access_token = payload.get("access_token")
        expires_in = payload.get("expires_in")

        if not access_token:
            logger.error("IMS response missing access token: %s", payload)
            raise AuthenticationError(
                "Authentication token missing from IMS response",
                details={"response": payload},
            )

        expires_at: datetime | None = None

        try:
            expires_seconds = int(expires_in) if expires_in is not None else None
        except (TypeError, ValueError):
            expires_seconds = None

        if expires_seconds is not None:
            expires_at = datetime.now() + timedelta(seconds=expires_seconds)

        self.access_token = access_token
        self.access_token_expires_at = expires_at

        if self.session_info is not None:
            self.session_info.access_token = self.access_token
            self.session_info.access_token_expires_at = self.access_token_expires_at

        logger.info("Obtained Adobe IMS guest access token")

    async def _refresh_session_context(self) -> None:
        """Refresh page context to obtain fresh cookies and CSRF token."""

        current_user_agent = self.client.headers.get("user-agent", DEFAULT_USER_AGENT)
        try:
            response = await self.client.get(
                PDF_TO_WORD_PAGE,
                headers={**SESSION_INIT_HEADERS, "User-Agent": current_user_agent},
                timeout=SESSION_INIT_TIMEOUT,
                follow_redirects=True,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AuthenticationError(
                "Failed to refresh session context",
                details={"error": str(exc)},
            ) from exc

        html_content = response.text
        self.csrf_token = extract_csrf_token(html_content)
        cookies = {cookie.name: cookie.value for cookie in self.client.cookies.jar}
        self.session_id = extract_session_id(cookies)

        if self.session_info is not None:
            self.session_info.csrf_token = self.csrf_token
            self.session_info.session_id = self.session_id
            self.session_info.cookies = cookies

    def is_active(self) -> bool:
        """
        Check if the current session is active and valid

        Returns:
            True if session is active, False otherwise
        """
        if self.session_info is None:
            return False

        # Check if session has expired
        if self.session_info.is_expired():
            logger.warning("Session has expired")
            return False

        return True

    async def refresh_if_needed(self, max_conversions: int = 2) -> SessionInfo:
        """
        Refresh the session if it's expired or has reached conversion limit

        Args:
            max_conversions: Maximum conversions before refresh

        Returns:
            Current or refreshed SessionInfo

        Raises:
            AuthenticationError: If refresh fails
        """
        if self.session_info is None or self.session_info.should_refresh(max_conversions):
            logger.info("Refreshing session...")
            return await self.initialize()

        await self.ensure_access_token()
        return self.session_info

    async def ensure_access_token(self, force: bool = False) -> SessionInfo:
        """Ensure a valid access token is present, refreshing if required."""

        if self.session_info is None:
            return await self.initialize()

        needs_refresh = force or not self.session_info.access_token_is_valid()

        if needs_refresh:
            await self._fetch_guest_access_token()

            if self.session_info is None or not self.session_info.access_token:
                raise AuthenticationError("Failed to obtain Adobe access token")

        return self.session_info

    def increment_conversion_count(self) -> None:
        """Increment the conversion counter for the current session"""
        if self.session_info is not None:
            self.session_info.conversion_count += 1

            if self.auto_save:
                self.save_session()

    def save_session(self) -> None:
        """Save session data to disk"""
        if self.session_info is None:
            logger.warning("No session to save")
            return

        session_file = self.session_dir / SESSION_FILE

        try:
            # Convert SessionInfo to dict for JSON serialization
            session_data = {
                "session_id": self.session_info.session_id,
                "csrf_token": self.session_info.csrf_token,
                "cookies": self.session_info.cookies,
                "created_at": self.session_info.created_at.isoformat(),
                "expires_at": (
                    self.session_info.expires_at.isoformat()
                    if self.session_info.expires_at
                    else None
                ),
                "conversion_count": self.session_info.conversion_count,
                "is_anonymous": self.session_info.is_anonymous,
                "access_token": self.session_info.access_token,
                "access_token_expires_at": (
                    self.session_info.access_token_expires_at.isoformat()
                    if self.session_info.access_token_expires_at
                    else None
                ),
            }

            with open(session_file, "w") as f:
                json.dump(session_data, f, indent=2)

            logger.debug(f"Session saved to {session_file}")

        except OSError as e:
            logger.error(f"Failed to save session: {e}")

    def load_session(self) -> SessionInfo | None:
        """
        Load session data from disk

        Returns:
            SessionInfo if loaded successfully, None otherwise
        """
        session_file = self.session_dir / SESSION_FILE

        if not session_file.exists():
            logger.debug("No saved session found")
            return None

        try:
            with open(session_file) as f:
                session_data = json.load(f)

            # Parse datetime strings
            created_at = datetime.fromisoformat(session_data["created_at"])
            expires_at = (
                datetime.fromisoformat(session_data["expires_at"])
                if session_data.get("expires_at")
                else None
            )
            token_expires_at = (
                datetime.fromisoformat(session_data["access_token_expires_at"])
                if session_data.get("access_token_expires_at")
                else None
            )

            # Create SessionInfo object
            self.session_info = SessionInfo(
                session_id=session_data.get("session_id"),
                csrf_token=session_data.get("csrf_token"),
                cookies=session_data.get("cookies", {}),
                created_at=created_at,
                expires_at=expires_at,
                conversion_count=session_data.get("conversion_count", 0),
                is_anonymous=session_data.get("is_anonymous", True),
                access_token=session_data.get("access_token"),
                access_token_expires_at=token_expires_at,
            )

            # Restore tokens
            self.csrf_token = self.session_info.csrf_token
            self.session_id = self.session_info.session_id
            self.access_token = self.session_info.access_token
            self.access_token_expires_at = self.session_info.access_token_expires_at

            # Restore cookies to client
            for name, value in self.session_info.cookies.items():
                self.client.cookies.set(name, value)

            logger.info(
                f"Session loaded from disk (ID: {self.session_id[:8] if self.session_id else 'N/A'}...)"
            )

            return self.session_info

        except (OSError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to load session: {e}")
            return None

    def clear_session(self) -> None:
        """Clear the current session from memory and disk"""
        self.session_info = None
        self.csrf_token = None
        self.session_id = None

        session_file = self.session_dir / SESSION_FILE

        if session_file.exists():
            try:
                session_file.unlink()
                logger.info("Session cleared")
            except OSError as e:
                logger.error(f"Failed to delete session file: {e}")
