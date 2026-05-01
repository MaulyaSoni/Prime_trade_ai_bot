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
import time
import csv
from datetime import datetime
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
    help="Binance Futures Testnet Trading Bot — place MARKET, LIMIT, and STOP_LIMIT orders.",
    add_completion=False,
)

def _log_trade_journal(res: dict) -> None:
    """Tier 3: Trade journal — logs every executed order to a local CSV with PnL tracking hints."""
    try:
        file_exists = os.path.isfile("trade_journal.csv")
        with open("trade_journal.csv", mode="a", newline="") as csvfile:
            fieldnames = ["time", "orderId", "symbol", "side", "type", "origQty", "price", "status"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "orderId": res.get("orderId", ""),
                "symbol": res.get("symbol", ""),
                "side": res.get("side", ""),
                "type": res.get("type", ""),
                "origQty": res.get("origQty", ""),
                "price": res.get("price", ""),
                "status": res.get("status", ""),
            })
    except Exception as e:
        console.print(f"[yellow]Could not log to trade journal: {e}[/yellow]")



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
        Panel("\n".join(rows), title="Order Request Summary", border_style="cyan")
    )


@app.command("balance")
def get_balance() -> None:
    """Fetch and display USDT and BTC balances from Binance Testnet."""
    logger = setup_logging()
    load_dotenv()
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    if not api_key or not api_secret:
        console.print("[bold red]ERROR: Missing credentials.[/bold red]")
        raise typer.Exit(code=1)

    client = BinanceClient(api_key, api_secret)
    try:
        data = client.get_signed("/api/v3/account")
        console.print(f"\n[bold cyan]Account Balances (Testnet)[/bold cyan]")
        console.print("──────────────────────────────────────────────────")
        for asset in data.get("balances", []):
            if asset["asset"] in ["USDT", "BTC", "ETH"]:
                console.print(f"[bold]{asset['asset']:>6}[/bold]: {float(asset['free']):.4f} (Locked: {float(asset['locked']):.4f})")
    except Exception as e:
        console.print(f"[bold red]Failed to fetch balance: {e}[/bold red]")


@app.command("price")
def get_price(symbol: str = typer.Argument(..., help="Symbol (e.g. BTCUSDT)")) -> None:
    """Get the current market price for a symbol."""
    logger = setup_logging()
    client = BinanceClient("", "") # Public endpoint, no keys needed
    try:
        data = client.get_public("/api/v3/ticker/price", {"symbol": symbol.upper()})
        price = float(data['price'])
        console.print(f"\n📈 [bold yellow]{symbol.upper()}[/bold yellow] Latest Price: [bold green]${price:,.2f}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Failed to fetch price: {e}[/bold red]")


@app.command("open-orders")
def get_open_orders(
    symbol: Optional[str] = typer.Option(None, "--symbol", "-s", help="Filter by symbol")
) -> None:
    """List all open orders on your testnet account."""
    logger = setup_logging()
    load_dotenv()
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    client = BinanceClient(api_key, api_secret)
    try:
        params = {"symbol": symbol.upper()} if symbol else {}
        data = client.get_signed("/api/v3/openOrders", params)
        console.print(f"\n[bold cyan]Open Orders (Testnet)[/bold cyan]")
        console.print("──────────────────────────────────────────────────")
        if not data:
            console.print("[yellow]No open orders found.[/yellow]")
            return
        for idx, order in enumerate(data, 1):
            console.print(
                f"{idx}. [bold]{order['symbol']}[/bold] | {order['side']} | {order['type']} | "
                f"Qty: {order['origQty']} | Price: {order.get('price', 'MARKET')} | "
                f"Status: {order['status']} | ID: {order['orderId']}"
            )
    except Exception as e:
        console.print(f"[bold red]Failed to fetch open orders: {e}[/bold red]")


@app.command("order")
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
    load_dotenv()
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    if not api_key or not api_secret:
        console.print(
            "[bold red]ERROR: Missing credentials.[/bold red] "
            "Set BINANCE_API_KEY and BINANCE_API_SECRET in your .env file."
        )
        logger.error("Missing API credentials - check .env file.")
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
        console.print(f"[bold red]Validation error:[/bold red] {exc}")
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

        _log_trade_journal(response)

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
            "[bold red]Network error:[/bold red] "
            "Cannot reach Binance Testnet. Check your internet connection."
        )
        logger.error("Network connection failed.")
        raise typer.Exit(code=1)

    except requests.exceptions.Timeout:
        console.print("[bold red]Timeout:[/bold red] The request took too long and was aborted.")
        logger.error("Request timed out.")
        raise typer.Exit(code=1)

    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]Unexpected error:[/bold red] {exc}")
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


@app.command("twap")
def twap_order(
    symbol: str = typer.Option(..., "--symbol", "-s", help="Symbol (e.g. BTCUSDT)"),
    side: str = typer.Option(..., "--side", help="BUY or SELL"),
    total_qty: float = typer.Option(..., "--quantity", "-q", help="Total quantity to trade"),
    chunks: int = typer.Option(..., "--chunks", "-c", help="Number of chunks to split the order into"),
    interval_sec: int = typer.Option(..., "--interval", "-i", help="Time between chunks in seconds"),
) -> None:
    """TWAP execution — splits a large MARKET order into equal chunks over a time window."""
    logger = setup_logging()
    load_dotenv()
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    if not api_key or not api_secret:
        console.print("[bold red]ERROR: Missing credentials.[/bold red]")
        raise typer.Exit(code=1)

    chunk_qty = total_qty / chunks
    console.print(f"[bold magenta]Starting TWAP Execution...[/bold magenta]")
    console.print(f"Total: {total_qty} {symbol} • Chunks: {chunks} • Qty per chunk: {chunk_qty} • Interval: {interval_sec}s\n")

    client = BinanceClient(api_key, api_secret)
    
    for i in range(1, chunks + 1):
        console.print(f"[cyan]Executing chunk {i}/{chunks}...[/cyan]")
        try:
            from bot.orders import place_market_order, format_order_response
            res = place_market_order(client, symbol, side, chunk_qty)
            _log_trade_journal(res)
            console.print(format_order_response(res))
            if i < chunks:
                time.sleep(interval_sec)
        except Exception as str_exc:
            console.print(f"[bold red]Chunk {i} failed: {str_exc}[/bold red]")
            break
    console.print("[bold green]TWAP Execution Complete.[/bold green]")


@app.command("interactive")
def interactive_mode():
    """Tier 3: Interactive menu mode with step-by-step prompts."""
    console.print("[bold cyan]=== Interactive Trading Mode ===[/bold cyan]")
    
    symbol = typer.prompt("Enter Symbol", default="BTCUSDT").upper()
    side = typer.prompt("Side (BUY/SELL)", default="BUY").upper()
    order_type = typer.prompt("Order Type (MARKET/LIMIT/STOP_LIMIT)", default="MARKET").upper()
    quantity = typer.prompt("Quantity", type=float)
    
    price = None
    if order_type in ["LIMIT", "STOP_LIMIT"]:
        price = typer.prompt("Limit Price", type=float)
        
    stop_price = None
    if order_type == "STOP_LIMIT":
        stop_price = typer.prompt("Stop Price", type=float)
        
    console.print(f"\n[bold]Ready to place {order_type} {side} order for {quantity} {symbol}.[/bold]")
    confirm = typer.confirm("Execute this trade?")
    
    if confirm:
        place_order(symbol=symbol, side=side, order_type=order_type, quantity=quantity, price=price, stop_price=stop_price, tif="GTC")
    else:
        console.print("[yellow]Trade cancelled.[/yellow]")

if __name__ == "__main__":
    app()