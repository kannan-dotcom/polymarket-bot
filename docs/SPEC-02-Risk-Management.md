# SPEC 02 — Risk Management & Portfolio Framework

**Product**: MY Stock Market Trading Platform
**Modules**: `risk_manager.py`, `portfolio.py`, `portfolio_optimizer.py`, `price_analysis.py`, `config.py`
**Version**: 1.0 | April 2026

---

## 1. Purpose

The Risk Management layer controls position sizing, enforces drawdown limits, and manages the portfolio lifecycle. It uses a fractional Kelly Criterion adapted for equity trading, combined with hard caps to protect capital.

---

## 2. Architecture Overview

```
+------------------+
| Signal Engine    |
| (score, edge,    |
|  confidence)     |
+--------+---------+
         |
         v
+------------------+     +------------------+
| Risk Manager     | --> | Portfolio        |
| - Kelly sizing   |     | - Open positions |
| - Daily loss cap |     | - P&L tracking   |
| - Position caps  |     | - Trade log      |
| - Drawdown track |     | - Exchange stats  |
+--------+---------+     +------------------+
         |
         v
+------------------+
| Price Analyzer   |
| - Buy/Sell zones |
| - Win probability|
| - Edge calc      |
| - Kelly optimal% |
+------------------+
```

---

## 3. Capital & Risk Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `STARTING_CAPITAL` | $100.00 | Initial bankroll (USD) |
| `MAX_POSITION_PCT` | 5% | Maximum single position as % of bankroll |
| `MAX_DAILY_LOSS_PCT` | 10% | Stop all trading after 10% daily drawdown |
| `MAX_CONCURRENT_POSITIONS` | 5 | Maximum simultaneous open positions |
| `MIN_TRADE_SIZE` | $5.00 | Minimum trade size |
| `MAX_TRADE_SIZE` | $20.00 | Maximum trade size |
| `KELLY_FRACTION` | 0.25 | Quarter-Kelly (conservative) |

---

## 4. Kelly Criterion Position Sizing

### 4.1 Core Formula

The classical Kelly Criterion:

```
f* = (p * b - q) / b
```

Where:
- `p` = estimated win probability
- `q` = 1 - p (loss probability)
- `b` = payoff ratio (expected gain / expected loss)
- `f*` = optimal fraction of bankroll to wager

### 4.2 Win Probability Estimation

Derived from the Signal Engine output:

```
score_dist = abs(signal.score - 50) / 50         # 0 to 1
base_prob  = 0.50 + score_dist * 0.20            # 50% to 70%
edge_boost = min(signal.edge * 0.5, 0.10)        # capped at +10%
win_prob   = min(base_prob + edge_boost, 0.80)    # hard cap at 80%
```

| Signal Score | Base Prob | With Max Edge |
|-------------|-----------|---------------|
| 50 (neutral) | 50% | 60% |
| 60 (BUY threshold) | 54% | 64% |
| 75 (strong) | 60% | 70% |
| 90 (very strong) | 66% | 76% |

### 4.3 Payoff Ratio

```
b = 1.0 + signal.edge * 10
b = clip(b, 1.0, 3.0)
```

| Edge | Payoff Ratio |
|------|-------------|
| 0.03 | 1.3 |
| 0.05 | 1.5 |
| 0.10 | 2.0 |
| 0.20 | 3.0 (max) |

### 4.4 Confidence-Weighted Kelly

```
confidence_multiplier = 0.5 + 0.5 * signal.confidence   # range: 0.5 to 1.0
fraction = kelly_f * KELLY_FRACTION * confidence_multiplier
raw_size = balance * fraction
```

This implements "Quarter-Kelly" as the baseline (KELLY_FRACTION = 0.25), further modulated by signal confidence. Low-confidence signals use Half-of-Quarter-Kelly (12.5% of full Kelly), while high-confidence signals use the full Quarter-Kelly (25%).

### 4.5 Worked Example

```
Signal: score=72, edge=0.07, confidence=0.65

win_prob = 0.50 + (22/50)*0.20 + min(0.07*0.5, 0.10) = 0.588 + 0.035 = 0.623
b        = 1.0 + 0.07 * 10 = 1.7
q        = 1.0 - 0.623 = 0.377
kelly_f  = (0.623 * 1.7 - 0.377) / 1.7 = (1.059 - 0.377) / 1.7 = 0.401

conf_mult = 0.5 + 0.5 * 0.65 = 0.825
fraction  = 0.401 * 0.25 * 0.825 = 0.0827 (8.27% of bankroll)

With $100 balance: raw_size = $8.27
After MAX_POSITION_PCT cap (5%): size = $5.00
```

---

## 5. Trade Size Constraints

The `compute_trade_size()` function applies these checks in order:

```
1. signal.is_tradeable?           (edge >= 0.03, confidence >= 0.10, not HOLD)
2. Daily loss limit OK?           (daily P&L > -10% of start-of-day balance)
3. Open positions < 5?
4. kelly_size()                   (raw Kelly-based size)
5. Cap at MAX_POSITION_PCT        (5% of balance)
6. Strong signal bonus?           (1.5x if score >= 75 or <= 25)
7. Hard cap: MAX_TRADE_SIZE       ($20.00)
8. Minimum: MIN_TRADE_SIZE        ($5.00)
9. Available capital check        (balance - committed positions)

If any check fails or size < $5.00 --> returns $0.00 (skip trade)
```

---

## 6. Risk Controls

### 6.1 Daily Loss Limit

```
max_daily_loss = daily_start_balance * MAX_DAILY_LOSS_PCT (10%)
if daily_pnl < -max_daily_loss:
    ALL trading halted for remainder of day
```

Resets automatically at start of each new calendar day.

### 6.2 Drawdown Tracking

```
if balance > peak_balance:
    peak_balance = balance
drawdown = (peak_balance - balance) / peak_balance
max_drawdown = max(max_drawdown, drawdown)
```

### 6.3 Position P&L

```
BUY position:   pnl = shares * (exit_price - entry_price)
SELL position:  pnl = shares * (entry_price - exit_price)
```

---

## 7. Price Analysis & Target System

The Price Analyzer computes actionable buy/sell/hold price zones for each stock.

### 7.1 Volume Profile (VPOC / VAH / VAL)

Uses a 30-day lookback with 20 price bins:

```
POC (Point of Control) = center of highest-volume bin
Value Area = 70% of total volume, expanding from POC
VAH = upper bound of value area
VAL = lower bound of value area
```

### 7.2 Support & Resistance

From 20-day swing highs/lows:

```
Support 1  = nearest swing low below current price
Support 2  = next deeper swing low
Resistance 1 = nearest swing high above current price
Resistance 2 = next higher swing high

Fallback (no swings found): ATR-based levels
    S1 = price - ATR,    S2 = price - 2*ATR
    R1 = price + ATR,    R2 = price + 2*ATR
```

### 7.3 Buy/Sell/Hold Target Formulas

```
buy_target  = 0.4 * S1 + 0.3 * VAL + 0.3 * (price - ATR * 0.5)
buy_strong  = 0.4 * S2 + 0.3 * VAL + 0.3 * (price - ATR * 1.5)

sell_target = 0.4 * R1 + 0.3 * VAH + 0.3 * (price + ATR * 0.5)
sell_strong = 0.4 * R2 + 0.3 * VAH + 0.3 * (price + ATR * 1.5)

hold_low  = buy_target + (sell_target - buy_target) * 0.25
hold_high = buy_target + (sell_target - buy_target) * 0.75
```

**Volume Signal Adjustments:**

| Condition | Adjustment |
|-----------|------------|
| OBV accumulation (> 0.3) | Raise buy targets by `ATR * 0.2 * obv_trend` |
| OBV distribution (< -0.3) | Lower sell targets by `ATR * 0.2 * abs(obv)` |
| Bullish vol-price confirm (> 0.3) | Raise sell targets by `ATR * 0.15 / 0.30` |
| Bearish vol-price confirm (< -0.3) | Lower buy targets by `ATR * 0.15 / 0.30` |

### 7.4 Volatility Bands

```
daily_vol = annualized_vol / sqrt(252)
Upper 1-sigma = price * (1 + daily_vol)
Lower 1-sigma = price * (1 - daily_vol)
Upper 2-sigma = price * (1 + 2 * daily_vol)
Lower 2-sigma = price * (1 - 2 * daily_vol)
```

### 7.5 Price Prediction Model

Combines 7 weak signals into a composite directional prediction:

| Signal | Weight | Source |
|--------|--------|--------|
| Momentum persistence | 20% | Short-term price trend (normalized to +/-5%) |
| RSI mean reversion | 10% | Extreme RSI reversal expectation |
| OBV trend | 20% | Accumulation/distribution pressure |
| Vol-price confirmation | 15% | Volume validating price direction |
| Signal score bias | 15% | Composite signal direction |
| Price velocity | 10% | Acceleration of returns (5d vs 10d) |
| Volume trend | 10% | Rising/falling participation directionally |

**Composite calculation:**
```
effective_weight_i = base_weight_i * (0.5 + 0.5 * confidence_i)
composite = sum(signal_i * effective_weight_i) / sum(effective_weight_i)
expected_move = composite * (ATR / price)

Direction:  composite > +0.15 = UP,  < -0.15 = DOWN,  else NEUTRAL
Confidence: clip(total_confidence * abs(composite) * 2, 0, 1)
```

### 7.6 Edge Calculation (Probability-Based)

```
Estimated Win Probability:
    base_prob = 0.50 + (abs(score - 50) / 50) * 0.20
    + OBV confirmation bonus   (up to +5%)
    + Vol-price confirmation   (up to +5%)
    + Momentum confirmation    (up to +3%)
    = min(sum, 0.80)

Market-Implied Probability:
    High vol (>50%):    0.48 (choppy)
    Low vol (<15%):     0.52 (trending)
    Normal:             0.50

Edge = estimated_prob - market_prob

Kelly Optimal % = (p * b - q) / b * 100
    where b = 1.5 (assumed payoff ratio for stocks)
```

---

## 8. Portfolio State Tracking

| Metric | Formula |
|--------|---------|
| Win Rate | winning_trades / total_trades * 100 |
| Total P&L % | total_pnl / STARTING_CAPITAL * 100 |
| Available Capital | balance - sum(open_position_sizes) |
| Max Drawdown % | (peak_balance - min_balance) / peak_balance * 100 |

---

## 9. Data Flow Diagram

```
Scanner Loop (every 5 min)
    |
    v
For each stock:
    MarketData --> SignalEngine.generate() --> Signal
                                                |
                         +----------------------+
                         |                      |
                         v                      v
                   RiskManager              PriceAnalyzer
                   .compute_trade_size()    .analyze()
                         |                      |
                         v                      v
                   If size > 0:            PriceTargets
                   Portfolio.open_position()   (buy/sell/hold zones,
                         |                      prediction, edge)
                         v
                   Position tracked
                   P&L updated on close
                   Drawdown monitored
```
