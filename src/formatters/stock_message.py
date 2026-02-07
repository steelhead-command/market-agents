from datetime import datetime, timezone

from src.models.stock import StockReport
from src.notifiers.telegram import escape_html


def _format_number(n: float, prefix: str = "$") -> str:
    """Format a number with appropriate suffix (K, M, B)."""
    abs_n = abs(n)
    if abs_n >= 1_000_000_000:
        return f"{prefix}{n / 1_000_000_000:.1f}B"
    if abs_n >= 1_000_000:
        return f"{prefix}{n / 1_000_000:.1f}M"
    if abs_n >= 1_000:
        return f"{prefix}{n / 1_000:.1f}K"
    return f"{prefix}{n:,.2f}"


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


def format_stock_report(report: StockReport) -> str:
    """Build the full HTML message for a stock market daily brief."""
    now = datetime.now(timezone.utc)
    parts: list[str] = []

    # Header
    header = (
        f"<b>Stock Market Daily Brief</b>\n"
        f"<i>{now.strftime('%A, %b %d, %Y - %H:%M UTC')}</i>\n"
        f"Data as of: {report.timestamp.strftime('%Y-%m-%d %H:%M')} | "
        f"{report.successful_tickers}/{report.total_tickers} tickers loaded"
    )
    parts.append(header)

    # Watchlist
    if report.watchlist:
        lines = ["<b>YOUR WATCHLIST</b>"]
        for analysis in report.watchlist:
            q = analysis.quote
            ind = analysis.indicators
            lines.append("")
            lines.append(f"<b>{escape_html(q.symbol)}</b> - {escape_html(q.name)}")
            lines.append(f"${q.price:,.2f} | {_change_arrow(q.change_percent)}")
            lines.append(f"RSI: {_rsi_label(ind.rsi)}")
            lines.append(f"MACD: {_macd_label(ind.macd_histogram)}")

            sma_parts = []
            if ind.sma_short is not None:
                relation = "Above" if q.price > ind.sma_short else "Below"
                sma_parts.append(f"SMA20: ${ind.sma_short:,.2f} ({relation})")
            if ind.sma_long is not None:
                sma_parts.append(f"SMA50: ${ind.sma_long:,.2f}")
            if sma_parts:
                lines.append(" | ".join(sma_parts))

            vol_note = "SPIKE" if ind.volume_spike else "Normal"
            lines.append(f"Volume: {_format_number(q.volume, '')} ({vol_note})")
            lines.append(f"Signal: <b>{analysis.signal}</b>")

        parts.append("\n".join(lines))

    # Market Overview
    if report.market_overview:
        lines = ["<b>MARKET OVERVIEW</b>"]
        for idx in report.market_overview:
            lines.append(
                f"{escape_html(idx.name)}: ${idx.price:,.2f} ({_change_arrow(idx.change_percent)})"
            )
        parts.append("\n".join(lines))

    # Sectors
    if report.sectors:
        lines = ["<b>SECTOR PERFORMANCE</b>"]
        for i, sector in enumerate(report.sectors, 1):
            lines.append(f"{i}. {escape_html(sector.name)}: {_change_arrow(sector.change_percent)}")
        parts.append("\n".join(lines))

    # Top Movers
    if report.top_gainers or report.top_losers:
        lines = ["<b>TOP MOVERS</b>"]
        if report.top_gainers:
            gainers_str = ", ".join(
                f"{escape_html(m.symbol)} {_change_arrow(m.change_percent)}"
                for m in report.top_gainers
            )
            lines.append(f"Gainers: {gainers_str}")
        if report.top_losers:
            losers_str = ", ".join(
                f"{escape_html(m.symbol)} {_change_arrow(m.change_percent)}"
                for m in report.top_losers
            )
            lines.append(f"Losers: {losers_str}")
        parts.append("\n".join(lines))

    # Errors
    if report.errors:
        lines = ["<b>WARNINGS</b>"]
        for err in report.errors:
            lines.append(f"- {escape_html(err)}")
        parts.append("\n".join(lines))

    return "\n\n".join(parts)
