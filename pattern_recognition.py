"""
Chart Pattern Recognition Engine
Detects candlestick patterns and chart formations from OHLCV data.
Returns pattern signals used by the signal engine.
"""

import numpy as np
import logging
from dataclasses import dataclass, field
from typing import Optional
from market_data import MarketDataAggregator, PriceFeed

logger = logging.getLogger("patterns")


@dataclass
class PatternResult:
    """Result of pattern analysis for a single stock."""
    patterns_detected: list[dict] = field(default_factory=list)
    pattern_score: float = 50.0      # 0-100 composite (50 = neutral)
    bullish_count: int = 0
    bearish_count: int = 0
    strongest_pattern: str = ""
    strongest_bias: str = "neutral"   # bullish/bearish/neutral
    confidence: float = 0.0          # 0-1

    def to_dict(self) -> dict:
        return {
            "patterns": self.patterns_detected,
            "pattern_score": round(self.pattern_score, 1),
            "bullish_count": self.bullish_count,
            "bearish_count": self.bearish_count,
            "strongest_pattern": self.strongest_pattern,
            "strongest_bias": self.strongest_bias,
            "confidence": round(self.confidence, 3),
        }


class PatternRecognitionEngine:
    """
    Detects candlestick patterns and simple chart formations.
    Each pattern returns a bias (bullish/bearish) and strength (0-1).
    """

    def __init__(self, aggregator: MarketDataAggregator):
        self.agg = aggregator

    def analyze(self, ticker: str) -> Optional[PatternResult]:
        """Run full pattern analysis on a ticker."""
        feed = self.agg.get_feed(ticker)
        if not feed or len(feed.candles) < 20:
            return None

        closes = self.agg.closes(feed)
        highs = self.agg.highs(feed)
        lows = self.agg.lows(feed)
        opens = np.array([c.open for c in feed.candles])
        volumes = self.agg.volumes(feed)

        patterns = []

        # Candlestick patterns (last 3 candles)
        patterns += self._detect_candlestick_patterns(opens, highs, lows, closes, volumes)

        # Chart formations (need more history)
        if len(closes) >= 30:
            patterns += self._detect_double_top_bottom(highs, lows, closes)
            patterns += self._detect_support_resistance_break(highs, lows, closes, volumes)

        if len(closes) >= 20:
            patterns += self._detect_triangle(highs, lows, closes)
            patterns += self._detect_trend_channel(highs, lows, closes)

        if not patterns:
            return PatternResult()

        # Aggregate
        bullish = [p for p in patterns if p["bias"] == "bullish"]
        bearish = [p for p in patterns if p["bias"] == "bearish"]

        bull_strength = sum(p["strength"] for p in bullish)
        bear_strength = sum(p["strength"] for p in bearish)
        total = bull_strength + bear_strength

        if total > 0:
            net = (bull_strength - bear_strength) / total
            score = 50.0 + net * 40  # maps -1..+1 to 10..90
        else:
            score = 50.0

        score = float(np.clip(score, 5, 95))

        # Strongest pattern
        all_sorted = sorted(patterns, key=lambda p: p["strength"], reverse=True)
        strongest = all_sorted[0] if all_sorted else {"name": "", "bias": "neutral"}

        confidence = min(total / 3.0, 1.0)  # normalize: 3+ total strength = full confidence

        return PatternResult(
            patterns_detected=patterns,
            pattern_score=score,
            bullish_count=len(bullish),
            bearish_count=len(bearish),
            strongest_pattern=strongest["name"],
            strongest_bias=strongest["bias"],
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # Candlestick patterns
    # ------------------------------------------------------------------

    def _detect_candlestick_patterns(
        self, opens, highs, lows, closes, volumes
    ) -> list[dict]:
        patterns = []
        n = len(closes)
        if n < 3:
            return patterns

        # Use last 3 candles
        o, h, l, c = opens[-3:], highs[-3:], lows[-3:], closes[-3:]
        v = volumes[-3:]
        body = c - o
        body_size = np.abs(body)
        candle_range = h - l

        # Avoid division by zero
        safe_range = np.where(candle_range > 0, candle_range, 1e-10)

        # Body ratio (body / range)
        body_ratio = body_size / safe_range

        avg_body = np.mean(np.abs(closes[:-1] - opens[:-1])[-10:]) if n > 10 else np.mean(body_size)
        if avg_body == 0:
            avg_body = 1e-10

        # ---- Hammer / Inverted Hammer (bullish reversal) ----
        # Hammer: small body at top, long lower shadow, at end of downtrend
        lower_shadow = np.minimum(o[-1], c[-1]) - l[-1]
        upper_shadow = h[-1] - np.maximum(o[-1], c[-1])
        if (lower_shadow > 2 * body_size[-1]
                and upper_shadow < body_size[-1] * 0.5
                and closes[-4:-1].mean() > closes[-1] if n > 3 else False):
            patterns.append({
                "name": "Hammer",
                "bias": "bullish",
                "strength": 0.6,
                "description": "Bullish reversal after downtrend",
            })

        # Inverted Hammer
        if (upper_shadow > 2 * body_size[-1]
                and lower_shadow < body_size[-1] * 0.5
                and closes[-4:-1].mean() > closes[-1] if n > 3 else False):
            patterns.append({
                "name": "Inverted Hammer",
                "bias": "bullish",
                "strength": 0.5,
                "description": "Potential bullish reversal",
            })

        # ---- Shooting Star (bearish reversal) ----
        if (upper_shadow > 2 * body_size[-1]
                and lower_shadow < body_size[-1] * 0.5
                and closes[-4:-1].mean() < closes[-1] if n > 3 else False):
            patterns.append({
                "name": "Shooting Star",
                "bias": "bearish",
                "strength": 0.6,
                "description": "Bearish reversal after uptrend",
            })

        # ---- Hanging Man (bearish) ----
        if (lower_shadow > 2 * body_size[-1]
                and upper_shadow < body_size[-1] * 0.5
                and closes[-4:-1].mean() < closes[-1] if n > 3 else False):
            patterns.append({
                "name": "Hanging Man",
                "bias": "bearish",
                "strength": 0.5,
                "description": "Bearish reversal after uptrend",
            })

        # ---- Doji (indecision) ----
        if body_ratio[-1] < 0.1 and candle_range[-1] > 0:
            # Doji at extreme: reversal signal
            if n > 5:
                recent_trend = closes[-1] - closes[-6]
                if recent_trend > 0:
                    patterns.append({
                        "name": "Doji",
                        "bias": "bearish",
                        "strength": 0.3,
                        "description": "Indecision after uptrend",
                    })
                elif recent_trend < 0:
                    patterns.append({
                        "name": "Doji",
                        "bias": "bullish",
                        "strength": 0.3,
                        "description": "Indecision after downtrend",
                    })

        # ---- Engulfing (2-candle pattern) ----
        if n >= 2:
            # Bullish engulfing: red candle followed by larger green candle
            if (body[-2] < 0 and body[-1] > 0
                    and o[-1] <= c[-2] and c[-1] >= o[-2]):
                strength = min(body_size[-1] / avg_body * 0.4, 0.8)
                patterns.append({
                    "name": "Bullish Engulfing",
                    "bias": "bullish",
                    "strength": max(strength, 0.5),
                    "description": "Strong bullish reversal candle",
                })

            # Bearish engulfing
            if (body[-2] > 0 and body[-1] < 0
                    and o[-1] >= c[-2] and c[-1] <= o[-2]):
                strength = min(body_size[-1] / avg_body * 0.4, 0.8)
                patterns.append({
                    "name": "Bearish Engulfing",
                    "bias": "bearish",
                    "strength": max(strength, 0.5),
                    "description": "Strong bearish reversal candle",
                })

        # ---- Morning Star / Evening Star (3-candle) ----
        if n >= 3:
            # Morning Star: big red, small body, big green
            if (body[-3] < 0 and body_size[-3] > avg_body
                    and body_size[-2] < avg_body * 0.3
                    and body[-1] > 0 and body_size[-1] > avg_body):
                patterns.append({
                    "name": "Morning Star",
                    "bias": "bullish",
                    "strength": 0.7,
                    "description": "3-candle bullish reversal",
                })

            # Evening Star: big green, small body, big red
            if (body[-3] > 0 and body_size[-3] > avg_body
                    and body_size[-2] < avg_body * 0.3
                    and body[-1] < 0 and body_size[-1] > avg_body):
                patterns.append({
                    "name": "Evening Star",
                    "bias": "bearish",
                    "strength": 0.7,
                    "description": "3-candle bearish reversal",
                })

        # ---- Three White Soldiers / Three Black Crows ----
        if n >= 3:
            if all(body[-3:] > 0) and all(body_size[-3:] > avg_body * 0.5):
                patterns.append({
                    "name": "Three White Soldiers",
                    "bias": "bullish",
                    "strength": 0.8,
                    "description": "Three consecutive bullish candles",
                })

            if all(body[-3:] < 0) and all(body_size[-3:] > avg_body * 0.5):
                patterns.append({
                    "name": "Three Black Crows",
                    "bias": "bearish",
                    "strength": 0.8,
                    "description": "Three consecutive bearish candles",
                })

        # ---- Marubozu (strong conviction candle) ----
        if body_ratio[-1] > 0.85 and body_size[-1] > avg_body * 1.5:
            bias = "bullish" if body[-1] > 0 else "bearish"
            patterns.append({
                "name": "Marubozu",
                "bias": bias,
                "strength": 0.6,
                "description": f"Strong {'bullish' if bias == 'bullish' else 'bearish'} conviction",
            })

        return patterns

    # ------------------------------------------------------------------
    # Chart formations
    # ------------------------------------------------------------------

    def _detect_double_top_bottom(
        self, highs, lows, closes
    ) -> list[dict]:
        """Detect double top / double bottom patterns."""
        patterns = []
        n = len(closes)
        if n < 30:
            return patterns

        window = min(30, n)
        h = highs[-window:]
        l = lows[-window:]
        c = closes[-window:]

        # Find local maxima and minima
        maxima = []
        minima = []
        for i in range(2, window - 2):
            if h[i] >= h[i - 1] and h[i] >= h[i - 2] and h[i] >= h[i + 1] and h[i] >= h[i + 2]:
                maxima.append((i, h[i]))
            if l[i] <= l[i - 1] and l[i] <= l[i - 2] and l[i] <= l[i + 1] and l[i] <= l[i + 2]:
                minima.append((i, l[i]))

        # Double top: two peaks at similar levels, with price now below neckline
        for i in range(len(maxima) - 1):
            for j in range(i + 1, len(maxima)):
                idx1, peak1 = maxima[i]
                idx2, peak2 = maxima[j]
                if abs(idx2 - idx1) < 5:
                    continue
                tolerance = 0.02 * peak1  # 2% tolerance
                if abs(peak1 - peak2) < tolerance:
                    neckline = min(l[idx1:idx2+1])
                    if c[-1] < neckline:
                        patterns.append({
                            "name": "Double Top",
                            "bias": "bearish",
                            "strength": 0.7,
                            "description": f"Double top near {peak1:.2f}, broke neckline",
                        })
                        break
            else:
                continue
            break

        # Double bottom: two troughs at similar levels, price now above neckline
        for i in range(len(minima) - 1):
            for j in range(i + 1, len(minima)):
                idx1, trough1 = minima[i]
                idx2, trough2 = minima[j]
                if abs(idx2 - idx1) < 5:
                    continue
                tolerance = 0.02 * trough1
                if abs(trough1 - trough2) < tolerance:
                    neckline = max(h[idx1:idx2+1])
                    if c[-1] > neckline:
                        patterns.append({
                            "name": "Double Bottom",
                            "bias": "bullish",
                            "strength": 0.7,
                            "description": f"Double bottom near {trough1:.2f}, broke neckline",
                        })
                        break
            else:
                continue
            break

        return patterns

    def _detect_support_resistance_break(
        self, highs, lows, closes, volumes
    ) -> list[dict]:
        """Detect support/resistance breakouts with volume confirmation."""
        patterns = []
        n = len(closes)
        if n < 20:
            return patterns

        window = min(30, n)
        h = highs[-window:]
        l = lows[-window:]
        c = closes[-window:]
        v = volumes[-window:]

        # Resistance: recent high that was tested multiple times
        recent_high = np.max(h[:-3])
        # Support: recent low
        recent_low = np.min(l[:-3])

        avg_vol = np.mean(v[:-3]) if len(v) > 3 else np.mean(v)
        current_vol = v[-1]

        # Breakout above resistance with volume
        if c[-1] > recent_high and current_vol > avg_vol * 1.3:
            patterns.append({
                "name": "Resistance Breakout",
                "bias": "bullish",
                "strength": 0.7,
                "description": f"Broke above {recent_high:.2f} on volume",
            })

        # Breakdown below support with volume
        if c[-1] < recent_low and current_vol > avg_vol * 1.3:
            patterns.append({
                "name": "Support Breakdown",
                "bias": "bearish",
                "strength": 0.7,
                "description": f"Broke below {recent_low:.2f} on volume",
            })

        return patterns

    def _detect_triangle(self, highs, lows, closes) -> list[dict]:
        """Detect converging triangle patterns (ascending, descending, symmetric)."""
        patterns = []
        n = len(closes)
        if n < 20:
            return patterns

        window = 20
        h = highs[-window:]
        l = lows[-window:]

        # Fit linear regression to highs and lows
        x = np.arange(window)
        high_slope = np.polyfit(x, h, 1)[0]
        low_slope = np.polyfit(x, l, 1)[0]

        # Normalize slopes by price
        avg_price = np.mean(closes[-window:])
        if avg_price == 0:
            return patterns
        norm_high_slope = high_slope / avg_price
        norm_low_slope = low_slope / avg_price

        # Converging: highs falling and lows rising
        if norm_high_slope < -0.001 and norm_low_slope > 0.001:
            # Symmetric triangle — breakout direction uncertain
            if closes[-1] > h[-2]:
                patterns.append({
                    "name": "Triangle Breakout Up",
                    "bias": "bullish",
                    "strength": 0.6,
                    "description": "Symmetric triangle breakout to upside",
                })
            elif closes[-1] < l[-2]:
                patterns.append({
                    "name": "Triangle Breakdown",
                    "bias": "bearish",
                    "strength": 0.6,
                    "description": "Symmetric triangle breakdown",
                })

        # Ascending triangle: flat highs, rising lows
        if abs(norm_high_slope) < 0.001 and norm_low_slope > 0.001:
            if closes[-1] > np.max(h[-5:-1]):
                patterns.append({
                    "name": "Ascending Triangle Breakout",
                    "bias": "bullish",
                    "strength": 0.7,
                    "description": "Ascending triangle breakout",
                })

        # Descending triangle: flat lows, falling highs
        if norm_high_slope < -0.001 and abs(norm_low_slope) < 0.001:
            if closes[-1] < np.min(l[-5:-1]):
                patterns.append({
                    "name": "Descending Triangle Breakdown",
                    "bias": "bearish",
                    "strength": 0.7,
                    "description": "Descending triangle breakdown",
                })

        return patterns

    def _detect_trend_channel(self, highs, lows, closes) -> list[dict]:
        """Detect trend channel and price position within it."""
        patterns = []
        n = len(closes)
        if n < 20:
            return patterns

        window = 20
        x = np.arange(window)
        c = closes[-window:]

        # Linear regression on closes
        slope, intercept = np.polyfit(x, c, 1)
        trend_line = slope * x + intercept
        deviations = c - trend_line
        std_dev = np.std(deviations)

        if std_dev == 0:
            return patterns

        # Current position relative to channel
        current_dev = deviations[-1] / std_dev

        avg_price = np.mean(c)
        if avg_price == 0:
            return patterns
        norm_slope = slope / avg_price

        # Strong uptrend + price at bottom of channel = buy opportunity
        if norm_slope > 0.002 and current_dev < -1.0:
            patterns.append({
                "name": "Channel Bottom Bounce",
                "bias": "bullish",
                "strength": 0.5,
                "description": "Price at bottom of uptrend channel",
            })

        # Strong uptrend + price at top of channel = possible reversal
        if norm_slope > 0.002 and current_dev > 1.5:
            patterns.append({
                "name": "Channel Top Overbought",
                "bias": "bearish",
                "strength": 0.4,
                "description": "Price at top of uptrend channel",
            })

        # Downtrend + price at top of channel = sell opportunity
        if norm_slope < -0.002 and current_dev > 1.0:
            patterns.append({
                "name": "Channel Top Rejection",
                "bias": "bearish",
                "strength": 0.5,
                "description": "Price at top of downtrend channel",
            })

        # Downtrend + price at bottom breaking down
        if norm_slope < -0.002 and current_dev < -1.5:
            patterns.append({
                "name": "Channel Bottom Breakdown",
                "bias": "bearish",
                "strength": 0.4,
                "description": "Breaking below downtrend channel",
            })

        return patterns
