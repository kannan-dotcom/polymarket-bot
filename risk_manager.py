"""
Risk Manager — Position sizing, bankroll management, and drawdown controls.

Uses fractional Kelly Criterion for sizing, with hard caps
to protect the $100 starting bankroll.
"""

import time
from dataclasses import dataclass, field
from config import (
    STARTING_CAPITAL,
    MAX_POSITION_PCT,
    MAX_DAILY_LOSS_PCT,
    MAX_CONCURRENT_POSITIONS,
    MIN_TRADE_SIZE,
    MAX_TRADE_SIZE,
    KELLY_FRACTION,
)
from signals import Signal, Direction


@dataclass
class Position:
    """An open position."""
    id: str
    market_id: str
    symbol: str
    direction: Direction
    outcome: str              # "YES" or "NO"
    entry_price: float
    size_usdc: float
    shares: float             # size / entry_price
    timestamp: float
    signal_confidence: float
    signal_edge: float


@dataclass
class RiskState:
    """Current risk management state."""
    balance: float = STARTING_CAPITAL
    daily_start_balance: float = STARTING_CAPITAL
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    open_positions: list = field(default_factory=list)
    peak_balance: float = STARTING_CAPITAL
    max_drawdown: float = 0.0
    daily_trades: int = 0
    last_reset_day: str = ""


class RiskManager:
    """
    Controls position sizing and enforces risk limits.
    """

    def __init__(self, starting_balance: float = STARTING_CAPITAL):
        self.state = RiskState(
            balance=starting_balance,
            daily_start_balance=starting_balance,
            peak_balance=starting_balance,
        )

    # ------------------------------------------------------------------
    # Position sizing
    # ------------------------------------------------------------------

    def kelly_size(self, signal: Signal) -> float:
        """
        Fractional Kelly Criterion position size.

        Kelly formula: f* = (bp - q) / b
        where:
          b = odds ratio (net payout per $1 risked)
          p = probability of winning (our model)
          q = 1 - p

        For binary markets:
          If buying YES at price P, payout on win = (1/P - 1)
          b = (1 - P) / P
        """
        if signal.direction == Direction.UP:
            entry_price = signal.market_prob_up  # price of YES
            win_prob = signal.model_prob_up
        elif signal.direction == Direction.DOWN:
            entry_price = 1.0 - signal.market_prob_up  # price of NO
            win_prob = 1.0 - signal.model_prob_up
        else:
            return 0.0

        if entry_price <= 0 or entry_price >= 1:
            return 0.0

        # Odds: how much you win per dollar risked
        b = (1.0 - entry_price) / entry_price
        q = 1.0 - win_prob

        # Kelly fraction
        kelly_f = (b * win_prob - q) / b
        if kelly_f <= 0:
            return 0.0  # negative edge, don't trade

        # Apply fractional Kelly (conservative)
        fraction = kelly_f * KELLY_FRACTION

        # Convert to USDC amount
        raw_size = self.state.balance * fraction

        return raw_size

    def compute_trade_size(self, signal: Signal) -> float:
        """
        Final trade size after applying all constraints.
        Returns 0.0 if trade should be skipped.
        """
        if not signal.is_tradeable:
            return 0.0

        if not self._check_daily_loss_limit():
            return 0.0

        if len(self.state.open_positions) >= MAX_CONCURRENT_POSITIONS:
            return 0.0

        # Kelly-based size
        size = self.kelly_size(signal)

        # Cap at max position percentage
        max_pct_size = self.state.balance * MAX_POSITION_PCT
        size = min(size, max_pct_size)

        # Strong edge → allow slightly larger size (up to 1.5x)
        if signal.is_strong:
            size = min(size * 1.5, self.state.balance * MAX_POSITION_PCT * 1.5)

        # Hard caps
        size = min(size, MAX_TRADE_SIZE)
        size = max(size, 0.0)

        # Must meet minimum
        if size < MIN_TRADE_SIZE:
            return 0.0

        # Can't bet more than we have
        committed = sum(p.size_usdc for p in self.state.open_positions)
        available = self.state.balance - committed
        if size > available:
            size = available
        if size < MIN_TRADE_SIZE:
            return 0.0

        return round(size, 2)

    # ------------------------------------------------------------------
    # Position tracking
    # ------------------------------------------------------------------

    def open_position(
        self,
        position_id: str,
        market_id: str,
        symbol: str,
        signal: Signal,
        entry_price: float,
        size_usdc: float,
    ) -> Position:
        """Record a new open position."""
        outcome = "YES" if signal.direction == Direction.UP else "NO"
        shares = size_usdc / entry_price if entry_price > 0 else 0

        pos = Position(
            id=position_id,
            market_id=market_id,
            symbol=symbol,
            direction=signal.direction,
            outcome=outcome,
            entry_price=entry_price,
            size_usdc=size_usdc,
            shares=shares,
            timestamp=time.time(),
            signal_confidence=signal.confidence,
            signal_edge=signal.edge,
        )
        self.state.open_positions.append(pos)
        return pos

    def close_position(self, position_id: str, won: bool) -> float:
        """
        Close a position and update P&L.
        won: True if the outcome resolved in our favor.

        Returns the P&L for this trade.
        """
        pos = None
        for p in self.state.open_positions:
            if p.id == position_id:
                pos = p
                break

        if pos is None:
            return 0.0

        self.state.open_positions.remove(pos)
        self.state.total_trades += 1
        self.state.daily_trades += 1

        if won:
            # Payout = shares * $1.00 (winning shares pay $1)
            payout = pos.shares * 1.0
            pnl = payout - pos.size_usdc
            self.state.winning_trades += 1
        else:
            # Losing shares = $0
            pnl = -pos.size_usdc
            self.state.losing_trades += 1

        self.state.balance += pnl
        self.state.daily_pnl += pnl
        self.state.total_pnl += pnl

        # Update peak and drawdown
        if self.state.balance > self.state.peak_balance:
            self.state.peak_balance = self.state.balance
        drawdown = (self.state.peak_balance - self.state.balance) / self.state.peak_balance
        if drawdown > self.state.max_drawdown:
            self.state.max_drawdown = drawdown

        return pnl

    # ------------------------------------------------------------------
    # Risk checks
    # ------------------------------------------------------------------

    def _check_daily_loss_limit(self) -> bool:
        """Returns False if daily loss limit is breached."""
        self._maybe_reset_daily()
        max_loss = self.state.daily_start_balance * MAX_DAILY_LOSS_PCT
        return self.state.daily_pnl > -max_loss

    def _maybe_reset_daily(self):
        """Reset daily counters at start of new day."""
        today = time.strftime("%Y-%m-%d")
        if self.state.last_reset_day != today:
            self.state.last_reset_day = today
            self.state.daily_start_balance = self.state.balance
            self.state.daily_pnl = 0.0
            self.state.daily_trades = 0

    def is_trading_allowed(self) -> bool:
        """Check all risk constraints."""
        if self.state.balance < MIN_TRADE_SIZE:
            return False
        if not self._check_daily_loss_limit():
            return False
        return True

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Return current risk/portfolio stats."""
        win_rate = (
            self.state.winning_trades / self.state.total_trades
            if self.state.total_trades > 0
            else 0.0
        )
        committed = sum(p.size_usdc for p in self.state.open_positions)

        return {
            "balance": round(self.state.balance, 2),
            "total_pnl": round(self.state.total_pnl, 2),
            "total_pnl_pct": round(self.state.total_pnl / STARTING_CAPITAL * 100, 2),
            "daily_pnl": round(self.state.daily_pnl, 2),
            "total_trades": self.state.total_trades,
            "winning_trades": self.state.winning_trades,
            "losing_trades": self.state.losing_trades,
            "win_rate": round(win_rate * 100, 2),
            "open_positions": len(self.state.open_positions),
            "committed_capital": round(committed, 2),
            "available_capital": round(self.state.balance - committed, 2),
            "peak_balance": round(self.state.peak_balance, 2),
            "max_drawdown": round(self.state.max_drawdown * 100, 2),
        }

    def format_stats(self) -> str:
        """Pretty-print portfolio stats."""
        s = self.get_stats()
        lines = [
            "=" * 50,
            "  PORTFOLIO STATUS",
            "=" * 50,
            f"  Balance:       ${s['balance']:.2f}",
            f"  Total P&L:     ${s['total_pnl']:+.2f} ({s['total_pnl_pct']:+.2f}%)",
            f"  Daily P&L:     ${s['daily_pnl']:+.2f}",
            f"  Win Rate:      {s['win_rate']:.1f}% ({s['winning_trades']}W / {s['losing_trades']}L)",
            f"  Total Trades:  {s['total_trades']}",
            f"  Open Pos:      {s['open_positions']}",
            f"  Committed:     ${s['committed_capital']:.2f}",
            f"  Available:     ${s['available_capital']:.2f}",
            f"  Peak Balance:  ${s['peak_balance']:.2f}",
            f"  Max Drawdown:  {s['max_drawdown']:.1f}%",
            "=" * 50,
        ]
        return "\n".join(lines)
