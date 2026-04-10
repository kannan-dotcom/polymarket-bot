"""
Portfolio Optimization Engine
Mean-Variance Optimization (MVO) and Risk Parity allocation.
Uses historical returns from the scanner to compute optimal portfolio weights.
"""

import numpy as np
import logging
from dataclasses import dataclass, field
from typing import Optional
from market_data import MarketDataAggregator

logger = logging.getLogger("portfolio_optimizer")


@dataclass
class OptimizationResult:
    """Result of portfolio optimization for tradeable stocks."""
    method: str                              # "mvo" or "risk_parity"
    weights: dict[str, float] = field(default_factory=dict)  # ticker -> weight
    expected_return: float = 0.0             # portfolio expected annualized return
    expected_volatility: float = 0.0         # portfolio annualized volatility
    sharpe_ratio: float = 0.0               # portfolio Sharpe ratio
    diversification_ratio: float = 0.0       # >1 means diversification benefit
    max_weight: float = 0.0
    min_weight: float = 0.0
    num_assets: int = 0

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "weights": {k: round(v, 4) for k, v in self.weights.items()},
            "expected_return": round(self.expected_return, 4),
            "expected_volatility": round(self.expected_volatility, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 3),
            "diversification_ratio": round(self.diversification_ratio, 3),
            "max_weight": round(self.max_weight, 4),
            "min_weight": round(self.min_weight, 4),
            "num_assets": self.num_assets,
        }


class PortfolioOptimizer:
    """
    Computes optimal portfolio allocations using two methods:
    1. Mean-Variance Optimization (MVO) — Markowitz efficient frontier
    2. Risk Parity — equalizes risk contribution from each asset
    """

    def __init__(self, aggregator: MarketDataAggregator, risk_free_rate: float = 0.03):
        self.agg = aggregator
        self.rf = risk_free_rate  # annualized risk-free rate (3%)
        self._cache = {}
        self._cache_time = 0

    def optimize(
        self,
        tickers: list[str],
        method: str = "mvo",
        max_weight: float = 0.20,
        min_weight: float = 0.01,
        signal_scores: Optional[dict] = None,
    ) -> Optional[OptimizationResult]:
        """
        Run portfolio optimization on a set of tickers.

        Args:
            tickers: list of Yahoo Finance tickers
            method: "mvo" or "risk_parity"
            max_weight: maximum weight per asset
            min_weight: minimum weight per asset
            signal_scores: optional dict {ticker: score 0-100} to tilt MVO

        Returns OptimizationResult or None if insufficient data.
        """
        if len(tickers) < 2:
            return None

        # Collect return series
        return_series = {}
        for ticker in tickers:
            feed = self.agg.get_feed(ticker)
            if not feed or len(feed.candles) < 30:
                continue
            returns = self.agg.compute_returns(feed)
            if len(returns) < 20:
                continue
            # Use last 60 days of returns (or whatever is available)
            return_series[ticker] = returns[-60:]

        # Need at least 2 assets with enough history
        valid_tickers = list(return_series.keys())
        if len(valid_tickers) < 2:
            return None

        # Align lengths (use minimum common length)
        min_len = min(len(r) for r in return_series.values())
        if min_len < 15:
            return None

        returns_matrix = np.column_stack([
            return_series[t][-min_len:] for t in valid_tickers
        ])

        if method == "risk_parity":
            return self._risk_parity(valid_tickers, returns_matrix, max_weight)
        else:
            return self._mvo(valid_tickers, returns_matrix, max_weight, min_weight, signal_scores)

    def _mvo(
        self,
        tickers: list[str],
        returns: np.ndarray,
        max_weight: float,
        min_weight: float,
        signal_scores: Optional[dict],
    ) -> OptimizationResult:
        """
        Mean-Variance Optimization using analytical solution.
        Tilts expected returns by signal scores if provided.
        Uses iterative clipping to enforce weight constraints.
        """
        n_assets = len(tickers)
        mean_returns = np.mean(returns, axis=0) * 252  # annualize
        cov_matrix = np.cov(returns.T) * 252

        # Apply signal tilt: stocks with higher scores get higher expected returns
        if signal_scores:
            for i, ticker in enumerate(tickers):
                score = signal_scores.get(ticker, 50.0)
                # Score 50 = neutral, 75 = +50% tilt, 25 = -50% tilt
                tilt = (score - 50) / 50.0 * 0.5
                mean_returns[i] *= (1.0 + tilt)

        # Inverse variance portfolio as starting point (robust to estimation errors)
        variances = np.diag(cov_matrix)
        safe_var = np.where(variances > 0, variances, 1e-10)
        inv_var = 1.0 / safe_var
        weights = inv_var / np.sum(inv_var)

        # Tilt by expected return (combine inverse variance with return-weighted)
        if np.any(mean_returns > 0):
            return_weights = np.maximum(mean_returns, 0)
            if np.sum(return_weights) > 0:
                return_weights /= np.sum(return_weights)
                weights = 0.6 * weights + 0.4 * return_weights

        # Enforce constraints via clipping
        for _ in range(20):
            weights = np.clip(weights, min_weight, max_weight)
            total = np.sum(weights)
            if total > 0:
                weights /= total
            if np.all(weights >= min_weight - 1e-6) and np.all(weights <= max_weight + 1e-6):
                break

        # Normalize
        weights /= np.sum(weights)

        # Portfolio metrics
        port_return = float(np.dot(weights, mean_returns))
        port_vol = float(np.sqrt(np.dot(weights, np.dot(cov_matrix, weights))))
        sharpe = (port_return - self.rf) / port_vol if port_vol > 0 else 0.0

        # Diversification ratio
        weighted_vols = np.sum(weights * np.sqrt(np.diag(cov_matrix)))
        div_ratio = weighted_vols / port_vol if port_vol > 0 else 1.0

        weight_dict = {tickers[i]: float(weights[i]) for i in range(n_assets)}

        return OptimizationResult(
            method="mvo",
            weights=weight_dict,
            expected_return=port_return,
            expected_volatility=port_vol,
            sharpe_ratio=sharpe,
            diversification_ratio=div_ratio,
            max_weight=float(np.max(weights)),
            min_weight=float(np.min(weights)),
            num_assets=n_assets,
        )

    def _risk_parity(
        self,
        tickers: list[str],
        returns: np.ndarray,
        max_weight: float,
    ) -> OptimizationResult:
        """
        Risk Parity: each asset contributes equally to portfolio risk.
        Uses iterative Newton method to find weights.
        """
        n_assets = len(tickers)
        cov_matrix = np.cov(returns.T) * 252
        mean_returns = np.mean(returns, axis=0) * 252

        # Target: equal risk contribution
        target_risk = 1.0 / n_assets

        # Initial: equal weights
        weights = np.ones(n_assets) / n_assets

        # Iterative solving (simplified Spinu method)
        for iteration in range(100):
            port_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
            if port_vol == 0:
                break

            # Marginal risk contribution
            marginal = np.dot(cov_matrix, weights) / port_vol
            # Risk contribution
            risk_contrib = weights * marginal
            total_risk = np.sum(risk_contrib)

            if total_risk == 0:
                break

            # Risk contribution ratio
            risk_ratio = risk_contrib / total_risk

            # Adjustment: move toward equal risk
            adjustment = target_risk - risk_ratio
            step_size = 0.1 / (1 + iteration * 0.1)  # decreasing step
            weights = weights * (1.0 + adjustment * step_size)

            # Keep positive and normalize
            weights = np.maximum(weights, 1e-6)
            weights /= np.sum(weights)

        # Enforce max weight
        weights = np.clip(weights, 0, max_weight)
        weights /= np.sum(weights)

        # Portfolio metrics
        port_return = float(np.dot(weights, mean_returns))
        port_vol = float(np.sqrt(np.dot(weights, np.dot(cov_matrix, weights))))
        sharpe = (port_return - self.rf) / port_vol if port_vol > 0 else 0.0

        weighted_vols = np.sum(weights * np.sqrt(np.diag(cov_matrix)))
        div_ratio = weighted_vols / port_vol if port_vol > 0 else 1.0

        weight_dict = {tickers[i]: float(weights[i]) for i in range(n_assets)}

        return OptimizationResult(
            method="risk_parity",
            weights=weight_dict,
            expected_return=port_return,
            expected_volatility=port_vol,
            sharpe_ratio=sharpe,
            diversification_ratio=div_ratio,
            max_weight=float(np.max(weights)),
            min_weight=float(np.min(weights)),
            num_assets=n_assets,
        )

    def get_correlation_matrix(self, tickers: list[str]) -> Optional[dict]:
        """
        Compute correlation matrix for a set of tickers.
        Returns dict with tickers and correlation values.
        """
        return_series = {}
        for ticker in tickers:
            feed = self.agg.get_feed(ticker)
            if not feed or len(feed.candles) < 30:
                continue
            returns = self.agg.compute_returns(feed)
            if len(returns) < 20:
                continue
            return_series[ticker] = returns[-60:]

        valid = list(return_series.keys())
        if len(valid) < 2:
            return None

        min_len = min(len(r) for r in return_series.values())
        matrix = np.column_stack([return_series[t][-min_len:] for t in valid])
        corr = np.corrcoef(matrix.T)

        # Find most/least correlated pairs
        pairs = []
        for i in range(len(valid)):
            for j in range(i + 1, len(valid)):
                pairs.append((valid[i], valid[j], float(corr[i, j])))

        pairs.sort(key=lambda x: x[2])
        avg_corr = float(np.mean([p[2] for p in pairs]))

        return {
            "tickers": valid,
            "avg_correlation": round(avg_corr, 3),
            "least_correlated": [
                {"pair": [p[0], p[1]], "correlation": round(p[2], 3)}
                for p in pairs[:3]
            ],
            "most_correlated": [
                {"pair": [p[0], p[1]], "correlation": round(p[2], 3)}
                for p in pairs[-3:]
            ],
        }
