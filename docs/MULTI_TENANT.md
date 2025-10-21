# Multi-Tenant Support

## Overview

Adobe's PDF conversion API uses **tenant-specific endpoints**. Each session gets a unique tenant ID that must be included in the API endpoint URLs.

**Endpoint Pattern:**
```
https://pdfnow-{region}.adobe.io/{tenant_id}/{endpoint}
```

**Example:**
```
https://pdfnow-jpn3.adobe.io/1761291926/assets
https://pdfnow-jpn3.adobe.io/1761291926/assets/exportpdf
https://pdfnow-jpn3.adobe.io/1761291926/jobs/status
https://pdfnow-jpn3.adobe.io/1761291926/assets/download_uri
```

## How It Works

### 1. Tenant ID Extraction

The library automatically extracts the tenant ID from the Adobe IMS authentication response:

```python
# When initializing a session:
session_manager = SessionManager(client)
await session_manager.initialize()

# The tenant ID is extracted from:
# 1. IMS response payload (tenant_id, org_id, client_id fields)
# 2. JWT access token payload (decoded from the token)
```

### 2. Automatic Endpoint Building

Once a tenant ID is extracted, the library automatically builds tenant-specific endpoints:

```python
from adobe.urls import get_endpoints_for_session

# Get endpoints for a specific tenant
endpoints = get_endpoints_for_session(tenant_id="1761291926")

# Returns:
{
    "upload": "https://pdfnow-jpn3.adobe.io/1761291926/assets",
    "conversion": "https://pdfnow-jpn3.adobe.io/1761291926/assets/exportpdf",
    "status": "https://pdfnow-jpn3.adobe.io/1761291926/jobs/status",
    "download": "https://pdfnow-jpn3.adobe.io/1761291926/assets/download_uri"
}
```

### 3. Session-Specific Tenants

**Each new session gets its own tenant ID:**

```python
# Session 1
async with AdobePDFConverter() as converter1:
    # Internally uses tenant ID from session 1's IMS token
    await converter1.convert_pdf_to_word(pdf_file)

# Session 2
async with AdobePDFConverter() as converter2:
    # Internally uses tenant ID from session 2's IMS token
    # May be the same or different tenant ID
    await converter2.convert_pdf_to_word(pdf_file)
```

## Implementation Details

### Tenant ID Storage

The tenant ID is stored in the `SessionInfo` model:

```python
@dataclass
class SessionInfo(BaseModel):
    session_id: str | None
    csrf_token: str | None
    cookies: dict[str, str]
    access_token: str | None
    tenant_id: str | None  # ← Tenant ID
    # ... other fields
```

### Tenant Extraction Functions

**From JWT Token:**
```python
from adobe.utils import extract_tenant_id_from_token

access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
tenant_id = extract_tenant_id_from_token(access_token)
# Returns: "1761291926" or None
```

**From IMS Response:**
```python
from adobe.utils import extract_tenant_from_ims_response

ims_response = {
    "access_token": "...",
    "tenant_id": "1761291926",
    "expires_in": 86400
}
tenant_id = extract_tenant_from_ims_response(ims_response)
# Returns: "1761291926"
```

### URL Substitution

**Replace placeholder tenant IDs:**
```python
from adobe.urls import substitute_tenant_in_url

# Replace numeric tenant ID
old_url = "https://pdfnow-jpn3.adobe.io/1111111111/assets"
new_url = substitute_tenant_in_url(old_url, "1761291926")
# Returns: "https://pdfnow-jpn3.adobe.io/1761291926/assets"

# Replace <tenant> placeholder
template_url = "https://pdfnow-jpn3.adobe.io/<tenant>/assets"
actual_url = substitute_tenant_in_url(template_url, "1761291926")
# Returns: "https://pdfnow-jpn3.adobe.io/1761291926/assets"
```

## Usage Examples

### Basic Usage (Automatic)

The library handles tenant IDs automatically:

```python
import asyncio
from pathlib import Path
from adobe import AdobePDFConverter

async def main():
    async with AdobePDFConverter() as converter:
        # Tenant ID is automatically:
        # 1. Extracted from IMS token
        # 2. Stored in session
        # 3. Used to build endpoints

        result = await converter.convert_pdf_to_word(
            Path("document.pdf")
        )
        print(f"Converted: {result}")

asyncio.run(main())
```

### Manual Tenant Inspection

Check the tenant ID being used:

```python
async with AdobePDFConverter() as converter:
    # Get tenant ID from session manager
    if isinstance(converter.session_manager, SessionManager):
        tenant_id = converter.session_manager.tenant_id
        print(f"Using tenant: {tenant_id}")

    # Or from session info
    session_info = await converter.session_manager.ensure_access_token()
    print(f"Tenant ID: {session_info.tenant_id}")

    # Convert with this tenant's endpoints
    result = await converter.convert_pdf_to_word(pdf_file)
```

### Multiple Sessions with Different Tenants

```python
async def convert_with_session(pdf_file: Path, session_name: str):
    async with AdobePDFConverter() as converter:
        tenant = converter.session_manager.tenant_id
        print(f"{session_name} using tenant: {tenant}")

        result = await converter.convert_pdf_to_word(pdf_file)
        return result

# Each session may get a different tenant ID
result1 = await convert_with_session(pdf_file, "Session-1")
result2 = await convert_with_session(pdf_file, "Session-2")
```

### Custom Endpoint Configuration

Override tenant-specific endpoints if needed:

```python
import os

# Set custom endpoints with your tenant ID
os.environ["ADOBE_HELPER_UPLOAD_URL"] = "https://pdfnow-jpn3.adobe.io/YOUR_TENANT/assets"
os.environ["ADOBE_HELPER_CONVERSION_URL"] = "https://pdfnow-jpn3.adobe.io/YOUR_TENANT/assets/exportpdf"
os.environ["ADOBE_HELPER_STATUS_URL"] = "https://pdfnow-jpn3.adobe.io/YOUR_TENANT/jobs/status"
os.environ["ADOBE_HELPER_DOWNLOAD_URL"] = "https://pdfnow-jpn3.adobe.io/YOUR_TENANT/assets/download_uri"

# Library will use these endpoints instead
async with AdobePDFConverter() as converter:
    result = await converter.convert_pdf_to_word(pdf_file)
```

## Tenant ID Sources

The library tries to extract tenant ID from (in order):

1. **IMS Response Payload:**
   - `tenant_id` field
   - `org_id` field
   - `client_id` field
   - `user_id` field

2. **JWT Access Token:**
   - Decodes the token payload
   - Extracts `client_id`, `user_id`, `sub`, `tenant_id`, or `org_id`

3. **Fallback:**
   - Uses discovered endpoints from config files
   - Uses environment variable overrides

## Session Persistence

Tenant IDs are saved with session data:

```json
{
  "session_id": "abc123...",
  "csrf_token": "xyz789...",
  "access_token": "eyJhbG...",
  "tenant_id": "1761291926",
  "created_at": "2025-10-21T10:30:00",
  "expires_at": "2025-10-21T18:30:00"
}
```

When loading a saved session:
```python
# Session is restored with its tenant ID
session_manager.load_session()
# tenant_id is automatically restored
tenant_id = session_manager.tenant_id  # "1761291926"
```

## Debugging Tenant Issues

### Enable Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
```

**You'll see:**
```
2025-10-21 10:30:45 - adobe.auth - INFO - Obtained Adobe IMS guest access token
2025-10-21 10:30:45 - adobe.auth - INFO - Extracted tenant ID: 1761291926
2025-10-21 10:30:46 - adobe.urls - INFO - Using tenant ID 1761291926 for API endpoints
2025-10-21 10:30:46 - adobe.client - INFO - Using tenant-specific endpoints for tenant: 1761291926
```

### Check Endpoints

```python
async with AdobePDFConverter() as converter:
    endpoints = converter.endpoints
    print(f"Upload:     {endpoints['upload']}")
    print(f"Conversion: {endpoints['conversion']}")
    print(f"Status:     {endpoints['status']}")
    print(f"Download:   {endpoints['download']}")
```

### Inspect JWT Token

```python
from adobe.utils import extract_tenant_id_from_token
import base64
import json

access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."

# Extract tenant
tenant = extract_tenant_id_from_token(access_token)
print(f"Tenant ID: {tenant}")

# Decode token manually to inspect
parts = access_token.split(".")
payload_b64 = parts[1]
padding = 4 - len(payload_b64) % 4
if padding != 4:
    payload_b64 += "=" * padding

payload_json = base64.urlsafe_b64decode(payload_b64)
payload = json.loads(payload_json)
print(json.dumps(payload, indent=2))
```

## Regional Endpoints

Adobe uses different regions (`jpn3`, `va7`, etc.). The library uses the region from discovered endpoints:

```python
# If your discovered endpoints use a different region:
# https://pdfnow-va7.adobe.io/...

# The library will extract and preserve the region
from adobe.urls import build_endpoint_urls

# Build endpoints for specific region
endpoints = build_endpoint_urls(
    tenant_id="1761291926",
    region="va7"  # or "jpn3", etc.
)
```

## Best Practices

1. **Let the library handle tenants automatically** - Don't hardcode tenant IDs
2. **Use session rotation** - Each fresh session gets a new tenant ID
3. **Save discovered endpoints** - Keep your `discovered_endpoints.json` updated
4. **Enable logging** - Monitor which tenant IDs are being used
5. **Don't share tenant IDs** - They're session-specific and temporary

## Troubleshooting

### "No tenant ID available"

**Cause:** IMS token didn't contain a tenant identifier

**Solutions:**
1. Check if access token was obtained successfully
2. Verify the JWT token format
3. Use environment variable overrides with your tenant ID

### "API endpoints not configured"

**Cause:** No tenant-specific endpoints available

**Solutions:**
1. Capture endpoints via Chrome DevTools (see `docs/discovery/API_DISCOVERY.md`)
2. Update `discovered_endpoints.json` with real endpoints
3. Set environment variables with your tenant's endpoints

### Endpoints using wrong tenant

**Cause:** Stale session or cached tenant ID

**Solutions:**
1. Clear session data: `await converter.reset_session_data()`
2. Create fresh session: `AdobePDFConverter.create_with_fresh_session()`
3. Delete `~/.adobe-helper/session.json`

## Summary

The **multi-tenant support** ensures:

✓ Each session automatically gets its own tenant ID
✓ API endpoints are dynamically built with the correct tenant
✓ Different sessions can use different tenants simultaneously
✓ Tenant IDs are extracted from IMS tokens automatically
✓ Session persistence includes tenant information
✓ URL substitution handles both discovered and template endpoints

No manual configuration needed - just initialize a session and convert!
