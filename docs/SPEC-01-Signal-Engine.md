# SPEC 01 — Signal Engine & Composite Scoring Model

**Product**: MY Stock Market Trading Platform
**Module**: `signals.py`, `config.py`, `sentiment_config.py`
**Version**: 1.0 | April 2026

---

## 1. Purpose

The Signal Engine generates BUY / SELL / HOLD trading signals for each stock in the KLSE universe (~129 stocks) by combining nine independent technical sub-signals into a single composite score (0-100). The score drives downstream position sizing, price targets, and the AI analysis prompt.

---

## 2. Architecture Overview

```
                         Yahoo Finance (yfinance)
                                 |
                        MarketDataAggregator
                       /    |    |    |    \
                      /     |    |    |     \
               Closes  Highs  Lows  Volumes  OHLCV
                      \     |    |    |     /
                       \    |    |    |    /
                  +---------+---------+---------+
                  |     Signal Engine           |
                  |  (9 sub-signal functions)    |
                  +---------+---------+---------+
                            |
              +-------------+-------------+
              |             |             |
        Momentum(0.14)  RSI(0.10)   VWAP(0.10)
        EMA(0.10)     Volume(0.07) VolPrice(0.19)
        Sentiment(0.08) Ichimoku(0.12) Pattern(0.10)
              |             |             |
              +-------------+-------------+
                            |
                   Weighted Composite (0-100)
                            |
                  +---------+---------+
                  |  Direction Logic  |
                  |  >= 60 = BUY     |
                  |  <= 40 = SELL    |
                  |  else  = HOLD   |
                  +-------------------+
                            |
                  Signal(direction, score,
                         edge, confidence,
                         reasons[])
```

---

## 3. Sub-Signal Specifications

Each sub-signal maps its indicator to a 0-100 scale where:
- **0** = strongly bearish
- **50** = neutral
- **100** = strongly bullish

### 3.1 Momentum Signal (Weight: 14%)

| Parameter | Value |
|-----------|-------|
| Window | 10 days |
| Threshold | 2% (0.02) |
| Noise Filter | `abs(momentum) < threshold * 0.3` returns 50 |

**Formula:**
```
scaled = momentum / (threshold * 3)
score  = clip(50 + scaled * 50, 0, 100)
```

Mapping: A +6% momentum over 10 days maps to score 100 (max bullish). A -6% maps to 0 (max bearish).

### 3.2 RSI Signal (Weight: 10%)

| Parameter | Value |
|-----------|-------|
| Period | 14 days |
| Overbought | 70 |
| Oversold | 30 |

**Counter-trend logic** (mean-reversion approach):
```
If RSI >= 70 (overbought):
    excess = (RSI - 70) / 30
    score  = clip(50 - excess * 40, 5, 50)    # bearish

If RSI <= 30 (oversold):
    excess = (30 - RSI) / 30
    score  = clip(50 + excess * 40, 50, 95)   # bullish

Else (neutral zone):
    score  = 50 + (RSI - 50) * 0.3
```

### 3.3 VWAP Deviation Signal (Weight: 10%)

| Parameter | Value |
|-----------|-------|
| Deviation Threshold | 1% (0.01) |
| Extreme Threshold | 4x deviation threshold |

**Dual-mode logic:**
```
If deviation < threshold:           score = 50 (no signal)
If moderate (< 4x threshold):      trend continuation
    score = clip(50 + deviation / (threshold * 8) * 50, 10, 90)
If extreme (>= 4x threshold):      mean reversion
    score = clip(50 - deviation / (threshold * 8) * 50, 10, 90)
```

### 3.4 EMA Crossover Signal (Weight: 10%)

| Parameter | Value |
|-----------|-------|
| Short EMA | 12 periods |
| Long EMA | 26 periods |

**Formula:**
```
diff_pct    = (EMA_12 - EMA_26) / EMA_26
price_vs_ema = (price - EMA_12) / EMA_12
combined    = diff_pct * 0.7 + price_vs_ema * 0.3
score       = clip(50 + combined * 500, 10, 90)
```

### 3.5 Volume Activity Signal (Weight: 7%)

| Parameter | Value |
|-----------|-------|
| Spike Multiplier | 2.0x average |

**Logic:**
```
If volume_ratio < 0.5:  score = 50 (too quiet)
If volume_ratio > 2.0x:
    If momentum > 0: score = clip(50 + ratio * 10, 50, 90)
    If momentum < 0: score = clip(50 - ratio * 10, 10, 50)
    Else:            score = 50 (spike without direction)
Normal volume + momentum > 0 + ratio > 1.0: score = 55
Normal volume + momentum < 0 + ratio > 1.0: score = 45
```

### 3.6 Volume-Price Analysis (Weight: 19%)

The heaviest-weighted sub-signal. Three internal components:

| Component | Internal Weight | Source |
|-----------|----------------|--------|
| OBV Trend | 40% | On-Balance Volume slope |
| Vol-Price Confirmation | 35% | Correlation of volume & price direction |
| Activity Level | 25% | Volume trend + current ratio boost |

**OBV Component:**
```
obv_score = clip(50 + obv_trend * 40, 10, 90)
```

**Volume-Price Confirmation:**
```
confirm_score = clip(50 + vol_price_confirm * 40, 10, 90)
```

**Activity Level:**
```
Rising vol + positive momentum:  clip(50 + vol_trend * 30, 50, 85)
Rising vol + negative momentum:  clip(50 - vol_trend * 30, 15, 50)
Declining vol:                   50 + momentum * 200, clip to [40, 60]

Volume ratio > 1.5x bonus:
    boost = min((ratio - 1.0) * 5, 10)
    Applied directionally
```

**Composite:**
```
vp_score = clip(OBV * 0.40 + Confirm * 0.35 + Activity * 0.25, 0, 100)
```

### 3.7 Sentiment Signal (Weight: 8%)

Only included when `mention_count >= 2` (configurable). Score sourced directly from the Sentiment Pipeline (see SPEC-03).

| Threshold | Reason Generated |
|-----------|-----------------|
| Score > 65 | "Forum bullish (N mentions)" |
| Score < 35 | "Forum bearish (N mentions)" |
| Buzz > 70 | "High forum buzz: N mentions" |

### 3.8 Ichimoku Cloud Signal (Weight: 12%)

Starts at 50.0 and applies additive adjustments:

| Component | Bullish | Bearish |
|-----------|---------|---------|
| Cloud Color (Senkou A vs B) | +10 | -10 |
| Price vs Cloud | +15 (above) | -15 (below) |
| TK Cross | +12 (bullish) | -12 (bearish) |
| Tenkan vs Kijun diff | `+diff * 200` | `-diff * 200` |
| Cloud Thickness > 2% | +5 (support) | -5 (resistance) |

**Range:** clip(5, 95)

### 3.9 Pattern Recognition Signal (Weight: 10%)

Sourced from the Pattern Recognition Engine (see SPEC-01 Appendix B).

**Scoring formula:**
```
net      = (bull_strength - bear_strength) / (bull_strength + bear_strength)
score    = clip(50 + net * 40, 5, 95)
confidence = min(total_strength / 3.0, 1.0)
```

---

## 4. Composite Score Calculation

```
composite = sum(sub_score_i * weight_i)  for all active sub-signals
composite = clip(composite, 0, 100)
```

**Weight Sets:**

With Sentiment (9 signals, sum = 1.00):
| Signal | Weight |
|--------|--------|
| Momentum | 0.14 |
| RSI | 0.10 |
| VWAP | 0.10 |
| EMA | 0.10 |
| Volume | 0.07 |
| Vol-Price | 0.19 |
| Sentiment | 0.08 |
| Ichimoku | 0.12 |
| Pattern | 0.10 |

Without Sentiment (8 signals, sum = 1.00):
| Signal | Weight |
|--------|--------|
| Momentum | 0.16 |
| RSI | 0.11 |
| VWAP | 0.11 |
| EMA | 0.11 |
| Volume | 0.08 |
| Vol-Price | 0.21 |
| Ichimoku | 0.12 |
| Pattern | 0.10 |

---

## 5. Direction Determination

| Condition | Direction |
|-----------|-----------|
| `score >= 60` | BUY |
| `score <= 40` | SELL |
| `40 < score < 60` | HOLD |
| `score >= 75 or score <= 25` | Strong signal (1.5x size multiplier) |

---

## 6. Confidence Calculation

```
score_deviations  = [abs(sub_score - 50) / 50 for each sub-signal]
avg_deviation     = mean(score_deviations)
signal_agreement  = 1.0 - std(score_deviations)
vol_factor        = volatility_filter(annualized_vol)
confidence        = clip(avg_deviation * signal_agreement * vol_factor, 0, 1)
```

**Volatility Filter (confidence multiplier):**

| Annualized Vol | Factor |
|----------------|--------|
| > 80% | 0.3 (extreme) |
| > 50% | 0.6 (high) |
| > 30% | 0.8 (elevated) |
| > 15% | 1.0 (normal) |
| > 8% | 0.8 (low) |
| <= 8% | 0.4 (dead market) |

---

## 7. Edge Calculation

Adapted from probability-based edge (arbitrage formula applied to stocks):

```
score_dist     = abs(score - 50) / 50
estimated_prob = 0.50 + score_dist * 0.20              # range: 50-70%

# Confirmation bonuses (each capped at +5%)
if OBV confirms direction:       +min(abs(obv_trend) * 0.05, 0.05)
if vol_price confirms direction: +min(abs(vpc) * 0.05, 0.05)

estimated_prob = min(estimated_prob, 0.80)
edge           = (estimated_prob - 0.50) * vol_factor
```

**Tradeability Requirements:**
- `edge >= 0.03` (3% minimum)
- `confidence >= 0.10`
- `direction != HOLD`

---

## 8. Data Flow Diagram

```
+------------------+     +------------------+     +------------------+
| Yahoo Finance    | --> | MarketData       | --> | Signal Engine    |
| (3mo daily OHLCV)|     | Aggregator       |     | .generate()      |
+------------------+     | - closes, highs  |     | - 9 sub-signals  |
                         | - lows, volumes  |     | - composite      |
+------------------+     | - RSI, EMA       |     | - confidence     |
| Sentiment        | --> | - VWAP, OBV      |     | - edge           |
| Aggregator       |     | - Ichimoku       |     +--------+---------+
+------------------+     | - volatility     |              |
                         +------------------+              v
+------------------+                              +------------------+
| Pattern Engine   | --------------------------> | Signal Output    |
+------------------+                              | (direction,      |
                                                  |  score, edge,    |
                                                  |  confidence,     |
                                                  |  reasons[])      |
                                                  +--------+---------+
                                                           |
                              +----------------------------+
                              |            |               |
                              v            v               v
                        Risk Manager  Price Analyzer  AI Analysis
                        (sizing)      (targets)       (Claude prompt)
```

---

## Appendix A: Configuration Constants

From `config.py`:

| Constant | Value | Description |
|----------|-------|-------------|
| `momentum_window` | 10 | Days for momentum calculation |
| `momentum_threshold` | 0.02 | 2% move considered significant |
| `rsi_period` | 14 | Standard RSI lookback |
| `rsi_overbought` | 70 | RSI overbought level |
| `rsi_oversold` | 30 | RSI oversold level |
| `vwap_deviation_threshold` | 0.01 | 1% VWAP deviation |
| `buy_threshold` | 60 | Composite score for BUY |
| `sell_threshold` | 40 | Composite score for SELL |
| `strong_signal_threshold` | 75 | Strong signal level |
| `edge_threshold` | 0.03 | Minimum 3% edge to trade |
| `min_confidence` | 0.10 | Minimum confidence to trade |
| `volume_spike_multiplier` | 2.0 | 2x avg = volume spike |

## Appendix B: Pattern Recognition Catalogue

**Candlestick Patterns (last 3 candles):**

| Pattern | Bias | Strength | Condition |
|---------|------|----------|-----------|
| Hammer | Bullish | 0.6 | Small body at top, lower shadow > 2x body, in downtrend |
| Inverted Hammer | Bullish | 0.5 | Upper shadow > 2x body, in downtrend |
| Shooting Star | Bearish | 0.6 | Upper shadow > 2x body, in uptrend |
| Hanging Man | Bearish | 0.5 | Lower shadow > 2x body, in uptrend |
| Doji | Context | 0.3 | Body ratio < 10% of range, bias from 5-day trend |
| Bullish Engulfing | Bullish | 0.5-0.8 | Red candle followed by larger green, fully engulfing |
| Bearish Engulfing | Bearish | 0.5-0.8 | Green candle followed by larger red, fully engulfing |
| Morning Star | Bullish | 0.7 | Big red + small body + big green (3-candle) |
| Evening Star | Bearish | 0.7 | Big green + small body + big red (3-candle) |
| Three White Soldiers | Bullish | 0.8 | Three consecutive bullish candles > avg body |
| Three Black Crows | Bearish | 0.8 | Three consecutive bearish candles > avg body |
| Marubozu | Context | 0.6 | Body ratio > 85%, body > 1.5x avg |

**Chart Formations (20-30 day lookback):**

| Pattern | Bias | Strength | Method |
|---------|------|----------|--------|
| Double Top | Bearish | 0.7 | Two peaks within 2% tolerance, price below neckline |
| Double Bottom | Bullish | 0.7 | Two troughs within 2% tolerance, price above neckline |
| Resistance Breakout | Bullish | 0.7 | Close > recent high + volume > 1.3x avg |
| Support Breakdown | Bearish | 0.7 | Close < recent low + volume > 1.3x avg |
| Triangle Breakout Up | Bullish | 0.6-0.7 | Converging highs/lows, breakout above |
| Triangle Breakdown | Bearish | 0.6-0.7 | Converging highs/lows, breakdown below |
| Channel Bottom Bounce | Bullish | 0.5 | Uptrend, price at -1 sigma in channel |
| Channel Top Overbought | Bearish | 0.4 | Uptrend, price at +1.5 sigma in channel |
