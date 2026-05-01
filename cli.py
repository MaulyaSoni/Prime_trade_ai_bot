"""
cli.py — command-line entry point for the Binance Futures Testnet trading bot.

Usage:
    python cli.py --help
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 95000
    python cli.py --symbol BTCUSDT --side BUY --type STOP_LIMIT \\
                  --quantity 0.001 --price 96000 --stop-price 95500
"""
import os
import sys
from typing import Optional

import requests
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from bot.client import BinanceClient
from bot.logging_config import setup_logging
from bot.orders import (
    format_error,
    format_order_response,
    place_limit_order,
    place_market_order,
    place_stop_limit_order,
)
from bot.validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
    validate_tif,
)

load_dotenv()
console = Console()
app = typer.Typer(
    name="trading-bot",
    help="🤖 Binance Futures Testnet Trading Bot — place MARKET, LIMIT, and STOP_LIMIT orders.",
    add_completion=False,
)


def _print_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float],
    stop_price: Optional[float],
    tif: str,
) -> None:
    rows = [
        f"[bold]Symbol[/bold]     : {symbol}",
        f"[bold]Side[/bold]       : {'[green]BUY[/green]' if side == 'BUY' else '[red]SELL[/red]'}",
        f"[bold]Order Type[/bold] : {order_type}",
        f"[bold]Quantity[/bold]   : {quantity}",
    ]
    if price is not None:
        rows.append(f"[bold]Limit Price[/bold]: {price}")
    if stop_price is not None:
        rows.append(f"[bold]Stop Price[/bold] : {stop_price}")
    if order_type != "MARKET":
        rows.append(f"[bold]Time in Force[/bold]: {tif}")

    console.print(
        Panel("\n".join(rows), title="📋 Order Request Summary", border_style="cyan")
    )


@app.command()
def place_order(
    symbol: str = typer.Option(
        ..., "--symbol", "-s",
        help="Trading pair symbol, e.g. BTCUSDT.",
    ),
    side: str = typer.Option(
        ..., "--side",
        help="Order side: BUY or SELL.",
    ),
    order_type: str = typer.Option(
        ..., "--type", "-t",
        help="Order type: MARKET | LIMIT | STOP_LIMIT.",
    ),
    quantity: float = typer.Option(
        ..., "--quantity", "-q",
        help="Order quantity (in base asset units).",
    ),
    price: Optional[float] = typer.Option(
        None, "--price", "-p",
        help="Limit price. Required for LIMIT and STOP_LIMIT.",
    ),
    stop_price: Optional[float] = typer.Option(
        None, "--stop-price",
        help="Stop trigger price. Required for STOP_LIMIT.",
    ),
    tif: str = typer.Option(
        "GTC", "--tif",
        help="Time-in-force: GTC (default) | IOC | FOK.",
    ),
) -> None:
    """Place a trading order on Binance Futures Testnet (USDT-M)."""

    logger = setup_logging()

    # ── Credentials ──────────────────────────────────────────────── #
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    if not api_key or not api_secret:
        console.print(
            "[bold red]❌ Missing credentials.[/bold red] "
            "Set BINANCE_API_KEY and BINANCE_API_SECRET in your .env file."
        )
        logger.error("Missing API credentials — check .env file.")
        raise typer.Exit(code=1)

    # ── Validation ────────────────────────────────────────────────── #
    try:
        symbol     = validate_symbol(symbol)
        side       = validate_side(side)
        order_type = validate_order_type(order_type)
        quantity   = validate_quantity(quantity)
        price      = validate_price(price, order_type)
        stop_price = validate_stop_price(stop_price, order_type)
        tif        = validate_tif(tif)
    except typer.BadParameter as exc:
        console.print(f"[bold red]❌ Validation error:[/bold red] {exc}")
        logger.error("Validation failed: %s", exc)
        raise typer.Exit(code=1)

    logger.info(
        "CLI input validated | symbol=%s side=%s type=%s qty=%s "
        "price=%s stop_price=%s tif=%s",
        symbol, side, order_type, quantity, price, stop_price, tif,
    )

    # ── Print summary ─────────────────────────────────────────────── #
    _print_summary(symbol, side, order_type, quantity, price, stop_price, tif)

    # ── Place order ───────────────────────────────────────────────── #
    client = BinanceClient(api_key, api_secret)

    try:
        if order_type == "MARKET":
            response = place_market_order(client, symbol, side, quantity)

        elif order_type == "LIMIT":
            response = place_limit_order(client, symbol, side, quantity, price, tif)  # type: ignore[arg-type]

        else:  # STOP_LIMIT
            response = place_stop_limit_order(
                client, symbol, side, quantity, price, stop_price, tif  # type: ignore[arg-type]
            )

    except requests.exceptions.HTTPError as exc:
        error_body: dict = {}
        if exc.response is not None:
            try:
                error_body = exc.response.json()
            except Exception:
                pass
        code = error_body.get("code", exc.response.status_code if exc.response else "N/A")
        msg  = error_body.get("msg", str(exc))
        console.print(format_error(code, msg))
        logger.error("API error | code=%s msg=%s", code, msg)
        raise typer.Exit(code=1)

    except requests.exceptions.ConnectionError:
        console.print(
            "[bold red]❌ Network error:[/bold red] "
            "Cannot reach Binance Testnet. Check your internet connection."
        )
        logger.error("Network connection failed.")
        raise typer.Exit(code=1)

    except requests.exceptions.Timeout:
        console.print("[bold red]❌ Timeout:[/bold red] The request took too long and was aborted.")
        logger.error("Request timed out.")
        raise typer.Exit(code=1)

    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]❌ Unexpected error:[/bold red] {exc}")
        logger.exception("Unexpected error: %s", exc)
        raise typer.Exit(code=1)

    # ── Success ───────────────────────────────────────────────────── #
    console.print(format_order_response(response))
    logger.info(
        "Order successful | orderId=%s status=%s executedQty=%s avgPrice=%s",
        response.get("orderId"),
        response.get("status"),
        response.get("executedQty"),
        response.get("avgPrice"),
    )


if __name__ == "__main__":
    app()
