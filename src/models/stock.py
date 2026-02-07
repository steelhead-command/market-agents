from datetime import datetime

from pydantic import BaseModel, Field


class WatchlistItem(BaseModel):
    symbol: str
    name: str


class StockQuote(BaseModel):
    symbol: str
    name: str
    price: float = Field(gt=0)
    change_percent: float
    volume: int = Field(ge=0)
    prev_close: float = Field(gt=0)
    timestamp: datetime


class StockIndicators(BaseModel):
    rsi: float | None = None
    macd_line: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    sma_short: float | None = None
    sma_long: float | None = None
    volume_spike: bool = False


class StockAnalysis(BaseModel):
    quote: StockQuote
    indicators: StockIndicators
    signal: str = "Neutral"  # Bullish / Bearish / Neutral


class MarketIndex(BaseModel):
    name: str
    symbol: str
    price: float
    change_percent: float


class SectorPerformance(BaseModel):
    name: str
    symbol: str
    change_percent: float


class Mover(BaseModel):
    symbol: str
    name: str
    change_percent: float


class StockReport(BaseModel):
    timestamp: datetime
    watchlist: list[StockAnalysis] = []
    market_overview: list[MarketIndex] = []
    sectors: list[SectorPerformance] = []
    top_gainers: list[Mover] = []
    top_losers: list[Mover] = []
    total_tickers: int = 0
    successful_tickers: int = 0
    errors: list[str] = []
