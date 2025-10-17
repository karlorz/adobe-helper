"""Tests for Adobe Helper exception classes"""

from adobe.exceptions import (
    AdobeHelperError,
    AuthenticationError,
    BrowserAutomationError,
    ConversionError,
    DownloadError,
    NetworkError,
    QuotaExceededError,
    RateLimitError,
    UploadError,
    ValidationError,
)
from adobe.exceptions import (
    TimeoutError as AdobeTimeoutError,
)


class TestBaseException:
    """Tests for AdobeHelperError base exception"""

    def test_basic_exception(self):
        """Test basic exception creation"""
        error = AdobeHelperError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.details == {}

    def test_exception_with_details(self):
        """Test exception with additional details"""
        error = AdobeHelperError("Upload failed", details={"file": "test.pdf", "size": 1024})
        assert "Upload failed" in str(error)
        assert "file=test.pdf" in str(error)
        assert "size=1024" in str(error)


class TestSpecificExceptions:
    """Tests for specific exception types"""

    def test_authentication_error(self):
        """Test AuthenticationError"""
        error = AuthenticationError("Session expired")
        assert isinstance(error, AdobeHelperError)
        assert "Session expired" in str(error)

    def test_upload_error(self):
        """Test UploadError"""
        error = UploadError("File too large", details={"max_size": 100})
        assert isinstance(error, AdobeHelperError)

    def test_conversion_error(self):
        """Test ConversionError"""
        error = ConversionError("PDF is corrupted")
        assert isinstance(error, AdobeHelperError)

    def test_download_error(self):
        """Test DownloadError"""
        error = DownloadError("Download URL expired")
        assert isinstance(error, AdobeHelperError)

    def test_validation_error(self):
        """Test ValidationError"""
        error = ValidationError("Invalid file format")
        assert isinstance(error, AdobeHelperError)

    def test_network_error(self):
        """Test NetworkError"""
        error = NetworkError("Connection refused")
        assert isinstance(error, AdobeHelperError)

    def test_browser_automation_error(self):
        """Test BrowserAutomationError"""
        error = BrowserAutomationError("Playwright not installed")
        assert isinstance(error, AdobeHelperError)


class TestQuotaExceededError:
    """Tests for QuotaExceededError"""

    def test_quota_exceeded_basic(self):
        """Test basic quota exceeded error"""
        error = QuotaExceededError()
        assert "quota exceeded" in str(error).lower()

    def test_quota_exceeded_with_limits(self):
        """Test quota exceeded with limit information"""
        error = QuotaExceededError("Daily limit reached", limit=2, current=2)
        assert error.limit == 2
        assert error.current == 2
        assert "limit=2" in str(error)
        assert "current=2" in str(error)


class TestTimeoutError:
    """Tests for TimeoutError"""

    def test_timeout_basic(self):
        """Test basic timeout error"""
        error = AdobeTimeoutError()
        assert "timed out" in str(error).lower()

    def test_timeout_with_duration(self):
        """Test timeout with duration information"""
        error = AdobeTimeoutError("Upload timed out", timeout=60.0)
        assert error.timeout == 60.0
        assert "60" in str(error)


class TestRateLimitError:
    """Tests for RateLimitError"""

    def test_rate_limit_basic(self):
        """Test basic rate limit error"""
        error = RateLimitError()
        assert "rate limit" in str(error).lower()

    def test_rate_limit_with_retry_after(self):
        """Test rate limit with retry information"""
        error = RateLimitError("Too many requests", retry_after=30)
        assert error.retry_after == 30
        assert "30" in str(error)
