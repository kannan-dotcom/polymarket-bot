"""
Configuration for MY Stock Market Trading Platform
Exchange: Bursa Malaysia (KLSE) — 129 stocks
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
}

# ============================================================
# STOCK UNIVERSE — 129 KLSE stocks, all verified on Yahoo Finance
# ============================================================
STOCKS = {
    # ── Finance (14) ─────────────────────────────────────────
    "ABMB": {"ticker": "2488.KL", "name": "Alliance Bank Malaysia", "exchange": "KLSE", "sector": "Finance", "enabled": True},
    "AEONCR": {"ticker": "5139.KL", "name": "AEON Credit Service", "exchange": "KLSE", "sector": "Finance", "enabled": True},
    "ALLIANZ": {"ticker": "1163.KL", "name": "Allianz Malaysia", "exchange": "KLSE", "sector": "Finance", "enabled": True},
    "AMBANK": {"ticker": "1015.KL", "name": "AMMB Holdings", "exchange": "KLSE", "sector": "Finance", "enabled": True},
    "BIMB": {"ticker": "5258.KL", "name": "Bank Islam Malaysia", "exchange": "KLSE", "sector": "Finance", "enabled": True},
    "BURSA": {"ticker": "1818.KL", "name": "Bursa Malaysia", "exchange": "KLSE", "sector": "Finance", "enabled": True},
    "CIMB": {"ticker": "1023.KL", "name": "CIMB Group", "exchange": "KLSE", "sector": "Finance", "enabled": True},
    "HLBANK": {"ticker": "5819.KL", "name": "Hong Leong Bank", "exchange": "KLSE", "sector": "Finance", "enabled": True},
    "HLFG": {"ticker": "1082.KL", "name": "Hong Leong Financial Group", "exchange": "KLSE", "sector": "Finance", "enabled": True},
    "LPI": {"ticker": "8621.KL", "name": "LPI Capital", "exchange": "KLSE", "sector": "Finance", "enabled": True},
    "MAYBANK": {"ticker": "1155.KL", "name": "Malayan Banking", "exchange": "KLSE", "sector": "Finance", "enabled": True},
    "OSK": {"ticker": "5053.KL", "name": "OSK Holdings", "exchange": "KLSE", "sector": "Finance", "enabled": True},
    "PBBANK": {"ticker": "1295.KL", "name": "Public Bank", "exchange": "KLSE", "sector": "Finance", "enabled": True},
    "RHBBANK": {"ticker": "1066.KL", "name": "RHB Bank", "exchange": "KLSE", "sector": "Finance", "enabled": True},

    # ── Energy (11) ──────────────────────────────────────────
    "ARMADA": {"ticker": "5210.KL", "name": "Bumi Armada", "exchange": "KLSE", "sector": "Energy", "enabled": True},
    "DAYANG": {"ticker": "5141.KL", "name": "Dayang Enterprise", "exchange": "KLSE", "sector": "Energy", "enabled": True},
    "DIALOG": {"ticker": "7277.KL", "name": "Dialog Group", "exchange": "KLSE", "sector": "Energy", "enabled": True},
    "ELRIDGE": {"ticker": "0318.KL", "name": "Elridge Energy", "exchange": "KLSE", "sector": "Energy", "enabled": True},
    "GASMSIA": {"ticker": "5209.KL", "name": "Gas Malaysia", "exchange": "KLSE", "sector": "Energy", "enabled": True},
    "HENGYUAN": {"ticker": "4324.KL", "name": "Hengyuan Refining", "exchange": "KLSE", "sector": "Energy", "enabled": True},
    "HIBISCS": {"ticker": "5199.KL", "name": "Hibiscus Petroleum", "exchange": "KLSE", "sector": "Energy", "enabled": True},
    "PCHEM": {"ticker": "5183.KL", "name": "Petronas Chemicals", "exchange": "KLSE", "sector": "Energy", "enabled": True},
    "PETDAG": {"ticker": "5681.KL", "name": "Petronas Dagangan", "exchange": "KLSE", "sector": "Energy", "enabled": True},
    "PETGAS": {"ticker": "6033.KL", "name": "Petronas Gas", "exchange": "KLSE", "sector": "Energy", "enabled": True},
    "YINSON": {"ticker": "7293.KL", "name": "Yinson Holdings", "exchange": "KLSE", "sector": "Energy", "enabled": True},

    # ── Utilities (7) ────────────────────────────────────────
    "CYPARK": {"ticker": "5184.KL", "name": "Cypark Resources", "exchange": "KLSE", "sector": "Utilities", "enabled": True},
    "MALAKOF": {"ticker": "5264.KL", "name": "Malakoff Corporation", "exchange": "KLSE", "sector": "Utilities", "enabled": True},
    "SAMAIDEN": {"ticker": "0223.KL", "name": "Samaiden Group", "exchange": "KLSE", "sector": "Utilities", "enabled": True},
    "SDCG": {"ticker": "0321.KL", "name": "Solar District Cooling", "exchange": "KLSE", "sector": "Utilities", "enabled": True},
    "TENAGA": {"ticker": "5347.KL", "name": "Tenaga Nasional", "exchange": "KLSE", "sector": "Utilities", "enabled": True},
    "YTL": {"ticker": "4677.KL", "name": "YTL Corporation", "exchange": "KLSE", "sector": "Utilities", "enabled": True},
    "YTLPOWR": {"ticker": "6742.KL", "name": "YTL Power International", "exchange": "KLSE", "sector": "Utilities", "enabled": True},

    # ── Telecom (4) ──────────────────────────────────────────
    "AXIATA": {"ticker": "6888.KL", "name": "Axiata Group", "exchange": "KLSE", "sector": "Telecom", "enabled": True},
    "MAXIS": {"ticker": "6012.KL", "name": "Maxis Berhad", "exchange": "KLSE", "sector": "Telecom", "enabled": True},
    "TIMECOM": {"ticker": "5031.KL", "name": "Time dotCom", "exchange": "KLSE", "sector": "Telecom", "enabled": True},
    "TM": {"ticker": "4863.KL", "name": "Telekom Malaysia", "exchange": "KLSE", "sector": "Telecom", "enabled": True},

    # ── Technology (15) ──────────────────────────────────────
    "ATECH": {"ticker": "5302.KL", "name": "Aurelius Technologies", "exchange": "KLSE", "sector": "Technology", "enabled": True},
    "CORAZA": {"ticker": "0240.KL", "name": "Coraza Integrated Tech", "exchange": "KLSE", "sector": "Technology", "enabled": True},
    "DUFU": {"ticker": "7233.KL", "name": "Dufu Technology", "exchange": "KLSE", "sector": "Technology", "enabled": True},
    "EG": {"ticker": "8907.KL", "name": "EG Industries", "exchange": "KLSE", "sector": "Technology", "enabled": True},
    "GREATEC": {"ticker": "0208.KL", "name": "Greatech Technology", "exchange": "KLSE", "sector": "Technology", "enabled": True},
    "IAB": {"ticker": "0376.KL", "name": "Insights Analytics", "exchange": "KLSE", "sector": "Technology", "enabled": True},
    "INARI": {"ticker": "0166.KL", "name": "Inari Amertron", "exchange": "KLSE", "sector": "Technology", "enabled": True},
    "ITMAX": {"ticker": "5309.KL", "name": "ITMAX System", "exchange": "KLSE", "sector": "Technology", "enabled": True},
    "MPI": {"ticker": "3867.KL", "name": "Malaysian Pacific Industries", "exchange": "KLSE", "sector": "Technology", "enabled": True},
    "NATGATE": {"ticker": "0270.KL", "name": "Nationgate Holdings", "exchange": "KLSE", "sector": "Technology", "enabled": True},
    "PENTA": {"ticker": "7160.KL", "name": "Pentamaster Corporation", "exchange": "KLSE", "sector": "Technology", "enabled": True},
    "RAMSSOL": {"ticker": "0236.KL", "name": "Ramssol Group", "exchange": "KLSE", "sector": "Technology", "enabled": True},
    "SEMICO": {"ticker": "0388.KL", "name": "Semico Capital", "exchange": "KLSE", "sector": "Technology", "enabled": True},
    "UWC": {"ticker": "5292.KL", "name": "UWC Berhad", "exchange": "KLSE", "sector": "Technology", "enabled": True},
    "ZETRIX": {"ticker": "0138.KL", "name": "Zetrix AI", "exchange": "KLSE", "sector": "Technology", "enabled": True},

    # ── Healthcare (5) ───────────────────────────────────────
    "HARTA": {"ticker": "5168.KL", "name": "Hartalega Holdings", "exchange": "KLSE", "sector": "Healthcare", "enabled": True},
    "IHH": {"ticker": "5225.KL", "name": "IHH Healthcare", "exchange": "KLSE", "sector": "Healthcare", "enabled": True},
    "KOSSAN": {"ticker": "7153.KL", "name": "Kossan Rubber Industries", "exchange": "KLSE", "sector": "Healthcare", "enabled": True},
    "KPJ": {"ticker": "5878.KL", "name": "KPJ Healthcare", "exchange": "KLSE", "sector": "Healthcare", "enabled": True},
    "TOPGLOV": {"ticker": "7113.KL", "name": "Top Glove Corporation", "exchange": "KLSE", "sector": "Healthcare", "enabled": True},

    # ── Consumer (21) ────────────────────────────────────────
    "99SMART": {"ticker": "5326.KL", "name": "99 Speed Mart", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "AEON": {"ticker": "6599.KL", "name": "AEON Co Malaysia", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "BAT": {"ticker": "4162.KL", "name": "British American Tobacco MY", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "BAUTO": {"ticker": "5248.KL", "name": "Bermaz Auto", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "CARLSBG": {"ticker": "2836.KL", "name": "Carlsberg Brewery Malaysia", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "DKSH": {"ticker": "5908.KL", "name": "DKSH Holdings Malaysia", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "DLADY": {"ticker": "3026.KL", "name": "Dutch Lady Milk Industries", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "ECOSHOP": {"ticker": "5337.KL", "name": "Eco-Shop Marketing", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "F&N": {"ticker": "3689.KL", "name": "Fraser & Neave Holdings", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "FFB": {"ticker": "5306.KL", "name": "Farm Fresh", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "GENM": {"ticker": "4715.KL", "name": "Genting Malaysia", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "GENTING": {"ticker": "3182.KL", "name": "Genting Berhad", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "HEIM": {"ticker": "3255.KL", "name": "Heineken Malaysia", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "KOPI": {"ticker": "0338.KL", "name": "Oriental Kopi Holdings", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "LHI": {"ticker": "6633.KL", "name": "Leong Hup International", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "LWSABAH": {"ticker": "5328.KL", "name": "Life Water Sabah", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "MFLOUR": {"ticker": "3662.KL", "name": "Malayan Flour Mills", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "MRDIY": {"ticker": "5296.KL", "name": "Mr DIY Group", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "NESTLE": {"ticker": "4707.KL", "name": "Nestle Malaysia", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "QL": {"ticker": "7084.KL", "name": "QL Resources", "exchange": "KLSE", "sector": "Consumer", "enabled": True},
    "SJC": {"ticker": "9431.KL", "name": "Seni Jaya Corporation", "exchange": "KLSE", "sector": "Consumer", "enabled": True},

    # ── Industrial (19) ──────────────────────────────────────
    "AUMAS": {"ticker": "0098.KL", "name": "Aumas Resources", "exchange": "KLSE", "sector": "Industrial", "enabled": True},
    "CBHB": {"ticker": "0339.KL", "name": "CBH Engineering", "exchange": "KLSE", "sector": "Industrial", "enabled": True},
    "CGB": {"ticker": "8052.KL", "name": "Central Global", "exchange": "KLSE", "sector": "Industrial", "enabled": True},
    "CMSB": {"ticker": "2852.KL", "name": "Cahya Mata Sarawak", "exchange": "KLSE", "sector": "Industrial", "enabled": True},
    "HEXTAR": {"ticker": "5151.KL", "name": "Hextar Global", "exchange": "KLSE", "sector": "Industrial", "enabled": True},
    "HLIND": {"ticker": "3301.KL", "name": "Hong Leong Industries", "exchange": "KLSE", "sector": "Industrial", "enabled": True},
    "KEEMING": {"ticker": "0392.KL", "name": "Kee Ming Group", "exchange": "KLSE", "sector": "Industrial", "enabled": True},
    "KGB": {"ticker": "0151.KL", "name": "Kelington Group", "exchange": "KLSE", "sector": "Industrial", "enabled": True},
    "MCLEAN": {"ticker": "0167.KL", "name": "Mclean Technologies", "exchange": "KLSE", "sector": "Industrial", "enabled": True},
    "MEGAFB": {"ticker": "5327.KL", "name": "Mega Fortris", "exchange": "KLSE", "sector": "Industrial", "enabled": True},
    "NCT": {"ticker": "0056.KL", "name": "NCT Alliance", "exchange": "KLSE", "sector": "Industrial", "enabled": True},
    "NE": {"ticker": "0325.KL", "name": "Northeast Group", "exchange": "KLSE", "sector": "Industrial", "enabled": True},
    "NGGB": {"ticker": "7241.KL", "name": "Nextgreen Global", "exchange": "KLSE", "sector": "Industrial", "enabled": True},
    "PEKAT": {"ticker": "0233.KL", "name": "Pekat Group", "exchange": "KLSE", "sector": "Industrial", "enabled": True},
    "PMETAL": {"ticker": "8869.KL", "name": "Press Metal Aluminium", "exchange": "KLSE", "sector": "Industrial", "enabled": True},
    "TANCO": {"ticker": "2429.KL", "name": "Tanco Holdings", "exchange": "KLSE", "sector": "Industrial", "enabled": True},
    "THMY": {"ticker": "0375.KL", "name": "THMY Holdings", "exchange": "KLSE", "sector": "Industrial", "enabled": True},
    "XL": {"ticker": "7121.KL", "name": "XL Holdings", "exchange": "KLSE", "sector": "Industrial", "enabled": True},
    "YEWLEE": {"ticker": "0248.KL", "name": "Yew Lee Pacific Group", "exchange": "KLSE", "sector": "Industrial", "enabled": True},

    # ── Construction (5) ─────────────────────────────────────
    "GAMUDA": {"ticker": "5398.KL", "name": "Gamuda Berhad", "exchange": "KLSE", "sector": "Construction", "enabled": True},
    "IJM": {"ticker": "3336.KL", "name": "IJM Corporation", "exchange": "KLSE", "sector": "Construction", "enabled": True},
    "KERJAYA": {"ticker": "7161.KL", "name": "Kerjaya Prospek Group", "exchange": "KLSE", "sector": "Construction", "enabled": True},
    "MCEMENT": {"ticker": "3794.KL", "name": "Malayan Cement", "exchange": "KLSE", "sector": "Construction", "enabled": True},
    "SCGBHD": {"ticker": "0225.KL", "name": "Southern Cable Group", "exchange": "KLSE", "sector": "Construction", "enabled": True},

    # ── Plantation (9) ───────────────────────────────────────
    "GENP": {"ticker": "2291.KL", "name": "Genting Plantations", "exchange": "KLSE", "sector": "Plantation", "enabled": True},
    "IOICORP": {"ticker": "1961.KL", "name": "IOI Corporation", "exchange": "KLSE", "sector": "Plantation", "enabled": True},
    "JPG": {"ticker": "5323.KL", "name": "Johor Plantations Group", "exchange": "KLSE", "sector": "Plantation", "enabled": True},
    "JTIASA": {"ticker": "4383.KL", "name": "Jaya Tiasa Holdings", "exchange": "KLSE", "sector": "Plantation", "enabled": True},
    "KLK": {"ticker": "2445.KL", "name": "Kuala Lumpur Kepong", "exchange": "KLSE", "sector": "Plantation", "enabled": True},
    "SDG": {"ticker": "5285.KL", "name": "SD Guthrie", "exchange": "KLSE", "sector": "Plantation", "enabled": True},
    "TSH": {"ticker": "9059.KL", "name": "TSH Resources", "exchange": "KLSE", "sector": "Plantation", "enabled": True},
    "UTDPLT": {"ticker": "2089.KL", "name": "United Plantations", "exchange": "KLSE", "sector": "Plantation", "enabled": True},
    "WTK": {"ticker": "4243.KL", "name": "WTK Holdings", "exchange": "KLSE", "sector": "Plantation", "enabled": True},

    # ── REIT & Property (10) ─────────────────────────────────
    "AXREIT": {"ticker": "5106.KL", "name": "Axis REIT", "exchange": "KLSE", "sector": "REIT", "enabled": True},
    "ECOWLD": {"ticker": "8206.KL", "name": "Eco World Development", "exchange": "KLSE", "sector": "REIT", "enabled": True},
    "IGBREIT": {"ticker": "5227.KL", "name": "IGB REIT", "exchange": "KLSE", "sector": "REIT", "enabled": True},
    "IOIPG": {"ticker": "5249.KL", "name": "IOI Properties Group", "exchange": "KLSE", "sector": "REIT", "enabled": True},
    "KLCC": {"ticker": "5235SS.KL", "name": "KLCCP Stapled", "exchange": "KLSE", "sector": "REIT", "enabled": True},
    "LAGENDA": {"ticker": "7179.KL", "name": "Lagenda Properties", "exchange": "KLSE", "sector": "REIT", "enabled": True},
    "MAHSING": {"ticker": "8583.KL", "name": "Mah Sing Group", "exchange": "KLSE", "sector": "REIT", "enabled": True},
    "PAVREIT": {"ticker": "5212.KL", "name": "Pavilion REIT", "exchange": "KLSE", "sector": "REIT", "enabled": True},
    "UEMS": {"ticker": "5148.KL", "name": "UEM Sunrise", "exchange": "KLSE", "sector": "REIT", "enabled": True},
    "YTLREIT": {"ticker": "5109.KL", "name": "YTL Hospitality REIT", "exchange": "KLSE", "sector": "REIT", "enabled": True},

    # ── Transport (4) ────────────────────────────────────────
    "AAX": {"ticker": "5238.KL", "name": "AirAsia X", "exchange": "KLSE", "sector": "Transport", "enabled": True},
    "CAPITALA": {"ticker": "5099.KL", "name": "Capital A", "exchange": "KLSE", "sector": "Transport", "enabled": True},
    "MISC": {"ticker": "3816.KL", "name": "MISC Berhad", "exchange": "KLSE", "sector": "Transport", "enabled": True},
    "WPRTS": {"ticker": "5246.KL", "name": "Westports Holdings", "exchange": "KLSE", "sector": "Transport", "enabled": True},

    # ── Conglomerate (4) ─────────────────────────────────────
    "DRBHCOM": {"ticker": "1619.KL", "name": "DRB-HICOM", "exchange": "KLSE", "sector": "Conglomerate", "enabled": True},
    "PPB": {"ticker": "4065.KL", "name": "PPB Group", "exchange": "KLSE", "sector": "Conglomerate", "enabled": True},
    "SIME": {"ticker": "4197.KL", "name": "Sime Darby", "exchange": "KLSE", "sector": "Conglomerate", "enabled": True},
    "SUNWAY": {"ticker": "5211.KL", "name": "Sunway Berhad", "exchange": "KLSE", "sector": "Conglomerate", "enabled": True},

    # ── Media (1) ────────────────────────────────────────────
    "ASTRO": {"ticker": "6399.KL", "name": "Astro Malaysia Holdings", "exchange": "KLSE", "sector": "Media", "enabled": True},
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
