"""Crypto Market Agent — fetches data, runs analysis, sends Telegram brief."""

import asyncio
import sys
from datetime import datetime, timezone

from src.analyzers.technical import (
    calculate_macd,
    calculate_rsi,
    calculate_sma,
    get_signal_summary,
)
from src.data_sources import coingecko
from src.data_sources import fear_greed as fear_greed_client
from src.formatters.crypto_message import format_crypto_report
from src.models.crypto import CoinAnalysis, CoinIndicators, CryptoReport
from src.notifiers.telegram import TelegramNotifier
from src.utils.config import load_config
from src.utils.logger import setup_logger

logger = setup_logger("crypto_agent")


def analyze_coin(
    coin_data,
    config,
) -> CoinAnalysis | None:
    """Fetch OHLC and compute indicators for a single coin."""
    ohlc = coingecko.get_coin_ohlc(coin_data.id, days=30)
    if ohlc.empty:
        return None

    closes = ohlc["close"]
    ind_cfg = config.crypto.indicators
    rsi = calculate_rsi(closes, ind_cfg.rsi_period)
    macd = calculate_macd(closes, ind_cfg.macd_fast, ind_cfg.macd_slow, ind_cfg.macd_signal)
    sma_short = (
        calculate_sma(closes, ind_cfg.sma_short) if len(closes) >= ind_cfg.sma_short else None
    )
    sma_long = (
        calculate_sma(closes, ind_cfg.sma_long) if len(closes) >= ind_cfg.sma_long else None
    )

    # CoinGecko OHLC doesn't include volume, so skip volume spike for now
    indicators = CoinIndicators(
        rsi=rsi,
        macd_line=macd["line"],
        macd_signal=macd["signal"],
        macd_histogram=macd["histogram"],
        sma_short=sma_short,
        sma_long=sma_long,
        volume_spike=False,
    )

    signal = get_signal_summary(
        rsi=rsi,
        macd_histogram=macd["histogram"],
        price=coin_data.price,
        sma_short=sma_short,
        sma_long=sma_long,
    )

    return CoinAnalysis(coin=coin_data, indicators=indicators, signal=signal)


async def run(dry_run: bool = False) -> None:
    """Run the crypto market agent."""
    config = load_config(require_telegram=not dry_run)
    crypto_cfg = config.crypto
    errors: list[str] = []

    coin_ids = [p.id for p in crypto_cfg.portfolio]
    total_coins = len(coin_ids)

    # Fetch portfolio market data (single batch call)
    logger.info("Fetching market data for %d coins", total_coins)
    try:
        coins_data = coingecko.get_coins_market_data(coin_ids)
    except Exception as e:
        logger.error("Failed to fetch portfolio data: %s", e)
        if not dry_run:
            notifier = TelegramNotifier(config.telegram.bot_token, config.telegram.chat_id)
            await notifier.send_error(f"Failed to fetch portfolio data: {e}")
        sys.exit(1)

    coin_map = {c.id: c for c in coins_data}

    # Analyze each coin
    portfolio_analyses: list[CoinAnalysis] = []
    for item in crypto_cfg.portfolio:
        coin = coin_map.get(item.id)
        if not coin:
            errors.append(f"No data for {item.name} ({item.id})")
            continue
        try:
            analysis = analyze_coin(coin, config)
            if analysis:
                portfolio_analyses.append(analysis)
            else:
                errors.append(f"No OHLC data for {item.name}")
        except Exception as e:
            logger.error("Analysis failed for %s: %s", item.id, e)
            errors.append(f"Analysis failed for {item.name}: {e}")

    successful = len(portfolio_analyses)

    # Abort if less than 50% succeeded
    if total_coins > 0 and successful < total_coins * 0.5:
        msg = f"Too many failures: {successful}/{total_coins} coins succeeded"
        logger.error(msg)
        if not dry_run:
            notifier = TelegramNotifier(config.telegram.bot_token, config.telegram.chat_id)
            await notifier.send_error(msg)
        sys.exit(1)

    # Fetch market overview data
    market_overview = None
    fear_greed = None
    trending = []
    top_coins = []

    if crypto_cfg.sections.market_overview:
        try:
            market_overview = coingecko.get_global_data()
        except Exception as e:
            logger.error("Global data failed: %s", e)
            errors.append(f"Market overview unavailable: {e}")

    if crypto_cfg.sections.fear_greed:
        try:
            fear_greed = fear_greed_client.get_index()
        except Exception as e:
            logger.error("Fear & Greed failed: %s", e)
            errors.append(f"Fear & Greed unavailable: {e}")

    if crypto_cfg.sections.trending:
        try:
            trending = coingecko.get_trending()
        except Exception as e:
            logger.error("Trending failed: %s", e)
            errors.append(f"Trending unavailable: {e}")

    if crypto_cfg.sections.market_overview:
        try:
            top_coins = coingecko.get_top_coins(limit=10)
        except Exception as e:
            logger.error("Top coins failed: %s", e)
            errors.append(f"Top coins unavailable: {e}")

    # Build report
    report = CryptoReport(
        timestamp=datetime.now(timezone.utc),
        portfolio=portfolio_analyses,
        top_coins=top_coins,
        market_overview=market_overview,
        trending=trending,
        fear_greed=fear_greed,
        total_coins=total_coins,
        successful_coins=successful,
        errors=errors,
    )

    # Format message
    message = format_crypto_report(report)

    if dry_run:
        print("\n" + "=" * 60)
        print("CRYPTO MARKET DAILY BRIEF (DRY RUN)")
        print("=" * 60)
        import re

        print(re.sub(r"<[^>]+>", "", message))
        print("=" * 60)
        print(f"\nRaw HTML length: {len(message)} chars")
        return

    # Send via Telegram
    notifier = TelegramNotifier(config.telegram.bot_token, config.telegram.chat_id)
    ok = await notifier.send_message(message)
    if not ok:
        logger.error("Failed to send Telegram message")
        sys.exit(1)

    logger.info("Crypto brief sent successfully (%d chars)", len(message))


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
