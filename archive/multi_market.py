"""Multi-market snapshot example for the Futunn API client."""

import asyncio

from futunn import MARKETS, RANK_TYPE_TOP_TURNOVER, FutunnClient, MarketInfo


async def _fetch_market_preview(
    client: FutunnClient, market_entry: MarketInfo
) -> tuple[str, int, str]:
    """Fetch a single page for the provided market and return summary details."""

    stock_list = await client.get_stock_list(
        market_type=market_entry.market_type,
        rank_type=RANK_TYPE_TOP_TURNOVER,
        page_size=5,
    )

    total = stock_list.pagination.total
    top_symbol = stock_list.stocks[0].stock_code if stock_list.stocks else "N/A"
    return market_entry.code, total, top_symbol


async def main() -> None:
    """Fetch a quick snapshot for every supported market."""

    print("=== Futunn API Client - Multi-Market Snapshot ===\n")

    async with FutunnClient() as client:
        tasks = [
            _fetch_market_preview(client, market)
            for market in MARKETS.values()
        ]

        results = await asyncio.gather(*tasks)

    print("Market overview (top 5 turnover):")
    print("-" * 60)
    print(f"{'Market':<8}{'Total Listings':>18}{'Top Symbol':>16}")
    print("-" * 60)

    for code, total, symbol in results:
        print(f"{code:<8}{total:>18,}{symbol:>16}")

    print("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())
