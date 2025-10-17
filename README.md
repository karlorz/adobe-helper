# futunn-helper

Asynchronous Python client for Futunn stock market quote API.

## Features

- 🚀 Async/await support with `httpx`
- 🌍 Multiple markets (US, HK, CN, SG, AU, JP, MY, CA)
- 🔐 Automatic token management
- 📊 Real-time stock data
- ⚡ Concurrent request handling

## Installation

```bash
pip install futunn-helper
```

## Quick Start

```python
import asyncio
from futunn import FutunnClient

async def main():
    client = FutunnClient()
    
    # Get top turnover US stocks
    stocks = await client.get_stock_list(
        market_type=2,      # US market
        rank_type=5,        # Top turnover
        page_size=50
    )
    
    print(f"Total: {stocks.pagination.total} stocks")
    for stock in stocks.stocks[:5]:
        print(f"{stock.stock_code}: ${stock.price_nominal}")

asyncio.run(main())
```

## Requirements

- Python >= 3.11
- httpx[http2] >= 0.27.0

## License

MIT License
