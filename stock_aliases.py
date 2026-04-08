"""
Stock Aliases — Maps informal stock names, abbreviations, and
Bursa codes to the canonical STOCKS dictionary keys in config.py.

Used by SentimentAnalyzer to match forum mentions to tracked stocks.
"""

from config import STOCKS

# Manual aliases for colloquial names used in Malaysian forums
MANUAL_ALIASES = {
    # ── Finance ──────────────────────────────────────────────
    "mbb": "MAYBANK", "maybank": "MAYBANK", "malayan banking": "MAYBANK",
    "pbbank": "PBBANK", "pb bank": "PBBANK", "public bank": "PBBANK",
    "cimb": "CIMB", "cimb group": "CIMB",
    "hlbank": "HLBANK", "hl bank": "HLBANK", "hong leong bank": "HLBANK",
    "rhb": "RHBBANK", "rhb bank": "RHBBANK", "rhbbank": "RHBBANK",
    "ambank": "AMBANK", "ammb": "AMBANK", "ammb holdings": "AMBANK",
    "abmb": "ABMB", "alliance bank": "ABMB",
    "bimb": "BIMB", "bank islam": "BIMB",
    "bursa": "BURSA", "bursa malaysia": "BURSA",
    "allianz": "ALLIANZ", "allianz malaysia": "ALLIANZ",
    "hlfg": "HLFG", "hong leong financial": "HLFG",
    "lpi": "LPI", "lpi capital": "LPI",
    "aeoncr": "AEONCR", "aeon credit": "AEONCR",
    "osk": "OSK", "osk holdings": "OSK",

    # ── Energy ───────────────────────────────────────────────
    "pchem": "PCHEM", "petronas chem": "PCHEM", "petronas chemicals": "PCHEM",
    "petdag": "PETDAG", "petronas dagangan": "PETDAG",
    "petgas": "PETGAS", "petronas gas": "PETGAS",
    "dialog": "DIALOG", "dialog group": "DIALOG",
    "hibiscs": "HIBISCS", "hibiscus": "HIBISCS", "hibiscus petroleum": "HIBISCS",
    "yinson": "YINSON", "yinson holdings": "YINSON",
    "dayang": "DAYANG", "dayang enterprise": "DAYANG",
    "armada": "ARMADA", "bumi armada": "ARMADA",
    "hengyuan": "HENGYUAN", "hrc": "HENGYUAN",
    "gasmsia": "GASMSIA", "gas malaysia": "GASMSIA",
    "elridge": "ELRIDGE", "elridge energy": "ELRIDGE",

    # ── Utilities ────────────────────────────────────────────
    "tnb": "TENAGA", "tenaga": "TENAGA", "tenaga nasional": "TENAGA",
    "ytl": "YTL", "ytl corp": "YTL", "ytl corporation": "YTL",
    "ytlpowr": "YTLPOWR", "ytl power": "YTLPOWR", "ytlpower": "YTLPOWR",
    "malakof": "MALAKOF", "malakoff": "MALAKOF",
    "samaiden": "SAMAIDEN",
    "sdcg": "SDCG", "solar district cooling": "SDCG",
    "cypark": "CYPARK",

    # ── Telecom ──────────────────────────────────────────────
    "tm": "TM", "telekom": "TM", "telekom malaysia": "TM",
    "maxis": "MAXIS",
    "axiata": "AXIATA", "axiata group": "AXIATA",
    "timecom": "TIMECOM", "time dotcom": "TIMECOM", "time": "TIMECOM",

    # ── Technology ───────────────────────────────────────────
    "inari": "INARI", "inari amertron": "INARI",
    "mpi": "MPI", "malaysian pacific": "MPI",
    "greatec": "GREATEC", "greatech": "GREATEC",
    "penta": "PENTA", "pentamaster": "PENTA",
    "uwc": "UWC",
    "dufu": "DUFU", "dufu tech": "DUFU",
    "natgate": "NATGATE", "nationgate": "NATGATE",
    "eg": "EG", "eg industries": "EG",
    "atech": "ATECH", "aurelius": "ATECH",
    "coraza": "CORAZA",
    "itmax": "ITMAX",
    "zetrix": "ZETRIX", "zetrix ai": "ZETRIX",
    "semico": "SEMICO",
    "ramssol": "RAMSSOL",
    "iab": "IAB", "insights analytics": "IAB",

    # ── Healthcare ───────────────────────────────────────────
    "topglov": "TOPGLOV", "top glove": "TOPGLOV", "topglove": "TOPGLOV",
    "harta": "HARTA", "hartalega": "HARTA",
    "ihh": "IHH", "ihh healthcare": "IHH",
    "kossan": "KOSSAN", "kossan rubber": "KOSSAN",
    "kpj": "KPJ", "kpj healthcare": "KPJ",

    # ── Consumer ─────────────────────────────────────────────
    "genting": "GENTING", "genting bhd": "GENTING",
    "genm": "GENM", "genting malaysia": "GENM", "gentingm": "GENM",
    "nestle": "NESTLE", "nestle malaysia": "NESTLE",
    "mr diy": "MRDIY", "mrdiy": "MRDIY",
    "ql": "QL", "ql resources": "QL",
    "heim": "HEIM", "heineken": "HEIM", "heineken malaysia": "HEIM",
    "carlsbg": "CARLSBG", "carlsberg": "CARLSBG", "carlsberg malaysia": "CARLSBG",
    "f&n": "F&N", "fn": "F&N", "fraser neave": "F&N", "fraser & neave": "F&N",
    "dlady": "DLADY", "dutch lady": "DLADY",
    "bat": "BAT", "british american tobacco": "BAT",
    "99smart": "99SMART", "99 speedmart": "99SMART", "99speedmart": "99SMART", "speed mart": "99SMART",
    "aeon": "AEON", "aeon co": "AEON",
    "bauto": "BAUTO", "bermaz": "BAUTO", "bermaz auto": "BAUTO",
    "ecoshop": "ECOSHOP", "eco shop": "ECOSHOP",
    "ffb": "FFB", "farm fresh": "FFB", "farmfresh": "FFB",
    "kopi": "KOPI", "oriental kopi": "KOPI",
    "lhi": "LHI", "leong hup": "LHI",
    "mflour": "MFLOUR", "malayan flour": "MFLOUR",
    "dksh": "DKSH",
    "sjc": "SJC", "seni jaya": "SJC",
    "lwsabah": "LWSABAH", "life water": "LWSABAH",

    # ── Industrial ───────────────────────────────────────────
    "pmetal": "PMETAL", "press metal": "PMETAL",
    "hlind": "HLIND", "hong leong industries": "HLIND",
    "cmsb": "CMSB", "cahya mata": "CMSB",
    "megafb": "MEGAFB", "mega fortris": "MEGAFB",
    "pekat": "PEKAT", "pekat group": "PEKAT",
    "kgb": "KGB", "kelington": "KGB",
    "nggb": "NGGB", "nextgreen": "NGGB",
    "hextar": "HEXTAR",
    "tanco": "TANCO",
    "cbhb": "CBHB",
    "cgb": "CGB", "central global": "CGB",
    "nct": "NCT",
    "ne": "NE", "northeast": "NE",
    "thmy": "THMY",
    "xl": "XL",
    "yewlee": "YEWLEE", "yew lee": "YEWLEE",
    "mclean": "MCLEAN",
    "aumas": "AUMAS",
    "keeming": "KEEMING", "kee ming": "KEEMING",

    # ── Construction ─────────────────────────────────────────
    "gamuda": "GAMUDA", "gamuda bhd": "GAMUDA",
    "ijm": "IJM", "ijm corporation": "IJM",
    "kerjaya": "KERJAYA", "kerjaya prospek": "KERJAYA",
    "mcement": "MCEMENT", "malayan cement": "MCEMENT",
    "scgbhd": "SCGBHD", "southern cable": "SCGBHD",

    # ── Plantation ───────────────────────────────────────────
    "sd guthrie": "SDG", "sdg": "SDG",
    "ioicorp": "IOICORP", "ioi corporation": "IOICORP", "ioi corp": "IOICORP",
    "genp": "GENP", "genting plantations": "GENP",
    "klk": "KLK", "kl kepong": "KLK", "kuala lumpur kepong": "KLK",
    "utdplt": "UTDPLT", "united plantations": "UTDPLT",
    "jpg": "JPG", "johor plantations": "JPG",
    "jtiasa": "JTIASA", "jaya tiasa": "JTIASA",
    "tsh": "TSH", "tsh resources": "TSH",
    "wtk": "WTK",

    # ── REIT & Property ──────────────────────────────────────
    "klcc": "KLCC", "klccp": "KLCC",
    "ytlreit": "YTLREIT", "ytl reit": "YTLREIT",
    "pavreit": "PAVREIT", "pavilion reit": "PAVREIT",
    "igbreit": "IGBREIT", "igb reit": "IGBREIT",
    "axreit": "AXREIT", "axis reit": "AXREIT",
    "ioipg": "IOIPG", "ioi properties": "IOIPG",
    "ecowld": "ECOWLD", "ecoworld": "ECOWLD", "eco world": "ECOWLD",
    "mahsing": "MAHSING", "mah sing": "MAHSING",
    "lagenda": "LAGENDA",
    "uems": "UEMS", "uem sunrise": "UEMS",

    # ── Transport ────────────────────────────────────────────
    "misc": "MISC", "misc bhd": "MISC",
    "wprts": "WPRTS", "westports": "WPRTS",
    "aax": "AAX", "airasia x": "AAX",
    "capitala": "CAPITALA", "capital a": "CAPITALA", "airasia": "CAPITALA",

    # ── Conglomerate ─────────────────────────────────────────
    "ppb": "PPB", "ppb group": "PPB",
    "sunway": "SUNWAY", "sunway bhd": "SUNWAY",
    "sime": "SIME", "sime darby": "SIME",
    "drbhcom": "DRBHCOM", "drb hicom": "DRBHCOM", "drb-hicom": "DRBHCOM",

    # ── Media ────────────────────────────────────────────────
    "astro": "ASTRO", "astro malaysia": "ASTRO",
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
