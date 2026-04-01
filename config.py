"""
Configuration for Polymarket HF Trading Bot
"""

# ============================================================
# CAPITAL & RISK MANAGEMENT
# ============================================================
STARTING_CAPITAL = 100.00          # USD starting bankroll
MAX_POSITION_PCT = 0.05            # Max 5% of bankroll per trade
MAX_DAILY_LOSS_PCT = 0.10          # Stop trading after 10% daily drawdown
MAX_CONCURRENT_POSITIONS = 3       # Max simultaneous open positions
MIN_TRADE_SIZE = 1.00              # Minimum trade size in USDC
MAX_TRADE_SIZE = 10.00             # Maximum trade size in USDC (cap for $100 bankroll)
KELLY_FRACTION = 0.25              # Quarter-Kelly for conservative sizing

# ============================================================
# MARKET SETTINGS
# ============================================================
MARKETS = {
    "BTC_5M": {
        "name": "Bitcoin 5-Minute",
        "symbol": "BTCUSDT",
        "interval": 5,              # minutes
        "exchange_feed": "binance",
        "polymarket_slug": "crypto/5M",
        "enabled": True,
    },
    "ETH_5M": {
        "name": "Ethereum 5-Minute",
        "symbol": "ETHUSDT",
        "interval": 5,
        "exchange_feed": "binance",
        "polymarket_slug": "crypto/5M",
        "enabled": True,
    },
    "XRP_5M": {
        "name": "XRP 5-Minute",
        "symbol": "XRPUSDT",
        "interval": 5,
        "exchange_feed": "binance",
        "polymarket_slug": "crypto/5M",
        "enabled": True,
    },
    "XLM_5M": {
        "name": "Stellar 5-Minute",
        "symbol": "XLMUSDT",
        "interval": 5,
        "exchange_feed": "binance",
        "polymarket_slug": "crypto/5M",
        "enabled": True,
    },
    "SPX_DAILY": {
        "name": "S&P 500 Daily Close",
        "symbol": "SPY",
        "interval": 1440,           # daily (minutes)
        "exchange_feed": "yahoo",
        "polymarket_slug": "stocks",
        "enabled": False,           # enable when market available
    },
}

# ============================================================
# SIGNAL ENGINE PARAMETERS
# ============================================================
SIGNAL = {
    # Momentum (short-term price direction)
    "momentum_window": 12,          # number of candles for momentum calc
    "momentum_threshold": 0.0015,   # 0.15% move threshold to trigger signal

    # Volatility filter
    "volatility_window": 20,        # candles for ATR/volatility calc
    "high_vol_multiplier": 1.5,     # skip trades when vol > 1.5x average
    "low_vol_multiplier": 0.5,      # skip trades when vol too low (no edge)

    # RSI
    "rsi_period": 14,
    "rsi_overbought": 70,
    "rsi_oversold": 30,

    # VWAP deviation
    "vwap_deviation_threshold": 0.002,  # 0.2% deviation from VWAP

    # Arbitrage: polymarket odds vs model probability
    "edge_threshold": 0.05,         # minimum 5% edge to enter trade
    "strong_edge_threshold": 0.10,  # 10%+ edge = increase size

    # Confidence scoring
    "min_confidence": 0.08,         # minimum model confidence to trade
}

# ============================================================
# EXCHANGE DATA FEED
# ============================================================
BINANCE_BASE_URL = "https://api.binance.com"
BINANCE_KLINES_ENDPOINT = "/api/v3/klines"
BINANCE_TICKER_ENDPOINT = "/api/v3/ticker/price"
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws"

# ============================================================
# POLYMARKET API
# ============================================================
POLYMARKET_CLOB_URL = "https://clob.polymarket.com"
POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com"
POLYMARKET_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

# API keys (set via environment variables)
POLYMARKET_API_KEY = ""            # Set in .env
POLYMARKET_API_SECRET = ""         # Set in .env
POLYMARKET_PASSPHRASE = ""         # Set in .env

# ============================================================
# LOGGING & PERSISTENCE
# ============================================================
LOG_FILE = "trades.log"
TRADE_HISTORY_FILE = "trade_history.json"
PORTFOLIO_FILE = "portfolio.json"
LOG_LEVEL = "INFO"

# ============================================================
# TIMING
# ============================================================
POLL_INTERVAL_SECONDS = 5          # how often to check for new rounds
PRE_ROUND_BUFFER_SECONDS = 30      # enter position this many secs before round start
POST_ROUND_COOLDOWN_SECONDS = 10   # wait after round settles before next
