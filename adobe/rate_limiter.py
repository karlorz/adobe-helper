"""
Rate limiting for Adobe Helper

This module implements rate limiting to ensure respectful usage of Adobe's
services and avoid triggering anti-bot mechanisms.
"""

import asyncio
import logging
import random
import time

from adobe.constants import (
    DEFAULT_MAX_DELAY,
    DEFAULT_MIN_DELAY,
    MAX_RETRIES,
    RATE_LIMIT_BACKOFF,
    RETRY_BACKOFF_BASE,
)

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter with human-like delays and exponential backoff

    Implements delays between requests to avoid triggering rate limits
    and provides retry logic with backoff.
    """

    def __init__(
        self,
        min_delay: float = DEFAULT_MIN_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
        max_retries: int = MAX_RETRIES,
    ):
        """
        Initialize the rate limiter

        Args:
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
            max_retries: Maximum number of retry attempts
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.last_request_time: float = 0

    async def wait(self) -> None:
        """
        Wait with a random human-like delay before the next request

        This method ensures that requests are spaced out with randomized
        delays to appear more human-like and avoid detection.
        """
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        # Calculate required delay
        if time_since_last < self.min_delay:
            # Add random jitter to make delays more human-like
            delay = random.uniform(
                self.min_delay - time_since_last, self.max_delay - time_since_last
            )
            delay = max(0, delay)  # Ensure non-negative

            logger.debug(f"Rate limiting: waiting {delay:.2f}s before next request")
            await asyncio.sleep(delay)

        # Update last request time
        self.last_request_time = time.time()

    async def wait_for_rate_limit(self, retry_after: int | None = None) -> None:
        """
        Wait when rate limited by the server

        Args:
            retry_after: Seconds to wait (from server), or use default backoff
        """
        wait_time = retry_after if retry_after is not None else RATE_LIMIT_BACKOFF

        logger.warning(f"Rate limited - waiting {wait_time}s before retry")
        await asyncio.sleep(wait_time)

    def calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay for retries

        Args:
            attempt: Retry attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff with jitter
        base_delay = RETRY_BACKOFF_BASE**attempt
        jitter = random.uniform(0, base_delay * 0.1)  # Add 0-10% jitter
        delay = base_delay + jitter

        logger.debug(f"Retry attempt {attempt + 1}: backoff delay {delay:.2f}s")
        return delay

    async def retry_with_backoff(self, attempt: int) -> None:
        """
        Wait with exponential backoff before retry

        Args:
            attempt: Retry attempt number (0-indexed)
        """
        if attempt >= self.max_retries:
            logger.error(f"Max retries ({self.max_retries}) exceeded")
            return

        delay = self.calculate_backoff(attempt)
        await asyncio.sleep(delay)

    def reset(self) -> None:
        """Reset the rate limiter state"""
        self.last_request_time = 0
        logger.debug("Rate limiter reset")


class AdaptiveRateLimiter(RateLimiter):
    """
    Advanced rate limiter that adapts delays based on server responses

    Dynamically adjusts delays based on observed response times and
    rate limit errors.
    """

    def __init__(
        self,
        min_delay: float = DEFAULT_MIN_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
        max_retries: int = MAX_RETRIES,
        adaptation_factor: float = 1.5,
    ):
        """
        Initialize the adaptive rate limiter

        Args:
            min_delay: Minimum delay between requests
            max_delay: Maximum delay between requests
            max_retries: Maximum retry attempts
            adaptation_factor: Factor to increase delay when rate limited
        """
        super().__init__(min_delay, max_delay, max_retries)
        self.adaptation_factor = adaptation_factor
        self.current_min_delay = min_delay
        self.current_max_delay = max_delay
        self.rate_limit_count = 0

    def adjust_for_rate_limit(self) -> None:
        """Increase delays after encountering a rate limit"""
        self.rate_limit_count += 1

        # Increase delays by adaptation factor
        self.current_min_delay = min(
            self.current_min_delay * self.adaptation_factor, self.max_delay
        )
        self.current_max_delay = min(
            self.current_max_delay * self.adaptation_factor, self.max_delay * 2
        )

        logger.info(
            f"Adjusted delays after rate limit (count: {self.rate_limit_count}): "
            f"{self.current_min_delay:.1f}s - {self.current_max_delay:.1f}s"
        )

    def adjust_for_success(self) -> None:
        """Gradually decrease delays after successful requests"""
        if self.current_min_delay > self.min_delay:
            # Slowly reduce delays back to normal
            self.current_min_delay = max(
                self.current_min_delay / (self.adaptation_factor**0.5), self.min_delay
            )
            self.current_max_delay = max(
                self.current_max_delay / (self.adaptation_factor**0.5), self.max_delay
            )

            logger.debug(
                f"Adjusted delays after success: "
                f"{self.current_min_delay:.1f}s - {self.current_max_delay:.1f}s"
            )

    async def wait(self) -> None:
        """Wait with adaptive delay based on current state"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.current_min_delay:
            delay = random.uniform(
                self.current_min_delay - time_since_last,
                self.current_max_delay - time_since_last,
            )
            delay = max(0, delay)

            logger.debug(f"Adaptive rate limiting: waiting {delay:.2f}s")
            await asyncio.sleep(delay)

        self.last_request_time = time.time()

    def reset(self) -> None:
        """Reset the adaptive rate limiter to initial state"""
        super().reset()
        self.current_min_delay = self.min_delay
        self.current_max_delay = self.max_delay
        self.rate_limit_count = 0
        logger.debug("Adaptive rate limiter reset")
