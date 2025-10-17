"""Constants for Futunn API.

Defines market identifiers, ranking options, and default configuration shared
across the client library.
"""

from dataclasses import dataclass

# Market Types
MARKET_TYPE_HK = 1
MARKET_TYPE_US = 2
MARKET_TYPE_CN = 4
MARKET_TYPE_SG = 15
MARKET_TYPE_AU = 22
MARKET_TYPE_JP = 25
MARKET_TYPE_MY = 27
MARKET_TYPE_CA = 30

# Plate Types
PLATE_TYPE_ALL = 1

# Rank Types
RANK_TYPE_TOP_TURNOVER = 5
RANK_TYPE_TOP_GAINERS = 1
RANK_TYPE_TOP_LOSERS = 2
RANK_TYPE_TOP_VOLUME = 3
RANK_TYPE_TOP_AMPLITUDE = 4

# Default Configuration
DEFAULT_PAGE_SIZE = 50
DEFAULT_TIMEOUT = 10
DEFAULT_CONCURRENCY_LIMIT = 5

# User Agent
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/141.0.0.0 Safari/537.36"
)

# API Response Codes
SUCCESS_CODE = 0
ERROR_CODE = -1


@dataclass(frozen=True)
class MarketInfo:
    """Canonical metadata for a Futunn market."""

    code: str
    slug: str
    name: str
    market_type: int


MARKETS: dict[str, MarketInfo] = {
    "HK": MarketInfo(code="HK", slug="hk", name="Hong Kong", market_type=MARKET_TYPE_HK),
    "US": MarketInfo(code="US", slug="us", name="United States", market_type=MARKET_TYPE_US),
    "CN": MarketInfo(code="CN", slug="cn", name="Mainland China", market_type=MARKET_TYPE_CN),
    "SG": MarketInfo(code="SG", slug="sg", name="Singapore", market_type=MARKET_TYPE_SG),
    "AU": MarketInfo(code="AU", slug="au", name="Australia", market_type=MARKET_TYPE_AU),
    "JP": MarketInfo(code="JP", slug="jp", name="Japan", market_type=MARKET_TYPE_JP),
    "MY": MarketInfo(code="MY", slug="my", name="Malaysia", market_type=MARKET_TYPE_MY),
    "CA": MarketInfo(code="CA", slug="ca", name="Canada", market_type=MARKET_TYPE_CA),
}

# Convenience tuple for validation and iteration
SUPPORTED_MARKET_TYPES: frozenset[int] = frozenset(
    market.market_type for market in MARKETS.values()
)

_MARKET_CODE_LOOKUP: dict[str, MarketInfo] = {
    market.code.upper(): market for market in MARKETS.values()
}
_MARKET_SLUG_LOOKUP: dict[str, MarketInfo] = {
    market.slug.lower(): market for market in MARKETS.values()
}


def resolve_market_type(value: int | str | MarketInfo) -> int:
    """Normalize different market identifiers to a Futunn market type integer."""

    if isinstance(value, MarketInfo):
        return value.market_type

    if isinstance(value, int):
        if value not in SUPPORTED_MARKET_TYPES:
            raise ValueError(f"Unsupported market type id: {value}")
        return value

    if isinstance(value, str):
        code = value.strip()
        if not code:
            raise ValueError("Market identifier cannot be empty")

        # Allow uppercase codes (e.g., "US") and lowercase slugs (e.g., "us")
        market = _MARKET_CODE_LOOKUP.get(code.upper())
        if market is None:
            market = _MARKET_SLUG_LOOKUP.get(code.lower())

        if market is None:
            raise ValueError(f"Unknown market identifier: {value}")
        return market.market_type

    raise TypeError(
        "market value must be an int, str, or MarketInfo instance"
    )
