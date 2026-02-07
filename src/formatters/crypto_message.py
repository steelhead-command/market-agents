from datetime import datetime, timezone

from src.models.crypto import CryptoReport
from src.notifiers.telegram import escape_html


def _format_large_number(n: float) -> str:
    """Format a large number with suffix."""
    if n >= 1_000_000_000_000:
        return f"${n / 1_000_000_000_000:.2f}T"
    if n >= 1_000_000_000:
        return f"${n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"${n / 1_000_000:.2f}M"
    return f"${n:,.2f}"


def _format_price(price: float) -> str:
    """Format price — more decimals for small values."""
    if price >= 1:
        return f"${price:,.2f}"
    if price >= 0.01:
        return f"${price:.4f}"
    return f"${price:.6f}"


def _change_arrow(pct: float) -> str:
    if pct > 0:
        return f"+{pct:.2f}%"
    return f"{pct:.2f}%"


def _rsi_label(rsi: float | None) -> str:
    if rsi is None:
        return "N/A"
    if rsi >= 70:
        return f"{rsi:.1f} (Overbought)"
    if rsi <= 30:
        return f"{rsi:.1f} (Oversold)"
    return f"{rsi:.1f} (Neutral)"


def _macd_label(histogram: float | None) -> str:
    if histogram is None:
        return "N/A"
    if histogram > 0:
        return "Bullish crossover"
    if histogram < 0:
        return "Bearish crossover"
    return "Neutral"


def _fear_greed_emoji(value: int) -> str:
    """Return a text indicator for fear/greed level."""
    if value <= 25:
        return "[Extreme Fear]"
    if value <= 45:
        return "[Fear]"
    if value <= 55:
        return "[Neutral]"
    if value <= 75:
        return "[Greed]"
    return "[Extreme Greed]"


def format_crypto_report(report: CryptoReport) -> str:
    """Build the full HTML message for a crypto market daily brief."""
    now = datetime.now(timezone.utc)
    parts: list[str] = []

    # Header
    header = (
        f"<b>Crypto Market Daily Brief</b>\n"
        f"<i>{now.strftime('%A, %b %d, %Y - %H:%M UTC')}</i>\n"
        f"Data as of: {report.timestamp.strftime('%Y-%m-%d %H:%M')} | "
        f"{report.successful_coins}/{report.total_coins} coins loaded"
    )
    parts.append(header)

    # Portfolio
    if report.portfolio:
        lines = ["<b>YOUR PORTFOLIO</b>"]
        for analysis in report.portfolio:
            c = analysis.coin
            ind = analysis.indicators
            lines.append("")
            rank_str = f" #{c.rank}" if c.rank else ""
            lines.append(f"<b>{escape_html(c.symbol)}</b> - {escape_html(c.name)}{rank_str}")
            lines.append(f"{_format_price(c.price)} | 24h: {_change_arrow(c.change_24h)}")
            if c.change_7d is not None:
                lines.append(f"7d: {_change_arrow(c.change_7d)}")
            lines.append(f"MCap: {_format_large_number(c.market_cap)}")
            lines.append(f"Vol 24h: {_format_large_number(c.volume_24h)}")
            lines.append(f"RSI: {_rsi_label(ind.rsi)}")
            lines.append(f"MACD: {_macd_label(ind.macd_histogram)}")

            if ind.sma_short is not None:
                relation = "Above" if c.price > ind.sma_short else "Below"
                lines.append(f"SMA20: {_format_price(ind.sma_short)} ({relation})")

            vol_note = "SPIKE" if ind.volume_spike else "Normal"
            lines.append(f"Volume trend: {vol_note}")
            lines.append(f"Signal: <b>{analysis.signal}</b>")

        parts.append("\n".join(lines))

    # Market Overview
    if report.market_overview:
        mo = report.market_overview
        lines = ["<b>MARKET OVERVIEW</b>"]
        lines.append(f"Total Market Cap: {_format_large_number(mo.total_market_cap)}")
        if mo.market_cap_change_24h is not None:
            lines.append(f"24h Change: {_change_arrow(mo.market_cap_change_24h)}")
        lines.append(f"24h Volume: {_format_large_number(mo.total_volume_24h)}")
        lines.append(f"BTC Dominance: {mo.btc_dominance:.1f}%")
        if mo.eth_dominance is not None:
            lines.append(f"ETH Dominance: {mo.eth_dominance:.1f}%")
        parts.append("\n".join(lines))

    # Fear & Greed
    if report.fear_greed:
        fg = report.fear_greed
        lines = ["<b>FEAR &amp; GREED INDEX</b>"]
        lines.append(f"{fg.value}/100 {_fear_greed_emoji(fg.value)}")
        lines.append(f"Classification: {escape_html(fg.label)}")
        parts.append("\n".join(lines))

    # Trending
    if report.trending:
        lines = ["<b>TRENDING</b>"]
        for coin in report.trending[:10]:
            change_str = ""
            if coin.price_change_24h is not None:
                change_str = f" ({_change_arrow(coin.price_change_24h)})"
            lines.append(f"- {escape_html(coin.symbol)}: {escape_html(coin.name)}{change_str}")
        parts.append("\n".join(lines))

    # Top Coins by Market Cap
    if report.top_coins:
        lines = ["<b>TOP 10 BY MARKET CAP</b>"]
        for coin in report.top_coins[:10]:
            lines.append(
                f"{coin.rank}. <b>{escape_html(coin.symbol)}</b> "
                f"{_format_price(coin.price)} ({_change_arrow(coin.change_24h)})"
            )
        parts.append("\n".join(lines))

    # Errors
    if report.errors:
        lines = ["<b>WARNINGS</b>"]
        for err in report.errors:
            lines.append(f"- {escape_html(err)}")
        parts.append("\n".join(lines))

    return "\n\n".join(parts)
