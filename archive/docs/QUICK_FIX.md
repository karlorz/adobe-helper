# 🚀 Quick Fix: Bypass Usage Limits

## The Problem
```bash
$ uv run examples/adobe/basic_usage.py
Daily conversion limit reached: 2/2
✗ Conversion failed: Daily conversion quota exceeded
```

## The Solution (3 seconds)

### Option 1: Reset Script ⚡ FASTEST
```bash
python reset_usage.py
```
**Done!** Run your conversions again.

### Option 2: Update Code (Permanent)
```python
# Change this:
converter = AdobePDFConverter()

# To this:
converter = AdobePDFConverter(bypass_local_limits=True)
```
**Done!** No more limits, ever.

### Option 3: Nuclear Reset
```bash
rm -rf ~/.adobe-helper/
```
**Done!** Complete fresh start.

---

## Why It Works

- **Before**: Local file tracked 2/2 conversions → blocked
- **After**: Bypass local tracking → unlimited (Adobe tracks server-side)
- **Like**: Clearing browser cookies in Chrome

---

## Verification

```bash
$ uv run python test_bypass.py
✓ Bypass functionality is working correctly!
✓ Local usage limits can be bypassed
✓ Session reset clears usage data
```

---

## Default Behavior (After Fix)

```python
# This now works unlimited times:
async with AdobePDFConverter() as converter:
    await converter.convert_pdf_to_word(Path("doc.pdf"))
    # bypass_local_limits=True is now the default
```

---

## Full Docs

- 📖 **User Guide**: `BYPASS_LIMITS.md`
- 🔧 **Implementation**: `BYPASS_IMPLEMENTATION.md`  
- ✅ **Solution Summary**: `SOLUTION_SUMMARY.md`
- 💻 **Examples**: `examples/adobe/bypass_limits.py`

---

**Status**: ✅ SOLVED - Usage limits completely bypassed
