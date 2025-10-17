"""Tests for Adobe Helper data models"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from adobe.models import (
    ConversionJob,
    ConversionProgress,
    ConversionStatus,
    ConversionType,
    FileInfo,
    SessionInfo,
    UploadProgress,
)


class TestConversionJob:
    """Tests for ConversionJob model"""

    def test_create_conversion_job(self):
        """Test creating a basic conversion job"""
        job = ConversionJob(job_uri="https://example.com/jobs/123")
        assert job.job_uri == "https://example.com/jobs/123"
        assert job.status == ConversionStatus.PENDING
        assert job.conversion_type == ConversionType.PDF_TO_WORD

    def test_conversion_job_with_all_fields(self):
        """Test conversion job with all fields"""
        now = datetime.now()
        job = ConversionJob(
            job_uri="https://example.com/jobs/456",
            status=ConversionStatus.COMPLETED,
            upload_id="upload-789",
            asset_uri="https://example.com/assets/abc",
            download_url="https://example.com/download/file.docx",
            created_at=now,
            completed_at=now + timedelta(minutes=5),
            conversion_type=ConversionType.PDF_TO_EXCEL,
            progress=100,
        )
        assert job.job_uri == "https://example.com/jobs/456"
        assert job.status == ConversionStatus.COMPLETED
        assert job.progress == 100

    def test_conversion_job_invalid_progress(self):
        """Test that invalid progress values are rejected"""
        with pytest.raises(ValidationError):
            ConversionJob(job_id="test-job", progress=150)

        with pytest.raises(ValidationError):
            ConversionJob(job_id="test-job", progress=-10)


class TestFileInfo:
    """Tests for FileInfo model"""

    def test_create_file_info(self, sample_pdf_path: Path):
        """Test creating FileInfo for a valid PDF"""
        file_info = FileInfo(
            file_path=sample_pdf_path,
            file_name="test.pdf",
            file_size=sample_pdf_path.stat().st_size,
        )
        assert file_info.file_path == sample_pdf_path
        assert file_info.file_name == "test.pdf"
        assert file_info.file_size > 0

    def test_file_info_validates_extension(self, sample_pdf_path: Path):
        """Test that non-PDF files are rejected"""
        with pytest.raises(ValidationError, match="must have .pdf extension"):
            FileInfo(
                file_path=sample_pdf_path,
                file_name="test.txt",
                file_size=100,
            )

    def test_file_info_validates_existence(self, tmp_path: Path):
        """Test that non-existent files are rejected"""
        non_existent = tmp_path / "does_not_exist.pdf"
        with pytest.raises(ValidationError, match="File does not exist"):
            FileInfo(
                file_path=non_existent,
                file_name="does_not_exist.pdf",
                file_size=100,
            )

    def test_file_info_validates_mime_type(self, sample_pdf_path: Path):
        """Test that invalid MIME types are rejected"""
        with pytest.raises(ValidationError, match="MIME type must be application/pdf"):
            FileInfo(
                file_path=sample_pdf_path,
                file_name="test.pdf",
                file_size=100,
                mime_type="text/plain",
            )


class TestSessionInfo:
    """Tests for SessionInfo model"""

    def test_create_session_info(self):
        """Test creating basic session info"""
        session = SessionInfo(access_token="token", access_token_expires_at=datetime.now())
        assert session.is_anonymous is True
        assert session.conversion_count == 0
        assert isinstance(session.created_at, datetime)
        assert session.access_token_is_valid(buffer_seconds=0)

    def test_session_expiry(self):
        """Test session expiry check"""
        # Not expired session
        session = SessionInfo(expires_at=datetime.now() + timedelta(hours=1))
        assert not session.is_expired()

        # Expired session
        session = SessionInfo(expires_at=datetime.now() - timedelta(hours=1))
        assert session.is_expired()

    def test_session_should_refresh(self):
        """Test session refresh logic"""
        # Should refresh due to conversion count
        session = SessionInfo(conversion_count=2)
        assert session.should_refresh(max_conversions=2)

        # Should refresh due to expiry
        session = SessionInfo(expires_at=datetime.now() - timedelta(hours=1))
        assert session.should_refresh()

        # Should not refresh
        session = SessionInfo(conversion_count=1)
        assert not session.should_refresh(max_conversions=2)


class TestUploadProgress:
    """Tests for UploadProgress dataclass"""

    def test_upload_progress(self):
        """Test upload progress tracking"""
        progress = UploadProgress(
            bytes_uploaded=500,
            total_bytes=1000,
            percentage=50.0,
            upload_speed=1024.0,
        )
        assert progress.bytes_uploaded == 500
        assert progress.percentage == 50.0
        assert not progress.is_complete

    def test_upload_complete(self):
        """Test upload completion check"""
        progress = UploadProgress(bytes_uploaded=1000, total_bytes=1000, percentage=100.0)
        assert progress.is_complete


class TestConversionProgress:
    """Tests for ConversionProgress dataclass"""

    def test_conversion_progress(self):
        """Test conversion progress tracking"""
        progress = ConversionProgress(
            status=ConversionStatus.PROCESSING,
            percentage=75,
            message="Converting page 3 of 4",
            elapsed_time=30.5,
        )
        assert progress.status == ConversionStatus.PROCESSING
        assert progress.percentage == 75
        assert not progress.is_complete

    def test_conversion_complete(self):
        """Test conversion completion check"""
        progress = ConversionProgress(status=ConversionStatus.COMPLETED, percentage=100)
        assert progress.is_complete

    def test_conversion_failed(self):
        """Test failed conversion status"""
        progress = ConversionProgress(status=ConversionStatus.FAILED, percentage=0)
        assert progress.is_complete
