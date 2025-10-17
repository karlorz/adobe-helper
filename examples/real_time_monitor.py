"""
Real-time monitoring example for Futunn API Client

Demonstrates how to continuously monitor top stocks at regular intervals.
"""

import asyncio
from datetime import datetime

from futunn import MARKET_TYPE_US, RANK_TYPE_TOP_TURNOVER, FutunnClient


async def monitor_top_stocks(interval: int = 5, top_n: int = 5):
    """
    Monitor top N stocks by turnover at regular intervals.

    Args:
        interval: Seconds between each update
        top_n: Number of top stocks to display
    """
    print("=== Futunn API Client - Real-Time Monitor ===\n")
    print(f"Monitoring top {top_n} stocks every {interval} seconds")
    print("Press Ctrl+C to stop\n")

    async with FutunnClient() as client:
        iteration = 0

        try:
            while True:
                iteration += 1
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                print(f"\n[{timestamp}] Update #{iteration}")
                print("-" * 80)

                # Fetch latest data
                stock_list = await client.get_stock_list(
                    market_type=MARKET_TYPE_US,
                    rank_type=RANK_TYPE_TOP_TURNOVER,
                    page_size=top_n,
                )

                # Display top stocks
                print(
                    f"{'Rank':<6}{'Symbol':<10}{'Price':<12}{'Change':<10}{'Turnover':<15}"
                )
                print("-" * 80)

                for idx, stock in enumerate(stock_list.stocks[:top_n], 1):
                    # Format values
                    symbol = stock.stock_code
                    price = stock.price_nominal
                    change = stock.change_ratio
                    turnover = stock.trade_turnover

                    print(
                        f"{idx:<6}{symbol:<10}{price:<12}{change:<10}{turnover:<15}"
                    )

                print("-" * 80)

                # Wait before next update
                await asyncio.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n✓ Monitoring stopped by user")
        except Exception as e:
            print(f"\n✗ Error occurred: {e}")


async def main():
    """Main entry point"""
    # Monitor top 5 stocks every 10 seconds
    await monitor_top_stocks(interval=10, top_n=5)


if __name__ == "__main__":
    asyncio.run(main())
