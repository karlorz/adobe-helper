"""
Constants for Adobe Helper

This module contains configuration constants, limits, and default values
used throughout the library.
"""

from adobe.models import ConversionType

# File constraints
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_FILE_SIZE_FREE = 25 * 1024 * 1024  # 25 MB for free tier
MIN_FILE_SIZE = 1024  # 1 KB
ALLOWED_EXTENSIONS = [".pdf"]
PDF_MAGIC_BYTES = b"%PDF-"

# Conversion settings
DEFAULT_CONVERSION_TYPE = ConversionType.PDF_TO_WORD
SUPPORTED_OUTPUT_FORMATS = {
    ConversionType.PDF_TO_WORD: ".docx",
    ConversionType.PDF_TO_EXCEL: ".xlsx",
    ConversionType.PDF_TO_PPT: ".pptx",
    ConversionType.PDF_TO_IMAGE: ".jpg",
}

# Timeout settings (in seconds)
DEFAULT_TIMEOUT = 300.0  # 5 minutes
UPLOAD_TIMEOUT = 600.0  # 10 minutes
CONVERSION_TIMEOUT = 600.0  # 10 minutes
DOWNLOAD_TIMEOUT = 300.0  # 5 minutes
SESSION_INIT_TIMEOUT = 30.0  # 30 seconds

# Polling settings
POLL_INTERVAL = 2.0  # 2 seconds
MAX_POLL_ATTEMPTS = 150  # 150 attempts * 2 seconds = 5 minutes
POLL_BACKOFF_MULTIPLIER = 1.1  # Increase interval by 10% each time
MAX_POLL_INTERVAL = 10.0  # Maximum 10 seconds between polls

# Rate limiting
DEFAULT_MIN_DELAY = 5.0  # Minimum 5 seconds between requests
DEFAULT_MAX_DELAY = 15.0  # Maximum 15 seconds between requests
RATE_LIMIT_BACKOFF = 60.0  # Wait 60 seconds on rate limit
MAX_RETRIES = 3  # Maximum retry attempts
RETRY_BACKOFF_BASE = 2.0  # Exponential backoff base

# Session management
MAX_CONVERSIONS_PER_SESSION = 2  # Max conversions before refreshing session
SESSION_EXPIRY_HOURS = 24  # Sessions expire after 24 hours
COOKIE_MAX_AGE_DAYS = 7  # Clean up cookies older than 7 days

# Free tier quotas
FREE_TIER_DAILY_LIMIT = 2  # Adobe's free tier allows ~2 conversions per day
FREE_TIER_SESSION_LIMIT = 2  # Per anonymous session

# Storage paths
DEFAULT_SESSION_DIR = ".adobe-helper"
SESSION_FILE = "session.json"
COOKIES_DIR = "cookies"
USAGE_FILE = "usage.json"
CACHE_DIR = "cache"

# HTTP settings
HTTP_MAX_REDIRECTS = 10
HTTP_MAX_CONNECTIONS = 100
HTTP_MAX_KEEPALIVE_CONNECTIONS = 20
HTTP_KEEPALIVE_EXPIRY = 5.0

# Upload settings
UPLOAD_CHUNK_SIZE = 8192  # 8 KB chunks for streaming upload
DOWNLOAD_CHUNK_SIZE = 8192  # 8 KB chunks for streaming download
UPLOAD_BUFFER_SIZE = 65536  # 64 KB buffer

# Browser automation settings (for fallback)
BROWSER_HEADLESS = True
BROWSER_TIMEOUT = 300000  # 5 minutes in milliseconds
BROWSER_VIEWPORT = {"width": 1920, "height": 1080}
BROWSER_DOWNLOAD_TIMEOUT = 600000  # 10 minutes

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_LEVEL = "INFO"

# Error messages
ERROR_FILE_NOT_FOUND = "PDF file not found: {path}"
ERROR_FILE_TOO_LARGE = "File exceeds maximum size of {max_size} bytes: {size} bytes"
ERROR_INVALID_PDF = "File is not a valid PDF: {path}"
ERROR_UPLOAD_FAILED = "Failed to upload file: {reason}"
ERROR_CONVERSION_FAILED = "Conversion failed: {reason}"
ERROR_DOWNLOAD_FAILED = "Failed to download converted file: {reason}"
ERROR_QUOTA_EXCEEDED = "Daily conversion quota exceeded: {current}/{limit}"
ERROR_SESSION_EXPIRED = "Session has expired, please refresh"
ERROR_TIMEOUT = "Operation timed out after {timeout} seconds"
ERROR_RATE_LIMITED = "Rate limited, please retry after {retry_after} seconds"

# Success messages
SUCCESS_UPLOAD = "File uploaded successfully: {filename}"
SUCCESS_CONVERSION = "Conversion completed: {input_file} -> {output_file}"
SUCCESS_DOWNLOAD = "File downloaded successfully: {output_path}"

# Status messages
STATUS_INITIALIZING = "Initializing session..."
STATUS_UPLOADING = "Uploading file..."
STATUS_CONVERTING = "Converting PDF to DOCX..."
STATUS_DOWNLOADING = "Downloading converted file..."
STATUS_POLLING = "Checking conversion status..."
STATUS_WAITING = "Waiting for conversion to complete..."

# MIME types
MIME_PDF = "application/pdf"
MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MIME_PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

# Feature flags
ENABLE_CACHING = True
ENABLE_PROGRESS_CALLBACKS = True
ENABLE_SESSION_ROTATION = True
ENABLE_BROWSER_FALLBACK = False  # Disabled by default, requires Playwright
