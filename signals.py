"""
Signal Engine — Generates trading signals by comparing exchange price
analysis against Polymarket odds to find mispricings.

Core strategy:
1. Compute model probability of "UP" using momentum, RSI, VWAP, volatility
2. Compare model probability to Polymarket implied probability
3. If edge > threshold → generate signal with confidence score
4. Size the trade using Kelly Criterion (in risk_manager.py)
"""

import numpy as np
from dataclasses import dataclass
from enum import Enum
from market_data import MarketDataAggregator, PriceFeed
from config import SIGNAL


class Direction(Enum):
    UP = "UP"
    DOWN = "DOWN"
    NEUTRAL = "NEUTRAL"


@dataclass
class Signal:
    """A trading signal with direction, confidence, and edge."""
    direction: Direction
    model_prob_up: float        # our model's P(price goes up)
    market_prob_up: float       # Polymarket's implied P(up) from YES price
    edge: float                 # model_prob - market_prob (for chosen direction)
    confidence: float           # 0-1 composite confidence score
    reasons: list[str]          # human-readable signal justifications

    @property
    def is_tradeable(self) -> bool:
        return (
            self.direction != Direction.NEUTRAL
            and abs(self.edge) >= SIGNAL["edge_threshold"]
            and self.confidence >= SIGNAL["min_confidence"]
        )

    @property
    def is_strong(self) -> bool:
        return abs(self.edge) >= SIGNAL["strong_edge_threshold"]


class SignalEngine:
    """
    Produces trading signals by combining technical indicators
    from exchange data with Polymarket pricing.
    """

    def __init__(self, aggregator: MarketDataAggregator):
        self.agg = aggregator

    def generate(self, symbol: str, polymarket_yes_price: float) -> Signal:
        """
        Generate a signal for a given symbol + current Polymarket YES price.

        polymarket_yes_price: current price of YES token (0-1),
                              represents market's implied P(up).
        """
        snapshot = self.agg.get_snapshot(symbol)
        if not snapshot:
            return Signal(
                direction=Direction.NEUTRAL,
                model_prob_up=0.5,
                market_prob_up=polymarket_yes_price,
                edge=0.0,
                confidence=0.0,
                reasons=["No market data available"],
            )

        # ---- Step 1: Compute individual sub-signals ----
        scores = []
        reasons = []

        # (a) Momentum signal
        momentum = snapshot["momentum"]
        mom_score = self._momentum_signal(momentum)
        scores.append(("momentum", mom_score, 0.30))  # weight 30%
        if abs(momentum) > SIGNAL["momentum_threshold"]:
            direction_word = "bullish" if momentum > 0 else "bearish"
            reasons.append(f"Momentum {direction_word}: {momentum:.4f}")

        # (b) RSI signal
        rsi = snapshot["rsi"]
        rsi_score = self._rsi_signal(rsi)
        scores.append(("rsi", rsi_score, 0.20))  # weight 20%
        if rsi > SIGNAL["rsi_overbought"]:
            reasons.append(f"RSI overbought: {rsi:.1f}")
        elif rsi < SIGNAL["rsi_oversold"]:
            reasons.append(f"RSI oversold: {rsi:.1f}")

        # (c) VWAP deviation signal
        vwap_dev = snapshot["vwap_deviation"]
        vwap_score = self._vwap_signal(vwap_dev)
        scores.append(("vwap", vwap_score, 0.20))  # weight 20%
        if abs(vwap_dev) > SIGNAL["vwap_deviation_threshold"]:
            side = "above" if vwap_dev > 0 else "below"
            reasons.append(f"Price {side} VWAP by {vwap_dev:.4f}")

        # (d) EMA crossover signal
        ema_12 = snapshot["ema_12"]
        ema_26 = snapshot["ema_26"]
        ema_score = self._ema_signal(ema_12, ema_26, snapshot["price"])
        scores.append(("ema", ema_score, 0.15))  # weight 15%
        if ema_12 > ema_26:
            reasons.append("EMA 12 > EMA 26 (bullish)")
        else:
            reasons.append("EMA 12 < EMA 26 (bearish)")

        # (e) Volatility filter (adjusts confidence, not direction)
        vol = snapshot["volatility"]
        vol_factor = self._volatility_filter(vol)
        scores.append(("vol_adj", 0.5, 0.15))  # neutral contribution
        if vol_factor < 0.5:
            reasons.append(f"High volatility warning: {vol:.4f}")

        # ---- Step 2: Weighted composite → model probability ----
        weighted_sum = sum(score * weight for _, score, weight in scores)
        # weighted_sum is 0-1, maps to model probability of UP
        model_prob_up = np.clip(weighted_sum, 0.02, 0.98)

        # Apply volatility scaling to confidence
        raw_confidence = abs(model_prob_up - 0.5) * 2  # distance from 50/50
        confidence = raw_confidence * vol_factor

        # ---- Step 3: Compare to Polymarket odds ----
        market_prob_up = polymarket_yes_price
        market_prob_down = 1.0 - polymarket_yes_price

        # Edge for going UP: our P(up) - market's P(up)
        edge_up = model_prob_up - market_prob_up
        # Edge for going DOWN: our P(down) - market's P(down)
        edge_down = (1.0 - model_prob_up) - market_prob_down

        # Pick the direction with the larger edge
        if edge_up > edge_down and edge_up > 0:
            direction = Direction.UP
            edge = edge_up
            reasons.insert(0, f"BUY YES — edge: {edge:.1%}")
        elif edge_down > edge_up and edge_down > 0:
            direction = Direction.DOWN
            edge = edge_down
            reasons.insert(0, f"BUY NO — edge: {edge:.1%}")
        else:
            direction = Direction.NEUTRAL
            edge = 0.0
            reasons.insert(0, "No actionable edge found")

        return Signal(
            direction=direction,
            model_prob_up=float(model_prob_up),
            market_prob_up=market_prob_up,
            edge=edge,
            confidence=float(confidence),
            reasons=reasons,
        )

    # ------------------------------------------------------------------
    # Sub-signal functions — each returns a score between 0 and 1
    # 0 = strongly bearish, 0.5 = neutral, 1 = strongly bullish
    # ------------------------------------------------------------------

    def _momentum_signal(self, momentum: float) -> float:
        """Convert momentum to 0-1 score."""
        threshold = SIGNAL["momentum_threshold"]
        if abs(momentum) < threshold * 0.5:
            return 0.5  # noise, ignore
        # Scale: ±3x threshold maps to 0/1
        scaled = momentum / (threshold * 3)
        return float(np.clip(0.5 + scaled, 0.0, 1.0))

    def _rsi_signal(self, rsi: float) -> float:
        """
        RSI → probability of UP.
        Counter-trend: oversold = likely to bounce up, overbought = likely to fall.
        """
        if rsi >= SIGNAL["rsi_overbought"]:
            # Overbought → bearish (expect mean reversion)
            return max(0.0, 0.5 - (rsi - SIGNAL["rsi_overbought"]) / 60)
        elif rsi <= SIGNAL["rsi_oversold"]:
            # Oversold → bullish
            return min(1.0, 0.5 + (SIGNAL["rsi_oversold"] - rsi) / 60)
        else:
            # Neutral zone — slight directional lean
            return 0.5 + (rsi - 50) / 200

    def _vwap_signal(self, deviation: float) -> float:
        """
        Price vs VWAP. Above VWAP = bullish continuation (trend),
        but extreme deviation = mean reversion.
        """
        threshold = SIGNAL["vwap_deviation_threshold"]
        if abs(deviation) < threshold:
            return 0.5

        # Moderate deviation: trend continuation
        if abs(deviation) < threshold * 3:
            return float(np.clip(0.5 + deviation / (threshold * 6), 0.1, 0.9))

        # Extreme deviation: mean reversion
        return float(np.clip(0.5 - deviation / (threshold * 6), 0.1, 0.9))

    def _ema_signal(self, ema_short: float, ema_long: float, price: float) -> float:
        """EMA crossover signal."""
        if ema_long == 0:
            return 0.5
        diff_pct = (ema_short - ema_long) / ema_long
        return float(np.clip(0.5 + diff_pct * 50, 0.1, 0.9))

    def _volatility_filter(self, volatility: float) -> float:
        """
        Returns a confidence multiplier (0-1).
        Calibrated for 1-minute crypto candles where vol is typically 0.001-0.005.
        Very high or very low volatility → reduce confidence.
        """
        if volatility == 0:
            return 0.5

        # Calibrated for 1-min crypto candles
        if volatility > 0.02:      # extreme vol (flash crash etc)
            return 0.3
        elif volatility > 0.008:   # high vol — tradeable but risky
            return 0.7
        elif volatility > 0.003:   # elevated — good conditions
            return 1.0
        elif volatility > 0.001:   # normal — solid conditions
            return 0.9
        elif volatility > 0.0005:  # low vol — still tradeable
            return 0.7
        else:                       # dead market
            return 0.4
