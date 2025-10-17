"""
Bulk fetching example for Futunn API Client

Demonstrates how to fetch multiple pages concurrently with rate limiting.
"""

import asyncio
from datetime import datetime

from futunn import MARKET_TYPE_US, RANK_TYPE_TOP_TURNOVER, FutunnClient


async def main():
    """Main example function"""

    print("=== Futunn API Client - Bulk Fetch Example ===\n")

    # Create client with concurrency limit
    async with FutunnClient(concurrency_limit=5) as client:
        print("Fetching first 5 pages concurrently (250 stocks)...")
        start_time = datetime.now()

        # Fetch multiple pages at once
        pages_to_fetch = list(range(0, 5))  # Pages 0-4
        results = await client.get_multiple_pages(
            pages=pages_to_fetch,
            market_type=MARKET_TYPE_US,
            rank_type=RANK_TYPE_TOP_TURNOVER,
        )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Aggregate results
        all_stocks = []
        for result in results:
            all_stocks.extend(result.stocks)

        print(f"\n✓ Successfully fetched {len(all_stocks)} stocks in {duration:.2f}s")
        print(f"Average: {len(all_stocks)/duration:.1f} stocks/second\n")

        # Display summary statistics
        print("Summary Statistics:")
        print("-" * 60)

        # Count by market label
        market_counts = {}
        for stock in all_stocks:
            market_counts[stock.market_label] = (
                market_counts.get(stock.market_label, 0) + 1
            )

        for market, count in market_counts.items():
            print(f"  {market} stocks: {count}")

        # Find top gainers and losers
        print("\nTop 5 Gainers:")
        sorted_by_change = sorted(
            all_stocks,
            key=lambda s: float(s.change_ratio.rstrip("%").replace("+", "")),
            reverse=True,
        )[:5]

        for stock in sorted_by_change:
            print(
                f"  {stock.stock_code:<8} {stock.name[:25]:<25} {stock.change_ratio:>8}"
            )

        print("\nTop 5 Losers:")
        sorted_by_change = sorted(
            all_stocks,
            key=lambda s: float(s.change_ratio.rstrip("%").replace("+", "")),
        )[:5]

        for stock in sorted_by_change:
            print(
                f"  {stock.stock_code:<8} {stock.name[:25]:<25} {stock.change_ratio:>8}"
            )

        print("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())
