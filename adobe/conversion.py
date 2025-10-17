"""
Conversion workflow manager for Adobe Helper

This module handles the conversion job lifecycle, including job submission,
status polling, and completion tracking.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, cast

import httpx

from adobe.constants import (
    CONVERSION_TIMEOUT,
    ERROR_CONVERSION_FAILED,
    MAX_POLL_ATTEMPTS,
    MAX_POLL_INTERVAL,
    POLL_BACKOFF_MULTIPLIER,
    POLL_INTERVAL,
    STATUS_CONVERTING,
    STATUS_POLLING,
    STATUS_WAITING,
)
from adobe.exceptions import ConversionError, TimeoutError
from adobe.models import ConversionJob, ConversionStatus, ConversionType
from adobe.utils import extract_asset_result

logger = logging.getLogger(__name__)


class ConversionManager:
    """
    Manages PDF conversion jobs and status polling

    Handles job submission, status tracking, and waiting for completion
    with adaptive polling intervals.
    """

    def __init__(self, client: httpx.AsyncClient):
        """
        Initialize the conversion manager

        Args:
            client: HTTPX async client for making requests
        """
        self.client = client

    async def start_export_job(
        self,
        asset_uri: str,
        conversion_url: str,
        headers: dict[str, str],
        conversion_type: ConversionType = ConversionType.PDF_TO_WORD,
    ) -> ConversionJob:
        """Kick off the export job and return conversion metadata."""

        logger.info("Submitting export job to Adobe API")

        payload = {
            "asset_uri": asset_uri,
            "name": "document.docx",
            "format": self._get_target_format(conversion_type),
            "context": "PDFNowLifeCycle",
            "persistence": "transient",
            "do_ocr": True,
            "ocr_lang": "en-US",
        }

        try:
            response = await self.client.post(
                conversion_url,
                json=payload,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("HTTP error starting export job: %s", exc)
            raise ConversionError(
                ERROR_CONVERSION_FAILED.format(reason=f"HTTP {exc.response.status_code}"),
                details={
                    "status_code": exc.response.status_code,
                    "response": exc.response.text[:500],
                },
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Network error starting export job: %s", exc)
            raise ConversionError(
                ERROR_CONVERSION_FAILED.format(reason="Network error"),
                details={"error": str(exc)},
            ) from exc

        raw_payload = response.json()
        if not isinstance(raw_payload, dict):
            raise ConversionError(
                "Export job response malformed",
                details={"response": str(raw_payload)[:500]},
            )

        payload = cast(dict[str, Any], raw_payload)
        job_uri = payload.get("job_uri")

        if not job_uri:
            raise ConversionError(
                "Export job response missing job_uri",
                details={"response": payload},
            )

        job = ConversionJob.model_validate(
            {
                "job_uri": job_uri,
                "asset_uri": asset_uri,
                "status": ConversionStatus.PROCESSING,
                "conversion_type": conversion_type,
                "created_at": datetime.now(),
            }
        )

        logger.info("Adobe export job accepted: %s", job_uri)
        return job

    def _get_target_format(self, conversion_type: ConversionType) -> str:
        """Get target format for conversion type"""
        format_map = {
            ConversionType.PDF_TO_WORD: "docx",
            ConversionType.PDF_TO_EXCEL: "xlsx",
            ConversionType.PDF_TO_PPT: "pptx",
            ConversionType.PDF_TO_IMAGE: "jpg",
        }
        return format_map.get(conversion_type, "docx")

    async def check_status(
        self, job_uri: str, status_url: str, headers: dict[str, str]
    ) -> dict[str, Any]:
        """
        Check the status of a conversion job

        Args:
            job_uri: Conversion job URI
            status_url: URL to check job status

        Returns:
            Dictionary with status information

        Raises:
            ConversionError: If status check fails
        """
        try:
            response = await self.client.get(
                status_url,
                params={"job_uri": job_uri},
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()

            raw_payload = response.json()
            if not isinstance(raw_payload, dict):
                raise ConversionError(
                    "Job status response malformed",
                    details={"job_uri": job_uri, "response": str(raw_payload)[:500]},
                )

            return cast(dict[str, Any], raw_payload)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error checking status: {e}")
            raise ConversionError(
                f"Failed to check job status: HTTP {e.response.status_code}",
                details={"job_uri": job_uri, "status_code": e.response.status_code},
            ) from e

        except httpx.RequestError as e:
            logger.error(f"Network error checking status: {e}")
            raise ConversionError(
                "Network error checking job status",
                details={"job_uri": job_uri, "error": str(e)},
            ) from e

    async def wait_for_completion(
        self,
        job_uri: str,
        status_url: str,
        headers: dict[str, str],
        poll_interval: float = POLL_INTERVAL,
        timeout: float = CONVERSION_TIMEOUT,
    ) -> dict:
        """
        Wait for conversion job to complete with adaptive polling

        Args:
            job_id: Conversion job ID
            status_url: URL to check job status
            poll_interval: Initial polling interval in seconds
            timeout: Maximum time to wait in seconds

        Returns:
            Dictionary with final job status and download URL

        Raises:
            ConversionError: If conversion fails
            TimeoutError: If conversion times out
        """
        logger.info(STATUS_WAITING)

        start_time = asyncio.get_event_loop().time()
        current_interval = poll_interval
        attempts = 0

        while True:
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(
                    f"Conversion timed out after {elapsed:.1f}s",
                    timeout=timeout,
                    details={"job_uri": job_uri, "elapsed": elapsed},
                )

            # Check max attempts
            if attempts >= MAX_POLL_ATTEMPTS:
                raise TimeoutError(
                    f"Max polling attempts ({MAX_POLL_ATTEMPTS}) exceeded",
                    timeout=timeout,
                    details={"job_uri": job_uri, "attempts": attempts},
                )

            # Poll status
            logger.debug(f"{STATUS_POLLING} (attempt {attempts + 1})")
            status_data = await self.check_status(job_uri, status_url, headers)

            # Parse status
            state = self._parse_status(status_data)

            # Check completion
            if state == ConversionStatus.COMPLETED:
                logger.info("Conversion completed successfully")
                return status_data

            if state == ConversionStatus.FAILED:
                error_msg = (
                    status_data.get("error") or status_data.get("message") or "Unknown error"
                )
                raise ConversionError(
                    f"Conversion failed: {error_msg}",
                    details={"job_uri": job_uri, "status": status_data},
                )

            # Update progress if available
            progress = status_data.get("progress", 0)
            logger.info(f"{STATUS_CONVERTING} {progress}%")

            # Wait before next poll with backoff
            await asyncio.sleep(current_interval)

            # Increase polling interval gradually
            current_interval = min(
                current_interval * POLL_BACKOFF_MULTIPLIER,
                MAX_POLL_INTERVAL,
            )

            attempts += 1

    def _parse_status(self, status_data: dict) -> ConversionStatus:
        """
        Parse status from API response

        Args:
            status_data: Status response from API

        Returns:
            ConversionStatus enum value
        """
        # Try various status field names
        status_str = (
            status_data.get("status")
            or status_data.get("state")
            or status_data.get("jobStatus")
            or ""
        ).lower()

        # Map status strings to ConversionStatus
        if status_str in ["completed", "complete", "done", "success"]:
            return ConversionStatus.COMPLETED

        if status_str in ["failed", "error", "cancelled", "canceled"]:
            return ConversionStatus.FAILED

        if status_str in ["processing", "converting", "in_progress", "running"]:
            return ConversionStatus.PROCESSING

        if status_str in ["pending", "queued", "waiting"]:
            return ConversionStatus.PENDING

        # Default to processing
        return ConversionStatus.PROCESSING

    def extract_asset_uri(self, status_data: dict) -> str | None:
        """Extract the asset_uri for the converted document from status payload."""

        asset_section = extract_asset_result(status_data)
        if not asset_section:
            return None

        asset_uri = (
            asset_section.get("asset_uri")
            or asset_section.get("assetUri")
            or asset_section.get("uri")
        )
        if isinstance(asset_uri, str) and asset_uri:
            return asset_uri

        return None
