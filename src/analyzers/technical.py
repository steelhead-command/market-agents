import pandas as pd

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def calculate_rsi(closes: pd.Series, period: int = 14) -> float | None:
    """Calculate Relative Strength Index.

    RSI = 100 - (100 / (1 + RS))
    RS = average gain / average loss over `period` days
    """
    if len(closes) < period + 1:
        return None

    deltas = closes.diff().dropna()
    gains = deltas.where(deltas > 0, 0.0)
    losses = (-deltas).where(deltas < 0, 0.0)

    # Use exponential moving average (Wilder's smoothing)
    avg_gain = gains.ewm(alpha=1 / period, min_periods=period).mean().iloc[-1]
    avg_loss = losses.ewm(alpha=1 / period, min_periods=period).mean().iloc[-1]

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(rsi, 1)


def calculate_ema(closes: pd.Series, period: int) -> float | None:
    """Calculate Exponential Moving Average."""
    if len(closes) < period:
        return None
    ema = closes.ewm(span=period, min_periods=period).mean().iloc[-1]
    return round(ema, 4)


def calculate_sma(closes: pd.Series, period: int) -> float | None:
    """Calculate Simple Moving Average."""
    if len(closes) < period:
        return None
    sma = closes.rolling(window=period).mean().iloc[-1]
    return round(sma, 4)


def calculate_macd(
    closes: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, float | None]:
    """Calculate MACD (Moving Average Convergence Divergence).

    Returns dict with keys: line, signal, histogram
    """
    if len(closes) < slow + signal:
        return {"line": None, "signal": None, "histogram": None}

    ema_fast = closes.ewm(span=fast, min_periods=fast).mean()
    ema_slow = closes.ewm(span=slow, min_periods=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, min_periods=signal).mean()
    histogram = macd_line - signal_line

    return {
        "line": round(macd_line.iloc[-1], 4),
        "signal": round(signal_line.iloc[-1], 4),
        "histogram": round(histogram.iloc[-1], 4),
    }


def detect_volume_spike(volumes: pd.Series, threshold: float = 2.0) -> bool:
    """Detect if the latest volume is a spike above the rolling average.

    A spike means the latest volume exceeds `threshold` times the 20-day average.
    """
    if len(volumes) < 21:
        return False

    avg_volume = volumes.iloc[:-1].rolling(window=20).mean().iloc[-1]
    if avg_volume == 0 or pd.isna(avg_volume):
        return False

    return bool(volumes.iloc[-1] > (avg_volume * threshold))


def get_signal_summary(
    rsi: float | None,
    macd_histogram: float | None,
    price: float | None = None,
    sma_short: float | None = None,
    sma_long: float | None = None,
) -> str:
    """Generate a simple signal summary from indicators.

    Uses a point-based system:
    - RSI < 30 (oversold) = +1 bullish, RSI > 70 (overbought) = +1 bearish
    - MACD histogram > 0 = +1 bullish, < 0 = +1 bearish
    - Price above SMA short = +1 bullish, below = +1 bearish
    - SMA short > SMA long (golden cross direction) = +1 bullish, opposite = +1 bearish
    """
    bullish = 0
    bearish = 0

    if rsi is not None:
        if rsi < 30:
            bullish += 1
        elif rsi > 70:
            bearish += 1

    if macd_histogram is not None:
        if macd_histogram > 0:
            bullish += 1
        elif macd_histogram < 0:
            bearish += 1

    if price is not None and sma_short is not None:
        if price > sma_short:
            bullish += 1
        else:
            bearish += 1

    if sma_short is not None and sma_long is not None:
        if sma_short > sma_long:
            bullish += 1
        else:
            bearish += 1

    if bullish > bearish:
        return "Bullish"
    elif bearish > bullish:
        return "Bearish"
    return "Neutral"
