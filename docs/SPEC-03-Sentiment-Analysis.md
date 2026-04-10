# SPEC 03 — Sentiment Analysis & NLP Pipeline

**Product**: MY Stock Market Trading Platform
**Modules**: `sentiment_scraper.py`, `sentiment_config.py`, `stock_aliases.py`
**Version**: 1.0 | April 2026

---

## 1. Purpose

The Sentiment Pipeline scrapes Malaysian stock forums and news sites every 10 minutes, extracts stock mentions, scores sentiment using both keyword dictionaries and LLM classification (Claude Sonnet), detects company events/catalysts, and feeds a time-decay-weighted sentiment score into the Signal Engine as one of 9 sub-signals.

---

## 2. Architecture Overview

```
                    +----------------------------+
                    |    Forum/News Sources (8)   |
                    |  KLSE Screener | i3investor  |
                    |  Reddit (2)   | Lowyat      |
                    |  MalaysiaStock| TheEdge     |
                    |  TheStar      |             |
                    +----------+---+-------------+
                               |
                    (every 10 min, rate-limited)
                               |
                               v
                    +----------------------------+
                    |    ForumPost Extraction     |
                    |  - HTML parsing (BS4)       |
                    |  - JSON API (Reddit)        |
                    |  - Rate limiting per source  |
                    +----------+-----------------+
                               |
                    +----------v-----------------+
                    |    Stock Mention Detection  |
                    |  - Alias map (name, ticker, |
                    |    code, sector keywords)    |
                    |  - Longest-match-first       |
                    |  - Word boundary for short   |
                    +----------+-----------------+
                               |
               +---------------+---------------+
               |                               |
               v                               v
    +-------------------+           +-------------------+
    | Keyword Scoring   |           | LLM Classification|
    | - EN bullish (24) |           | - Claude Sonnet   |
    | - EN bearish (24) |           | - Batch of 5 posts|
    | - MS bullish (13) |           | - POSITIVE/NEG/   |
    | - MS bearish (11) |           |   NOISE + conf    |
    | - Weighted sum    |           | - 20 calls/cycle  |
    +--------+----------+           +--------+----------+
             |                               |
             +---------- BLEND -------------+
             |                               |
             v                               |
    +-------------------+                    |
    | Time-Decay        |<-------------------+
    | Weighted Agg      |
    | - 10-day window   |
    | - Exponential     |
    |   decay           |
    | - Min 2 mentions  |
    +--------+----------+
             |
             v
    +-------------------+
    | StockSentiment    |
    | - score (0-100)   |
    | - buzz_score      |
    | - mention_trend   |
    | - events[]        |
    | - llm_consensus   |
    +-------------------+
             |
             v
       Signal Engine
       (8% weight)
```

---

## 3. Data Sources

| Source | Type | Rate Limit | Max Pages |
|--------|------|------------|-----------|
| KLSE Screener | HTML scrape + JSON API | 5s | 3 |
| i3investor | HTML scrape | 5s | 1 |
| Reddit r/Bursa_Malaysia | JSON API | 2s | 25 posts |
| Reddit r/MalaysianPF | JSON API | 2s | 25 posts |
| MalaysiaStock.Biz | HTML scrape | 5s | 1 |
| Lowyat Forum | HTML scrape | 5s | 2 |
| The Edge Malaysia | HTML scrape | 5s | 1 |
| The Star Business | HTML scrape | 5s | 1 |

Scrape interval: **600 seconds** (10 minutes)
Post retention window: **240 hours** (10 days)

---

## 4. Stock Mention Detection

The `stock_aliases.py` module builds a reverse map from all known aliases to stock keys:

- Stock key (e.g., "MAYBANK")
- Full name (e.g., "Malayan Banking")
- Yahoo Finance ticker (e.g., "1155.KL")
- Stock code (e.g., "1155")
- Common abbreviations

**Matching rules:**
- Aliases sorted longest-first (greedy matching)
- Short aliases (length <= 2): require word boundary (`\b` regex)
- Longer aliases: simple substring match in lowercased text

---

## 5. Keyword-Based Sentiment Scoring

### 5.1 Dictionary Structure

**English Bullish (24 keywords):**

| Keyword | Weight | Keyword | Weight |
|---------|--------|---------|--------|
| buy | 1.0 | bullish | 1.5 |
| breakout | 1.2 | accumulate | 1.0 |
| undervalued | 1.0 | strong | 0.5 |
| long | 0.8 | support | 0.5 |
| rally | 1.0 | uptrend | 1.0 |
| upgrade | 1.2 | dividend | 0.5 |
| growth | 0.5 | profit | 0.5 |
| oversold | 0.8 | recovery | 0.8 |
| golden cross | 1.5 | all time high | 0.8 |
| bottom | 0.6 | bounce | 0.8 |
| upside | 0.8 | momentum | 0.5 |
| accumulation | 1.0 | value play | 0.8 |

**English Bearish (24 keywords):**

| Keyword | Weight | Keyword | Weight |
|---------|--------|---------|--------|
| sell | 1.0 | bearish | 1.5 |
| breakdown | 1.2 | overvalued | 1.0 |
| weak | 0.5 | short | 0.8 |
| resistance | 0.5 | crash | 1.5 |
| downtrend | 1.0 | cut loss | 1.2 |
| downgrade | 1.2 | overbought | 0.8 |
| loss | 0.5 | debt | 0.5 |
| death cross | 1.5 | drop | 0.8 |
| dump | 1.0 | warning | 0.8 |
| distribution | 0.8 | top out | 0.8 |
| decline | 0.8 | risky | 0.5 |
| danger | 0.8 | avoid | 1.0 |

**Malay Bullish (13 keywords):** beli(1.0), naik(0.8), untung(0.8), bagus(0.5), kuat(0.5), terbang(1.0), goreng(0.5), masuk(0.8), saham padu(1.0), target(0.5), murah(0.6), potensi(0.5), mantap(0.8)

**Malay Bearish (11 keywords):** jual(1.0), turun(0.8), rugi(0.8), lemah(0.5), potong(1.0), keluar(0.8), bahaya(1.0), jatuh(1.0), merosot(0.8), risiko(0.5), elak(0.8)

### 5.2 Scoring Formula

```
For each post:
    bullish_sum = sum(weight for each bullish keyword found in text)
    bearish_sum = sum(weight for each bearish keyword found in text)
    total       = bullish_sum + bearish_sum

    if total == 0: raw_score = 0.0
    else:          raw_score = (bullish_sum - bearish_sum) / total
                   # range: -1.0 (fully bearish) to +1.0 (fully bullish)
```

---

## 6. LLM Classification (Claude Sonnet)

### 6.1 Configuration

| Parameter | Value |
|-----------|-------|
| Model | `claude-sonnet-4-20250514` |
| Max Tokens | 150 |
| Temperature | 0.0 (deterministic) |
| Batch Size | 5 posts per API call |
| Max Calls per Cycle | 20 |
| API Timeout | 10 seconds |
| Min Text Length | 20 characters |
| Cache TTL | 3600 seconds (1 hour) |
| Daily Cost Cap | $2.00 USD |
| Fallback on Error | Yes (keyword scoring) |

### 6.2 Prompt Template

The LLM receives batched posts with this system prompt:

```
You are a Malaysian stock market sentiment classifier.
Analyze these forum posts and classify each as POSITIVE, NEGATIVE, or NOISE.

Context: Posts from Malaysian stock forums (Bursa Malaysia / KLSE).
May contain English, Malay (Bahasa Malaysia), or mixed language.
Stock codes like "7113" or names like "TOPGLOV" refer to KLSE-listed companies.

Rules:
- POSITIVE: Bullish sentiment, good news, buy recommendation, upward catalysts
- NEGATIVE: Bearish sentiment, bad news, sell recommendation, downward catalysts
- NOISE: Neutral, off-topic, questions without sentiment, too vague

Response format per post:
<index>|<label>|<confidence>|<reason>
```

### 6.3 LLM Aggregation

For each stock, after classification:

```
llm_positive_pct = count(POSITIVE) / classified_count * 100
llm_negative_pct = count(NEGATIVE) / classified_count * 100
llm_noise_pct    = count(NOISE) / classified_count * 100

Consensus:
    if positive_pct > 50%:  "POSITIVE"
    if negative_pct > 50%:  "NEGATIVE"
    if noise_pct > 60%:     "NOISE"
    else:                   "MIXED"
```

---

## 7. Time-Decay Weighted Aggregation

### 7.1 Parameters

| Parameter | Value |
|-----------|-------|
| Decay Window | 240 hours (10 days) |
| Min Mentions | 2 (below this, no score generated) |
| Buzz Threshold | 10 mentions = high buzz |
| Strong Sentiment | raw score > 0.5 |

### 7.2 Decay Formula

Posts older than 10 days are discarded. Within the window:

```
For each post with age_hours:
    decay_weight = exp(-age_hours / decay_hours)
    # 0 hours  -> weight 1.00
    # 24 hours -> weight 0.90
    # 120 hours (5 days) -> weight 0.61
    # 240 hours (10 days) -> weight 0.37
```

### 7.3 Final Sentiment Score

```
weighted_sum   = sum(post_sentiment * decay_weight)
total_weight   = sum(decay_weight)
avg_sentiment  = weighted_sum / total_weight     # range: -1 to +1
sentiment_score = 50 + avg_sentiment * 50        # mapped to 0-100 scale
```

### 7.4 Buzz Score

```
Percentile-based across all stocks:
    buzz_score = percentile_rank(this_stock_mentions, all_stock_mentions) * 100
```

---

## 8. Event Detection

The system scans forum posts for company-specific catalysts using keyword dictionaries. Each event type has keywords (English + Malay) and a market impact classification.

### 8.1 Event Categories

| Event Type | Impact | Weight | Example Keywords |
|------------|--------|--------|-----------------|
| New Contract | Bullish | 2.0 | "new contract", "awarded", "kontrak baru", "LOA" |
| Contract Loss | Bearish | 2.0 | "lost contract", "terminated", "kontrak batal" |
| Legal Issue | Bearish | 2.5 | "lawsuit", "sued", "MACC", "fraud", "saman" |
| Earnings Positive | Bullish | 2.0 | "record profit", "beat estimates", "untung besar" |
| Earnings Negative | Bearish | 2.0 | "profit warning", "missed estimates", "rugi" |
| Management Change | Neutral | 1.5 | "new CEO", "CEO resign", "pengarah baru" |
| Merger/Acquisition | Bullish | 2.5 | "acquisition", "takeover", "general offer" |
| Regulatory | Neutral | 1.5 | "new regulation", "license granted", "tariff" |
| Analyst Upgrade | Bullish | 1.5 | "upgrade", "target price raised", "outperform" |
| Analyst Downgrade | Bearish | 1.5 | "downgrade", "target price cut", "underweight" |

### 8.2 Event Impact Score

```
event_impact = sum(event_weight * (+1 if bullish, -1 if bearish, 0 if neutral))
             / total_event_weights
             # range: -1.0 to +1.0

has_catalyst = True if any event with weight >= 2.0 detected
```

---

## 9. Data Flow: Scrape to Signal

```
10-minute cycle:
    For each source:
        1. HTTP request (rate-limited)
        2. Parse HTML/JSON -> ForumPost[]
        3. Extract stock mentions via alias map
        4. Keyword sentiment scoring
        5. Queue for LLM classification (batches of 5)

    LLM classification (if enabled + budget remaining):
        6. Batch posts -> Claude Sonnet API
        7. Parse response -> label + confidence + reason
        8. Blend with keyword score

    Aggregation per stock:
        9.  Filter posts within 10-day window
        10. Apply time-decay weights
        11. Compute weighted average sentiment
        12. Map to 0-100 scale
        13. Detect events from keywords
        14. Compute buzz score (percentile)
        15. Determine LLM consensus

    Output -> StockSentiment
        16. Stored in SentimentAggregator
        17. Consumed by Signal Engine (8% weight)
        18. Displayed on dashboard
        19. Fed to AI Analysis prompt
```

---

## 10. Integration with Signal Engine

The sentiment score enters the composite as one of 9 sub-signals:

- **Weight**: 8% (with sentiment) or 0% (without — other weights re-normalized)
- **Activation threshold**: `mention_count >= 2`
- **Score range**: 0-100 (same as other sub-signals)
- **Reason generation**: Bullish/bearish at thresholds of 65/35, buzz at 70

When sentiment data is unavailable for a stock (< 2 mentions), the system automatically switches to the 8-signal weight set where the other signals absorb the 8% redistribution.

---

## 11. LLM Cost Model

| Metric | Value |
|--------|-------|
| Model | Claude Sonnet |
| Input tokens per batch | ~200 tokens (5 posts) |
| Output tokens per batch | ~100 tokens |
| Cost per batch | ~$0.01 |
| Batches per cycle | up to 20 |
| Cycles per day | 144 (every 10 min) |
| Daily cost (max) | ~$28.80 (if all 20 batches every cycle) |
| Daily cost (typical) | ~$1-3 (most cycles use < 5 batches) |
| Daily cap | $2.00 USD |
| Cache hit rate | ~60-70% (1-hour LLM cache) |
