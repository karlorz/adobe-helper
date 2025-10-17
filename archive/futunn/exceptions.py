"""
Custom exceptions for Futunn API client
"""


class FutunnAPIError(Exception):
    """Base exception for all Futunn API errors"""

    pass


class TokenExpiredError(FutunnAPIError):
    """Raised when authentication token has expired"""

    pass


class RateLimitError(FutunnAPIError):
    """Raised when API rate limit is exceeded"""

    pass


class InvalidResponseError(FutunnAPIError):
    """Raised when API returns invalid or unexpected response"""

    pass


class ConnectionError(FutunnAPIError):
    """Raised when connection to API fails"""

    pass
