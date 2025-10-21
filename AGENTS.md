# AGENTS.md

**Instructions for Agents when working in this repository.**

## Project Overview

This is an **Adobe PDF-to-Word Helper** library inspired by the architecture of Adobe's online PDF conversion service. The goal is to create a Python client that converts PDF files to DOCX format using Adobe's online conversion workflow.

**Target Service:** `https://www.adobe.com/acrobat/online/pdf-to-word.html`

**Reference Architecture:** Adobe Acrobat Online - Uses Unity workflow system with file upload, conversion processing, and download capabilities.

## Recent Progress (2025-10-21)

### ✅ Multi-Tenant Architecture Implemented

The library now supports **automatic tenant discovery and dynamic endpoint switching**:

1. **Logging Configuration Fixed**
   - Added `logging.basicConfig()` to examples to display conversion progress
   - Users now see real-time INFO messages during conversion workflow

2. **Dynamic Tenant Discovery**
   - Each session automatically discovers its numeric tenant ID during upload
   - Initial IMS token provides client ID (e.g., `dc-prod-virgoweb`)
   - Discovery endpoint (`/discovery`) returns numeric tenant (e.g., `1761640175`)
   - Endpoints are rebuilt automatically with the discovered tenant
   - Different sessions can use different tenants without conflicts

3. **Working Flow**
   ```
   1. Session Init → Extract IMS token tenant: "dc-prod-virgoweb"
   2. Upload → Call /discovery → Discover numeric tenant: "1761640175"
   3. Update Session → Store numeric tenant ID
   4. Rebuild Endpoints → Use tenant-specific URLs
   5. Convert/Download → All APIs use correct tenant: "1761640175"
   ```

4. **Key Changes**
   - `adobe/auth.py`: Added `extract_tenant_from_ims_response()` method
   - `adobe/upload.py`: Added `get_discovered_tenant_id()` method
   - `adobe/client.py`: Automatic tenant extraction and endpoint rebuilding
   - `adobe/urls.py`: `get_endpoints_for_session()` now accepts dynamic tenant_id
   - `adobe/models.py`: `SessionInfo` includes tenant_id field
   - `examples/adobe/basic_usage.py`: Added logging configuration

5. **Benefits**
   - ✅ No hardcoded tenant IDs required
   - ✅ Sessions are tenant-isolated
   - ✅ Supports multi-region deployments
   - ✅ Handles tenant rotation automatically
   - ✅ Each new session gets its own tenant from Adobe's servers

## Key Features

- File upload mechanism (drag-and-drop or file selection)
- PDF to DOCX conversion via Adobe's online service
- Session management and authentication
- Download converted files
- Support for various PDF sizes and formats
- Error handling and status tracking

## Architecture Analysis (From Chrome DevTools Study)

### Adobe's Workflow System

Based on network analysis, Adobe uses a sophisticated workflow system:

1. **Unity Workflow Framework** (`/unitylibs/core/workflow/`)
   - `workflow.js` - Main workflow orchestrator
   - `workflow-acrobat/` - Acrobat-specific workflows
   - Supported features include: pdf-to-word, pdf-to-excel, pdf-to-ppt, etc.

2. **Key Components:**
   - **Interactive Area** - File upload drop zone
   - **Action Binder** - Binds user actions to workflow steps
   - **Target Config** - Configuration for each conversion type
   - **Widget System** - UI components for file handling

3. **Workflow Steps:**
   ```
   1. User selects/drops PDF file
   2. File upload to Adobe servers (HTTPS/TLS 1.2, AES-256 encryption)
   3. Server-side conversion process
   4. Download converted DOCX file
   ```

### Authentication & Security

- **IMS (Identity Management Services)** - Adobe's auth system
- **Session tokens** - Managed via cookies and headers
- **CSRF protection** - Token-based security
- **Encryption** - Files secured using HTTPS w/TLS 1.2 and stored using AES-256

### API Endpoints Discovered

Key endpoints from network analysis:
```
- https://www.adobe.com/unitylibs/core/workflow/workflow-acrobat/
- https://acroipm2.adobe.com/acrobat-web/machine/unity-dc-frictionless/
- IMS authentication endpoints (adobeid-na1.services.adobe.com)
- Asset upload (multipart form-data): https://pdfnow-<region>.adobe.io/<tenant>/assets
  * Requires `Authorization: Bearer <guest token>` and optional block-upload initialize/finalize APIs
  * Response includes `asset_id`/`asset_uri` used by subsequent export requests
- Export job submission: https://pdfnow-<region>.adobe.io/<tenant>/assets/exportpdf (POST JSON with `asset_uri`)
- Job status polling: https://pdfnow-<region>.adobe.io/<tenant>/jobs/status?job_uri=...
- Download URI negotiation: https://pdfnow-<region>.adobe.io/<tenant>/assets/download_uri?asset_uri=...
- Discovery endpoint: https://pdfnow-<region>.adobe.io/<tenant>/discovery (returns numeric tenant ID)
```

**Important:** 
- Browser sessions surface an `asset_uri` in the URL fragment (`#assets=...`), but the backend still expects the asset bytes to be uploaded via the `/assets` endpoint before calling `exportpdf`. Our client must reproduce that upload step to obtain a valid `asset_uri`.
- The `<tenant>` placeholder is dynamically discovered per session via the `/discovery` endpoint and stored in session cache.
- Tenant IDs can vary between sessions and regions (e.g., `dc-prod-virgoweb` client ID → `1761640175` numeric tenant).

**Endpoint caching:** On initialization the library copies any discovered endpoint file into `~/.adobe-helper/discovered_endpoints.json`. If nothing exists it writes a fresh template with the same Chrome DevTools checklist. Keep the canonical capture under `docs/discovery/discovered_endpoints.json` (or `archive/discovery/` for historical snapshots) current so new installs inherit working URLs.
```

---

## Quick Start (UV-Based Setup)

```bash
# Clone repository
git clone https://github.com/karlorz/adobe-helper.git
cd adobe-helper

# Install UV (if missing) and sync project deps
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.11
uv sync --all-extras --dev

# Run smoke checks
uv run pytest
uv run python examples/basic_usage.py
```

### Minimal Editable Install (pip-compatible)

```bash
python -m venv .venv
source .venv/bin/activate    # or .venv\Scripts\activate on Windows
pip install -e .[dev]
pytest
```

---

## Proposed Architecture Design

### Core Components

```
adobe-helper/
├── adobe/
│   ├── __init__.py
│   ├── client.py          # Main AdobePDFConverter class
│   ├── auth.py            # Authentication & session management
│   ├── upload.py          # File upload handler
│   ├── conversion.py      # Conversion workflow manager
│   ├── download.py        # File download handler
│   ├── models.py          # Data models (ConversionJob, FileInfo)
│   ├── urls.py            # API endpoint constants
│   ├── constants.py       # Conversion types, status codes
│   └── utils.py           # Helper functions
├── examples/
│   ├── basic_usage.py
│   ├── batch_convert.py
│   └── async_convert.py
├── tests/
│   └── test_client.py
├── pyproject.toml
├── README.md
└── AGENTS.md              # This file
```

---

## Technical Implementation Guidelines

### 1. HTTP Client Architecture

**Similar to Adobe's workflow:**

```python
import httpx
from typing import Optional
from pathlib import Path

class AdobePDFConverter:
    def __init__(self, session_dir: Optional[Path] = None):
        self.client = httpx.AsyncClient(
            http2=True,
            timeout=300.0,  # Conversion may take time
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
                'Accept': 'application/json, text/plain, */*',
            }
        )
        self.session_manager = SessionManager(self.client, session_dir)
        self.uploader = FileUploader(self.client)
        self.converter = ConversionManager(self.client)
        self.downloader = FileDownloader(self.client)
```

### 2. Session & Authentication Management

**Adobe uses IMS authentication:**

```python
class SessionManager:
    def __init__(self, client: httpx.AsyncClient, session_dir: Optional[Path]):
        self.client = client
        self.session_dir = session_dir or Path.home() / '.adobe-helper'
        self.session_file = self.session_dir / 'session.json'
        self.csrf_token = None
        self.session_id = None

    async def initialize(self):
        """Initialize session by visiting the PDF-to-Word page"""
        # Visit main page to get cookies and CSRF token
        response = await self.client.get(
            'https://www.adobe.com/acrobat/online/pdf-to-word.html'
        )
        # Extract CSRF token from cookies or response
        self.extract_tokens(response)

    def extract_tokens(self, response):
        """Extract CSRF and session tokens"""
        # Parse cookies and headers for security tokens
        pass
```

### 3. File Upload Handler

```python
class FileUploader:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def upload_pdf(
        self,
        file_path: Path,
        csrf_token: str
    ) -> str:
        """
        Upload PDF file to Adobe servers

        Returns:
            upload_id: Unique identifier for the uploaded file
        """
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'application/pdf')}
            headers = {
                'X-CSRF-Token': csrf_token,
            }

            response = await self.client.post(
                'https://www.adobe.com/dc-api/upload',  # Example endpoint
                files=files,
                headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                return data['uploadId']
            else:
                raise UploadError(f"Upload failed: {response.status_code}")
```

### 4. Conversion Workflow Manager

```python
class ConversionManager:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def start_conversion(
        self,
        upload_id: str,
        conversion_type: str = 'pdf-to-word'
    ) -> ConversionJob:
        """
        Initiate PDF to DOCX conversion

        Returns:
            ConversionJob with job_id and status
        """
        payload = {
            'uploadId': upload_id,
            'targetFormat': 'docx',
            'feature': conversion_type
        }

        response = await self.client.post(
            'https://www.adobe.com/dc-api/convert',  # Example endpoint
            json=payload
        )

        if response.status_code == 200:
            data = response.json()
            return ConversionJob(
                job_id=data['jobId'],
                status=data['status'],
                upload_id=upload_id
            )
        else:
            raise ConversionError(f"Conversion failed: {response.status_code}")

    async def check_status(self, job_id: str) -> dict:
        """Poll conversion status"""
        response = await self.client.get(
            f'https://www.adobe.com/dc-api/status/{job_id}'
        )
        return response.json()

    async def wait_for_completion(
        self,
        job_id: str,
        poll_interval: float = 2.0,
        timeout: float = 300.0
    ) -> dict:
        """Wait for conversion to complete"""
        import asyncio
        start_time = asyncio.get_event_loop().time()

        while True:
            status = await self.check_status(job_id)

            if status['state'] == 'completed':
                return status
            elif status['state'] == 'failed':
                raise ConversionError(f"Conversion failed: {status.get('error')}")

            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(f"Conversion timed out after {timeout}s")

            await asyncio.sleep(poll_interval)
```

### 5. File Download Handler

```python
class FileDownloader:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def download_file(
        self,
        download_url: str,
        output_path: Path
    ) -> Path:
        """
        Download converted DOCX file

        Returns:
            Path to downloaded file
        """
        async with self.client.stream('GET', download_url) as response:
            response.raise_for_status()

            with open(output_path, 'wb') as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)

        return output_path
```

### 6. Data Models

```python
from dataclasses import dataclass
from typing import Optional
from enum import Enum

class ConversionStatus(str, Enum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'

@dataclass
class ConversionJob:
    job_id: str
    status: ConversionStatus
    upload_id: str
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None

@dataclass
class FileInfo:
    file_path: Path
    file_name: str
    file_size: int
    mime_type: str = 'application/pdf'
```

### 7. Main Client Interface

```python
class AdobePDFConverter:
    async def convert_pdf_to_word(
        self,
        pdf_path: Path,
        output_path: Optional[Path] = None,
        wait: bool = True
    ) -> Path:
        """
        Convert PDF to Word (DOCX)

        Args:
            pdf_path: Path to input PDF file
            output_path: Path for output DOCX file (optional)
            wait: Wait for conversion to complete (default: True)

        Returns:
            Path to converted DOCX file
        """
        # 1. Initialize session if needed
        if not self.session_manager.is_active():
            await self.session_manager.initialize()

        # 2. Upload PDF file
        upload_id = await self.uploader.upload_pdf(
            pdf_path,
            self.session_manager.csrf_token
        )

        # 3. Start conversion
        job = await self.converter.start_conversion(upload_id)

        # 4. Wait for completion (if requested)
        if wait:
            status = await self.converter.wait_for_completion(job.job_id)
            download_url = status['downloadUrl']
        else:
            return job  # Return job for async tracking

        # 5. Download converted file
        if output_path is None:
            output_path = pdf_path.with_suffix('.docx')

        result_path = await self.downloader.download_file(
            download_url,
            output_path
        )

        return result_path
```

---

## Example Usage Patterns

### Basic Usage

```python
import asyncio
from pathlib import Path
from adobe import AdobePDFConverter

async def main():
    # Initialize converter
    converter = AdobePDFConverter()

    # Convert PDF to Word
    pdf_file = Path('document.pdf')
    docx_file = await converter.convert_pdf_to_word(pdf_file)

    print(f"Converted: {docx_file}")

    # Clean up
    await converter.close()

asyncio.run(main())
```

### Batch Conversion

```python
async def batch_convert():
    converter = AdobePDFConverter()

    pdf_files = Path('.').glob('*.pdf')

    tasks = [
        converter.convert_pdf_to_word(pdf_file)
        for pdf_file in pdf_files
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for pdf_file, result in zip(pdf_files, results):
        if isinstance(result, Exception):
            print(f"Failed: {pdf_file} - {result}")
        else:
            print(f"Success: {pdf_file} -> {result}")

    await converter.close()

asyncio.run(batch_convert())
```

### Context Manager Usage

```python
async def convert_with_context():
    async with AdobePDFConverter() as converter:
        result = await converter.convert_pdf_to_word(
            Path('input.pdf'),
            Path('output.docx')
        )
        print(f"Converted: {result}")

asyncio.run(convert_with_context())
```

---

## Development Workflow

### Phase 1: Core Implementation
1. Create `adobe/client.py` with `AdobePDFConverter` class
2. Create `adobe/auth.py` with `SessionManager` class
3. Create `adobe/upload.py` with `FileUploader` class
4. Create `adobe/conversion.py` with `ConversionManager` class
5. Create `adobe/download.py` with `FileDownloader` class
6. Create `adobe/models.py` with data models

### Phase 2: Testing
1. Write unit tests for session management
2. Test file upload with small PDFs
3. Test conversion workflow
4. Test download functionality
5. Test error handling (timeouts, failures, invalid files)

### Phase 3: Features
1. Add support for batch conversions
2. Add progress callbacks
3. Add caching for converted files
4. Add retry logic with exponential backoff
5. Add support for other conversion types (PDF to Excel, PPT, etc.)

### Phase 4: Documentation & Examples
1. Write comprehensive README.md
2. Create example scripts
3. Add docstrings to all public methods
4. Create API documentation

---

## Dependencies

**Required packages:**
```toml
[project]
dependencies = [
    "httpx[http2]>=0.27.0",  # Async HTTP client with HTTP/2 support
    "pydantic>=2.0.0",        # Data validation
    "python-dotenv>=1.0.0",   # Environment configuration
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.7.1",
    "black>=24.0.0",
    "mypy>=1.8.0",
]
```

---

## Best Practices

### 1. Always Use Async/Await
- All network operations must be async
- Use `asyncio.gather()` for concurrent operations
- Implement proper error handling in async contexts

### 2. Session Management
- Cache session tokens in memory and optionally on disk
- Refresh tokens before expiration
- Handle 401/403 responses gracefully

### 3. File Handling
- Validate PDF files before upload
- Stream large files during upload/download
- Clean up temporary files

### 4. Error Handling
```python
class AdobeHelperError(Exception):
    """Base exception for Adobe Helper"""
    pass

class AuthenticationError(AdobeHelperError):
    """Raised when authentication fails"""
    pass

class UploadError(AdobeHelperError):
    """Raised when file upload fails"""
    pass

class ConversionError(AdobeHelperError):
    """Raised when conversion fails"""
    pass

class DownloadError(AdobeHelperError):
    """Raised when download fails"""
    pass
```

### 5. Rate Limiting
- Implement rate limiting to respect Adobe's servers
- Use `asyncio.Semaphore` to limit concurrent requests
- Add exponential backoff on 429 errors

### 6. Logging
```python
import logging

logger = logging.getLogger('adobe-helper')
logger.setLevel(logging.INFO)

# Usage
logger.info(f"Uploading file: {file_path}")
logger.error(f"Conversion failed: {error}")
```

---

## Testing Strategy

### Unit Tests
- Test session token management
- Test file validation
- Test response parsing
- Test error handling

### Integration Tests
- Test actual file upload (with small test PDFs)
- Test conversion workflow
- Test file download
- Test session refresh

### Mock Testing
```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_convert_pdf():
    converter = AdobePDFConverter()
    converter.client.post = AsyncMock(return_value=mock_response)

    result = await converter.convert_pdf_to_word(Path('test.pdf'))
    assert result.exists()
```

---

## Bypassing Login/Registration Requirements

Adobe's online tools often require user login after a certain number of conversions. Here are strategies to handle this:

### Strategy 1: Anonymous Session Cycling

```python
class AnonymousSessionManager:
    """Manage anonymous sessions by cycling through fresh sessions"""

    def __init__(self, max_conversions_per_session: int = 2):
        self.max_conversions = max_conversions_per_session
        self.conversion_count = 0
        self.session_pool = []

    async def get_fresh_session(self):
        """Create a new anonymous session"""
        client = httpx.AsyncClient(
            http2=True,
            headers={
                'User-Agent': self._get_random_user_agent(),
                'Accept-Language': 'en-US,en;q=0.9',
            }
        )

        # Visit the main page to establish cookies
        await client.get('https://www.adobe.com/acrobat/online/pdf-to-word.html')

        return client

    async def should_refresh_session(self):
        """Check if we need a new session"""
        self.conversion_count += 1
        if self.conversion_count >= self.max_conversions:
            self.conversion_count = 0
            return True
        return False

    def _get_random_user_agent(self):
        """Rotate user agents to appear as different users"""
        user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        ]
        import random
        return random.choice(user_agents)
```

### Strategy 2: Cookie Management

```python
import json
from pathlib import Path

class CookieManager:
    """Manage cookies to simulate different sessions"""

    def __init__(self, cookie_dir: Path = None):
        self.cookie_dir = cookie_dir or Path.home() / '.adobe-helper' / 'cookies'
        self.cookie_dir.mkdir(parents=True, exist_ok=True)

    async def save_cookies(self, client: httpx.AsyncClient, session_id: str):
        """Save cookies for reuse"""
        cookie_file = self.cookie_dir / f'{session_id}.json'
        cookies = {c.name: c.value for c in client.cookies.jar}
        with open(cookie_file, 'w') as f:
            json.dump(cookies, f)

    async def load_cookies(self, client: httpx.AsyncClient, session_id: str):
        """Load saved cookies"""
        cookie_file = self.cookie_dir / f'{session_id}.json'
        if cookie_file.exists():
            with open(cookie_file, 'r') as f:
                cookies = json.load(f)
                for name, value in cookies.items():
                    client.cookies.set(name, value)

    def clear_old_sessions(self, max_age_days: int = 7):
        """Clean up old cookie files"""
        import time
        current_time = time.time()
        for cookie_file in self.cookie_dir.glob('*.json'):
            if current_time - cookie_file.stat().st_mtime > max_age_days * 86400:
                cookie_file.unlink()
```

### Strategy 3: Headless Browser Automation (Fallback)

If the web service becomes too restrictive, use browser automation:

```python
from playwright.async_api import async_playwright

class BrowserBasedConverter:
    """Use headless browser to bypass JavaScript checks"""

    async def convert_with_browser(self, pdf_path: Path, output_path: Path):
        async with async_playwright() as p:
            # Launch browser in headless mode
            browser = await p.chromium.launch(headless=True)

            # Create new page with random viewport
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
            )
            page = await context.new_page()

            # Navigate to conversion page
            await page.goto('https://www.adobe.com/acrobat/online/pdf-to-word.html')

            # Upload file
            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(pdf_path))

            # Wait for conversion to complete
            download_button = await page.wait_for_selector(
                'a[download], button[download]',
                timeout=300000  # 5 minutes
            )

            # Trigger download
            async with page.expect_download() as download_info:
                await download_button.click()
            download = await download_info.value

            # Save file
            await download.save_as(str(output_path))

            await browser.close()
```

### Strategy 4: Rate Limiting & Delays

```python
import asyncio
import random

class RateLimiter:
    """Add human-like delays between conversions"""

    def __init__(self, min_delay: float = 5.0, max_delay: float = 15.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time = 0

    async def wait(self):
        """Wait with random human-like delay"""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_delay:
            delay = random.uniform(
                self.min_delay - time_since_last,
                self.max_delay - time_since_last
            )
            await asyncio.sleep(delay)

        self.last_request_time = asyncio.get_event_loop().time()
```

### Strategy 5: Implement Free Tier Tracking

```python
class FreeUsageTracker:
    """Track free conversion quota"""

    def __init__(self, daily_limit: int = 2):
        self.daily_limit = daily_limit
        self.usage_file = Path.home() / '.adobe-helper' / 'usage.json'
        self.usage_data = self._load_usage()

    def _load_usage(self):
        if self.usage_file.exists():
            with open(self.usage_file, 'r') as f:
                return json.load(f)
        return {'date': str(datetime.date.today()), 'count': 0}

    def can_convert(self) -> bool:
        """Check if we can still convert without login"""
        today = str(datetime.date.today())

        # Reset counter if new day
        if self.usage_data['date'] != today:
            self.usage_data = {'date': today, 'count': 0}

        return self.usage_data['count'] < self.daily_limit

    def increment_usage(self):
        """Increment usage counter"""
        self.usage_data['count'] += 1
        with open(self.usage_file, 'w') as f:
            json.dump(self.usage_data, f)

    def get_remaining(self) -> int:
        """Get remaining free conversions"""
        return max(0, self.daily_limit - self.usage_data['count'])
```

### Integration Example

```python
class AdobePDFConverter:
    def __init__(self):
        self.session_manager = AnonymousSessionManager(max_conversions_per_session=2)
        self.cookie_manager = CookieManager()
        self.rate_limiter = RateLimiter(min_delay=10.0, max_delay=20.0)
        self.usage_tracker = FreeUsageTracker(daily_limit=2)
        self.browser_fallback = BrowserBasedConverter()

    async def convert_pdf_to_word(self, pdf_path: Path, output_path: Path) -> Path:
        # Check free quota
        if not self.usage_tracker.can_convert():
            print(f"Daily limit reached. Remaining: {self.usage_tracker.get_remaining()}")
            # Fall back to browser automation
            return await self.browser_fallback.convert_with_browser(pdf_path, output_path)

        # Add human-like delay
        await self.rate_limiter.wait()

        # Check if we need fresh session
        if await self.session_manager.should_refresh_session():
            self.client = await self.session_manager.get_fresh_session()

        try:
            # Attempt conversion
            result = await self._do_conversion(pdf_path, output_path)
            self.usage_tracker.increment_usage()
            return result

        except AuthenticationRequired:
            # If login is required, use browser fallback
            return await self.browser_fallback.convert_with_browser(pdf_path, output_path)
```

---

## Security Considerations

1. **Do not commit session tokens** - Add `.adobe-helper/` to `.gitignore`
2. **Respect rate limits** - Implement proper throttling
3. **Use HTTPS only** - Never downgrade to HTTP
4. **Handle sensitive data** - Don't log file contents or tokens
5. **Implement timeouts** - Prevent hanging requests
6. **Validate file types** - Only accept valid PDF files
7. **Respect Adobe's Terms of Service** - Use responsibly and within limits
8. **Session rotation ethics** - Don't abuse the free tier excessively

---

## PyPI Publishing (Trusted Workflow)

Follow this compact checklist when preparing a release to PyPI:

1. **One-time setup (skip if already done):**
   - On PyPI, add a *Trusted Publisher* pointing to `karlorz/adobe-helper`, workflow `release.yml`, environment `pypi`.
   - In GitHub → Settings → Environments, create an environment named `pypi` (match casing) and grant it the default permissions.
2. **Prepare the build:**
   - Update `pyproject.toml` with the new version number.
   - Run local checks (`ruff`, `black`, `pytest`) to confirm the release is green.
3. **Cut the release:**
   - Commit the version bump and tag it (`git tag vX.Y.Z`).
   - Push the tag to GitHub *or* trigger `.github/workflows/release.yml` via **Run workflow** (the maintainer prefers manual dispatch).
4. **Automation handles publishing:**
   - The release workflow builds wheels/sdists with `uv build`, runs twine checks + smoke tests, and calls `uv publish` using OIDC—no PyPI token needed.
   - Monitor the workflow logs; once it succeeds, verify the package at https://pypi.org/project/adobe-helper/.

If the workflow cannot access PyPI (e.g., environment missing), fix the configuration, rerun the job, and keep AGENTS.md in sync with any process changes.

---

## Known Workflow Endpoints (From Analysis)

Based on network analysis of `https://www.adobe.com/acrobat/online/pdf-to-word.html`:

### Unity Workflow System
```
GET /unitylibs/core/workflow/workflow.js
GET /unitylibs/core/workflow/workflow-acrobat/target-config.json
GET /unitylibs/core/workflow/workflow-acrobat/action-binder.js
```

### Acrobat Web Services
```
POST /acrobat-web/machine/unity-dc-frictionless/
GET /acrobat-web/machine/overall/adobe_com/1.0/unspecified/anon/
```

### File Operations (To be discovered)
```
POST /dc-api/upload (hypothetical)
POST /dc-api/convert (hypothetical)
GET /dc-api/status/{jobId} (hypothetical)
GET /dc-api/download/{jobId} (hypothetical)
```

**Note:** Actual endpoints need to be discovered through:
1. Network monitoring during actual file upload
2. JavaScript analysis of workflow files
3. API documentation (if available)

---

## Reverse Engineering Steps

To complete the implementation, we need to:

1. **Capture actual API calls:**
   - Upload a real PDF file on Adobe's website
   - Monitor network traffic to capture exact endpoints
   - Record request/response formats

2. **Analyze authentication flow:**
   - Identify required headers and tokens
   - Understand session management
   - Document CSRF protection mechanism

3. **Document upload protocol:**
   - Multipart form data format
   - Required metadata fields
   - File size limits and chunking

4. **Map conversion workflow:**
   - Job submission parameters
   - Status polling mechanism
   - Download link generation

---

## Future Enhancements

1. **Multi-format Support** - PDF to Excel, PowerPoint, images
2. **OCR Integration** - For scanned PDFs
3. **Batch Processing** - Process multiple files efficiently
4. **Progress Tracking** - Real-time conversion progress
5. **CLI Tool** - Command-line interface
6. **GUI** - Simple desktop app using tkinter/PyQt
7. **Cloud Storage** - Direct upload from Google Drive, Dropbox

---

## Contributing Guidelines

When working on this project:

1. Study Adobe's workflow system architecture
2. Maintain async/await consistency
3. Add type hints to all functions
4. Write tests for new features
5. Update AGENTS.md when discovering new endpoints
6. Document all public methods with docstrings
7. Keep dependencies minimal

---

## Project Configuration (pyproject.toml)

```toml
[project]
name = "adobe-helper"
version = "0.1.0"
description = "Python client for Adobe PDF to Word conversion"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [
    { name = "Your Name", email = "your.email@example.com" }
]

dependencies = [
    "httpx[http2]>=0.27.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.7.1",
    "black>=24.0.0",
    "mypy>=1.8.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.black]
line-length = 100
target-version = ['py311']

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

---

## Quick Start for Agents

To start implementing:

1. **Setup Environment:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   uv python install 3.11
   uv sync --all-extras --dev
   ```

2. **Next Steps:**
   - Perform live network capture during PDF upload
   - Extract actual API endpoints
   - Implement authentication flow
   - Build upload/conversion/download pipeline

3. **Development Workflow:**
   ```bash
   # Make changes
   uv run ruff check adobe/      # Lint
   uv run black adobe/           # Format
   uv run pytest                  # Test
   uv run python examples/basic_usage.py  # Try it
   ```

**Remember:**
- This is reverse engineering of Adobe's web service
- API endpoints need to be discovered through network analysis
- Always respect Adobe's Terms of Service
- Use for legitimate PDF conversion purposes only

---

## External Research Notes

- **py-googletrans (ssut/py-googletrans)**
  - Unofficial Google Translate wrapper; main `Translator` class issues translate/detect requests, while `TokenAcquirer` reproduces Google web token logic refreshed hourly.
  - Relies on `httpx.AsyncClient` (HTTP/2 optional) with configurable service URLs (e.g., `translate.googleapis.com` to bypass token), custom user-agents/proxies, and concurrency controls for batch ops.
  - Key modules: `googletrans.client` (public API), `googletrans.gtoken` (tk generation), `googletrans.constants` (language mappings/defaults), `googletrans.models` (response dataclasses), `googletrans.utils` (param building/JSON parsing).
  - Caveats: unofficial scraping approach; subject to breakage, ~15K char per request cap, heavy usage can trigger IP bans; official Google Translate API recommended for production stability.
