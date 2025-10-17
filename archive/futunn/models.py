"""
Data models for Futunn API responses

Uses dataclasses for type safety and clean serialization.
"""

from dataclasses import dataclass


@dataclass
class Stock:
    """Represents a single stock entry from the API"""

    stock_id: int
    name: str
    stock_code: str
    market_label: str
    instrument_type: int
    price_nominal: str
    change_ratio: str
    price_direct: str
    change: str
    trade_turnover: str
    trade_volumn: str
    market_val: str
    circulation_market_value: str
    total_shares: str
    circulation_total_shares: str
    c_5days: str | None = None
    c_5days_price_direct: str | None = None
    c_10days: str | None = None
    c_10days_price_direct: str | None = None
    c_20days: str | None = None
    c_20days_price_direct: str | None = None
    c_60days: str | None = None
    c_60days_price_direct: str | None = None
    c_120days: str | None = None
    c_120days_price_direct: str | None = None
    c_250days: str | None = None
    c_250days_price_direct: str | None = None
    c_year_days: str | None = None
    c_year_days_price_direct: str | None = None
    trade_changeraio: str | None = None
    price_amplitude: str | None = None
    volumn_ratio: str | None = None
    buysell_ratio: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Stock":
        """Create a Stock instance from API response dict"""
        return cls(
            stock_id=data.get("stockId"),
            name=data.get("name", ""),
            stock_code=data.get("stockCode", ""),
            market_label=data.get("marketLabel", ""),
            instrument_type=data.get("instrumentType", 0),
            price_nominal=data.get("priceNominal", "0"),
            change_ratio=data.get("changeRatio", "0%"),
            price_direct=data.get("priceDirect", ""),
            change=data.get("change", "0"),
            trade_turnover=data.get("tradeTrunover", "0"),
            trade_volumn=data.get("tradeVolumn", "0"),
            market_val=data.get("marketVal", "0"),
            circulation_market_value=data.get("circulationMarketValue", "0"),
            total_shares=data.get("totalShares", "0"),
            circulation_total_shares=data.get("circulationTotalShares", "0"),
            c_5days=data.get("c_5Days"),
            c_5days_price_direct=data.get("c_5Days_priceDirect"),
            c_10days=data.get("c_10Days"),
            c_10days_price_direct=data.get("c_10Days_priceDirect"),
            c_20days=data.get("c_20Days"),
            c_20days_price_direct=data.get("c_20Days_priceDirect"),
            c_60days=data.get("c_60Days"),
            c_60days_price_direct=data.get("c_60Days_priceDirect"),
            c_120days=data.get("c_120Days"),
            c_120days_price_direct=data.get("c_120Days_priceDirect"),
            c_250days=data.get("c_250Days"),
            c_250days_price_direct=data.get("c_250Days_priceDirect"),
            c_year_days=data.get("c_YearDays"),
            c_year_days_price_direct=data.get("c_YearDays_priceDirect"),
            trade_changeraio=data.get("tradeChangeraio"),
            price_amplitude=data.get("priceAmplitude"),
            volumn_ratio=data.get("volumnRatio"),
            buysell_ratio=data.get("buysellRatio"),
        )

    def to_dict(self) -> dict:
        """Convert Stock to dictionary"""
        return {
            "stockId": self.stock_id,
            "name": self.name,
            "stockCode": self.stock_code,
            "priceNominal": self.price_nominal,
            "changeRatio": self.change_ratio,
            "tradeTurnover": self.trade_turnover,
            "marketVal": self.market_val,
        }


@dataclass
class Pagination:
    """Represents pagination information from the API"""

    page: int
    page_size: int
    page_count: int
    total: int

    @classmethod
    def from_dict(cls, data: dict) -> "Pagination":
        """Create a Pagination instance from API response dict"""
        return cls(
            page=data.get("page", 0),
            page_size=data.get("pageSize", 50),
            page_count=data.get("pageCount", 0),
            total=data.get("total", 0),
        )


@dataclass
class StockList:
    """Represents a paginated list of stocks from the API"""

    pagination: Pagination
    stocks: list[Stock]
    code: int = 0
    message: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "StockList":
        """Create a StockList instance from API response dict"""
        if "data" not in data:
            raise ValueError("Invalid API response: missing 'data' field")

        return cls(
            code=data.get("code", 0),
            message=data.get("message", ""),
            pagination=Pagination.from_dict(data["data"].get("pagination", {})),
            stocks=[Stock.from_dict(item) for item in data["data"].get("list", [])],
        )

    def __len__(self) -> int:
        """Return the number of stocks in this list"""
        return len(self.stocks)

    def __iter__(self):
        """Allow iteration over stocks"""
        return iter(self.stocks)


@dataclass
class IndexQuote:
    """Represents market index quote data"""

    index_code: str
    name: str
    current_price: str
    change: str
    change_ratio: str
    price_direct: str

    @classmethod
    def from_dict(cls, data: dict) -> "IndexQuote":
        """Create an IndexQuote instance from API response dict"""
        return cls(
            index_code=data.get("indexCode", ""),
            name=data.get("name", ""),
            current_price=data.get("currentPrice", "0"),
            change=data.get("change", "0"),
            change_ratio=data.get("changeRatio", "0%"),
            price_direct=data.get("priceDirect", ""),
        )
