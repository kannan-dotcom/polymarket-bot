#!/usr/bin/env python3
"""Generate formatted PDFs for all 4 product spec documents using fpdf2."""

import os
import re
from fpdf import FPDF

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# Color palette
# ============================================================
NAVY = (15, 23, 42)
BLUE = (37, 99, 235)
LIGHT_BLUE = (219, 234, 254)
GREEN = (22, 163, 74)
RED = (220, 38, 38)
GRAY = (100, 116, 139)
LIGHT_GRAY = (241, 245, 249)
WHITE = (255, 255, 255)
DARK = (30, 41, 59)
AMBER = (217, 119, 6)


class SpecPDF(FPDF):
    """Custom PDF class for spec documents."""

    def __init__(self, title, subtitle):
        super().__init__()
        self.doc_title = title
        self.doc_subtitle = subtitle
        self.set_auto_page_break(auto=True, margin=25)

    def header(self):
        if self.page_no() == 1:
            return  # Cover page has its own header
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 6, self.doc_title, align="L")
        self.cell(0, 6, "MY Stock Market Trading Platform", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*BLUE)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*GRAY)
        self.cell(0, 8, "Confidential - MY Stock Market Trading Platform", align="L")
        self.cell(0, 8, f"Page {self.page_no()}/{{nb}}", align="R")

    def cover_page(self):
        self.add_page()
        self.ln(50)
        # Title
        self.set_font("Helvetica", "B", 28)
        self.set_text_color(*NAVY)
        self.cell(0, 14, self.doc_title, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        # Subtitle
        self.set_font("Helvetica", "", 14)
        self.set_text_color(*BLUE)
        self.cell(0, 10, self.doc_subtitle, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(8)
        # Line
        self.set_draw_color(*BLUE)
        self.set_line_width(0.8)
        self.line(60, self.get_y(), 150, self.get_y())
        self.ln(12)
        # Meta
        self.set_font("Helvetica", "", 11)
        self.set_text_color(*DARK)
        self.cell(0, 7, "Product: MY Stock Market Trading Platform", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 7, "Version: 1.0  |  April 2026", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 7, "Classification: Confidential", align="C", new_x="LMARGIN", new_y="NEXT")

    def section_heading(self, number, text):
        self.ln(6)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*NAVY)
        self.cell(0, 10, f"{number}. {text}", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*BLUE)
        self.set_line_width(0.4)
        self.line(10, self.get_y(), 80, self.get_y())
        self.ln(4)

    def subsection_heading(self, text):
        self.ln(3)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*DARK)
        self.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*DARK)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def code_block(self, text):
        self.set_fill_color(*LIGHT_GRAY)
        self.set_font("Courier", "", 8.5)
        self.set_text_color(30, 41, 59)
        x = self.get_x()
        w = 190
        lines = text.strip().split("\n")
        h_per_line = 4.5
        total_h = len(lines) * h_per_line + 6
        # Check page break
        if self.get_y() + total_h > 270:
            self.add_page()
        y_start = self.get_y()
        self.rect(x, y_start, w, total_h, style="F")
        self.set_xy(x + 3, y_start + 3)
        for line in lines:
            self.cell(w - 6, h_per_line, line[:100], new_x="LMARGIN", new_y="NEXT")
            self.set_x(x + 3)
        self.ln(4)

    def info_table(self, headers, rows, col_widths=None):
        """Draw a formatted table."""
        if not col_widths:
            n = len(headers)
            col_widths = [190 / n] * n

        # Header row
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(*NAVY)
        self.set_text_color(*WHITE)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=1, fill=True, align="C")
        self.ln()

        # Data rows
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*DARK)
        for row_idx, row in enumerate(rows):
            if row_idx % 2 == 0:
                self.set_fill_color(*WHITE)
            else:
                self.set_fill_color(*LIGHT_GRAY)
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 6, str(cell)[:40], border=1, fill=True, align="C")
            self.ln()
        self.ln(3)

    def callout_box(self, text, color=BLUE):
        self.set_fill_color(color[0], color[1], color[2])
        x = self.get_x()
        y = self.get_y()
        self.rect(x, y, 3, 18, style="F")
        self.set_fill_color(color[0], color[1], color[2], 0.1)
        self.set_xy(x + 5, y + 2)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*DARK)
        self.multi_cell(183, 5, text)
        self.ln(4)

    def metric_card(self, label, value, x, y, w=42, h=18, color=BLUE):
        self.set_fill_color(color[0], color[1], color[2])
        self.rect(x, y, w, h, style="F")
        # Value
        self.set_xy(x + 2, y + 2)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*WHITE)
        self.cell(w - 4, 8, str(value), align="C")
        # Label
        self.set_xy(x + 2, y + 10)
        self.set_font("Helvetica", "", 7)
        self.cell(w - 4, 6, label, align="C")


# ============================================================
# SPEC 01: Signal Engine
# ============================================================
def build_spec01():
    pdf = SpecPDF("SPEC 01 - Signal Engine", "Composite Scoring Model & Sub-Signal Specifications")
    pdf.alias_nb_pages()
    pdf.cover_page()

    # Page 2: Architecture
    pdf.add_page()
    pdf.section_heading("1", "Purpose")
    pdf.body_text(
        "The Signal Engine generates BUY / SELL / HOLD trading signals for each stock in "
        "the KLSE universe (~129 stocks) by combining nine independent technical sub-signals "
        "into a single composite score (0-100). The score drives downstream position sizing, "
        "price targets, and the AI analysis prompt."
    )

    pdf.section_heading("2", "Architecture Overview")
    pdf.body_text(
        "Data flows from Yahoo Finance through the MarketDataAggregator into 9 parallel "
        "sub-signal functions. Each sub-signal produces a score from 0 (strongly bearish) "
        "to 100 (strongly bullish). These are combined via weighted sum into a composite score."
    )
    pdf.code_block(
        "Yahoo Finance --> MarketDataAggregator --> Signal Engine (9 sub-signals)\n"
        "                                              |\n"
        "         +----+----+----+----+----+----+----+----+----+\n"
        "         |Mom |RSI |VWAP|EMA |Vol |VP  |Sent|Ichi|Pat |\n"
        "         |14% |10% |10% |10% |7%  |19% |8%  |12% |10% |\n"
        "         +----+----+----+----+----+----+----+----+----+\n"
        "                              |\n"
        "                    Weighted Composite (0-100)\n"
        "                    >= 60 = BUY | <= 40 = SELL | else HOLD"
    )

    pdf.section_heading("3", "Sub-Signal Specifications")

    # Momentum
    pdf.subsection_heading("3.1 Momentum Signal (Weight: 14%)")
    pdf.info_table(
        ["Parameter", "Value"],
        [["Window", "10 days"], ["Threshold", "2% (0.02)"], ["Noise Filter", "abs(mom) < threshold*0.3 = 50"]],
        [70, 120]
    )
    pdf.code_block(
        "scaled = momentum / (threshold * 3)\n"
        "score  = clip(50 + scaled * 50, 0, 100)"
    )

    # RSI
    pdf.subsection_heading("3.2 RSI Signal (Weight: 10%)")
    pdf.info_table(
        ["Parameter", "Value"],
        [["Period", "14 days"], ["Overbought", "70"], ["Oversold", "30"]],
        [70, 120]
    )
    pdf.body_text("Counter-trend logic (mean-reversion): overbought = bearish score, oversold = bullish.")
    pdf.code_block(
        "If RSI >= 70: score = clip(50 - excess*40, 5, 50)\n"
        "If RSI <= 30: score = clip(50 + excess*40, 50, 95)\n"
        "Else:         score = 50 + (RSI - 50) * 0.3"
    )

    # VWAP
    pdf.subsection_heading("3.3 VWAP Deviation (Weight: 10%)")
    pdf.body_text("Dual-mode: moderate deviation = trend continuation, extreme = mean reversion.")
    pdf.code_block(
        "Moderate (< 4x threshold): score = clip(50 + dev/(thr*8)*50, 10, 90)\n"
        "Extreme  (>= 4x):         score = clip(50 - dev/(thr*8)*50, 10, 90)"
    )

    # EMA
    pdf.subsection_heading("3.4 EMA Crossover (Weight: 10%)")
    pdf.code_block(
        "diff_pct    = (EMA_12 - EMA_26) / EMA_26\n"
        "price_vs_ema = (price - EMA_12) / EMA_12\n"
        "combined    = diff_pct * 0.7 + price_vs_ema * 0.3\n"
        "score       = clip(50 + combined * 500, 10, 90)"
    )

    # Volume Activity
    pdf.subsection_heading("3.5 Volume Activity (Weight: 7%)")
    pdf.body_text("Volume spikes (> 2x average) confirm momentum direction.")

    # Volume-Price
    pdf.add_page()
    pdf.subsection_heading("3.6 Volume-Price Analysis (Weight: 19%)")
    pdf.body_text("Heaviest-weighted signal. Three internal components:")
    pdf.info_table(
        ["Component", "Weight", "Source"],
        [
            ["OBV Trend", "40%", "On-Balance Volume slope"],
            ["Vol-Price Confirm", "35%", "Volume & price correlation"],
            ["Activity Level", "25%", "Volume trend + ratio boost"],
        ],
        [55, 30, 105]
    )
    pdf.code_block(
        "obv_score     = clip(50 + obv_trend * 40, 10, 90)\n"
        "confirm_score = clip(50 + vol_price_confirm * 40, 10, 90)\n"
        "vp_composite  = OBV*0.40 + Confirm*0.35 + Activity*0.25"
    )

    # Sentiment
    pdf.subsection_heading("3.7 Sentiment Signal (Weight: 8%)")
    pdf.body_text(
        "Only included when mention_count >= 2. Score sourced from the Sentiment Pipeline "
        "(SPEC-03). Thresholds: >65 = bullish reason, <35 = bearish reason, buzz >70 noted."
    )

    # Ichimoku
    pdf.subsection_heading("3.8 Ichimoku Cloud (Weight: 12%)")
    pdf.info_table(
        ["Component", "Bullish", "Bearish"],
        [
            ["Cloud Color", "+10", "-10"],
            ["Price vs Cloud", "+15 (above)", "-15 (below)"],
            ["TK Cross", "+12", "-12"],
            ["TK Diff", "+diff*200", "-diff*200"],
            ["Cloud Thickness>2%", "+5 support", "-5 resistance"],
        ],
        [60, 65, 65]
    )

    # Pattern
    pdf.subsection_heading("3.9 Pattern Recognition (Weight: 10%)")
    pdf.body_text("12 candlestick + 8 chart patterns. Scoring: net = (bull-bear)/(bull+bear), score = clip(50+net*40, 5, 95).")

    # Composite
    pdf.section_heading("4", "Composite Score & Direction")
    pdf.code_block(
        "composite = sum(sub_score_i * weight_i)  for all active sub-signals\n"
        "composite = clip(composite, 0, 100)\n\n"
        "Direction: >= 60 = BUY, <= 40 = SELL, else HOLD\n"
        "Strong signal: score >= 75 or <= 25 (1.5x size multiplier)"
    )

    # Confidence
    pdf.section_heading("5", "Confidence & Edge")
    pdf.code_block(
        "Confidence:\n"
        "  avg_deviation   = mean(abs(sub_score - 50) / 50)\n"
        "  signal_agreement = 1 - std(score_deviations)\n"
        "  confidence = clip(avg_dev * agreement * vol_factor, 0, 1)\n\n"
        "Edge:\n"
        "  estimated_prob = 0.50 + score_dist*0.20 + OBV/VPC bonuses\n"
        "  edge = (estimated_prob - 0.50) * vol_factor\n"
        "  Tradeable: edge >= 3%, confidence >= 10%, not HOLD"
    )

    # Weight table
    pdf.add_page()
    pdf.section_heading("6", "Weight Sets")
    pdf.subsection_heading("With Sentiment (9 signals)")
    pdf.info_table(
        ["Signal", "Weight"],
        [["Momentum", "14%"], ["RSI", "10%"], ["VWAP", "10%"], ["EMA", "10%"],
         ["Volume", "7%"], ["Vol-Price", "19%"], ["Sentiment", "8%"],
         ["Ichimoku", "12%"], ["Pattern", "10%"]],
        [95, 95]
    )
    pdf.subsection_heading("Without Sentiment (8 signals)")
    pdf.info_table(
        ["Signal", "Weight"],
        [["Momentum", "16%"], ["RSI", "11%"], ["VWAP", "11%"], ["EMA", "11%"],
         ["Volume", "8%"], ["Vol-Price", "21%"], ["Ichimoku", "12%"], ["Pattern", "10%"]],
        [95, 95]
    )

    # Pattern catalogue
    pdf.section_heading("7", "Pattern Recognition Catalogue")
    pdf.subsection_heading("Candlestick Patterns")
    pdf.info_table(
        ["Pattern", "Bias", "Strength"],
        [
            ["Hammer", "Bullish", "0.6"],
            ["Inverted Hammer", "Bullish", "0.5"],
            ["Shooting Star", "Bearish", "0.6"],
            ["Hanging Man", "Bearish", "0.5"],
            ["Doji", "Context", "0.3"],
            ["Bullish Engulfing", "Bullish", "0.5-0.8"],
            ["Bearish Engulfing", "Bearish", "0.5-0.8"],
            ["Morning Star", "Bullish", "0.7"],
            ["Evening Star", "Bearish", "0.7"],
            ["Three White Soldiers", "Bullish", "0.8"],
            ["Three Black Crows", "Bearish", "0.8"],
            ["Marubozu", "Context", "0.6"],
        ],
        [70, 60, 60]
    )

    return pdf


# ============================================================
# SPEC 02: Risk Management
# ============================================================
def build_spec02():
    pdf = SpecPDF("SPEC 02 - Risk Management", "Portfolio Framework & Kelly Criterion Position Sizing")
    pdf.alias_nb_pages()
    pdf.cover_page()

    pdf.add_page()
    pdf.section_heading("1", "Purpose")
    pdf.body_text(
        "The Risk Management layer controls position sizing, enforces drawdown limits, "
        "and manages the portfolio lifecycle. It uses a fractional Kelly Criterion adapted "
        "for equity trading, combined with hard caps to protect capital."
    )

    pdf.section_heading("2", "Capital & Risk Parameters")
    pdf.info_table(
        ["Parameter", "Value", "Description"],
        [
            ["STARTING_CAPITAL", "$100.00", "Initial bankroll"],
            ["MAX_POSITION_PCT", "5%", "Max single position"],
            ["MAX_DAILY_LOSS_PCT", "10%", "Stop trading threshold"],
            ["MAX_CONCURRENT", "5", "Max open positions"],
            ["MIN_TRADE_SIZE", "$5.00", "Minimum trade"],
            ["MAX_TRADE_SIZE", "$20.00", "Maximum trade"],
            ["KELLY_FRACTION", "0.25", "Quarter-Kelly"],
        ],
        [55, 40, 95]
    )

    pdf.section_heading("3", "Kelly Criterion Position Sizing")
    pdf.subsection_heading("3.1 Core Formula")
    pdf.code_block("f* = (p * b - q) / b\n\nwhere p=win prob, q=1-p, b=payoff ratio")

    pdf.subsection_heading("3.2 Win Probability Estimation")
    pdf.code_block(
        "score_dist = abs(signal.score - 50) / 50\n"
        "base_prob  = 0.50 + score_dist * 0.20    (50% to 70%)\n"
        "edge_boost = min(signal.edge * 0.5, 0.10) (capped at +10%)\n"
        "win_prob   = min(base_prob + edge_boost, 0.80)"
    )

    pdf.subsection_heading("3.3 Payoff Ratio")
    pdf.code_block("b = clip(1.0 + signal.edge * 10, 1.0, 3.0)")

    pdf.subsection_heading("3.4 Confidence-Weighted Kelly")
    pdf.code_block(
        "confidence_multiplier = 0.5 + 0.5 * signal.confidence\n"
        "fraction = kelly_f * 0.25 * confidence_multiplier\n"
        "raw_size = balance * fraction"
    )

    pdf.subsection_heading("3.5 Worked Example")
    pdf.code_block(
        "Signal: score=72, edge=0.07, confidence=0.65\n"
        "win_prob = 0.588 + 0.035 = 0.623\n"
        "b = 1.7,  q = 0.377\n"
        "kelly_f = (0.623*1.7-0.377)/1.7 = 0.401\n"
        "conf_mult = 0.825\n"
        "fraction = 0.401 * 0.25 * 0.825 = 8.27%\n"
        "With $100: raw=$8.27, after 5% cap: $5.00"
    )

    # Trade size pipeline
    pdf.add_page()
    pdf.section_heading("4", "Trade Size Constraint Pipeline")
    pdf.code_block(
        "1. signal.is_tradeable?        (edge>=0.03, conf>=0.10, not HOLD)\n"
        "2. Daily loss limit OK?        (daily P&L > -10%)\n"
        "3. Open positions < 5?\n"
        "4. kelly_size()                (raw Kelly-based size)\n"
        "5. Cap at MAX_POSITION_PCT     (5% of balance)\n"
        "6. Strong signal bonus?        (1.5x if score>=75 or <=25)\n"
        "7. Hard cap: MAX_TRADE_SIZE    ($20.00)\n"
        "8. Minimum: MIN_TRADE_SIZE     ($5.00)\n"
        "9. Available capital check\n"
        "   If any fails or size < $5 --> skip trade"
    )

    # Price targets
    pdf.section_heading("5", "Price Target System")
    pdf.subsection_heading("5.1 Volume Profile")
    pdf.code_block(
        "30-day lookback, 20 price bins:\n"
        "POC = center of highest-volume bin\n"
        "Value Area = 70% of total volume around POC\n"
        "VAH = upper bound, VAL = lower bound"
    )

    pdf.subsection_heading("5.2 Buy/Sell/Hold Targets")
    pdf.code_block(
        "buy_target  = 0.4*S1 + 0.3*VAL + 0.3*(price - ATR*0.5)\n"
        "sell_target = 0.4*R1 + 0.3*VAH + 0.3*(price + ATR*0.5)\n"
        "hold_low  = buy + (sell-buy)*0.25\n"
        "hold_high = buy + (sell-buy)*0.75"
    )

    # Volatility
    pdf.section_heading("6", "Volatility Filter")
    pdf.info_table(
        ["Annualized Vol", "Factor", "Interpretation"],
        [
            ["> 80%", "0.3", "Extreme volatility"],
            ["> 50%", "0.6", "High risk"],
            ["> 30%", "0.8", "Elevated"],
            ["> 15%", "1.0", "Normal (optimal)"],
            ["> 8%", "0.8", "Low volatility"],
            ["<= 8%", "0.4", "Dead market"],
        ],
        [50, 40, 100]
    )

    return pdf


# ============================================================
# SPEC 03: Sentiment Analysis
# ============================================================
def build_spec03():
    pdf = SpecPDF("SPEC 03 - Sentiment Analysis", "NLP Pipeline & Forum Scraping System")
    pdf.alias_nb_pages()
    pdf.cover_page()

    pdf.add_page()
    pdf.section_heading("1", "Purpose")
    pdf.body_text(
        "The Sentiment Pipeline scrapes Malaysian stock forums and news sites every 10 "
        "minutes, extracts stock mentions, scores sentiment using keyword dictionaries and "
        "LLM classification (Claude Sonnet), detects company events, and feeds a time-decay "
        "weighted sentiment score into the Signal Engine as one of 9 sub-signals (8% weight)."
    )

    pdf.section_heading("2", "Data Sources")
    pdf.info_table(
        ["Source", "Type", "Rate Limit", "Max Pages"],
        [
            ["KLSE Screener", "HTML + JSON API", "5s", "3"],
            ["i3investor", "HTML scrape", "5s", "1"],
            ["Reddit r/Bursa_MY", "JSON API", "2s", "25 posts"],
            ["Reddit r/MalaysianPF", "JSON API", "2s", "25 posts"],
            ["MalaysiaStock.Biz", "HTML scrape", "5s", "1"],
            ["Lowyat Forum", "HTML scrape", "5s", "2"],
            ["The Edge Malaysia", "HTML scrape", "5s", "1"],
            ["The Star Business", "HTML scrape", "5s", "1"],
        ],
        [55, 45, 35, 55]
    )

    pdf.section_heading("3", "Keyword Scoring")
    pdf.body_text("72 bilingual keywords (English + Malay): 24 EN bullish, 24 EN bearish, 13 MS bullish, 11 MS bearish.")
    pdf.code_block(
        "bullish_sum = sum(weight for bullish keywords found)\n"
        "bearish_sum = sum(weight for bearish keywords found)\n"
        "total = bullish_sum + bearish_sum\n"
        "if total == 0: raw = 0.0\n"
        "else: raw = (bullish - bearish) / total   # -1.0 to +1.0"
    )

    pdf.section_heading("4", "LLM Classification (Claude Sonnet)")
    pdf.info_table(
        ["Parameter", "Value"],
        [
            ["Model", "claude-sonnet-4-20250514"],
            ["Temperature", "0.0 (deterministic)"],
            ["Batch Size", "5 posts per call"],
            ["Max Calls/Cycle", "20"],
            ["Cache TTL", "3600s (1 hour)"],
            ["Daily Cost Cap", "$2.00 USD"],
        ],
        [80, 110]
    )
    pdf.body_text("Labels: POSITIVE / NEGATIVE / NOISE with confidence + reason. Consensus: majority vote with 50%/60% thresholds.")

    pdf.add_page()
    pdf.section_heading("5", "Time-Decay Aggregation")
    pdf.code_block(
        "decay_weight = exp(-age_hours / 240)\n"
        "  0 hours  -> 1.00    24 hours -> 0.90\n"
        "  5 days   -> 0.61    10 days  -> 0.37\n\n"
        "avg_sentiment  = sum(post_sent * decay) / sum(decay)\n"
        "sentiment_score = 50 + avg_sentiment * 50  (0-100)"
    )

    pdf.section_heading("6", "Event Detection")
    pdf.info_table(
        ["Event Type", "Impact", "Weight"],
        [
            ["New Contract", "Bullish", "2.0"],
            ["Contract Loss", "Bearish", "2.0"],
            ["Legal Issue", "Bearish", "2.5"],
            ["Earnings Positive", "Bullish", "2.0"],
            ["Earnings Negative", "Bearish", "2.0"],
            ["Management Change", "Neutral", "1.5"],
            ["Merger/Acquisition", "Bullish", "2.5"],
            ["Regulatory", "Neutral", "1.5"],
            ["Analyst Upgrade", "Bullish", "1.5"],
            ["Analyst Downgrade", "Bearish", "1.5"],
        ],
        [60, 50, 80]
    )

    pdf.section_heading("7", "Cost Model")
    pdf.info_table(
        ["Metric", "Value"],
        [
            ["Cost per batch", "~$0.01"],
            ["Cycles per day", "144"],
            ["Daily cost (typical)", "$1-3"],
            ["Daily cap", "$2.00"],
            ["Cache hit rate", "60-70%"],
        ],
        [80, 110]
    )

    return pdf


# ============================================================
# SPEC 04: AI Analysis Engine
# ============================================================
def build_spec04():
    pdf = SpecPDF("SPEC 04 - AI Analysis Engine", "Claude Sonnet Integration & Conflict Resolution")
    pdf.alias_nb_pages()
    pdf.cover_page()

    pdf.add_page()
    pdf.section_heading("1", "Purpose")
    pdf.body_text(
        "The AI Analysis Engine provides on-demand per-stock analysis via the dashboard "
        "search bar. All available data (technical signals, fundamentals, price targets, "
        "chart patterns, forum sentiment) is compiled into a structured prompt sent to "
        "Claude Sonnet, which assumes the persona of a Maybank Investment Bank equity "
        "research analyst. A rule-based fallback operates when the API is unavailable."
    )

    pdf.section_heading("2", "Data Gathering")
    pdf.body_text(
        "Five data gathering functions pull from existing in-memory objects with zero new "
        "computation: scanner data, fundamentals, price targets, patterns, and sentiment."
    )
    pdf.info_table(
        ["Data Source", "Function", "Key Fields"],
        [
            ["Scanner", "_get_scanner_data()", "score, direction, edge, confidence"],
            ["Fundamentals", "_get_fundamentals_data()", "PE, ROE, D/E, dividend yield"],
            ["Price Targets", "_get_price_targets()", "buy/sell/hold zones, prediction"],
            ["Patterns", "_get_pattern_data()", "pattern name, bias, strength"],
            ["Sentiment", "_get_sentiment_data()", "score, buzz, mention count"],
        ],
        [45, 55, 90]
    )

    pdf.section_heading("3", "Claude Sonnet Configuration")
    pdf.info_table(
        ["Parameter", "Value"],
        [
            ["Model", "claude-sonnet-4-20250514"],
            ["Max Tokens", "300"],
            ["Temperature", "0.0"],
            ["Cache TTL", "300s (5 min)"],
            ["Daily Call Cap", "200"],
            ["Est. Cost/Call", "~$0.003"],
        ],
        [80, 110]
    )

    pdf.section_heading("4", "Analyst Persona")
    pdf.body_text(
        "The prompt instructs Claude to act as a senior Maybank Investment Bank equity "
        "research analyst covering KLSE. It must cross-validate technical vs fundamental "
        "signals, resolve conflicts explicitly, and assess news/catalyst confidence."
    )

    pdf.add_page()
    pdf.section_heading("5", "Response Format")
    pdf.code_block(
        "RECOMMENDATION|BUY|0.85\n"
        "RISK|MEDIUM\n"
        "NEWS_CONFIDENCE|72\n"
        "CONFLICT_RESOLUTION|Technical bullish but D/E elevated...\n"
        "NARRATIVE|Maybank shows strong bullish momentum..."
    )

    pdf.section_heading("6", "Rule-Based Fallback")
    pdf.body_text("When the API is unavailable, recommendations are derived directly from scanner signals:")
    pdf.code_block(
        "score>=65 + direction=BUY  --> BUY\n"
        "score<=35 + direction=SELL --> SELL\n"
        "is_tradeable               --> TRADE\n"
        "else                       --> HOLD\n\n"
        "Risk: vol>0.03 or D/E>1.5 = HIGH\n"
        "       vol<0.015 & neutral  = LOW\n"
        "       else                 = MEDIUM"
    )

    pdf.section_heading("7", "Fundamental Scoring")
    pdf.info_table(
        ["Component", "Weight", "Scoring Range"],
        [
            ["Revenue Growth", "20%", "Growth tiers: 0-20-50-80-100"],
            ["Profit Margin", "15%", "Margin tiers: 0-25-50-75-100"],
            ["Return on Equity", "15%", "ROE tiers: 0-25-50-75-100"],
            ["Debt-to-Equity", "15%", "D/E inverse: low=100, high=0"],
            ["P/E Ratio", "15%", "P/E sweet spot: 8-15=100"],
            ["Free Cash Flow", "10%", "FCF yield tiers"],
            ["Dividend Yield", "10%", "Yield tiers: 0-25-50-75-100"],
        ],
        [55, 30, 105]
    )

    pdf.section_heading("8", "Conflict Detection")
    pdf.body_text(
        "Sub-signal conflict is flagged when the spread between max and min sub-scores "
        "exceeds 15 points. The AI must explicitly address such conflicts in its narrative."
    )

    return pdf


# ============================================================
# Main: Generate all 4 PDFs
# ============================================================
def main():
    specs = [
        ("SPEC-01-Signal-Engine.pdf", build_spec01),
        ("SPEC-02-Risk-Management.pdf", build_spec02),
        ("SPEC-03-Sentiment-Analysis.pdf", build_spec03),
        ("SPEC-04-AI-Analysis-Engine.pdf", build_spec04),
    ]

    for filename, builder in specs:
        filepath = os.path.join(OUTPUT_DIR, filename)
        print(f"Generating {filename}...")
        pdf = builder()
        pdf.output(filepath)
        size_kb = os.path.getsize(filepath) / 1024
        print(f"  -> {filepath} ({size_kb:.0f} KB)")

    print("\nAll 4 PDFs generated successfully!")


if __name__ == "__main__":
    main()
