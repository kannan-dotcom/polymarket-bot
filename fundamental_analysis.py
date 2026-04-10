"""
Fundamental Analysis Module — Fetches and scores company financials
(revenue, profit, growth, valuation ratios) via Yahoo Finance.

Provides a composite fundamental_score (0-100) for each stock based on:
  - Revenue growth
  - Profit margin
  - Return on equity (ROE)
  - Debt-to-equity ratio
  - P/E ratio (valuation)
  - Free cash flow yield
  - Dividend yield
  - Earnings consistency

Data is cached and refreshed periodically (default every 6 hours)
since fundamental data changes infrequently.
"""

import time
import logging
import threading
import numpy as np
import yfinance as yf
from dataclasses import dataclass, field
from typing import Optional
from config import STOCKS

logger = logging.getLogger("fundamentals")

# ============================================================
# Configuration
# ============================================================
FUNDAMENTALS_REFRESH_INTERVAL = 6 * 3600  # 6 hours between full refreshes
FUNDAMENTALS_CACHE_TTL = 6 * 3600         # cache per-stock for 6 hours
FUNDAMENTALS_ENABLED = True


@dataclass
class StockFundamentals:
    """Fundamental data for a single stock."""
    stock_key: str
    ticker: str

    # Income statement
    revenue: Optional[float] = None             # total revenue (annual)
    revenue_growth: Optional[float] = None      # YoY revenue growth %
    net_income: Optional[float] = None          # net income
    profit_margin: Optional[float] = None       # net profit margin (0-1)
    gross_margin: Optional[float] = None        # gross margin (0-1)

    # Valuation
    pe_ratio: Optional[float] = None            # price-to-earnings
    pb_ratio: Optional[float] = None            # price-to-book
    market_cap: Optional[float] = None          # market capitalization
    eps: Optional[float] = None                 # earnings per share (trailing)

    # Balance sheet & efficiency
    roe: Optional[float] = None                 # return on equity (0-1)
    debt_to_equity: Optional[float] = None      # debt/equity ratio
    current_ratio: Optional[float] = None       # current assets / current liabilities

    # Cash flow
    free_cash_flow: Optional[float] = None      # free cash flow
    dividend_yield: Optional[float] = None      # dividend yield (0-1)

    # Dividend detail
    last_dividend_value: Optional[float] = None   # most recent dividend per share (MYR)
    last_dividend_date: Optional[str] = None      # date of last dividend payment (YYYY-MM-DD)
    ex_dividend_date: Optional[str] = None        # next/last ex-dividend date (YYYY-MM-DD)
    dividend_frequency: Optional[str] = None      # "Quarterly", "Semi-Annual", "Annual", "Irregular"
    trailing_annual_dividend: Optional[float] = None  # trailing 12-month dividend per share
    payout_ratio: Optional[float] = None          # payout ratio (0-1)

    # Composite score
    fundamental_score: Optional[float] = None   # 0-100 composite

    # Metadata
    last_updated: float = 0.0
    data_quality: str = "none"                  # "full", "partial", "none"

    def to_dict(self) -> dict:
        return {
            "stock_key": self.stock_key,
            "ticker": self.ticker,
            "revenue": self.revenue,
            "revenue_growth": self.revenue_growth,
            "net_income": self.net_income,
            "profit_margin": self.profit_margin,
            "gross_margin": self.gross_margin,
            "pe_ratio": self.pe_ratio,
            "pb_ratio": self.pb_ratio,
            "market_cap": self.market_cap,
            "eps": self.eps,
            "roe": self.roe,
            "debt_to_equity": self.debt_to_equity,
            "current_ratio": self.current_ratio,
            "free_cash_flow": self.free_cash_flow,
            "dividend_yield": self.dividend_yield,
            "last_dividend_value": self.last_dividend_value,
            "last_dividend_date": self.last_dividend_date,
            "ex_dividend_date": self.ex_dividend_date,
            "dividend_frequency": self.dividend_frequency,
            "trailing_annual_dividend": self.trailing_annual_dividend,
            "payout_ratio": self.payout_ratio,
            "fundamental_score": self.fundamental_score,
            "last_updated": self.last_updated,
            "data_quality": self.data_quality,
        }


class FundamentalAnalyzer:
    """
    Fetches fundamental data from Yahoo Finance and computes
    a composite fundamental score for each stock.

    Thread-safe: uses a lock around the data store.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._data: dict[str, StockFundamentals] = {}
        self._last_full_refresh = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_all(self):
        """Fetch fundamentals for all enabled stocks."""
        enabled = {k: v for k, v in STOCKS.items() if v.get("enabled")}
        logger.info(f"Fundamentals refresh starting for {len(enabled)} stocks")
        count = 0
        errors = 0

        for stock_key, cfg in enabled.items():
            try:
                fund = self._fetch_fundamentals(stock_key, cfg["ticker"])
                if fund:
                    with self._lock:
                        self._data[stock_key] = fund
                    count += 1
            except Exception as e:
                logger.debug(f"Fundamentals error for {stock_key}: {e}")
                errors += 1
            # Rate limit: avoid hammering Yahoo Finance
            time.sleep(0.5)

        self._last_full_refresh = time.time()
        logger.info(
            f"Fundamentals refresh done: {count} stocks updated, "
            f"{errors} errors"
        )

    def get_fundamentals(self, stock_key: str) -> Optional[StockFundamentals]:
        """Get cached fundamentals for a stock."""
        with self._lock:
            return self._data.get(stock_key)

    def get_all_fundamentals(self) -> dict[str, StockFundamentals]:
        """Get all cached fundamentals."""
        with self._lock:
            return dict(self._data)

    def get_all_as_dicts(self) -> dict[str, dict]:
        """Get all fundamentals as serializable dicts."""
        with self._lock:
            return {k: v.to_dict() for k, v in self._data.items()}

    # ------------------------------------------------------------------
    # Data Fetching
    # ------------------------------------------------------------------

    def _fetch_fundamentals(self, stock_key: str, ticker: str) -> Optional[StockFundamentals]:
        """Fetch fundamental data from Yahoo Finance for a single stock."""
        try:
            tk = yf.Ticker(ticker)
            info = tk.info or {}
        except Exception as e:
            logger.debug(f"yfinance info error for {ticker}: {e}")
            return None

        if not info or info.get("regularMarketPrice") is None:
            # Try basic fields — some KLSE stocks have limited data
            pass

        fund = StockFundamentals(
            stock_key=stock_key,
            ticker=ticker,
            last_updated=time.time(),
        )

        # --- Extract from info dict ---
        fund.market_cap = _safe_float(info.get("marketCap"))
        fund.pe_ratio = _safe_float(info.get("trailingPE") or info.get("forwardPE"))
        fund.pb_ratio = _safe_float(info.get("priceToBook"))
        fund.eps = _safe_float(info.get("trailingEps"))
        fund.profit_margin = _safe_float(info.get("profitMargins"))
        fund.gross_margin = _safe_float(info.get("grossMargins"))
        fund.roe = _safe_float(info.get("returnOnEquity"))
        fund.debt_to_equity = _safe_float(info.get("debtToEquity"))
        fund.dividend_yield = _safe_float(info.get("dividendYield"))
        fund.current_ratio = _safe_float(info.get("currentRatio"))
        fund.free_cash_flow = _safe_float(info.get("freeCashflow"))
        fund.revenue = _safe_float(info.get("totalRevenue"))
        fund.net_income = _safe_float(info.get("netIncomeToCommon"))
        fund.revenue_growth = _safe_float(info.get("revenueGrowth"))

        # debtToEquity from yfinance is often in percentage (e.g., 45.2 = 45.2%)
        # Normalize to ratio
        if fund.debt_to_equity is not None and fund.debt_to_equity > 10:
            fund.debt_to_equity = fund.debt_to_equity / 100.0

        # dividendYield from yfinance varies: sometimes decimal (0.059), sometimes
        # percentage (5.91). Normalize to decimal for internal use and frontend.
        if fund.dividend_yield is not None and fund.dividend_yield > 1.0:
            fund.dividend_yield = fund.dividend_yield / 100.0  # 5.91 -> 0.0591

        # --- Dividend detail fields ---
        fund.trailing_annual_dividend = _safe_float(info.get("trailingAnnualDividendRate"))
        fund.payout_ratio = _safe_float(info.get("payoutRatio"))
        if fund.payout_ratio is not None and fund.payout_ratio > 5.0:
            fund.payout_ratio = fund.payout_ratio / 100.0  # normalize if percentage

        # Ex-dividend date (Unix timestamp from yfinance)
        ex_div_ts = info.get("exDividendDate")
        if ex_div_ts and isinstance(ex_div_ts, (int, float)) and ex_div_ts > 0:
            try:
                import datetime
                fund.ex_dividend_date = datetime.datetime.fromtimestamp(
                    ex_div_ts, tz=datetime.timezone.utc
                ).strftime("%Y-%m-%d")
            except Exception:
                pass

        # Last dividend value and date + frequency from dividend history
        try:
            divs = tk.dividends
            if divs is not None and len(divs) > 0:
                fund.last_dividend_value = round(float(divs.iloc[-1]), 4)
                fund.last_dividend_date = divs.index[-1].strftime("%Y-%m-%d")
                # Infer frequency from payment gaps in the last 2 years
                fund.dividend_frequency = _infer_dividend_frequency(divs)
        except Exception:
            pass

        # revenue_growth from yfinance is already a decimal (e.g., 0.12 = 12%)
        # Convert to percentage for display
        if fund.revenue_growth is not None:
            fund.revenue_growth = fund.revenue_growth * 100  # now 12.0 = 12%

        # --- Try to get revenue growth from financials if not in info ---
        if fund.revenue_growth is None:
            fund.revenue_growth = self._compute_revenue_growth(tk)

        # --- Determine data quality ---
        fields_present = sum(1 for v in [
            fund.revenue, fund.net_income, fund.profit_margin,
            fund.pe_ratio, fund.roe, fund.market_cap, fund.eps,
        ] if v is not None)

        if fields_present >= 5:
            fund.data_quality = "full"
        elif fields_present >= 2:
            fund.data_quality = "partial"
        else:
            fund.data_quality = "none"

        # --- Compute composite score ---
        fund.fundamental_score = self._compute_score(fund)

        return fund

    def _compute_revenue_growth(self, tk) -> Optional[float]:
        """Compute YoY revenue growth from annual financials."""
        try:
            financials = tk.financials
            if financials is None or financials.empty:
                return None

            # financials columns are dates, rows are line items
            # Look for "Total Revenue" row
            rev_row = None
            for label in ["Total Revenue", "Operating Revenue", "Revenue"]:
                if label in financials.index:
                    rev_row = financials.loc[label]
                    break

            if rev_row is None or len(rev_row) < 2:
                return None

            # Most recent two years
            values = rev_row.dropna().values
            if len(values) < 2 or values[1] == 0:
                return None

            growth = (values[0] - values[1]) / abs(values[1])
            return float(growth * 100)  # as percentage

        except Exception:
            return None

    # ------------------------------------------------------------------
    # Composite Score Calculation
    # ------------------------------------------------------------------

    def _compute_score(self, fund: StockFundamentals) -> float:
        """
        Compute a composite fundamental score (0-100) from available metrics.

        Scoring criteria (each contributes 0-100, weighted):
          - Revenue growth: higher growth = better (20%)
          - Profit margin: higher = better (15%)
          - ROE: higher = better (15%)
          - Debt/Equity: lower = better (15%)
          - P/E ratio: moderate = best, extreme = bad (15%)
          - Free cash flow: positive & growing = better (10%)
          - Dividend yield: positive = bonus (10%)
        """
        components = []

        # (1) Revenue Growth — 20% weight
        if fund.revenue_growth is not None:
            # revenue_growth is in % (e.g., 12.0 = 12%)
            rg = fund.revenue_growth
            if rg > 30:
                score = 90
            elif rg > 15:
                score = 75
            elif rg > 5:
                score = 60
            elif rg > 0:
                score = 50
            elif rg > -5:
                score = 40
            elif rg > -15:
                score = 25
            else:
                score = 10
            components.append((score, 0.20))

        # (2) Profit Margin — 15% weight
        if fund.profit_margin is not None:
            pm = fund.profit_margin  # decimal (0.15 = 15%)
            if pm > 0.25:
                score = 90
            elif pm > 0.15:
                score = 75
            elif pm > 0.08:
                score = 60
            elif pm > 0.03:
                score = 50
            elif pm > 0:
                score = 40
            elif pm > -0.05:
                score = 25
            else:
                score = 10
            components.append((score, 0.15))

        # (3) ROE — 15% weight
        if fund.roe is not None:
            roe = fund.roe  # decimal (0.15 = 15%)
            if roe > 0.25:
                score = 90
            elif roe > 0.15:
                score = 75
            elif roe > 0.10:
                score = 60
            elif roe > 0.05:
                score = 50
            elif roe > 0:
                score = 35
            else:
                score = 15
            components.append((score, 0.15))

        # (4) Debt/Equity — 15% weight (lower is better)
        if fund.debt_to_equity is not None:
            de = fund.debt_to_equity  # ratio
            if de < 0.2:
                score = 90
            elif de < 0.5:
                score = 75
            elif de < 1.0:
                score = 60
            elif de < 1.5:
                score = 45
            elif de < 2.5:
                score = 30
            else:
                score = 10
            components.append((score, 0.15))

        # (5) P/E Ratio — 15% weight (moderate PE is best)
        if fund.pe_ratio is not None and fund.pe_ratio > 0:
            pe = fund.pe_ratio
            if pe < 5:
                score = 40  # suspiciously low, possible value trap
            elif pe < 10:
                score = 75  # cheap
            elif pe < 15:
                score = 85  # fairly valued
            elif pe < 20:
                score = 70  # reasonable
            elif pe < 30:
                score = 50  # getting expensive
            elif pe < 50:
                score = 30  # expensive
            else:
                score = 15  # very expensive
            components.append((score, 0.15))

        # (6) Free Cash Flow — 10% weight
        if fund.free_cash_flow is not None and fund.market_cap is not None and fund.market_cap > 0:
            fcf_yield = fund.free_cash_flow / fund.market_cap
            if fcf_yield > 0.08:
                score = 90
            elif fcf_yield > 0.05:
                score = 75
            elif fcf_yield > 0.02:
                score = 60
            elif fcf_yield > 0:
                score = 50
            elif fcf_yield > -0.02:
                score = 35
            else:
                score = 15
            components.append((score, 0.10))
        elif fund.free_cash_flow is not None:
            score = 60 if fund.free_cash_flow > 0 else 30
            components.append((score, 0.10))

        # (7) Dividend Yield — 10% weight
        if fund.dividend_yield is not None:
            dy = fund.dividend_yield  # decimal (0.04 = 4%)
            if dy > 0.06:
                score = 85
            elif dy > 0.04:
                score = 75
            elif dy > 0.02:
                score = 65
            elif dy > 0:
                score = 55
            else:
                score = 40  # no dividend isn't necessarily bad
            components.append((score, 0.10))

        # --- Compute weighted average ---
        if not components:
            return 50.0  # no data → neutral

        total_weight = sum(w for _, w in components)
        if total_weight == 0:
            return 50.0

        weighted_sum = sum(s * w for s, w in components)
        # Re-normalize if not all components present
        composite = weighted_sum / total_weight

        return float(np.clip(composite, 0, 100))


# ============================================================
# Utility
# ============================================================

def _infer_dividend_frequency(divs) -> str:
    """Infer dividend payment frequency from a pandas Series of dividends."""
    try:
        # Use last 2 years of payments
        import datetime
        cutoff = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=730)
        recent = divs[divs.index >= cutoff]
        if len(recent) < 2:
            recent = divs
        if len(recent) < 2:
            return "Annual"

        # Count payments per year
        dates = sorted(recent.index)
        # Compute average gap in days between consecutive payments
        gaps = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
        avg_gap = sum(gaps) / len(gaps) if gaps else 365

        if avg_gap < 50:
            return "Monthly"
        elif avg_gap < 120:
            return "Quarterly"
        elif avg_gap < 250:
            return "Semi-Annual"
        elif avg_gap < 500:
            return "Annual"
        else:
            return "Irregular"
    except Exception:
        return "Unknown"


def _safe_float(val) -> Optional[float]:
    """Safely convert a value to float, returning None on failure."""
    if val is None:
        return None
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None
