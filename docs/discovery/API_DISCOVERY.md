# API Endpoint Discovery Guide

This guide explains how to discover Adobe's actual API endpoints using Chrome DevTools network analysis. This is the **critical final step** to make Adobe Helper functional.

## Why This Is Needed

Adobe Helper ships with placeholder endpoints. The runtime automatically looks for a discovery JSON file (see `docs/discovery/discovered_endpoints.json` or `~/.adobe-helper/discovered_endpoints.json`) and falls back to the placeholders only when no data is available. To make conversions work you must capture the **real endpoints** and populate the discovery file, which the client then loads via `adobe.urls.get_api_endpoints()`.

This guide walks through capturing those URLs so you can update the discovery JSON and let the library auto-configure itself.

## Prerequisites

- Google Chrome or Chromium browser
- A PDF file for testing (any small PDF will do)
- Basic understanding of browser DevTools

## Step-by-Step Guide

### Step 1: Open Chrome DevTools

1. Open Google Chrome
2. Navigate to: https://www.adobe.com/acrobat/online/pdf-to-word.html
3. Press `F12` or `Cmd+Option+I` (Mac) to open DevTools
4. Click on the **Network** tab
5. ✅ **Check "Preserve log"** checkbox (important!)
6. Clear any existing network logs (trash can icon)

### Step 2: Filter for API Requests

In the Network tab:
1. Click the **Filter** icon
2. Uncheck **All** and check only:
   - ✅ **Fetch/XHR** (this shows AJAX requests)
   - ✅ **Doc** (this shows document requests)
3. This will hide CSS, images, and scripts - showing only API calls

### Step 3: Upload a PDF File

1. Click "Select a file" on Adobe's page
2. Choose a small PDF file (1-2 pages is fine)
3. Watch the Network tab as the file uploads

### Step 4: Identify Upload Endpoint

Look for a POST request that contains your PDF file:

**What to look for:**
- Method: `POST`
- Type: Usually `fetch` or `xhr`
- Size: Should match your PDF file size
- Status: `200 OK` or `201 Created`

**Example patterns to watch for:**
```
POST /dc/api/upload/...
POST /acrobat-web/...upload...
POST /api/v1/...
```

**Click on the request and note:**
1. **Full URL** - Copy the complete URL from the Headers tab
2. **Request Headers** - Look for:
   - `X-CSRF-Token` or similar
   - `Authorization` headers
   - Custom Adobe headers
3. **Request Payload** - How is the PDF sent?
   - Multipart form data?
   - Base64 encoded?
   - Raw binary?

**Document this:**
```
Upload Endpoint: [PASTE URL HERE]
Method: POST
Headers:
  - X-CSRF-Token: [value or "from-cookie"]
  - Content-Type: multipart/form-data
Payload Format: [multipart/base64/raw]
```

### Step 5: Identify Conversion Endpoint

After upload, look for the next POST request that starts the conversion:

**What to look for:**
- Method: `POST`
- Happens right after upload
- Smaller payload (just metadata, not the file)
- Returns a job ID or conversion ID

**Example patterns:**
```
POST /dc/api/convert
POST /conversion/start
POST /api/v1/jobs/create
```

**Click on the request and note:**
1. **Full URL**
2. **Request Payload** - Usually JSON like:
   ```json
   {
     "uploadId": "...",
     "targetFormat": "docx",
     "feature": "pdf-to-word"
   }
   ```
3. **Response** - Should contain:
   ```json
   {
     "jobId": "...",
     "status": "processing"
   }
   ```

**Document this:**
```
Conversion Endpoint: [PASTE URL HERE]
Method: POST
Payload Example: [PASTE JSON]
Response Example: [PASTE JSON]
```

### Step 6: Identify Status Polling Endpoint

Wait a few seconds and watch for repeated GET requests:

**What to look for:**
- Method: `GET`
- Repeats every 2-5 seconds
- URL contains job ID from conversion response
- Status changes from "processing" to "completed"

**Example patterns:**
```
GET /dc/api/status/{jobId}
GET /conversion/poll/{id}
GET /api/v1/jobs/{jobId}/status
```

**Click on a successful response and note:**
1. **Full URL pattern** - Replace actual job ID with `{jobId}` placeholder
2. **Response when completed**:
   ```json
   {
     "status": "completed",
     "downloadUrl": "https://...",
     "progress": 100
   }
   ```

**Document this:**
```
Status Endpoint: [PASTE URL PATTERN]
Method: GET
Polling Interval: ~2-5 seconds
Response Fields:
  - status: "processing" | "completed" | "failed"
  - downloadUrl: "..."
  - progress: 0-100
```

### Step 7: Identify Download Endpoint

Look for the final GET request that downloads the DOCX file:

**What to look for:**
- Method: `GET`
- Type: `document` or `fetch`
- Response: Large file (DOCX)
- Content-Type: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`

**The download URL should be in the status response from Step 6.**

**Document this:**
```
Download URL: [PASTE URL]
Method: GET
Headers Required: [any special headers]
```

## Step 8: Document Request/Response Formats

For each endpoint, create a documentation file:

### Create `API_ENDPOINTS.md`:

```markdown
# Adobe PDF-to-Word API Endpoints

## Upload File

**Endpoint:** `POST https://[discovered-url]`

**Headers:**
```
Content-Type: multipart/form-data
X-CSRF-Token: [from session]
```

**Payload:**
```
FormData:
  file: [PDF binary]
```

**Response:**
```json
{
  "uploadId": "abc123",
  "status": "uploaded"
}
```

## Start Conversion

**Endpoint:** `POST https://[discovered-url]`

**Headers:**
```
Content-Type: application/json
```

**Payload:**
```json
{
  "uploadId": "abc123",
  "targetFormat": "docx",
  "feature": "pdf-to-word"
}
```

**Response:**
```json
{
  "jobId": "xyz789",
  "status": "processing"
}
```

## Poll Status

**Endpoint:** `GET https://[discovered-url]/{jobId}`

**Response:**
```json
{
  "status": "completed",
  "downloadUrl": "https://...",
  "progress": 100
}
```

## Download File

**Endpoint:** `GET [downloadUrl from status]`

**Response:** Binary DOCX file
```

## Step 9: Update the Discovery JSON

Place the captured URLs into the discovery file so the helper library can load them automatically. There are two supported locations:

- Project-level default: `docs/discovery/discovered_endpoints.json`
- User cache: `~/.adobe-helper/discovered_endpoints.json`

Each entry should live under the `"endpoints"` mapping using the structure below (actual values omitted here):

```json
{
  "endpoints": {
    "upload": { "url": "https://pdfnow-<region>.adobe.io/<tenant>/assets" },
    "conversion": { "url": "https://pdfnow-<region>.adobe.io/<tenant>/assets/exportpdf" },
    "status": { "url": "https://pdfnow-<region>.adobe.io/<tenant>/jobs/status" },
    "download": { "url": "https://pdfnow-<region>.adobe.io/<tenant>/assets/download_uri" }
  }
}
```

When you run the client (or the helper script `python -m adobe.cli.api_discovery_helper update`), the project-level file is copied into the user cache if one is not already present. The client reads the user cache first, then project defaults, and finally falls back to environment variables before resorting to placeholders.

**CLI shortcuts:**
- `python -m adobe.cli.api_discovery_helper template` – create a fresh template if the file is missing
- `python -m adobe.cli.api_discovery_helper update` – validate URLs and sync project ↔ user cache
- `python -m adobe.cli.api_discovery_helper validate` – same as update but exits with non-zero status if any URL is missing
- Installed entry point: `adobe-api-discovery <command>`
- The helper writes to `~/.adobe-helper` when possible, but automatically falls back to `<project>/.adobe-helper` or the system temp directory when the home directory is read-only (e.g., sandboxed CI).

## Step 10: Test the Integration

After updating the discovery JSON:

```bash
# Quick sanity check for discovery plumbing
pytest tests/test_urls.py
```

Then try a live conversion (requires valid endpoints and network access):

```bash
# Run a test conversion
cd adobe-helper
uv run python -c "
import asyncio
from pathlib import Path
from adobe import AdobePDFConverter

async def test():
    async with AdobePDFConverter() as converter:
        result = await converter.convert_pdf_to_word(Path('test.pdf'))
        print(f'Success: {result}')

asyncio.run(test())
"
```

## Tips for Successful Discovery

### Common Mistakes to Avoid

❌ **Don't** clear network logs before conversion completes
✅ **Do** enable "Preserve log" in DevTools

❌ **Don't** only look at the first few requests
✅ **Do** scroll through the entire timeline

❌ **Don't** assume endpoint names
✅ **Do** copy exact URLs from DevTools

### What If I Can't Find an Endpoint?

**Upload not found?**
- Look for large POST requests (file size)
- Check Response tab for upload ID

**Conversion not found?**
- Look for POST right after upload
- Check for JSON payloads with "convert" or "job"

**Status not found?**
- Look for repeated GET requests
- Filter by "fetch" or "XHR" type
- Check for job IDs in URLs

### Advanced: Using Chrome DevTools MCP

If you have the Chrome DevTools MCP server installed:

```bash
# Take a snapshot during conversion
mcp-chrome snapshot

# Search network requests
mcp-chrome network --filter "api"
```

## Need Help?

If you're stuck:

1. **Check the Examples**: Look at `/examples/adobe/` for usage patterns
2. **Review AGENTS.md**: Contains Adobe's architecture analysis
3. **Check Request Payloads**: Sometimes endpoints are in response bodies
4. **Try Different PDFs**: Sometimes different file sizes trigger different endpoints

## Security Notes

- ⚠️ **Never commit actual session tokens** to git
- ⚠️ **Don't share your personal cookies** or session IDs
- ✅ **Only document the endpoint URLs** and request formats
- ✅ **Use placeholder values** in documentation

## Next Steps After Discovery

Once you've discovered and documented all endpoints:

1. ✅ Add the real URLs to `docs/discovery/discovered_endpoints.json` (and confirm they flow to `~/.adobe-helper/discovered_endpoints.json`)
2. ✅ Document the endpoints in `API_ENDPOINTS.md`
3. ✅ Test with a real PDF file
4. ✅ Add integration tests
5. ✅ Update this guide with actual endpoint patterns (optional)

Good luck! Once you complete this step, Adobe Helper will be 100% functional! 🎉
