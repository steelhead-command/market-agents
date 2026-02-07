import time
from datetime import datetime, timezone

import pandas as pd
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.models.crypto import CoinData, GlobalCryptoData, TrendingCoin
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

BASE_URL = "https://api.coingecko.com/api/v3"

# Simple rate limiter: track last request time
_last_request_time = 0.0
_min_interval = 2.1  # seconds between requests (30 calls/min = 2s each)


def _rate_limit() -> None:
    """Enforce rate limiting between requests."""
    global _last_request_time
    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < _min_interval:
        time.sleep(_min_interval - elapsed)
    _last_request_time = time.monotonic()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=3, max=30),
    retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
    reraise=True,
)
def _get(endpoint: str, params: dict | None = None) -> dict | list:
    """Make a rate-limited GET request to CoinGecko."""
    _rate_limit()
    url = f"{BASE_URL}/{endpoint}"
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_coins_market_data(coin_ids: list[str]) -> list[CoinData]:
    """Batch fetch market data for portfolio coins. Single API call."""
    ids_str = ",".join(coin_ids)
    data = _get(
        "coins/markets",
        params={
            "vs_currency": "usd",
            "ids": ids_str,
            "order": "market_cap_desc",
            "sparkline": "false",
            "price_change_percentage": "24h,7d",
        },
    )

    coins = []
    for item in data:
        try:
            coins.append(
                CoinData(
                    id=item["id"],
                    symbol=item["symbol"].upper(),
                    name=item["name"],
                    price=item.get("current_price", 0),
                    change_24h=item.get("price_change_percentage_24h", 0) or 0,
                    change_7d=item.get("price_change_percentage_7d_in_currency"),
                    market_cap=item.get("market_cap", 0) or 0,
                    volume_24h=item.get("total_volume", 0) or 0,
                    rank=item.get("market_cap_rank"),
                )
            )
        except Exception as e:
            logger.error("Failed to parse coin data for %s: %s", item.get("id", "?"), e)

    return coins


def get_coin_ohlc(coin_id: str, days: int = 30) -> pd.DataFrame:
    """Fetch OHLC data for a coin. Returns DataFrame with columns: open, high, low, close."""
    try:
        data = _get(f"coins/{coin_id}/ohlc", params={"vs_currency": "usd", "days": days})
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df
    except Exception as e:
        logger.error("Failed to fetch OHLC for %s: %s", coin_id, e)
        return pd.DataFrame()


def get_top_coins(limit: int = 20) -> list[CoinData]:
    """Fetch top coins by market cap."""
    data = _get(
        "coins/markets",
        params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": limit,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h,7d",
        },
    )

    coins = []
    for item in data:
        try:
            coins.append(
                CoinData(
                    id=item["id"],
                    symbol=item["symbol"].upper(),
                    name=item["name"],
                    price=item.get("current_price", 0),
                    change_24h=item.get("price_change_percentage_24h", 0) or 0,
                    change_7d=item.get("price_change_percentage_7d_in_currency"),
                    market_cap=item.get("market_cap", 0) or 0,
                    volume_24h=item.get("total_volume", 0) or 0,
                    rank=item.get("market_cap_rank"),
                )
            )
        except Exception as e:
            logger.error("Failed to parse top coin: %s", e)

    return coins


def get_trending() -> list[TrendingCoin]:
    """Fetch trending coins."""
    try:
        data = _get("search/trending")
        coins = []
        for item in data.get("coins", []):
            coin = item.get("item", {})
            coins.append(
                TrendingCoin(
                    id=coin.get("id", ""),
                    symbol=coin.get("symbol", "").upper(),
                    name=coin.get("name", ""),
                    rank=coin.get("market_cap_rank"),
                    price_change_24h=coin.get("data", {}).get(
                        "price_change_percentage_24h", {}
                    ).get("usd"),
                )
            )
        return coins
    except Exception as e:
        logger.error("Failed to fetch trending: %s", e)
        return []


def get_global_data() -> GlobalCryptoData | None:
    """Fetch global crypto market data."""
    try:
        data = _get("global")
        d = data.get("data", {})
        total_cap = sum(d.get("total_market_cap", {}).values())
        total_vol = sum(d.get("total_volume", {}).values())

        return GlobalCryptoData(
            total_market_cap=total_cap,
            total_volume_24h=total_vol,
            btc_dominance=d.get("market_cap_percentage", {}).get("btc", 0),
            eth_dominance=d.get("market_cap_percentage", {}).get("eth"),
            market_cap_change_24h=d.get("market_cap_change_percentage_24h_usd"),
        )
    except Exception as e:
        logger.error("Failed to fetch global data: %s", e)
        return None
