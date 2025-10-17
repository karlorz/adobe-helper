"""
Futunn API Client

Main client class for interacting with Futunn's quote API.
Inspired by the Translator class from py-googletrans.
"""

import asyncio
import logging
from collections.abc import Mapping

import httpx

from futunn import constants, urls
from futunn.exceptions import (
    FutunnAPIError,
    InvalidResponseError,
    RateLimitError,
    TokenExpiredError,
)
from futunn.models import StockList
from futunn.token import TokenManager

logger = logging.getLogger(__name__)


class FutunnClient:
    """
    Asynchronous client for Futunn quote API.

    Example:
        >>> import asyncio
        >>> from futunn import FutunnClient
        >>>
        >>> async def main():
        >>>     client = FutunnClient()
        >>>     stock_list = await client.get_stock_list(market_type=2, page_size=10)
        >>>     for stock in stock_list.stocks:
        >>>         print(f"{stock.stock_code}: ${stock.price_nominal}")
        >>>
        >>> asyncio.run(main())
    """

    def __init__(
        self,
        proxies: str | Mapping[str, str] | None = None,
        timeout: int = constants.DEFAULT_TIMEOUT,
        concurrency_limit: int = constants.DEFAULT_CONCURRENCY_LIMIT,
    ):
        """
        Initialize FutunnClient.

        Args:
            proxies: Optional proxy configuration for requests
            timeout: Request timeout in seconds (default: 10)
            concurrency_limit: Maximum concurrent requests (default: 5)
        """
        client_kwargs = {
            "http2": True,
            "timeout": timeout,
            "follow_redirects": True,
        }

        self.client = None  # type: ignore[assignment]

        if proxies:
            proxy_value: str | Mapping[str, str] | None = proxies
            if isinstance(proxies, Mapping):
                proxy_value = (
                    proxies.get("all")
                    or proxies.get("https")
                    or proxies.get("http")
                    or None
                )

            if proxy_value is not None:
                try:
                    self.client = httpx.AsyncClient(proxy=proxy_value, **client_kwargs)
                except TypeError:
                    self.client = None

            if self.client is None:
                try:
                    self.client = httpx.AsyncClient(proxies=proxies, **client_kwargs)
                except TypeError as exc:  # pragma: no cover - defensive
                    raise ValueError("Unsupported proxy configuration for current httpx version") from exc

        if self.client is None:
            self.client = httpx.AsyncClient(**client_kwargs)
        self.token_manager = TokenManager(self.client)
        self.concurrency_limit = concurrency_limit
        self._semaphore = asyncio.Semaphore(concurrency_limit)

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def close(self):
        """Close the HTTP client connection"""
        await self.client.aclose()

    async def get_stock_list(
        self,
        market_type: int | str | constants.MarketInfo = constants.MARKET_TYPE_US,
        plate_type: int = constants.PLATE_TYPE_ALL,
        rank_type: int = constants.RANK_TYPE_TOP_TURNOVER,
        page: int = 0,
        page_size: int = constants.DEFAULT_PAGE_SIZE,
    ) -> StockList:
        """
        Fetch a paginated list of stocks.

        Args:
            market_type: Market identifier (see ``futunn.constants.MARKETS``)
            plate_type: Plate type (1=all stocks)
            rank_type: Ranking type (5=turnover, 1=gainers, 2=losers)
            page: Page number (0-indexed)
            page_size: Number of stocks per page (default: 50)

        Returns:
            StockList containing pagination info and list of stocks

        Raises:
            FutunnAPIError: If API request fails
            TokenExpiredError: If authentication fails
            RateLimitError: If rate limit is exceeded

        Example:
            >>> client = FutunnClient()
            >>> stocks = await client.get_stock_list(market_type=2, page_size=10)
            >>> print(f"Total: {stocks.pagination.total} stocks")
        """
        resolved_market_type = constants.resolve_market_type(market_type)

        params = {
            "marketType": resolved_market_type,
            "plateType": plate_type,
            "rankType": rank_type,
            "page": page,
            "pageSize": page_size,
        }

        try:
            data = await self._make_request(urls.GET_STOCK_LIST, params=params)
            return StockList.from_dict(data)

        except InvalidResponseError as e:
            logger.error(f"Invalid response from API: {e}")
            raise

    async def get_multiple_pages(
        self,
        pages: list[int],
        market_type: int | str | constants.MarketInfo = constants.MARKET_TYPE_US,
        rank_type: int = constants.RANK_TYPE_TOP_TURNOVER,
        page_size: int = constants.DEFAULT_PAGE_SIZE,
    ) -> list[StockList]:
        """
        Fetch multiple pages concurrently with rate limiting.

        Args:
            pages: List of page numbers to fetch
            market_type: Market identifier (see ``futunn.constants.MARKETS``)
            rank_type: Ranking type (5=turnover, 1=gainers, 2=losers)
            page_size: Number of stocks per page

        Returns:
            List of StockList objects, one per page

        Example:
            >>> client = FutunnClient(concurrency_limit=5)
            >>> results = await client.get_multiple_pages([0, 1, 2, 3, 4])
            >>> total_stocks = sum(len(result.stocks) for result in results)
        """

        resolved_market_type = constants.resolve_market_type(market_type)

        async def fetch_with_semaphore(page: int) -> StockList:
            async with self._semaphore:
                return await self.get_stock_list(
                    market_type=resolved_market_type,
                    rank_type=rank_type,
                    page=page,
                    page_size=page_size,
                )
        tasks = [fetch_with_semaphore(page) for page in pages]
        results = await asyncio.gather(*tasks)
        return results

    async def get_all_stocks(
        self,
        market_type: int | str | constants.MarketInfo = constants.MARKET_TYPE_US,
        rank_type: int = constants.RANK_TYPE_TOP_TURNOVER,
        max_pages: int | None = None,
    ) -> list[StockList]:
        """
        Fetch all available stocks (or up to max_pages).

        Args:
            market_type: Market identifier (see ``futunn.constants.MARKETS``)
            rank_type: Ranking type (5=turnover, 1=gainers, 2=losers)
            max_pages: Maximum number of pages to fetch (None = all pages)

        Returns:
            List of all StockList objects

        Example:
            >>> client = FutunnClient()
            >>> results = await client.get_all_stocks(max_pages=10)
        """
        # First, fetch page 0 to get total page count
        resolved_market_type = constants.resolve_market_type(market_type)

        first_page = await self.get_stock_list(
            market_type=resolved_market_type, rank_type=rank_type, page=0
        )

        total_pages = first_page.pagination.page_count
        if max_pages:
            total_pages = min(total_pages, max_pages)

        logger.info(f"Fetching {total_pages} pages of stocks")

        # Fetch remaining pages (we already have page 0)
        if total_pages > 1:
            remaining_pages = list(range(1, total_pages))
            remaining_results = await self.get_multiple_pages(
                remaining_pages,
                market_type=resolved_market_type,
                rank_type=rank_type,
            )
            return [first_page] + remaining_results
        else:
            return [first_page]

    async def get_index_quote(
        self,
        market_type: int | str | constants.MarketInfo = constants.MARKET_TYPE_US,
    ) -> dict:
        """
        Get market index quote data.

        Args:
            market_type: Market identifier (see ``futunn.constants.MARKETS``)

        Returns:
            Dictionary containing index quote data

        Example:
            >>> client = FutunnClient()
            >>> index_data = await client.get_index_quote(market_type=2)
        """
        params = {"marketType": constants.resolve_market_type(market_type)}
        return await self._make_request(urls.GET_INDEX_QUOTE, params=params)

    async def _make_request(
        self,
        url: str,
        *,
        params: dict | None = None,
        data: dict | None = None,
        retry_on_token_error: bool = True,
    ) -> dict:
        """
        Make an authenticated API request.

        Args:
            url: API endpoint URL
            params: Query parameters
            retry_on_token_error: Whether to retry once on token error

        Returns:
            JSON response as dictionary

        Raises:
            FutunnAPIError: On API errors
            TokenExpiredError: On authentication errors
            RateLimitError: On rate limit errors
        """
        # Get authentication headers
        headers = await self.token_manager.get_headers(params=params, data=data)

        try:
            logger.debug(f"Making request to {url} with params {params}")

            response = await self.client.get(url, params=params, headers=headers)

            # Handle different response codes
            if response.status_code == 200:
                data = response.json()

                # Check API response code
                if data.get("code") == constants.SUCCESS_CODE:
                    return data
                else:
                    error_msg = data.get("message", "Unknown error")
                    raise InvalidResponseError(f"API error: {error_msg}")

            elif response.status_code == 403:
                # Token expired or invalid
                if retry_on_token_error:
                    logger.warning("Token expired, refreshing and retrying")
                    await self.token_manager.refresh_tokens()
                    return await self._make_request(
                        url, params=params, data=data, retry_on_token_error=False
                    )
                else:
                    raise TokenExpiredError("Authentication failed after retry")

            elif response.status_code == 429:
                raise RateLimitError("API rate limit exceeded")

            else:
                raise FutunnAPIError(
                    f"API request failed with status {response.status_code}"
                )

        except httpx.RequestError as e:
            logger.error(f"Network error: {e}")
            raise FutunnAPIError(f"Network error: {e}")
