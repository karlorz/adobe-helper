"""
Adobe Helper - Python client for Adobe PDF to Word conversion

This library provides a Python interface to Adobe's online PDF conversion services,
supporting PDF to DOCX conversion with both API-based and browser-based methods.
"""

__version__ = "0.1.0"
__author__ = "Adobe Helper Contributors"
__license__ = "MIT"

# Import main classes for convenience
from adobe.client import AdobePDFConverter
from adobe.exceptions import (
    AdobeHelperError,
    AuthenticationError,
    BrowserAutomationError,
    ConversionError,
    DownloadError,
    NetworkError,
    QuotaExceededError,
    RateLimitError,
    TimeoutError,
    UploadError,
    ValidationError,
)
from adobe.models import ConversionJob, ConversionStatus, ConversionType, FileInfo

__all__ = [
    "__version__",
    # Main client
    "AdobePDFConverter",
    # Exceptions
    "AdobeHelperError",
    "AuthenticationError",
    "UploadError",
    "ConversionError",
    "DownloadError",
    "QuotaExceededError",
    "ValidationError",
    "TimeoutError",
    "NetworkError",
    "RateLimitError",
    "BrowserAutomationError",
    # Models
    "ConversionStatus",
    "ConversionType",
    "ConversionJob",
    "FileInfo",
]
