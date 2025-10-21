# Adobe Helper

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/linter-ruff-orange.svg)](https://github.com/astral-sh/ruff)

**Adobe Helper** is a Python library for converting PDF files to Word (DOCX) format using Adobe's online conversion services. It provides a clean, async API with automatic session management, rate limiting, and quota tracking.

## ⚠️ Current Status

**This project is ~98% complete.** The architecture, all modules, and examples are fully implemented and tested. However, **API endpoint discovery is required** before the library can perform actual conversions.

### Recent Updates (2025-10-21)

✅ **Multi-Tenant Architecture**
- Automatic tenant discovery during session initialization
- Dynamic endpoint switching per session
- Support for multiple regions and tenant IDs
- Each session discovers its own numeric tenant ID from Adobe's servers

✅ **Logging Enhancement**
- Examples now include proper logging configuration
- Real-time visibility into conversion progress
- Better debugging and troubleshooting support

See [docs/discovery/API_DISCOVERY.md](docs/discovery/API_DISCOVERY.md) for instructions on discovering Adobe's actual API endpoints using Chrome DevTools.

## Features

✨ **Easy to Use**
- Simple async API with context manager support
- Automatic session management and rotation
- Built-in retry logic with exponential backoff
- **Bypass local usage limits** (mimics clearing browser data)

📊 **Smart Management**
- Optional usage tracking with daily limits
- Intelligent rate limiting with human-like delays
- Automatic session rotation for unlimited conversions
- Fresh session creation (like incognito mode)

🔒 **Reliable**
- Streaming upload/download for large files
- File integrity verification
- Comprehensive error handling
- Progress tracking support

🚀 **Fast**
- Async/await throughout
- HTTP/2 support via httpx
- Concurrent batch processing

## Installation

### Using uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/karlorz/adobe-helper.git
cd adobe-helper

# Install with uv
uv sync --all-extras
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/karlorz/adobe-helper.git
cd adobe-helper

# Install in development mode
pip install -e .
```

## Quick Start

### Basic Usage

```python
import asyncio
import logging
from pathlib import Path
from adobe import AdobePDFConverter

# Configure logging to see conversion progress
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

async def main():
    # Convert a PDF to Word (bypasses local limits by default)
    async with AdobePDFConverter(
        bypass_local_limits=True  # Mimics clearing browser data
    ) as converter:
        output_file = await converter.convert_pdf_to_word(
            Path("document.pdf")
        )
        print(f"Converted: {output_file}")

asyncio.run(main())
```

### Batch Conversion

```python
from adobe import AdobePDFConverter

async def batch_convert():
    pdf_files = [
        Path("doc1.pdf"),
        Path("doc2.pdf"),
        Path("doc3.pdf"),
    ]

    async with AdobePDFConverter() as converter:
        for pdf_file in pdf_files:
            try:
                output = await converter.convert_pdf_to_word(pdf_file)
                print(f"✓ {pdf_file.name} -> {output.name}")
            except Exception as e:
                print(f"✗ {pdf_file.name}: {e}")
```

### Advanced Configuration

```python
from adobe import AdobePDFConverter
from pathlib import Path

async def advanced_convert():
    # Custom configuration
    converter = AdobePDFConverter(
        session_dir=Path(".cache"),      # Custom cache directory
        use_session_rotation=True,       # Enable session rotation
        track_usage=True,                # Track daily quota
        enable_rate_limiting=True,       # Rate limiting
    )

    try:
        await converter.initialize()

        # Convert with custom output path
        output = await converter.convert_pdf_to_word(
            Path("input.pdf"),
            output_path=Path("output/converted.docx"),
        )

        # Check usage stats
        usage = converter.get_usage_summary()
        print(f"Daily usage: {usage['count']}/{usage['limit']}")

    finally:
        await converter.close()
```

## Endpoint Discovery CLI

Use the bundled helper to capture endpoints and keep discovery files synced:

```bash
# Show available commands
python -m adobe.cli.api_discovery_helper --help

# Create or refresh the project discovery template
python -m adobe.cli.api_discovery_helper template

# Validate captured URLs and sync project ↔ user cache copies
python -m adobe.cli.api_discovery_helper update

# Installed entry point (after `pip install .`)
adobe-api-discovery checklist
```

See [docs/discovery/API_DISCOVERY.md](docs/discovery/API_DISCOVERY.md) for the full walkthrough.

The helper stores discovered endpoints in `~/.adobe-helper` by default, but will fall back to `./.adobe-helper` (or the system temp directory) automatically when the home directory is not writable—useful for containerized or sandboxed environments.

## Architecture

### Core Components

```
adobe/
├── client.py              # Main AdobePDFConverter class
├── auth.py                # Session management
├── session_cycling.py     # Anonymous session rotation
├── cookie_manager.py      # Cookie persistence
├── upload.py              # File upload handler
├── conversion.py          # Conversion workflow manager
├── download.py            # File download handler
├── rate_limiter.py        # Rate limiting with backoff
├── usage_tracker.py       # Free tier quota tracking
├── models.py              # Pydantic data models
├── exceptions.py          # Custom exceptions
├── constants.py           # Configuration constants
├── urls.py                # API endpoints
└── utils.py               # Helper functions
```

### Data Flow

```
PDF File → Upload → Conversion Job → Poll Status → Download DOCX
           ↓         ↓                 ↓             ↓
        Validate  Create Job      Wait/Poll    Stream Download
        Retry     Track Status    Adaptive      Verify
                                  Polling       Integrity
```

## Examples

See the [`examples/adobe/`](examples/adobe/) directory for complete examples:

- **basic_usage.py** - Simple conversion with bypass enabled
- **batch_convert.py** - Sequential and concurrent batch processing
- **advanced_usage.py** - Advanced configuration and error handling

Legacy bypass/reset scripts now live under `archive/docs/` for reference.

### Bypassing Usage Limits

By default, the library now bypasses local usage tracking and relies on Adobe's server-side limits with automatic session rotation:

```python
# Automatic session rotation (recommended for batch processing)
async with AdobePDFConverter(
    bypass_local_limits=True,  # Default: True
    use_session_rotation=True,  # Auto-rotate sessions
) as converter:
    for pdf in pdf_files:
        await converter.convert_pdf_to_word(pdf)
```

For more details, see [BYPASS_LIMITS.md](BYPASS_LIMITS.md).

**Quick reset**: Call `AdobePDFConverter.reset_session_data()` (or use `AdobePDFConverter.create_with_fresh_session()`) to clear all local state; the legacy helper script now resides in `archive/docs/`.

## API Discovery Required

⚠️ **Important**: Before this library can perform actual conversions, you need to discover Adobe's API endpoints using Chrome DevTools.

See [docs/discovery/API_DISCOVERY.md](docs/discovery/API_DISCOVERY.md) for detailed instructions.

Discovered endpoint files are cached automatically: any `discovered_endpoints.json` found in `docs/discovery/` or `archive/discovery/` is copied into `~/.adobe-helper/` on first run, and a template is generated if missing.

## Development

### Setup Development Environment

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/karlorz/adobe-helper.git
cd adobe-helper
uv sync --all-extras --dev
```

### Run Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=adobe --cov-report=html

# Run specific test file
uv run pytest tests/test_models.py -v
```

### Code Quality

```bash
# Format code
uv run black adobe/ tests/

# Lint code
uv run ruff check adobe/ tests/

# Type checking
uv run mypy adobe/
```

## Project Status

### ✅ Completed (Phases 1-10)

- [x] Project setup and architecture
- [x] Data models with Pydantic validation
- [x] Custom exception hierarchy
- [x] Session management and rotation
- [x] Cookie management
- [x] Rate limiting with adaptive backoff
- [x] Usage tracking
- [x] File upload handler
- [x] Conversion workflow manager
- [x] File download handler
- [x] Main client class
- [x] Example scripts with logging
- [x] Unit tests (30 tests, 100% pass rate)
- [x] Documentation
- [x] **Multi-tenant architecture with automatic discovery** ✨ NEW
- [x] **Dynamic endpoint switching per session** ✨ NEW

### 🔄 Remaining

- [ ] **API endpoint discovery** (critical - see `docs/discovery/API_DISCOVERY.md`)
- [ ] Integration tests with real API
- [ ] CLI tool (optional)
- [ ] Browser automation fallback (optional)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run code quality checks
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This library is for legitimate use only. Please respect Adobe's Terms of Service and rate limits. The library includes built-in rate limiting and quota tracking to prevent abuse.

## Acknowledgments

- Inspired by Adobe's online PDF conversion services
- Built with [httpx](https://www.python-httpx.org/), [pydantic](https://docs.pydantic.dev/), and modern Python async patterns
- Developed using [uv](https://github.com/astral-sh/uv) for fast dependency management

## Support

- 📫 Issues: [GitHub Issues](https://github.com/karlorz/adobe-helper/issues)
- 📖 Documentation: See `examples/` and `AGENTS.md`
- 💬 Discussions: [GitHub Discussions](https://github.com/karlorz/adobe-helper/discussions)
