import os
import tempfile

import pytest
import yaml

from src.utils.config import AppConfig, TelegramConfig, load_config


@pytest.fixture
def sample_config_dict():
    return {
        "stock": {
            "watchlist": [{"symbol": "AAPL", "name": "Apple"}],
            "alerts": {"rsi_overbought": 70, "rsi_oversold": 30, "volume_spike": 2.0},
            "indicators": {
                "rsi_period": 14,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
                "sma_short": 20,
                "sma_long": 50,
            },
            "sections": {
                "watchlist": True,
                "market_overview": True,
                "sector_performance": True,
                "top_movers": True,
            },
        },
        "crypto": {
            "portfolio": [{"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin"}],
            "alerts": {"rsi_overbought": 70, "rsi_oversold": 30, "volume_spike": 2.0},
            "indicators": {
                "rsi_period": 14,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
                "sma_short": 20,
                "sma_long": 50,
            },
            "sections": {
                "portfolio": True,
                "market_overview": True,
                "trending": True,
                "fear_greed": True,
            },
        },
    }


@pytest.fixture
def config_file(sample_config_dict, tmp_path):
    path = tmp_path / "config.yaml"
    with open(path, "w") as f:
        yaml.dump(sample_config_dict, f)
    return str(path)


class TestConfigLoading:
    def test_loads_valid_config(self, config_file, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token-123")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
        config = load_config(config_file)
        assert len(config.stock.watchlist) == 1
        assert config.stock.watchlist[0].symbol == "AAPL"
        assert len(config.crypto.portfolio) == 1
        assert config.telegram.bot_token == "test-token-123"

    def test_dry_run_no_telegram(self, config_file, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        config = load_config(config_file, require_telegram=False)
        assert config.telegram.bot_token == "dry-run-token"

    def test_empty_token_raises(self, config_file, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
        with pytest.raises(Exception):
            load_config(config_file)

    def test_empty_chat_id_raises(self, config_file, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "  ")
        with pytest.raises(Exception):
            load_config(config_file)

    def test_missing_watchlist_raises(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
        bad_config = {
            "stock": {
                "watchlist": [],  # Empty — should fail min_length=1
            },
            "crypto": {
                "portfolio": [{"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin"}],
            },
        }
        path = tmp_path / "bad.yaml"
        with open(path, "w") as f:
            yaml.dump(bad_config, f)
        with pytest.raises(Exception):
            load_config(str(path))

    def test_default_indicator_values(self, config_file, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
        config = load_config(config_file)
        assert config.stock.indicators.rsi_period == 14
        assert config.stock.indicators.macd_fast == 12
        assert config.stock.alerts.rsi_overbought == 70

    def test_section_flags(self, config_file, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
        config = load_config(config_file)
        assert config.stock.sections.watchlist is True
        assert config.crypto.sections.fear_greed is True


class TestTelegramConfig:
    def test_valid_config(self):
        tc = TelegramConfig(bot_token="abc123", chat_id="456")
        assert tc.bot_token == "abc123"

    def test_empty_token_raises(self):
        with pytest.raises(Exception):
            TelegramConfig(bot_token="", chat_id="456")

    def test_whitespace_token_raises(self):
        with pytest.raises(Exception):
            TelegramConfig(bot_token="   ", chat_id="456")
