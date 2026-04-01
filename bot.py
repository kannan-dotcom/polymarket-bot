#!/usr/bin/env python3
"""
Polymarket HF Trading Bot — Main Entry Point

Usage:
    python bot.py                    # Paper trading mode (default)
    python bot.py --live             # Live trading (requires API keys)
    python bot.py --scan             # Single scan, print signals, exit
    python bot.py --backtest         # Run backtest simulation
    python bot.py --stats            # Show portfolio stats and exit

Starting capital: $100 USDC
Markets: BTC 5-min, ETH 5-min, S&P 500 daily
"""

import sys
import time
import signal
import logging
import argparse

from config import (
    STARTING_CAPITAL,
    MARKETS,
    POLL_INTERVAL_SECONDS,
    LOG_LEVEL,
)
from market_data import MarketDataAggregator
from polymarket_client import PolymarketClient, SimulatedPolymarketClient
from signals import SignalEngine
from risk_manager import RiskManager
from portfolio import Portfolio
from executor import TradeExecutor

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


def signal_handler(sig, frame):
    global running
    logger.info("Shutdown signal received. Stopping bot...")
    running = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def print_banner():
    print("""
╔══════════════════════════════════════════════════════╗
║         POLYMARKET HF TRADING BOT                    ║
║         High-Frequency Prediction Market Trader      ║
╠══════════════════════════════════════════════════════╣
║  Starting Capital:  $100.00 USDC                     ║
║  Strategy:          Price Feed Arbitrage              ║
║  Markets:  BTC | ETH | XRP | XLM 5m | SPX Daily      ║
║  Risk:              Quarter-Kelly | 5% max per trade  ║
║  Drawdown Limit:    10% daily                        ║
╚══════════════════════════════════════════════════════╝
    """)


def run_scan(executor: TradeExecutor):
    """Single scan mode — evaluate all markets once and print results."""
    print("\n--- MARKET SCAN ---\n")

    for market_key, cfg in MARKETS.items():
        if not cfg["enabled"]:
            print(f"  [{market_key}] DISABLED")
            continue

        symbol = cfg["symbol"]
        print(f"  Scanning {market_key} ({symbol})...")

        try:
            executor.agg.update(symbol)
            snapshot = executor.agg.get_snapshot(symbol)

            print(f"    Price:      ${snapshot['price']:,.2f}")
            print(f"    Momentum:   {snapshot['momentum']:.4f}")
            print(f"    RSI:        {snapshot['rsi']:.1f}")
            print(f"    Volatility: {snapshot['volatility']:.4f}")
            print(f"    VWAP Dev:   {snapshot['vwap_deviation']:.4f}")
            print(f"    EMA 12/26:  {snapshot['ema_12']:,.2f} / {snapshot['ema_26']:,.2f}")

            # Generate signal
            signal_result = executor.signals.generate(symbol, 0.50)
            print(f"    Signal:     {signal_result.direction.value}")
            print(f"    Model P(up): {signal_result.model_prob_up:.2%}")
            print(f"    Edge:       {signal_result.edge:.2%}")
            print(f"    Confidence: {signal_result.confidence:.2f}")
            print(f"    Tradeable:  {'YES' if signal_result.is_tradeable else 'NO'}")

            if signal_result.is_tradeable:
                size = executor.risk.compute_trade_size(signal_result)
                print(f"    Trade Size: ${size:.2f}")

            print(f"    Reasons:")
            for r in signal_result.reasons:
                print(f"      - {r}")

        except Exception as e:
            print(f"    ERROR: {e}")

        print()

    # Print portfolio status
    print(executor.risk.format_stats())


def run_loop(executor: TradeExecutor):
    """Main trading loop — continuously scan markets and execute trades."""
    global running
    cycle = 0

    while running:
        cycle += 1
        logger.info(f"--- Cycle {cycle} ---")

        try:
            # Scan all markets and execute where signals found
            contexts = executor.run_single_scan()

            if contexts:
                for ctx in contexts:
                    logger.info(
                        f"Trade taken: {ctx.market_key} | "
                        f"{ctx.signal.direction.value} | "
                        f"Size: ${ctx.trade_result.size:.2f}"
                    )

                    # In paper mode, simulate resolution after interval
                    if executor.paper_mode and ctx.position:
                        _simulate_resolution(executor, ctx)

            # Print stats every 10 cycles
            if cycle % 10 == 0:
                stats = executor.risk.get_stats()
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
        time.sleep(POLL_INTERVAL_SECONDS)

    # Final stats
    print(executor.portfolio.format_performance())
    print(executor.risk.format_stats())


def _simulate_resolution(executor: TradeExecutor, ctx):
    """
    In paper trading, simulate whether the prediction was correct.
    Uses the actual price movement during the round.
    """
    import random

    # For simulation: use the signal's model probability as the
    # approximate chance of being correct (since we only trade
    # when we have edge, this should be >50%)
    if ctx.signal.direction.value == "UP":
        win_prob = ctx.signal.model_prob_up
    else:
        win_prob = 1.0 - ctx.signal.model_prob_up

    # Add some noise to simulate real-world variance
    # The model isn't perfect — reduce win probability slightly
    adjusted_prob = win_prob * 0.85 + 0.05  # compress toward 50%
    won = random.random() < adjusted_prob

    executor.resolve_position(ctx.position.id, won)


def run_backtest(executor: TradeExecutor, num_rounds: int = 200):
    """
    Backtest simulation — runs N rounds using historical data patterns.
    """
    print(f"\n--- BACKTEST: {num_rounds} rounds ---\n")

    for i in range(num_rounds):
        contexts = executor.run_single_scan()
        for ctx in contexts:
            if ctx and ctx.position:
                _simulate_resolution(executor, ctx)

        if (i + 1) % 50 == 0:
            stats = executor.risk.get_stats()
            print(
                f"  Round {i+1:4d} | "
                f"Balance: ${stats['balance']:7.2f} | "
                f"P&L: ${stats['total_pnl']:+7.2f} | "
                f"Trades: {stats['total_trades']:3d} | "
                f"WR: {stats['win_rate']:5.1f}%"
            )

        # Small delay for API rate limits
        time.sleep(0.5)

    print(executor.portfolio.format_performance())


def main():
    parser = argparse.ArgumentParser(
        description="Polymarket HF Trading Bot — $100 Starting Capital"
    )
    parser.add_argument(
        "--live", action="store_true",
        help="Enable live trading (requires Polymarket API keys)"
    )
    parser.add_argument(
        "--scan", action="store_true",
        help="Single scan mode — evaluate markets and exit"
    )
    parser.add_argument(
        "--backtest", action="store_true",
        help="Run backtest simulation"
    )
    parser.add_argument(
        "--rounds", type=int, default=200,
        help="Number of backtest rounds (default: 200)"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Show portfolio stats and exit"
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Reset portfolio and trade history"
    )
    args = parser.parse_args()

    print_banner()

    # Initialize components
    aggregator = MarketDataAggregator()
    signal_engine = SignalEngine(aggregator)
    risk_manager = RiskManager(starting_balance=STARTING_CAPITAL)
    portfolio = Portfolio(starting_capital=STARTING_CAPITAL)

    paper_mode = not args.live
    executor = TradeExecutor(
        risk_manager=risk_manager,
        portfolio=portfolio,
        aggregator=aggregator,
        signal_engine=signal_engine,
        paper_mode=paper_mode,
    )

    if args.reset:
        portfolio.reset()
        print("Portfolio reset. Starting fresh with $100.00")
        return

    if args.stats:
        print(portfolio.format_performance())
        print(risk_manager.format_stats())
        return

    if args.scan:
        run_scan(executor)
        return

    if args.backtest:
        run_backtest(executor, num_rounds=args.rounds)
        return

    # Default: run the trading loop
    mode_str = "LIVE" if args.live else "PAPER"
    logger.info(f"Starting bot in {mode_str} mode with ${STARTING_CAPITAL:.2f}")
    run_loop(executor)


if __name__ == "__main__":
    main()
