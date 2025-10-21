"""Asset upload workflow."""

import asyncio
import base64
import hashlib
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import httpx

from adobe.constants import (
    ERROR_FILE_NOT_FOUND,
    ERROR_FILE_TOO_LARGE,
    ERROR_INVALID_PDF,
    ERROR_UPLOAD_FAILED,
    MAX_FILE_SIZE,
    SUCCESS_UPLOAD,
    UPLOAD_TIMEOUT,
)
from adobe.exceptions import UploadError, ValidationError
from adobe.models import FileInfo, UploadProgress
from adobe.utils import (
    calculate_file_checksum,
    format_file_size,
    generate_request_id,
    now_seconds,
    validate_pdf_file,
)

logger = logging.getLogger(__name__)

SIMPLE_UPLOAD_THRESHOLD = 5 * 1024 * 1024
MIN_BLOCK_SIZE = 5 * 1024 * 1024
MAX_BLOCK_SIZE = 50 * 1024 * 1024
DISCOVERY_TTL_SECONDS = 300.0
DEFAULT_PERSISTENCE = "transient"
API_CLIENT_ID = "api_browser"
API_APP_INFO = "dc-web-app"
DEFAULT_USER_ACTION = "pdf-to-word"


class FileUploader:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self._discovery_cache: dict[str, Any] | None = None
        self._discovery_base: str | None = None
        self._discovery_expires_at: float = 0.0

    async def validate_file(self, file_path: Path) -> FileInfo:
        if not file_path.exists():
            raise ValidationError(
                ERROR_FILE_NOT_FOUND.format(path=file_path),
                details={"file_path": str(file_path)},
            )

        if not file_path.is_file():
            raise ValidationError(
                f"Path is not a file: {file_path}",
                details={"file_path": str(file_path)},
            )

        file_size = file_path.stat().st_size

        if file_size > MAX_FILE_SIZE:
            raise ValidationError(
                ERROR_FILE_TOO_LARGE.format(
                    max_size=format_file_size(MAX_FILE_SIZE),
                    size=format_file_size(file_size),
                ),
                details={"file_size": file_size, "max_size": MAX_FILE_SIZE},
            )

        if not validate_pdf_file(file_path):
            raise ValidationError(
                ERROR_INVALID_PDF.format(path=file_path),
                details={"file_path": str(file_path)},
            )

        checksum = calculate_file_checksum(file_path)
        logger.info(
            "File validated: %s (%s, checksum: %s...)",
            file_path.name,
            format_file_size(file_size),
            checksum[:8],
        )

        return FileInfo(
            file_path=file_path,
            file_name=file_path.name,
            file_size=file_size,
            mime_type="application/pdf",
            checksum=checksum,
        )

    async def upload_asset(
        self,
        file_path: Path,
        upload_url: str,
        headers: dict[str, str],
        progress_callback: Callable[[UploadProgress], None] | None = None,
    ) -> dict[str, Any]:
        file_info = await self.validate_file(file_path)
        discovery, base_url = await self._get_discovery(upload_url, headers)

        resources = discovery.get("resources", {}).get("assets", {})
        upload_resource = resources.get("upload")
        block_init_resource = resources.get("block_upload_initialize")
        block_finalize_resource = resources.get("block_upload_finalize")
        monitor_resource = resources.get("upload_status")

        if (
            file_info.file_size > SIMPLE_UPLOAD_THRESHOLD
            and block_init_resource
            and block_finalize_resource
            and monitor_resource
        ):
            response_payload = await self._upload_large(
                file_info,
                block_init_resource,
                block_finalize_resource,
                monitor_resource,
                headers,
                progress_callback,
            )
        else:
            simple_uri = self._resolve_resource_uri(
                upload_resource,
                upload_url,
                stage="upload",
            )
            response_payload = await self._upload_small(
                file_info,
                simple_uri,
                upload_resource,
                headers,
                progress_callback,
            )

        return self._extract_asset_metadata(response_payload)

    def get_discovered_tenant_id(self) -> str | None:
        """Get the most recently discovered tenant ID from the discovery cache."""
        if self._discovery_cache:
            return self._discovery_cache.get("_discovered_tenant_id")
        return None

    async def upload_with_retry(
        self,
        file_path: Path,
        upload_url: str,
        headers: dict[str, str],
        max_retries: int = 3,
        progress_callback: Callable[[UploadProgress], None] | None = None,
    ) -> dict[str, Any]:
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.info("Upload attempt %s/%s", attempt + 1, max_retries)
                return await self.upload_asset(
                    file_path,
                    upload_url,
                    headers,
                    progress_callback,
                )
            except UploadError as exc:
                last_error = exc
                logger.warning("Upload attempt %s failed: %s", attempt + 1, exc)

                if isinstance(exc, ValidationError):
                    raise

                if attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    logger.info("Waiting %ss before retry...", wait_time)
                    await asyncio.sleep(wait_time)

        raise UploadError(
            f"Upload failed after {max_retries} attempts",
            details={"last_error": str(last_error)},
        ) from last_error

    async def _upload_small(
        self,
        file_info: FileInfo,
        upload_uri: str,
        resource: dict[str, Any] | None,
        headers: dict[str, str],
        progress_callback: Callable[[UploadProgress], None] | None,
    ) -> dict[str, Any]:
        request_id = generate_request_id()
        request_headers = self._augment_headers(headers, request_id)
        if resource:
            request_headers["Accept"] = self._select_media_type(
                resource, "accept", "application/json"
            )

        logger.info("Uploading PDF via multipart to %s", upload_uri)

        try:
            with open(file_info.file_path, "rb") as handle:
                files = {"file": (file_info.file_name, handle, file_info.mime_type)}
                response = await self.client.post(
                    upload_uri,
                    files=files,
                    headers=request_headers,
                    timeout=UPLOAD_TIMEOUT,
                )
                response.raise_for_status()
                payload = self._ensure_dict(response.json(), "upload")
        except httpx.HTTPStatusError as exc:
            logger.error("HTTP error during asset upload: %s", exc)
            raise UploadError(
                ERROR_UPLOAD_FAILED.format(reason=f"HTTP {exc.response.status_code}"),
                details={
                    "status_code": exc.response.status_code,
                    "response": exc.response.text[:500],
                },
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Network error during asset upload: %s", exc)
            raise UploadError(
                ERROR_UPLOAD_FAILED.format(reason="Network error"),
                details={"error": str(exc)},
            ) from exc

        if progress_callback:
            progress_callback(
                UploadProgress(
                    bytes_uploaded=file_info.file_size,
                    total_bytes=file_info.file_size,
                    percentage=100.0,
                )
            )

        logger.info(SUCCESS_UPLOAD.format(filename=file_info.file_name))
        return payload

    async def _upload_large(
        self,
        file_info: FileInfo,
        init_resource: dict[str, Any],
        finalize_resource: dict[str, Any],
        status_resource: dict[str, Any],
        headers: dict[str, str],
        progress_callback: Callable[[UploadProgress], None] | None,
    ) -> dict[str, Any]:
        block_size = self._determine_block_size(file_info.file_size)
        init_uri = self._resolve_resource_uri(init_resource, None, stage="initialize")
        init_headers = self._augment_headers(headers, generate_request_id())
        init_headers["Accept"] = self._select_media_type(
            init_resource,
            "accept",
            "application/json",
        )
        init_headers["Content-Type"] = self._select_media_type(
            init_resource,
            "content_type",
            "application/json",
        )

        init_payload = {
            "size": file_info.file_size,
            "block_size": block_size,
            "persistence": DEFAULT_PERSISTENCE,
            "content_type": file_info.mime_type,
        }

        try:
            init_response = await self.client.post(
                init_uri,
                json=init_payload,
                headers=init_headers,
                timeout=UPLOAD_TIMEOUT,
            )
            init_response.raise_for_status()
            init_data = self._ensure_dict(init_response.json(), "initialize")
        except httpx.HTTPStatusError as exc:
            raise UploadError(
                ERROR_UPLOAD_FAILED.format(reason=f"HTTP {exc.response.status_code}"),
                details={"stage": "initialize", "status_code": exc.response.status_code},
            ) from exc
        except httpx.RequestError as exc:
            raise UploadError(
                ERROR_UPLOAD_FAILED.format(reason="Network error during initialize"),
                details={"stage": "initialize", "error": str(exc)},
            ) from exc

        links_container = init_data.get("_links") or {}
        upload_links = (
            links_container.get("upload_links") or links_container.get("uploadLinks") or []
        )
        if not upload_links:
            raise UploadError(
                ERROR_UPLOAD_FAILED.format(reason="Upload links missing"),
                details={"stage": "initialize", "response": init_data},
            )

        bytes_uploaded = 0
        md5_hasher = hashlib.md5()

        with open(file_info.file_path, "rb") as stream:
            for entry in upload_links:
                uri = entry.get("uri") or entry.get("href")
                if not uri:
                    raise UploadError(
                        ERROR_UPLOAD_FAILED.format(reason="Upload link missing URI"),
                        details={"stage": "upload"},
                    )

                chunk = stream.read(block_size)
                if not chunk:
                    break

                md5_hasher.update(chunk)
                await self._upload_chunk(uri=uri, data=chunk, headers=headers)
                bytes_uploaded += len(chunk)

                if progress_callback:
                    progress_callback(
                        UploadProgress(
                            bytes_uploaded=bytes_uploaded,
                            total_bytes=file_info.file_size,
                            percentage=min(100.0, (bytes_uploaded / file_info.file_size) * 100),
                        )
                    )

            remainder = stream.read(1)
            if remainder:
                raise UploadError(
                    ERROR_UPLOAD_FAILED.format(reason="Upload links exhausted"),
                    details={"stage": "upload", "bytes_uploaded": bytes_uploaded},
                )

        content_md5 = base64.b64encode(md5_hasher.digest()).decode("ascii")

        finalize_headers = self._augment_headers(headers, generate_request_id())
        finalize_headers["Accept"] = self._select_media_type(
            finalize_resource,
            "accept",
            "application/json",
        )
        finalize_headers["Content-Type"] = self._select_media_type(
            finalize_resource,
            "content_type",
            "application/json",
        )

        finalize_payload = {
            "_links": init_data.get("_links", {}),
            "upload_info": init_data.get("upload_info"),
            "size": file_info.file_size,
            "content_md5": content_md5,
            "content_type": file_info.mime_type,
            "name": file_info.file_name,
            "persistence": DEFAULT_PERSISTENCE,
            "on_dup_name": "auto_rename",
        }

        finalize_uri = self._resolve_resource_uri(finalize_resource, "", stage="finalize")

        try:
            finalize_response = await self.client.post(
                finalize_uri,
                json=finalize_payload,
                headers=finalize_headers,
                timeout=UPLOAD_TIMEOUT,
            )
            finalize_response.raise_for_status()
            finalize_data = self._ensure_dict(finalize_response.json(), "finalize")
        except httpx.HTTPStatusError as exc:
            raise UploadError(
                ERROR_UPLOAD_FAILED.format(reason=f"HTTP {exc.response.status_code}"),
                details={"stage": "finalize", "status_code": exc.response.status_code},
            ) from exc
        except httpx.RequestError as exc:
            raise UploadError(
                ERROR_UPLOAD_FAILED.format(reason="Network error during finalize"),
                details={"stage": "finalize", "error": str(exc)},
            ) from exc

        monitor_link = finalize_data.get("monitor_link") or finalize_data.get("monitorLink")
        if monitor_link:
            monitor_uri = monitor_link.get("uri") or monitor_link.get("href")
            monitor_payload = await self._poll_upload_status(
                monitor_uri,
                status_resource,
                headers,
            )
            finalize_data = monitor_payload

        if progress_callback:
            progress_callback(
                UploadProgress(
                    bytes_uploaded=file_info.file_size,
                    total_bytes=file_info.file_size,
                    percentage=100.0,
                )
            )

        return finalize_data

    async def _upload_chunk(self, uri: str, data: bytes, headers: dict[str, str]) -> None:
        chunk_headers = self._augment_headers(headers, generate_request_id())
        chunk_headers["Content-Type"] = "application/octet-stream"
        chunk_headers["Content-Length"] = str(len(data))

        response = await self.client.put(
            uri,
            content=data,
            headers=chunk_headers,
            timeout=UPLOAD_TIMEOUT,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise UploadError(
                ERROR_UPLOAD_FAILED.format(reason=f"HTTP {exc.response.status_code}"),
                details={"stage": "chunk", "status_code": exc.response.status_code},
            ) from exc

    async def _poll_upload_status(
        self,
        monitor_uri: str | None,
        status_resource: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        if not monitor_uri:
            raise UploadError(
                ERROR_UPLOAD_FAILED.format(reason="Monitor URI missing"),
                details={"stage": "monitor"},
            )

        accept = self._select_media_type(status_resource, "accept", "application/json")
        retry_interval_ms = status_resource.get("retry_interval", 2000)

        while True:
            request_headers = self._augment_headers(headers, generate_request_id())
            request_headers["Accept"] = accept

            response = await self.client.get(
                monitor_uri,
                headers=request_headers,
                timeout=UPLOAD_TIMEOUT,
            )
            response.raise_for_status()
            payload = self._ensure_dict(response.json(), "monitor")

            status = (payload.get("status") or payload.get("state") or "").lower()
            if status not in {"processing", "in progress", "pending"}:
                return payload

            sleep_ms = payload.get("retry_interval", retry_interval_ms)
            await asyncio.sleep(max(1.0, sleep_ms / 1000.0))

    def _augment_headers(
        self, base_headers: dict[str, str], request_id: str | None
    ) -> dict[str, str]:
        if "Authorization" not in base_headers:
            raise UploadError("Authorization header missing", details={})

        headers = {key: value for key, value in base_headers.items()}
        if request_id:
            headers["X-Request-ID"] = request_id
        headers["X-Api-Client-Id"] = API_CLIENT_ID
        headers["X-Api-App-Info"] = API_APP_INFO
        headers["X-User-Action-Name"] = DEFAULT_USER_ACTION
        headers.setdefault("Accept", "application/json")
        return headers

    async def _get_discovery(
        self,
        upload_url: str,
        headers: dict[str, str],
    ) -> tuple[dict[str, Any], str]:
        base_url = self._extract_base_url(upload_url)
        now = now_seconds()

        if (
            self._discovery_cache
            and self._discovery_base == base_url
            and now < self._discovery_expires_at
        ):
            return self._discovery_cache, base_url

        request_headers = self._augment_headers(headers, generate_request_id())
        discovery_url = f"{base_url}/discovery"

        try:
            response = await self.client.get(
                discovery_url,
                headers=request_headers,
                timeout=UPLOAD_TIMEOUT,
            )
            response.raise_for_status()
            data = self._ensure_dict(response.json(), "discovery")

            # Extract the real tenant ID from the discovery response
            # The discovery endpoint URLs contain the actual numeric tenant ID
            tenant_id = self._extract_tenant_from_discovery(data, base_url)
            if tenant_id:
                logger.info(f"Discovered numeric tenant ID: {tenant_id}")
                # Store it for session manager to use
                data["_discovered_tenant_id"] = tenant_id

        except httpx.HTTPStatusError as exc:
            raise UploadError(
                ERROR_UPLOAD_FAILED.format(reason=f"HTTP {exc.response.status_code}"),
                details={"stage": "discovery", "status_code": exc.response.status_code},
            ) from exc
        except httpx.RequestError as exc:
            raise UploadError(
                ERROR_UPLOAD_FAILED.format(reason="Network error during discovery"),
                details={"stage": "discovery", "error": str(exc)},
            ) from exc

        self._discovery_cache = data
        self._discovery_base = base_url
        self._discovery_expires_at = now + DISCOVERY_TTL_SECONDS
        return data, base_url

    def _extract_tenant_from_discovery(
        self, discovery_data: dict[str, Any], base_url: str
    ) -> str | None:
        """Extract the numeric tenant ID from discovery response URLs."""
        import re

        # Check resource URIs in the discovery response
        resources = discovery_data.get("resources", {}).get("assets", {})

        for resource in resources.values():
            if isinstance(resource, dict):
                uri = resource.get("uri") or resource.get("href", "")
                if isinstance(uri, str):
                    # Extract numeric tenant from URL pattern: /{tenant_id}/
                    match = re.search(r"/(\d{10,})/", uri)
                    if match:
                        return match.group(1)

        return None

    def _extract_base_url(self, upload_url: str) -> str:
        parsed = urlparse(upload_url)
        if not parsed.scheme or not parsed.netloc:
            raise UploadError(
                ERROR_UPLOAD_FAILED.format(reason="Invalid upload URL"),
                details={"url": upload_url},
            )
        return f"{parsed.scheme}://{parsed.netloc}"

    def _resolve_resource_uri(
        self,
        resource: dict[str, Any] | None,
        fallback: str | None,
        *,
        stage: str,
    ) -> str:
        if resource:
            uri = resource.get("uri") or resource.get("href")
            if isinstance(uri, str) and uri:
                return uri

        if fallback and fallback.strip():
            return fallback

        raise UploadError(
            ERROR_UPLOAD_FAILED.format(reason="Resource URI missing"),
            details={"stage": stage},
        )

    def _select_media_type(self, resource: dict[str, Any] | None, key: str, default: str) -> str:
        if not resource:
            return default

        value = resource.get(key)
        if isinstance(value, dict) and value:
            first = next(iter(value.values()))
            if isinstance(first, str) and first:
                return first
        if isinstance(value, str) and value:
            return value
        return default

    def _determine_block_size(self, file_size: int) -> int:
        block_size = max(MIN_BLOCK_SIZE, file_size // 10 or MIN_BLOCK_SIZE)
        block_size = min(block_size, MAX_BLOCK_SIZE)
        remainder = block_size % MIN_BLOCK_SIZE
        if remainder:
            block_size += MIN_BLOCK_SIZE - remainder
        return block_size

    def _extract_asset_metadata(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise UploadError(
                ERROR_UPLOAD_FAILED.format(reason="Unexpected upload response"),
                details={"response": payload},
            )

        asset_result = payload.get("asset_result") or payload.get("assetResult")
        if isinstance(asset_result, dict):
            payload = asset_result

        asset_uri = payload.get("asset_uri") or payload.get("uri")
        if not asset_uri:
            raise UploadError(
                ERROR_UPLOAD_FAILED.format(reason="Upload response missing asset_uri"),
                details={"response": payload},
            )

        payload["asset_uri"] = asset_uri
        return payload

    def _ensure_dict(self, payload: Any, stage: str) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise UploadError(
                ERROR_UPLOAD_FAILED.format(reason="Unexpected response structure"),
                details={"stage": stage, "response": str(payload)[:500]},
            )
        return cast(dict[str, Any], payload)
