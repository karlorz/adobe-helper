"""
Cookie management for Adobe Helper

This module provides functionality for saving, loading, and managing cookies
to support session persistence and rotation.
"""

import json
import logging
import time
from pathlib import Path

from adobe.constants import COOKIE_MAX_AGE_DAYS, COOKIES_DIR, DEFAULT_SESSION_DIR

logger = logging.getLogger(__name__)


class CookieManager:
    """
    Manages cookie storage and retrieval for session persistence

    Supports saving cookies to disk, loading them back, and cleaning up
    old cookie files.
    """

    def __init__(self, cookie_dir: Path | None = None):
        """
        Initialize the cookie manager

        Args:
            cookie_dir: Directory to store cookie files (default: ~/.adobe-helper/cookies)
        """
        base_dir = Path.home() / DEFAULT_SESSION_DIR if cookie_dir is None else cookie_dir
        self.cookie_dir = base_dir / COOKIES_DIR if cookie_dir is None else cookie_dir

        # Ensure cookie directory exists
        self.cookie_dir.mkdir(parents=True, exist_ok=True)

    def save_cookies(self, cookies: dict[str, str], session_id: str) -> None:
        """
        Save cookies to disk for a specific session

        Args:
            cookies: Dictionary of cookie name-value pairs
            session_id: Unique identifier for the session
        """
        cookie_file = self.cookie_dir / f"{session_id}.json"

        try:
            cookie_data = {
                "cookies": cookies,
                "saved_at": time.time(),
                "session_id": session_id,
            }

            with open(cookie_file, "w") as f:
                json.dump(cookie_data, f, indent=2)

            logger.debug(f"Saved {len(cookies)} cookies for session {session_id[:8]}...")

        except OSError as e:
            logger.error(f"Failed to save cookies: {e}")

    def load_cookies(self, session_id: str) -> dict[str, str] | None:
        """
        Load cookies from disk for a specific session

        Args:
            session_id: Unique identifier for the session

        Returns:
            Dictionary of cookies if found, None otherwise
        """
        cookie_file = self.cookie_dir / f"{session_id}.json"

        if not cookie_file.exists():
            logger.debug(f"No cookies found for session {session_id[:8]}...")
            return None

        try:
            with open(cookie_file) as f:
                cookie_data = json.load(f)

            cookies_raw = cookie_data.get("cookies", {})
            if not isinstance(cookies_raw, dict):
                logger.debug(
                    "Cookie payload malformed for session %s; returning empty dict",
                    session_id[:8],
                )
                return {}

            cookies: dict[str, str] = {
                str(name): str(value) for name, value in cookies_raw.items() if value is not None
            }
            logger.debug(f"Loaded {len(cookies)} cookies for session {session_id[:8]}...")

            return cookies

        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load cookies: {e}")
            return None

    def delete_cookies(self, session_id: str) -> None:
        """
        Delete cookies for a specific session

        Args:
            session_id: Unique identifier for the session
        """
        cookie_file = self.cookie_dir / f"{session_id}.json"

        if cookie_file.exists():
            try:
                cookie_file.unlink()
                logger.debug(f"Deleted cookies for session {session_id[:8]}...")
            except OSError as e:
                logger.error(f"Failed to delete cookies: {e}")

    def clean_old_cookies(self, max_age_days: int = COOKIE_MAX_AGE_DAYS) -> int:
        """
        Clean up cookie files older than the specified age

        Args:
            max_age_days: Maximum age in days (default from constants)

        Returns:
            Number of cookie files deleted
        """
        current_time = time.time()
        max_age_seconds = max_age_days * 86400
        deleted_count = 0

        try:
            for cookie_file in self.cookie_dir.glob("*.json"):
                # Check file modification time
                file_age = current_time - cookie_file.stat().st_mtime

                if file_age > max_age_seconds:
                    try:
                        cookie_file.unlink()
                        deleted_count += 1
                        logger.debug(f"Deleted old cookie file: {cookie_file.name}")
                    except OSError as e:
                        logger.error(f"Failed to delete {cookie_file.name}: {e}")

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old cookie file(s)")

        except OSError as e:
            logger.error(f"Error during cookie cleanup: {e}")

        return deleted_count

    def list_sessions(self) -> list[str]:
        """
        List all session IDs that have saved cookies

        Returns:
            List of session IDs
        """
        session_ids: list[str] = []

        try:
            for cookie_file in self.cookie_dir.glob("*.json"):
                # Extract session ID from filename (remove .json extension)
                session_id = cookie_file.stem
                session_ids.append(session_id)

        except OSError as e:
            logger.error(f"Error listing sessions: {e}")

        return session_ids

    def get_cookie_count(self, session_id: str) -> int:
        """
        Get the number of cookies stored for a session

        Args:
            session_id: Unique identifier for the session

        Returns:
            Number of cookies, or 0 if session not found
        """
        cookies = self.load_cookies(session_id)
        return len(cookies) if cookies else 0

    def clear_all_cookies(self) -> int:
        """
        Delete all stored cookie files

        Returns:
            Number of files deleted
        """
        deleted_count = 0

        try:
            for cookie_file in self.cookie_dir.glob("*.json"):
                try:
                    cookie_file.unlink()
                    deleted_count += 1
                except OSError as e:
                    logger.error(f"Failed to delete {cookie_file.name}: {e}")

            if deleted_count > 0:
                logger.info(f"Cleared all cookies ({deleted_count} file(s))")

        except OSError as e:
            logger.error(f"Error clearing cookies: {e}")

        return deleted_count
