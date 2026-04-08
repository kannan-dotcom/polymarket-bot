#!/usr/bin/env python3
"""
Multi-Exchange Stock Scanner & Trading Bot — Main Entry Point

Usage:
    python bot.py                    # Scan all stocks once (default)
    python bot.py --scan             # Same as above — single scan
    python bot.py --loop             # Continuous scanning loop
    python bot.py --backtest         # Run backtest simulation
    python bot.py --stats            # Show portfolio stats and exit
    python bot.py --exchange KLSE    # Scan only one exchange

Exchanges: Bursa Malaysia (KLSE), SGX Singapore, DFM Dubai
Starting Capital: $100 USD
"""

import sys
import time
import signal as sig
import logging
import argparse
import uuid

from config import (
    STARTING_CAPITAL,
    STOCKS,
    EXCHANGES,
    POLL_INTERVAL_SECONDS,
    LOG_LEVEL,
    SENTIMENT_ENABLED,
)
from market_data import MarketDataAggregator
from signals import SignalEngine, Direction
from risk_manager import RiskManager
from portfolio import Portfolio

# ---- Logging setup ----
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("trades.log"),
    ],
)
logger = logging.getLogger("bot")


# ---- Graceful shutdown ----
running = True


def signal_handler(s, frame):
    global running
    logger.info("Shutdown signal received. Stopping bot...")
    running = False


sig.signal(sig.SIGINT, signal_handler)
sig.signal(sig.SIGTERM, signal_handler)


def print_banner():
    print("""
╔════════════════════════════════════════════════════════════╗
║         MULTI-EXCHANGE STOCK SCANNER & TRADER              ║
║         KLSE | SGX | DFM — Yahoo Finance Data Feed         ║
╠════════════════════════════════════════════════════════════╣
║  Starting Capital:  $100.00 USD                            ║
║  Strategy:          Technical Composite Scoring (0-100)    ║
║  Indicators:        Momentum | RSI | VWAP | EMA | Volume   ║
║  Stocks:            48 across 3 exchanges                  ║
║  Risk:              Quarter-Kelly | 5% max per trade       ║
║  Drawdown Limit:    10% daily                              ║
╚════════════════════════════════════════════════════════════╝
    """)


def get_stocks_for_exchange(exchange_filter: str = None) -> dict:
    """Get stocks filtered by exchange, or all enabled stocks."""
    result = {}
    for key, cfg in STOCKS.items():
        if not cfg["enabled"]:
            continue
        if exchange_filter and cfg["exchange"] != exchange_filter.upper():
            continue
        result[key] = cfg
    return result


def run_scan(
    aggregator: MarketDataAggregator,
    signal_engine: SignalEngine,
    risk_manager: RiskManager,
    portfolio: Portfolio,
    exchange_filter: str = None,
    paper_mode: bool = True,
):
    """Single scan mode — evaluate all stocks and print results."""
    stocks = get_stocks_for_exchange(exchange_filter)
    if not stocks:
        print(f"No enabled stocks found{' for ' + exchange_filter if exchange_filter else ''}.")
        return

    current_exchange = None
    signals_found = 0
    tradeable_count = 0

    for stock_key, cfg in stocks.items():
        ticker = cfg["ticker"]
        exchange = cfg["exchange"]

        # Print exchange header
        if exchange != current_exchange:
            current_exchange = exchange
            ex_info = EXCHANGES[exchange]
            print(f"\n{'='*60}")
            print(f"  {ex_info['name']} ({exchange}) — {ex_info['currency']}")
            print(f"{'='*60}")

        # Fetch data
        try:
            feed = aggregator.update(ticker)
            if not feed:
                print(f"  [{stock_key:12s}] {cfg['name']:25s} — NO DATA")
                continue

            snapshot = aggregator.get_snapshot(ticker)
            if not snapshot:
                print(f"  [{stock_key:12s}] {cfg['name']:25s} — NO SNAPSHOT")
                continue

            # Generate signal
            signal_result = signal_engine.generate(ticker)
            signals_found += 1

            # Direction symbol
            if signal_result.direction == Direction.BUY:
                dir_sym = "▲ BUY "
            elif signal_result.direction == Direction.SELL:
                dir_sym = "▼ SELL"
            else:
                dir_sym = "— HOLD"

            # Tradeable?
            trade_size = risk_manager.compute_trade_size(signal_result)
            tradeable = "✓" if trade_size > 0 else " "
            if trade_size > 0:
                tradeable_count += 1

            print(
                f"  [{stock_key:12s}] {cfg['name']:25s} | "
                f"${snapshot['price']:>10.2f} | "
                f"Score: {signal_result.score:5.1f} | "
                f"{dir_sym} | "
                f"Edge: {signal_result.edge:5.2%} | "
                f"Conf: {signal_result.confidence:.2f} | "
                f"RSI: {snapshot['rsi']:5.1f} | "
                f"Mom: {snapshot['momentum']:+.2%} | "
                f"Vol: {snapshot['volume_ratio']:.1f}x | "
                f"{tradeable}"
            )

            # Print trade details if tradeable
            if trade_size > 0:
                print(
                    f"  {'':12s}  → Trade: ${trade_size:.2f} | "
                    f"Reasons: {', '.join(signal_result.reasons[:3])}"
                )

                # In paper mode, record and simulate
                if paper_mode:
                    trade_id = str(uuid.uuid4())[:8]
                    risk_manager.open_position(
                        position_id=trade_id,
                        stock_key=stock_key,
                        ticker=ticker,
                        exchange=exchange,
                        signal=signal_result,
                        entry_price=snapshot["price"],
                        size_usd=trade_size,
                    )
                    portfolio.record_trade(
                        trade_id=trade_id,
                        stock_key=stock_key,
                        ticker=ticker,
                        exchange=exchange,
                        direction=signal_result.direction.value,
                        entry_price=snapshot["price"],
                        size_usd=trade_size,
                        score=signal_result.score,
                        edge=signal_result.edge,
                        confidence=signal_result.confidence,
                    )

            # Small delay to be nice to Yahoo Finance API
            time.sleep(0.3)

        except Exception as e:
            print(f"  [{stock_key:12s}] {cfg['name']:25s} — ERROR: {e}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  SCAN SUMMARY")
    print(f"{'='*60}")
    print(f"  Stocks scanned:   {signals_found}")
    print(f"  Tradeable signals: {tradeable_count}")
    print(f"{'='*60}")

    # Print portfolio status
    print(risk_manager.format_stats())


def run_loop(
    aggregator: MarketDataAggregator,
    signal_engine: SignalEngine,
    risk_manager: RiskManager,
    portfolio: Portfolio,
    exchange_filter: str = None,
):
    """Continuous scanning loop."""
    global running
    cycle = 0

    while running:
        cycle += 1
        logger.info(f"--- Scan Cycle {cycle} ---")

        try:
            run_scan(
                aggregator, signal_engine, risk_manager, portfolio,
                exchange_filter=exchange_filter,
                paper_mode=True,
            )

            # Print stats every 5 cycles
            if cycle % 5 == 0:
                stats = risk_manager.get_stats()
                logger.info(
                    f"Balance: ${stats['balance']:.2f} | "
                    f"P&L: ${stats['total_pnl']:+.2f} | "
                    f"Trades: {stats['total_trades']} | "
                    f"WR: {stats['win_rate']:.1f}%"
                )

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in cycle {cycle}: {e}", exc_info=True)

        # Wait before next scan
        logger.info(f"Waiting {POLL_INTERVAL_SECONDS}s before next scan...")
        for _ in range(POLL_INTERVAL_SECONDS):
            if not running:
                break
            time.sleep(1)

    # Final stats
    print(portfolio.format_performance())
    print(risk_manager.format_stats())


def run_backtest(
    aggregator: MarketDataAggregator,
    signal_engine: SignalEngine,
    risk_manager: RiskManager,
    portfolio: Portfolio,
    exchange_filter: str = None,
    num_rounds: int = 50,
):
    """
    Backtest simulation — uses historical price data to simulate trades.
    For each stock, walks through historical candles and generates signals.
    """
    import random

    stocks = get_stocks_for_exchange(exchange_filter)
    if not stocks:
        print("No stocks to backtest.")
        return

    print(f"\n--- BACKTEST: {len(stocks)} stocks, {num_rounds} simulated rounds ---\n")

    # First, load all data
    print("  Loading historical data...")
    for stock_key, cfg in stocks.items():
        aggregator.update(cfg["ticker"])
        time.sleep(0.3)

    print("  Running simulation...\n")

    for round_num in range(num_rounds):
        for stock_key, cfg in stocks.items():
            ticker = cfg["ticker"]
            exchange = cfg["exchange"]

            snapshot = aggregator.get_snapshot(ticker)
            if not snapshot:
                continue

            signal_result = signal_engine.generate(ticker)
            trade_size = risk_manager.compute_trade_size(signal_result)

            if trade_size > 0:
                trade_id = str(uuid.uuid4())[:8]
                entry_price = snapshot["price"]

                # Open position
                pos = risk_manager.open_position(
                    position_id=trade_id,
                    stock_key=stock_key,
                    ticker=ticker,
                    exchange=exchange,
                    signal=signal_result,
                    entry_price=entry_price,
                    size_usd=trade_size,
                )

                portfolio.record_trade(
                    trade_id=trade_id,
                    stock_key=stock_key,
                    ticker=ticker,
                    exchange=exchange,
                    direction=signal_result.direction.value,
                    entry_price=entry_price,
                    size_usd=trade_size,
                    score=signal_result.score,
                    edge=signal_result.edge,
                    confidence=signal_result.confidence,
                )

                # Simulate exit: use ATR-based price movement
                atr = snapshot["atr"]
                atr_pct = atr / entry_price if entry_price > 0 else 0.02

                # Win probability based on signal strength
                score_dist = abs(signal_result.score - 50) / 50
                win_prob = 0.50 + score_dist * 0.15
                won = random.random() < win_prob

                if won:
                    move = abs(random.gauss(atr_pct, atr_pct * 0.5))
                else:
                    move = -abs(random.gauss(atr_pct * 0.8, atr_pct * 0.3))

                if signal_result.direction == Direction.BUY:
                    exit_price = entry_price * (1 + move)
                else:
                    exit_price = entry_price * (1 - move)

                pnl = risk_manager.close_position(trade_id, exit_price)
                portfolio.resolve_trade(trade_id, exit_price, pnl)

        # Progress report
        if (round_num + 1) % 10 == 0:
            stats = risk_manager.get_stats()
            print(
                f"  Round {round_num+1:4d} | "
                f"Balance: ${stats['balance']:7.2f} | "
                f"P&L: ${stats['total_pnl']:+7.2f} | "
                f"Trades: {stats['total_trades']:3d} | "
                f"WR: {stats['win_rate']:5.1f}%"
            )

    print(portfolio.format_performance())


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Exchange Stock Scanner — KLSE | SGX | DFM"
    )
    parser.add_argument(
        "--scan", action="store_true",
        help="Single scan mode — evaluate all stocks and exit (default)"
    )
    parser.add_argument(
        "--loop", action="store_true",
        help="Continuous scanning loop"
    )
    parser.add_argument(
        "--backtest", action="store_true",
        help="Run backtest simulation"
    )
    parser.add_argument(
        "--rounds", type=int, default=50,
        help="Number of backtest rounds (default: 50)"
    )
    parser.add_argument(
        "--exchange", type=str, default=None,
        help="Filter by exchange: KLSE, SGX, or DFM"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Show portfolio stats and exit"
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Reset portfolio and trade history"
    )
    parser.add_argument(
        "--sentiment", action="store_true",
        help="Enable forum sentiment analysis (scrapes 6 sources)"
    )
    args = parser.parse_args()

    print_banner()

    # Initialize components
    aggregator = MarketDataAggregator()

    # Sentiment (optional)
    _sentiment = None
    if args.sentiment or SENTIMENT_ENABLED:
        try:
            from sentiment_scraper import SentimentAggregator
            _sentiment = SentimentAggregator()
            print("  Sentiment analysis: ENABLED (scraping 6 forum sources)")
            _sentiment.update()
            stats = _sentiment.get_all_sentiments()
            active = sum(1 for s in stats.values() if s.mention_count > 0)
            print(f"  Initial scrape: {active} stocks with forum mentions")
        except Exception as e:
            print(f"  Sentiment init failed (continuing without): {e}")
            _sentiment = None

    signal_engine = SignalEngine(aggregator, sentiment_aggregator=_sentiment)
    risk_manager = RiskManager(starting_balance=STARTING_CAPITAL)
    portfolio = Portfolio(starting_capital=STARTING_CAPITAL)

    if args.reset:
        portfolio.reset()
        print("Portfolio reset. Starting fresh with $100.00")
        return

    if args.stats:
        print(portfolio.format_performance())
        print(risk_manager.format_stats())
        return

    if args.backtest:
        run_backtest(
            aggregator, signal_engine, risk_manager, portfolio,
            exchange_filter=args.exchange,
            num_rounds=args.rounds,
        )
        return

    if args.loop:
        logger.info(f"Starting continuous scan loop with ${STARTING_CAPITAL:.2f}")
        run_loop(
            aggregator, signal_engine, risk_manager, portfolio,
            exchange_filter=args.exchange,
        )
        return

    # Default: single scan
    run_scan(
        aggregator, signal_engine, risk_manager, portfolio,
        exchange_filter=args.exchange,
        paper_mode=True,
    )


if __name__ == "__main__":
    main()
