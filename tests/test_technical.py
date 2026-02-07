import numpy as np
import pandas as pd
import pytest

from src.analyzers.technical import (
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
    detect_volume_spike,
    get_signal_summary,
)


@pytest.fixture
def uptrend_closes():
    """Steadily rising prices — should produce RSI > 50."""
    return pd.Series([100 + i * 0.5 for i in range(60)])


@pytest.fixture
def downtrend_closes():
    """Steadily falling prices — should produce RSI < 50."""
    return pd.Series([130 - i * 0.5 for i in range(60)])


@pytest.fixture
def flat_closes():
    """Flat prices."""
    return pd.Series([100.0] * 60)


@pytest.fixture
def normal_volumes():
    """Normal volume series with a spike at the end."""
    vols = [1_000_000] * 25
    vols.append(5_000_000)  # 5x normal — should be a spike
    return pd.Series(vols)


class TestRSI:
    def test_uptrend_rsi_above_50(self, uptrend_closes):
        rsi = calculate_rsi(uptrend_closes, period=14)
        assert rsi is not None
        assert rsi > 50

    def test_downtrend_rsi_below_50(self, downtrend_closes):
        rsi = calculate_rsi(downtrend_closes, period=14)
        assert rsi is not None
        assert rsi < 50

    def test_rsi_bounds(self, uptrend_closes):
        rsi = calculate_rsi(uptrend_closes, period=14)
        assert 0 <= rsi <= 100

    def test_insufficient_data(self):
        short = pd.Series([100, 101, 102])
        assert calculate_rsi(short, period=14) is None

    def test_all_gains_rsi_100(self):
        """If price only goes up, RSI should be 100."""
        closes = pd.Series([float(i) for i in range(1, 20)])
        rsi = calculate_rsi(closes, period=14)
        assert rsi == 100.0


class TestSMA:
    def test_sma_correct_value(self):
        closes = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
        sma = calculate_sma(closes, period=5)
        assert sma == 30.0

    def test_sma_insufficient_data(self):
        closes = pd.Series([10.0, 20.0])
        assert calculate_sma(closes, period=5) is None


class TestEMA:
    def test_ema_returns_value(self, uptrend_closes):
        ema = calculate_ema(uptrend_closes, period=20)
        assert ema is not None
        assert isinstance(ema, float)

    def test_ema_insufficient_data(self):
        closes = pd.Series([10.0, 20.0])
        assert calculate_ema(closes, period=5) is None


class TestMACD:
    def test_macd_returns_all_keys(self, uptrend_closes):
        macd = calculate_macd(uptrend_closes)
        assert "line" in macd
        assert "signal" in macd
        assert "histogram" in macd

    def test_macd_insufficient_data(self):
        short = pd.Series([100.0] * 10)
        macd = calculate_macd(short)
        assert macd["line"] is None
        assert macd["signal"] is None
        assert macd["histogram"] is None

    def test_macd_uptrend_positive(self, uptrend_closes):
        macd = calculate_macd(uptrend_closes)
        # In a steady uptrend, MACD line should be positive
        assert macd["line"] is not None
        assert macd["line"] > 0


class TestVolumeSpike:
    def test_detects_spike(self, normal_volumes):
        assert detect_volume_spike(normal_volumes, threshold=2.0) is True

    def test_no_spike(self):
        vols = pd.Series([1_000_000] * 25)
        assert detect_volume_spike(vols, threshold=2.0) is False

    def test_insufficient_data(self):
        vols = pd.Series([1_000_000] * 5)
        assert detect_volume_spike(vols) is False


class TestSignalSummary:
    def test_bullish_signal(self):
        signal = get_signal_summary(
            rsi=25,  # Oversold -> bullish
            macd_histogram=0.5,  # Positive -> bullish
            price=110,
            sma_short=100,  # Price above -> bullish
            sma_long=90,  # Short above long -> bullish
        )
        assert signal == "Bullish"

    def test_bearish_signal(self):
        signal = get_signal_summary(
            rsi=75,  # Overbought -> bearish
            macd_histogram=-0.5,  # Negative -> bearish
            price=80,
            sma_short=100,  # Price below -> bearish
            sma_long=110,  # Short below long -> bearish
        )
        assert signal == "Bearish"

    def test_neutral_signal(self):
        signal = get_signal_summary(
            rsi=50,  # Neutral
            macd_histogram=None,
            price=None,
            sma_short=None,
            sma_long=None,
        )
        assert signal == "Neutral"

    def test_mixed_signals(self):
        signal = get_signal_summary(
            rsi=25,  # Bullish
            macd_histogram=-0.5,  # Bearish
        )
        assert signal == "Neutral"
