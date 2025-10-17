"""
Exception classes for Adobe Helper

This module defines custom exceptions used throughout the library
for proper error handling and reporting.
"""


class AdobeHelperError(Exception):
    """Base exception for all Adobe Helper errors"""

    def __init__(self, message: str, details: dict | None = None):
        """
        Initialize the exception

        Args:
            message: Error message
            details: Additional error details (optional)
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """String representation of the error"""
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class AuthenticationError(AdobeHelperError):
    """
    Raised when authentication or session management fails

    This can occur when:
    - Unable to obtain session tokens
    - CSRF token validation fails
    - Session has expired
    - Login is required but credentials not provided
    """

    pass


class UploadError(AdobeHelperError):
    """
    Raised when file upload fails

    This can occur when:
    - File is too large
    - Invalid file format
    - Network error during upload
    - Server rejects the file
    - Upload timeout
    """

    pass


class ConversionError(AdobeHelperError):
    """
    Raised when PDF conversion fails

    This can occur when:
    - Conversion job fails on server
    - Invalid conversion parameters
    - PDF file is corrupted
    - Unsupported PDF features
    - Server-side processing error
    """

    pass


class DownloadError(AdobeHelperError):
    """
    Raised when downloading converted file fails

    This can occur when:
    - Download URL is invalid or expired
    - Network error during download
    - Incomplete download
    - File corruption during download
    """

    pass


class QuotaExceededError(AdobeHelperError):
    """
    Raised when free conversion quota is exceeded

    This occurs when:
    - Daily conversion limit reached
    - Session conversion limit reached
    - Account-based quota exceeded
    """

    def __init__(
        self,
        message: str = "Conversion quota exceeded",
        limit: int | None = None,
        current: int | None = None,
        details: dict | None = None,
    ):
        """
        Initialize the exception

        Args:
            message: Error message
            limit: The quota limit
            current: Current usage count
            details: Additional error details
        """
        self.limit = limit
        self.current = current
        details = details or {}
        if limit is not None:
            details["limit"] = limit
        if current is not None:
            details["current"] = current
        super().__init__(message, details)


class ValidationError(AdobeHelperError):
    """
    Raised when input validation fails

    This can occur when:
    - Invalid file path
    - File doesn't exist
    - File is not a PDF
    - Invalid conversion parameters
    - Invalid configuration
    """

    pass


class TimeoutError(AdobeHelperError):
    """
    Raised when an operation times out

    This can occur when:
    - Upload takes too long
    - Conversion takes too long
    - Download takes too long
    - Polling timeout exceeded
    """

    def __init__(
        self,
        message: str = "Operation timed out",
        timeout: float | None = None,
        details: dict | None = None,
    ):
        """
        Initialize the exception

        Args:
            message: Error message
            timeout: The timeout duration in seconds
            details: Additional error details
        """
        self.timeout = timeout
        details = details or {}
        if timeout is not None:
            details["timeout"] = f"{timeout}s"
        super().__init__(message, details)


class NetworkError(AdobeHelperError):
    """
    Raised when network-related errors occur

    This can occur when:
    - Connection refused
    - DNS resolution fails
    - Network timeout
    - SSL/TLS errors
    - Proxy errors
    """

    pass


class RateLimitError(AdobeHelperError):
    """
    Raised when rate limiting is encountered

    This can occur when:
    - Too many requests in short time
    - Server returns 429 status
    - API rate limit exceeded
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
        details: dict | None = None,
    ):
        """
        Initialize the exception

        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            details: Additional error details
        """
        self.retry_after = retry_after
        details = details or {}
        if retry_after is not None:
            details["retry_after"] = f"{retry_after}s"
        super().__init__(message, details)


class BrowserAutomationError(AdobeHelperError):
    """
    Raised when browser automation fails

    This can occur when:
    - Playwright/browser not installed
    - Page navigation fails
    - Element not found
    - JavaScript execution fails
    - Browser crashes
    """

    pass
