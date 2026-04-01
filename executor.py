"""
Trade Execution Engine — Orchestrates the signal → size → execute → track loop.
Handles both live and simulated (paper) trading modes.
"""

import time
import logging
from dataclasses import dataclass
from typing import Optional

from market_data import MarketDataAggregator
from polymarket_client import PolymarketClient, SimulatedPolymarketClient, TradeResult
from signals import SignalEngine, Signal, Direction
from risk_manager import RiskManager, Position
from portfolio import Portfolio
from config import MARKETS, POLL_INTERVAL_SECONDS, PRE_ROUND_BUFFER_SECONDS

logger = logging.getLogger("executor")


@dataclass
class RoundContext:
    """Context for a single trading round."""
    market_key: str
    symbol: str
    token_id_yes: str
    token_id_no: str
    round_start: float
    round_end: float
    signal: Optional[Signal] = None
    position: Optional[Position] = None
    trade_result: Optional[TradeResult] = None


class TradeExecutor:
    """
    Main execution engine. Runs the trading loop:
    1. Fetch exchange data
    2. Fetch Polymarket odds
    3. Generate signal
    4. Size position
    5. Execute trade
    6. Track result
    """

    def __init__(
        self,
        risk_manager: RiskManager,
        portfolio: Portfolio,
        aggregator: MarketDataAggregator,
        signal_engine: SignalEngine,
        polymarket: Optional[PolymarketClient] = None,
        paper_mode: bool = True,
    ):
        self.risk = risk_manager
        self.portfolio = portfolio
        self.agg = aggregator
        self.signals = signal_engine
        self.paper_mode = paper_mode

        if paper_mode:
            self.poly = SimulatedPolymarketClient()
            logger.info("Running in PAPER TRADING mode")
        else:
            self.poly = polymarket or PolymarketClient()
            logger.info("Running in LIVE TRADING mode")

    def evaluate_market(self, market_key: str) -> Optional[RoundContext]:
        """
        Evaluate a single market for trading opportunity.
        Returns a RoundContext if a trade was executed, None otherwise.
        """
        market_cfg = MARKETS.get(market_key)
        if not market_cfg or not market_cfg["enabled"]:
            return None

        symbol = market_cfg["symbol"]

        # Step 1: Update exchange price data
        try:
            self.agg.update(symbol)
        except Exception as e:
            logger.error(f"Failed to fetch {symbol} data: {e}")
            return None

        # Step 2: Get Polymarket odds
        try:
            polymarket_yes_price = self._get_polymarket_price(market_key)
        except Exception as e:
            logger.warning(f"Failed to fetch Polymarket odds for {market_key}: {e}")
            # In paper mode, simulate with 50/50 odds
            polymarket_yes_price = 0.50

        # Step 3: Generate signal
        signal = self.signals.generate(symbol, polymarket_yes_price)
        logger.info(
            f"[{market_key}] Signal: {signal.direction.value} | "
            f"Model P(up)={signal.model_prob_up:.2%} | "
            f"Market P(up)={signal.market_prob_up:.2%} | "
            f"Edge={signal.edge:.2%} | "
            f"Confidence={signal.confidence:.2f}"
        )

        for reason in signal.reasons:
            logger.debug(f"  → {reason}")

        if not signal.is_tradeable:
            logger.info(f"[{market_key}] No trade — edge or confidence too low")
            return None

        # Step 4: Risk check and position sizing
        if not self.risk.is_trading_allowed():
            logger.warning(f"[{market_key}] Trading halted — risk limits breached")
            return None

        trade_size = self.risk.compute_trade_size(signal)
        if trade_size <= 0:
            logger.info(f"[{market_key}] Position size = $0 — skipping")
            return None

        # Step 5: Execute trade
        ctx = RoundContext(
            market_key=market_key,
            symbol=symbol,
            token_id_yes="",  # would be set from actual market lookup
            token_id_no="",
            round_start=time.time(),
            round_end=time.time() + market_cfg["interval"] * 60,
            signal=signal,
        )

        trade_result = self._execute_trade(signal, trade_size, ctx)
        ctx.trade_result = trade_result

        if trade_result.success:
            # Record position
            pos = self.risk.open_position(
                position_id=trade_result.order_id,
                market_id=market_key,
                symbol=symbol,
                signal=signal,
                entry_price=trade_result.price,
                size_usdc=trade_size,
            )
            ctx.position = pos

            # Log to portfolio
            self.portfolio.record_trade(
                trade_id=trade_result.order_id,
                market_key=market_key,
                symbol=symbol,
                direction=signal.direction.value,
                outcome=pos.outcome,
                entry_price=trade_result.price,
                size_usdc=trade_size,
                model_prob=signal.model_prob_up,
                market_prob=signal.market_prob_up,
                edge=signal.edge,
                confidence=signal.confidence,
            )

            logger.info(
                f"[{market_key}] *** TRADE EXECUTED *** "
                f"{'YES' if signal.direction == Direction.UP else 'NO'} "
                f"@ ${trade_result.price:.4f} | Size: ${trade_size:.2f} | "
                f"Order: {trade_result.order_id}"
            )
        else:
            logger.error(
                f"[{market_key}] Trade FAILED: {trade_result.error}"
            )

        return ctx

    def resolve_position(self, position_id: str, won: bool):
        """
        Resolve a position after the round ends.
        won: True if our prediction was correct.
        """
        pnl = self.risk.close_position(position_id, won)
        self.portfolio.resolve_trade(position_id, won, pnl)

        status = "WON" if won else "LOST"
        logger.info(
            f"Position {position_id} {status} | P&L: ${pnl:+.2f} | "
            f"Balance: ${self.risk.state.balance:.2f}"
        )

    def run_single_scan(self) -> list[RoundContext]:
        """
        Scan all enabled markets once and execute trades where signals exist.
        Returns list of contexts for trades taken.
        """
        results = []
        for market_key, cfg in MARKETS.items():
            if not cfg["enabled"]:
                continue
            ctx = self.evaluate_market(market_key)
            if ctx:
                results.append(ctx)
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_polymarket_price(self, market_key: str) -> float:
        """Fetch the current YES price from Polymarket for a market."""
        # In a full implementation, this would:
        # 1. Look up the active 5-min round for this asset
        # 2. Get the token_id for the YES outcome
        # 3. Fetch the midpoint price
        #
        # For now, we search for relevant markets
        market_cfg = MARKETS[market_key]
        try:
            markets = self.poly.get_crypto_5m_markets(
                asset=market_cfg["symbol"][:3]  # BTC, ETH
            )
            if markets and len(markets) > 0:
                # Get the most recent active market
                for m in markets:
                    tokens = m.get("tokens", [])
                    if tokens:
                        # YES token is typically first
                        return float(tokens[0].get("price", 0.5))
        except Exception:
            pass
        return 0.50  # default to 50/50 if can't fetch

    def _execute_trade(
        self,
        signal: Signal,
        size: float,
        ctx: RoundContext,
    ) -> TradeResult:
        """Place the actual trade on Polymarket."""
        # Determine which token to buy
        if signal.direction == Direction.UP:
            token_id = ctx.token_id_yes or "YES_TOKEN"
        else:
            token_id = ctx.token_id_no or "NO_TOKEN"

        return self.poly.place_market_order(
            token_id=token_id,
            side="BUY",
            size=size,
        )
