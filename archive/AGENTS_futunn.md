# AGENTS.md

**Instructions for Agents when working in this repository.**

## Project Overview

This is a **Futunn API Client** library inspired by the architecture of `py-googletrans`. The goal is to create an asynchronous Python client that fetches stock market data from Futunn's quote API endpoints.

**Target API:** `https://www.futunn.com/quote-api/quote-v2/get-stock-list`

**Reference Architecture:** `ssut/py-googletrans` - Uses `httpx.AsyncClient` with `asyncio` for concurrent HTTP requests.

## Key Features

- Async `httpx.AsyncClient` architecture with full awaitable API surface
- Built-in concurrency controls for fetching multiple pages in parallel
- Automatic token acquisition and refresh flow for Futunn endpoints
  - CSRF token sourced from response cookies
  - Quote-token generated via HMAC-SHA512/“quote_web” secret + SHA256 truncation
- Typed dataclass models for stocks, pagination, and responses
- Custom error hierarchy covering API failures, auth refresh, and rate limiting

## Quick Start (UV-Based Setup)

```bash
# Clone repository
git clone https://github.com/karlorz/futunn-helper.git
cd futunn-helper

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

## Architecture Design

### Core Components (Inspired by py-googletrans)

```
futunn-helper/
├── futunn/
│   ├── __init__.py
│   ├── client.py          # Main FutunnClient class (like Translator)
│   ├── token.py           # TokenManager class (like TokenAcquirer)
│   ├── models.py          # Data models (Stock, StockList, Pagination)
│   ├── urls.py            # API endpoint constants
│   ├── constants.py       # Market types, rank types, etc.
│   └── utils.py           # Helper functions (format_response, etc.)
├── examples/
│   ├── basic_usage.py
│   ├── bulk_fetch.py
│   └── real_time_monitor.py
├── tests/
│   └── test_client.py
├── requirements.txt
├── setup.py
├── README.md
└── AGENTS.md              # This file
```

---

## Technical Implementation Guidelines

### 1. HTTP Client Architecture

**Follow py-googletrans pattern:**

- Use `httpx.AsyncClient` for all HTTP requests
- Implement async/await throughout
- Support HTTP/2 and proxy configuration
- Handle rate limiting with `asyncio.Semaphore`

**Example Pattern:**
```python
class FutunnClient:
    def __init__(self, service_urls=None, proxies=None, timeout=10):
        self.client = httpx.AsyncClient(
            http2=True,
            proxies=proxies,
            timeout=timeout,
            follow_redirects=True
        )
        self.token_manager = TokenManager(self.client)
```

### 2. Token Management

**Required Headers for Futunn API:**
```python
Headers are generated per request by the token manager:

- `futu-x-csrf-token` — extracted from the `csrfToken` cookie
- `quote-token` — computed as `SHA256(HMAC_SHA512(payload or "quote", "quote_web"))[0:10]`
- `referer` — Futunn stock list page
- `user-agent` — desktop browser UA string
```

**Token Acquisition Strategy:**
- `TokenManager` visits the Futunn stock list page to capture the `csrfToken` cookie (cached until invalidated)
- Each API call signs its params/body using the Futunn web client algorithm (`quote-token` HMAC + SHA256 truncation)
- Tokens are regenerated automatically on 403 responses or explicit refresh

### 3. Async Request Handling

**Single Request:**
```python
async def get_stock_list(
    self,
    market_type: int = 2,      # 2 = US market
    plate_type: int = 1,       # 1 = all stocks
    rank_type: int = 5,        # 5 = top turnover
    page: int = 0,
    page_size: int = 50
) -> StockList:
    params = {
        'marketType': market_type,
        'plateType': plate_type,
        'rankType': rank_type,
        'page': page,
        'pageSize': page_size
    }

    url = urls.GET_STOCK_LIST.format(host=self._pick_service_url())
    response = await self.client.get(url, params=params, headers=self.headers)

    if response.status_code == 200:
        data = response.json()
        return StockList.from_dict(data)
    else:
        raise FutunnAPIError(f"API returned {response.status_code}")
```

**Bulk/Concurrent Requests:**
```python
async def get_multiple_pages(self, pages: List[int]) -> List[StockList]:
    semaphore = asyncio.Semaphore(self.concurrency_limit)

    async def fetch_with_semaphore(page: int):
        async with semaphore:
            return await self.get_stock_list(page=page)

    tasks = [fetch_with_semaphore(page) for page in pages]
    results = await asyncio.gather(*tasks)
    return results
```

### 4. Data Models

**Use dataclasses or Pydantic for type safety:**

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Stock:
    stock_id: int
    name: str
    stock_code: str
    market_label: str
    price_nominal: str
    change_ratio: str
    trade_turnover: str
    market_val: str
    # ... more fields

    @classmethod
    def from_dict(cls, data: dict) -> 'Stock':
        return cls(
            stock_id=data['stockId'],
            name=data['name'],
            stock_code=data['stockCode'],
            # ... map all fields
        )

@dataclass
class Pagination:
    page: int
    page_size: int
    page_count: int
    total: int

@dataclass
class StockList:
    pagination: Pagination
    stocks: List[Stock]

    @classmethod
    def from_dict(cls, data: dict) -> 'StockList':
        return cls(
            pagination=Pagination(**data['data']['pagination']),
            stocks=[Stock.from_dict(item) for item in data['data']['list']]
        )
```

### 5. Constants and Configuration

**urls.py:**
```python
# API endpoints
BASE_URL = "https://www.futunn.com"
GET_STOCK_LIST = BASE_URL + "/quote-api/quote-v2/get-stock-list"
GET_INDEX_QUOTE = BASE_URL + "/quote-api/quote-v2/get-index-quote"
GET_INDEX_SPARK_DATA = BASE_URL + "/quote-api/quote-v2/get-index-spark-data"
```

**constants.py:**
```python
from dataclasses import dataclass

# Market types (API identifiers)
MARKET_TYPE_HK = 1
MARKET_TYPE_US = 2
MARKET_TYPE_CN = 4
MARKET_TYPE_SG = 15
MARKET_TYPE_AU = 22
MARKET_TYPE_JP = 25
MARKET_TYPE_MY = 27
MARKET_TYPE_CA = 30

@dataclass(frozen=True)
class MarketInfo:
    code: str
    slug: str
    name: str
    market_type: int

MARKETS: dict[str, MarketInfo] = {
    "US": MarketInfo(code="US", slug="us", name="United States", market_type=MARKET_TYPE_US),
    # ... remaining markets (HK, CN, SG, AU, JP, MY, CA)
}

SUPPORTED_MARKET_TYPES = frozenset(info.market_type for info in MARKETS.values())

def resolve_market_type(value: int | str | MarketInfo) -> int:
    """Accepts numeric IDs, market codes ("US"), slugs ("us"), or MarketInfo objects."""
    ...

# Plate types
PLATE_TYPE_ALL = 1

# Rank types
RANK_TYPE_TOP_TURNOVER = 5
RANK_TYPE_TOP_GAINERS = 1
RANK_TYPE_TOP_LOSERS = 2
```

**Usage tip:** `MARKETS` provides human-friendly metadata (code, slug, display name, API id) for all eight supported exchanges. Pass either a `MarketInfo`, string code/slug, or raw integer to any client method; `resolve_market_type` normalizes the input before hitting the Futunn API.

---

## API Response Structure

### Successful Response
```json
{
  "code": 0,
  "message": "成功",
  "data": {
    "pagination": {
      "page": 0,
      "pageSize": 50,
      "pageCount": 215,
      "total": 10718
    },
    "list": [
      {
        "stockId": 202805,
        "name": "标普500ETF-SPDR",
        "stockCode": "SPY",
        "marketLabel": "US",
        "priceNominal": "653.020",
        "changeRatio": "-2.70%",
        "tradeTrunover": "1054.49亿",
        ...
      }
    ]
  }
}
```

### Error Handling
- `code: 0` = Success
- `code: -1` or other = Error
- HTTP 403 = Token expired or missing
- HTTP 429 = Rate limited

---

## Example Usage Patterns

### Basic Usage
```python
import asyncio
from futunn import FutunnClient

async def main():
    client = FutunnClient()

    # Fetch top turnover US stocks
    stock_list = await client.get_stock_list(
        market_type=2,      # US market
        rank_type=5,        # Top turnover
        page_size=50
    )

    print(f"Total stocks: {stock_list.pagination.total}")
    for stock in stock_list.stocks[:10]:
        print(f"{stock.stock_code}: {stock.name} - ${stock.price_nominal}")

asyncio.run(main())
```

### Bulk Fetching (Multiple Pages)
```python
async def fetch_all_pages():
    client = FutunnClient(concurrency_limit=5)

    # Fetch first 10 pages concurrently
    pages = range(0, 10)
    results = await client.get_multiple_pages(list(pages))

    all_stocks = []
    for result in results:
        all_stocks.extend(result.stocks)

    print(f"Fetched {len(all_stocks)} stocks")

asyncio.run(fetch_all_pages())
```

### Real-time Monitoring
```python
async def monitor_stocks(interval=5):
    client = FutunnClient()

    while True:
        stock_list = await client.get_stock_list()
        print(f"[{datetime.now()}] Top stock: {stock_list.stocks[0].stock_code}")
        await asyncio.sleep(interval)

asyncio.run(monitor_stocks())
```

---

## Development Workflow

### Phase 1: Core Implementation
1. Create `futunn/client.py` with `FutunnClient` class
2. Create `futunn/token.py` with `TokenManager` class
3. Create `futunn/models.py` with data models
4. Create `futunn/urls.py` and `futunn/constants.py`

### Phase 2: Testing
1. Write unit tests for token acquisition
2. Test single API request
3. Test concurrent requests with rate limiting
4. Test error handling (403, 429, timeouts)

### Phase 3: Features
1. Add support for different market types (HK, CN)
2. Add support for different ranking types (gainers, losers)
3. Add caching layer to reduce API calls
4. Add retry logic with exponential backoff

### Phase 4: Documentation & Examples
1. Write comprehensive README.md
2. Create example scripts
3. Add docstrings to all public methods
4. Create API documentation

## Support Resources for Agents

- When you need up-to-date documentation on Futunn APIs, Python packaging, or related tooling, use the Context7 MCP integration (`context7___resolve-library-id` followed by `context7___get-library-docs`) to retrieve the latest references.
- For quick-start guidance on Python package publishing workflows, query DeepWiki (`deepwiki___ask_question`) to pull concise setup and release instructions.

---

## Development Environment with UV

This project uses **UV** for dependency management and **Trusted Publishing** for secure PyPI releases.

### UV Setup (Quick Start)

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
# or
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# Setup development environment
uv python install 3.11
uv sync --all-extras --dev
```

### UV Commands

```bash
# Run code
uv run python examples/basic_usage.py
uv run pytest

# Build package
uv build

# Publish (with trusted publishing)
uv publish
```

### Manual CLI Reference

```bash
# Tests
uv run pytest tests/ -v
uv run pytest --cov=futunn --cov-report=html

# Quality checks
uv run ruff check futunn/ examples/
uv run black futunn/ examples/
uv run mypy futunn/

# Examples
uv run python examples/basic_usage.py
uv run python examples/bulk_fetch.py

# Build & validation
uv build
uv run twine check dist/*
```

### Why UV?

- **Fast**: 10-100x faster than pip
- **Reliable**: Lock file ensures reproducible builds
- **Simple**: Single tool for everything (venv, deps, build, publish)
- **Modern**: Built in Rust, designed for modern Python workflows

### Project Configuration (pyproject.toml)

The project uses `pyproject.toml` instead of `setup.py` + `requirements.txt`:

```toml
[project]
name = "futunn-helper"
version = "0.1.0"
dependencies = ["httpx[http2]>=0.27.0"]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.7.1",
    "black>=24.0.0"
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## Dependencies

**Required packages:**
```
httpx[http2]>=0.27.0 # Async HTTP client with HTTP/2 support + h2 extras
asyncio              # Built-in async support
dataclasses          # Built-in for Python 3.7+
typing               # Built-in type hints
```

**Development packages (installed with uv):**
```
pytest>=8.0          # For testing
pytest-asyncio>=0.23 # For async tests
ruff>=0.7.1          # Fast linter
black>=24.0.0        # Code formatter
mypy>=1.8.0          # Type checker
```

**Optional packages:**
```
pydantic>=2.0        # For advanced data validation
aiofiles>=23.0       # For async file I/O
```

---

## Best Practices

### 1. Always Use Async/Await
- All network operations must be async
- Use `asyncio.gather()` for concurrent operations
- Implement proper error handling in async contexts

### 2. Rate Limiting
- Default concurrency limit: 5 concurrent requests
- Use `asyncio.Semaphore` to enforce limits
- Implement exponential backoff on 429 errors

### 3. Token Management
- Cache tokens in memory
- Refresh tokens on 403 responses
- Don't hardcode tokens - fetch dynamically

### 4. Error Handling
```python
class FutunnAPIError(Exception):
    """Base exception for Futunn API errors"""
    pass

class TokenExpiredError(FutunnAPIError):
    """Raised when token is expired"""
    pass

class RateLimitError(FutunnAPIError):
    """Raised when rate limited"""
    pass
```

### 5. Type Hints
- Use type hints for all function signatures
- Use `typing.Optional` for nullable fields
- Use `typing.List`, `typing.Dict` for collections

### 6. Logging
```python
import logging

logger = logging.getLogger('futunn')
logger.setLevel(logging.INFO)

# Usage
logger.info(f"Fetching stock list: page={page}")
logger.error(f"API error: {response.status_code}")
```

---

## Testing Strategy

### Unit Tests
- Test token acquisition logic
- Test parameter building
- Test response parsing
- Test error handling

### Integration Tests
- Test actual API calls (with rate limiting)
- Test pagination
- Test concurrent requests
- Test token refresh flow

### Mock Testing
```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_get_stock_list():
    client = FutunnClient()
    client.client.get = AsyncMock(return_value=mock_response)

    result = await client.get_stock_list()
    assert len(result.stocks) == 50
```

---

## Security Considerations

1. **Do not commit tokens** - Add `.env` to `.gitignore`
2. **Respect rate limits** - Implement proper throttling
3. **Use HTTPS only** - Never downgrade to HTTP
4. **Handle sensitive data** - Don't log full responses with PII
5. **Implement timeouts** - Prevent hanging requests

---

## Known API Endpoints

Based on network analysis of `https://www.futunn.com/quote/us/stock-list/all-us-stocks/top-turnover`:

### Stock List API
```
GET /quote-api/quote-v2/get-stock-list
Parameters:
  - marketType: int (2=US, 1=HK, 3=CN)
  - plateType: int (1=all)
  - rankType: int (5=turnover, 1=gainers, 2=losers)
  - page: int (0-indexed)
  - pageSize: int (default: 50)
```

### Index Quote API
```
GET /quote-api/quote-v2/get-index-quote
Parameters:
  - marketType: int
```

### Index Spark Data API
```
GET /quote-api/quote-v2/get-index-spark-data
Parameters:
  - marketType: int
```

---

## Future Enhancements

1. **WebSocket Support** - Real-time streaming data
2. **Caching Layer** - Redis/SQLite for historical data
3. **CLI Tool** - Command-line interface for quick queries
4. **Data Export** - CSV/JSON/Parquet export functionality
5. **Visualization** - Integration with matplotlib/plotly
6. **Alerts** - Price/volume threshold notifications

---

## Contributing Guidelines

When working on this project:

1. Follow the py-googletrans architecture pattern
2. Maintain async/await consistency
3. Add type hints to all new functions
4. Write tests for new features
5. Update AGENTS.md when adding new APIs
6. Document all public methods with docstrings
7. Keep dependencies minimal

---

## Trusted Publishing to PyPI

This project uses **OpenID Connect (OIDC) Trusted Publishing** for secure, automated releases.

### What is Trusted Publishing?

- Eliminates need for manually managing PyPI API tokens
- Uses short-lived OIDC tokens from GitHub Actions
- More secure than long-lived API tokens
- Automatically configured between GitHub and PyPI

### Setup (One-Time)

**1. Configure PyPI:**
- Visit: https://pypi.org/manage/project/futunn-helper/settings/publishing/
- Add trusted publisher:
  - **Owner**: `karlorz`
  - **Repository**: `futunn-helper`
  - **Workflow**: `release.yml`
  - **Environment**: `pypi`

**2. Create GitHub Environment:**
- Go to: Repository → Settings → Environments
- Create environment named `pypi`
- (Optional) Add protection rules

### Publishing a Release

```bash
# 1. Update version in pyproject.toml
# version = "0.2.0"

# 2. Commit and tag
git add pyproject.toml
git commit -m "Release v0.2.0"
git tag v0.2.0

# 3. Push tag
git push origin main --tags

# 4. GitHub Actions automatically:
#    - Builds package
#    - Runs smoke tests
#    - Publishes to PyPI via OIDC
```

### Workflow Configuration

The `.github/workflows/release.yml` workflow handles releases:

```yaml
name: Release to PyPI

on:
  push:
    tags:
      - v*  # Trigger on version tags

jobs:
  pypi:
    name: Build and Publish to PyPI
    runs-on: ubuntu-latest

    environment:
      name: pypi  # Must match PyPI config

    permissions:
      id-token: write  # REQUIRED for OIDC
      contents: read

    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: uv python install 3.11
      - run: uv build
      - run: uv publish  # Uses OIDC automatically
```

### Continuous Integration

The `.github/workflows/ci.yml` runs on every push:

- Tests on Python 3.7-3.12
- Linting with ruff
- Formatting checks with black
- Type checking with mypy
- Build verification

---

## References

- **py-googletrans GitHub**: https://github.com/ssut/py-googletrans
- **httpx Documentation**: https://www.python-httpx.org/
- **asyncio Documentation**: https://docs.python.org/3/library/asyncio.html
- **Futunn Website**: https://www.futunn.com/
- **UV Documentation**: https://docs.astral.sh/uv/
- **Trusted Publishing**: https://docs.pypi.org/trusted-publishers/
- **Astral Trusted Publishing Examples**: https://github.com/astral-sh/trusted-publishing-examples

---

## Quick Start for Agents

To start implementing:

1. **Setup Environment**:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   uv python install 3.11
   uv sync --all-extras --dev
   ```

2. **Review This Guide**:
   - Key Features & Quick Start sections for workflow expectations
   - Technical Implementation Guidelines for architectural patterns
   - Support Resources to know when to use Context7 MCP or DeepWiki

3. **Implementation Order**:
   - Start with `futunn/models.py` (data structures)
   - Then `futunn/token.py` (token management)
   - Then `futunn/client.py` (main client)
   - Finally `examples/basic_usage.py` (usage examples)

4. **Development Workflow**:
   ```bash
   # Make changes
   uv run ruff check futunn/      # Lint
   uv run black futunn/           # Format
   uv run pytest                  # Test
   uv run python examples/basic_usage.py  # Try it
   ```

5. **Publishing**:
   ```bash
   # Update version in pyproject.toml
   git tag v0.1.0
   git push --tags
   # GitHub Actions handles the rest!
   ```

**Remember:**
- Follow the async patterns from py-googletrans exactly
- Use UV for all dependency management
- Let trusted publishing handle PyPI releases
- This architecture has proven to be robust, scalable, and maintainable
