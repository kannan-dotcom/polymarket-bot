"""
Configuration for Multi-Exchange Stock Scanner & Trading Bot
Exchanges: Bursa Malaysia (KLSE), SGX Singapore, DFM Dubai
Data Feed: Yahoo Finance (yfinance)
"""

# ============================================================
# CAPITAL & RISK MANAGEMENT
# ============================================================
STARTING_CAPITAL = 100.00          # USD starting bankroll
MAX_POSITION_PCT = 0.05            # Max 5% of bankroll per trade
MAX_DAILY_LOSS_PCT = 0.10          # Stop trading after 10% daily drawdown
MAX_CONCURRENT_POSITIONS = 5       # Max simultaneous open positions
MIN_TRADE_SIZE = 5.00              # Minimum trade size in USD
MAX_TRADE_SIZE = 20.00             # Maximum trade size in USD
KELLY_FRACTION = 0.25              # Quarter-Kelly for conservative sizing

# ============================================================
# EXCHANGE DEFINITIONS
# ============================================================
EXCHANGES = {
    "KLSE": {
        "name": "Bursa Malaysia",
        "currency": "MYR",
        "suffix": ".KL",
        "timezone": "Asia/Kuala_Lumpur",
        "trading_hours": {"open": "09:00", "close": "17:00"},
    },
    "SGX": {
        "name": "Singapore Exchange",
        "currency": "SGD",
        "suffix": ".SI",
        "timezone": "Asia/Singapore",
        "trading_hours": {"open": "09:00", "close": "17:00"},
    },
    "DFM": {
        "name": "Dubai Financial Market",
        "currency": "AED",
        "suffix": ".AE",
        "timezone": "Asia/Dubai",
        "trading_hours": {"open": "10:00", "close": "14:00"},
    },
}

# ============================================================
# STOCK UNIVERSE — Verified tickers on Yahoo Finance
# ============================================================
STOCKS = {
    # --- Bursa Malaysia (KLSE) ---
    "MAYBANK": {
        "ticker": "1155.KL", "name": "Malayan Banking",
        "exchange": "KLSE", "sector": "Finance", "enabled": True,
    },
    "PUBBANK": {
        "ticker": "1295.KL", "name": "Public Bank",
        "exchange": "KLSE", "sector": "Finance", "enabled": True,
    },
    "PCHEM": {
        "ticker": "5183.KL", "name": "Petronas Chemicals",
        "exchange": "KLSE", "sector": "Energy", "enabled": True,
    },
    "CIMB": {
        "ticker": "1023.KL", "name": "CIMB Group",
        "exchange": "KLSE", "sector": "Finance", "enabled": True,
    },
    "TM": {
        "ticker": "4863.KL", "name": "Telekom Malaysia",
        "exchange": "KLSE", "sector": "Telecom", "enabled": True,
    },
    "GENTING": {
        "ticker": "3182.KL", "name": "Genting Berhad",
        "exchange": "KLSE", "sector": "Consumer", "enabled": True,
    },
    "TENAGA": {
        "ticker": "5347.KL", "name": "Tenaga Nasional",
        "exchange": "KLSE", "sector": "Utilities", "enabled": True,
    },
    "MAXIS": {
        "ticker": "6012.KL", "name": "Maxis Berhad",
        "exchange": "KLSE", "sector": "Telecom", "enabled": True,
    },
    "YTL": {
        "ticker": "4677.KL", "name": "YTL Corporation",
        "exchange": "KLSE", "sector": "Conglomerate", "enabled": True,
    },
    # --- Expanded KLSE stocks ---
    "TOPGLOV": {
        "ticker": "7113.KL", "name": "Top Glove",
        "exchange": "KLSE", "sector": "Healthcare", "enabled": True,
    },
    "HARTA": {
        "ticker": "5168.KL", "name": "Hartalega",
        "exchange": "KLSE", "sector": "Healthcare", "enabled": True,
    },
    "IHH": {
        "ticker": "5225.KL", "name": "IHH Healthcare",
        "exchange": "KLSE", "sector": "Healthcare", "enabled": True,
    },
    "AXIATA": {
        "ticker": "6888.KL", "name": "Axiata Group",
        "exchange": "KLSE", "sector": "Telecom", "enabled": True,
    },
    "DIALOG": {
        "ticker": "7277.KL", "name": "Dialog Group",
        "exchange": "KLSE", "sector": "Energy", "enabled": True,
    },
    "PETDAG": {
        "ticker": "5681.KL", "name": "Petronas Dagangan",
        "exchange": "KLSE", "sector": "Energy", "enabled": True,
    },
    "HLBANK": {
        "ticker": "5819.KL", "name": "Hong Leong Bank",
        "exchange": "KLSE", "sector": "Finance", "enabled": True,
    },
    "PRESS": {
        "ticker": "8869.KL", "name": "Press Metal",
        "exchange": "KLSE", "sector": "Industrial", "enabled": True,
    },
    "MRDIY": {
        "ticker": "5296.KL", "name": "Mr DIY Group",
        "exchange": "KLSE", "sector": "Consumer", "enabled": True,
    },
    "INARI": {
        "ticker": "0166.KL", "name": "Inari Amertron",
        "exchange": "KLSE", "sector": "Technology", "enabled": True,
    },
    "SUNWAY": {
        "ticker": "5211.KL", "name": "Sunway Berhad",
        "exchange": "KLSE", "sector": "Conglomerate", "enabled": True,
    },
    "GAMUDA": {
        "ticker": "5398.KL", "name": "Gamuda Berhad",
        "exchange": "KLSE", "sector": "Construction", "enabled": True,
    },
    "QL": {
        "ticker": "7084.KL", "name": "QL Resources",
        "exchange": "KLSE", "sector": "Consumer", "enabled": True,
    },
    "NESTLE": {
        "ticker": "4707.KL", "name": "Nestle Malaysia",
        "exchange": "KLSE", "sector": "Consumer", "enabled": True,
    },
    "PPB": {
        "ticker": "4065.KL", "name": "PPB Group",
        "exchange": "KLSE", "sector": "Conglomerate", "enabled": True,
    },
    "RHB": {
        "ticker": "1066.KL", "name": "RHB Bank",
        "exchange": "KLSE", "sector": "Finance", "enabled": True,
    },
    "SDG": {
        "ticker": "5285.KL", "name": "SD Guthrie",
        "exchange": "KLSE", "sector": "Plantation", "enabled": True,
    },
    "MISC": {
        "ticker": "3816.KL", "name": "MISC Berhad",
        "exchange": "KLSE", "sector": "Transport", "enabled": True,
    },
    "KLCC": {
        "ticker": "5235SS.KL", "name": "KLCCP Stapled",
        "exchange": "KLSE", "sector": "REIT", "enabled": True,
    },
    "AMBANK": {
        "ticker": "1015.KL", "name": "AMMB Holdings",
        "exchange": "KLSE", "sector": "Finance", "enabled": True,
    },

    # --- Singapore Exchange (SGX) ---
    "DBS": {
        "ticker": "D05.SI", "name": "DBS Group",
        "exchange": "SGX", "sector": "Finance", "enabled": False,
    },
    "OCBC": {
        "ticker": "O39.SI", "name": "OCBC Bank",
        "exchange": "SGX", "sector": "Finance", "enabled": False,
    },
    "SINGTEL": {
        "ticker": "Z74.SI", "name": "Singapore Telecom",
        "exchange": "SGX", "sector": "Telecom", "enabled": False,
    },
    "UOB": {
        "ticker": "U11.SI", "name": "United Overseas Bank",
        "exchange": "SGX", "sector": "Finance", "enabled": False,
    },
    "KEPPEL": {
        "ticker": "BN4.SI", "name": "Keppel Corporation",
        "exchange": "SGX", "sector": "Industrial", "enabled": False,
    },
    "SIA": {
        "ticker": "C6L.SI", "name": "Singapore Airlines",
        "exchange": "SGX", "sector": "Transport", "enabled": False,
    },
    "ASCENDAS": {
        "ticker": "A17U.SI", "name": "Ascendas REIT",
        "exchange": "SGX", "sector": "REIT", "enabled": False,
    },
    "VENTURE": {
        "ticker": "V03.SI", "name": "Venture Corporation",
        "exchange": "SGX", "sector": "Technology", "enabled": False,
    },
    "THAIBEV": {
        "ticker": "Y92.SI", "name": "Thai Beverage",
        "exchange": "SGX", "sector": "Consumer", "enabled": False,
    },
    "SATS": {
        "ticker": "S58.SI", "name": "SATS Ltd",
        "exchange": "SGX", "sector": "Industrial", "enabled": False,
    },

    # --- Dubai Financial Market (DFM) ---
    "EMAAR": {
        "ticker": "EMAAR.AE", "name": "Emaar Properties",
        "exchange": "DFM", "sector": "Real Estate", "enabled": False,
    },
    "DIB": {
        "ticker": "DIB.AE", "name": "Dubai Islamic Bank",
        "exchange": "DFM", "sector": "Finance", "enabled": False,
    },
    "DFMGI": {
        "ticker": "DFM.AE", "name": "Dubai Financial Market",
        "exchange": "DFM", "sector": "Finance", "enabled": False,
    },
    "EMAARDEV": {
        "ticker": "EMAARDEV.AE", "name": "Emaar Development",
        "exchange": "DFM", "sector": "Real Estate", "enabled": False,
    },
    "DEWA": {
        "ticker": "DEWA.AE", "name": "DEWA",
        "exchange": "DFM", "sector": "Utilities", "enabled": False,
    },
    "SALIK": {
        "ticker": "SALIK.AE", "name": "Salik Company",
        "exchange": "DFM", "sector": "Transport", "enabled": False,
    },
    "GFH": {
        "ticker": "GFH.AE", "name": "GFH Financial Group",
        "exchange": "DFM", "sector": "Finance", "enabled": False,
    },
    "PARKIN": {
        "ticker": "PARKIN.AE", "name": "Parkin Company",
        "exchange": "DFM", "sector": "Transport", "enabled": False,
    },
    "TECOM": {
        "ticker": "TECOM.AE", "name": "TECOM Group",
        "exchange": "DFM", "sector": "Real Estate", "enabled": False,
    },
}

# ============================================================
# SIGNAL ENGINE PARAMETERS (calibrated for daily stock data)
# ============================================================
SIGNAL = {
    # Momentum (daily price direction)
    "momentum_window": 10,           # number of days for momentum calc
    "momentum_threshold": 0.02,      # 2% move threshold

    # Volatility filter
    "volatility_window": 20,         # days for volatility calc
    "high_vol_multiplier": 1.5,
    "low_vol_multiplier": 0.5,

    # RSI
    "rsi_period": 14,
    "rsi_overbought": 70,
    "rsi_oversold": 30,

    # VWAP deviation
    "vwap_deviation_threshold": 0.01,  # 1% deviation from VWAP

    # Signal scoring thresholds
    "buy_threshold": 60,             # score >= 60 = BUY signal
    "sell_threshold": 40,            # score <= 40 = SELL signal
    "strong_signal_threshold": 75,   # score >= 75 or <= 25 = strong signal

    # Edge thresholds for Kelly sizing
    "edge_threshold": 0.03,          # minimum 3% expected edge
    "strong_edge_threshold": 0.08,   # 8%+ edge = increase size
    "min_confidence": 0.10,          # minimum confidence to trade

    # Volume spike detection
    "volume_spike_multiplier": 2.0,  # volume > 2x average = spike
}

# ============================================================
# YAHOO FINANCE SETTINGS
# ============================================================
YFINANCE_PERIOD = "3mo"             # historical data lookback
YFINANCE_INTERVAL = "1d"            # daily candles

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
POLL_INTERVAL_SECONDS = 300         # scan every 5 minutes
SCAN_INTERVAL_HOURS = 1             # full scan every hour in loop mode

# ============================================================
# SENTIMENT ANALYSIS
# ============================================================
SENTIMENT_ENABLED = True            # Enable forum sentiment scraping
