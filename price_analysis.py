"""
Price Analysis Module — Computes buy/sell/hold price targets,
volume-based price prediction, and average price movement analysis.

Implements concepts from:
1. Probability-based edge calculation (Polymarket arbitrage formula adapted for stocks)
2. Multi-signal composite scoring (combining weak signals into conviction)
3. ATR-based price targets with volume confirmation
4. Historical volatility bands for expected price ranges
"""

import numpy as np
import logging
from dataclasses import dataclass
from typing import Optional
from market_data import MarketDataAggregator, PriceFeed

logger = logging.getLogger("price_analysis")


@dataclass
class PriceTargets:
    """Buy/Sell/Hold price targets for a stock."""
    ticker: str
    current_price: float

    # Buy targets (entry points)
    buy_target: float           # ideal buy price (support + volume profile)
    buy_strong: float           # strong buy (deep support)

    # Sell targets (exit points)
    sell_target: float          # ideal sell price (resistance + momentum)
    sell_strong: float          # strong sell / take-profit

    # Hold zone
    hold_low: float             # lower bound of hold zone
    hold_high: float            # upper bound of hold zone

    # Price prediction (based on volume and momentum)
    predicted_direction: str    # "UP", "DOWN", "NEUTRAL"
    predicted_move_pct: float   # expected % move in next period
    predicted_price: float      # predicted price (current + expected move)
    prediction_confidence: float  # 0-1 confidence in prediction

    # Volatility bands
    upper_band: float           # 1-sigma upper bound
    lower_band: float           # 1-sigma lower bound
    upper_2sigma: float         # 2-sigma upper
    lower_2sigma: float         # 2-sigma lower

    # Volume analysis
    volume_profile_poc: float   # Point of Control (highest volume price)
    volume_profile_vah: float   # Value Area High
    volume_profile_val: float   # Value Area Low
    avg_daily_range: float      # average daily price range (high-low)
    avg_daily_range_pct: float  # as percentage

    # Support/Resistance levels
    support_1: float
    support_2: float
    resistance_1: float
    resistance_2: float

    # Edge calculation (from Article 1 - adapted probability edge)
    estimated_win_prob: float   # estimated probability signal is correct
    market_implied_prob: float  # what the current price movement implies
    edge: float                 # win_prob - market_implied
    kelly_optimal_pct: float    # Kelly-optimal allocation percentage

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "current_price": round(self.current_price, 4),
            "buy_target": round(self.buy_target, 4),
            "buy_strong": round(self.buy_strong, 4),
            "sell_target": round(self.sell_target, 4),
            "sell_strong": round(self.sell_strong, 4),
            "hold_low": round(self.hold_low, 4),
            "hold_high": round(self.hold_high, 4),
            "predicted_direction": self.predicted_direction,
            "predicted_move_pct": round(self.predicted_move_pct, 4),
            "predicted_price": round(self.predicted_price, 4),
            "prediction_confidence": round(self.prediction_confidence, 4),
            "upper_band": round(self.upper_band, 4),
            "lower_band": round(self.lower_band, 4),
            "upper_2sigma": round(self.upper_2sigma, 4),
            "lower_2sigma": round(self.lower_2sigma, 4),
            "volume_profile_poc": round(self.volume_profile_poc, 4),
            "volume_profile_vah": round(self.volume_profile_vah, 4),
            "volume_profile_val": round(self.volume_profile_val, 4),
            "avg_daily_range": round(self.avg_daily_range, 4),
            "avg_daily_range_pct": round(self.avg_daily_range_pct, 4),
            "support_1": round(self.support_1, 4),
            "support_2": round(self.support_2, 4),
            "resistance_1": round(self.resistance_1, 4),
            "resistance_2": round(self.resistance_2, 4),
            "estimated_win_prob": round(self.estimated_win_prob, 4),
            "market_implied_prob": round(self.market_implied_prob, 4),
            "edge": round(self.edge, 4),
            "kelly_optimal_pct": round(self.kelly_optimal_pct, 4),
        }


class PriceAnalyzer:
    """
    Comprehensive price analysis engine.
    Computes buy/sell/hold targets, volume profiles, and price predictions.
    """

    def __init__(self, aggregator: MarketDataAggregator):
        self.agg = aggregator

    def analyze(self, ticker: str, signal_score: float = 50.0,
                signal_confidence: float = 0.0) -> Optional[PriceTargets]:
        """
        Full price analysis for a ticker.

        Args:
            ticker: Yahoo Finance ticker symbol
            signal_score: composite signal score (0-100) from SignalEngine
            signal_confidence: signal confidence (0-1)

        Returns:
            PriceTargets or None if insufficient data
        """
        feed = self.agg.get_feed(ticker)
        if not feed or len(feed.candles) < 20:
            return None

        closes = self.agg.closes(feed)
        highs = self.agg.highs(feed)
        lows = self.agg.lows(feed)
        volumes = self.agg.volumes(feed)
        price = feed.current_price

        # --- Core calculations ---
        atr = self.agg.compute_atr(feed)
        volatility = self.agg.compute_volatility(feed)
        momentum = self.agg.compute_momentum(feed)
        rsi = self.agg.compute_rsi(feed)
        obv_trend = self.agg.compute_obv_trend(feed)
        vol_price_confirm = self.agg.compute_volume_price_confirm(feed)

        # --- Average daily range ---
        daily_ranges = highs - lows
        avg_range = float(np.mean(daily_ranges[-20:])) if len(daily_ranges) >= 20 else float(np.mean(daily_ranges))
        avg_range_pct = avg_range / price if price > 0 else 0.0

        # --- Volume Profile (simplified VPOC/VAH/VAL) ---
        poc, vah, val = self._compute_volume_profile(closes, volumes, window=30)

        # --- Support/Resistance ---
        s1, s2, r1, r2 = self._compute_support_resistance(closes, highs, lows, atr, price)

        # --- Volatility Bands ---
        daily_vol = volatility / np.sqrt(252) if volatility > 0 else 0.02
        upper_1 = price * (1 + daily_vol)
        lower_1 = price * (1 - daily_vol)
        upper_2 = price * (1 + 2 * daily_vol)
        lower_2 = price * (1 - 2 * daily_vol)

        # --- Price Prediction (volume + momentum composite) ---
        pred_dir, pred_move, pred_conf = self._predict_price_move(
            closes, volumes, momentum, rsi, obv_trend,
            vol_price_confirm, atr, price, signal_score
        )
        pred_price = price * (1 + pred_move)

        # --- Buy/Sell/Hold Targets ---
        buy_target, buy_strong, sell_target, sell_strong, hold_low, hold_high = \
            self._compute_targets(price, atr, s1, s2, r1, r2, poc, val, vah,
                                  momentum, obv_trend, vol_price_confirm)

        # --- Edge Calculation (Article 1 formula adapted) ---
        est_win_prob, mkt_implied_prob, edge, kelly_pct = \
            self._compute_edge(signal_score, signal_confidence, momentum,
                               vol_price_confirm, obv_trend, volatility)

        return PriceTargets(
            ticker=ticker,
            current_price=price,
            buy_target=buy_target,
            buy_strong=buy_strong,
            sell_target=sell_target,
            sell_strong=sell_strong,
            hold_low=hold_low,
            hold_high=hold_high,
            predicted_direction=pred_dir,
            predicted_move_pct=pred_move,
            predicted_price=pred_price,
            prediction_confidence=pred_conf,
            upper_band=upper_1,
            lower_band=lower_1,
            upper_2sigma=upper_2,
            lower_2sigma=lower_2,
            volume_profile_poc=poc,
            volume_profile_vah=vah,
            volume_profile_val=val,
            avg_daily_range=avg_range,
            avg_daily_range_pct=avg_range_pct,
            support_1=s1,
            support_2=s2,
            resistance_1=r1,
            resistance_2=r2,
            estimated_win_prob=est_win_prob,
            market_implied_prob=mkt_implied_prob,
            edge=edge,
            kelly_optimal_pct=kelly_pct,
        )

    # ------------------------------------------------------------------
    # Volume Profile Analysis
    # ------------------------------------------------------------------

    def _compute_volume_profile(self, closes: np.ndarray, volumes: np.ndarray,
                                 window: int = 30) -> tuple:
        """
        Simplified Volume Profile computation.
        Returns (POC, VAH, VAL):
        - POC: Price level with highest traded volume (Point of Control)
        - VAH: Value Area High (upper bound of 70% volume concentration)
        - VAL: Value Area Low (lower bound of 70% volume concentration)
        """
        n = min(window, len(closes))
        c = closes[-n:]
        v = volumes[-n:]

        if len(c) == 0 or np.sum(v) == 0:
            p = float(closes[-1]) if len(closes) > 0 else 0.0
            return (p, p, p)

        # Create price bins
        price_min = float(np.min(c))
        price_max = float(np.max(c))
        if price_max == price_min:
            return (float(c[-1]), float(c[-1]), float(c[-1]))

        num_bins = min(20, n)
        bin_edges = np.linspace(price_min, price_max, num_bins + 1)
        bin_volumes = np.zeros(num_bins)

        # Assign volume to price bins
        for i in range(len(c)):
            bin_idx = np.searchsorted(bin_edges[1:], c[i])
            bin_idx = min(bin_idx, num_bins - 1)
            bin_volumes[bin_idx] += v[i]

        # POC = center of highest-volume bin
        poc_idx = int(np.argmax(bin_volumes))
        poc = float((bin_edges[poc_idx] + bin_edges[poc_idx + 1]) / 2)

        # Value Area (70% of total volume)
        total_vol = np.sum(bin_volumes)
        target_vol = total_vol * 0.70
        sorted_indices = np.argsort(bin_volumes)[::-1]
        cumulative = 0.0
        va_bins = []
        for idx in sorted_indices:
            va_bins.append(idx)
            cumulative += bin_volumes[idx]
            if cumulative >= target_vol:
                break

        va_low_idx = min(va_bins)
        va_high_idx = max(va_bins)
        val = float(bin_edges[va_low_idx])
        vah = float(bin_edges[va_high_idx + 1])

        return (poc, vah, val)

    # ------------------------------------------------------------------
    # Support/Resistance
    # ------------------------------------------------------------------

    def _compute_support_resistance(self, closes: np.ndarray, highs: np.ndarray,
                                      lows: np.ndarray, atr: float,
                                      price: float) -> tuple:
        """
        Compute support and resistance levels using:
        1. Recent swing lows/highs
        2. ATR-based levels
        3. SMA levels
        """
        n = min(20, len(closes))
        recent_lows = lows[-n:]
        recent_highs = highs[-n:]

        # Swing low/high
        sorted_lows = np.sort(recent_lows)
        sorted_highs = np.sort(recent_highs)[::-1]

        # Support levels: recent lows below current price
        supports = sorted_lows[sorted_lows < price]
        if len(supports) >= 2:
            s1 = float(supports[-1])  # nearest support
            s2 = float(supports[-2])  # deeper support
        elif len(supports) == 1:
            s1 = float(supports[-1])
            s2 = price - 2 * atr
        else:
            s1 = price - atr
            s2 = price - 2 * atr

        # Resistance levels: recent highs above current price
        resistances = sorted_highs[sorted_highs > price]
        if len(resistances) >= 2:
            r1 = float(resistances[-1])  # nearest resistance
            r2 = float(resistances[-2])  # higher resistance
        elif len(resistances) == 1:
            r1 = float(resistances[-1])
            r2 = price + 2 * atr
        else:
            r1 = price + atr
            r2 = price + 2 * atr

        return (s1, s2, r1, r2)

    # ------------------------------------------------------------------
    # Price Prediction
    # ------------------------------------------------------------------

    def _predict_price_move(self, closes: np.ndarray, volumes: np.ndarray,
                             momentum: float, rsi: float, obv_trend: float,
                             vol_price_confirm: float, atr: float,
                             price: float, signal_score: float) -> tuple:
        """
        Predict next-period price movement using composite of weak signals.
        (Article 2 concept: combining 50 weak signals into one winning trade)

        Combines:
        1. Momentum persistence (price tends to continue in same direction)
        2. RSI mean reversion (extreme RSI → expect bounce/pullback)
        3. OBV trend (accumulation/distribution predicts direction)
        4. Volume-price confirmation (volume validates price moves)
        5. Signal score directional bias
        6. Recent price velocity (rate of change acceleration)
        7. Volume trend (rising/falling participation)
        8. Price vs moving averages (trend alignment)

        Returns: (direction, expected_move_pct, confidence)
        """
        signals = []  # list of (signal_value -1 to +1, weight, confidence)

        # 1. Momentum persistence
        # Short-term momentum tends to persist for 1-3 periods
        mom_signal = np.clip(momentum / 0.05, -1, 1)  # normalize ±5% to ±1
        mom_conf = min(abs(momentum) / 0.03, 1.0)
        signals.append((mom_signal, 0.20, mom_conf))

        # 2. RSI mean reversion
        if rsi > 70:
            rsi_signal = -1.0 * min((rsi - 70) / 30, 1.0)
            rsi_conf = min((rsi - 70) / 20, 1.0)
        elif rsi < 30:
            rsi_signal = 1.0 * min((30 - rsi) / 30, 1.0)
            rsi_conf = min((30 - rsi) / 20, 1.0)
        else:
            rsi_signal = (rsi - 50) / 50 * 0.3
            rsi_conf = 0.3
        signals.append((rsi_signal, 0.10, rsi_conf))

        # 3. OBV trend (accumulation = buy pressure building)
        obv_signal = np.clip(obv_trend, -1, 1)
        obv_conf = min(abs(obv_trend), 1.0)
        signals.append((obv_signal, 0.20, obv_conf))

        # 4. Volume-price confirmation
        vpc_signal = np.clip(vol_price_confirm, -1, 1)
        vpc_conf = min(abs(vol_price_confirm) * 2, 1.0)
        signals.append((vpc_signal, 0.15, vpc_conf))

        # 5. Signal score directional bias
        score_signal = (signal_score - 50) / 50  # -1 to +1
        score_conf = abs(score_signal)
        signals.append((score_signal, 0.15, score_conf))

        # 6. Price velocity (acceleration of price change)
        if len(closes) >= 10:
            returns_5 = (closes[-1] - closes[-5]) / closes[-5] if closes[-5] != 0 else 0
            returns_10 = (closes[-1] - closes[-10]) / closes[-10] if closes[-10] != 0 else 0
            acceleration = returns_5 - (returns_10 / 2)  # recent faster than avg
            vel_signal = np.clip(acceleration / 0.03, -1, 1)
            vel_conf = min(abs(acceleration) / 0.02, 1.0)
        else:
            vel_signal = 0.0
            vel_conf = 0.0
        signals.append((vel_signal, 0.10, vel_conf))

        # 7. Volume trend
        if len(volumes) >= 20:
            recent_vol = np.mean(volumes[-5:])
            prior_vol = np.mean(volumes[-20:-5])
            vol_change = (recent_vol - prior_vol) / prior_vol if prior_vol > 0 else 0
            # Rising volume with momentum = confirms direction
            if momentum > 0 and vol_change > 0:
                vt_signal = min(vol_change, 1.0)
            elif momentum < 0 and vol_change > 0:
                vt_signal = -min(vol_change, 1.0)
            else:
                vt_signal = 0.0
            vt_conf = min(abs(vol_change), 1.0)
        else:
            vt_signal = 0.0
            vt_conf = 0.0
        signals.append((vt_signal, 0.10, vt_conf))

        # --- Composite prediction ---
        # Article 2: Weighted combination with confidence-based weighting
        # Each signal contributes: signal_value * base_weight * confidence
        # This amplifies high-confidence signals and dampens uncertain ones
        total_weighted = 0.0
        total_weight = 0.0
        total_confidence = 0.0

        for sig_val, base_weight, conf in signals:
            effective_weight = base_weight * (0.5 + 0.5 * conf)  # confidence boosts weight
            total_weighted += sig_val * effective_weight
            total_weight += effective_weight
            total_confidence += conf * base_weight

        if total_weight == 0:
            return ("NEUTRAL", 0.0, 0.0)

        composite = total_weighted / total_weight  # -1 to +1

        # Expected move = composite * ATR-based range
        atr_pct = atr / price if price > 0 else 0.02
        expected_move = composite * atr_pct

        # Direction
        if composite > 0.15:
            direction = "UP"
        elif composite < -0.15:
            direction = "DOWN"
        else:
            direction = "NEUTRAL"

        # Confidence in prediction
        confidence = float(np.clip(total_confidence * abs(composite) * 2, 0, 1))

        return (direction, float(expected_move), confidence)

    # ------------------------------------------------------------------
    # Buy/Sell/Hold Targets
    # ------------------------------------------------------------------

    def _compute_targets(self, price: float, atr: float,
                          s1: float, s2: float, r1: float, r2: float,
                          poc: float, val: float, vah: float,
                          momentum: float, obv_trend: float,
                          vol_price_confirm: float) -> tuple:
        """
        Compute actionable price targets for BUY/SELL/HOLD.

        Buy targets: near support levels, below value area
        Sell targets: near resistance levels, above value area
        Hold zone: between buy and sell targets (normal trading range)
        """
        # Buy target: weighted average of support and value area low
        # (where volume profile says there's buying interest)
        buy_target = 0.4 * s1 + 0.3 * val + 0.3 * (price - atr * 0.5)
        buy_strong = 0.4 * s2 + 0.3 * val + 0.3 * (price - atr * 1.5)

        # Sell target: weighted average of resistance and value area high
        sell_target = 0.4 * r1 + 0.3 * vah + 0.3 * (price + atr * 0.5)
        sell_strong = 0.4 * r2 + 0.3 * vah + 0.3 * (price + atr * 1.5)

        # Adjust targets based on volume signals
        # Strong accumulation (OBV up) → raise buy targets slightly (less discount needed)
        if obv_trend > 0.3:
            adjustment = atr * 0.2 * obv_trend
            buy_target += adjustment
            buy_strong += adjustment
        elif obv_trend < -0.3:
            adjustment = atr * 0.2 * abs(obv_trend)
            sell_target -= adjustment
            sell_strong -= adjustment

        # Volume-price confirmation adjustment
        if vol_price_confirm > 0.3:
            # Bullish volume → raise sell targets (momentum likely continues)
            sell_target += atr * 0.15
            sell_strong += atr * 0.3
        elif vol_price_confirm < -0.3:
            # Bearish volume → lower buy targets (more downside likely)
            buy_target -= atr * 0.15
            buy_strong -= atr * 0.3

        # Hold zone: between buy and sell
        hold_low = buy_target + (sell_target - buy_target) * 0.25
        hold_high = buy_target + (sell_target - buy_target) * 0.75

        # Ensure logical ordering
        buy_strong = min(buy_strong, buy_target - atr * 0.3)
        sell_strong = max(sell_strong, sell_target + atr * 0.3)

        return (buy_target, buy_strong, sell_target, sell_strong, hold_low, hold_high)

    # ------------------------------------------------------------------
    # Edge Calculation (Article 1 adapted)
    # ------------------------------------------------------------------

    def _compute_edge(self, signal_score: float, signal_confidence: float,
                       momentum: float, vol_price_confirm: float,
                       obv_trend: float, volatility: float) -> tuple:
        """
        Probability-based edge calculation adapted from Article 1
        (latency arbitrage edge formula applied to stock signals).

        The core concept: Our signal gives us an estimated probability of being
        correct. The market's current price implies a different probability.
        The edge is the difference.

        Article 1 formula: edge = estimated_prob - market_implied_prob
        Kelly: f* = (p * b - q) / b where p=win_prob, q=1-p, b=payoff_ratio

        For stocks, we adapt this:
        - estimated_prob: derived from signal score + confirmation signals
        - market_implied_prob: derived from recent price action efficiency
        - edge: the informational advantage our composite signal has
        """
        # Estimated win probability from composite signals
        # Signal score > 50 = bullish edge, < 50 = bearish edge
        score_dist = abs(signal_score - 50) / 50  # 0-1
        base_prob = 0.50 + score_dist * 0.20  # 50-70%

        # Boost from confirmation signals
        confirmation_bonus = 0.0

        # OBV confirms direction → higher probability
        if (signal_score > 50 and obv_trend > 0.2) or (signal_score < 50 and obv_trend < -0.2):
            confirmation_bonus += min(abs(obv_trend) * 0.05, 0.05)

        # Volume-price confirms → higher probability
        if (signal_score > 50 and vol_price_confirm > 0.2) or \
           (signal_score < 50 and vol_price_confirm < -0.2):
            confirmation_bonus += min(abs(vol_price_confirm) * 0.05, 0.05)

        # Momentum confirms → higher probability
        if (signal_score > 50 and momentum > 0.01) or (signal_score < 50 and momentum < -0.01):
            confirmation_bonus += min(abs(momentum) * 2, 0.03)

        estimated_prob = min(base_prob + confirmation_bonus, 0.80)

        # Market-implied probability from price efficiency
        # In efficient markets, the "implied probability" of continuation = ~50%
        # In trending markets with low vol, implied prob is higher
        # In choppy markets with high vol, implied prob is lower
        if volatility > 0.50:
            market_prob = 0.48  # choppy → slightly less than 50-50
        elif volatility < 0.15:
            market_prob = 0.52  # trending → slightly above 50-50
        else:
            market_prob = 0.50

        # Edge
        edge = estimated_prob - market_prob

        # Kelly-optimal allocation
        # Assume payoff ratio b = 1.5 (typical risk-reward for stock trades)
        b = 1.5
        q = 1.0 - estimated_prob
        kelly_f = (estimated_prob * b - q) / b
        kelly_pct = max(kelly_f, 0.0) * 100  # as percentage

        return (estimated_prob, market_prob, edge, kelly_pct)
