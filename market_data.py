"""
Market Data Module — Fetches daily OHLCV data from Yahoo Finance
for stocks on KLSE, SGX, and DFM exchanges.
"""

import time
import logging
import numpy as np
import yfinance as yf
from dataclasses import dataclass, field
from typing import Optional
from config import SIGNAL, YFINANCE_PERIOD, YFINANCE_INTERVAL

logger = logging.getLogger("market_data")


@dataclass
class Candle:
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class PriceFeed:
    symbol: str
    candles: list = field(default_factory=list)
    current_price: float = 0.0
    last_update: float = 0.0
    name: str = ""
    exchange: str = ""
    currency: str = ""


class YahooFinanceFeed:
    """Fetches daily price data from Yahoo Finance via yfinance."""

    def __init__(self):
        self._cache: dict[str, tuple[float, PriceFeed]] = {}
        self._cache_ttl = 300  # 5 minutes

    def get_price_feed(
        self,
        ticker: str,
        period: str = YFINANCE_PERIOD,
        interval: str = YFINANCE_INTERVAL,
    ) -> Optional[PriceFeed]:
        """
        Fetch historical OHLCV data for a ticker.
        Returns PriceFeed with candles, or None on failure.
        """
        # Check cache
        if ticker in self._cache:
            cached_time, cached_feed = self._cache[ticker]
            if time.time() - cached_time < self._cache_ttl:
                return cached_feed

        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)

            if df.empty:
                logger.warning(f"No data for {ticker}")
                return None

            # Drop rows with NaN close
            df = df.dropna(subset=["Close"])
            if df.empty:
                return None

            candles = []
            for idx, row in df.iterrows():
                candles.append(
                    Candle(
                        timestamp=idx.timestamp(),
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=float(row["Volume"]),
                    )
                )

            if not candles:
                return None

            feed = PriceFeed(
                symbol=ticker,
                candles=candles,
                current_price=candles[-1].close,
                last_update=time.time(),
            )

            # Cache it
            self._cache[ticker] = (time.time(), feed)
            return feed

        except Exception as e:
            logger.error(f"Error fetching {ticker}: {e}")
            return None

    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get the latest closing price for a ticker."""
        feed = self.get_price_feed(ticker, period="5d", interval="1d")
        if feed and feed.candles:
            return feed.current_price
        return None


class MarketDataAggregator:
    """
    Aggregates price data across exchanges and computes
    derived metrics used by the signal engine.
    """

    def __init__(self):
        self.yahoo = YahooFinanceFeed()
        self._feeds: dict[str, PriceFeed] = {}

    def update(self, ticker: str) -> Optional[PriceFeed]:
        """Refresh the feed for a given ticker."""
        feed = self.yahoo.get_price_feed(ticker)
        if feed:
            self._feeds[ticker] = feed
        return feed

    def get_feed(self, ticker: str) -> Optional[PriceFeed]:
        return self._feeds.get(ticker)

    # ------------------------------------------------------------------
    # Derived metrics
    # ------------------------------------------------------------------

    @staticmethod
    def closes(feed: PriceFeed) -> np.ndarray:
        return np.array([c.close for c in feed.candles])

    @staticmethod
    def volumes(feed: PriceFeed) -> np.ndarray:
        return np.array([c.volume for c in feed.candles])

    @staticmethod
    def highs(feed: PriceFeed) -> np.ndarray:
        return np.array([c.high for c in feed.candles])

    @staticmethod
    def lows(feed: PriceFeed) -> np.ndarray:
        return np.array([c.low for c in feed.candles])

    def compute_returns(self, feed: PriceFeed) -> np.ndarray:
        """Compute log returns from close prices."""
        closes = self.closes(feed)
        if len(closes) < 2:
            return np.array([])
        return np.diff(np.log(closes))

    def compute_volatility(self, feed: PriceFeed, window: int = 20) -> float:
        """Annualized volatility from recent daily returns."""
        returns = self.compute_returns(feed)
        if len(returns) < window:
            return 0.0
        recent = returns[-window:]
        # Annualize: daily std * sqrt(252 trading days)
        return float(np.std(recent) * np.sqrt(252))

    def compute_atr(self, feed: PriceFeed, period: int = 14) -> float:
        """Average True Range."""
        highs = self.highs(feed)
        lows = self.lows(feed)
        closes = self.closes(feed)
        if len(closes) < period + 1:
            return 0.0

        tr_values = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            tr_values.append(tr)

        return float(np.mean(tr_values[-period:]))

    def compute_rsi(self, feed: PriceFeed, period: int = 14) -> float:
        """Relative Strength Index."""
        closes = self.closes(feed)
        if len(closes) < period + 1:
            return 50.0

        deltas = np.diff(closes)
        recent = deltas[-period:]
        gains = np.where(recent > 0, recent, 0)
        losses = np.where(recent < 0, -recent, 0)

        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return float(100 - (100 / (1 + rs)))

    def compute_vwap(self, feed: PriceFeed, window: int = 20) -> float:
        """Volume Weighted Average Price."""
        closes = self.closes(feed)
        volumes = self.volumes(feed)
        if len(closes) < window:
            return float(closes[-1]) if len(closes) > 0 else 0.0

        c = closes[-window:]
        v = volumes[-window:]
        total_vol = np.sum(v)
        if total_vol == 0:
            return float(c[-1])
        return float(np.sum(c * v) / total_vol)

    def compute_ema(self, feed: PriceFeed, period: int = 12) -> float:
        """Exponential Moving Average."""
        closes = self.closes(feed)
        if len(closes) == 0:
            return 0.0
        if len(closes) < period:
            return float(np.mean(closes))

        multiplier = 2.0 / (period + 1)
        ema = float(closes[0])
        for price in closes[1:]:
            ema = (price - ema) * multiplier + ema
        return ema

    def compute_momentum(self, feed: PriceFeed, window: int = 10) -> float:
        """
        Price momentum as percentage change over window.
        Positive = upward momentum, negative = downward.
        """
        closes = self.closes(feed)
        if len(closes) < window:
            return 0.0
        return float((closes[-1] - closes[-window]) / closes[-window])

    def compute_volume_ratio(self, feed: PriceFeed, window: int = 20) -> float:
        """
        Current volume relative to average.
        > 1.0 means above average, > 2.0 = volume spike.
        """
        volumes = self.volumes(feed)
        if len(volumes) < window + 1:
            return 1.0
        avg_vol = np.mean(volumes[-window - 1:-1])
        if avg_vol == 0:
            return 1.0
        return float(volumes[-1] / avg_vol)

    def compute_sma(self, feed: PriceFeed, period: int = 50) -> float:
        """Simple Moving Average."""
        closes = self.closes(feed)
        if len(closes) < period:
            return float(np.mean(closes)) if len(closes) > 0 else 0.0
        return float(np.mean(closes[-period:]))

    def compute_obv_trend(self, feed: PriceFeed, window: int = 10) -> float:
        """
        On-Balance Volume trend (normalized).
        Positive = accumulation (buying pressure), negative = distribution.
        Returns the slope of OBV over the window, normalized by avg volume.
        """
        closes = self.closes(feed)
        volumes = self.volumes(feed)
        if len(closes) < window + 1:
            return 0.0

        # Compute OBV for the window
        obv = [0.0]
        for i in range(-window, 0):
            if closes[i] > closes[i - 1]:
                obv.append(obv[-1] + volumes[i])
            elif closes[i] < closes[i - 1]:
                obv.append(obv[-1] - volumes[i])
            else:
                obv.append(obv[-1])

        # Linear regression slope of OBV
        x = np.arange(len(obv))
        slope = float(np.polyfit(x, obv, 1)[0])

        # Normalize by average volume so it's comparable across stocks
        avg_vol = np.mean(volumes[-window:])
        if avg_vol == 0:
            return 0.0
        return slope / avg_vol

    def compute_volume_price_confirm(self, feed: PriceFeed, window: int = 5) -> float:
        """
        Volume-price confirmation score.
        Checks if recent price moves are confirmed by volume.
        +1.0 = price up on high vol (strong buy), -1.0 = price down on high vol (strong sell)
        Near 0 = divergence (price moving without volume support)
        """
        closes = self.closes(feed)
        volumes = self.volumes(feed)
        if len(closes) < window + 1:
            return 0.0

        avg_vol = np.mean(volumes[-window * 2:-window]) if len(volumes) > window * 2 else np.mean(volumes[:-window])
        if avg_vol == 0:
            return 0.0

        confirmations = []
        for i in range(-window, 0):
            price_change = (closes[i] - closes[i - 1]) / closes[i - 1]
            vol_relative = volumes[i] / avg_vol

            if price_change > 0 and vol_relative > 1.0:
                confirmations.append(min(vol_relative - 1.0, 1.0))  # bullish confirmation
            elif price_change < 0 and vol_relative > 1.0:
                confirmations.append(-min(vol_relative - 1.0, 1.0))  # bearish confirmation
            elif price_change > 0.005 and vol_relative < 0.7:
                confirmations.append(-0.3)  # price up on low vol = weak/bearish
            elif price_change < -0.005 and vol_relative < 0.7:
                confirmations.append(0.3)  # price down on low vol = weak sell
            else:
                confirmations.append(0.0)

        return float(np.mean(confirmations))

    def compute_volume_trend(self, feed: PriceFeed, window: int = 10) -> float:
        """
        Volume trend: is volume increasing or decreasing?
        Positive = rising volume, negative = declining volume.
        Normalized to roughly -1 to +1.
        """
        volumes = self.volumes(feed)
        if len(volumes) < window + 5:
            return 0.0

        recent_avg = np.mean(volumes[-window:])
        prior_avg = np.mean(volumes[-window * 2:-window]) if len(volumes) >= window * 2 else np.mean(volumes[:-window])

        if prior_avg == 0:
            return 0.0
        return float((recent_avg - prior_avg) / prior_avg)

    def compute_ichimoku(self, feed: PriceFeed) -> dict:
        """
        Ichimoku Cloud indicator.
        Returns dict with tenkan_sen, kijun_sen, senkou_a, senkou_b, chikou_span,
        and derived signals (cloud_signal, tk_cross, price_vs_cloud).
        """
        highs = self.highs(feed)
        lows = self.lows(feed)
        closes = self.closes(feed)
        n = len(closes)

        result = {
            "tenkan_sen": 0.0,
            "kijun_sen": 0.0,
            "senkou_a": 0.0,
            "senkou_b": 0.0,
            "chikou_span": 0.0,
            "cloud_signal": "neutral",   # bullish/bearish/neutral
            "tk_cross": "none",          # bullish/bearish/none
            "price_vs_cloud": "inside",  # above/below/inside
            "cloud_thickness": 0.0,      # normalized cloud thickness
        }

        if n < 52:
            return result

        # Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
        tenkan = (np.max(highs[-9:]) + np.min(lows[-9:])) / 2.0
        # Kijun-sen (Base Line): (26-period high + 26-period low) / 2
        kijun = (np.max(highs[-26:]) + np.min(lows[-26:])) / 2.0
        # Senkou Span A (Leading Span A): (Tenkan + Kijun) / 2 (plotted 26 periods ahead)
        senkou_a = (tenkan + kijun) / 2.0
        # Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2
        senkou_b = (np.max(highs[-52:]) + np.min(lows[-52:])) / 2.0
        # Chikou Span (Lagging Span): current close plotted 26 periods behind
        chikou = closes[-1]

        result["tenkan_sen"] = float(tenkan)
        result["kijun_sen"] = float(kijun)
        result["senkou_a"] = float(senkou_a)
        result["senkou_b"] = float(senkou_b)
        result["chikou_span"] = float(chikou)

        # Cloud signal: bullish when Senkou A > Senkou B
        if senkou_a > senkou_b:
            result["cloud_signal"] = "bullish"
        elif senkou_a < senkou_b:
            result["cloud_signal"] = "bearish"

        # TK cross: Tenkan crossing Kijun
        if n >= 27:
            prev_tenkan = (np.max(highs[-10:-1]) + np.min(lows[-10:-1])) / 2.0
            prev_kijun = (np.max(highs[-27:-1]) + np.min(lows[-27:-1])) / 2.0
            if tenkan > kijun and prev_tenkan <= prev_kijun:
                result["tk_cross"] = "bullish"
            elif tenkan < kijun and prev_tenkan >= prev_kijun:
                result["tk_cross"] = "bearish"

        # Price vs cloud
        cloud_top = max(senkou_a, senkou_b)
        cloud_bottom = min(senkou_a, senkou_b)
        price = closes[-1]
        if price > cloud_top:
            result["price_vs_cloud"] = "above"
        elif price < cloud_bottom:
            result["price_vs_cloud"] = "below"
        else:
            result["price_vs_cloud"] = "inside"

        # Normalized cloud thickness (relative to price)
        if price > 0:
            result["cloud_thickness"] = float(abs(senkou_a - senkou_b) / price)

        return result

    def get_snapshot(self, ticker: str) -> Optional[dict]:
        """
        Full snapshot of derived metrics for a ticker.
        Call update() first to refresh data.
        """
        feed = self._feeds.get(ticker)
        if feed is None or not feed.candles:
            return None

        closes = self.closes(feed)
        volumes = self.volumes(feed)
        current = feed.current_price
        vwap = self.compute_vwap(feed)

        # Volume stats
        daily_volume = float(volumes[-1]) if len(volumes) > 0 else 0.0
        avg_volume_20 = float(np.mean(volumes[-20:])) if len(volumes) >= 20 else float(np.mean(volumes))

        # Ichimoku Cloud
        ichimoku = self.compute_ichimoku(feed)

        return {
            "ticker": ticker,
            "price": current,
            "momentum": self.compute_momentum(feed),
            "rsi": self.compute_rsi(feed),
            "volatility": self.compute_volatility(feed),
            "atr": self.compute_atr(feed),
            "vwap": vwap,
            "ema_12": self.compute_ema(feed, 12),
            "ema_26": self.compute_ema(feed, 26),
            "sma_50": self.compute_sma(feed, 50),
            "vwap_deviation": (current - vwap) / vwap if vwap != 0 else 0.0,
            "volume_ratio": self.compute_volume_ratio(feed),
            "candle_count": len(closes),
            "last_update": feed.last_update,
            # Volume analytics
            "daily_volume": daily_volume,
            "avg_volume_20": avg_volume_20,
            "volume_trend": self.compute_volume_trend(feed),
            "obv_trend": self.compute_obv_trend(feed),
            "vol_price_confirm": self.compute_volume_price_confirm(feed),
            # Ichimoku Cloud
            "ichimoku": ichimoku,
        }
