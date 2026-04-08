#!/usr/bin/env python3
"""
Web Dashboard for Multi-Exchange Stock Scanner
Serves a Flask web UI while running the scanner in a background thread.
"""

import os
import sys
import time
import uuid
import threading
import logging
from flask import Flask, jsonify, render_template

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


# ---- Background sentiment scraper ----
sentiment_agg = None  # Module-level reference for API endpoints


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
                        "daily_volume": snapshot["daily_volume"],
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
                        "is_tradeable": signal.is_tradeable,
                        "is_strong": signal.is_strong,
                        # Sub-scores
                        "momentum_score": round(signal.momentum_score, 1),
                        "rsi_score": round(signal.rsi_score, 1),
                        "vwap_score": round(signal.vwap_score, 1),
                        "ema_score": round(signal.ema_score, 1),
                        "volume_score": round(signal.volume_score, 1),
                        "vol_price_score": round(signal.vol_price_score, 1),
                        "sentiment_score": round(signal.sentiment_score, 1),
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
app = Flask(__name__)
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
        }
    return jsonify({"enabled": True, "stocks": out})


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
        out.append({
            "stock_key": sk,
            "name": name,
            "mention_count": s.get("mentions", 0),
            "sentiment_score": round(s.get("sentiment_score", 50), 1),
            "buzz_score": round(s.get("buzz_score", 0), 1),
            "mention_trend": round(s.get("mention_trend", 0), 2),
        })
    return jsonify({"enabled": True, "trending": out})


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

    signal_engine = SignalEngine(aggregator, sentiment_aggregator=_sentiment)
    risk_manager = RiskManager(starting_balance=STARTING_CAPITAL)
    portfolio = Portfolio(starting_capital=STARTING_CAPITAL)

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
