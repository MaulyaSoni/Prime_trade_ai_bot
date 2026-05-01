# 🤖 Binance Futures Testnet Trading Bot

A clean Python CLI application built to satisfy the **Application Task – Python Developer**. It places **MARKET**, **LIMIT**, and **STOP_LIMIT** orders on the Binance Futures Testnet (USDT-M) with structured logging, robust error handling, and a highly polished Typer CLI interface.

---

## 🎯 Task Requirements & Deliverables Achieved

This project fulfills all core requirements and tackles multiple **bonus** objectives:
- ✅ **Core Requirement 1 & 2:** Placed MARKET and LIMIT orders on both BUY and SELL sides.
- ✅ **Core Requirement 3:** Input efficiently validated via `typer` and custom `validators.py`.
- ✅ **Core Requirement 4:** Clean console output formatted with `rich` to show summary, response, and success/failure cleanly.
- ✅ **Core Requirement 5:** Structured architecture (`cli.py` separate from `bot/client.py`), and dedicated file/console logging.
- 🚀 **Advanced Tier 1:** Live Prices, Balances, and Open Orders directly from CLI.
- 🚀 **Advanced Tier 2:** TWAP execution algorithm added to slice single large orders across chunks.
- 🚀 **Advanced Tier 3:** Interactive TUI Menu for step-by-step order placement, plus a Trade Journal (`trade_journal.csv`) to automatically log trade details and PnL framing.
- 🚀 **Bonus 1:** Implemented a third order type: `STOP_LIMIT` (`STOP`).
- 🚀 **Bonus 2:** Enhanced CLI UX using Typer and Rich with colored tables, explicit validation hints, and help menus.
- 📦 **Deliverables included:** Full source code, this README, requirements list, and timestamped log files in the `/logs` directory demonstrating successful limits/markets.

---

## 📁 Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # HMAC-signed Binance REST client using requests
│   ├── orders.py          # Order placement logic + response formatting
│   ├── validators.py      # Input validation & business rules
│   └── logging_config.py  # File + console logging setup
├── cli.py                 # Typer CLI entry point
├── .env.example           # Credential template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🔑 Step 1 — Get Testnet API Keys

1. Open your browser and go to: **https://testnet.binancefuture.com**
2. Log in (using GitHub OAuth).
3. In the top-right corner, click your profile icon → **"API Key"**.
4. Click **"Generate Key"** and copy both immediately.

---

## ⚙️ Step 2 — Environment Setup

Ensure Python 3.10+ is installed.

```bash
# Clone the repository
git clone https://github.com/MaulyaSoni/Prime_trade_ai_bot.git
cd Prime_trade_ai_bot

# Set up virtual environment (or conda)
python -m venv venv
# On Windows
venv\Scripts\activate
# On Linux/Mac: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🔐 Step 3 — Configure Credentials

Copy the `.env.example` to `.env`:

```bash
cp .env.example .env
```

Open `.env` and paste your actual Testnet keys:
```env
BINANCE_API_KEY=your_actual_api_key_here
BINANCE_API_SECRET=your_actual_secret_key_here
```

---

## 🚀 Step 4 — Run the Bot (Examples)

### View Help
```powershell
python cli.py --help
```

### 1. MARKET order — Buy 0.01 ETH at market price
```powershell
python cli.py --symbol ETHUSDT --side BUY --type MARKET --quantity 0.01
```

### 2. LIMIT order — Sell 0.01 ETH with a price ceiling
```powershell
python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.01 --price 3500
```

### 3. STOP_LIMIT order — Buy ETH when price drops to stop, limit execution
```powershell
python cli.py --symbol ETHUSDT --side BUY --type STOP_LIMIT --quantity 0.01 --stop-price 3000 --price 3050
```
### 7. View Live Price & Auto Logs (Trade Journal) 
Every executed order, regardless of type, is inherently appended to the `trade_journal.csv` within the project. 

### 8. Use TWAP (Time-Weighted Average Price) algorithmic execution (Tier 2)
Splits your large order (e.g. 0.02 BTC) into 2 chunks of 0.01, placed 10 seconds apart.
```powershell
python cli.py twap --symbol BTCUSDT --side BUY --quantity 0.02 --chunks 2 --interval 10
```
---

## 📝 Logs

Logs are written automatically to `logs/trading_bot_YYYYMMDD_HHMMSS.log`.

- **Console** → `INFO` level (clean, human-readable).
- **File** → `DEBUG` level (full request params, raw API responses, payload errors).

---

## 🧩 Assumptions

1. **Testnet only** — base URL defaults to `https://testnet.binancefuture.com`. Do not use real funds.
2. **USDT-M perpetuals** — specifically targeting USDT-margined contracts (`BTCUSDT`, `ETHUSDT`).
3. **Trailing precision** — the bot passes quantities as floats. If the exchange throws `"LOT_SIZE"` or precision errors, adjust `--quantity` to match the specific pair's decimal limits (e.g., BTC needs 0.001 decimals).

---

## 🧪 Edge Cases & Error Handling Tested (All Working)

The application includes robust validation to prevent invalid requests from reaching the exchange, and handles API errors gracefully. All of the following edge cases have been successfully tested:

### 1. Invalid Order Types & Missing Prices
**Test:** Try placing a `LIMIT` order without providing a `--price`.
**Behavior:** The CLI immediately errors out and warns the user that the `LIMIT` order requires a `--price`.
```powershell
python cli.py --symbol ETHUSDT --side BUY --type LIMIT --quantity 0.01
```

### 2. Negative or Zero Quantity
**Test:** Try placing an order with `--quantity 0` or `--quantity -1.5`. 
**Behavior:** Local validation catches this invalid input before hitting the Binance API.
```powershell
python cli.py --symbol ETHUSDT --side BUY --type MARKET --quantity -0.01
```

### 3. Precision & LOT_SIZE Errors
**Test:** Provide a quantity that is too precise for the trading pair (e.g. BTCUSDT allows 3 decimal places).
**Behavior:** The Binance API returns an HTTP 400 `LOT_SIZE` or `PRICE_FILTER` error, which the bot safely catches and displays cleanly.
```powershell
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.0012345
```

### 4. Invalid Trading Symbol
**Test:** Buying a token pair that doesn't exist on the futures testnet.
**Behavior:** The API returns `Invalid symbol` (Code: -1121). The bot handles the error without crashing.
```powershell
python cli.py --symbol FAKE_COIN_USDT --side BUY --type MARKET --quantity 1
```

### 5. Stop-Limit Trigger Validation
**Test:** Provide a `--price` but forget the `--stop-price` for a `STOP_LIMIT` order.
**Behavior:** The CLI validator correctly requires *both* a limit price and a stop trigger.
```powershell
python cli.py --symbol ETHUSDT --side BUY --type STOP_LIMIT --quantity 0.01 --price 3500
```
