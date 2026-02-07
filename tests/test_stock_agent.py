from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.agents.stock_agent import analyze_ticker, run
from src.models.stock import StockQuote


@pytest.fixture
def mock_config():
    """Minimal config mock for stock agent."""
    config = MagicMock()
    config.stock.watchlist = [
        MagicMock(symbol="AAPL", name="Apple Inc."),
        MagicMock(symbol="MSFT", name="Microsoft Corp."),
    ]
    config.stock.indicators.rsi_period = 14
    config.stock.indicators.macd_fast = 12
    config.stock.indicators.macd_slow = 26
    config.stock.indicators.macd_signal = 9
    config.stock.indicators.sma_short = 20
    config.stock.indicators.sma_long = 50
    config.stock.alerts.volume_spike = 2.0
    config.stock.sections.market_overview = True
    config.stock.sections.sector_performance = True
    config.stock.sections.top_movers = True
    config.telegram.bot_token = "test-token"
    config.telegram.chat_id = "12345"
    return config


@pytest.fixture
def sample_history():
    """Sample OHLCV DataFrame with enough data for indicators."""
    dates = pd.date_range("2026-01-01", periods=60, freq="D")
    closes = [100 + i * 0.5 + (i % 5) for i in range(60)]
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [c + 2 for c in closes],
            "Low": [c - 2 for c in closes],
            "Close": closes,
            "Volume": [1_000_000 + i * 10000 for i in range(60)],
        },
        index=dates,
    )


@pytest.fixture
def sample_quote():
    return StockQuote(
        symbol="AAPL",
        name="Apple Inc.",
        price=175.23,
        change_percent=2.34,
        volume=45000000,
        prev_close=171.22,
        timestamp=datetime(2026, 2, 6, 16, 0, tzinfo=timezone.utc),
    )


class TestAnalyzeTicker:
    @patch("src.agents.stock_agent.yahoo_finance")
    def test_returns_analysis(self, mock_yf, sample_quote, sample_history, mock_config):
        mock_yf.get_daily_history.return_value = sample_history
        result = analyze_ticker("AAPL", "Apple Inc.", sample_quote, mock_config)
        assert result is not None
        assert result.quote.symbol == "AAPL"
        assert result.indicators.rsi is not None
        assert result.signal in ("Bullish", "Bearish", "Neutral")

    @patch("src.agents.stock_agent.yahoo_finance")
    def test_empty_history_returns_none(self, mock_yf, sample_quote, mock_config):
        mock_yf.get_daily_history.return_value = pd.DataFrame()
        result = analyze_ticker("AAPL", "Apple Inc.", sample_quote, mock_config)
        assert result is None


class TestStockAgentRun:
    @patch("src.agents.stock_agent.TelegramNotifier")
    @patch("src.agents.stock_agent.yahoo_finance")
    @patch("src.agents.stock_agent.load_config")
    async def test_dry_run(self, mock_load, mock_yf, mock_tg, mock_config, sample_history, capsys):
        mock_load.return_value = mock_config

        mock_yf.get_quotes.return_value = [
            StockQuote(
                symbol="AAPL",
                name="Apple Inc.",
                price=175.23,
                change_percent=2.34,
                volume=45000000,
                prev_close=171.22,
                timestamp=datetime.now(timezone.utc),
            ),
            StockQuote(
                symbol="MSFT",
                name="Microsoft Corp.",
                price=415.67,
                change_percent=-0.45,
                volume=22000000,
                prev_close=417.55,
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        mock_yf.get_daily_history.return_value = sample_history
        mock_yf.get_market_overview.return_value = []
        mock_yf.get_sector_performance.return_value = []
        mock_yf.get_top_movers.return_value = ([], [])

        await run(dry_run=True)

        captured = capsys.readouterr()
        assert "STOCK MARKET DAILY BRIEF" in captured.out
        assert "AAPL" in captured.out

    @patch("src.agents.stock_agent.TelegramNotifier")
    @patch("src.agents.stock_agent.yahoo_finance")
    @patch("src.agents.stock_agent.load_config")
    async def test_sends_telegram(self, mock_load, mock_yf, mock_tg_cls, mock_config, sample_history):
        mock_load.return_value = mock_config
        mock_notifier = AsyncMock()
        mock_notifier.send_message.return_value = True
        mock_tg_cls.return_value = mock_notifier

        mock_yf.get_quotes.return_value = [
            StockQuote(
                symbol="AAPL",
                name="Apple Inc.",
                price=175.23,
                change_percent=2.34,
                volume=45000000,
                prev_close=171.22,
                timestamp=datetime.now(timezone.utc),
            ),
            StockQuote(
                symbol="MSFT",
                name="Microsoft Corp.",
                price=415.67,
                change_percent=-0.45,
                volume=22000000,
                prev_close=417.55,
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        mock_yf.get_daily_history.return_value = sample_history
        mock_yf.get_market_overview.return_value = []
        mock_yf.get_sector_performance.return_value = []
        mock_yf.get_top_movers.return_value = ([], [])

        await run(dry_run=False)
        mock_notifier.send_message.assert_called_once()
