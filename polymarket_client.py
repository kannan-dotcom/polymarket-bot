"""
Polymarket Integration Module — Fetches markets, odds, orderbooks.
Handles trade placement via the CLOB API.

NOTE: Actual order execution requires API keys + wallet on Polygon.
This module provides the full interface; set keys in .env to go live.
"""

import time
import hmac
import hashlib
import requests
from dataclasses import dataclass
from typing import Optional
from config import (
    POLYMARKET_CLOB_URL,
    POLYMARKET_GAMMA_URL,
    POLYMARKET_API_KEY,
    POLYMARKET_API_SECRET,
    POLYMARKET_PASSPHRASE,
)


@dataclass
class PolymarketMarket:
    """Represents a single binary market on Polymarket."""
    condition_id: str
    question: str
    token_id_yes: str
    token_id_no: str
    price_yes: float          # current price of YES token (0-1)
    price_no: float           # current price of NO token (0-1)
    volume: float
    end_date: str
    active: bool
    slug: str


@dataclass
class OrderBookLevel:
    price: float
    size: float


@dataclass
class OrderBook:
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    midpoint: float
    spread: float


@dataclass
class TradeResult:
    success: bool
    order_id: str = ""
    side: str = ""          # "BUY" or "SELL"
    outcome: str = ""       # "YES" or "NO"
    price: float = 0.0
    size: float = 0.0
    error: str = ""


class PolymarketClient:
    """Interface to Polymarket Gamma (data) and CLOB (trading) APIs."""

    def __init__(self, api_key: str = "", api_secret: str = "", passphrase: str = ""):
        self.api_key = api_key or POLYMARKET_API_KEY
        self.api_secret = api_secret or POLYMARKET_API_SECRET
        self.passphrase = passphrase or POLYMARKET_PASSPHRASE
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    # ------------------------------------------------------------------
    # Authentication helpers
    # ------------------------------------------------------------------

    def _sign_request(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        """HMAC-SHA256 signature for CLOB API requests."""
        message = timestamp + method.upper() + path + body
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def _auth_headers(self, method: str, path: str, body: str = "") -> dict:
        """Build authentication headers for trading endpoints."""
        timestamp = str(int(time.time()))
        signature = self._sign_request(timestamp, method, path, body)
        return {
            "POLY_API_KEY": self.api_key,
            "POLY_TIMESTAMP": timestamp,
            "POLY_SIGNATURE": signature,
            "POLY_PASSPHRASE": self.passphrase,
        }

    @property
    def is_authenticated(self) -> bool:
        return bool(self.api_key and self.api_secret)

    # ------------------------------------------------------------------
    # Market data (Gamma API — no auth needed)
    # ------------------------------------------------------------------

    def search_markets(self, query: str, limit: int = 10) -> list[dict]:
        """Search for markets by keyword."""
        url = f"{POLYMARKET_GAMMA_URL}/markets"
        params = {"limit": limit, "active": True}
        if query:
            params["tag"] = query
        resp = self.session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_crypto_5m_markets(self, asset: str = "BTC") -> list[dict]:
        """Fetch active 5-minute crypto prediction markets."""
        url = f"{POLYMARKET_GAMMA_URL}/markets"
        params = {
            "active": True,
            "limit": 20,
            "tag": f"{asset}-5M",
        }
        resp = self.session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_market_by_id(self, condition_id: str) -> Optional[dict]:
        """Get details for a specific market."""
        url = f"{POLYMARKET_GAMMA_URL}/markets/{condition_id}"
        resp = self.session.get(url, timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def get_events(self, slug: str = "", limit: int = 20) -> list[dict]:
        """List events, optionally filtered by slug."""
        url = f"{POLYMARKET_GAMMA_URL}/events"
        params = {"limit": limit, "active": True}
        if slug:
            params["slug"] = slug
        resp = self.session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Order book (CLOB API — public endpoints)
    # ------------------------------------------------------------------

    def get_orderbook(self, token_id: str) -> OrderBook:
        """Fetch the order book for a token."""
        url = f"{POLYMARKET_CLOB_URL}/book"
        params = {"token_id": token_id}
        resp = self.session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        bids = [OrderBookLevel(float(b["price"]), float(b["size"])) for b in data.get("bids", [])]
        asks = [OrderBookLevel(float(a["price"]), float(a["size"])) for a in data.get("asks", [])]

        best_bid = bids[0].price if bids else 0.0
        best_ask = asks[0].price if asks else 1.0

        return OrderBook(
            bids=bids,
            asks=asks,
            midpoint=(best_bid + best_ask) / 2,
            spread=best_ask - best_bid,
        )

    def get_midpoint(self, token_id: str) -> float:
        """Get midpoint price for a token."""
        url = f"{POLYMARKET_CLOB_URL}/midpoint"
        params = {"token_id": token_id}
        resp = self.session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return float(resp.json().get("mid", 0.5))

    def get_price(self, token_id: str, side: str = "BUY") -> float:
        """Get price for a specific side (BUY/SELL)."""
        url = f"{POLYMARKET_CLOB_URL}/price"
        params = {"token_id": token_id, "side": side}
        resp = self.session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return float(resp.json().get("price", 0.5))

    def get_last_trade(self, token_id: str) -> float:
        """Get the last trade price."""
        url = f"{POLYMARKET_CLOB_URL}/last-trade-price"
        params = {"token_id": token_id}
        resp = self.session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return float(resp.json().get("price", 0.5))

    # ------------------------------------------------------------------
    # Trading (CLOB API — requires auth)
    # ------------------------------------------------------------------

    def place_market_order(
        self,
        token_id: str,
        side: str,
        size: float,
    ) -> TradeResult:
        """
        Place a market order.
        side: "BUY" or "SELL"
        size: amount in USDC
        """
        if not self.is_authenticated:
            return TradeResult(
                success=False,
                error="Not authenticated. Set API keys in .env to trade live.",
            )

        path = "/order"
        body_dict = {
            "tokenID": token_id,
            "side": side,
            "size": str(size),
            "type": "MARKET",
        }
        import json
        body = json.dumps(body_dict)

        headers = self._auth_headers("POST", path, body)
        headers["Content-Type"] = "application/json"

        url = f"{POLYMARKET_CLOB_URL}{path}"
        resp = self.session.post(url, data=body, headers=headers, timeout=15)

        if resp.status_code == 200:
            data = resp.json()
            return TradeResult(
                success=True,
                order_id=data.get("orderID", ""),
                side=side,
                price=float(data.get("price", 0)),
                size=size,
            )
        else:
            return TradeResult(
                success=False,
                error=f"HTTP {resp.status_code}: {resp.text}",
            )

    def place_limit_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
    ) -> TradeResult:
        """
        Place a limit order at a specific price.
        price: 0.01 to 0.99
        """
        if not self.is_authenticated:
            return TradeResult(
                success=False,
                error="Not authenticated. Set API keys in .env to trade live.",
            )

        path = "/order"
        body_dict = {
            "tokenID": token_id,
            "side": side,
            "price": str(price),
            "size": str(size),
            "type": "LIMIT",
        }
        import json
        body = json.dumps(body_dict)

        headers = self._auth_headers("POST", path, body)
        headers["Content-Type"] = "application/json"

        url = f"{POLYMARKET_CLOB_URL}{path}"
        resp = self.session.post(url, data=body, headers=headers, timeout=15)

        if resp.status_code == 200:
            data = resp.json()
            return TradeResult(
                success=True,
                order_id=data.get("orderID", ""),
                side=side,
                price=price,
                size=size,
            )
        else:
            return TradeResult(
                success=False,
                error=f"HTTP {resp.status_code}: {resp.text}",
            )

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        if not self.is_authenticated:
            return False

        path = "/order"
        body_dict = {"orderID": order_id}
        import json
        body = json.dumps(body_dict)

        headers = self._auth_headers("DELETE", path, body)
        headers["Content-Type"] = "application/json"

        url = f"{POLYMARKET_CLOB_URL}{path}"
        resp = self.session.delete(url, data=body, headers=headers, timeout=10)
        return resp.status_code == 200


class SimulatedPolymarketClient(PolymarketClient):
    """
    Paper trading mode — simulates order fills locally.
    Uses real market data but doesn't place actual orders.
    """

    def __init__(self):
        super().__init__()
        self._order_counter = 0

    def place_market_order(self, token_id: str, side: str, size: float) -> TradeResult:
        """Simulate a market order fill at current midpoint."""
        try:
            price = self.get_midpoint(token_id)
        except Exception:
            price = 0.50  # fallback for simulation

        self._order_counter += 1
        return TradeResult(
            success=True,
            order_id=f"SIM-{self._order_counter:06d}",
            side=side,
            price=price,
            size=size,
        )

    def place_limit_order(self, token_id: str, side: str, price: float, size: float) -> TradeResult:
        """Simulate a limit order fill at the specified price."""
        self._order_counter += 1
        return TradeResult(
            success=True,
            order_id=f"SIM-{self._order_counter:06d}",
            side=side,
            price=price,
            size=size,
        )

    def cancel_order(self, order_id: str) -> bool:
        return True
