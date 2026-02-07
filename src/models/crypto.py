from datetime import datetime

from pydantic import BaseModel, Field


class PortfolioItem(BaseModel):
    id: str  # CoinGecko ID e.g. "bitcoin"
    symbol: str  # e.g. "BTC"
    name: str  # e.g. "Bitcoin"


class CoinData(BaseModel):
    id: str
    symbol: str
    name: str
    price: float = Field(ge=0)
    change_24h: float
    change_7d: float | None = None
    market_cap: float = Field(ge=0)
    volume_24h: float = Field(ge=0)
    rank: int | None = None


class CoinIndicators(BaseModel):
    rsi: float | None = None
    macd_line: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    sma_short: float | None = None
    sma_long: float | None = None
    volume_spike: bool = False


class CoinAnalysis(BaseModel):
    coin: CoinData
    indicators: CoinIndicators
    signal: str = "Neutral"


class TrendingCoin(BaseModel):
    id: str
    symbol: str
    name: str
    rank: int | None = None
    price_change_24h: float | None = None


class GlobalCryptoData(BaseModel):
    total_market_cap: float
    total_volume_24h: float
    btc_dominance: float
    eth_dominance: float | None = None
    market_cap_change_24h: float | None = None


class FearGreedIndex(BaseModel):
    value: int = Field(ge=0, le=100)
    label: str  # "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
    timestamp: datetime | None = None


class CryptoReport(BaseModel):
    timestamp: datetime
    portfolio: list[CoinAnalysis] = []
    top_coins: list[CoinData] = []
    market_overview: GlobalCryptoData | None = None
    trending: list[TrendingCoin] = []
    fear_greed: FearGreedIndex | None = None
    total_coins: int = 0
    successful_coins: int = 0
    errors: list[str] = []
