"""
Data models for Adobe Helper

This module defines the core data structures used throughout the library
using Pydantic for validation and serialization.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConversionStatus(str, Enum):
    """Status of a PDF conversion job"""

    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ConversionType(str, Enum):
    """Supported conversion types"""

    PDF_TO_WORD = "pdf-to-word"
    PDF_TO_EXCEL = "pdf-to-excel"
    PDF_TO_PPT = "pdf-to-ppt"
    PDF_TO_IMAGE = "pdf-to-image"


class ConversionJob(BaseModel):
    """Represents a conversion job in Adobe's system"""

    job_id: str | None = Field(
        None,
        description="Unique identifier for the conversion job (legacy flow)",
        deprecated=True,
    )
    job_uri: str | None = Field(None, description="URI returned by Adobe for the conversion job")
    asset_uri: str | None = Field(None, description="Asset URI for uploaded or converted resources")
    status: ConversionStatus = Field(
        default=ConversionStatus.PENDING, description="Current status of the job"
    )
    upload_id: str | None = Field(
        None,
        description="Upload identifier from legacy multipart upload (deprecated)",
        deprecated=True,
    )
    download_url: str | None = Field(None, description="URL to download converted file")
    error_message: str | None = Field(None, description="Error message if conversion failed")
    created_at: datetime | None = Field(
        default_factory=datetime.now, description="When the job was created"
    )
    completed_at: datetime | None = Field(None, description="When the job completed")
    conversion_type: ConversionType = Field(
        default=ConversionType.PDF_TO_WORD, description="Type of conversion"
    )
    progress: int | None = Field(
        None, ge=0, le=100, description="Conversion progress percentage (0-100)"
    )

    model_config = ConfigDict(use_enum_values=False)


class FileInfo(BaseModel):
    """Information about a file to be converted"""

    file_path: Path = Field(..., description="Path to the PDF file")
    file_name: str = Field(..., description="Name of the file")
    file_size: int = Field(..., ge=0, description="Size of the file in bytes")
    mime_type: str = Field(default="application/pdf", description="MIME type of the file")
    checksum: str | None = Field(None, description="MD5 checksum of the file")

    @field_validator("file_path")
    @classmethod
    def validate_file_exists(cls, v: Path) -> Path:
        """Validate that the file exists"""
        if not v.exists():
            raise ValueError(f"File does not exist: {v}")
        if not v.is_file():
            raise ValueError(f"Path is not a file: {v}")
        return v

    @field_validator("file_name")
    @classmethod
    def validate_pdf_extension(cls, v: str) -> str:
        """Validate that the file has a .pdf extension"""
        if not v.lower().endswith(".pdf"):
            raise ValueError(f"File must have .pdf extension: {v}")
        return v

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, v: str) -> str:
        """Validate that the MIME type is PDF"""
        if v != "application/pdf":
            raise ValueError(f"MIME type must be application/pdf, got: {v}")
        return v

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SessionInfo(BaseModel):
    """Information about an Adobe session"""

    session_id: str | None = Field(None, description="Session identifier")
    csrf_token: str | None = Field(None, description="CSRF token for requests")
    cookies: dict[str, str] = Field(default_factory=dict, description="Session cookies")
    created_at: datetime = Field(
        default_factory=datetime.now, description="When the session was created"
    )
    expires_at: datetime | None = Field(None, description="When the session expires")
    conversion_count: int = Field(default=0, ge=0, description="Number of conversions in session")
    is_anonymous: bool = Field(default=True, description="Whether this is an anonymous session")
    access_token: str | None = Field(None, description="Guest access token for API calls")
    access_token_expires_at: datetime | None = Field(
        None, description="When the current access token expires"
    )
    tenant_id: str | None = Field(None, description="Adobe tenant ID for API endpoints")

    def is_expired(self) -> bool:
        """Check if the session has expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def should_refresh(self, max_conversions: int = 2) -> bool:
        """Check if the session should be refreshed"""
        return self.is_expired() or self.conversion_count >= max_conversions

    def access_token_is_valid(self, buffer_seconds: int = 60) -> bool:
        """Return True if the stored access token is still valid."""
        if not self.access_token:
            return False

        if self.access_token_expires_at is None:
            return True

        now = datetime.now()
        if buffer_seconds < 0:
            buffer_seconds = 0

        tolerance = timedelta(seconds=1)
        threshold = self.access_token_expires_at - timedelta(seconds=buffer_seconds)
        return now <= threshold + tolerance


@dataclass
class UploadProgress:
    """Progress information for file upload"""

    bytes_uploaded: int
    total_bytes: int
    percentage: float
    upload_speed: float | None = None  # bytes per second

    @property
    def is_complete(self) -> bool:
        """Check if upload is complete"""
        return self.bytes_uploaded >= self.total_bytes


@dataclass
class ConversionProgress:
    """Progress information for conversion"""

    status: ConversionStatus
    percentage: int
    message: str | None = None
    elapsed_time: float | None = None  # seconds

    @property
    def is_complete(self) -> bool:
        """Check if conversion is complete"""
        return self.status in [ConversionStatus.COMPLETED, ConversionStatus.FAILED]
