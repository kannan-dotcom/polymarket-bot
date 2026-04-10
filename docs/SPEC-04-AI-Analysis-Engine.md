# SPEC 04 — AI Analysis Engine & Conflict Resolution

**Product**: MY Stock Market Trading Platform
**Modules**: `dashboard.py` (AI analysis endpoints), `fundamental_analysis.py`
**Version**: 1.0 | April 2026

---

## 1. Purpose

The AI Analysis Engine provides on-demand, per-stock investment analysis via a search bar on the dashboard. When a user selects a stock, all available data (technical signals, fundamentals, price targets, chart patterns, forum sentiment) is compiled into a structured prompt and sent to Claude Sonnet, which assumes the persona of a Maybank Investment Bank equity research analyst. The response includes a BUY/SELL/HOLD/TRADE recommendation, risk level, news confidence assessment, conflict resolution, and a narrative assessment.

A rule-based fallback generates equivalent output when the AI API is unavailable.

---

## 2. Architecture Overview

```
User types stock name in search bar
            |
            v
    +-------------------+
    | Autocomplete      |
    | - Fuzzy match on  |
    |   name, ticker,   |
    |   code, sector    |
    | - Config-seeded   |
    |   (instant, 144   |
    |   stocks)         |
    +--------+----------+
             |
             v
    GET /api/ai-analysis/<stock_key>
             |
    +--------v----------+
    | Cache Check       |
    | TTL: 5 min        |
    | Daily cap: 200    |
    +--------+----------+
         |          |
      HIT         MISS
         |          |
         v          v
    Return       Gather Data
    cached       from 5 sources
                     |
         +-----------+-----------+-----------+-----------+
         |           |           |           |           |
         v           v           v           v           v
    Scanner     Fundamentals  Price       Patterns   Sentiment
    Data        Data          Targets     Data       Data
    (in-memory) (in-memory)   (computed)  (computed) (in-memory)
         |           |           |           |           |
         +-----------+-----------+-----------+-----------+
                                 |
                                 v
                    +----------------------------+
                    | Build Analysis Prompt      |
                    | (Maybank IB Broker Persona) |
                    +----------------------------+
                                 |
                   +-------------+-------------+
                   |                           |
             API Key exists              No API Key
                   |                           |
                   v                           v
            Claude Sonnet              Rule-Based Fallback
            API Call                   (deterministic)
                   |                           |
                   v                           v
            Parse Response            Generate from signals
                   |                           |
                   +-------------+-------------+
                                 |
                                 v
                    +----------------------------+
                    | Response JSON              |
                    | - recommendation           |
                    | - confidence               |
                    | - risk_level               |
                    | - news_confidence          |
                    | - conflict_resolution      |
                    | - narrative                |
                    | - all raw metrics          |
                    +----------------------------+
                                 |
                                 v
                    Frontend Analysis Panel
```

---

## 3. Caching & Rate Limiting

| Parameter | Value |
|-----------|-------|
| Cache TTL | 300 seconds (5 minutes) |
| Daily API Call Cap | 200 calls |
| Thread Safety | `threading.Lock()` |
| Cache Key | stock_key (uppercase) |
| Cache Structure | `{stock_key: (result_dict, timestamp)}` |

---

## 4. Data Gathering

Five data sources are queried from in-memory objects (no external API calls):

| Source | Function | Data |
|--------|----------|------|
| Scanner | `_get_scanner_data_for()` | Price, score, direction, edge, confidence, all 9 sub-scores, volume metrics, reasons |
| Fundamentals | `_get_fundamentals_for()` | P/E, ROE, revenue growth, profit margin, D/E, dividend yield, EPS, fundamental score |
| Price Targets | `_get_price_targets_for()` | Buy/sell targets, predicted direction, win probability, support/resistance, volatility bands |
| Patterns | `_get_pattern_data_for()` | Detected candlestick/chart patterns, pattern score, strongest pattern |
| Sentiment | `_get_sentiment_for()` | Mention count, sentiment score, LLM consensus, events, recent posts with timestamps |

---

## 5. AI Prompt Design (Maybank IB Persona)

### 5.1 Persona

```
"You are a senior equity research analyst at Maybank Investment Bank
covering Bursa Malaysia (KLSE). You evaluate stocks for institutional
and retail clients with rigorous, evidence-based analysis. You are
skeptical of noise and demand corroboration before trusting any single
data source."
```

### 5.2 Prompt Structure

```
[PERSONA]

STOCK: {name} ({key}, {ticker}), Sector: {sector}
DATE: {current datetime}

── TECHNICAL SIGNALS ──
Price, RSI, Momentum
Composite Score: X/100, System Signal: BUY/SELL/HOLD
Sub-Scores: Momentum=X, RSI=X, VWAP=X, EMA=X, Volume=X,
            VolPrice=X, Ichimoku=X, Pattern=X, Sentiment=X
Volume: Daily=X, Avg20=X, Ratio=Xx, OBV=X

MODEL CONFLICTS (if any):
  - {sub-signal} bearish (X) vs BUY signal
  - {sub-signal} bullish (X) vs SELL signal

System Reasons: reason1 | reason2 | ...

── FUNDAMENTALS ──
P/E=X, RevGrowth%=X, Margin=X%, ROE=X%, D/E=X, DivYield=X%, EPS=X, FundScore=X

── PRICE TARGETS ──
Buy Target: X, Sell Target: X, Predicted: UP/DOWN X%, Win Prob: X

── CHART PATTERNS ──
  PatternName (bias, strength=X%)
  ...

── MARKET SENTIMENT & NEWS ──
Mentions: X, Sentiment Score: X/100, LLM Consensus: X, Catalyst: Yes/No

VERBATIM FORUM POSTS:
  [1] 2026-04-10 14:30 (2h ago) [klsescreener] POSITIVE: "post text..."
  [2] 2026-04-10 10:00 (6h ago) [reddit] NEGATIVE: "post text..."
  ...

── YOUR ANALYSIS TASKS ──
1. NEWS SIGNAL: Evaluate each forum post for authenticity (0-100)
2. CROSS-VALIDATION: Check if posts corroborate; compute NEWS_CONFIDENCE (0-100)
3. CONFLICT RESOLUTION: Resolve model conflicts with rationale
4. FINAL VERDICT: Recommendation combining all evidence

Response format (exact, one line each):
RECOMMENDATION|<BUY/SELL/HOLD/TRADE>|<confidence 0.0-1.0>
RISK|<LOW/MEDIUM/HIGH>
NEWS_CONFIDENCE|<0-100>
CONFLICT_RESOLUTION|<1-2 sentences>
NARRATIVE|<2-3 sentences citing specific evidence>
```

### 5.3 Conflict Detection

Before sending to Claude, the system pre-detects model conflicts with a 15-point threshold:

```
For each sub-signal:
    if direction == "BUY" and sub_score < 35:
        conflict: "{signal} bearish ({score}) vs BUY"
    if direction == "SELL" and sub_score > 65:
        conflict: "{signal} bullish ({score}) vs SELL"
```

These are embedded in the prompt so Claude can address them.

### 5.4 Claude API Configuration

| Parameter | Value |
|-----------|-------|
| Model | `claude-sonnet-4-20250514` |
| Max Tokens | 300 |
| Temperature | 0 |
| Estimated Input Tokens | ~300 |
| Estimated Cost per Call | ~$0.003 |
| Daily Cost (with cache) | $0.06 - $0.25 |

---

## 6. Response Parsing

The structured response is parsed line by line:

| Line Prefix | Extracted Field | Validation |
|-------------|----------------|------------|
| `RECOMMENDATION\|` | recommendation, confidence | BUY/SELL/HOLD/TRADE, 0.0-1.0 |
| `RISK\|` | risk_level | LOW/MEDIUM/HIGH |
| `NEWS_CONFIDENCE\|` | news_confidence | integer 0-100 |
| `CONFLICT_RESOLUTION\|` | conflict_resolution | free text |
| `NARRATIVE\|` | narrative | free text |

All raw metrics from scanner, fundamentals, and price targets are attached to the response for frontend display.

---

## 7. Rule-Based Fallback

When `ANTHROPIC_API_KEY` is not set or Claude API fails:

### 7.1 Recommendation Logic

```
score     = scan.score (composite signal score)
direction = scan.direction
tradeable = scan.is_tradeable
confidence_val = scan.confidence (signal confidence)

if score >= 65 and direction == "BUY":
    recommendation = "BUY"
    confidence     = min(0.5 + (score - 60) * 0.01, 0.85)

elif score <= 35 and direction == "SELL":
    recommendation = "SELL"
    confidence     = min(0.5 + (40 - score) * 0.01, 0.85)

elif tradeable and direction in ("BUY", "SELL"):
    recommendation = "TRADE"
    confidence     = min(0.3 + confidence_val * 0.3, 0.70)

else:
    recommendation = "HOLD"
    confidence     = 0.3
```

### 7.2 Risk Level

```
volatility = scan.volatility
debt_ratio = fund.debt_to_equity (if available)

Base risk from volatility:
    vol > 0.50: "HIGH"
    vol > 0.30: "MEDIUM"
    else:       "LOW"

Override to "HIGH" if debt_to_equity > 1.5
```

### 7.3 News Confidence (Rule-Based)

```
Default: 50 (moderate)

Based on sentiment data quality:
    mentions >= 10 AND sources >= 3:  nc = 80
    mentions >= 5  AND sources >= 2:  nc = 65
    mentions >= 2:                    nc = 50
    mentions < 2:                     nc = 30
    No sentiment data:                nc = 20

Modulates recommendation confidence:
    nc_factor = (nc - 50) / 500      # range: -0.06 to +0.06
    confidence += nc_factor           # clamped to [0.1, 0.95]
```

### 7.4 Conflict Resolution (Rule-Based)

Detects and describes conflicts between models:

| Conflict | Detection |
|----------|-----------|
| RSI vs overall signal | RSI bearish (< 35) vs BUY, or RSI bullish (> 65) vs SELL |
| Momentum vs Ichimoku | abs(momentum_score - ichimoku_score) > 30 |
| Sentiment vs signal | Positive forum (> 60) vs SELL, or negative (< 40) vs BUY |

### 7.5 Narrative Generation

```
parts = [
    f"{name}: Composite {score}/100 ({direction})",
    f"Key drivers: {top 3 signal reasons from scanner}",
]
if fund:
    parts.append(f"Fundamental score {fund_score}/100")
    if pe: parts.append(f"(P/E: {pe})")
    if div: parts.append(f"Div yield: {div}%")
```

---

## 8. Fundamental Analysis Composite

### 8.1 Data Source

Yahoo Finance via `yfinance` library. Refreshed every 6 hours in a background thread.

### 8.2 Scoring Components

| Component | Weight | Scoring Tiers |
|-----------|--------|---------------|
| **Revenue Growth** | 20% | >30%=90, >15%=75, >5%=60, >0%=50, >-5%=40, >-15%=25, else=10 |
| **Profit Margin** | 15% | >25%=90, >15%=75, >8%=60, >3%=50, >0%=40, >-5%=25, else=10 |
| **ROE** | 15% | >25%=90, >15%=75, >10%=60, >5%=50, >0%=35, else=15 |
| **Debt/Equity** | 15% | <0.2=90, <0.5=75, <1.0=60, <1.5=45, <2.5=30, else=10 |
| **P/E Ratio** | 15% | <5=40(trap), <10=75, <15=85(optimal), <20=70, <30=50, <50=30, else=15 |
| **FCF Yield** | 10% | >8%=90, >5%=75, >2%=60, >0%=50, >-2%=35, else=15 |
| **Dividend Yield** | 10% | >6%=85, >4%=75, >2%=65, >0%=55, 0=40 |

### 8.3 Composite Formula

```
If no components available: score = 50 (neutral)

Otherwise:
    total_weight = sum of available component weights
    weighted_sum = sum(component_score * component_weight)
    composite    = weighted_sum / total_weight
    final_score  = clip(composite, 0, 100)
```

Note: If only 4 of 7 components have data, weights are re-normalized so they sum to 1.0.

### 8.4 Dividend Detail Fields

| Field | Source | Description |
|-------|--------|-------------|
| `last_dividend_value` | `tk.dividends[-1]` | Most recent dividend per share (MYR) |
| `last_dividend_date` | `tk.dividends.index[-1]` | Date of last payment |
| `ex_dividend_date` | `info["exDividendDate"]` | Next/last ex-dividend date |
| `dividend_frequency` | Inferred from payment gaps | Quarterly / Semi-Annual / Annual / Irregular |
| `trailing_annual_dividend` | `info["trailingAnnualDividendRate"]` | Trailing 12-month dividend |
| `payout_ratio` | `info["payoutRatio"]` | Earnings paid as dividends |

**Frequency Inference:**
```
Using last 2 years of dividend payments:
    avg_gap_days between payments:
        < 120 days:  "Quarterly"
        < 240 days:  "Semi-Annual"
        else:        "Annual"
    < 2 payments in 2 years: "Irregular"
```

---

## 9. Frontend Integration

### 9.1 Search Bar

- Positioned below header, above portfolio cards
- Glass container with text input + clear button + "Analyze" button
- Autocomplete dropdown (max 12 results)
- Fuzzy matching on stock key, name, ticker, sector
- Config-seeded on page load (all 144 stocks available instantly)
- Upgraded with scanner data (prices, scores) after first scan cycle

### 9.2 AI Analysis Panel

Slides open below search bar on stock selection. Sections:

1. **Header**: Stock name/ticker/price + recommendation badge (color-coded) + confidence % + risk pill
2. **Narrative**: AI explanation paragraph (2-3 sentences)
3. **News Confidence**: Bar indicator (0-100) with label
4. **Conflict Resolution**: If conflicts detected, resolution text displayed
5. **Metrics Grid**: Signal Score, Fund Score, RSI, Sentiment, Ichimoku, Pattern, P/E, Div Yield
6. **Price Targets**: Buy/Hold/Sell zones + predicted price + support/resistance
7. **Source Footer**: "Claude Sonnet AI" or "Rule-Based" indicator + cache timestamp

### 9.3 Recommendation Badge Colors

| Recommendation | Color |
|---------------|-------|
| BUY | Green (#22c55e) |
| SELL | Red (#ef4444) |
| HOLD | Grey (text-secondary) |
| TRADE | Blue (#3b82f6) |

---

## 10. Complete Data Flow

```
Page Load
    |
    +-> GET /api/config -> seed searchStockList (144 stocks, instant)
    |
    +-> GET /api/scanner -> upgrade searchStockList with prices/scores
    |
User types in search bar
    |
    +-> fuzzyMatch() -> render dropdown (max 12)
    |
User clicks stock
    |
    +-> GET /api/ai-analysis/{stock_key}
            |
            +-> Cache hit? -> return cached (< 5 min old)
            |
            +-> Gather 5 data sources (in-memory)
            |
            +-> API key exists?
            |       |
            |    YES: Build prompt -> Claude Sonnet -> Parse response
            |    NO:  Rule-based analysis
            |
            +-> Cache result (5 min TTL)
            |
            +-> Return JSON
                    |
                    v
            Frontend renders analysis panel
                - Recommendation badge
                - Narrative text
                - Metrics grid
                - Price targets
                - Source indicator
```

---

## 11. API Response Schema

```json
{
    "stock_key": "MAYBANK",
    "name": "Malayan Banking",
    "ticker": "1155.KL",
    "sector": "Finance",
    "ai_source": "claude_sonnet",
    "recommendation": "BUY",
    "confidence": 0.78,
    "risk_level": "LOW",
    "news_confidence": 72,
    "conflict_resolution": "RSI is neutral at 48, not in conflict...",
    "narrative": "Maybank shows strong bullish momentum with...",
    "timestamp": 1712764800,

    "price": 10.52,
    "score": 72,
    "direction": "BUY",
    "edge": 0.065,
    "rsi": 48.2,
    "momentum_score": 68,
    "rsi_score": 52,
    "vwap_score": 61,
    "ema_score": 65,
    "volume_score": 55,
    "vol_price_score": 71,
    "sentiment_score": 62,
    "ichimoku_score": 75,
    "pattern_score": 58,

    "fundamental_score": 71,
    "pe_ratio": 12.3,
    "dividend_yield": 0.052,
    "roe": 0.11,
    "profit_margin": 0.35,

    "price_targets": {
        "buy_target": 10.20,
        "sell_target": 10.85,
        "buy_strong": 9.95,
        "sell_strong": 11.10,
        "hold_low": 10.36,
        "hold_high": 10.69,
        "predicted_direction": "UP",
        "predicted_move_pct": 0.012,
        "predicted_price": 10.65,
        "support_1": 10.15,
        "support_2": 9.88,
        "resistance_1": 10.78,
        "resistance_2": 11.05
    }
}
```
