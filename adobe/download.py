"""
File download handler for Adobe Helper

This module handles downloading converted files from Adobe's servers
with streaming, progress tracking, and integrity verification.
"""

import logging
from collections.abc import Callable
from pathlib import Path

import httpx

from adobe.constants import (
    DOWNLOAD_CHUNK_SIZE,
    DOWNLOAD_TIMEOUT,
    ERROR_DOWNLOAD_FAILED,
    SUCCESS_DOWNLOAD,
)
from adobe.exceptions import DownloadError
from adobe.models import UploadProgress
from adobe.utils import format_file_size, sanitize_filename

logger = logging.getLogger(__name__)


class FileDownloader:
    """
    Handles downloading converted files from Adobe's servers

    Provides streaming download with progress tracking, integrity
    verification, and automatic retry logic.
    """

    def __init__(self, client: httpx.AsyncClient):
        """
        Initialize the file downloader

        Args:
            client: HTTPX async client for making requests
        """
        self.client = client

    async def download_file(
        self,
        download_url: str,
        output_path: Path,
        headers: dict[str, str],
        progress_callback: Callable[[UploadProgress], None] | None = None,
    ) -> Path:
        """
        Download a converted file to disk

        Args:
            download_url: URL to download the file from
            output_path: Path where the file should be saved
            progress_callback: Optional callback for download progress

        Returns:
            Path to the downloaded file

        Raises:
            DownloadError: If download fails
        """
        logger.info(f"Downloading file to: {output_path}")

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Stream the download
            merged_headers = {key: value for key, value in headers.items() if value is not None}

            async with self.client.stream(
                "GET", download_url, headers=merged_headers, timeout=DOWNLOAD_TIMEOUT
            ) as response:
                response.raise_for_status()

                # Get total file size if available
                total_size = int(response.headers.get("content-length", 0))
                downloaded_size = 0

                logger.info(
                    f"Starting download ({format_file_size(total_size) if total_size else 'unknown size'})"
                )

                # Write to file in chunks
                with open(output_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=DOWNLOAD_CHUNK_SIZE):
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        # Report progress
                        if progress_callback and total_size > 0:
                            progress = UploadProgress(
                                bytes_uploaded=downloaded_size,
                                total_bytes=total_size,
                                percentage=(downloaded_size / total_size) * 100,
                            )
                            progress_callback(progress)

                # Verify download completed
                if total_size > 0 and downloaded_size != total_size:
                    raise DownloadError(
                        "Incomplete download",
                        details={
                            "expected": total_size,
                            "received": downloaded_size,
                        },
                    )

                logger.info(SUCCESS_DOWNLOAD.format(output_path=output_path))

                return output_path

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during download: {e}")
            raise DownloadError(
                ERROR_DOWNLOAD_FAILED.format(reason=f"HTTP {e.response.status_code}"),
                details={
                    "status_code": e.response.status_code,
                    "url": download_url,
                },
            ) from e

        except httpx.RequestError as e:
            logger.error(f"Network error during download: {e}")
            raise DownloadError(
                ERROR_DOWNLOAD_FAILED.format(reason="Network error"),
                details={"error": str(e), "url": download_url},
            ) from e

        except OSError as e:
            logger.error(f"File I/O error during download: {e}")
            raise DownloadError(
                ERROR_DOWNLOAD_FAILED.format(reason="File I/O error"),
                details={"error": str(e), "output_path": str(output_path)},
            ) from e

    async def download_with_retry(
        self,
        download_url: str,
        output_path: Path,
        headers: dict[str, str],
        max_retries: int = 3,
        progress_callback: Callable[[UploadProgress], None] | None = None,
    ) -> Path:
        """
        Download file with automatic retry on failure

        Args:
            download_url: URL to download the file from
            output_path: Path where the file should be saved
            max_retries: Maximum number of retry attempts
            progress_callback: Optional callback for download progress

        Returns:
            Path to the downloaded file

        Raises:
            DownloadError: If all download attempts fail
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.info(f"Download attempt {attempt + 1}/{max_retries}")
                return await self.download_file(
                    download_url, output_path, headers, progress_callback
                )

            except DownloadError as e:
                last_error = e
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")

                # Clean up partial download
                if output_path.exists():
                    try:
                        output_path.unlink()
                        logger.debug(f"Cleaned up partial download: {output_path}")
                    except OSError:
                        pass

                # Wait before retry (except on last attempt)
                if attempt < max_retries - 1:
                    import asyncio

                    wait_time = 2 ** (attempt + 1)  # Exponential backoff
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)

        # All retries failed
        raise DownloadError(
            f"Download failed after {max_retries} attempts",
            details={"last_error": str(last_error)},
        ) from last_error

    def generate_output_filename(self, input_path: Path, conversion_type: str = "docx") -> Path:
        """
        Generate output filename from input path and conversion type

        Args:
            input_path: Path to input file
            conversion_type: Output file extension

        Returns:
            Path for output file
        """
        # Get base name and directory
        base_name = input_path.stem
        directory = input_path.parent

        # Sanitize filename
        safe_name = sanitize_filename(base_name)

        # Create output filename
        output_name = f"{safe_name}.{conversion_type}"

        return directory / output_name

    async def verify_file_integrity(
        self, file_path: Path, expected_size: int | None = None
    ) -> bool:
        """
        Verify downloaded file integrity

        Args:
            file_path: Path to downloaded file
            expected_size: Expected file size in bytes (optional)

        Returns:
            True if file is valid, False otherwise
        """
        if not file_path.exists():
            logger.error(f"Downloaded file not found: {file_path}")
            return False

        if not file_path.is_file():
            logger.error(f"Downloaded path is not a file: {file_path}")
            return False

        # Check file size
        actual_size = file_path.stat().st_size

        if actual_size == 0:
            logger.error(f"Downloaded file is empty: {file_path}")
            return False

        if expected_size is not None and actual_size != expected_size:
            logger.warning(f"File size mismatch: expected {expected_size}, got {actual_size}")
            return False

        logger.debug(f"File integrity verified: {file_path} ({format_file_size(actual_size)})")
        return True
