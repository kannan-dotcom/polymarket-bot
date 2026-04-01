"""
Market Data Module — Fetches real-time and historical price data from exchanges.
Primary feed: Binance (BTC, ETH). Secondary: Yahoo Finance (stocks).
"""

import time
import requests
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from config import (
    BINANCE_BASE_URL,
    BINANCE_KLINES_ENDPOINT,
    BINANCE_TICKER_ENDPOINT,
)


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


class BinanceFeed:
    """Fetches price data from Binance REST API."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def get_current_price(self, symbol: str) -> float:
        """Get the latest price for a symbol."""
        url = f"{BINANCE_BASE_URL}{BINANCE_TICKER_ENDPOINT}"
        resp = self.session.get(url, params={"symbol": symbol}, timeout=5)
        resp.raise_for_status()
        return float(resp.json()["price"])

    def get_klines(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 100,
    ) -> list[Candle]:
        """
        Fetch historical klines (candlestick data).
        interval: 1m, 3m, 5m, 15m, 1h, 4h, 1d
        """
        url = f"{BINANCE_BASE_URL}{BINANCE_KLINES_ENDPOINT}"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        resp = self.session.get(url, params=params, timeout=10)
        resp.raise_for_status()

        candles = []
        for k in resp.json():
            candles.append(
                Candle(
                    timestamp=k[0] / 1000.0,
                    open=float(k[1]),
                    high=float(k[2]),
                    low=float(k[3]),
                    close=float(k[4]),
                    volume=float(k[5]),
                )
            )
        return candles

    def get_price_feed(self, symbol: str, lookback: int = 100) -> PriceFeed:
        """Build a complete price feed with current price + history."""
        candles = self.get_klines(symbol, interval="1m", limit=lookback)
        current = self.get_current_price(symbol)
        return PriceFeed(
            symbol=symbol,
            candles=candles,
            current_price=current,
            last_update=time.time(),
        )


class MarketDataAggregator:
    """
    Aggregates price data across exchanges and computes
    derived metrics used by the signal engine.
    """

    def __init__(self):
        self.binance = BinanceFeed()
        self._feeds: dict[str, PriceFeed] = {}

    def update(self, symbol: str) -> PriceFeed:
        """Refresh the feed for a given symbol."""
        feed = self.binance.get_price_feed(symbol)
        self._feeds[symbol] = feed
        return feed

    def get_feed(self, symbol: str) -> Optional[PriceFeed]:
        return self._feeds.get(symbol)

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
        """Annualised volatility from recent returns."""
        returns = self.compute_returns(feed)
        if len(returns) < window:
            return 0.0
        recent = returns[-window:]
        return float(np.std(recent) * np.sqrt(window))

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
            return 50.0  # neutral

        deltas = np.diff(closes)
        recent = deltas[-(period):]
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

    def compute_momentum(self, feed: PriceFeed, window: int = 12) -> float:
        """
        Price momentum as percentage change over window.
        Positive = upward momentum, negative = downward.
        """
        closes = self.closes(feed)
        if len(closes) < window:
            return 0.0
        return float((closes[-1] - closes[-window]) / closes[-window])

    def get_snapshot(self, symbol: str) -> dict:
        """
        Full snapshot of derived metrics for a symbol.
        Call update() first to refresh data.
        """
        feed = self._feeds.get(symbol)
        if feed is None:
            return {}

        closes = self.closes(feed)
        current = feed.current_price

        return {
            "symbol": symbol,
            "price": current,
            "momentum": self.compute_momentum(feed),
            "rsi": self.compute_rsi(feed),
            "volatility": self.compute_volatility(feed),
            "atr": self.compute_atr(feed),
            "vwap": self.compute_vwap(feed),
            "ema_12": self.compute_ema(feed, 12),
            "ema_26": self.compute_ema(feed, 26),
            "vwap_deviation": (current - self.compute_vwap(feed)) / self.compute_vwap(feed)
            if self.compute_vwap(feed) != 0
            else 0.0,
            "candle_count": len(closes),
            "last_update": feed.last_update,
        }
