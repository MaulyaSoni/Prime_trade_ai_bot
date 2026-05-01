"""
orders.py — order placement logic and response formatting.
Each function builds the Binance-specific params dict and delegates
the actual HTTP call to BinanceClient.
"""
import logging
from typing import Any, Dict, Optional

from bot.client import BASE_URL, ORDER_ENDPOINT, BinanceClient

logger = logging.getLogger("trading_bot.orders")

# ------------------------------------------------------------------ #
#  Order placement functions                                           #
# ------------------------------------------------------------------ #


def place_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: float,
) -> Dict[str, Any]:
    """Place a MARKET order — executes immediately at current best price."""
    params: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": quantity,
    }
    logger.info(
        "Placing MARKET order | symbol=%s side=%s qty=%s", symbol, side, quantity
    )
    return client.post_signed(ORDER_ENDPOINT, params)


def place_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    time_in_force: str = "GTC",
) -> Dict[str, Any]:
    """Place a LIMIT order — executes only at the specified price or better."""
    params: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "type": "LIMIT",
        "quantity": quantity,
        "price": price,
        "timeInForce": time_in_force,
    }
    logger.info(
        "Placing LIMIT order | symbol=%s side=%s qty=%s price=%s tif=%s",
        symbol, side, quantity, price, time_in_force,
    )
    return client.post_signed(ORDER_ENDPOINT, params)


def place_stop_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    stop_price: float,
    time_in_force: str = "GTC",
) -> Dict[str, Any]:
    """
    Place a STOP-LIMIT order (Binance type: STOP).
    - stopPrice  → price at which the order is triggered
    - price      → limit price the order is placed at once triggered
    """
    params: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "type": "STOP",          # Binance Futures uses 'STOP' for stop-limit
        "quantity": quantity,
        "price": price,
        "stopPrice": stop_price,
        "timeInForce": time_in_force,
    }
    logger.info(
        "Placing STOP_LIMIT order | symbol=%s side=%s qty=%s "
        "limitPrice=%s stopPrice=%s tif=%s",
        symbol, side, quantity, price, stop_price, time_in_force,
    )
    return client.post_signed(ORDER_ENDPOINT, params)


# ------------------------------------------------------------------ #
#  Response formatting                                                 #
# ------------------------------------------------------------------ #

_DIVIDER = "─" * 52


def _field(label: str, value: Any, unit: str = "") -> str:
    display = f"{value}{unit}" if value not in (None, "", "0", 0) else "—"
    return f"  {label:<18}: {display}"


def format_order_response(response: Dict[str, Any]) -> str:
    lines = [
        "",
        _DIVIDER,
        "  ✅  ORDER PLACED SUCCESSFULLY",
        _DIVIDER,
        _field("Order ID",     response.get("orderId")),
        _field("Symbol",       response.get("symbol")),
        _field("Side",         response.get("side")),
        _field("Type",         response.get("type")),
        _field("Status",       response.get("status")),
        _field("Quantity",     response.get("origQty")),
        _field("Executed Qty", response.get("executedQty")),
        _field("Avg Price",    response.get("avgPrice")),
        _field("Limit Price",  response.get("price")),
        _field("Stop Price",   response.get("stopPrice")),
        _field("Time in Force",response.get("timeInForce")),
        _DIVIDER,
        "",
    ]
    return "\n".join(lines)


def format_error(code: Any, msg: str) -> str:
    return (
        f"\n{_DIVIDER}\n"
        f"  ❌  ORDER FAILED\n"
        f"{_DIVIDER}\n"
        f"  Error Code : {code}\n"
        f"  Message    : {msg}\n"
        f"{_DIVIDER}\n"
    )
