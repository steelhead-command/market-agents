from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.agents.crypto_agent import analyze_coin, run
from src.models.crypto import CoinData


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.crypto.portfolio = [
        MagicMock(id="bitcoin", symbol="BTC", name="Bitcoin"),
        MagicMock(id="ethereum", symbol="ETH", name="Ethereum"),
    ]
    config.crypto.indicators.rsi_period = 14
    config.crypto.indicators.macd_fast = 12
    config.crypto.indicators.macd_slow = 26
    config.crypto.indicators.macd_signal = 9
    config.crypto.indicators.sma_short = 20
    config.crypto.indicators.sma_long = 50
    config.crypto.alerts.volume_spike = 2.0
    config.crypto.sections.market_overview = True
    config.crypto.sections.trending = True
    config.crypto.sections.fear_greed = True
    config.telegram.bot_token = "test-token"
    config.telegram.chat_id = "12345"
    return config


@pytest.fixture
def sample_ohlc():
    """Sample OHLC DataFrame for crypto."""
    dates = pd.date_range("2026-01-01", periods=60, freq="12h")
    closes = [50000 + i * 100 + (i % 7) * 50 for i in range(60)]
    return pd.DataFrame(
        {
            "open": closes,
            "high": [c + 500 for c in closes],
            "low": [c - 500 for c in closes],
            "close": closes,
        },
        index=dates,
    )


@pytest.fixture
def sample_coin():
    return CoinData(
        id="bitcoin",
        symbol="BTC",
        name="Bitcoin",
        price=97500.00,
        change_24h=2.15,
        change_7d=5.43,
        market_cap=1920000000000,
        volume_24h=35000000000,
        rank=1,
    )


class TestAnalyzeCoin:
    @patch("src.agents.crypto_agent.coingecko")
    def test_returns_analysis(self, mock_cg, sample_coin, sample_ohlc, mock_config):
        mock_cg.get_coin_ohlc.return_value = sample_ohlc
        result = analyze_coin(sample_coin, mock_config)
        assert result is not None
        assert result.coin.symbol == "BTC"
        assert result.signal in ("Bullish", "Bearish", "Neutral")

    @patch("src.agents.crypto_agent.coingecko")
    def test_empty_ohlc_returns_none(self, mock_cg, sample_coin, mock_config):
        mock_cg.get_coin_ohlc.return_value = pd.DataFrame()
        result = analyze_coin(sample_coin, mock_config)
        assert result is None


class TestCryptoAgentRun:
    @patch("src.agents.crypto_agent.TelegramNotifier")
    @patch("src.agents.crypto_agent.fear_greed_client")
    @patch("src.agents.crypto_agent.coingecko")
    @patch("src.agents.crypto_agent.load_config")
    async def test_dry_run(
        self, mock_load, mock_cg, mock_fg, mock_tg, mock_config, sample_ohlc, capsys
    ):
        mock_load.return_value = mock_config

        mock_cg.get_coins_market_data.return_value = [
            CoinData(
                id="bitcoin", symbol="BTC", name="Bitcoin",
                price=97500, change_24h=2.15, market_cap=1920e9, volume_24h=35e9, rank=1,
            ),
            CoinData(
                id="ethereum", symbol="ETH", name="Ethereum",
                price=3250, change_24h=-1.23, market_cap=390e9, volume_24h=18e9, rank=2,
            ),
        ]
        mock_cg.get_coin_ohlc.return_value = sample_ohlc
        mock_cg.get_global_data.return_value = None
        mock_cg.get_trending.return_value = []
        mock_cg.get_top_coins.return_value = []
        mock_fg.get_index.return_value = None

        await run(dry_run=True)

        captured = capsys.readouterr()
        assert "CRYPTO MARKET DAILY BRIEF" in captured.out
        assert "BTC" in captured.out

    @patch("src.agents.crypto_agent.TelegramNotifier")
    @patch("src.agents.crypto_agent.fear_greed_client")
    @patch("src.agents.crypto_agent.coingecko")
    @patch("src.agents.crypto_agent.load_config")
    async def test_sends_telegram(
        self, mock_load, mock_cg, mock_fg, mock_tg_cls, mock_config, sample_ohlc
    ):
        mock_load.return_value = mock_config
        mock_notifier = AsyncMock()
        mock_notifier.send_message.return_value = True
        mock_tg_cls.return_value = mock_notifier

        mock_cg.get_coins_market_data.return_value = [
            CoinData(
                id="bitcoin", symbol="BTC", name="Bitcoin",
                price=97500, change_24h=2.15, market_cap=1920e9, volume_24h=35e9, rank=1,
            ),
            CoinData(
                id="ethereum", symbol="ETH", name="Ethereum",
                price=3250, change_24h=-1.23, market_cap=390e9, volume_24h=18e9, rank=2,
            ),
        ]
        mock_cg.get_coin_ohlc.return_value = sample_ohlc
        mock_cg.get_global_data.return_value = None
        mock_cg.get_trending.return_value = []
        mock_cg.get_top_coins.return_value = []
        mock_fg.get_index.return_value = None

        await run(dry_run=False)
        mock_notifier.send_message.assert_called_once()
