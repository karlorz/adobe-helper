"""
Main client for Adobe Helper

This module provides the main AdobePDFConverter class that integrates
all components for PDF to Word conversion.
"""

import logging
from collections.abc import Callable
from pathlib import Path

import httpx

from adobe.auth import SessionManager
from adobe.constants import (
    DEFAULT_TIMEOUT,
    HTTP_KEEPALIVE_EXPIRY,
    HTTP_MAX_CONNECTIONS,
    HTTP_MAX_KEEPALIVE_CONNECTIONS,
    HTTP_MAX_REDIRECTS,
)
from adobe.conversion import ConversionManager
from adobe.download import FileDownloader
from adobe.exceptions import (
    AdobeHelperError,
    ConversionError,
    DownloadError,
    QuotaExceededError,
    UploadError,
)
from adobe.models import ConversionType, UploadProgress
from adobe.rate_limiter import RateLimiter
from adobe.session_cycling import AnonymousSessionManager
from adobe.upload import FileUploader
from adobe.urls import (
    API_CONVERT,
    API_DOWNLOAD,
    API_STATUS,
    API_UPLOAD,
    COMMON_HEADERS,
    DEFAULT_USER_AGENT,
    get_api_endpoints,
    get_endpoints_for_session,
)
from adobe.usage_tracker import FreeUsageTracker

logger = logging.getLogger(__name__)


class AdobePDFConverter:
    """
    Main client for converting PDFs using Adobe's online services

    Integrates session management, file upload, conversion, and download
    with automatic rate limiting and usage tracking.
    """

    def __init__(
        self,
        session_dir: Path | None = None,
        use_session_rotation: bool = True,
        track_usage: bool = False,  # Changed: Disable local tracking by default
        enable_rate_limiting: bool = True,
        bypass_local_limits: bool = True,  # New: Allow bypassing local limits
    ):
        """
        Initialize the Adobe PDF Converter

        Args:
            session_dir: Directory for session data storage
            use_session_rotation: Enable anonymous session rotation
            track_usage: Enable local usage tracking (NOT recommended - Adobe tracks server-side)
            enable_rate_limiting: Enable rate limiting
            bypass_local_limits: Bypass local usage limits (mimics clearing browser data)
        """
        self.session_dir = session_dir
        self.use_session_rotation = use_session_rotation
        self.track_usage = track_usage
        self.enable_rate_limiting = enable_rate_limiting
        self.bypass_local_limits = bypass_local_limits

        # Will be initialized in __aenter__ or initialize()
        self.client: httpx.AsyncClient | None = None
        self.session_manager: SessionManager | AnonymousSessionManager | None = None
        self.uploader: FileUploader | None = None
        self.converter: ConversionManager | None = None
        self.downloader: FileDownloader | None = None
        self.rate_limiter: RateLimiter | None = None
        self.usage_tracker: FreeUsageTracker | None = None
        self.endpoints: dict[str, str] | None = None

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the converter and all components"""
        if self._initialized:
            return

        logger.info("Initializing Adobe PDF Converter...")

        # Create HTTP client
        self.client = httpx.AsyncClient(
            http2=True,
            timeout=httpx.Timeout(DEFAULT_TIMEOUT),
            follow_redirects=True,
            max_redirects=HTTP_MAX_REDIRECTS,
            limits=httpx.Limits(
                max_connections=HTTP_MAX_CONNECTIONS,
                max_keepalive_connections=HTTP_MAX_KEEPALIVE_CONNECTIONS,
                keepalive_expiry=HTTP_KEEPALIVE_EXPIRY,
            ),
            headers={
                **COMMON_HEADERS,
                "User-Agent": DEFAULT_USER_AGENT,
            },
        )

        # Initialize session manager
        if self.use_session_rotation:
            self.session_manager = AnonymousSessionManager(session_dir=self.session_dir)
            await self.session_manager.get_session()
        else:
            self.session_manager = SessionManager(self.client, session_dir=self.session_dir)
            await self.session_manager.initialize()

        # Initialize components
        self.uploader = FileUploader(self.client)
        self.converter = ConversionManager(self.client)
        self.downloader = FileDownloader(self.client)

        # Initialize optional components
        if self.enable_rate_limiting:
            self.rate_limiter = RateLimiter()

        if self.track_usage:
            self.usage_tracker = FreeUsageTracker(usage_dir=self.session_dir)

        self.endpoints = get_api_endpoints()

        self._initialized = True
        logger.info("Adobe PDF Converter initialized successfully")

    def _ensure_components(
        self,
    ) -> tuple[
        httpx.AsyncClient,
        SessionManager | AnonymousSessionManager,
        FileUploader,
        ConversionManager,
        FileDownloader,
    ]:
        """Return initialized core components or raise an error."""

        if (
            self.client is None
            or self.session_manager is None
            or self.uploader is None
            or self.converter is None
            or self.downloader is None
        ):
            raise AdobeHelperError(
                "AdobePDFConverter is not initialized. Call initialize() before converting.",
            )

        return (
            self.client,
            self.session_manager,
            self.uploader,
            self.converter,
            self.downloader,
        )

    async def convert_pdf_to_word(
        self,
        pdf_path: Path,
        output_path: Path | None = None,
        wait: bool = True,
        progress_callback: Callable[[UploadProgress], None] | None = None,
    ) -> Path:
        """
        Convert a PDF file to Word (DOCX) format

        Args:
            pdf_path: Path to input PDF file
            output_path: Path for output DOCX file (optional, auto-generated if None)
            wait: Wait for conversion to complete (default: True)
            progress_callback: Optional callback for progress updates

        Returns:
            Path to converted DOCX file

        Raises:
            QuotaExceededError: If daily conversion limit exceeded
            AdobeHelperError: If conversion fails
        """
        # Ensure initialized
        if not self._initialized:
            await self.initialize()

        client, _session_manager, uploader, converter, downloader = self._ensure_components()

        # Check usage quota (only if not bypassing local limits)
        if (
            self.track_usage
            and self.usage_tracker
            and not self.bypass_local_limits
            and not self.usage_tracker.can_convert()
        ):
            raise QuotaExceededError(
                "Daily conversion quota exceeded",
                limit=self.usage_tracker.daily_limit,
                current=self.usage_tracker.get_current_count(),
            )

        # Rate limiting
        if self.enable_rate_limiting and self.rate_limiter:
            await self.rate_limiter.wait()

        logger.info(f"Converting PDF to Word: {pdf_path.name}")

        try:
            # Get tenant ID from session manager
            tenant_id: str | None = None
            if isinstance(self.session_manager, SessionManager):
                tenant_id = self.session_manager.tenant_id
            elif isinstance(self.session_manager, AnonymousSessionManager):
                current_session = await self.session_manager.get_session()
                session_info = await current_session.ensure_access_token()
                tenant_id = session_info.tenant_id

            # Get endpoints with tenant substitution
            if tenant_id:
                logger.info(f"Using tenant-specific endpoints for tenant: {tenant_id}")
                endpoints = get_endpoints_for_session(tenant_id=tenant_id)
            else:
                logger.warning("No tenant ID available, using default endpoints")
                endpoints = get_api_endpoints()

            self.endpoints = endpoints

            upload_url = endpoints.get("upload", "")
            conversion_url = endpoints.get("conversion", "")
            status_url = endpoints.get("status", "")
            download_url = endpoints.get("download", "")

            unresolved = []
            for name, (url, placeholder) in {
                "upload": (upload_url, API_UPLOAD),
                "conversion": (conversion_url, API_CONVERT),
                "status": (status_url, API_STATUS),
                "download": (download_url, API_DOWNLOAD),
            }.items():
                if not url or url == placeholder:
                    unresolved.append(name)

            if unresolved:
                logger.error("API endpoints not configured: %s", ", ".join(unresolved))
                raise AdobeHelperError(
                    "Adobe API endpoints are not configured yet. "
                    "Capture the real endpoints (see docs/discovery/API_DISCOVERY.md) and update discovered_endpoints.json.",
                    details={"missing": ",".join(unresolved)},
                )

            headers = await self._refresh_access_token()

            # Step 1: Upload PDF file
            logger.info("Uploading PDF file...")
            upload_response = await self._with_token_retry(
                lambda h: uploader.upload_with_retry(
                    file_path=pdf_path,
                    upload_url=upload_url,
                    headers=h,
                    progress_callback=progress_callback,
                ),
                headers,
            )

            # Extract discovered tenant ID from uploader's discovery cache
            discovered_tenant = uploader.get_discovered_tenant_id()
            if discovered_tenant and discovered_tenant != tenant_id:
                logger.info(f"Using discovered numeric tenant ID: {discovered_tenant}")
                tenant_id = discovered_tenant

                # Update session with the discovered tenant
                if isinstance(self.session_manager, SessionManager):
                    self.session_manager.tenant_id = tenant_id
                    if self.session_manager.session_info:
                        self.session_manager.session_info.tenant_id = tenant_id
                elif isinstance(self.session_manager, AnonymousSessionManager):
                    session_mgr = await self.session_manager.get_session()
                    session_mgr.tenant_id = tenant_id
                    if session_mgr.session_info:
                        session_mgr.session_info.tenant_id = tenant_id

                # Rebuild endpoints with the discovered tenant
                endpoints = get_endpoints_for_session(tenant_id=tenant_id)
                self.endpoints = endpoints
                conversion_url = endpoints.get("conversion", "")
                status_url = endpoints.get("status", "")
                download_url = endpoints.get("download", "")

            # Step 2: Start conversion
            logger.info("Starting conversion job...")
            asset_uri = upload_response.get("asset_uri")

            if not asset_uri:
                raise AdobeHelperError(
                    "Upload response missing asset_uri",
                    details={"response": upload_response},
                )

            job = await self._with_token_retry(
                lambda h: converter.start_export_job(
                    asset_uri=asset_uri,
                    conversion_url=conversion_url,
                    headers=h,
                    conversion_type=ConversionType.PDF_TO_WORD,
                ),
                headers,
            )

            # Step 3: Wait for completion (if requested)
            if wait:
                logger.info("Waiting for conversion to complete...")
                status_data = await converter.wait_for_completion(
                    job_uri=job.job_uri,
                    status_url=status_url,
                    headers=headers,
                )

                result_asset_uri = converter.extract_asset_uri(status_data)

                if not result_asset_uri:
                    raise AdobeHelperError(
                        "Conversion status missing asset_uri",
                        details={"job_uri": job.job_uri, "status": status_data},
                    )

                # Fetch direct download URL
                logger.info("Fetching download URI...")
                download_response = await self._with_token_retry(
                    lambda h: client.get(
                        download_url,
                        params={
                            "asset_uri": result_asset_uri,
                            "make_direct_storage_uri": "true",
                        },
                        headers=h,
                        timeout=DEFAULT_TIMEOUT,
                    ),
                    headers,
                )
                download_response.raise_for_status()
                download_payload = download_response.json()

                direct_download = (
                    download_payload.get("download_uri")
                    or download_payload.get("downloadUrl")
                    or download_payload.get("uri")
                )
                direct_headers: dict[str, str] = {}
                payload_headers = download_payload.get("headers")
                if isinstance(payload_headers, dict):
                    direct_headers = {
                        str(key): str(value)
                        for key, value in payload_headers.items()
                        if value is not None
                    }

                if not direct_download:
                    raise AdobeHelperError(
                        "Download response missing URI",
                        details={"response": download_payload},
                    )

                # Step 4: Generate output path if not provided
                if output_path is None:
                    output_path = downloader.generate_output_filename(
                        pdf_path, conversion_type="docx"
                    )

                # Step 5: Download converted file
                logger.info("Downloading converted file...")
                result_path = await downloader.download_with_retry(
                    download_url=direct_download,
                    output_path=output_path,
                    headers=direct_headers,
                    progress_callback=progress_callback,
                )

                # Track usage
                if self.track_usage and self.usage_tracker:
                    self.usage_tracker.increment_usage(filename=pdf_path.name)

                # Update session conversion count
                if isinstance(self.session_manager, AnonymousSessionManager):
                    await self.session_manager.increment_and_check_rotation()
                elif isinstance(self.session_manager, SessionManager):
                    self.session_manager.increment_conversion_count()

                logger.info(f"Conversion complete: {result_path}")

                return result_path

            else:
                # Return job for async tracking
                logger.info(f"Conversion job submitted: {job.job_uri}")
                return job  # type: ignore

        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            raise

    async def _refresh_access_token(self) -> dict[str, str]:
        headers = {**COMMON_HEADERS}

        access_token: str | None = None

        if isinstance(self.session_manager, SessionManager):
            session = await self.session_manager.ensure_access_token()
            access_token = session.access_token

        elif isinstance(self.session_manager, AnonymousSessionManager):
            session_manager = await self.session_manager.get_session()
            info = await session_manager.ensure_access_token()
            access_token = info.access_token if info else None

        if not access_token:
            raise AdobeHelperError("Could not obtain Adobe access token")

        headers["Authorization"] = f"Bearer {access_token}"
        return headers

    async def _with_token_retry(
        self,
        operation,
        headers: dict[str, str],
        max_attempts: int = 2,
    ):
        last_error: Exception | None = None

        for attempt in range(max_attempts):
            try:
                return await operation(headers)
            except (UploadError, ConversionError, DownloadError) as exc:
                status = getattr(exc, "details", {}).get("status_code")
                if status in {401, 403} and attempt < max_attempts - 1:
                    logger.info("Access token rejected (status %s); refreshing", status)
                    headers.update(await self._refresh_access_token())
                    last_error = exc
                    continue
                raise
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in {401, 403} and attempt < max_attempts - 1:
                    logger.info(
                        "HTTP %s received; refreshing access token",
                        exc.response.status_code,
                    )
                    headers.update(await self._refresh_access_token())
                    last_error = exc
                    continue
                raise
        raise last_error if last_error else AdobeHelperError("Operation failed")

    async def close(self) -> None:
        """Close the converter and clean up resources"""
        if self.client:
            await self.client.aclose()

        if isinstance(self.session_manager, AnonymousSessionManager):
            await self.session_manager.close()

        self.endpoints = None
        self._initialized = False
        logger.info("Adobe PDF Converter closed")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    def get_usage_summary(self) -> dict | None:
        """
        Get usage statistics summary

        Returns:
            Usage summary dict if tracking enabled, None otherwise
        """
        if self.track_usage and self.usage_tracker:
            return self.usage_tracker.get_usage_summary()
        return None

    def get_session_stats(self) -> dict | None:
        """
        Get session statistics

        Returns:
            Session stats dict if using session rotation, None otherwise
        """
        if isinstance(self.session_manager, AnonymousSessionManager):
            return self.session_manager.get_session_stats()
        return None

    async def reset_session_data(self) -> None:
        """
        Reset all session data (mimics clearing browser data)

        This clears:
        - Usage tracking data
        - Session cookies
        - Access tokens
        - Conversion counters

        Use this when you hit limits and want to start fresh,
        similar to clearing browser data in Chrome.
        """
        logger.info("Resetting session data...")

        # Reset usage tracker
        if self.usage_tracker:
            self.usage_tracker.reset_usage()
            logger.info("✓ Usage tracking reset")

        # Clear cookies
        if isinstance(self.session_manager, AnonymousSessionManager):
            # Clear all saved cookies
            if self.session_manager.cookie_manager:
                count = self.session_manager.cookie_manager.clear_all_cookies()
                logger.info(f"✓ Cleared {count} cookie file(s)")

            # Force new session
            await self.session_manager.create_fresh_session()
            logger.info("✓ Created fresh session")

        elif isinstance(self.session_manager, SessionManager):
            # Clear session info
            self.session_manager.clear_session()
            # Re-initialize
            await self.session_manager.initialize()
            logger.info("✓ Session re-initialized")

        logger.info("Session reset complete - ready for new conversions")

    @classmethod
    async def create_with_fresh_session(
        cls,
        session_dir: Path | None = None,
        bypass_local_limits: bool = True,
    ) -> "AdobePDFConverter":
        """
        Create a new converter instance with completely fresh session data

        This is equivalent to:
        1. Clearing browser data in Chrome
        2. Creating a new converter instance

        Args:
            session_dir: Directory for session data storage
            bypass_local_limits: Whether to bypass local usage limits

        Returns:
            New AdobePDFConverter instance with fresh session
        """
        instance = cls(
            session_dir=session_dir,
            use_session_rotation=True,
            track_usage=False,  # Don't track locally
            bypass_local_limits=bypass_local_limits,
        )
        await instance.initialize()
        await instance.reset_session_data()
        return instance
