"""
Anonymous session cycling for Adobe Helper

This module implements session rotation to work around free tier limits
by cycling through fresh anonymous sessions with different identities.
"""

import logging
from pathlib import Path

import httpx

from adobe.auth import SessionManager
from adobe.constants import (
    FREE_TIER_SESSION_LIMIT,
    HTTP_KEEPALIVE_EXPIRY,
    HTTP_MAX_CONNECTIONS,
    HTTP_MAX_KEEPALIVE_CONNECTIONS,
    HTTP_MAX_REDIRECTS,
)
from adobe.cookie_manager import CookieManager
from adobe.models import SessionInfo
from adobe.utils import get_random_user_agent

logger = logging.getLogger(__name__)


class AnonymousSessionManager:
    """
    Manages anonymous session rotation for extended free tier usage

    Creates and cycles through fresh sessions to bypass conversion limits
    while appearing as different anonymous users.
    """

    def __init__(
        self,
        max_conversions_per_session: int = FREE_TIER_SESSION_LIMIT,
        session_dir: Path | None = None,
    ):
        """
        Initialize the anonymous session manager

        Args:
            max_conversions_per_session: Max conversions before rotating session
            session_dir: Directory for session data storage
        """
        self.max_conversions = max_conversions_per_session
        self.session_dir = session_dir

        # Current session
        self.current_client: httpx.AsyncClient | None = None
        self.current_session_manager: SessionManager | None = None

        # Cookie manager for session persistence
        self.cookie_manager = CookieManager(session_dir)

    async def get_session(self) -> SessionManager:
        """
        Get the current session or create a new one if needed

        Returns:
            Active SessionManager instance

        Raises:
            AuthenticationError: If session creation fails
        """
        # Check if we need a new session
        if self.should_refresh_session():
            logger.info("Creating fresh anonymous session...")
            await self.create_fresh_session()

        return self.current_session_manager  # type: ignore

    async def ensure_access_token(self, force: bool = False) -> SessionInfo:
        """Ensure the active session has a valid access token."""

        session_manager = await self.get_session()
        session_info = await session_manager.ensure_access_token(force=force)
        return session_info

    def should_refresh_session(self) -> bool:
        """
        Check if session should be refreshed

        Returns:
            True if refresh needed, False otherwise
        """
        # No session exists
        if self.current_session_manager is None:
            return True

        # Check conversion count
        if self.current_session_manager.session_info is None:
            return True

        # Check if session has reached conversion limit
        if self.current_session_manager.session_info.should_refresh(self.max_conversions):
            logger.info(
                f"Session reached conversion limit "
                f"({self.current_session_manager.session_info.conversion_count}/{self.max_conversions})"
            )
            return True

        return False

    async def create_fresh_session(self) -> SessionManager:
        """
        Create a brand new anonymous session with fresh identity

        Returns:
            New SessionManager instance
        """
        # Close existing client if present
        if self.current_client is not None:
            await self.current_client.aclose()

        # Create new HTTP client with random user agent
        user_agent = get_random_user_agent()

        self.current_client = httpx.AsyncClient(
            http2=True,
            timeout=httpx.Timeout(300.0),
            follow_redirects=True,
            max_redirects=HTTP_MAX_REDIRECTS,
            limits=httpx.Limits(
                max_connections=HTTP_MAX_CONNECTIONS,
                max_keepalive_connections=HTTP_MAX_KEEPALIVE_CONNECTIONS,
                keepalive_expiry=HTTP_KEEPALIVE_EXPIRY,
            ),
            headers={"User-Agent": user_agent},
        )

        # Create session manager
        self.current_session_manager = SessionManager(
            client=self.current_client, session_dir=self.session_dir, auto_save=False
        )

        # Initialize the session
        session_info = await self.current_session_manager.initialize()

        # Save cookies for this session
        if session_info.session_id:
            self.cookie_manager.save_cookies(session_info.cookies, session_info.session_id)

        logger.info(f"Fresh session created with user agent: {user_agent[:50]}...")

        return self.current_session_manager

    async def increment_and_check_rotation(self) -> None:
        """
        Increment conversion count and rotate session if needed

        This should be called after each successful conversion.
        """
        if self.current_session_manager is not None:
            self.current_session_manager.increment_conversion_count()

            # Check if we need to rotate
            if self.should_refresh_session():
                logger.info("Session limit reached - will rotate on next request")

    async def close(self) -> None:
        """Close the current HTTP client and clean up resources"""
        if self.current_client is not None:
            await self.current_client.aclose()
            self.current_client = None

        self.current_session_manager = None
        logger.info("Anonymous session manager closed")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    def get_session_stats(self) -> dict:
        """
        Get statistics about the current session

        Returns:
            Dictionary with session statistics
        """
        if (
            self.current_session_manager is None
            or self.current_session_manager.session_info is None
        ):
            return {
                "active": False,
                "conversions": 0,
                "limit": self.max_conversions,
            }

        session_info = self.current_session_manager.session_info

        return {
            "active": True,
            "session_id": session_info.session_id[:8] if session_info.session_id else "N/A",
            "conversions": session_info.conversion_count,
            "limit": self.max_conversions,
            "remaining": self.max_conversions - session_info.conversion_count,
            "is_expired": session_info.is_expired(),
        }

    def cleanup_old_sessions(self, max_age_days: int = 7) -> int:
        """
        Clean up old session data

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of sessions cleaned up
        """
        return self.cookie_manager.clean_old_cookies(max_age_days)
