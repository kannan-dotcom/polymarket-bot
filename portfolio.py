"""
Portfolio Tracker — Persists trade history, P&L, and performance metrics
for multi-exchange stock trading.
"""

import json
import time
import os
from dataclasses import dataclass, field, asdict
from typing import Optional
from config import TRADE_HISTORY_FILE, PORTFOLIO_FILE, STARTING_CAPITAL


@dataclass
class TradeRecord:
    trade_id: str
    stock_key: str           # key in STOCKS dict
    ticker: str              # Yahoo Finance ticker
    exchange: str            # KLSE, SGX, DFM
    direction: str           # "BUY" or "SELL"
    entry_price: float
    size_usd: float
    score: float             # signal composite score
    edge: float
    confidence: float
    timestamp: float
    resolved: bool = False
    exit_price: float = 0.0
    pnl: float = 0.0
    balance_after: float = 0.0


class Portfolio:
    """
    Tracks all trades, persists to disk, and computes performance metrics.
    """

    def __init__(self, starting_capital: float = STARTING_CAPITAL):
        self.starting_capital = starting_capital
        self.trades: list[TradeRecord] = []
        self._load()

    def record_trade(
        self,
        trade_id: str,
        stock_key: str,
        ticker: str,
        exchange: str,
        direction: str,
        entry_price: float,
        size_usd: float,
        score: float,
        edge: float,
        confidence: float,
    ):
        """Record a new trade entry."""
        record = TradeRecord(
            trade_id=trade_id,
            stock_key=stock_key,
            ticker=ticker,
            exchange=exchange,
            direction=direction,
            entry_price=entry_price,
            size_usd=size_usd,
            score=score,
            edge=edge,
            confidence=confidence,
            timestamp=time.time(),
        )
        self.trades.append(record)
        self._save()

    def resolve_trade(self, trade_id: str, exit_price: float, pnl: float):
        """Mark a trade as resolved with its result."""
        for t in self.trades:
            if t.trade_id == trade_id and not t.resolved:
                t.resolved = True
                t.exit_price = exit_price
                t.pnl = pnl
                t.balance_after = self._compute_current_balance()
                break
        self._save()

    # ------------------------------------------------------------------
    # Performance metrics
    # ------------------------------------------------------------------

    def get_performance(self) -> dict:
        """Compute comprehensive performance metrics."""
        resolved = [t for t in self.trades if t.resolved]
        if not resolved:
            return {
                "total_trades": 0,
                "balance": self.starting_capital,
                "total_pnl": 0.0,
                "roi": 0.0,
                "win_rate": 0.0,
                "avg_edge": 0.0,
                "avg_pnl_per_trade": 0.0,
                "profit_factor": 0.0,
                "sharpe_estimate": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
                "streak": 0,
            }

        total_pnl = sum(t.pnl for t in resolved)
        wins = [t for t in resolved if t.pnl > 0]
        losses = [t for t in resolved if t.pnl <= 0]

        gross_profit = sum(t.pnl for t in wins) if wins else 0.0
        gross_loss = abs(sum(t.pnl for t in losses)) if losses else 0.0

        pnls = [t.pnl for t in resolved]
        import numpy as np
        pnl_array = np.array(pnls)

        # Current streak
        streak = 0
        for t in reversed(resolved):
            if t.pnl > 0 and streak >= 0:
                streak += 1
            elif t.pnl <= 0 and streak <= 0:
                streak -= 1
            else:
                break

        return {
            "total_trades": len(resolved),
            "balance": round(self._compute_current_balance(), 2),
            "total_pnl": round(total_pnl, 2),
            "roi": round(total_pnl / self.starting_capital * 100, 2),
            "win_rate": round(len(wins) / len(resolved) * 100, 2),
            "avg_edge": round(np.mean([t.edge for t in resolved]) * 100, 2),
            "avg_pnl_per_trade": round(np.mean(pnls), 2),
            "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else float("inf"),
            "sharpe_estimate": round(
                float(np.mean(pnl_array) / np.std(pnl_array)) if np.std(pnl_array) > 0 else 0.0,
                2
            ),
            "best_trade": round(max(pnls), 2),
            "worst_trade": round(min(pnls), 2),
            "streak": streak,
        }

    def get_trade_log(self, last_n: int = 20) -> list[dict]:
        """Return the most recent N trades as dicts."""
        recent = self.trades[-last_n:]
        return [asdict(t) for t in recent]

    def get_exchange_breakdown(self) -> dict:
        """Performance breakdown by exchange."""
        breakdown = {}
        for t in self.trades:
            if not t.resolved:
                continue
            key = t.exchange
            if key not in breakdown:
                breakdown[key] = {
                    "trades": 0, "wins": 0, "pnl": 0.0, "volume": 0.0
                }
            breakdown[key]["trades"] += 1
            if t.pnl > 0:
                breakdown[key]["wins"] += 1
            breakdown[key]["pnl"] += t.pnl
            breakdown[key]["volume"] += t.size_usd

        for key in breakdown:
            b = breakdown[key]
            b["win_rate"] = round(b["wins"] / b["trades"] * 100, 2) if b["trades"] > 0 else 0.0
            b["pnl"] = round(b["pnl"], 2)
            b["volume"] = round(b["volume"], 2)

        return breakdown

    def get_stock_breakdown(self) -> dict:
        """Performance breakdown by individual stock."""
        breakdown = {}
        for t in self.trades:
            if not t.resolved:
                continue
            key = t.stock_key
            if key not in breakdown:
                breakdown[key] = {
                    "ticker": t.ticker, "exchange": t.exchange,
                    "trades": 0, "wins": 0, "pnl": 0.0, "volume": 0.0
                }
            breakdown[key]["trades"] += 1
            if t.pnl > 0:
                breakdown[key]["wins"] += 1
            breakdown[key]["pnl"] += t.pnl
            breakdown[key]["volume"] += t.size_usd

        for key in breakdown:
            b = breakdown[key]
            b["win_rate"] = round(b["wins"] / b["trades"] * 100, 2) if b["trades"] > 0 else 0.0
            b["pnl"] = round(b["pnl"], 2)
            b["volume"] = round(b["volume"], 2)

        return breakdown

    def format_performance(self) -> str:
        """Pretty-print performance report."""
        p = self.get_performance()
        lines = [
            "",
            "=" * 60,
            "  PERFORMANCE REPORT",
            "=" * 60,
            f"  Starting Capital:  ${self.starting_capital:.2f}",
            f"  Current Balance:   ${p['balance']:.2f}",
            f"  Total P&L:         ${p['total_pnl']:+.2f} ({p['roi']:+.2f}%)",
            f"  Win Rate:          {p['win_rate']:.1f}%",
            f"  Total Trades:      {p['total_trades']}",
            f"  Avg P&L/Trade:     ${p['avg_pnl_per_trade']:+.2f}",
            f"  Profit Factor:     {p['profit_factor']:.2f}",
            f"  Sharpe Estimate:   {p['sharpe_estimate']:.2f}",
            f"  Best Trade:        ${p['best_trade']:+.2f}",
            f"  Worst Trade:       ${p['worst_trade']:+.2f}",
            f"  Current Streak:    {p['streak']:+d}",
            "=" * 60,
        ]

        # Exchange breakdown
        exchange_breakdown = self.get_exchange_breakdown()
        if exchange_breakdown:
            lines.append("")
            lines.append("  BY EXCHANGE:")
            lines.append("  " + "-" * 55)
            for key, b in exchange_breakdown.items():
                lines.append(
                    f"  {key:6s} | {b['trades']:3d} trades | "
                    f"WR: {b['win_rate']:5.1f}% | "
                    f"P&L: ${b['pnl']:+7.2f} | "
                    f"Vol: ${b['volume']:7.2f}"
                )
            lines.append("  " + "-" * 55)

        # Top stocks
        stock_breakdown = self.get_stock_breakdown()
        if stock_breakdown:
            lines.append("")
            lines.append("  TOP STOCKS BY P&L:")
            lines.append("  " + "-" * 55)
            sorted_stocks = sorted(
                stock_breakdown.items(),
                key=lambda x: x[1]["pnl"],
                reverse=True,
            )
            for key, b in sorted_stocks[:10]:
                lines.append(
                    f"  {key:12s} ({b['exchange']}) | {b['trades']:2d} trades | "
                    f"WR: {b['win_rate']:5.1f}% | "
                    f"P&L: ${b['pnl']:+7.2f}"
                )
            lines.append("  " + "-" * 55)

        lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _compute_current_balance(self) -> float:
        total_pnl = sum(t.pnl for t in self.trades if t.resolved)
        return self.starting_capital + total_pnl

    def _save(self):
        """Save trades to JSON file."""
        data = [asdict(t) for t in self.trades]
        try:
            with open(TRADE_HISTORY_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load(self):
        """Load trades from JSON file if exists."""
        if not os.path.exists(TRADE_HISTORY_FILE):
            return
        try:
            with open(TRADE_HISTORY_FILE, "r") as f:
                data = json.load(f)
            self.trades = [TradeRecord(**d) for d in data]
        except Exception:
            self.trades = []

    def reset(self):
        """Clear all trade history and start fresh."""
        self.trades = []
        self._save()
