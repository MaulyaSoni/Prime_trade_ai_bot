"""
validators.py — all CLI input validation lives here.
Raises typer.BadParameter so Typer prints a clean error and exits.
"""
from typing import Optional

import typer

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}
VALID_TIF = {"GTC", "IOC", "FOK"}


def validate_symbol(symbol: str) -> str:
    symbol = symbol.upper().strip()
    if not symbol.isalpha() or len(symbol) < 3:
        raise typer.BadParameter(
            f"'{symbol}' is not a valid symbol. Use alphabetic pairs like BTCUSDT."
        )
    return symbol


def validate_side(side: str) -> str:
    side = side.upper().strip()
    if side not in VALID_SIDES:
        raise typer.BadParameter(
            f"Side '{side}' is invalid. Choose from: {', '.join(VALID_SIDES)}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    order_type = order_type.upper().strip()
    if order_type not in VALID_ORDER_TYPES:
        raise typer.BadParameter(
            f"Order type '{order_type}' is invalid. "
            f"Choose from: {', '.join(VALID_ORDER_TYPES)}."
        )
    return order_type


def validate_quantity(quantity: float) -> float:
    if quantity <= 0:
        raise typer.BadParameter(
            f"Quantity must be a positive number, got {quantity}."
        )
    return round(quantity, 8)


def validate_price(price: Optional[float], order_type: str) -> Optional[float]:
    if order_type in ("LIMIT", "STOP_LIMIT") and price is None:
        raise typer.BadParameter(
            f"--price is required for {order_type} orders."
        )
    if price is not None and price <= 0:
        raise typer.BadParameter(
            f"Price must be a positive number, got {price}."
        )
    return round(price, 8) if price is not None else None


def validate_stop_price(stop_price: Optional[float], order_type: str) -> Optional[float]:
    if order_type == "STOP_LIMIT" and stop_price is None:
        raise typer.BadParameter(
            "--stop-price is required for STOP_LIMIT orders."
        )
    if stop_price is not None and stop_price <= 0:
        raise typer.BadParameter(
            f"Stop price must be a positive number, got {stop_price}."
        )
    return round(stop_price, 8) if stop_price is not None else None


def validate_tif(tif: str) -> str:
    tif = tif.upper().strip()
    if tif not in VALID_TIF:
        raise typer.BadParameter(
            f"Time-in-force '{tif}' is invalid. Choose from: {', '.join(VALID_TIF)}."
        )
    return tif
