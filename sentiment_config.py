"""
Sentiment Analysis Configuration
Forum sources, keyword dictionaries, and scraping parameters.
"""

# ============================================================
# MASTER TOGGLE
# ============================================================
SENTIMENT_ENABLED = True
SENTIMENT_SCRAPE_INTERVAL = 600  # 10 minutes between full scrape cycles

# ============================================================
# FORUM SOURCES
# ============================================================
FORUM_SOURCES = {
    "klsescreener": {
        "enabled": True,
        "base_url": "https://www.klsescreener.com",
        "discussion_url": "/v2/discussion/index/{page}",
        "stocks_api": "/v2/stocks/all.json",
        "max_pages": 3,
        "rate_limit": 5.0,
    },
    "i3investor": {
        "enabled": True,
        "base_url": "https://klse.i3investor.com",
        "discussion_url": "/web/blog/stock-market-pair",
        "rate_limit": 5.0,
    },
    "reddit_bursa": {
        "enabled": True,
        "url": "https://www.reddit.com/r/Bursa_Malaysia/new.json?limit=25",
        "rate_limit": 2.0,
    },
    "reddit_mypf": {
        "enabled": True,
        "url": "https://www.reddit.com/r/MalaysianPF/new.json?limit=25",
        "rate_limit": 2.0,
    },
    "malaysiastockbiz": {
        "enabled": True,
        "base_url": "https://www.malaysiastock.biz",
        "forum_url": "/Forum/Main.aspx",
        "rate_limit": 5.0,
    },
    "lowyat": {
        "enabled": True,
        "base_url": "https://forum.lowyat.net",
        "forum_url": "/StockExchange",
        "max_pages": 2,
        "rate_limit": 5.0,
    },
    "investing_com": {
        "enabled": False,  # Returns 403
        "url": "https://www.investing.com/equities/bursa-malaysia-bhd-commentary",
    },
    "tapatalk_fortuneclub": {
        "enabled": False,  # Unstructured
        "url": "https://www.tapatalk.com/groups/fortuneclub/",
    },
}

# ============================================================
# SENTIMENT SIGNAL INTEGRATION
# ============================================================
SENTIMENT_WEIGHT = 0.10  # 10% of composite signal score

# Weights WITH sentiment (7 sub-scores, total = 1.00)
WEIGHTS_WITH_SENTIMENT = {
    "momentum": 0.18,
    "rsi": 0.13,
    "vwap": 0.13,
    "ema": 0.13,
    "volume": 0.09,
    "vol_price": 0.24,
    "sentiment": 0.10,
}

# Weights WITHOUT sentiment (original 6 sub-scores, total = 1.00)
WEIGHTS_WITHOUT_SENTIMENT = {
    "momentum": 0.20,
    "rsi": 0.15,
    "vwap": 0.15,
    "ema": 0.15,
    "volume": 0.10,
    "vol_price": 0.25,
}

# ============================================================
# SENTIMENT SCORING PARAMETERS
# ============================================================
SENTIMENT_PARAMS = {
    "min_mentions": 2,          # minimum mentions to generate a sentiment score
    "decay_hours": 48,          # posts older than this get reduced weight
    "buzz_threshold": 10,       # mentions above this = high buzz
    "strong_sentiment": 0.5,    # raw score above this = strong sentiment
    "cache_ttl": 600,           # 10 minutes cache per scraper
}

# ============================================================
# KEYWORD DICTIONARIES — Weighted sentiment keywords
# ============================================================

# English bullish keywords (word -> weight)
BULLISH_EN = {
    "buy": 1.0, "bullish": 1.5, "breakout": 1.2, "accumulate": 1.0,
    "undervalued": 1.0, "strong": 0.5, "long": 0.8, "support": 0.5,
    "rally": 1.0, "uptrend": 1.0, "upgrade": 1.2,
    "dividend": 0.5, "growth": 0.5, "profit": 0.5,
    "oversold": 0.8, "recovery": 0.8, "golden cross": 1.5,
    "breakout": 1.2, "all time high": 0.8, "bottom": 0.6,
    "bounce": 0.8, "upside": 0.8, "momentum": 0.5,
    "accumulation": 1.0, "value play": 0.8,
}

# English bearish keywords
BEARISH_EN = {
    "sell": 1.0, "bearish": 1.5, "breakdown": 1.2, "overvalued": 1.0,
    "weak": 0.5, "short": 0.8, "resistance": 0.5, "crash": 1.5,
    "downtrend": 1.0, "cut loss": 1.2, "downgrade": 1.2,
    "overbought": 0.8, "loss": 0.5, "debt": 0.5, "death cross": 1.5,
    "drop": 0.8, "dump": 1.0, "warning": 0.8,
    "distribution": 0.8, "top out": 0.8, "decline": 0.8,
    "risky": 0.5, "danger": 0.8, "avoid": 1.0,
}

# Malay bullish keywords
BULLISH_MS = {
    "beli": 1.0, "naik": 0.8, "untung": 0.8, "bagus": 0.5,
    "kuat": 0.5, "terbang": 1.0, "goreng": 0.5,
    "masuk": 0.8, "saham padu": 1.0, "target": 0.5,
    "murah": 0.6, "potensi": 0.5, "mantap": 0.8,
}

# Malay bearish keywords
BEARISH_MS = {
    "jual": 1.0, "turun": 0.8, "rugi": 0.8, "lemah": 0.5,
    "potong": 1.0, "keluar": 0.8, "bahaya": 1.0, "jatuh": 1.0,
    "merosot": 0.8, "risiko": 0.5, "elak": 0.8,
}

# ============================================================
# EVENT DETECTION — Company-specific catalysts from social media
# ============================================================
# Events that could cause significant price movement
# Each event type has keywords (EN + MS) and an impact direction/magnitude

EVENT_KEYWORDS = {
    "new_contract": {
        "keywords": [
            "new contract", "awarded contract", "awarded new", "won contract", "secured contract",
            "contract win", "project award", "new project", "landed deal",
            "kontrak baru", "dapat kontrak", "projek baru", "menang tender",
            "letter of award", "LOA", "awarded by", "mou signed", "joint venture",
            "partnership", "collaboration", "strategic alliance",
        ],
        "impact": "bullish",
        "weight": 2.0,
    },
    "contract_loss": {
        "keywords": [
            "lost contract", "contract terminated", "contract cancelled",
            "project cancelled", "deal fell through", "kontrak batal",
            "terminated", "cancelled order", "order cancellation",
        ],
        "impact": "bearish",
        "weight": 2.0,
    },
    "legal_issue": {
        "keywords": [
            "lawsuit", "sued", "legal action", "court case", "investigation",
            "penalty", "fine", "charged", "fraud", "scandal", "corruption",
            "saman", "mahkamah", "siasatan", "denda", "kes jenayah",
            "MACC", "SEC", "regulatory action", "compliance issue",
            "class action", "injunction", "probe", "whistleblower",
        ],
        "impact": "bearish",
        "weight": 2.5,
    },
    "earnings_positive": {
        "keywords": [
            "record profit", "beat estimates", "exceeded expectations",
            "strong earnings", "revenue up", "profit surge", "revenue growth",
            "earnings beat", "above consensus", "untung besar", "hasil rekod",
            "dividend increase", "special dividend", "bonus issue",
            "margin expansion", "EPS beat",
        ],
        "impact": "bullish",
        "weight": 2.0,
    },
    "earnings_negative": {
        "keywords": [
            "profit warning", "missed estimates", "below expectations",
            "revenue down", "loss reported", "earnings miss", "profit drop",
            "revenue decline", "margin compression", "rugi", "untung turun",
            "dividend cut", "no dividend", "write-off", "impairment",
        ],
        "impact": "bearish",
        "weight": 2.0,
    },
    "management_change": {
        "keywords": [
            "new CEO", "CEO resign", "CEO appointed", "board reshuffle",
            "management change", "CFO resign", "new chairman",
            "CEO keluar", "pengarah baru", "lantik CEO",
            "succession", "interim CEO", "fired CEO",
        ],
        "impact": "neutral",  # could go either way
        "weight": 1.5,
    },
    "merger_acquisition": {
        "keywords": [
            "acquisition", "takeover", "merger", "buyout", "privatisation",
            "tender offer", "bid for", "acquired", "acquire stake",
            "pengambilalihan", "gabung", "beli syarikat",
            "general offer", "mandatory offer", "RTO",
        ],
        "impact": "bullish",
        "weight": 2.5,
    },
    "regulatory": {
        "keywords": [
            "new regulation", "policy change", "government contract",
            "subsidy", "tax incentive", "approved by", "license granted",
            "permit approved", "kelulusan", "lesen diluluskan",
            "tariff", "quota", "sanctions", "banned", "restriction",
        ],
        "impact": "neutral",
        "weight": 1.5,
    },
    "analyst_upgrade": {
        "keywords": [
            "upgrade", "target price raised", "outperform",
            "strong buy", "top pick", "overweight",
            "naik target", "recommended", "initiating coverage",
        ],
        "impact": "bullish",
        "weight": 1.5,
    },
    "analyst_downgrade": {
        "keywords": [
            "downgrade", "target price cut", "underperform",
            "sell rating", "underweight", "turun target",
            "reduce", "not recommended", "drop coverage",
        ],
        "impact": "bearish",
        "weight": 1.5,
    },
}

# ============================================================
# PERSISTENCE
# ============================================================
SENTIMENT_CACHE_FILE = "sentiment_cache.json"
