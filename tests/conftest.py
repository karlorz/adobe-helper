"""Test configuration and fixtures for Adobe Helper tests"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest


@pytest.fixture
def sample_pdf_path(tmp_path: Path) -> Path:
    """Create a sample PDF file for testing"""
    pdf_path = tmp_path / "test.pdf"
    # Create a minimal valid PDF
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
190
%%EOF
"""
    pdf_path.write_bytes(pdf_content)
    return pdf_path


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient"""
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest.fixture
def mock_session_manager(mock_httpx_client):
    """Mock SessionManager"""

    manager = MagicMock()
    manager.client = mock_httpx_client
    manager.csrf_token = "test-csrf-token"
    manager.session_id = "test-session-id"
    manager.is_active = MagicMock(return_value=True)
    manager.initialize = AsyncMock()
    return manager


@pytest.fixture
def temp_session_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for session data"""
    session_dir = tmp_path / ".adobe-helper"
    session_dir.mkdir(exist_ok=True)
    return session_dir
