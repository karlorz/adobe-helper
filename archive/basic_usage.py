"""
Basic usage example for Futunn API Client

Demonstrates how to fetch stock lists and display basic information.
"""

import asyncio

from futunn import MARKET_TYPE_US, RANK_TYPE_TOP_TURNOVER, FutunnClient


async def main():
    """Main example function"""

    print("=== Futunn API Client - Basic Usage ===\n")

    # Create client instance
    async with FutunnClient() as client:
        print("Fetching top 10 US stocks by turnover...\n")

        # Fetch stock list
        stock_list = await client.get_stock_list(
            market_type=MARKET_TYPE_US, rank_type=RANK_TYPE_TOP_TURNOVER, page_size=10
        )

        # Display pagination info
        print(f"Total stocks available: {stock_list.pagination.total:,}")
        print(f"Total pages: {stock_list.pagination.page_count:,}")
        print(f"Current page: {stock_list.pagination.page}\n")

        # Display stocks
        print("Top 10 Stocks by Turnover:")
        print("-" * 80)
        print(
            f"{'Rank':<6}{'Symbol':<10}{'Name':<30}{'Price':<12}{'Change':<10}"
        )
        print("-" * 80)

        for idx, stock in enumerate(stock_list.stocks, 1):
            # Format price and change
            price = stock.price_nominal
            change = stock.change_ratio

            # Truncate long names
            name = (
                stock.name[:27] + "..." if len(stock.name) > 30 else stock.name
            )

            print(
                f"{idx:<6}{stock.stock_code:<10}{name:<30}{price:<12}{change:<10}"
            )

        print("-" * 80)


if __name__ == "__main__":
    asyncio.run(main())
