"""
Stock Aliases — Maps informal stock names, abbreviations, and
Bursa codes to the canonical STOCKS dictionary keys in config.py.

Used by SentimentAnalyzer to match forum mentions to tracked stocks.
"""

from config import STOCKS

# Manual aliases for colloquial names used in Malaysian forums
MANUAL_ALIASES = {
    # --- KLSE stocks ---
    "mbb": "MAYBANK", "maybank": "MAYBANK", "malayan banking": "MAYBANK",
    "pbbank": "PUBBANK", "pb bank": "PUBBANK", "public bank": "PUBBANK",
    "pchem": "PCHEM", "petronas chem": "PCHEM", "petronas chemicals": "PCHEM",
    "cimb": "CIMB", "cimb group": "CIMB",
    "tm": "TM", "telekom": "TM", "telekom malaysia": "TM",
    "genting": "GENTING", "genting bhd": "GENTING",
    "tnb": "TENAGA", "tenaga": "TENAGA", "tenaga nasional": "TENAGA",
    "maxis": "MAXIS",
    "ytl": "YTL", "ytl corp": "YTL",
    # New KLSE stocks
    "topglov": "TOPGLOV", "top glove": "TOPGLOV", "topglove": "TOPGLOV",
    "harta": "HARTA", "hartalega": "HARTA",
    "ihh": "IHH", "ihh healthcare": "IHH",
    "axiata": "AXIATA", "axiata group": "AXIATA",
    "dialog": "DIALOG", "dialog group": "DIALOG",
    "petdag": "PETDAG", "petronas dagangan": "PETDAG",
    "hlbank": "HLBANK", "hl bank": "HLBANK", "hong leong bank": "HLBANK",
    "press metal": "PRESS", "pmetal": "PRESS", "press": "PRESS",
    "mr diy": "MRDIY", "mrdiy": "MRDIY",
    "inari": "INARI", "inari amertron": "INARI",
    "sunway": "SUNWAY", "sunway bhd": "SUNWAY",
    "gamuda": "GAMUDA", "gamuda bhd": "GAMUDA",
    "ql": "QL", "ql resources": "QL",
    "nestle": "NESTLE", "nestle malaysia": "NESTLE",
    "ppb": "PPB", "ppb group": "PPB",
    "rhb": "RHB", "rhb bank": "RHB",
    "sd guthrie": "SDG", "sdg": "SDG", "sime darby": "SDG",
    "misc": "MISC", "misc bhd": "MISC",
    "klcc": "KLCC", "klccp": "KLCC",
    "ambank": "AMBANK", "ammb": "AMBANK",

    # --- SGX stocks ---
    "dbs": "DBS", "dbs group": "DBS",
    "ocbc": "OCBC", "ocbc bank": "OCBC",
    "singtel": "SINGTEL", "singapore telecom": "SINGTEL",
    "uob": "UOB", "united overseas bank": "UOB",
    "keppel": "KEPPEL", "keppel corp": "KEPPEL",
    "sia": "SIA", "singapore airlines": "SIA",
    "ascendas": "ASCENDAS", "ascendas reit": "ASCENDAS",
    "venture": "VENTURE", "venture corp": "VENTURE",
    "thaibev": "THAIBEV", "thai beverage": "THAIBEV",
    "sats": "SATS",

    # --- DFM stocks ---
    "emaar": "EMAAR", "emaar properties": "EMAAR",
    "dib": "DIB", "dubai islamic bank": "DIB",
    "dfm": "DFMGI", "dubai financial market": "DFMGI",
    "emaardev": "EMAARDEV", "emaar development": "EMAARDEV",
    "dewa": "DEWA",
    "salik": "SALIK",
    "gfh": "GFH", "gfh financial": "GFH",
    "parkin": "PARKIN",
    "tecom": "TECOM", "tecom group": "TECOM",
}


def build_alias_map() -> dict[str, str]:
    """
    Build a comprehensive alias map combining:
    1. Automatic aliases from config.STOCKS (key, name, ticker code)
    2. Manual aliases from MANUAL_ALIASES

    Returns dict mapping lowercase alias -> STOCKS key (uppercase).
    """
    alias_map = {}

    # Auto-generate from STOCKS config
    for stock_key, cfg in STOCKS.items():
        # Stock key itself
        alias_map[stock_key.lower()] = stock_key

        # Stock name
        alias_map[cfg["name"].lower()] = stock_key

        # Yahoo Finance code number (e.g. "1155" from "1155.KL")
        ticker = cfg["ticker"]
        code = ticker.split(".")[0]
        if len(code) >= 3:  # avoid short codes that match random text
            alias_map[code] = stock_key

    # Merge manual aliases (overrides auto-generated on conflict)
    for alias, stock_key in MANUAL_ALIASES.items():
        alias_map[alias.lower()] = stock_key

    return alias_map
