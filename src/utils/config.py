import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class AlertConfig(BaseModel):
    rsi_overbought: float = 70
    rsi_oversold: float = 30
    volume_spike: float = 2.0


class IndicatorConfig(BaseModel):
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    sma_short: int = 20
    sma_long: int = 50


class WatchlistEntry(BaseModel):
    symbol: str
    name: str


class StockSections(BaseModel):
    watchlist: bool = True
    market_overview: bool = True
    sector_performance: bool = True
    top_movers: bool = True


class StockConfig(BaseModel):
    watchlist: list[WatchlistEntry] = Field(default_factory=list, min_length=1)
    alerts: AlertConfig = Field(default_factory=AlertConfig)
    indicators: IndicatorConfig = Field(default_factory=IndicatorConfig)
    sections: StockSections = Field(default_factory=StockSections)


class PortfolioEntry(BaseModel):
    id: str
    symbol: str
    name: str


class CryptoSections(BaseModel):
    portfolio: bool = True
    market_overview: bool = True
    trending: bool = True
    fear_greed: bool = True


class CryptoConfig(BaseModel):
    portfolio: list[PortfolioEntry] = Field(default_factory=list, min_length=1)
    alerts: AlertConfig = Field(default_factory=AlertConfig)
    indicators: IndicatorConfig = Field(default_factory=IndicatorConfig)
    sections: CryptoSections = Field(default_factory=CryptoSections)


class TelegramConfig(BaseModel):
    bot_token: str = ""
    chat_id: str = ""

    @model_validator(mode="after")
    def check_not_empty(self) -> "TelegramConfig":
        if not self.bot_token.strip():
            raise ValueError("TELEGRAM_BOT_TOKEN is empty or not set")
        if not self.chat_id.strip():
            raise ValueError("TELEGRAM_CHAT_ID is empty or not set")
        return self


class AppConfig(BaseModel):
    stock: StockConfig
    crypto: CryptoConfig
    telegram: TelegramConfig


def load_config(config_path: str | None = None, require_telegram: bool = True) -> AppConfig:
    """Load config from YAML file + environment variables.

    Args:
        config_path: Path to YAML config. Defaults to config/config.yaml,
                     falls back to config/config.example.yaml.
        require_telegram: If False, skip Telegram credential validation (for dry runs).
    """
    if config_path is None:
        project_root = Path(__file__).parent.parent.parent
        config_path = str(project_root / "config" / "config.yaml")
        if not Path(config_path).exists():
            config_path = str(project_root / "config" / "config.example.yaml")
            logger.info("Using config.example.yaml (no config.yaml found)")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not require_telegram:
        # Use dummy values for dry run
        bot_token = bot_token or "dry-run-token"
        chat_id = chat_id or "dry-run-chat-id"

    raw["telegram"] = {
        "bot_token": bot_token,
        "chat_id": chat_id,
    }

    config = AppConfig(**raw)
    logger.info(
        "Config loaded: %d stock watchlist items, %d crypto portfolio items",
        len(config.stock.watchlist),
        len(config.crypto.portfolio),
    )
    return config
