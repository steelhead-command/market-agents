"""Stock Market Agent — fetches data, runs analysis, sends Telegram brief."""

import asyncio
import sys
from datetime import datetime, timezone

from src.analyzers.technical import (
    calculate_macd,
    calculate_rsi,
    calculate_sma,
    detect_volume_spike,
    get_signal_summary,
)
from src.data_sources import yahoo_finance
from src.formatters.stock_message import format_stock_report
from src.models.stock import StockAnalysis, StockIndicators, StockReport
from src.notifiers.telegram import TelegramNotifier
from src.utils.config import load_config
from src.utils.logger import setup_logger

logger = setup_logger("stock_agent")


def analyze_ticker(
    symbol: str,
    name: str,
    quote,
    config,
) -> StockAnalysis | None:
    """Fetch history and compute indicators for a single ticker."""
    history = yahoo_finance.get_daily_history(symbol, period="3mo")
    if history.empty:
        return None

    closes = history["Close"]
    volumes = history["Volume"]
    ind_cfg = config.stock.indicators
    alert_cfg = config.stock.alerts

    rsi = calculate_rsi(closes, ind_cfg.rsi_period)
    macd = calculate_macd(closes, ind_cfg.macd_fast, ind_cfg.macd_slow, ind_cfg.macd_signal)
    sma_short = (
        calculate_sma(closes, ind_cfg.sma_short) if len(closes) >= ind_cfg.sma_short else None
    )
    sma_long = (
        calculate_sma(closes, ind_cfg.sma_long) if len(closes) >= ind_cfg.sma_long else None
    )
    vol_spike = detect_volume_spike(volumes, alert_cfg.volume_spike)

    indicators = StockIndicators(
        rsi=rsi,
        macd_line=macd["line"],
        macd_signal=macd["signal"],
        macd_histogram=macd["histogram"],
        sma_short=sma_short,
        sma_long=sma_long,
        volume_spike=vol_spike,
    )

    signal = get_signal_summary(
        rsi=rsi,
        macd_histogram=macd["histogram"],
        price=quote.price,
        sma_short=sma_short,
        sma_long=sma_long,
    )

    return StockAnalysis(quote=quote, indicators=indicators, signal=signal)


async def run(dry_run: bool = False) -> None:
    """Run the stock market agent."""
    config = load_config(require_telegram=not dry_run)
    stock_cfg = config.stock
    errors: list[str] = []

    symbols = [w.symbol for w in stock_cfg.watchlist]
    names = {w.symbol: w.name for w in stock_cfg.watchlist}
    total_tickers = len(symbols)

    # Fetch quotes
    logger.info("Fetching quotes for %d tickers", total_tickers)
    quotes = yahoo_finance.get_quotes(symbols, names)
    quote_map = {q.symbol: q for q in quotes}

    # Analyze each ticker
    watchlist_analyses: list[StockAnalysis] = []
    for item in stock_cfg.watchlist:
        quote = quote_map.get(item.symbol)
        if not quote:
            errors.append(f"No quote data for {item.symbol}")
            continue
        try:
            analysis = analyze_ticker(item.symbol, item.name, quote, config)
            if analysis:
                watchlist_analyses.append(analysis)
            else:
                errors.append(f"No history data for {item.symbol}")
        except Exception as e:
            logger.error("Analysis failed for %s: %s", item.symbol, e)
            errors.append(f"Analysis failed for {item.symbol}: {e}")

    successful = len(watchlist_analyses)

    # Abort if less than 50% succeeded
    if total_tickers > 0 and successful < total_tickers * 0.5:
        msg = f"Too many failures: {successful}/{total_tickers} tickers succeeded"
        logger.error(msg)
        if not dry_run:
            notifier = TelegramNotifier(config.telegram.bot_token, config.telegram.chat_id)
            await notifier.send_error(msg)
        sys.exit(1)

    # Fetch market data (independent calls)
    market_overview = []
    sectors = []
    gainers = []
    losers = []

    if stock_cfg.sections.market_overview:
        try:
            market_overview = yahoo_finance.get_market_overview()
        except Exception as e:
            logger.error("Market overview failed: %s", e)
            errors.append(f"Market overview unavailable: {e}")

    if stock_cfg.sections.sector_performance:
        try:
            sectors = yahoo_finance.get_sector_performance()
        except Exception as e:
            logger.error("Sector performance failed: %s", e)
            errors.append(f"Sector data unavailable: {e}")

    if stock_cfg.sections.top_movers:
        try:
            gainers, losers = yahoo_finance.get_top_movers()
        except Exception as e:
            logger.error("Top movers failed: %s", e)
            errors.append(f"Top movers unavailable: {e}")

    # Build report
    report = StockReport(
        timestamp=datetime.now(timezone.utc),
        watchlist=watchlist_analyses,
        market_overview=market_overview,
        sectors=sectors,
        top_gainers=gainers,
        top_losers=losers,
        total_tickers=total_tickers,
        successful_tickers=successful,
        errors=errors,
    )

    # Format message
    message = format_stock_report(report)

    if dry_run:
        print("\n" + "=" * 60)
        print("STOCK MARKET DAILY BRIEF (DRY RUN)")
        print("=" * 60)
        # Strip HTML for console display
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

    logger.info("Stock brief sent successfully (%d chars)", len(message))


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
