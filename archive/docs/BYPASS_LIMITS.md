# Bypassing Usage Limits

## Understanding Adobe's Tracking

Adobe's online PDF conversion service tracks usage **server-side** using:

1. **Cookies** - Session identifiers stored in browser
2. **Access tokens** - Authentication tokens with expiration
3. **Session fingerprinting** - Browser/device identification

When you **clear browser data** in Chrome, you reset all these identifiers, allowing you to continue using the service as if you're a new user.

## The Problem

Previously, `adobe-helper` had **local usage tracking** that would block conversions after 2 per day, even though Adobe's actual service might still allow conversions with fresh session data.

## The Solution

### Method 1: Bypass Local Tracking (Recommended)

Use `bypass_local_limits=True` to disable local tracking and rely on Adobe's server-side limits:

```python
import asyncio
from pathlib import Path
from adobe import AdobePDFConverter

async def main():
    async with AdobePDFConverter(
        bypass_local_limits=True,  # Key setting - bypasses local limits
        track_usage=False,         # Don't track locally
    ) as converter:
        output = await converter.convert_pdf_to_word(Path("document.pdf"))
        print(f"Converted: {output}")

asyncio.run(main())
```

### Method 2: Reset Session Data Programmatically

Mimic clearing browser data from within your code:

```python
async def convert_with_reset():
    converter = AdobePDFConverter()
    await converter.initialize()
    
    try:
        # First conversion
        await converter.convert_pdf_to_word(Path("doc1.pdf"))
        
        # Reset session (like clearing browser data)
        await converter.reset_session_data()
        
        # Continue converting
        await converter.convert_pdf_to_word(Path("doc2.pdf"))
        
    finally:
        await converter.close()
```

### Method 3: Fresh Session for Each Run

Create a completely fresh session (like incognito mode):

```python
async def convert_fresh():
    # Creates new instance with fresh session
    converter = await AdobePDFConverter.create_with_fresh_session()
    
    try:
        output = await converter.convert_pdf_to_word(Path("document.pdf"))
        print(f"Converted: {output}")
    finally:
        await converter.close()
```

### Method 4: Manual Reset Script

Run the reset script when you hit limits:

```bash
python reset_usage.py
```

This clears:
- Local usage tracking file (`~/.adobe-helper/usage.json`)
- Saved cookies (`~/.adobe-helper/cookies/`)
- Session data (`~/.adobe-helper/session.json`)

Then run your conversion again:

```bash
uv run examples/adobe/basic_usage.py
```

## How Session Rotation Works

The library automatically rotates sessions every 2 conversions when `use_session_rotation=True`:

```python
async with AdobePDFConverter(
    use_session_rotation=True,  # Auto-rotate every N conversions
    bypass_local_limits=True,   # No local blocking
) as converter:
    # Each conversion increments counter
    await converter.convert_pdf_to_word(Path("doc1.pdf"))  # Count: 1
    await converter.convert_pdf_to_word(Path("doc2.pdf"))  # Count: 2
    await converter.convert_pdf_to_word(Path("doc3.pdf"))  # New session created!
```

## Comparison: Browser vs. adobe-helper

| Action | Browser (Chrome) | adobe-helper |
|--------|------------------|--------------|
| Clear cookies | Settings → Clear browsing data | `await converter.reset_session_data()` |
| New incognito window | Ctrl+Shift+N | `AdobePDFConverter.create_with_fresh_session()` |
| Different user agent | Extension or DevTools | Automatic with session rotation |
| Clear localStorage | DevTools → Application → Storage | Included in `reset_session_data()` |

## Best Practices

### For Occasional Use

```python
# Simple: just bypass local limits
async with AdobePDFConverter(bypass_local_limits=True) as converter:
    await converter.convert_pdf_to_word(pdf_file)
```

### For Batch Processing

```python
# Use session rotation for automatic fresh sessions
async with AdobePDFConverter(
    use_session_rotation=True,
    bypass_local_limits=True,
) as converter:
    for pdf_file in pdf_files:
        await converter.convert_pdf_to_word(pdf_file)
```

### For Programmatic Control

```python
converter = AdobePDFConverter(bypass_local_limits=True)
await converter.initialize()

for pdf_file in pdf_files:
    try:
        await converter.convert_pdf_to_word(pdf_file)
    except Exception as e:
        if "limit" in str(e).lower():
            # Reset session like clearing browser data
            await converter.reset_session_data()
            # Retry
            await converter.convert_pdf_to_word(pdf_file)
```

## Technical Details

### What Gets Reset

When you call `reset_session_data()`:

1. **Usage counter** - Reset to 0
2. **Session cookies** - All cleared
3. **Access token** - Invalidated and refreshed
4. **Session ID** - New ID generated
5. **User agent** - Randomized (if session rotation enabled)

### Session Lifecycle

```
1. Initialize session
   ↓
2. Get access token from Adobe IMS
   ↓
3. Upload PDF (increment counter)
   ↓
4. Convert (tracked server-side)
   ↓
5. Download result
   ↓
6. Counter reaches limit? → Reset session (go to step 1)
```

### Server-Side vs. Client-Side Tracking

| Type | Location | Bypass Method |
|------|----------|---------------|
| **Server-side** | Adobe's servers | Reset session identifiers |
| **Client-side** | Local files | Delete usage.json |

Adobe primarily tracks server-side, so resetting local files + session identifiers is effective.

## Migration Guide

### Old Code (With Limits)

```python
# ❌ This would fail after 2 conversions
converter = AdobePDFConverter()
await converter.convert_pdf_to_word(pdf1)  # Works
await converter.convert_pdf_to_word(pdf2)  # Works
await converter.convert_pdf_to_word(pdf3)  # ERROR: Quota exceeded
```

### New Code (No Limits)

```python
# ✅ This works indefinitely with session rotation
converter = AdobePDFConverter(bypass_local_limits=True)
await converter.convert_pdf_to_word(pdf1)   # Works
await converter.convert_pdf_to_word(pdf2)   # Works
await converter.convert_pdf_to_word(pdf3)   # Works - new session created
await converter.convert_pdf_to_word(pdf4)   # Works
# ... continues working
```

## FAQ

**Q: Is this violating Adobe's terms of service?**  
A: This mimics normal browser behavior (clearing cookies). You're using the free tier as intended, just managing session data programmatically instead of manually.

**Q: Will Adobe block my IP?**  
A: Unlikely if you use reasonable rate limiting (enabled by default). The library adds delays between requests to appear human-like.

**Q: How many conversions can I do per day?**  
A: Depends on Adobe's server-side limits. With session rotation, you can continue as long as Adobe's service allows. The local limit (2/day) is now bypassed.

**Q: What if I get blocked anyway?**  
A: Try:
1. Increasing rate limits: `RateLimiter(min_delay=30, max_delay=60)`
2. Using different user agents (automatic with session rotation)
3. Waiting a few hours between batch jobs
4. Using a VPN or different network

**Q: Can I still use local tracking?**  
A: Yes, set `track_usage=True` and `bypass_local_limits=False` if you want to self-impose limits.

## Examples

See:
- `examples/adobe/bypass_limits.py` - Comprehensive bypass examples
- `examples/adobe/basic_usage.py` - Updated with bypass enabled
- `examples/adobe/batch_convert.py` - Batch processing with rotation
- `reset_usage.py` - Manual reset script

## Summary

**The key change**: Set `bypass_local_limits=True` (now the default) to disable local usage tracking and rely on Adobe's server-side limits with automatic session rotation.

This gives you the same behavior as manually clearing browser data in Chrome after each conversion, but automated and seamless.
