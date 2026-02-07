from datetime import datetime, timezone

import pandas as pd
import yfinance as yf
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.models.stock import MarketIndex, Mover, SectorPerformance, StockQuote
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

MARKET_INDICES = [
    ("S&P 500", "SPY"),
    ("NASDAQ", "QQQ"),
    ("Dow Jones", "DIA"),
    ("Russell 2000", "IWM"),
]

SECTOR_ETFS = [
    ("Technology", "XLK"),
    ("Healthcare", "XLV"),
    ("Financials", "XLF"),
    ("Consumer Disc.", "XLY"),
    ("Consumer Staples", "XLP"),
    ("Energy", "XLE"),
    ("Utilities", "XLU"),
    ("Industrials", "XLI"),
    ("Materials", "XLB"),
    ("Real Estate", "XLRE"),
    ("Communication", "XLC"),
]


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    reraise=True,
)
def get_quotes(symbols: list[str], names: dict[str, str]) -> list[StockQuote]:
    """Fetch current quotes for a list of symbols."""
    quotes = []
    tickers = yf.Tickers(" ".join(symbols))

    for symbol in symbols:
        try:
            ticker = tickers.tickers[symbol]
            info = ticker.fast_info
            price = info.last_price
            prev_close = info.previous_close

            if price is None or prev_close is None or price <= 0:
                logger.warning("Invalid price data for %s", symbol)
                continue

            change_pct = ((price - prev_close) / prev_close) * 100
            quotes.append(
                StockQuote(
                    symbol=symbol,
                    name=names.get(symbol, symbol),
                    price=round(price, 2),
                    change_percent=round(change_pct, 2),
                    volume=int(info.last_volume or 0),
                    prev_close=round(prev_close, 2),
                    timestamp=datetime.now(timezone.utc),
                )
            )
        except Exception as e:
            logger.error("Failed to fetch quote for %s: %s", symbol, e)

    return quotes


def get_daily_history(symbol: str, period: str = "1mo") -> pd.DataFrame:
    """Fetch daily OHLCV history for technical analysis."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        if df.empty:
            logger.warning("Empty history for %s", symbol)
            return pd.DataFrame()
        return df
    except Exception as e:
        logger.error("Failed to fetch history for %s: %s", symbol, e)
        return pd.DataFrame()


def get_market_overview() -> list[MarketIndex]:
    """Fetch major market index ETF prices."""
    indices = []
    symbols = [s for _, s in MARKET_INDICES]
    tickers = yf.Tickers(" ".join(symbols))

    for name, symbol in MARKET_INDICES:
        try:
            info = tickers.tickers[symbol].fast_info
            price = info.last_price
            prev = info.previous_close
            if price and prev and prev > 0:
                change = ((price - prev) / prev) * 100
                indices.append(
                    MarketIndex(
                        name=name,
                        symbol=symbol,
                        price=round(price, 2),
                        change_percent=round(change, 2),
                    )
                )
        except Exception as e:
            logger.error("Failed to fetch index %s: %s", symbol, e)

    return indices


def get_sector_performance() -> list[SectorPerformance]:
    """Fetch sector ETF performance."""
    sectors = []
    symbols = [s for _, s in SECTOR_ETFS]
    tickers = yf.Tickers(" ".join(symbols))

    for name, symbol in SECTOR_ETFS:
        try:
            info = tickers.tickers[symbol].fast_info
            price = info.last_price
            prev = info.previous_close
            if price and prev and prev > 0:
                change = ((price - prev) / prev) * 100
                sectors.append(
                    SectorPerformance(
                        name=name,
                        symbol=symbol,
                        change_percent=round(change, 2),
                    )
                )
        except Exception as e:
            logger.error("Failed to fetch sector %s: %s", symbol, e)

    sectors.sort(key=lambda s: s.change_percent, reverse=True)
    return sectors


def get_top_movers(limit: int = 5) -> tuple[list[Mover], list[Mover]]:
    """Fetch top gainers and losers from major indices.

    Uses a set of widely-held large-cap stocks as the universe.
    """
    universe = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
        "JPM", "JNJ", "V", "UNH", "XOM", "PG", "MA", "HD", "CVX", "MRK",
        "ABBV", "PEP", "KO", "COST", "AVGO", "LLY", "WMT", "MCD", "CSCO",
        "ACN", "TMO", "ABT", "DHR", "NEE", "LIN", "PM", "TXN", "UNP",
        "RTX", "ORCL", "CRM", "AMD",
    ]

    movers: list[Mover] = []
    tickers = yf.Tickers(" ".join(universe))

    for symbol in universe:
        try:
            info = tickers.tickers[symbol].fast_info
            price = info.last_price
            prev = info.previous_close
            if price and prev and prev > 0:
                change = ((price - prev) / prev) * 100
                movers.append(
                    Mover(symbol=symbol, name=symbol, change_percent=round(change, 2))
                )
        except Exception:
            continue

    movers.sort(key=lambda m: m.change_percent, reverse=True)
    gainers = movers[:limit]
    losers = movers[-limit:][::-1]  # worst performers, most negative first
    return gainers, losers
