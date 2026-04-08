"""
Signal Engine — Generates BUY/SELL/HOLD signals for stocks using
a composite scoring system based on technical indicators.

Core strategy:
1. Compute individual sub-scores from momentum, RSI, VWAP, EMA, volume-price
2. Weighted composite → score 0-100
3. Score >= 60 = BUY, score <= 40 = SELL, else HOLD
4. Volume-price analysis: OBV trend, volume confirmation, activity level
5. Confidence and edge calculated for position sizing
"""

import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from market_data import MarketDataAggregator
from config import SIGNAL, STOCKS
from sentiment_config import (
    SENTIMENT_PARAMS,
    WEIGHTS_WITH_SENTIMENT,
    WEIGHTS_WITHOUT_SENTIMENT,
)


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
    vol_price_score: float = 50.0  # volume-price analysis sub-score
    sentiment_score: float = 50.0  # forum sentiment sub-score

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

    def __init__(self, aggregator: MarketDataAggregator, sentiment_aggregator=None):
        self.agg = aggregator
        self.sentiment = sentiment_aggregator  # None if sentiment disabled
        # Build reverse ticker map for sentiment lookup
        self._ticker_map = {cfg["ticker"]: key for key, cfg in STOCKS.items()}

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

        # Check if sentiment data available for this stock
        sent_score = 50.0
        has_sentiment = False
        stock_key = self._ticker_map.get(ticker)
        if self.sentiment and stock_key:
            sent_data = self.sentiment.get_sentiment(stock_key)
            if sent_data and sent_data.mention_count >= SENTIMENT_PARAMS["min_mentions"]:
                sent_score = sent_data.sentiment_score
                has_sentiment = True

        # Select weight set based on sentiment availability
        weights = WEIGHTS_WITH_SENTIMENT if has_sentiment else WEIGHTS_WITHOUT_SENTIMENT

        # (a) Momentum signal
        momentum = snapshot["momentum"]
        mom_score = self._momentum_signal(momentum)
        scores.append(("momentum", mom_score, weights["momentum"]))
        if abs(momentum) > SIGNAL["momentum_threshold"]:
            direction_word = "bullish" if momentum > 0 else "bearish"
            reasons.append(f"Momentum {direction_word}: {momentum:.2%}")

        # (b) RSI signal
        rsi = snapshot["rsi"]
        rsi_score = self._rsi_signal(rsi)
        scores.append(("rsi", rsi_score, weights["rsi"]))
        if rsi > SIGNAL["rsi_overbought"]:
            reasons.append(f"RSI overbought: {rsi:.1f}")
        elif rsi < SIGNAL["rsi_oversold"]:
            reasons.append(f"RSI oversold: {rsi:.1f}")

        # (c) VWAP deviation signal
        vwap_dev = snapshot["vwap_deviation"]
        vwap_score = self._vwap_signal(vwap_dev)
        scores.append(("vwap", vwap_score, weights["vwap"]))
        if abs(vwap_dev) > SIGNAL["vwap_deviation_threshold"]:
            side = "above" if vwap_dev > 0 else "below"
            reasons.append(f"Price {side} VWAP by {vwap_dev:.2%}")

        # (d) EMA crossover signal
        ema_12 = snapshot["ema_12"]
        ema_26 = snapshot["ema_26"]
        ema_score = self._ema_signal(ema_12, ema_26, snapshot["price"])
        scores.append(("ema", ema_score, weights["ema"]))
        if ema_12 > ema_26:
            reasons.append("EMA 12 > EMA 26 (bullish)")
        else:
            reasons.append("EMA 12 < EMA 26 (bearish)")

        # (e) Volume activity signal
        volume_ratio = snapshot["volume_ratio"]
        vol_score = self._volume_signal(volume_ratio, momentum)
        scores.append(("volume", vol_score, weights["volume"]))
        if volume_ratio > SIGNAL["volume_spike_multiplier"]:
            reasons.append(f"Volume spike: {volume_ratio:.1f}x average")

        # (f) Volume-price analysis
        obv_trend = snapshot.get("obv_trend", 0.0)
        vol_price_confirm = snapshot.get("vol_price_confirm", 0.0)
        volume_trend = snapshot.get("volume_trend", 0.0)
        vp_score = self._volume_price_signal(
            obv_trend, vol_price_confirm, volume_trend, volume_ratio, momentum
        )
        scores.append(("vol_price", vp_score, weights["vol_price"]))

        # Generate reasons for volume-price
        if obv_trend > 0.3:
            reasons.append(f"OBV accumulation: {obv_trend:.2f}")
        elif obv_trend < -0.3:
            reasons.append(f"OBV distribution: {obv_trend:.2f}")
        if vol_price_confirm > 0.2:
            reasons.append("Volume confirms price up")
        elif vol_price_confirm < -0.2:
            reasons.append("Volume confirms price down")
        elif momentum > 0.01 and vol_price_confirm < 0:
            reasons.append("Warning: price up but volume diverging")
        elif momentum < -0.01 and vol_price_confirm > 0:
            reasons.append("Warning: price down but volume diverging")
        if volume_trend > 0.3:
            reasons.append(f"Rising volume trend: +{volume_trend:.0%}")
        elif volume_trend < -0.3:
            reasons.append(f"Declining volume: {volume_trend:.0%}")

        # (g) Sentiment signal (only when data available)
        if has_sentiment:
            scores.append(("sentiment", sent_score, weights["sentiment"]))
            if sent_score > 65:
                reasons.append(f"Forum bullish ({sent_data.mention_count} mentions)")
            elif sent_score < 35:
                reasons.append(f"Forum bearish ({sent_data.mention_count} mentions)")
            if sent_data.buzz_score > 70:
                reasons.append(f"High forum buzz: {sent_data.mention_count} mentions")

        # ---- Composite score (0-100) ----
        weighted_sum = sum(score * weight for _, score, weight in scores)
        composite_score = float(np.clip(weighted_sum, 0, 100))

        # ---- Volatility adjustment for confidence ----
        vol = snapshot["volatility"]
        vol_factor = self._volatility_filter(vol)

        # ---- Confidence-weighted composite (Article 2 concept) ----
        # Each sub-score's confidence contributes to overall signal confidence
        # Signals far from neutral (50) with confirming volume = high confidence
        score_deviations = [abs(s - 50) / 50 for _, s, _ in scores]
        avg_deviation = np.mean(score_deviations) if score_deviations else 0
        signal_agreement = 1.0 - np.std(score_deviations) if len(score_deviations) > 1 else 0.5
        raw_confidence = avg_deviation * signal_agreement * vol_factor
        confidence = float(np.clip(raw_confidence, 0, 1))

        # ---- Edge: probability-based (Article 1 adapted) ----
        # estimated_prob = our signal's win probability
        # edge = estimated_prob - market_implied (0.50)
        score_dist = abs(composite_score - 50) / 50
        estimated_prob = 0.50 + score_dist * 0.20  # 50-70%

        # Confirmation bonus from volume signals
        obv_trend = snapshot.get("obv_trend", 0.0)
        vol_price_confirm = snapshot.get("vol_price_confirm", 0.0)
        if (composite_score > 50 and obv_trend > 0.2) or (composite_score < 50 and obv_trend < -0.2):
            estimated_prob += min(abs(obv_trend) * 0.05, 0.05)
        if (composite_score > 50 and vol_price_confirm > 0.2) or \
           (composite_score < 50 and vol_price_confirm < -0.2):
            estimated_prob += min(abs(vol_price_confirm) * 0.05, 0.05)
        estimated_prob = min(estimated_prob, 0.80)

        edge = (estimated_prob - 0.50) * vol_factor

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
            vol_price_score=vp_score,
            sentiment_score=sent_score,
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

    def _volume_price_signal(
        self,
        obv_trend: float,
        vol_price_confirm: float,
        volume_trend: float,
        volume_ratio: float,
        momentum: float,
    ) -> float:
        """
        Volume-price analysis score (0-100).
        Combines OBV trend, volume-price confirmation, and volume activity.

        Key logic:
        - Accumulation (rising OBV + rising price) = bullish
        - Distribution (falling OBV + falling price) = bearish
        - Divergence (price up + OBV down or vice versa) = warning/reversal
        - Rising volume + directional move = conviction
        - Low/declining volume = weak move, fade toward 50
        """
        components = []

        # (1) OBV trend — strongest volume-price indicator
        # obv_trend > 0 = accumulation, < 0 = distribution
        obv_score = float(np.clip(50 + obv_trend * 40, 10, 90))
        components.append((obv_score, 0.40))

        # (2) Volume-price confirmation
        # +1 = strong buy confirmation, -1 = strong sell confirmation
        confirm_score = float(np.clip(50 + vol_price_confirm * 40, 10, 90))
        components.append((confirm_score, 0.35))

        # (3) Volume trend + activity
        # Rising volume = conviction (amplify direction), declining = fade
        activity_score = 50.0
        if volume_trend > 0.2 and momentum > 0:
            activity_score = float(np.clip(50 + volume_trend * 30, 50, 85))
        elif volume_trend > 0.2 and momentum < 0:
            activity_score = float(np.clip(50 - volume_trend * 30, 15, 50))
        elif volume_trend < -0.2:
            # Declining volume = weak conviction, pull toward neutral
            activity_score = 50.0 + (momentum * 200)  # slight directional lean
            activity_score = float(np.clip(activity_score, 40, 60))

        # Volume ratio bonus: high current volume amplifies signal
        if volume_ratio > 1.5:
            boost = min((volume_ratio - 1.0) * 5, 10)
            if momentum > 0:
                activity_score = min(activity_score + boost, 90)
            elif momentum < 0:
                activity_score = max(activity_score - boost, 10)

        components.append((activity_score, 0.25))

        # Weighted composite
        return float(np.clip(
            sum(s * w for s, w in components),
            0, 100,
        ))

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
