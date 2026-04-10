#!/usr/bin/env python3
"""
Generate a single comprehensive illustrated PDF combining all 4 spec documents.
Uses fpdf2 with custom drawn diagrams, flow charts, and visual elements.
"""

import os
import math
from fpdf import FPDF

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# Color palette
# ============================================================
NAVY = (15, 23, 42)
BLUE = (37, 99, 235)
BLUE_LIGHT = (219, 234, 254)
BLUE_MID = (96, 165, 250)
GREEN = (22, 163, 74)
GREEN_LIGHT = (220, 252, 231)
RED = (220, 38, 38)
RED_LIGHT = (254, 226, 226)
AMBER = (217, 119, 6)
AMBER_LIGHT = (254, 243, 199)
PURPLE = (124, 58, 237)
PURPLE_LIGHT = (237, 233, 254)
TEAL = (13, 148, 136)
TEAL_LIGHT = (204, 251, 241)
GRAY = (100, 116, 139)
GRAY_LIGHT = (241, 245, 249)
DARK = (30, 41, 59)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
ORANGE = (234, 88, 12)
SLATE = (71, 85, 105)


class MasterPDF(FPDF):
    """Custom PDF with rich illustration helpers."""

    def __init__(self):
        super().__init__()
        self.doc_title = "MY Stock Market Trading Platform"
        self.current_section = ""
        self.set_auto_page_break(auto=True, margin=22)

    def header(self):
        if self.page_no() <= 2:
            return
        # Header bar
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 12, style="F")
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*WHITE)
        self.set_xy(10, 3)
        self.cell(95, 5, self.current_section, align="L")
        self.cell(95, 5, "MY Stock Market Trading Platform - Technical Specification", align="R")
        self.ln(10)

    def footer(self):
        self.set_y(-12)
        # Footer line
        self.set_draw_color(*BLUE)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*GRAY)
        self.set_y(-10)
        self.cell(95, 5, "Confidential", align="L")
        self.cell(95, 5, f"Page {self.page_no()}", align="R")

    # ============================================================
    # Drawing primitives
    # ============================================================

    def draw_rounded_rect(self, x, y, w, h, r, fill_color, border_color=None):
        """Draw a rounded rectangle."""
        self.set_fill_color(*fill_color)
        if border_color:
            self.set_draw_color(*border_color)
            self.set_line_width(0.4)
        # Approximate with rect (fpdf2 doesn't have native rounded rect easily)
        self.rect(x, y, w, h, style="FD" if border_color else "F")

    def draw_box(self, x, y, w, h, text, fill=BLUE, text_color=WHITE, font_size=8, bold=True):
        """Draw a colored box with centered text."""
        self.set_fill_color(*fill)
        self.rect(x, y, w, h, style="F")
        self.set_font("Helvetica", "B" if bold else "", font_size)
        self.set_text_color(*text_color)
        # Center text vertically and horizontally
        self.set_xy(x, y + (h - font_size * 0.35) / 2 - 1)
        self.cell(w, font_size * 0.35 + 2, text, align="C")

    def draw_arrow_down(self, x, y, length=8):
        """Draw a downward arrow."""
        self.set_draw_color(*GRAY)
        self.set_line_width(0.5)
        self.line(x, y, x, y + length)
        # Arrowhead
        self.line(x, y + length, x - 2, y + length - 3)
        self.line(x, y + length, x + 2, y + length - 3)

    def draw_arrow_right(self, x, y, length=10):
        """Draw a rightward arrow."""
        self.set_draw_color(*GRAY)
        self.set_line_width(0.5)
        self.line(x, y, x + length, y)
        self.line(x + length, y, x + length - 3, y - 2)
        self.line(x + length, y, x + length - 3, y + 2)

    def draw_connector(self, x1, y1, x2, y2):
        """Draw an L-shaped connector."""
        self.set_draw_color(*SLATE)
        self.set_line_width(0.4)
        mid_y = (y1 + y2) / 2
        self.line(x1, y1, x1, mid_y)
        self.line(x1, mid_y, x2, mid_y)
        self.line(x2, mid_y, x2, y2)

    def draw_metric_card(self, x, y, w, h, value, label, color=BLUE):
        """Draw a metric card with large value and small label."""
        # Background
        self.set_fill_color(*color)
        self.rect(x, y, w, h, style="F")
        # Value
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*WHITE)
        self.set_xy(x, y + 3)
        self.cell(w, 10, str(value), align="C")
        # Label
        self.set_font("Helvetica", "", 7)
        r, g, b = WHITE
        self.set_text_color(r, g, b)
        self.set_xy(x, y + h - 10)
        self.cell(w, 7, label, align="C")

    def draw_progress_bar(self, x, y, w, h, pct, color=BLUE, bg=GRAY_LIGHT, label=""):
        """Draw a horizontal progress/percentage bar."""
        # Background
        self.set_fill_color(*bg)
        self.rect(x, y, w, h, style="F")
        # Fill
        fill_w = w * min(pct / 100, 1.0)
        self.set_fill_color(*color)
        self.rect(x, y, fill_w, h, style="F")
        # Label
        if label:
            self.set_font("Helvetica", "", 6)
            tc = WHITE if pct > 40 else DARK
            self.set_text_color(*tc)
            self.set_xy(x + 2, y)
            self.cell(w - 4, h, f"{label} ({pct:.0f}%)", align="L")

    def draw_gauge(self, cx, cy, r, value, max_val, label, color=BLUE):
        """Draw a simple semi-circular gauge."""
        # Background arc (approximated with lines)
        segments = 20
        self.set_draw_color(*GRAY_LIGHT)
        self.set_line_width(3)
        for i in range(segments):
            angle1 = math.pi + (math.pi * i / segments)
            angle2 = math.pi + (math.pi * (i + 1) / segments)
            x1 = cx + r * math.cos(angle1)
            y1 = cy + r * math.sin(angle1)
            x2 = cx + r * math.cos(angle2)
            y2 = cy + r * math.sin(angle2)
            self.line(x1, y1, x2, y2)

        # Value arc
        fill_segments = int(segments * min(value / max_val, 1.0))
        self.set_draw_color(*color)
        for i in range(fill_segments):
            angle1 = math.pi + (math.pi * i / segments)
            angle2 = math.pi + (math.pi * (i + 1) / segments)
            x1 = cx + r * math.cos(angle1)
            y1 = cy + r * math.sin(angle1)
            x2 = cx + r * math.cos(angle2)
            y2 = cy + r * math.sin(angle2)
            self.line(x1, y1, x2, y2)

        # Value text
        self.set_line_width(0.3)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*DARK)
        self.set_xy(cx - 12, cy - 6)
        self.cell(24, 8, str(int(value)), align="C")
        # Label
        self.set_font("Helvetica", "", 6)
        self.set_text_color(*GRAY)
        self.set_xy(cx - 20, cy + 2)
        self.cell(40, 5, label, align="C")

    # ============================================================
    # Text helpers
    # ============================================================

    def section_title(self, number, text):
        """Large section heading with accent bar."""
        self.ln(4)
        self.set_fill_color(*BLUE)
        self.rect(10, self.get_y(), 4, 12, style="F")
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*NAVY)
        self.set_x(18)
        self.cell(0, 12, f"{number}  {text}", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def subsection(self, text):
        self.ln(2)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*DARK)
        self.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body(self, text):
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(*DARK)
        self.multi_cell(0, 5, text)
        self.ln(1.5)

    def code(self, text):
        """Code block with gray background."""
        self.set_fill_color(*GRAY_LIGHT)
        self.set_font("Courier", "", 8)
        self.set_text_color(*DARK)
        lines = text.strip().split("\n")
        h = len(lines) * 4.2 + 5
        if self.get_y() + h > 270:
            self.add_page()
        y0 = self.get_y()
        self.rect(12, y0, 186, h, style="F")
        # Left accent bar
        self.set_fill_color(*BLUE_MID)
        self.rect(12, y0, 2.5, h, style="F")
        self.set_xy(17, y0 + 2.5)
        for line in lines:
            self.cell(0, 4.2, line[:105], new_x="LMARGIN", new_y="NEXT")
            self.set_x(17)
        self.ln(3)

    def table(self, headers, rows, col_widths=None, header_color=NAVY):
        """Draw a professional table."""
        n = len(headers)
        if not col_widths:
            col_widths = [186 / n] * n

        # Check if table fits
        needed = 8 + len(rows) * 6 + 4
        if self.get_y() + needed > 270:
            self.add_page()

        x0 = 12
        # Header
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*header_color)
        self.set_text_color(*WHITE)
        self.set_x(x0)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=0, fill=True, align="C")
        self.ln()

        # Rows
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*DARK)
        for ri, row in enumerate(rows):
            if ri % 2 == 0:
                self.set_fill_color(*WHITE)
            else:
                self.set_fill_color(*GRAY_LIGHT)
            self.set_x(x0)
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 5.5, str(cell)[:50], border=0, fill=True, align="C")
            self.ln()

        # Bottom border
        self.set_draw_color(*GRAY)
        self.set_line_width(0.2)
        self.line(x0, self.get_y(), x0 + sum(col_widths), self.get_y())
        self.ln(3)

    def callout(self, text, icon="!", color=BLUE):
        """Info/warning callout box."""
        y0 = self.get_y()
        if y0 + 16 > 270:
            self.add_page()
            y0 = self.get_y()
        # Background
        light = (min(color[0] + 180, 245), min(color[1] + 180, 245), min(color[2] + 180, 245))
        self.set_fill_color(*light)
        self.rect(12, y0, 186, 14, style="F")
        # Left accent
        self.set_fill_color(*color)
        self.rect(12, y0, 3, 14, style="F")
        # Icon circle
        self.set_fill_color(*color)
        cx, cy = 22, y0 + 7
        self.ellipse(cx - 4, cy - 4, 8, 8, style="F")
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*WHITE)
        self.set_xy(cx - 4, cy - 3)
        self.cell(8, 6, icon, align="C")
        # Text
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*DARK)
        self.set_xy(30, y0 + 2)
        self.multi_cell(165, 4.5, text)
        self.set_y(y0 + 16)
        self.ln(2)

    def badge(self, x, y, text, color=GREEN):
        """Small colored badge."""
        w = len(text) * 2.5 + 6
        self.set_fill_color(*color)
        self.rect(x, y, w, 6, style="F")
        self.set_font("Helvetica", "B", 6)
        self.set_text_color(*WHITE)
        self.set_xy(x, y)
        self.cell(w, 6, text, align="C")


def build_master_pdf():
    pdf = MasterPDF()
    pdf.alias_nb_pages()

    # ============================================================
    # COVER PAGE
    # ============================================================
    pdf.add_page()
    # Full navy background
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, 210, 297, style="F")

    # Blue accent stripe
    pdf.set_fill_color(*BLUE)
    pdf.rect(0, 90, 210, 4, style="F")

    # Title
    pdf.set_font("Helvetica", "B", 32)
    pdf.set_text_color(*WHITE)
    pdf.set_xy(0, 105)
    pdf.cell(210, 16, "Technical Specification", align="C")
    pdf.set_xy(0, 122)
    pdf.set_font("Helvetica", "", 16)
    pdf.set_text_color(*BLUE_MID)
    pdf.cell(210, 10, "MY Stock Market Trading Platform", align="C")

    # Subtitle line
    pdf.set_xy(0, 140)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*GRAY)
    pdf.cell(210, 7, "Signal Engine  |  Risk Management  |  Sentiment Analysis  |  AI Engine", align="C")

    # Version info
    pdf.set_xy(0, 200)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*SLATE)
    pdf.cell(210, 6, "Version 1.0  |  April 2026", align="C")
    pdf.set_xy(0, 208)
    pdf.cell(210, 6, "Classification: Confidential", align="C")

    # Bottom accent
    pdf.set_fill_color(*BLUE)
    pdf.rect(0, 280, 210, 3, style="F")

    # ============================================================
    # TABLE OF CONTENTS
    # ============================================================
    pdf.add_page()
    pdf.set_fill_color(*WHITE)
    pdf.rect(0, 0, 210, 297, style="F")

    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*NAVY)
    pdf.set_xy(10, 20)
    pdf.cell(0, 12, "Table of Contents")
    pdf.set_draw_color(*BLUE)
    pdf.set_line_width(0.6)
    pdf.line(10, 34, 80, 34)

    toc_items = [
        ("01", "System Architecture Overview", "3"),
        ("02", "Signal Engine & Composite Scoring", "4"),
        ("03", "Sub-Signal Specifications (9 Signals)", "5"),
        ("04", "Risk Management & Kelly Criterion", "8"),
        ("05", "Price Target System", "10"),
        ("06", "Sentiment Analysis & NLP Pipeline", "11"),
        ("07", "AI Analysis Engine (Claude Sonnet)", "13"),
        ("08", "Fundamental Analysis", "15"),
        ("09", "Configuration Constants", "16"),
    ]

    y = 42
    for num, title, page in toc_items:
        # Section box
        pdf.set_fill_color(*BLUE)
        pdf.rect(15, y, 10, 8, style="F")
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*WHITE)
        pdf.set_xy(15, y)
        pdf.cell(10, 8, num, align="C")
        # Title
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*DARK)
        pdf.set_xy(28, y)
        pdf.cell(150, 8, title)
        # Page number
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(180, y)
        pdf.cell(15, 8, page, align="R")
        # Dotted line
        pdf.set_draw_color(*GRAY_LIGHT)
        pdf.set_line_width(0.2)
        dots_start = 28 + pdf.get_string_width(title) + 3
        pdf.dashed_line(dots_start, y + 6, 178, y + 6, dash_length=1, space_length=1.5)
        y += 12

    # ============================================================
    # SECTION 1: SYSTEM ARCHITECTURE OVERVIEW
    # ============================================================
    pdf.add_page()
    pdf.current_section = "01 - System Architecture Overview"
    pdf.section_title("01", "System Architecture Overview")

    pdf.body(
        "The platform analyzes ~148 KLSE-listed stocks every 5 minutes through a "
        "multi-layered pipeline: market data collection, technical signal generation, "
        "sentiment analysis, fundamental scoring, and AI-powered recommendation synthesis."
    )

    # ---- ARCHITECTURE DIAGRAM ----
    y_start = pdf.get_y() + 2
    # Data sources row
    sources = [
        ("Yahoo Finance", BLUE, 14),
        ("8 Forum Sources", TEAL, 58),
        ("Company Filings", PURPLE, 102),
        ("Pattern Engine", AMBER, 146),
    ]
    for label, color, x in sources:
        pdf.draw_box(x, y_start, 40, 10, label, fill=color, font_size=7)

    # Arrows down
    for x in [34, 78, 122, 166]:
        pdf.draw_arrow_down(x, y_start + 10, 8)

    # Processing row
    y2 = y_start + 20
    procs = [
        ("Market Data\nAggregator", BLUE, 10, 44),
        ("Sentiment\nPipeline", TEAL, 54, 44),
        ("Fundamental\nAnalyzer", PURPLE, 98, 44),
        ("Chart Pattern\nRecognition", AMBER, 142, 44),
    ]
    for label, color, x, w in procs:
        pdf.draw_box(x, y2, w, 12, label.split("\n")[0], fill=color, font_size=7)

    # Converge arrows to Signal Engine
    y3 = y2 + 14
    for x in [32, 76, 120, 164]:
        pdf.draw_arrow_down(x, y3, 6)

    # Signal Engine (wide box)
    y4 = y3 + 8
    pdf.set_fill_color(*NAVY)
    pdf.rect(20, y4, 170, 14, style="F")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*WHITE)
    pdf.set_xy(20, y4 + 2)
    pdf.cell(170, 10, "SIGNAL ENGINE  -  9 Sub-Signals  ->  Composite Score (0-100)", align="C")

    # Arrow down
    pdf.draw_arrow_down(105, y4 + 14, 8)

    # Three output boxes
    y5 = y4 + 24
    outputs = [
        ("Risk Manager\n(Kelly Sizing)", GREEN, 15),
        ("Price Analyzer\n(Targets)", BLUE, 75),
        ("AI Analysis\n(Claude Sonnet)", PURPLE, 135),
    ]
    for label, color, x in outputs:
        pdf.draw_box(x, y5, 55, 12, label.split("\n")[0], fill=color, font_size=7)

    # Arrow down to final
    for x in [42, 102, 162]:
        pdf.draw_arrow_down(x, y5 + 12, 6)

    y6 = y5 + 20
    pdf.draw_box(20, y6, 170, 10, "DASHBOARD  -  BUY / SELL / HOLD / TRADE Recommendations", fill=NAVY, font_size=8)

    pdf.set_y(y6 + 16)

    # Key metrics row
    pdf.subsection("Platform Key Metrics")
    my = pdf.get_y()
    cards = [
        ("148", "KLSE Stocks", BLUE),
        ("9", "Sub-Signals", TEAL),
        ("8", "Forum Sources", PURPLE),
        ("5 min", "Scan Cycle", GREEN),
        ("72", "Sentiment Keywords", AMBER),
        ("12+8", "Chart Patterns", RED),
    ]
    cx = 14
    for val, lab, color in cards:
        pdf.draw_metric_card(cx, my, 28, 20, val, lab, color)
        cx += 30
    pdf.set_y(my + 24)

    # ============================================================
    # SECTION 2: SIGNAL ENGINE
    # ============================================================
    pdf.add_page()
    pdf.current_section = "02 - Signal Engine"
    pdf.section_title("02", "Signal Engine & Composite Scoring")

    pdf.body(
        "The Signal Engine generates BUY/SELL/HOLD signals by combining 9 independent "
        "technical sub-signals into a weighted composite score (0-100). Each sub-signal maps "
        "its indicator to a 0-100 scale: 0=strongly bearish, 50=neutral, 100=strongly bullish."
    )

    # ---- SIGNAL WEIGHT DIAGRAM ----
    pdf.subsection("Signal Weight Distribution")
    y0 = pdf.get_y() + 1
    signals = [
        ("Vol-Price Analysis", 19, BLUE),
        ("Momentum", 14, TEAL),
        ("Ichimoku Cloud", 12, PURPLE),
        ("RSI (Mean Revert)", 10, GREEN),
        ("VWAP Deviation", 10, AMBER),
        ("EMA Crossover", 10, RED),
        ("Pattern Recog.", 10, ORANGE),
        ("Sentiment (NLP)", 8, SLATE),
        ("Volume Activity", 7, GRAY),
    ]

    for i, (name, weight, color) in enumerate(signals):
        y = y0 + i * 8
        # Label
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*DARK)
        pdf.set_xy(12, y)
        pdf.cell(38, 6, name, align="R")
        # Bar
        bar_w = weight * 5.5  # scale factor
        pdf.set_fill_color(*color)
        pdf.rect(52, y + 0.5, bar_w, 5, style="F")
        # Percentage
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*color)
        pdf.set_xy(52 + bar_w + 2, y)
        pdf.cell(15, 6, f"{weight}%")

    pdf.set_y(y0 + len(signals) * 8 + 4)

    # Direction thresholds diagram
    pdf.subsection("Composite Score -> Direction")
    y0 = pdf.get_y()
    # Draw score bar
    bar_x = 25
    bar_w = 160
    bar_h = 12

    # SELL zone (0-40)
    sell_w = bar_w * 0.4
    pdf.set_fill_color(*RED_LIGHT)
    pdf.rect(bar_x, y0, sell_w, bar_h, style="F")
    pdf.set_fill_color(*RED)
    pdf.rect(bar_x, y0, sell_w, 2, style="F")

    # HOLD zone (40-60)
    hold_w = bar_w * 0.2
    pdf.set_fill_color(*GRAY_LIGHT)
    pdf.rect(bar_x + sell_w, y0, hold_w, bar_h, style="F")
    pdf.set_fill_color(*GRAY)
    pdf.rect(bar_x + sell_w, y0, hold_w, 2, style="F")

    # BUY zone (60-100)
    buy_w = bar_w * 0.4
    pdf.set_fill_color(*GREEN_LIGHT)
    pdf.rect(bar_x + sell_w + hold_w, y0, buy_w, bar_h, style="F")
    pdf.set_fill_color(*GREEN)
    pdf.rect(bar_x + sell_w + hold_w, y0, buy_w, 2, style="F")

    # Labels
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*RED)
    pdf.set_xy(bar_x, y0 + 3)
    pdf.cell(sell_w, 7, "SELL (<= 40)", align="C")
    pdf.set_text_color(*GRAY)
    pdf.set_xy(bar_x + sell_w, y0 + 3)
    pdf.cell(hold_w, 7, "HOLD", align="C")
    pdf.set_text_color(*GREEN)
    pdf.set_xy(bar_x + sell_w + hold_w, y0 + 3)
    pdf.cell(buy_w, 7, "BUY (>= 60)", align="C")

    # Scale markers
    pdf.set_font("Helvetica", "", 6)
    pdf.set_text_color(*DARK)
    for val in [0, 25, 40, 50, 60, 75, 100]:
        mx = bar_x + bar_w * val / 100
        pdf.set_xy(mx - 4, y0 + bar_h + 1)
        pdf.cell(8, 4, str(val), align="C")

    pdf.set_y(y0 + bar_h + 8)

    # Confidence & Edge formulas
    pdf.subsection("Confidence & Edge Calculation")
    pdf.code(
        "CONFIDENCE:\n"
        "  score_deviations = [abs(sub_score - 50) / 50 for each signal]\n"
        "  avg_deviation    = mean(score_deviations)\n"
        "  signal_agreement = 1.0 - std(score_deviations)\n"
        "  vol_factor       = volatility_filter(annualized_vol)  # 0.3-1.0\n"
        "  confidence       = clip(avg_dev * agreement * vol_factor, 0, 1)\n"
        "\n"
        "EDGE (Probability-Based):\n"
        "  estimated_prob = 0.50 + (score_dist * 0.20)\n"
        "                 + OBV confirmation bonus   (up to +5%)\n"
        "                 + Vol-price confirmation    (up to +5%)\n"
        "  estimated_prob = min(estimated_prob, 0.80)\n"
        "  edge = (estimated_prob - 0.50) * vol_factor\n"
        "\n"
        "TRADEABLE: edge >= 3%, confidence >= 10%, direction != HOLD"
    )

    # ============================================================
    # SECTION 3: SUB-SIGNAL DETAILS
    # ============================================================
    pdf.add_page()
    pdf.current_section = "03 - Sub-Signal Specifications"
    pdf.section_title("03", "Sub-Signal Specifications")

    # Momentum
    pdf.subsection("3.1  Momentum Signal (14%)")
    pdf.table(
        ["Parameter", "Value", "Description"],
        [
            ["Window", "10 days", "Lookback period for return calculation"],
            ["Threshold", "0.02 (2%)", "Significant momentum threshold"],
            ["Noise Filter", "< 0.6%", "abs(mom) < threshold*0.3 returns 50"],
        ],
        [40, 40, 106]
    )
    pdf.code("scaled = momentum / (threshold * 3)\nscore  = clip(50 + scaled * 50, 0, 100)\n\n+6% momentum -> score 100 (max bullish)\n-6% momentum -> score 0   (max bearish)")

    # RSI
    pdf.subsection("3.2  RSI Signal (10%) - Mean Reversion")
    pdf.body("Counter-trend logic: overbought = bearish (expect pullback), oversold = bullish (expect bounce).")
    pdf.code("RSI >= 70 (overbought): score = clip(50 - excess*40, 5, 50)   # bearish\nRSI <= 30 (oversold):   score = clip(50 + excess*40, 50, 95)  # bullish\nNeutral zone:           score = 50 + (RSI-50) * 0.3")

    # VWAP
    pdf.subsection("3.3  VWAP Deviation Signal (10%)")
    pdf.body("Dual-mode: moderate deviation = trend continuation; extreme deviation (>4x) = mean reversion.")
    pdf.code("Moderate (< 4x threshold): score = clip(50 + dev/(thr*8)*50, 10, 90)\nExtreme  (>= 4x):         score = clip(50 - dev/(thr*8)*50, 10, 90)")

    # EMA
    pdf.subsection("3.4  EMA Crossover Signal (10%)")
    pdf.code("diff_pct     = (EMA_12 - EMA_26) / EMA_26\nprice_vs_ema = (price - EMA_12) / EMA_12\ncombined     = diff_pct * 0.7 + price_vs_ema * 0.3\nscore        = clip(50 + combined * 500, 10, 90)")

    # Volume
    pdf.subsection("3.5  Volume Activity Signal (7%)")
    pdf.body("Volume spikes (>2x average) confirm momentum direction. High volume without direction = uncertain.")

    # Volume-Price (heaviest)
    pdf.add_page()
    pdf.subsection("3.6  Volume-Price Analysis (19%) - Heaviest Signal")
    pdf.callout("This is the most heavily weighted signal, combining three internal components.", "i", BLUE)

    pdf.table(
        ["Component", "Weight", "Source", "Formula"],
        [
            ["OBV Trend", "40%", "On-Balance Volume slope", "clip(50 + obv*40, 10, 90)"],
            ["Vol-Price Confirm", "35%", "Volume & price correlation", "clip(50 + vpc*40, 10, 90)"],
            ["Activity Level", "25%", "Volume trend + ratio", "Directional with boost"],
        ],
        [38, 20, 55, 73]
    )
    pdf.code("vp_score = OBV_score*0.40 + Confirm_score*0.35 + Activity_score*0.25\nvp_score = clip(vp_score, 0, 100)\n\nVolume ratio > 1.5x bonus: boost = min((ratio-1.0)*5, 10) applied directionally")

    # Sentiment
    pdf.subsection("3.7  Sentiment Signal (8%)")
    pdf.body(
        "Only active when mention_count >= 2 for a stock. Score from the NLP Sentiment Pipeline "
        "(see Section 06). When absent, other signals are re-weighted to sum to 100%."
    )
    pdf.table(
        ["Condition", "Result"],
        [
            ["Score > 65", "Reason: 'Forum bullish (N mentions)'"],
            ["Score < 35", "Reason: 'Forum bearish (N mentions)'"],
            ["Buzz > 70", "Reason: 'High forum buzz: N mentions'"],
            ["< 2 mentions", "Signal excluded, 8-signal weights used"],
        ],
        [60, 126]
    )

    # Ichimoku
    pdf.subsection("3.8  Ichimoku Cloud Signal (12%)")
    pdf.body("Starts at 50.0 and applies additive adjustments from 5 components:")

    # Visual component diagram
    y0 = pdf.get_y()
    components = [
        ("Cloud Color", "+10 / -10", BLUE),
        ("Price vs Cloud", "+15 / -15", GREEN),
        ("TK Cross", "+12 / -12", PURPLE),
        ("TK Diff", "+/-diff*200", AMBER),
        ("Cloud Thick.", "+5 / -5", TEAL),
    ]
    cx = 14
    for name, adj, color in components:
        pdf.draw_box(cx, y0, 35, 8, name, fill=color, font_size=6.5)
        pdf.set_font("Helvetica", "", 6)
        pdf.set_text_color(*DARK)
        pdf.set_xy(cx, y0 + 8)
        pdf.cell(35, 5, adj, align="C")
        cx += 37
    pdf.set_y(y0 + 16)
    pdf.body("Final score clipped to range [5, 95].")

    # Pattern
    pdf.subsection("3.9  Pattern Recognition Signal (10%)")
    pdf.body("12 candlestick patterns + 8 chart formations analyzed on last 3-30 candles.")

    pdf.add_page()
    pdf.table(
        ["Pattern", "Bias", "Strength", "Pattern", "Bias", "Strength"],
        [
            ["Hammer", "Bull", "0.6", "Shooting Star", "Bear", "0.6"],
            ["Inv. Hammer", "Bull", "0.5", "Hanging Man", "Bear", "0.5"],
            ["Bull Engulfing", "Bull", "0.5-0.8", "Bear Engulfing", "Bear", "0.5-0.8"],
            ["Morning Star", "Bull", "0.7", "Evening Star", "Bear", "0.7"],
            ["3 White Soldiers", "Bull", "0.8", "3 Black Crows", "Bear", "0.8"],
            ["Doji", "Context", "0.3", "Marubozu", "Context", "0.6"],
        ],
        [30, 16, 22, 30, 16, 22],
        header_color=PURPLE
    )

    pdf.table(
        ["Chart Formation", "Bias", "Strength", "Method"],
        [
            ["Double Top", "Bearish", "0.7", "Two peaks within 2%, price below neckline"],
            ["Double Bottom", "Bullish", "0.7", "Two troughs within 2%, above neckline"],
            ["Resistance Breakout", "Bullish", "0.7", "Close > high + volume > 1.3x avg"],
            ["Support Breakdown", "Bearish", "0.7", "Close < low + volume > 1.3x avg"],
            ["Triangle Breakout", "Bullish", "0.6-0.7", "Converging highs/lows, break above"],
            ["Triangle Breakdown", "Bearish", "0.6-0.7", "Converging highs/lows, break below"],
        ],
        [40, 22, 22, 102],
        header_color=PURPLE
    )

    pdf.code("net_strength = (bull_strength - bear_strength) / (bull + bear)\npattern_score = clip(50 + net_strength * 40, 5, 95)\nconfidence    = min(total_strength / 3.0, 1.0)")

    # ============================================================
    # SECTION 4: RISK MANAGEMENT
    # ============================================================
    pdf.add_page()
    pdf.current_section = "04 - Risk Management"
    pdf.section_title("04", "Risk Management & Kelly Criterion")

    pdf.body(
        "The Risk Management layer controls position sizing via fractional Kelly Criterion, "
        "enforces drawdown limits, and manages the portfolio lifecycle with hard caps."
    )

    # Capital params as metric cards
    pdf.subsection("Capital & Risk Parameters")
    y0 = pdf.get_y()
    params = [
        ("$100", "Starting Capital", BLUE),
        ("5%", "Max Position", TEAL),
        ("10%", "Daily Loss Cap", RED),
        ("5", "Max Positions", GREEN),
        ("$5-$20", "Trade Range", AMBER),
        ("0.25", "Kelly Fraction", PURPLE),
    ]
    cx = 14
    for val, lab, color in params:
        pdf.draw_metric_card(cx, y0, 28, 20, val, lab, color)
        cx += 30
    pdf.set_y(y0 + 24)

    # Kelly formula
    pdf.subsection("Kelly Criterion Formula")
    pdf.code(
        "CORE:  f* = (p * b - q) / b\n"
        "  p = win probability,  q = 1-p,  b = payoff ratio\n"
        "\n"
        "WIN PROBABILITY (from signal):\n"
        "  score_dist = abs(score - 50) / 50            # 0 to 1\n"
        "  base_prob  = 0.50 + score_dist * 0.20        # 50-70%\n"
        "  edge_boost = min(signal.edge * 0.5, 0.10)    # up to +10%\n"
        "  win_prob   = min(base_prob + edge_boost, 0.80)\n"
        "\n"
        "PAYOFF RATIO:\n"
        "  b = clip(1.0 + signal.edge * 10, 1.0, 3.0)\n"
        "\n"
        "CONFIDENCE-WEIGHTED:\n"
        "  conf_mult = 0.5 + 0.5 * signal.confidence   # 0.5-1.0\n"
        "  fraction  = kelly_f * 0.25 * conf_mult\n"
        "  raw_size  = balance * fraction"
    )

    # Worked example callout
    pdf.callout(
        "Example: score=72, edge=0.07, conf=0.65 -> win=62.3%, b=1.7, kelly=40.1%, "
        "quarter-kelly with conf: 8.27% of $100 = $8.27, capped at 5% = $5.00",
        "Ex", GREEN
    )

    # Trade size pipeline
    pdf.subsection("Trade Size Pipeline")
    y0 = pdf.get_y()
    steps = [
        ("Tradeable?", "edge>=3%, conf>=10%", BLUE),
        ("Daily loss OK?", "P&L > -10%", RED),
        ("Positions < 5?", "concurrent check", AMBER),
        ("Kelly size", "fractional Kelly", GREEN),
        ("Cap 5%", "MAX_POSITION_PCT", TEAL),
        ("Strong bonus?", "1.5x if score>=75", PURPLE),
        ("Hard cap $20", "MAX_TRADE_SIZE", NAVY),
        ("Min $5?", "MIN_TRADE_SIZE", SLATE),
    ]
    for i, (step, desc, color) in enumerate(steps):
        x = 14 + (i % 4) * 47
        y = y0 + (i // 4) * 16
        pdf.draw_box(x, y, 44, 8, step, fill=color, font_size=6.5)
        pdf.set_font("Helvetica", "", 5.5)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(x, y + 8)
        pdf.cell(44, 4, desc, align="C")
        # Arrow
        if i < len(steps) - 1 and i % 4 != 3:
            pdf.draw_arrow_right(x + 44, y + 4, 3)

    pdf.set_y(y0 + 36)

    # Volatility filter
    pdf.subsection("Volatility Confidence Filter")
    pdf.table(
        ["Annualized Vol", "Factor", "Interpretation"],
        [
            ["> 80%", "0.3", "Extreme - low confidence"],
            ["> 50%", "0.6", "High risk"],
            ["> 30%", "0.8", "Elevated but tradeable"],
            ["15-30%", "1.0", "Normal (optimal)"],
            ["8-15%", "0.8", "Low volatility"],
            ["< 8%", "0.4", "Dead market"],
        ],
        [50, 40, 96]
    )

    # ============================================================
    # SECTION 5: PRICE TARGETS
    # ============================================================
    pdf.add_page()
    pdf.current_section = "05 - Price Target System"
    pdf.section_title("05", "Price Target System")

    pdf.subsection("Volume Profile (VPOC / VAH / VAL)")
    pdf.code(
        "30-day lookback, 20 price bins:\n"
        "POC (Point of Control) = center of highest-volume bin\n"
        "Value Area = 70% of total volume, expanding from POC\n"
        "VAH = upper bound,  VAL = lower bound"
    )

    pdf.subsection("Buy/Sell/Hold Target Formulas")
    pdf.code(
        "buy_target  = 0.4*S1 + 0.3*VAL + 0.3*(price - ATR*0.5)\n"
        "buy_strong  = 0.4*S2 + 0.3*VAL + 0.3*(price - ATR*1.5)\n"
        "\n"
        "sell_target = 0.4*R1 + 0.3*VAH + 0.3*(price + ATR*0.5)\n"
        "sell_strong = 0.4*R2 + 0.3*VAH + 0.3*(price + ATR*1.5)\n"
        "\n"
        "hold_low  = buy_target + (sell_target - buy_target) * 0.25\n"
        "hold_high = buy_target + (sell_target - buy_target) * 0.75"
    )

    # Price zones visual
    pdf.subsection("Price Zone Visualization")
    y0 = pdf.get_y()
    zones = [
        ("Strong Buy", GREEN, 14, 36),
        ("Buy Target", (34, 197, 94), 52, 36),
        ("Hold Low", GRAY, 90, 15),
        ("Hold High", GRAY, 107, 15),
        ("Sell Target", (251, 146, 60), 124, 36),
        ("Strong Sell", RED, 162, 36),
    ]
    for label, color, x, w in zones:
        pdf.draw_box(x, y0, w, 10, label, fill=color, font_size=6.5)
    pdf.set_y(y0 + 14)

    pdf.subsection("Price Prediction Model (7 Weak Signals)")
    pdf.table(
        ["Signal", "Weight", "Source"],
        [
            ["Momentum persistence", "20%", "Short-term price trend (normalized)"],
            ["RSI mean reversion", "10%", "Extreme RSI reversal expectation"],
            ["OBV trend", "20%", "Accumulation/distribution pressure"],
            ["Vol-price confirmation", "15%", "Volume validating price direction"],
            ["Signal score bias", "15%", "Composite signal direction"],
            ["Price velocity", "10%", "Acceleration (5d vs 10d returns)"],
            ["Volume trend", "10%", "Rising/falling participation"],
        ],
        [48, 22, 116],
        header_color=TEAL
    )

    pdf.code(
        "effective_weight = base_weight * (0.5 + 0.5 * confidence)\n"
        "composite = sum(signal * eff_weight) / sum(eff_weight)\n"
        "expected_move = composite * (ATR / price)\n"
        "\n"
        "Direction: composite > +0.15 = UP, < -0.15 = DOWN, else NEUTRAL\n"
        "Confidence: clip(total_conf * abs(composite) * 2, 0, 1)"
    )

    # ============================================================
    # SECTION 6: SENTIMENT ANALYSIS
    # ============================================================
    pdf.add_page()
    pdf.current_section = "06 - Sentiment Analysis"
    pdf.section_title("06", "Sentiment Analysis & NLP Pipeline")

    pdf.body(
        "The Sentiment Pipeline scrapes 8 Malaysian stock forums/news sites every 10 minutes, "
        "extracts stock mentions, scores sentiment using 72 bilingual keywords + Claude Sonnet "
        "LLM classification, detects catalysts, and outputs a time-decay weighted score."
    )

    # Pipeline diagram
    pdf.subsection("Pipeline Architecture")
    y0 = pdf.get_y()

    # Source boxes
    src_names = ["KLSE\nScreener", "i3investor", "Reddit\n(2 subs)", "Lowyat", "Malaysia\nStock", "TheEdge", "TheStar", "News\nAPIs"]
    for i, name in enumerate(src_names):
        x = 12 + i * 23
        pdf.draw_box(x, y0, 21, 10, name.split("\n")[0], fill=TEAL, font_size=5.5)

    pdf.draw_arrow_down(105, y0 + 10, 6)

    y1 = y0 + 18
    pdf.draw_box(30, y1, 150, 9, "HTML Parsing (BeautifulSoup4) + JSON APIs (Reddit) - Rate Limited", fill=SLATE, font_size=7)
    pdf.draw_arrow_down(105, y1 + 9, 6)

    y2 = y1 + 17
    pdf.draw_box(30, y2, 150, 9, "Stock Mention Detection - Alias Map (name, ticker, code, sector)", fill=BLUE, font_size=7)
    pdf.draw_arrow_down(80, y2 + 9, 6)
    pdf.draw_arrow_down(130, y2 + 9, 6)

    y3 = y2 + 17
    pdf.draw_box(30, y3, 68, 9, "Keyword Scoring (72 words)", fill=AMBER, font_size=7)
    pdf.draw_box(110, y3, 70, 9, "LLM Classification (Claude)", fill=PURPLE, font_size=7)

    pdf.draw_arrow_down(80, y3 + 9, 6)
    pdf.draw_arrow_down(130, y3 + 9, 6)

    y4 = y3 + 17
    pdf.draw_box(50, y4, 110, 9, "Time-Decay Weighted Aggregation (10-day window)", fill=GREEN, font_size=7)
    pdf.draw_arrow_down(105, y4 + 9, 6)

    y5 = y4 + 17
    pdf.draw_box(50, y5, 110, 9, "StockSentiment -> Signal Engine (8% weight)", fill=NAVY, font_size=7)

    pdf.set_y(y5 + 14)

    # Data sources table
    pdf.subsection("Data Sources")
    pdf.table(
        ["Source", "Type", "Rate Limit", "Volume"],
        [
            ["KLSE Screener", "HTML + JSON", "5s delay", "3 pages"],
            ["i3investor", "HTML scrape", "5s delay", "1 page"],
            ["Reddit r/Bursa_MY", "JSON API", "2s delay", "25 posts"],
            ["Reddit r/MalaysianPF", "JSON API", "2s delay", "25 posts"],
            ["MalaysiaStock.Biz", "HTML scrape", "5s delay", "1 page"],
            ["Lowyat Forum", "HTML scrape", "5s delay", "2 pages"],
            ["The Edge Malaysia", "HTML scrape", "5s delay", "1 page"],
            ["The Star Business", "HTML scrape", "5s delay", "1 page"],
        ],
        [48, 38, 35, 65],
        header_color=TEAL
    )

    pdf.add_page()
    # Keyword scoring
    pdf.subsection("Keyword Sentiment Scoring")
    pdf.body("72 bilingual keywords: 24 English bullish, 24 English bearish, 13 Malay bullish, 11 Malay bearish.")
    pdf.code(
        "bullish_sum = sum(weight for each bullish keyword found)\n"
        "bearish_sum = sum(weight for each bearish keyword found)\n"
        "total = bullish_sum + bearish_sum\n"
        "if total == 0: raw_score = 0.0\n"
        "else:          raw_score = (bullish - bearish) / total  # -1.0 to +1.0"
    )

    # LLM config
    pdf.subsection("LLM Classification (Claude Sonnet)")
    pdf.table(
        ["Parameter", "Value"],
        [
            ["Model", "claude-sonnet-4-20250514"],
            ["Temperature", "0.0 (deterministic)"],
            ["Batch Size", "5 posts per API call"],
            ["Max Calls/Cycle", "20"],
            ["Cache TTL", "3600s (1 hour)"],
            ["Daily Cost Cap", "$2.00 USD"],
            ["Labels", "POSITIVE / NEGATIVE / NOISE"],
        ],
        [65, 121],
        header_color=PURPLE
    )

    # Time decay
    pdf.subsection("Time-Decay Aggregation")
    pdf.code(
        "decay_weight = exp(-age_hours / 240)\n"
        "\n"
        "  Age         Weight\n"
        "  0 hours     1.00 (full weight)\n"
        "  24 hours    0.90\n"
        "  5 days      0.61\n"
        "  10 days     0.37 (cutoff)\n"
        "\n"
        "avg_sentiment   = sum(post_sent * decay_wt) / sum(decay_wt)\n"
        "sentiment_score = 50 + avg_sentiment * 50     # mapped to 0-100"
    )

    # Event detection
    pdf.subsection("Event / Catalyst Detection")
    pdf.table(
        ["Event Type", "Impact", "Wt", "Example Keywords"],
        [
            ["New Contract", "Bullish", "2.0", "awarded, kontrak baru, LOA"],
            ["Legal Issue", "Bearish", "2.5", "lawsuit, MACC, fraud, saman"],
            ["Earnings +", "Bullish", "2.0", "record profit, beat estimates"],
            ["Earnings -", "Bearish", "2.0", "profit warning, rugi"],
            ["M&A", "Bullish", "2.5", "acquisition, takeover, general offer"],
            ["Analyst Up", "Bullish", "1.5", "upgrade, outperform"],
            ["Analyst Down", "Bearish", "1.5", "downgrade, underweight"],
        ],
        [38, 22, 14, 112],
        header_color=AMBER
    )

    # ============================================================
    # SECTION 7: AI ANALYSIS ENGINE
    # ============================================================
    pdf.add_page()
    pdf.current_section = "07 - AI Analysis Engine"
    pdf.section_title("07", "AI Analysis Engine (Claude Sonnet)")

    pdf.body(
        "The AI Analysis Engine provides on-demand per-stock analysis via the dashboard search bar. "
        "All data is compiled into a structured prompt sent to Claude Sonnet, which assumes the "
        "persona of a Maybank Investment Bank equity research analyst."
    )

    # Architecture diagram
    pdf.subsection("Analysis Flow")
    y0 = pdf.get_y()

    # User input
    pdf.draw_box(70, y0, 70, 9, "User selects stock in search bar", fill=SLATE, font_size=7)
    pdf.draw_arrow_down(105, y0 + 9, 6)

    # Data gathering boxes
    y1 = y0 + 17
    data_boxes = [
        ("Scanner\nData", BLUE, 12),
        ("Fundamental\nScores", TEAL, 50),
        ("Price\nTargets", GREEN, 88),
        ("Pattern\nSignals", AMBER, 126),
        ("Sentiment\nData", PURPLE, 164),
    ]
    for label, color, x in data_boxes:
        pdf.draw_box(x, y1, 34, 10, label.split("\n")[0], fill=color, font_size=6.5)

    # Converge
    for x in [29, 67, 105, 143, 181]:
        pdf.draw_arrow_down(x, y1 + 10, 5)

    y2 = y1 + 17
    pdf.draw_box(20, y2, 170, 12, "Claude Sonnet API  |  Maybank IB Analyst Persona  |  Structured Prompt", fill=NAVY, font_size=7.5)
    pdf.draw_arrow_down(105, y2 + 12, 6)

    y3 = y2 + 20
    outputs = [
        ("BUY/SELL/HOLD/TRADE", GREEN, 12, 42),
        ("Risk Level", RED, 56, 30),
        ("Confidence %", BLUE, 88, 30),
        ("Narrative", PURPLE, 120, 35),
        ("Conflict\nResolution", AMBER, 157, 35),
    ]
    for label, color, x, w in outputs:
        pdf.draw_box(x, y3, w, 9, label.split("\n")[0], fill=color, font_size=6)

    pdf.set_y(y3 + 14)

    # Claude config
    pdf.subsection("Claude Sonnet Configuration")
    pdf.table(
        ["Parameter", "Value"],
        [
            ["Model", "claude-sonnet-4-20250514"],
            ["Max Tokens", "300"],
            ["Temperature", "0.0 (deterministic)"],
            ["Cache TTL", "300 seconds (5 min)"],
            ["Daily Call Cap", "200 calls"],
            ["Est. Cost/Call", "~$0.003"],
            ["Daily Cost", "$0.06-$0.25 (typical)"],
        ],
        [65, 121],
        header_color=NAVY
    )

    # Response format
    pdf.subsection("Structured Response Format")
    pdf.code(
        "RECOMMENDATION|BUY|0.85\n"
        "RISK|MEDIUM\n"
        "NEWS_CONFIDENCE|72\n"
        "CONFLICT_RESOLUTION|Technical bullish but D/E ratio elevated...\n"
        "NARRATIVE|Maybank shows strong bullish momentum with OBV accumulation..."
    )

    # Rule-based fallback
    pdf.add_page()
    pdf.subsection("Rule-Based Fallback (No API)")
    pdf.callout(
        "When the Claude API is unavailable, the system generates recommendations directly "
        "from scanner signals. This ensures 100% uptime for the analysis feature.",
        "!", AMBER
    )
    pdf.code(
        "score >= 65 + direction = BUY   -->  BUY\n"
        "score <= 35 + direction = SELL  -->  SELL\n"
        "is_tradeable                    -->  TRADE\n"
        "else                            -->  HOLD\n"
        "\n"
        "RISK ASSESSMENT:\n"
        "  volatility > 3% OR D/E > 1.5  -->  HIGH\n"
        "  volatility < 1.5% & neutral   -->  LOW\n"
        "  else                          -->  MEDIUM"
    )

    # Conflict detection
    pdf.subsection("Sub-Signal Conflict Detection")
    pdf.body(
        "Conflicts are flagged when the spread between max and min sub-scores exceeds "
        "15 points. The AI must explicitly address such conflicts in its narrative, "
        "explaining which signal it trusts more and why."
    )

    # News confidence
    pdf.subsection("News Confidence Modulation")
    pdf.table(
        ["Condition", "News Confidence", "Effect on Recommendation"],
        [
            [">= 10 mentions, >= 3 sources", "80 (High)", "Confidence boosted up to +6%"],
            [">= 5 mentions, >= 2 sources", "65 (Moderate)", "Slight confidence boost"],
            [">= 2 mentions", "50 (Default)", "No adjustment"],
            ["No sentiment data", "20 (Low)", "Confidence dampened up to -6%"],
        ],
        [55, 40, 91]
    )

    # ============================================================
    # SECTION 8: FUNDAMENTAL ANALYSIS
    # ============================================================
    pdf.add_page()
    pdf.current_section = "08 - Fundamental Analysis"
    pdf.section_title("08", "Fundamental Analysis Scoring")

    pdf.body(
        "The fundamental analyzer scores each stock from 0-100 using 7 financial metrics "
        "fetched from Yahoo Finance. Data refreshes every 6 hours."
    )

    # Component weight bars
    pdf.subsection("Scoring Components & Weights")
    y0 = pdf.get_y()
    fund_components = [
        ("Revenue Growth", 20, GREEN, "Growth tiers: neg=0, <5%=20, <10%=50, <20%=80, >20%=100"),
        ("Profit Margin", 15, BLUE, "Margin tiers: neg=0, <5%=25, <10%=50, <15%=75, >15%=100"),
        ("Return on Equity", 15, TEAL, "ROE tiers: neg=0, <5%=25, <10%=50, <15%=75, >15%=100"),
        ("Debt-to-Equity", 15, RED, "Inverse: D/E<0.5=100, <1=75, <2=50, <3=25, >3=0"),
        ("P/E Ratio", 15, PURPLE, "Sweet spot: P/E 8-15=100, 15-25=50, neg=20"),
        ("Free Cash Flow", 10, AMBER, "FCF yield tiers: neg=0, <2%=25, <5%=50, >5%=100"),
        ("Dividend Yield", 10, SLATE, "Yield: 0=0, <1%=25, <3%=50, <5%=75, >5%=100"),
    ]

    for i, (name, weight, color, desc) in enumerate(fund_components):
        y = y0 + i * 11
        # Label
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(*DARK)
        pdf.set_xy(12, y)
        pdf.cell(35, 6, name, align="R")
        # Weight bar
        bar_w = weight * 4
        pdf.set_fill_color(*color)
        pdf.rect(49, y + 0.5, bar_w, 5, style="F")
        # Percentage
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*color)
        pdf.set_xy(49 + bar_w + 1, y)
        pdf.cell(10, 6, f"{weight}%")
        # Description
        pdf.set_font("Helvetica", "", 6)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(68 + bar_w, y)
        pdf.cell(0, 6, desc)

    pdf.set_y(y0 + len(fund_components) * 11 + 4)

    pdf.code(
        "fundamental_score = sum(component_score * weight) for all 7 components\n"
        "fundamental_score = clip(score, 0, 100)\n"
        "\n"
        "Note: D/E values > 10 are divided by 100 (assumed to be in % format)\n"
        "Finance sector stocks (banks, insurers) have structurally high D/E"
    )

    pdf.callout(
        "Finance sector stocks (MAYBANK, CIMB, etc.) have inherently high D/E ratios "
        "(3-10x) due to their lending business model. The D/E scoring penalizes them, "
        "and the risk assessment flags D/E > 1.5 as HIGH risk.",
        "!", RED
    )

    # ============================================================
    # SECTION 9: CONFIG CONSTANTS
    # ============================================================
    pdf.add_page()
    pdf.current_section = "09 - Configuration"
    pdf.section_title("09", "Configuration Constants")

    pdf.subsection("Signal Engine Parameters")
    pdf.table(
        ["Constant", "Value", "Description"],
        [
            ["momentum_window", "10", "Days for momentum calculation"],
            ["momentum_threshold", "0.02", "2% significant move"],
            ["rsi_period", "14", "Standard RSI lookback"],
            ["rsi_overbought", "70", "RSI overbought level"],
            ["rsi_oversold", "30", "RSI oversold level"],
            ["vwap_deviation_threshold", "0.01", "1% VWAP deviation"],
            ["buy_threshold", "60", "Composite score for BUY"],
            ["sell_threshold", "40", "Composite score for SELL"],
            ["strong_signal_threshold", "75", "Strong signal multiplier"],
            ["edge_threshold", "0.03", "Min 3% edge to trade"],
            ["min_confidence", "0.10", "Min confidence to trade"],
            ["volume_spike_multiplier", "2.0", "2x avg = volume spike"],
        ],
        [52, 30, 104]
    )

    pdf.subsection("Risk Management Parameters")
    pdf.table(
        ["Constant", "Value", "Description"],
        [
            ["STARTING_CAPITAL", "$100.00", "Initial bankroll (USD)"],
            ["MAX_POSITION_PCT", "0.05 (5%)", "Max single position % of bankroll"],
            ["MAX_DAILY_LOSS_PCT", "0.10 (10%)", "Daily loss limit before halt"],
            ["MAX_CONCURRENT_POSITIONS", "5", "Max simultaneous positions"],
            ["MIN_TRADE_SIZE", "$5.00", "Minimum trade size"],
            ["MAX_TRADE_SIZE", "$20.00", "Maximum trade size"],
            ["KELLY_FRACTION", "0.25", "Quarter-Kelly (conservative)"],
        ],
        [58, 36, 92]
    )

    pdf.subsection("Weight Sets (Sum = 1.00)")
    pdf.table(
        ["Signal", "With Sentiment", "Without Sentiment"],
        [
            ["Momentum", "14%", "16%"],
            ["RSI", "10%", "11%"],
            ["VWAP", "10%", "11%"],
            ["EMA", "10%", "11%"],
            ["Volume", "7%", "8%"],
            ["Vol-Price", "19%", "21%"],
            ["Sentiment", "8%", "N/A (excluded)"],
            ["Ichimoku", "12%", "12%"],
            ["Pattern", "10%", "10%"],
        ],
        [55, 55, 76]
    )

    return pdf


def main():
    filepath = os.path.join(OUTPUT_DIR, "MY-Stock-Platform-Technical-Spec.pdf")
    print("Generating master specification PDF...")
    pdf = build_master_pdf()
    pdf.output(filepath)
    size_kb = os.path.getsize(filepath) / 1024
    print(f"  -> {filepath} ({size_kb:.0f} KB)")
    print("Done!")


if __name__ == "__main__":
    main()
