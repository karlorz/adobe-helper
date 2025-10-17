"""
Usage tracking for Adobe Helper free tier

This module tracks conversion usage to respect Adobe's free tier limits
and avoid exceeding daily conversion quotas.
"""

import json
import logging
from datetime import date, datetime
from pathlib import Path

from adobe.constants import DEFAULT_SESSION_DIR, FREE_TIER_DAILY_LIMIT, USAGE_FILE

logger = logging.getLogger(__name__)


class FreeUsageTracker:
    """
    Tracks free conversion usage with daily reset

    Monitors the number of conversions performed per day and provides
    warnings when approaching the free tier limit.
    """

    def __init__(self, usage_dir: Path | None = None, daily_limit: int = FREE_TIER_DAILY_LIMIT):
        """
        Initialize the usage tracker

        Args:
            usage_dir: Directory to store usage data (default: ~/.adobe-helper)
            daily_limit: Maximum free conversions per day
        """
        self.usage_dir = Path.home() / DEFAULT_SESSION_DIR if usage_dir is None else usage_dir
        self.daily_limit = daily_limit
        self.usage_file = self.usage_dir / USAGE_FILE

        # Ensure directory exists
        self.usage_dir.mkdir(parents=True, exist_ok=True)

        # Load or initialize usage data
        self.usage_data = self._load_usage()

    def _load_usage(self) -> dict:
        """
        Load usage data from disk

        Returns:
            Dictionary with usage data
        """
        if not self.usage_file.exists():
            return self._create_empty_usage()

        try:
            with open(self.usage_file) as f:
                data = json.load(f)

            # Check if date has changed (new day)
            today = str(date.today())
            if data.get("date") != today:
                logger.info("New day detected - resetting usage counter")
                return self._create_empty_usage()

            return data

        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load usage data: {e}")
            return self._create_empty_usage()

    def _create_empty_usage(self) -> dict:
        """
        Create empty usage data structure for current day

        Returns:
            Dictionary with initial usage data
        """
        return {
            "date": str(date.today()),
            "count": 0,
            "conversions": [],
        }

    def _save_usage(self) -> None:
        """Save usage data to disk"""
        try:
            with open(self.usage_file, "w") as f:
                json.dump(self.usage_data, f, indent=2)

            logger.debug(f"Usage data saved: {self.usage_data['count']} conversions")

        except OSError as e:
            logger.error(f"Failed to save usage data: {e}")

    def can_convert(self) -> bool:
        """
        Check if conversion is allowed under free tier limits

        Returns:
            True if conversion is allowed, False if limit exceeded
        """
        # Refresh data in case day has changed
        self.usage_data = self._load_usage()

        current_count = self.usage_data.get("count", 0)
        can_proceed = current_count < self.daily_limit

        if not can_proceed:
            logger.warning(f"Daily conversion limit reached: {current_count}/{self.daily_limit}")

        return can_proceed

    def increment_usage(self, filename: str | None = None) -> None:
        """
        Increment the usage counter after a successful conversion

        Args:
            filename: Optional filename of the converted file
        """
        # Refresh data
        self.usage_data = self._load_usage()

        # Increment counter
        self.usage_data["count"] += 1

        # Record conversion details
        conversion_record = {
            "timestamp": datetime.now().isoformat(),
            "filename": filename,
        }
        self.usage_data["conversions"].append(conversion_record)

        # Save updated data
        self._save_usage()

        # Log warning if approaching limit
        remaining = self.get_remaining()
        if remaining <= 1:
            logger.warning(f"Approaching daily limit: {remaining} conversion(s) remaining")
        else:
            logger.info(f"Conversion tracked: {self.usage_data['count']}/{self.daily_limit}")

    def get_current_count(self) -> int:
        """
        Get the current conversion count for today

        Returns:
            Number of conversions performed today
        """
        # Refresh data
        self.usage_data = self._load_usage()
        return self.usage_data.get("count", 0)

    def get_remaining(self) -> int:
        """
        Get the number of remaining free conversions for today

        Returns:
            Number of conversions remaining (0 if limit reached)
        """
        return max(0, self.daily_limit - self.get_current_count())

    def reset_usage(self) -> None:
        """Reset usage data (useful for testing or manual reset)"""
        self.usage_data = self._create_empty_usage()
        self._save_usage()
        logger.info("Usage data reset")

    def get_conversion_history(self) -> list[dict]:
        """
        Get the list of conversions performed today

        Returns:
            List of conversion records with timestamps
        """
        # Refresh data
        self.usage_data = self._load_usage()
        return self.usage_data.get("conversions", [])

    def get_usage_summary(self) -> dict:
        """
        Get a summary of usage statistics

        Returns:
            Dictionary with usage statistics
        """
        # Refresh data
        self.usage_data = self._load_usage()

        return {
            "date": self.usage_data["date"],
            "count": self.usage_data["count"],
            "limit": self.daily_limit,
            "remaining": self.get_remaining(),
            "percentage_used": (
                (self.usage_data["count"] / self.daily_limit) * 100 if self.daily_limit > 0 else 0
            ),
        }

    def __str__(self) -> str:
        """String representation of usage tracker"""
        summary = self.get_usage_summary()
        return (
            f"Usage: {summary['count']}/{summary['limit']} "
            f"({summary['percentage_used']:.0f}%) "
            f"- {summary['remaining']} remaining"
        )
