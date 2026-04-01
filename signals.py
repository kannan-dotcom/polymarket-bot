"""
Signal Engine — Generates BUY/SELL/HOLD signals for stocks using
a composite scoring system based on technical indicators.

Core strategy:
1. Compute individual sub-scores from momentum, RSI, VWAP, EMA, volume
2. Weighted composite → score 0-100
3. Score >= 65 = BUY, score <= 35 = SELL, else HOLD
4. Confidence and edge calculated for position sizing
"""

import numpy as np
from dataclasses import dataclass
from enum import Enum
from market_data import MarketDataAggregator
from config import SIGNAL


class Direction(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Signal:
    """A trading signal with direction, score, and edge."""
    direction: Direction
    score: float               # composite score 0-100
    edge: float                # expected return magnitude
    confidence: float          # 0-1 composite confidence score
    reasons: list[str]         # human-readable signal justifications

    # Individual sub-scores for reporting
    momentum_score: float = 50.0
    rsi_score: float = 50.0
    vwap_score: float = 50.0
    ema_score: float = 50.0
    volume_score: float = 50.0

    @property
    def is_tradeable(self) -> bool:
        return (
            self.direction != Direction.HOLD
            and abs(self.edge) >= SIGNAL["edge_threshold"]
            and self.confidence >= SIGNAL["min_confidence"]
        )

    @property
    def is_strong(self) -> bool:
        return (
            self.score >= SIGNAL["strong_signal_threshold"]
            or self.score <= (100 - SIGNAL["strong_signal_threshold"])
        )


class SignalEngine:
    """
    Produces trading signals by combining technical indicators
    from daily stock data into a composite score.
    """

    def __init__(self, aggregator: MarketDataAggregator):
        self.agg = aggregator

    def generate(self, ticker: str) -> Signal:
        """
        Generate a signal for a given stock ticker.
        Returns Signal with direction, score, edge, and confidence.
        """
        snapshot = self.agg.get_snapshot(ticker)
        if not snapshot:
            return Signal(
                direction=Direction.HOLD,
                score=50.0,
                edge=0.0,
                confidence=0.0,
                reasons=["No market data available"],
            )

        scores = []
        reasons = []

        # (a) Momentum signal — weight 25%
        momentum = snapshot["momentum"]
        mom_score = self._momentum_signal(momentum)
        scores.append(("momentum", mom_score, 0.25))
        if abs(momentum) > SIGNAL["momentum_threshold"]:
            direction_word = "bullish" if momentum > 0 else "bearish"
            reasons.append(f"Momentum {direction_word}: {momentum:.2%}")

        # (b) RSI signal — weight 20%
        rsi = snapshot["rsi"]
        rsi_score = self._rsi_signal(rsi)
        scores.append(("rsi", rsi_score, 0.20))
        if rsi > SIGNAL["rsi_overbought"]:
            reasons.append(f"RSI overbought: {rsi:.1f}")
        elif rsi < SIGNAL["rsi_oversold"]:
            reasons.append(f"RSI oversold: {rsi:.1f}")

        # (c) VWAP deviation signal — weight 20%
        vwap_dev = snapshot["vwap_deviation"]
        vwap_score = self._vwap_signal(vwap_dev)
        scores.append(("vwap", vwap_score, 0.20))
        if abs(vwap_dev) > SIGNAL["vwap_deviation_threshold"]:
            side = "above" if vwap_dev > 0 else "below"
            reasons.append(f"Price {side} VWAP by {vwap_dev:.2%}")

        # (d) EMA crossover signal — weight 20%
        ema_12 = snapshot["ema_12"]
        ema_26 = snapshot["ema_26"]
        ema_score = self._ema_signal(ema_12, ema_26, snapshot["price"])
        scores.append(("ema", ema_score, 0.20))
        if ema_12 > ema_26:
            reasons.append("EMA 12 > EMA 26 (bullish)")
        else:
            reasons.append("EMA 12 < EMA 26 (bearish)")

        # (e) Volume signal — weight 15%
        volume_ratio = snapshot["volume_ratio"]
        vol_score = self._volume_signal(volume_ratio, momentum)
        scores.append(("volume", vol_score, 0.15))
        if volume_ratio > SIGNAL["volume_spike_multiplier"]:
            reasons.append(f"Volume spike: {volume_ratio:.1f}x average")

        # ---- Composite score (0-100) ----
        weighted_sum = sum(score * weight for _, score, weight in scores)
        composite_score = float(np.clip(weighted_sum, 0, 100))

        # ---- Volatility adjustment for confidence ----
        vol = snapshot["volatility"]
        vol_factor = self._volatility_filter(vol)

        # Confidence = distance from 50 (neutral) scaled by vol factor
        raw_confidence = abs(composite_score - 50) / 50  # 0-1
        confidence = raw_confidence * vol_factor

        # ---- Edge: expected return based on score strength ----
        # Map score distance from 50 to expected edge
        edge = (composite_score - 50) / 100 * vol_factor  # scaled ±0.5

        # ---- Direction ----
        if composite_score >= SIGNAL["buy_threshold"]:
            direction = Direction.BUY
            reasons.insert(0, f"BUY signal — score: {composite_score:.0f}/100")
        elif composite_score <= SIGNAL["sell_threshold"]:
            direction = Direction.SELL
            reasons.insert(0, f"SELL signal — score: {composite_score:.0f}/100")
        else:
            direction = Direction.HOLD
            reasons.insert(0, f"HOLD — score: {composite_score:.0f}/100 (neutral zone)")

        return Signal(
            direction=direction,
            score=composite_score,
            edge=abs(edge),
            confidence=float(confidence),
            reasons=reasons,
            momentum_score=mom_score,
            rsi_score=rsi_score,
            vwap_score=vwap_score,
            ema_score=ema_score,
            volume_score=vol_score,
        )

    # ------------------------------------------------------------------
    # Sub-signal functions — each returns a score between 0 and 100
    # 0 = strongly bearish, 50 = neutral, 100 = strongly bullish
    # ------------------------------------------------------------------

    def _momentum_signal(self, momentum: float) -> float:
        """Convert momentum to 0-100 score."""
        threshold = SIGNAL["momentum_threshold"]
        if abs(momentum) < threshold * 0.3:
            return 50.0  # noise, ignore

        # Scale: ±3x threshold maps to 0/100
        scaled = momentum / (threshold * 3)
        return float(np.clip(50 + scaled * 50, 0, 100))

    def _rsi_signal(self, rsi: float) -> float:
        """
        RSI → score.
        Counter-trend: oversold = bullish (bounce), overbought = bearish.
        """
        if rsi >= SIGNAL["rsi_overbought"]:
            # Overbought → bearish (expect mean reversion)
            excess = (rsi - SIGNAL["rsi_overbought"]) / 30  # 0-1 scale
            return float(np.clip(50 - excess * 40, 5, 50))
        elif rsi <= SIGNAL["rsi_oversold"]:
            # Oversold → bullish
            excess = (SIGNAL["rsi_oversold"] - rsi) / 30
            return float(np.clip(50 + excess * 40, 50, 95))
        else:
            # Neutral zone — slight directional lean
            return 50.0 + (rsi - 50) * 0.3

    def _vwap_signal(self, deviation: float) -> float:
        """
        Price vs VWAP. Moderate deviation = trend, extreme = reversion.
        """
        threshold = SIGNAL["vwap_deviation_threshold"]
        if abs(deviation) < threshold:
            return 50.0

        # Moderate deviation: trend continuation
        if abs(deviation) < threshold * 4:
            scaled = deviation / (threshold * 8) * 50
            return float(np.clip(50 + scaled, 10, 90))

        # Extreme deviation: mean reversion
        scaled = deviation / (threshold * 8) * 50
        return float(np.clip(50 - scaled, 10, 90))

    def _ema_signal(self, ema_short: float, ema_long: float, price: float) -> float:
        """EMA crossover signal."""
        if ema_long == 0:
            return 50.0
        diff_pct = (ema_short - ema_long) / ema_long
        # Also factor in price vs EMA
        price_vs_ema = (price - ema_short) / ema_short if ema_short != 0 else 0
        combined = diff_pct * 0.7 + price_vs_ema * 0.3
        return float(np.clip(50 + combined * 500, 10, 90))

    def _volume_signal(self, volume_ratio: float, momentum: float) -> float:
        """
        Volume confirms direction. High volume + momentum = strong signal.
        High volume without momentum = uncertainty.
        """
        if volume_ratio < 0.5:
            # Very low volume — weak signal
            return 50.0

        if volume_ratio > SIGNAL["volume_spike_multiplier"]:
            # Volume spike — confirm momentum direction
            if momentum > 0:
                return float(np.clip(50 + volume_ratio * 10, 50, 90))
            elif momentum < 0:
                return float(np.clip(50 - volume_ratio * 10, 10, 50))
            else:
                return 50.0  # spike without direction = uncertain

        # Normal volume — slight confirmation of trend
        if momentum > 0 and volume_ratio > 1.0:
            return 55.0
        elif momentum < 0 and volume_ratio > 1.0:
            return 45.0
        return 50.0

    def _volatility_filter(self, volatility: float) -> float:
        """
        Returns a confidence multiplier (0-1).
        Calibrated for daily stock data (annualized volatility).
        Typical stock: 15-40% annualized.
        """
        if volatility == 0:
            return 0.3

        if volatility > 0.80:       # extreme vol (>80% annualized)
            return 0.3
        elif volatility > 0.50:     # high vol — risky
            return 0.6
        elif volatility > 0.30:     # elevated — tradeable
            return 0.8
        elif volatility > 0.15:     # normal — good conditions
            return 1.0
        elif volatility > 0.08:     # low vol — still tradeable
            return 0.8
        else:                        # dead market
            return 0.4
