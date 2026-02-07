from datetime import datetime, timezone

import pytest

from src.formatters.crypto_message import format_crypto_report
from src.formatters.stock_message import format_stock_report
from src.models.crypto import (
    CoinAnalysis,
    CoinData,
    CoinIndicators,
    CryptoReport,
    FearGreedIndex,
    GlobalCryptoData,
    TrendingCoin,
)
from src.models.stock import (
    MarketIndex,
    Mover,
    SectorPerformance,
    StockAnalysis,
    StockIndicators,
    StockQuote,
    StockReport,
)
from src.notifiers.telegram import escape_html


NOW = datetime(2026, 2, 6, 16, 23, 0, tzinfo=timezone.utc)


@pytest.fixture
def stock_report():
    return StockReport(
        timestamp=NOW,
        watchlist=[
            StockAnalysis(
                quote=StockQuote(
                    symbol="AAPL",
                    name="Apple Inc.",
                    price=175.23,
                    change_percent=2.34,
                    volume=45000000,
                    prev_close=171.22,
                    timestamp=NOW,
                ),
                indicators=StockIndicators(
                    rsi=58.2,
                    macd_line=1.23,
                    macd_signal=0.98,
                    macd_histogram=0.25,
                    sma_short=172.50,
                    sma_long=168.30,
                    volume_spike=False,
                ),
                signal="Bullish",
            ),
        ],
        market_overview=[
            MarketIndex(name="S&P 500", symbol="SPY", price=523.45, change_percent=0.78),
        ],
        sectors=[
            SectorPerformance(name="Technology", symbol="XLK", change_percent=1.85),
        ],
        top_gainers=[
            Mover(symbol="NVDA", name="NVIDIA", change_percent=8.45),
        ],
        top_losers=[
            Mover(symbol="XOM", name="Exxon", change_percent=-5.67),
        ],
        total_tickers=1,
        successful_tickers=1,
    )


@pytest.fixture
def crypto_report():
    return CryptoReport(
        timestamp=NOW,
        portfolio=[
            CoinAnalysis(
                coin=CoinData(
                    id="bitcoin",
                    symbol="BTC",
                    name="Bitcoin",
                    price=97500.00,
                    change_24h=2.15,
                    change_7d=5.43,
                    market_cap=1920000000000,
                    volume_24h=35000000000,
                    rank=1,
                ),
                indicators=CoinIndicators(
                    rsi=62.5,
                    macd_line=500.0,
                    macd_signal=450.0,
                    macd_histogram=50.0,
                    sma_short=95000.0,
                    sma_long=90000.0,
                ),
                signal="Bullish",
            ),
        ],
        market_overview=GlobalCryptoData(
            total_market_cap=2800000000000,
            total_volume_24h=120000000000,
            btc_dominance=52.3,
            eth_dominance=16.8,
            market_cap_change_24h=1.45,
        ),
        fear_greed=FearGreedIndex(value=72, label="Greed"),
        trending=[
            TrendingCoin(id="pepe", symbol="PEPE", name="Pepe", price_change_24h=15.6),
        ],
        total_coins=1,
        successful_coins=1,
    )


class TestStockFormatter:
    def test_contains_header(self, stock_report):
        msg = format_stock_report(stock_report)
        assert "<b>Stock Market Daily Brief</b>" in msg

    def test_contains_ticker_data(self, stock_report):
        msg = format_stock_report(stock_report)
        assert "AAPL" in msg
        assert "175.23" in msg
        assert "+2.34%" in msg

    def test_contains_rsi(self, stock_report):
        msg = format_stock_report(stock_report)
        assert "RSI:" in msg
        assert "58.2" in msg

    def test_contains_market_overview(self, stock_report):
        msg = format_stock_report(stock_report)
        assert "MARKET OVERVIEW" in msg
        assert "S&amp;P 500" in msg  # HTML-escaped

    def test_contains_sectors(self, stock_report):
        msg = format_stock_report(stock_report)
        assert "SECTOR PERFORMANCE" in msg
        assert "Technology" in msg

    def test_contains_movers(self, stock_report):
        msg = format_stock_report(stock_report)
        assert "TOP MOVERS" in msg
        assert "NVDA" in msg
        assert "XOM" in msg

    def test_ticker_count(self, stock_report):
        msg = format_stock_report(stock_report)
        assert "1/1 tickers loaded" in msg

    def test_empty_watchlist(self):
        report = StockReport(timestamp=NOW, total_tickers=0, successful_tickers=0)
        msg = format_stock_report(report)
        assert "YOUR WATCHLIST" not in msg

    def test_with_errors(self):
        report = StockReport(
            timestamp=NOW,
            total_tickers=2,
            successful_tickers=1,
            errors=["No data for INVALID"],
        )
        msg = format_stock_report(report)
        assert "WARNINGS" in msg
        assert "INVALID" in msg


class TestCryptoFormatter:
    def test_contains_header(self, crypto_report):
        msg = format_crypto_report(crypto_report)
        assert "<b>Crypto Market Daily Brief</b>" in msg

    def test_contains_portfolio(self, crypto_report):
        msg = format_crypto_report(crypto_report)
        assert "BTC" in msg
        assert "Bitcoin" in msg
        assert "$97,500.00" in msg

    def test_contains_fear_greed(self, crypto_report):
        msg = format_crypto_report(crypto_report)
        assert "FEAR &amp; GREED INDEX" in msg
        assert "72/100" in msg
        assert "Greed" in msg

    def test_contains_market_overview(self, crypto_report):
        msg = format_crypto_report(crypto_report)
        assert "MARKET OVERVIEW" in msg
        assert "BTC Dominance" in msg

    def test_contains_trending(self, crypto_report):
        msg = format_crypto_report(crypto_report)
        assert "TRENDING" in msg
        assert "PEPE" in msg

    def test_empty_report(self):
        report = CryptoReport(timestamp=NOW, total_coins=0, successful_coins=0)
        msg = format_crypto_report(report)
        assert "Crypto Market Daily Brief" in msg


class TestHTMLEscaping:
    def test_escape_ampersand(self):
        assert escape_html("S&P 500") == "S&amp;P 500"

    def test_escape_angle_brackets(self):
        assert escape_html("<script>") == "&lt;script&gt;"

    def test_no_quote_escaping(self):
        assert escape_html('"quoted"') == '"quoted"'

    def test_plain_text_unchanged(self):
        assert escape_html("Hello World") == "Hello World"
