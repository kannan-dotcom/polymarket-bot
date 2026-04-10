#!/usr/bin/env python3
"""
Web Dashboard for Multi-Exchange Stock Scanner
Serves a Flask web UI while running the scanner in a background thread.
"""

import os
import sys
import time
import uuid
import json
import threading
import logging
import numpy as np
from flask import Flask, jsonify, render_template
from flask.json.provider import DefaultJSONProvider

from flask import request

from config import (
    STARTING_CAPITAL,
    STOCKS,
    EXCHANGES,
    POLL_INTERVAL_SECONDS,
    LOG_LEVEL,
    SENTIMENT_ENABLED,
)
from sentiment_config import SENTIMENT_SCRAPE_INTERVAL
from market_data import MarketDataAggregator
from signals import SignalEngine, Direction
from risk_manager import RiskManager
from portfolio import Portfolio
from price_analysis import PriceAnalyzer
from pattern_recognition import PatternRecognitionEngine
from portfolio_optimizer import PortfolioOptimizer
from fundamental_analysis import (
    FundamentalAnalyzer,
    FUNDAMENTALS_ENABLED,
    FUNDAMENTALS_REFRESH_INTERVAL,
)

if SENTIMENT_ENABLED:
    from sentiment_scraper import SentimentAggregator

# ---- Logging ----
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("dashboard")


# ---- Thread-safe shared state ----
class ScannerState:
    """Thread-safe store for latest scan results."""

    def __init__(self):
        self._lock = threading.Lock()
        self._results = []
        self._last_scan_time = 0.0
        self._scan_cycle = 0
        self._is_scanning = False
        self._error = None

    def update_results(self, results, cycle):
        with self._lock:
            self._results = results
            self._last_scan_time = time.time()
            self._scan_cycle = cycle
            self._is_scanning = False

    def set_scanning(self, val):
        with self._lock:
            self._is_scanning = val

    def set_error(self, err):
        with self._lock:
            self._error = str(err) if err else None

    def get_results(self):
        with self._lock:
            return {
                "stocks": list(self._results),
                "last_scan_time": self._last_scan_time,
                "scan_cycle": self._scan_cycle,
                "is_scanning": self._is_scanning,
                "error": self._error,
            }


# ---- IPO auto-migration: enable stocks on their listing date ----
def check_ipo_migrations():
    """Enable IPO stocks whose listing date has arrived."""
    from datetime import date
    today = date.today().isoformat()  # "YYYY-MM-DD"
    migrated = []
    for key, cfg in STOCKS.items():
        ipo_date = cfg.get("ipo_date")
        if ipo_date and not cfg.get("enabled") and ipo_date <= today:
            cfg["enabled"] = True
            migrated.append(f"{key} (IPO {ipo_date})")
    if migrated:
        logger.info(f"IPO auto-migration: enabled {', '.join(migrated)}")
    return migrated

# Run once at startup
check_ipo_migrations()


# ---- Module-level references for API endpoints ----
sentiment_agg = None
price_analyzer = None
fundamental_analyzer = None
pattern_engine = None
portfolio_optimizer = None

# ---- AI Analysis cache ----
_ai_analysis_cache: dict[str, tuple[dict, float]] = {}
_ai_analysis_lock = threading.Lock()
_ai_daily_calls = 0
_ai_daily_reset = time.time()
AI_CACHE_TTL = 300        # 5 minutes
AI_MAX_DAILY_CALLS = 200  # daily cap


def background_sentiment_scraper(agg: "SentimentAggregator"):
    """Runs in a daemon thread. Scrapes forum sentiment every 10 minutes."""
    logger.info("Sentiment scraper thread started")
    while True:
        try:
            logger.info("--- Sentiment scrape starting ---")
            agg.update()
            stats = agg.get_all_sentiments()
            active = sum(1 for s in stats.values() if s.mention_count > 0)
            total_mentions = sum(s.mention_count for s in stats.values())
            logger.info(
                f"--- Sentiment scrape done: {active} stocks with mentions, "
                f"{total_mentions} total mentions ---"
            )
        except Exception as e:
            logger.error(f"Sentiment scrape error: {e}", exc_info=True)
        time.sleep(SENTIMENT_SCRAPE_INTERVAL)


def background_fundamentals_refresh(analyzer: FundamentalAnalyzer):
    """Runs in a daemon thread. Refreshes fundamental data every 6 hours."""
    logger.info("Fundamentals refresh thread started")
    while True:
        try:
            analyzer.update_all()
        except Exception as e:
            logger.error(f"Fundamentals refresh error: {e}", exc_info=True)
        time.sleep(FUNDAMENTALS_REFRESH_INTERVAL)


# ---- Background scanner ----
def background_scanner(
    state: ScannerState,
    aggregator: MarketDataAggregator,
    signal_engine: SignalEngine,
    risk_mgr: RiskManager,
    portfolio: Portfolio,
):
    """Runs in a daemon thread. Scans all stocks periodically."""
    cycle = 0
    while True:
        cycle += 1
        # Check for IPO migrations every scan cycle
        check_ipo_migrations()
        state.set_scanning(True)
        state.set_error(None)
        results = []
        logger.info(f"--- Scan cycle {cycle} starting ---")

        try:
            for stock_key, cfg in STOCKS.items():
                if not cfg["enabled"]:
                    continue

                ticker = cfg["ticker"]
                exchange = cfg["exchange"]

                try:
                    feed = aggregator.update(ticker)
                    if not feed:
                        results.append({
                            "stock_key": stock_key,
                            "name": cfg["name"],
                            "ticker": ticker,
                            "exchange": exchange,
                            "sector": cfg["sector"],
                            "status": "NO_DATA",
                        })
                        continue

                    snapshot = aggregator.get_snapshot(ticker)
                    if not snapshot:
                        results.append({
                            "stock_key": stock_key,
                            "name": cfg["name"],
                            "ticker": ticker,
                            "exchange": exchange,
                            "sector": cfg["sector"],
                            "status": "NO_SNAPSHOT",
                        })
                        continue

                    signal = signal_engine.generate(ticker)
                    trade_size = risk_mgr.compute_trade_size(signal)

                    results.append({
                        "stock_key": stock_key,
                        "name": cfg["name"],
                        "ticker": ticker,
                        "exchange": exchange,
                        "sector": cfg["sector"],
                        "status": "OK",
                        # Price & indicators
                        "price": round(snapshot["price"], 4),
                        "momentum": round(snapshot["momentum"], 4),
                        "rsi": round(snapshot["rsi"], 1),
                        "volatility": round(snapshot["volatility"], 4),
                        "atr": round(snapshot["atr"], 4),
                        "vwap": round(snapshot["vwap"], 4),
                        "vwap_deviation": round(snapshot["vwap_deviation"], 4),
                        "ema_12": round(snapshot["ema_12"], 4),
                        "ema_26": round(snapshot["ema_26"], 4),
                        "sma_50": round(snapshot["sma_50"], 4),
                        "volume_ratio": round(snapshot["volume_ratio"], 2),
                        # Volume analytics
                        "daily_volume": int(snapshot["daily_volume"]),
                        "avg_volume_20": round(snapshot["avg_volume_20"]),
                        "volume_trend": round(snapshot["volume_trend"], 4),
                        "obv_trend": round(snapshot["obv_trend"], 4),
                        "vol_price_confirm": round(snapshot["vol_price_confirm"], 4),
                        # Signal
                        "direction": signal.direction.value,
                        "score": round(signal.score, 1),
                        "edge": round(signal.edge, 4),
                        "confidence": round(signal.confidence, 4),
                        "reasons": signal.reasons,
                        "is_tradeable": bool(signal.is_tradeable),
                        "is_strong": bool(signal.is_strong),
                        # Sub-scores
                        "momentum_score": round(signal.momentum_score, 1),
                        "rsi_score": round(signal.rsi_score, 1),
                        "vwap_score": round(signal.vwap_score, 1),
                        "ema_score": round(signal.ema_score, 1),
                        "volume_score": round(signal.volume_score, 1),
                        "vol_price_score": round(signal.vol_price_score, 1),
                        "sentiment_score": round(signal.sentiment_score, 1),
                        "ichimoku_score": round(signal.ichimoku_score, 1),
                        "pattern_score": round(signal.pattern_score, 1),
                        # Ichimoku detail
                        "ichimoku": snapshot.get("ichimoku", {}),
                        # Pattern detail (attached below)
                        "patterns": [],
                        "pattern_bias": "neutral",
                        "pattern_name": "",
                        # Sentiment detail (if available)
                        "sentiment_mentions": 0,
                        "sentiment_buzz": 0.0,
                        "sentiment_trend": 0.0,
                        # Sizing
                        "trade_size": trade_size,
                    })

                    # Attach live sentiment data if available
                    if sentiment_agg:
                        sent_data = sentiment_agg.get_sentiment(stock_key)
                        if sent_data and sent_data.mention_count > 0:
                            results[-1]["sentiment_mentions"] = sent_data.mention_count
                            results[-1]["sentiment_buzz"] = round(sent_data.buzz_score, 1)
                            results[-1]["sentiment_trend"] = round(sent_data.mention_trend, 2)
                            # Attach event data
                            results[-1]["events"] = sent_data.events
                            results[-1]["event_impact"] = sent_data.event_impact
                            results[-1]["has_catalyst"] = sent_data.has_catalyst
                            # Attach LLM classification data
                            results[-1]["llm_consensus"] = sent_data.llm_consensus
                            results[-1]["llm_positive_pct"] = sent_data.llm_positive_pct
                            results[-1]["llm_negative_pct"] = sent_data.llm_negative_pct
                            results[-1]["llm_noise_pct"] = sent_data.llm_noise_pct
                            results[-1]["llm_classified_count"] = sent_data.llm_classified_count

                    # Attach pattern recognition data
                    if pattern_engine:
                        try:
                            pat_result = pattern_engine.analyze(ticker)
                            if pat_result and pat_result.patterns_detected:
                                results[-1]["patterns"] = pat_result.patterns_detected[:5]
                                results[-1]["pattern_bias"] = pat_result.strongest_bias
                                results[-1]["pattern_name"] = pat_result.strongest_pattern
                        except Exception as pe:
                            logger.debug(f"Pattern analysis error for {stock_key}: {pe}")

                    # Attach price targets
                    if price_analyzer:
                        try:
                            targets = price_analyzer.analyze(
                                ticker,
                                signal_score=signal.score,
                                signal_confidence=signal.confidence,
                            )
                            if targets:
                                results[-1]["price_targets"] = {
                                    "buy_target": round(targets.buy_target, 4),
                                    "buy_strong": round(targets.buy_strong, 4),
                                    "sell_target": round(targets.sell_target, 4),
                                    "sell_strong": round(targets.sell_strong, 4),
                                    "hold_low": round(targets.hold_low, 4),
                                    "hold_high": round(targets.hold_high, 4),
                                    "predicted_direction": targets.predicted_direction,
                                    "predicted_move_pct": round(targets.predicted_move_pct, 4),
                                    "predicted_price": round(targets.predicted_price, 4),
                                    "prediction_confidence": round(targets.prediction_confidence, 4),
                                    "support_1": round(targets.support_1, 4),
                                    "support_2": round(targets.support_2, 4),
                                    "resistance_1": round(targets.resistance_1, 4),
                                    "resistance_2": round(targets.resistance_2, 4),
                                    "avg_daily_range_pct": round(targets.avg_daily_range_pct, 4),
                                    "volume_poc": round(targets.volume_profile_poc, 4),
                                    "edge": round(targets.edge, 4),
                                    "kelly_optimal_pct": round(targets.kelly_optimal_pct, 2),
                                    "win_probability": round(targets.estimated_win_prob, 4),
                                }
                        except Exception as pe:
                            logger.debug(f"Price analysis error for {stock_key}: {pe}")

                    # Execute paper trade if tradeable
                    if trade_size > 0:
                        trade_id = str(uuid.uuid4())[:8]
                        risk_mgr.open_position(
                            position_id=trade_id,
                            stock_key=stock_key,
                            ticker=ticker,
                            exchange=exchange,
                            signal=signal,
                            entry_price=snapshot["price"],
                            size_usd=trade_size,
                        )
                        portfolio.record_trade(
                            trade_id=trade_id,
                            stock_key=stock_key,
                            ticker=ticker,
                            exchange=exchange,
                            direction=signal.direction.value,
                            entry_price=snapshot["price"],
                            size_usd=trade_size,
                            score=signal.score,
                            edge=signal.edge,
                            confidence=signal.confidence,
                        )
                        logger.info(
                            f"Trade: {stock_key} {signal.direction.value} "
                            f"${trade_size:.2f} @ ${snapshot['price']:.2f}"
                        )

                    time.sleep(0.3)

                except Exception as e:
                    logger.error(f"Error scanning {stock_key}: {e}")
                    results.append({
                        "stock_key": stock_key,
                        "name": cfg["name"],
                        "ticker": ticker,
                        "exchange": exchange,
                        "sector": cfg["sector"],
                        "status": f"ERROR: {e}",
                    })

            state.update_results(results, cycle)
            ok_count = sum(1 for r in results if r["status"] == "OK")
            tradeable = sum(1 for r in results if r.get("is_tradeable"))
            logger.info(
                f"--- Scan cycle {cycle} done: {ok_count} stocks, "
                f"{tradeable} tradeable ---"
            )

        except Exception as e:
            logger.error(f"Scan cycle error: {e}", exc_info=True)
            state.set_error(str(e))
            state.set_scanning(False)

        time.sleep(POLL_INTERVAL_SECONDS)


# ---- Flask app ----
class NumpyJSONProvider(DefaultJSONProvider):
    """Handle numpy types that default Flask JSON encoder cannot serialize."""
    def default(self, o):
        if isinstance(o, (np.bool_, np.generic)):
            return o.item()
        return super().default(o)

app = Flask(__name__)
app.json_provider_class = NumpyJSONProvider
app.json = NumpyJSONProvider(app)
scanner_state = ScannerState()
risk_manager = None
portfolio = None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "timestamp": time.time()})


@app.route("/api/scanner")
def api_scanner():
    return jsonify(scanner_state.get_results())


@app.route("/api/portfolio")
def api_portfolio():
    return jsonify(portfolio.get_performance())


@app.route("/api/risk")
def api_risk():
    return jsonify(risk_manager.get_stats())


@app.route("/api/exchanges")
def api_exchanges():
    return jsonify(portfolio.get_exchange_breakdown())


@app.route("/api/trades")
def api_trades():
    return jsonify(portfolio.get_trade_log(last_n=50))


@app.route("/api/config")
def api_config():
    return jsonify({
        "exchanges": EXCHANGES,
        "stocks": {
            k: {
                "name": v["name"],
                "ticker": v["ticker"],
                "exchange": v["exchange"],
                "sector": v["sector"],
            }
            for k, v in STOCKS.items()
            if v["enabled"]
        },
        "starting_capital": STARTING_CAPITAL,
    })


@app.route("/api/sentiment")
def api_sentiment():
    """All stock sentiment data."""
    if not sentiment_agg:
        return jsonify({"enabled": False, "stocks": {}})
    all_sent = sentiment_agg.get_all_sentiments()
    out = {}
    for key, s in all_sent.items():
        if s.mention_count == 0:
            continue
        out[key] = {
            "stock_key": s.stock_key,
            "mention_count": s.mention_count,
            "sentiment_score": round(s.sentiment_score, 1),
            "buzz_score": round(s.buzz_score, 1),
            "mention_trend": round(s.mention_trend, 2),
            "bullish_count": s.bullish_count,
            "bearish_count": s.bearish_count,
            "neutral_count": s.neutral_count,
            "top_sources": s.top_sources,
            "events": s.events,
            "event_impact": s.event_impact,
            "has_catalyst": s.has_catalyst,
            "llm_positive_pct": s.llm_positive_pct,
            "llm_negative_pct": s.llm_negative_pct,
            "llm_noise_pct": s.llm_noise_pct,
            "llm_classified_count": s.llm_classified_count,
            "llm_consensus": s.llm_consensus,
        }
    stats = sentiment_agg.get_stats()
    return jsonify({"enabled": True, "llm_active": stats.get("llm_active", False), "stocks": out})


@app.route("/api/sentiment/trending")
def api_sentiment_trending():
    """Top 10 trending stocks by mention count."""
    if not sentiment_agg:
        return jsonify({"enabled": False, "trending": []})
    trending = sentiment_agg.get_trending()
    out = []
    for s in trending:
        sk = s.get("stock_key", "")
        name = STOCKS.get(sk, {}).get("name", sk)
        entry = {
            "stock_key": sk,
            "name": name,
            "mention_count": s.get("mentions", 0),
            "sentiment_score": round(s.get("sentiment_score", 50), 1),
            "buzz_score": round(s.get("buzz_score", 0), 1),
            "mention_trend": round(s.get("mention_trend", 0), 2),
            "snippets": [],
        }
        # Attach up to 2 recent post snippets for context
        sent_obj = sentiment_agg.get_sentiment(sk)
        if sent_obj and sent_obj.recent_posts:
            for p in sent_obj.recent_posts[:2]:
                text = p.get("text", "")[:120]
                entry["snippets"].append({
                    "text": text,
                    "source": p.get("source", ""),
                    "llm_label": p.get("llm_label", ""),
                })
        out.append(entry)
    return jsonify({"enabled": True, "trending": out})


@app.route("/api/price_targets/<stock_key>")
def api_price_targets(stock_key):
    """Price targets for a specific stock."""
    if not price_analyzer:
        return jsonify({"error": "Price analyzer not initialized"}), 503
    cfg = STOCKS.get(stock_key.upper())
    if not cfg:
        return jsonify({"error": f"Unknown stock: {stock_key}"}), 404
    ticker = cfg["ticker"]
    # Get signal score for this stock
    results = scanner_state.get_results()
    sig_score = 50.0
    sig_conf = 0.0
    for r in results.get("stocks", []):
        if r.get("stock_key") == stock_key.upper():
            sig_score = r.get("score", 50.0)
            sig_conf = r.get("confidence", 0.0)
            break
    targets = price_analyzer.analyze(ticker, signal_score=sig_score,
                                      signal_confidence=sig_conf)
    if not targets:
        return jsonify({"error": "Insufficient data for analysis"}), 404
    return jsonify(targets.to_dict())


@app.route("/api/events")
def api_events():
    """All detected company events across stocks."""
    if not sentiment_agg:
        return jsonify({"enabled": False, "events": []})
    all_sent = sentiment_agg.get_all_sentiments()
    events = []
    for key, s in all_sent.items():
        if not s.events:
            continue
        name = STOCKS.get(key, {}).get("name", key)
        for ev in s.events:
            events.append({
                "stock_key": key,
                "name": name,
                "event_type": ev.get("type", ""),
                "keyword": ev.get("keyword", ""),
                "impact": ev.get("impact", "neutral"),
                "source": ev.get("source", ""),
                "time": ev.get("time", 0),
            })
    # Sort by time descending
    events.sort(key=lambda e: e.get("time", 0), reverse=True)
    return jsonify({"enabled": True, "events": events[:50]})


@app.route("/api/fundamentals")
def api_fundamentals():
    """Fundamental analysis data for all stocks."""
    if not fundamental_analyzer:
        return jsonify({"enabled": False, "stocks": {}})
    all_fund = fundamental_analyzer.get_all_as_dicts()
    # Filter out stocks with no meaningful data
    out = {k: v for k, v in all_fund.items() if v.get("data_quality") != "none"}
    return jsonify({"enabled": True, "stocks": out})


@app.route("/api/patterns/<stock_key>")
def api_patterns(stock_key):
    """Pattern recognition for a specific stock."""
    if not pattern_engine:
        return jsonify({"error": "Pattern engine not initialized"}), 503
    cfg = STOCKS.get(stock_key.upper())
    if not cfg:
        return jsonify({"error": f"Unknown stock: {stock_key}"}), 404
    result = pattern_engine.analyze(cfg["ticker"])
    if not result:
        return jsonify({"error": "Insufficient data"}), 404
    return jsonify(result.to_dict())


# ═══════════════════════════════════════════════════════
# AI STOCK ANALYSIS
# ═══════════════════════════════════════════════════════

def _get_scanner_data_for(stock_key: str):
    """Extract scanner data for a stock from latest scan results."""
    results = scanner_state.get_results()
    for r in results.get("stocks", []):
        if r.get("stock_key") == stock_key:
            return r
    return None


def _get_fundamentals_for(stock_key: str):
    """Get fundamentals dict for a stock."""
    if not fundamental_analyzer:
        return None
    all_fund = fundamental_analyzer.get_all_as_dicts()
    return all_fund.get(stock_key)


def _get_price_targets_for(ticker: str, scan_data: dict):
    """Get price target analysis."""
    if not price_analyzer:
        return None
    sig_score = scan_data.get("score", 50.0) if scan_data else 50.0
    sig_conf = scan_data.get("confidence", 0.0) if scan_data else 0.0
    try:
        targets = price_analyzer.analyze(
            ticker, signal_score=sig_score, signal_confidence=sig_conf,
        )
        return targets.to_dict() if targets else None
    except Exception:
        return None


def _get_pattern_data_for(ticker: str):
    """Get pattern recognition data."""
    if not pattern_engine:
        return None
    try:
        result = pattern_engine.analyze(ticker)
        return result.to_dict() if result else None
    except Exception:
        return None


def _get_sentiment_for(stock_key: str):
    """Get sentiment data."""
    if not sentiment_agg:
        return None
    sent = sentiment_agg.get_sentiment(stock_key)
    if sent and sent.mention_count > 0:
        return sent.to_dict()
    return None


def _build_analysis_prompt(stock_key, cfg, scan, fund, targets, patterns, sentiment):
    """Build a prompt with Maybank IB broker persona, conflict resolution, and cross-validation."""
    import datetime as _dt

    lines = [
        "You are a senior equity research analyst at Maybank Investment Bank covering "
        "Bursa Malaysia (KLSE). You evaluate stocks for institutional and retail clients "
        "with rigorous, evidence-based analysis. You are skeptical of noise and demand "
        "corroboration before trusting any single data source.",
        "",
        f"STOCK: {cfg['name']} ({stock_key}, {cfg['ticker']}), Sector: {cfg.get('sector', 'N/A')}",
        f"DATE: {time.strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    # --- Technical data ---
    if scan:
        lines.append("── TECHNICAL SIGNALS ──")
        lines.append(
            f"Price: {scan.get('price')}, RSI: {scan.get('rsi', 'N/A')}, "
            f"Momentum: {scan.get('momentum', 0):.4f}"
        )
        lines.append(
            f"Composite Score: {scan.get('score', 50):.1f}/100, "
            f"System Signal: {scan.get('direction', 'HOLD')}, "
            f"Edge: {scan.get('edge', 0):.4f}, "
            f"Confidence: {scan.get('confidence', 0):.2f}"
        )
        lines.append(
            f"Sub-Scores: Momentum={scan.get('momentum_score', 50):.0f}, "
            f"RSI={scan.get('rsi_score', 50):.0f}, VWAP={scan.get('vwap_score', 50):.0f}, "
            f"EMA={scan.get('ema_score', 50):.0f}, Volume={scan.get('volume_score', 50):.0f}, "
            f"VolPrice={scan.get('vol_price_score', 50):.0f}, "
            f"Ichimoku={scan.get('ichimoku_score', 50):.0f}, "
            f"Pattern={scan.get('pattern_score', 50):.0f}, "
            f"Sentiment={scan.get('sentiment_score', 50):.0f}"
        )
        lines.append(
            f"Volume: Daily={scan.get('daily_volume', 0):.0f}, "
            f"Avg20={scan.get('avg_volume_20', 0):.0f}, "
            f"Ratio={scan.get('volume_ratio', 0):.2f}x, OBV={scan.get('obv_trend', 'N/A')}"
        )

        # Detect model conflicts inline
        conflicts_found = []
        direction = scan.get("direction", "HOLD")
        thresh = 15
        sub_map = {
            "Momentum": scan.get("momentum_score", 50),
            "RSI": scan.get("rsi_score", 50),
            "VWAP": scan.get("vwap_score", 50),
            "EMA": scan.get("ema_score", 50),
            "Volume": scan.get("volume_score", 50),
            "VolPrice": scan.get("vol_price_score", 50),
            "Ichimoku": scan.get("ichimoku_score", 50),
            "Pattern": scan.get("pattern_score", 50),
            "Sentiment": scan.get("sentiment_score", 50),
        }
        for name, val in sub_map.items():
            if direction == "BUY" and val < (50 - thresh):
                conflicts_found.append(f"{name} bearish ({val:.0f}) vs BUY")
            elif direction == "SELL" and val > (50 + thresh):
                conflicts_found.append(f"{name} bullish ({val:.0f}) vs SELL")

        if conflicts_found:
            lines.append(f"⚠ MODEL CONFLICTS ({len(conflicts_found)}):")
            for c in conflicts_found:
                lines.append(f"  - {c}")

        reasons = scan.get("reasons", [])
        if reasons:
            lines.append(f"System Reasons: {' | '.join(reasons[:5])}")
        lines.append("")

    # --- Fundamentals ---
    if fund:
        lines.append("── FUNDAMENTALS ──")
        parts = []
        for key, label in [
            ("pe_ratio", "P/E"), ("revenue_growth", "RevGrowth%"),
            ("profit_margin", "Margin"), ("roe", "ROE"),
            ("debt_to_equity", "D/E"), ("dividend_yield", "DivYield"),
            ("eps", "EPS"), ("fundamental_score", "FundScore"),
        ]:
            val = fund.get(key)
            if val is not None:
                if key in ("profit_margin", "roe", "dividend_yield"):
                    parts.append(f"{label}={val*100:.1f}%")
                elif key == "revenue_growth":
                    parts.append(f"{label}={val:+.1f}%")
                else:
                    parts.append(f"{label}={val:.2f}" if isinstance(val, float) else f"{label}={val}")
        if parts:
            lines.append(", ".join(parts))
        lines.append("")

    # --- Targets ---
    if targets:
        lines.append("── PRICE TARGETS ──")
        lines.append(
            f"Buy Target: {targets.get('buy_target')}, Sell Target: {targets.get('sell_target')}, "
            f"Predicted: {targets.get('predicted_direction')} {targets.get('predicted_move_pct')}%, "
            f"Win Prob: {targets.get('estimated_win_prob')}"
        )
        lines.append("")

    # --- Patterns ---
    if patterns:
        pat_list = patterns.get("patterns_detected", [])[:3]
        if pat_list:
            lines.append("── CHART PATTERNS ──")
            for p in pat_list:
                lines.append(f"  {p['name']} ({p['bias']}, strength={p.get('strength', 0):.0%})")
            lines.append("")

    # --- Sentiment & Forum Posts ---
    if sentiment:
        lines.append("── MARKET SENTIMENT & NEWS ──")
        lines.append(
            f"Mentions: {sentiment.get('mention_count', 0)}, "
            f"Sentiment Score: {sentiment.get('sentiment_score', 50)}/100, "
            f"LLM Consensus: {sentiment.get('llm_consensus', 'N/A')}, "
            f"Catalyst Detected: {'Yes' if sentiment.get('has_catalyst') else 'No'}"
        )

        recent = sentiment.get("recent_posts", [])
        if recent:
            lines.append("")
            lines.append("VERBATIM FORUM POSTS (you must evaluate each as a broker would):")
            for i, p in enumerate(recent[:5], 1):
                ts = p.get("time", 0)
                if ts > 0:
                    age_h = (time.time() - ts) / 3600
                    age_str = f"{age_h * 60:.0f}m ago" if age_h < 1 else (
                        f"{age_h:.0f}h ago" if age_h < 48 else f"{age_h / 24:.0f}d ago"
                    )
                    date_str = _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                else:
                    date_str = "unknown"
                    age_str = "unknown"
                src = p.get("source", "?")
                llm = p.get("llm_label", "")
                text = p.get("text", "")[:180]
                lines.append(f"  [{i}] {date_str} ({age_str}) [{src}] {llm}: {text}")
        lines.append("")

    # --- Instructions ---
    lines.append("── YOUR ANALYSIS TASKS ──")
    lines.append(
        "1. NEWS SIGNAL: For each forum post above, assess as a Maybank IB broker would: "
        "Is this news ACTIONABLE? Is it a catalyst for price movement? "
        "Score each post's authenticity 0-100 based on: "
        "(a) Does the content discuss a real, current event? "
        "(b) Do multiple posts from different sources corroborate the same theme? "
        "(c) Is the post about THIS company specifically, or generic/stale/IPO-era noise?"
    )
    lines.append(
        "2. CROSS-VALIDATION: Check if multiple posts reinforce the same narrative. "
        "Posts from different sources saying similar things = higher authenticity. "
        "A single post with no corroboration = lower authenticity. "
        "Compute an overall NEWS_CONFIDENCE score (0-100) for the sentiment data."
    )
    lines.append(
        "3. CONFLICT RESOLUTION: The system detected model conflicts (see above). "
        "As a senior analyst, determine which signals to trust and which to discount. "
        "Resolve the conflicts with a clear rationale — e.g., if Momentum is bearish "
        "but VWAP and Ichimoku are bullish, explain which you weight more and why."
    )
    lines.append(
        "4. FINAL VERDICT: Combining technicals, fundamentals, news authenticity, "
        "and conflict resolution — what is your recommendation?"
    )
    lines.append("")
    lines.append("Respond in EXACTLY this format (one line each, no extra text):")
    lines.append("RECOMMENDATION|<BUY or SELL or HOLD or TRADE>|<confidence 0.0-1.0>")
    lines.append("RISK|<LOW or MEDIUM or HIGH>")
    lines.append("NEWS_CONFIDENCE|<0-100 integer — how reliable is the sentiment/news data>")
    lines.append("CONFLICT_RESOLUTION|<1-2 sentences resolving any model conflicts>")
    lines.append("NARRATIVE|<2-3 sentences: your broker assessment, citing specific evidence>")

    return "\n".join(lines)


def _parse_ai_response(text, stock_key, cfg, scan, fund, targets):
    """Parse Claude's structured response into a result dict."""
    result = {
        "stock_key": stock_key,
        "name": cfg["name"],
        "ticker": cfg["ticker"],
        "sector": cfg.get("sector", ""),
        "ai_source": "claude_sonnet",
        "recommendation": "HOLD",
        "confidence": 0.5,
        "risk_level": "MEDIUM",
        "news_confidence": 50,
        "conflict_resolution": "",
        "narrative": "",
        "timestamp": time.time(),
    }

    # Attach raw data for frontend display
    if scan:
        for key in ["price", "score", "direction", "rsi", "momentum_score",
                     "volume_score", "sentiment_score", "ichimoku_score",
                     "pattern_score", "vol_price_score", "ema_score",
                     "vwap_score", "rsi_score", "volatility", "edge",
                     "is_tradeable", "reasons"]:
            if key in scan:
                result[key] = scan[key]
    if fund:
        for key in ["fundamental_score", "pe_ratio", "dividend_yield", "roe",
                     "debt_to_equity", "profit_margin", "revenue_growth"]:
            if fund.get(key) is not None:
                result[key] = fund[key]
    if targets:
        result["price_targets"] = targets

    # Parse Claude response lines
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("RECOMMENDATION|"):
            parts = line.split("|")
            if len(parts) >= 3:
                rec = parts[1].strip().upper()
                if rec in ("BUY", "SELL", "HOLD", "TRADE"):
                    result["recommendation"] = rec
                try:
                    result["confidence"] = max(0.0, min(1.0, float(parts[2].strip())))
                except ValueError:
                    pass
        elif line.startswith("RISK|"):
            parts = line.split("|")
            if len(parts) >= 2:
                risk = parts[1].strip().upper()
                if risk in ("LOW", "MEDIUM", "HIGH"):
                    result["risk_level"] = risk
        elif line.startswith("NEWS_CONFIDENCE|"):
            try:
                nc = int(line.split("|")[1].strip())
                result["news_confidence"] = max(0, min(100, nc))
            except (ValueError, IndexError):
                pass
        elif line.startswith("CONFLICT_RESOLUTION|"):
            result["conflict_resolution"] = line[len("CONFLICT_RESOLUTION|"):].strip()
        elif line.startswith("NARRATIVE|"):
            result["narrative"] = line[len("NARRATIVE|"):].strip()

    return result


def _rule_based_analysis(stock_key, cfg, scan, fund, targets, patterns, sentiment):
    """Generate recommendation from existing signals without AI."""
    result = {
        "stock_key": stock_key,
        "name": cfg["name"],
        "ticker": cfg["ticker"],
        "sector": cfg.get("sector", ""),
        "ai_source": "rule_based",
        "recommendation": "HOLD",
        "confidence": 0.0,
        "risk_level": "MEDIUM",
        "narrative": "",
        "timestamp": time.time(),
    }

    if not scan:
        result["narrative"] = (
            f"Insufficient data for {cfg['name']}. "
            f"Waiting for scanner data — try again after the next scan cycle."
        )
        return result

    # Attach raw data
    for key in ["price", "score", "direction", "rsi", "momentum_score",
                 "volume_score", "sentiment_score", "ichimoku_score",
                 "pattern_score", "vol_price_score", "ema_score",
                 "vwap_score", "rsi_score", "volatility", "edge",
                 "is_tradeable", "reasons"]:
        if key in scan:
            result[key] = scan[key]
    if fund:
        for key in ["fundamental_score", "pe_ratio", "dividend_yield", "roe",
                     "debt_to_equity", "profit_margin", "revenue_growth"]:
            if fund.get(key) is not None:
                result[key] = fund[key]
    if targets:
        result["price_targets"] = targets

    score = scan.get("score", 50)
    direction = scan.get("direction", "HOLD")
    confidence = scan.get("confidence", 0)
    is_tradeable = scan.get("is_tradeable", False)

    # Determine recommendation
    if is_tradeable and direction == "BUY" and score >= 65:
        result["recommendation"] = "BUY"
        result["confidence"] = round(min(confidence, 0.85), 2)
    elif is_tradeable and direction == "SELL" and score <= 35:
        result["recommendation"] = "SELL"
        result["confidence"] = round(min(confidence, 0.85), 2)
    elif is_tradeable:
        result["recommendation"] = "TRADE"
        result["confidence"] = round(confidence * 0.7, 2)
    else:
        result["recommendation"] = "HOLD"
        result["confidence"] = 0.5

    # Risk assessment
    volatility = scan.get("volatility", 0)
    high_debt = fund and fund.get("debt_to_equity") is not None and fund["debt_to_equity"] > 1.5
    if volatility > 0.03 or high_debt:
        result["risk_level"] = "HIGH"
    elif volatility < 0.015 and 40 <= score <= 60:
        result["risk_level"] = "LOW"

    # Build narrative
    parts = [
        f"{cfg['name']} ({stock_key}) shows a {direction} signal "
        f"with composite score {score:.0f}/100."
    ]
    reasons = scan.get("reasons", [])
    if reasons:
        parts.append(f"Key factors: {', '.join(reasons[:3])}.")
    if fund and fund.get("fundamental_score") is not None:
        fs = fund["fundamental_score"]
        parts.append(f"Fundamental score: {fs:.0f}/100.")
    if sentiment and sentiment.get("mention_count", 0) > 0:
        parts.append(
            f"Forum sentiment: {sentiment['sentiment_score']:.0f}/100 "
            f"({sentiment['mention_count']} mentions)."
        )
    if targets and targets.get("predicted_direction"):
        parts.append(
            f"Price prediction: {targets['predicted_direction']} "
            f"({targets['predicted_move_pct']:+.2f}%)."
        )

    result["narrative"] = " ".join(parts)

    # News confidence: derive from sentiment data quality
    nc = 50  # default moderate confidence
    if sentiment and sentiment.get("mention_count", 0) > 0:
        mentions = sentiment["mention_count"]
        source_count = sentiment.get("source_count", 1)
        if mentions >= 10 and source_count >= 3:
            nc = 80
        elif mentions >= 5 and source_count >= 2:
            nc = 65
        elif mentions >= 2:
            nc = 50
        else:
            nc = 30
    else:
        nc = 20  # no sentiment data = low confidence
    result["news_confidence"] = nc

    # Modulate recommendation confidence with news confidence
    # High news confidence (80+) boosts confidence by up to 10%
    # Low news confidence (<30) dampens confidence by up to 15%
    nc_factor = (nc - 50) / 500  # range: -0.06 to +0.06
    if result["confidence"] > 0:
        result["confidence"] = round(
            max(0.1, min(0.95, result["confidence"] + nc_factor)), 2
        )

    # Conflict resolution: detect and describe conflicts between models
    conflicts = []
    if scan:
        dir_ = scan.get("direction", "HOLD")
        rsi_s = scan.get("rsi_score", 50)
        mom_s = scan.get("momentum_score", 50)
        ichi_s = scan.get("ichimoku_score", 50)
        if dir_ == "BUY" and rsi_s < 35:
            conflicts.append("RSI bearish vs overall BUY signal")
        if dir_ == "SELL" and rsi_s > 65:
            conflicts.append("RSI bullish vs overall SELL signal")
        if abs(mom_s - ichi_s) > 30:
            conflicts.append(f"momentum ({mom_s:.0f}) diverges from Ichimoku ({ichi_s:.0f})")
        if sentiment and sentiment.get("sentiment_score", 50) > 60 and dir_ == "SELL":
            conflicts.append("positive forum sentiment vs SELL signal")
        if sentiment and sentiment.get("sentiment_score", 50) < 40 and dir_ == "BUY":
            conflicts.append("negative forum sentiment vs BUY signal")
    if conflicts:
        result["conflict_resolution"] = (
            f"Rule-based conflict detected: {'; '.join(conflicts)}. "
            f"Composite score ({score:.0f}) used as tiebreaker."
        )
    else:
        result["conflict_resolution"] = "No significant model conflicts detected."

    return result


@app.route("/api/ai-analysis/<stock_key>")
def api_ai_analysis(stock_key):
    """AI-powered stock analysis with buy/sell/hold recommendation."""
    global _ai_daily_calls, _ai_daily_reset

    stock_key = stock_key.upper()
    cfg = STOCKS.get(stock_key)
    if not cfg:
        return jsonify({"error": f"Unknown stock: {stock_key}"}), 404

    # Check cache
    now = time.time()
    with _ai_analysis_lock:
        cached = _ai_analysis_cache.get(stock_key)
        if cached and (now - cached[1]) < AI_CACHE_TTL:
            return jsonify(cached[0])

    # Reset daily counter
    with _ai_analysis_lock:
        if now - _ai_daily_reset > 86400:
            _ai_daily_calls = 0
            _ai_daily_reset = now

    # Gather all available data
    ticker = cfg["ticker"]
    scan = _get_scanner_data_for(stock_key)
    fund = _get_fundamentals_for(stock_key)
    targets = _get_price_targets_for(ticker, scan)
    pats = _get_pattern_data_for(ticker)
    sent = _get_sentiment_for(stock_key)

    # Attempt Claude analysis
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    use_ai = bool(api_key) and _ai_daily_calls < AI_MAX_DAILY_CALLS

    if use_ai:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            prompt = _build_analysis_prompt(stock_key, cfg, scan, fund, targets, pats, sent)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = response.content[0].text.strip()
            result = _parse_ai_response(response_text, stock_key, cfg, scan, fund, targets)
            with _ai_analysis_lock:
                _ai_daily_calls += 1
            logger.info(f"AI analysis for {stock_key}: {result['recommendation']} "
                        f"({result['confidence']:.0%} confidence)")
        except Exception as e:
            logger.error(f"AI analysis failed for {stock_key}: {e}")
            result = _rule_based_analysis(stock_key, cfg, scan, fund, targets, pats, sent)
            result["ai_source"] = "rule_based_fallback"
    else:
        result = _rule_based_analysis(stock_key, cfg, scan, fund, targets, pats, sent)

    # Cache result
    with _ai_analysis_lock:
        _ai_analysis_cache[stock_key] = (result, now)

    return jsonify(result)


@app.route("/api/conflicts")
def api_conflicts():
    """Detect model conflicts across all scanned stocks."""
    results = scanner_state.get_results()
    stocks = [r for r in results.get("stocks", []) if r.get("status") == "OK"]
    if not stocks:
        return jsonify({"stocks_analyzed": 0, "conflicts": []})

    all_fund = {}
    if fundamental_analyzer:
        all_fund = fundamental_analyzer.get_all_as_dicts()

    conflict_list = []
    for s in stocks:
        stock_key = s["stock_key"]
        direction = s.get("direction", "HOLD")
        if direction == "HOLD":
            continue  # Only flag conflicts for BUY/SELL stocks

        conflicts = []
        sub_scores = {
            "Momentum": s.get("momentum_score", 50),
            "RSI": s.get("rsi_score", 50),
            "VWAP": s.get("vwap_score", 50),
            "EMA": s.get("ema_score", 50),
            "Volume": s.get("volume_score", 50),
            "Vol-Price": s.get("vol_price_score", 50),
            "Sentiment": s.get("sentiment_score", 50),
            "Ichimoku": s.get("ichimoku_score", 50),
            "Pattern": s.get("pattern_score", 50),
        }

        thresh = 15
        for name, val in sub_scores.items():
            if direction == "BUY" and val < (50 - thresh):
                sev = "severe" if val < 30 else "warn"
                conflicts.append({
                    "model": name, "severity": sev,
                    "issue": f"{name} bearish ({val:.0f}) vs BUY signal",
                })
            elif direction == "SELL" and val > (50 + thresh):
                sev = "severe" if val > 70 else "warn"
                conflicts.append({
                    "model": name, "severity": sev,
                    "issue": f"{name} bullish ({val:.0f}) vs SELL signal",
                })

        # Ichimoku-specific
        ichi = s.get("ichimoku", {})
        if ichi:
            if direction == "BUY" and ichi.get("cloud_signal") == "bearish" and ichi.get("price_vs_cloud") != "above":
                conflicts.append({"model": "Ichimoku Cloud", "severity": "severe",
                                  "issue": "Bearish cloud + price not above cloud"})
            if direction == "SELL" and ichi.get("cloud_signal") == "bullish" and ichi.get("price_vs_cloud") != "below":
                conflicts.append({"model": "Ichimoku Cloud", "severity": "severe",
                                  "issue": "Bullish cloud + price not below cloud"})

        # Fundamental vs Technical
        fund = all_fund.get(stock_key, {})
        fs = fund.get("fundamental_score")
        if fs is not None:
            if direction == "BUY" and fs < 35:
                conflicts.append({"model": "Fundamentals", "severity": "severe",
                                  "issue": f"Weak fundamentals ({fs:.0f}) vs BUY"})
            elif direction == "SELL" and fs > 65:
                conflicts.append({"model": "Fundamentals", "severity": "warn",
                                  "issue": f"Strong fundamentals ({fs:.0f}) vs SELL"})

        # Risk factors
        risk_factors = []
        vol = s.get("volatility", 0)
        if vol > 0.04:
            risk_factors.append(f"Very high volatility ({vol*100:.1f}%)")
        de = fund.get("debt_to_equity")
        if de is not None and de > 3.0:
            risk_factors.append(f"High debt (D/E={de:.1f})")
        pm = fund.get("profit_margin")
        if pm is not None and pm < 0:
            risk_factors.append("Negative profit margin")

        if conflicts:
            conflict_list.append({
                "stock_key": stock_key,
                "name": s.get("name", stock_key),
                "direction": direction,
                "score": round(s.get("score", 50), 1),
                "conflicts": conflicts,
                "risk_factors": risk_factors,
                "severe_count": sum(1 for c in conflicts if c["severity"] == "severe"),
            })

    # Sort by severity count descending
    conflict_list.sort(key=lambda x: x["severe_count"], reverse=True)

    return jsonify({
        "stocks_analyzed": len(stocks),
        "stocks_with_conflicts": len(conflict_list),
        "conflicts": conflict_list,
    })


@app.route("/api/portfolio/optimize")
def api_portfolio_optimize():
    """Run portfolio optimization on tradeable stocks."""
    if not portfolio_optimizer:
        return jsonify({"error": "Portfolio optimizer not initialized"}), 503

    method = request.args.get("method", "mvo")
    max_w = request.args.get("max_weight", 0.20, type=float)

    # Get tradeable tickers from latest scan
    results = scanner_state.get_results()
    tradeable = [
        r for r in results.get("stocks", [])
        if r.get("is_tradeable") or r.get("status") == "OK"
    ]
    if len(tradeable) < 2:
        return jsonify({"error": "Need at least 2 stocks with data"}), 404

    tickers = [r["ticker"] for r in tradeable]
    signal_scores = {r["ticker"]: r.get("score", 50) for r in tradeable}

    result = portfolio_optimizer.optimize(
        tickers=tickers,
        method=method,
        max_weight=max_w,
        signal_scores=signal_scores if method == "mvo" else None,
    )
    if not result:
        return jsonify({"error": "Optimization failed — insufficient return data"}), 404

    # Map ticker weights to stock keys for readability
    ticker_to_key = {cfg["ticker"]: key for key, cfg in STOCKS.items()}
    named_weights = {}
    for ticker, weight in result.weights.items():
        key = ticker_to_key.get(ticker, ticker)
        name = STOCKS.get(key, {}).get("name", key)
        named_weights[key] = {
            "weight": round(weight, 4),
            "name": name,
            "ticker": ticker,
            "weight_pct": round(weight * 100, 2),
        }

    out = result.to_dict()
    out["named_weights"] = named_weights
    return jsonify(out)


@app.route("/api/portfolio/correlation")
def api_portfolio_correlation():
    """Correlation matrix for all scanned stocks."""
    if not portfolio_optimizer:
        return jsonify({"error": "Portfolio optimizer not initialized"}), 503
    results = scanner_state.get_results()
    tickers = [r["ticker"] for r in results.get("stocks", []) if r.get("status") == "OK"]
    if len(tickers) < 2:
        return jsonify({"error": "Need at least 2 stocks with data"}), 404
    corr = portfolio_optimizer.get_correlation_matrix(tickers)
    if not corr:
        return jsonify({"error": "Insufficient data for correlation"}), 404
    return jsonify(corr)


@app.route("/api/sentiment/posts")
def api_sentiment_posts():
    """Recent forum posts."""
    if not sentiment_agg:
        return jsonify({"enabled": False, "posts": []})
    limit = request.args.get("limit", 30, type=int)
    limit = min(limit, 100)
    posts = sentiment_agg.get_recent_forum_posts(limit=limit)
    out = []
    for p in posts:
        out.append({
            "source": p.get("source", ""),
            "text": p.get("text", "")[:200],
            "timestamp": p.get("time", 0),
            "stock_mentions": p.get("stock_mentions", []),
            "raw_sentiment": round(p.get("sentiment", 0), 2),
            "author": p.get("author", ""),
            "url": p.get("url", ""),
            "llm_label": p.get("llm_label", ""),
            "llm_confidence": p.get("llm_confidence", 0),
            "llm_reason": p.get("llm_reason", ""),
        })
    return jsonify({"enabled": True, "posts": out})


# ---- Main ----
if __name__ == "__main__":
    aggregator = MarketDataAggregator()

    # Initialize sentiment if enabled
    _sentiment = None
    if SENTIMENT_ENABLED:
        try:
            _sentiment = SentimentAggregator()
            sentiment_agg = _sentiment  # set module-level ref for API endpoints
            logger.info("Sentiment aggregator initialized")
        except Exception as e:
            logger.warning(f"Sentiment init failed (continuing without): {e}")
            _sentiment = None

    # Initialize pattern recognition engine
    _pattern_engine = PatternRecognitionEngine(aggregator)
    pattern_engine = _pattern_engine
    logger.info("Pattern recognition engine initialized")

    # Initialize portfolio optimizer
    _portfolio_optimizer = PortfolioOptimizer(aggregator)
    portfolio_optimizer = _portfolio_optimizer
    logger.info("Portfolio optimizer initialized")

    signal_engine = SignalEngine(aggregator, sentiment_aggregator=_sentiment, pattern_engine=_pattern_engine)
    risk_manager = RiskManager(starting_balance=STARTING_CAPITAL)
    portfolio = Portfolio(starting_capital=STARTING_CAPITAL)

    # Initialize price analyzer
    price_analyzer = PriceAnalyzer(aggregator)
    logger.info("Price analyzer initialized")

    # Initialize fundamental analyzer
    if FUNDAMENTALS_ENABLED:
        try:
            fundamental_analyzer = FundamentalAnalyzer()
            logger.info("Fundamental analyzer initialized")

            # Start background fundamentals refresh
            fund_thread = threading.Thread(
                target=background_fundamentals_refresh,
                args=(fundamental_analyzer,),
                daemon=True,
            )
            fund_thread.start()
            logger.info("Background fundamentals refresh started (6-hour interval)")
        except Exception as e:
            logger.warning(f"Fundamentals init failed (continuing without): {e}")
            fundamental_analyzer = None

    # Start background sentiment scraper (if enabled)
    if _sentiment:
        sentiment_thread = threading.Thread(
            target=background_sentiment_scraper,
            args=(_sentiment,),
            daemon=True,
        )
        sentiment_thread.start()
        logger.info("Background sentiment scraper started (10-min interval)")

    # Start background scanner
    scanner_thread = threading.Thread(
        target=background_scanner,
        args=(scanner_state, aggregator, signal_engine, risk_manager, portfolio),
        daemon=True,
    )
    scanner_thread.start()
    logger.info("Background scanner started")

    # Start Flask
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting dashboard on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
