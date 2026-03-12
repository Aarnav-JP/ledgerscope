<div align="center">

# 📊 LedgerScope

### SQL-Native Portfolio Risk Analytics Engine

[![CI/CD Pipeline](https://github.com/Aarnav-JP/ledgerscope/actions/workflows/ci.yml/badge.svg)](https://github.com/Aarnav-JP/ledgerscope/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![DuckDB](https://img.shields.io/badge/DuckDB-OLAP%20Engine-FFF000?logo=duckdb)](https://duckdb.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Import your brokerage trades. Get institutional-grade risk analytics. No cloud. No API keys. No data leaving your machine.**

[Quickstart](#-quickstart) · [Features](#-features) · [Architecture](#-architecture) · [CLI Reference](#-cli-reference) · [Contributing](#-contributing)

</div>

---

## 🧐 What is LedgerScope?

LedgerScope is an **open-source, privacy-first portfolio analytics tool** that turns your raw brokerage CSV exports into a professional-grade risk analytics dashboard — all running locally on your laptop.

You export your trades from Zerodha, Robinhood, or Interactive Brokers, run a single CLI command, and LedgerScope:

1. **Normalizes** the data into a unified schema using broker-specific parsers
2. **Enriches** it with live market prices (Yahoo Finance) and macroeconomic indicators (FRED API)
3. **Stores** everything in a local [DuckDB](https://duckdb.org/) OLAP database for sub-second analytics
4. **Computes** Sharpe Ratios, Maximum Drawdown, Beta, Alpha, and P&L using **pure SQL window functions**
5. **Presents** results via a CLI, a Textual terminal UI, a Next.js web dashboard, or a PDF report

> **Think of it as a Bloomberg Terminal for your personal portfolio — but open-source, offline, and free.**

---

## � New to Coding? Start Here!

**No programming experience? No problem!** Follow these simple steps to analyze your investment portfolio like a pro.

### 📋 What You'll Need
- A computer (Windows, Mac, or Linux)
- Your brokerage account export (CSV file from Zerodha/Robinhood/Interactive Brokers)
- 10 minutes of your time

### 🎯 Step-by-Step Guide for Beginners

#### **Step 1: Install Python** (One-time setup)
<details>
<summary>📱 <b>Mac Users</b> - Click to expand</summary>

1. Open **Terminal** (press `Cmd + Space`, type "Terminal", press Enter)
2. Copy and paste this command:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
3. After it finishes, run:
   ```bash
   brew install python@3.11
   ```
</details>

<details>
<summary>🪟 <b>Windows Users</b> - Click to expand</summary>

1. Download Python from [python.org/downloads](https://www.python.org/downloads/)
2. Run the installer
3. ✅ **Important**: Check "Add Python to PATH" during installation
4. Click "Install Now"
</details>

<details>
<summary>🐧 <b>Linux Users</b> - Click to expand</summary>

```bash
sudo apt update
sudo apt install python3.11 python3-pip python3-venv
```
</details>

#### **Step 2: Download LedgerScope** (One-time setup)

1. **Option A: Simple Download (No Git needed)**
   - Go to [github.com/Aarnav-JP/ledgerscope](https://github.com/Aarnav-JP/ledgerscope)
   - Click the green **"Code"** button → **"Download ZIP"**
   - Extract the ZIP file to your Desktop

2. **Option B: Using Git (if you have it)**
   ```bash
   git clone https://github.com/Aarnav-JP/ledgerscope.git
   cd ledgerscope
   ```

#### **Step 3: Install LedgerScope** (One-time setup)

Open Terminal/Command Prompt in the ledgerscope folder and run:

```bash
# Create a virtual environment (keeps things organized)
python -m venv .venv

# Activate it
# For Mac/Linux:
source .venv/bin/activate
# For Windows:
.venv\Scripts\activate

# Install LedgerScope
pip install -e .

# Run the fix script (Mac/Linux users only, due to a known bug)
./fix_entrypoint.sh
```

✅ **You're all set!** You only need to do this once.

#### **Step 4: Import Your Trades** (Every time you want to analyze)

1. **Export your trades from your broker:**
   - **Zerodha**: Console → Reports → Tradebook → Download CSV
   - **Robinhood**: Account → Menu → Statements & History → Download
   - **Interactive Brokers**: Reports → Trade Confirmation → Export CSV

2. **Import into LedgerScope:**
   ```bash
   # Activate virtual environment first (if not already active)
   source .venv/bin/activate   # Mac/Linux
   .venv\Scripts\activate      # Windows

   # Import your file (replace with your actual file path)
   ledgerscope ingest zerodha ~/Downloads/tradebook.csv
   # OR
   ledgerscope ingest robinhood ~/Downloads/account_activity.csv
   # OR
   ledgerscope ingest ibkr ~/Downloads/trades.csv
   ```

   **What happens now?**
   - ⚡ LedgerScope reads your trades
   - 📊 Downloads current stock prices (using Yahoo Finance)
   - 💾 Saves everything in a local database (no cloud, 100% private!)
   - ⏱️ Takes ~30-60 seconds

#### **Step 5: View Your Analytics** (Choose your favorite!)

**🌐 Option 1: Beautiful Web Dashboard (Recommended)**
```bash
ledgerscope serve
```
Then open your browser and go to: **http://localhost:3000**

You'll see:
- 📈 Interactive charts of your portfolio performance
- 💰 Profit/Loss breakdown by stock
- 📊 Risk metrics (Sharpe Ratio, Max Drawdown, Volatility)
- 🎯 Portfolio comparison vs. S&P 500
- ⚙️ Settings page for configuration

**💻 Option 2: Terminal Interface (For the minimalists)**
```bash
ledgerscope tui
```
Navigate with arrow keys, press `q` to quit.

**📄 Option 3: Quick Text Report**
```bash
ledgerscope report summary
```
Prints a quick overview in your terminal.

**📋 Option 4: Generate PDF Report**
```bash
ledgerscope report risk --export pdf
```
Creates a professional PDF report in your current folder.

### 🎓 Pro Tips

- **First time using a terminal?** No worries! Just copy-paste the commands exactly as shown.
- **Data stays private**: Everything runs on YOUR computer. No data is sent to any server.
- **Re-import anytime**: Download new trades and run the import command again. It won't create duplicates!
- **Try the examples**: After importing, try `ledgerscope query "SELECT * FROM holdings"` to see your current positions.

### 🆘 Need Help?

- **Error installing?** Make sure Python version is 3.11 or higher: `python --version`
- **Command not found?** Make sure you activated the virtual environment (Step 3)
- **Import failed?** Check if your CSV file is from the correct broker format
- **Something else?** [Open an issue](https://github.com/Aarnav-JP/ledgerscope/issues) with the error message

### 🎉 Success Looks Like This

After running `ledgerscope serve` and opening http://localhost:3000, you should see:

```
✓ Imported 127 transactions
✓ Fetched prices for 15 symbols
✓ Fetched macro data

Starting LedgerScope API server on http://localhost:8000
Starting Next.js dashboard on http://localhost:3000
Press Ctrl+C to stop both servers.
```

**Congratulations!** 🎊 You're now using professional portfolio analytics software that hedge funds pay thousands for!

---

## 🚀 Quickstart (For Developers)

### Installation

```bash
# Clone and install
git clone https://github.com/Aarnav-JP/ledgerscope.git
cd ledgerscope
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Initialize configuration (optional - auto-created on first run)
ledgerscope config-init
```

### Import Your Trades (30 Seconds)

```bash
# Export your tradebook CSV from your broker, then:
ledgerscope ingest zerodha   ~/Downloads/tradebook.csv
ledgerscope ingest robinhood ~/Downloads/account_activity.csv
ledgerscope ingest ibkr      ~/Downloads/trades.csv
```

LedgerScope automatically downloads historical prices, fetches macro data (10Y Treasury, CPI, S&P 500, NIFTY 50), and caches everything locally as Parquet files.

### Explore Your Portfolio

```bash
# Run SQL directly against your portfolio
ledgerscope query "SELECT * FROM risk_summary"

# Launch interfaces
ledgerscope tui       # Terminal UI with live metrics
ledgerscope serve     # Web dashboard at localhost:3000

# Generate a PDF report
ledgerscope report risk --export pdf
```

---

## ✨ Features

### 🆕 NEW: Enterprise-Grade Features (v0.2.0)
- **🔧 Configuration Management**: TOML-based config with environment variable overrides
- **📝 Structured Logging**: File and console logging with Rich formatting
- **💱 Multi-Currency Support**: Automatic exchange rate fetching and conversion to base currency
- **🔄 Robust Error Handling**: Automatic retries with exponential backoff for API calls


### 📥 Multi-Broker Data Ingestion
- **Zerodha**, **Robinhood**, and **Interactive Brokers** parsers with automatic column detection and aliasing
- Abstract `BrokerParser` base class — adding a new broker takes ~50 lines of Python
- **Idempotent imports**: SHA-256 deterministic transaction IDs prevent duplicate data on re-import

### 📈 SQL-Native Analytics (No Python Math Libraries)
All risk metrics are computed as **composable DuckDB SQL views**, not Python code. This means:
- Sub-second query performance on multi-year portfolios
- Full transparency — every calculation is a readable SQL statement
- Easy to extend — write a new `CREATE VIEW` and it's instantly available everywhere

| View | What It Computes |
|---|---|
| `holdings` | Current positions (cumulative BUY − SELL) with average cost basis |
| `risk_summary` | Sharpe Ratio, Annualized Volatility, Worst Single Day, Annual Return |
| `pnl_history` | Daily unrealized and realized P&L per symbol over time |
| `drawdown` | Maximum peak-to-trough drawdown per symbol with date |
| `benchmark_comparison` | Correlation, Beta, and Alpha vs. S&P 500 (SPY) |
| `dividend_income` | Annual and cumulative dividend income with yield-on-cost |

### 🧪 SQL-Native Backtesting Engine
Write trading strategies as plain SQL queries that return `(date, symbol, signal)` rows:
```sql
-- Example: Simple Moving Average Crossover
SELECT date, symbol,
    CASE
        WHEN avg_20 > avg_50 THEN 'BUY'
        WHEN avg_20 < avg_50 THEN 'SELL'
        ELSE 'HOLD'
    END AS signal
FROM (
    SELECT date, symbol,
        AVG(close) OVER (ORDER BY date ROWS 19 PRECEDING) AS avg_20,
        AVG(close) OVER (ORDER BY date ROWS 49 PRECEDING) AS avg_50
    FROM prices WHERE symbol = 'RELIANCE'
)
```
```bash
ledgerscope backtest --strategy sma_crossover.sql --symbol RELIANCE --capital 100000
```
Returns: Total Return, Annualized Return, Sharpe Ratio, Max Drawdown, Win Rate, and a full equity curve.

### 🖥️ Four Ways to Interact

| Interface | Command | Description |
|---|---|---|
| **CLI** | `ledgerscope query / report` | Pipe-friendly, scriptable output (table, CSV, JSON) |
| **Terminal UI** | `ledgerscope tui` | Textual-based dashboard with Overview, Risk, and SQL Console tabs |
| **Web Dashboard** | `ledgerscope serve` | Next.js app with Recharts visualizations at `localhost:3000` |
| **PDF Report** | `ledgerscope report risk --export pdf` | WeasyPrint-generated portfolio review document |

### 🔐 Privacy-First Design
- **Zero cloud dependencies** — everything runs locally
- DuckDB database stored at `~/.ledgerscope/ledgerscope.duckdb`
- Market data cached as Parquet files, no re-download needed
- `.gitignore` configured to never commit real portfolio data

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                              │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │   CLI    │  │  Textual TUI │  │  Next.js Web │  │  PDF Report│  │
│  │ (Typer)  │  │  (3 Tabs)    │  │  (5 Pages)   │  │ (WeasyPrint│  │
│  └────┬─────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  │
│       │               │                 │                 │         │
│  ┌────▼─────────────────────────────────▼─────────────────▼──────┐  │
│  │              FastAPI REST API (9 Endpoints)                   │  │
│  │  /holdings  /risk  /pnl  /drawdown  /benchmark  /backtest    │  │
│  └──────────────────────────┬────────────────────────────────────┘  │
│                             │                                       │
│  ┌──────────────────────────▼────────────────────────────────────┐  │
│  │           SQL ANALYTICS LAYER (Pure DuckDB Views)             │  │
│  │  holdings │ risk_summary │ pnl_history │ drawdown │ benchmark │  │
│  └──────────────────────────┬────────────────────────────────────┘  │
│                             │                                       │
│  ┌──────────────────────────▼────────────────────────────────────┐  │
│  │                     DuckDB (OLAP Engine)                       │  │
│  │              transactions │ prices │ macro_data                │  │
│  └──────────────────────────┬────────────────────────────────────┘  │
│                             │                                       │
│  ┌──────────────────────────▼────────────────────────────────────┐  │
│  │                    DATA INGESTION LAYER                        │  │
│  │  ┌──────────┐  ┌────────────┐  ┌───────┐  ┌───────────────┐  │  │
│  │  │ Zerodha  │  │ Robinhood  │  │ IBKR  │  │ + Your Broker │  │  │
│  │  └──────────┘  └────────────┘  └───────┘  └───────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                             │                                       │
│  ┌──────────────────────────▼────────────────────────────────────┐  │
│  │                   ENRICHMENT LAYER                             │  │
│  │        Yahoo Finance (OHLCV)  │  FRED API (Macro Data)        │  │
│  │              Parquet Cache (~/.ledgerscope/cache/)             │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📖 CLI Reference

| Command | Description |
|---|---|
| `ledgerscope ingest <broker> <file>` | Import a broker CSV export (zerodha, robinhood, ibkr) |
| `ledgerscope query "<sql>"` | Run raw SQL against the local database |
| `ledgerscope report summary` | Portfolio overview: value, cost, P&L, Sharpe |
| `ledgerscope report risk` | Full risk metrics per holding |
| `ledgerscope report pnl` | Profit & Loss history by symbol |
| `ledgerscope report drawdown` | Maximum drawdown analysis |
| `ledgerscope report benchmark` | Portfolio vs. S&P 500 comparison |
| `ledgerscope report dividends` | Dividend income and yield-on-cost |
| `ledgerscope backtest -s <file> --symbol <SYM>` | Run a SQL-native backtest strategy |
| `ledgerscope enrich [--refresh]` | Re-fetch market prices and macro data |
| `ledgerscope schema` | Print all tables and views in the database |
| `ledgerscope tui` | Launch the Textual terminal dashboard |
| `ledgerscope serve` | Start FastAPI (port 8000) + Next.js (port 3000) |
| `ledgerscope db path` | Print the database file location |
| `ledgerscope db shell` | Open an interactive DuckDB SQL prompt |
| `ledgerscope db reset` | Drop and recreate all tables (destructive) |

All `report` commands support `--format table|csv|json` and `--export pdf`.

---

## 🗂️ Project Structure

```
ledgerscope/
├── ledgerscope/                # Python package
│   ├── cli.py                  # Typer CLI with 10+ commands
│   ├── server.py               # FastAPI REST API (9 endpoints)
│   ├── db.py                   # DuckDB connection manager + migrations
│   ├── ingest/                 # Broker CSV parsers
│   │   ├── base.py             # Abstract BrokerParser class
│   │   ├── zerodha.py          # Zerodha parser
│   │   ├── robinhood.py        # Robinhood parser
│   │   └── ibkr.py             # Interactive Brokers parser
│   ├── enrich/                 # Market data enrichment
│   │   ├── prices.py           # yfinance OHLCV downloader
│   │   ├── macro.py            # FRED API + yfinance macro data
│   │   └── cache.py            # Parquet file caching
│   ├── analytics/              # SQL analytics layer
│   │   ├── views.sql           # 6 composable SQL views
│   │   ├── risk.py             # Typed Python wrappers
│   │   └── backtest.py         # SQL-native backtesting engine
│   ├── tui/                    # Textual terminal UI
│   │   ├── app.py              # 3-tab TUI application
│   │   └── widgets.py          # Custom metric card widgets
│   ├── report/                 # PDF report generation
│   │   ├── pdf.py              # WeasyPrint + Jinja2 + matplotlib
│   │   └── templates/          # HTML report template
│   └── migrations/             # SQL schema migrations
│       └── 001_initial.sql     # Core tables: transactions, prices, macro_data
├── web/                        # Next.js web dashboard
│   ├── app/                    # App Router pages
│   │   ├── page.tsx            # Overview with portfolio value chart
│   │   ├── risk/page.tsx       # Risk metrics table
│   │   ├── holdings/page.tsx   # Current positions
│   │   ├── backtest/page.tsx   # Strategy backtester UI
│   │   └── report/page.tsx     # PDF report download
│   ├── components/             # Reusable UI components
│   └── lib/api.ts              # FastAPI client
├── tests/                      # 65 tests across all layers
├── .github/workflows/ci.yml    # CI/CD: test → Docker → PyPI
├── Dockerfile                  # Multi-stage production build
└── pyproject.toml              # Package configuration
```

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Database** | DuckDB | Columnar OLAP engine, sub-second analytics, zero configuration |
| **CLI Framework** | Typer + Rich | Beautiful terminal output with tables, progress bars, colors |
| **Terminal UI** | Textual | Modern TUI framework with tabs, data tables, live refresh |
| **Web Frontend** | Next.js 14 + Recharts | React-based dashboard with interactive charts |
| **API Server** | FastAPI | Async Python web framework with automatic OpenAPI docs |
| **PDF Generation** | WeasyPrint + Jinja2 | HTML-to-PDF rendering with matplotlib charts |
| **Market Data** | yfinance | Free OHLCV data for any exchange-listed security |
| **Macro Data** | FRED API | 10Y Treasury, CPI, Unemployment, S&P 500 — no API key needed |
| **Caching** | Apache Parquet | Columnar file format for fast local data access |
| **Testing** | Pytest | 65 tests covering parsers, analytics, API, and end-to-end flows |
| **CI/CD** | GitHub Actions | Automated testing, Docker image build, PyPI publishing |

---

## 🤝 Contributing

We welcome contributions! Whether it's a new broker parser, a new SQL view, or a bug fix — every PR helps.

```bash
# Setup development environment
git clone https://github.com/Aarnav-JP/ledgerscope.git
cd ledgerscope
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run the test suite
pytest

# Add a new broker: create ledgerscope/ingest/your_broker.py
# It only takes ~50 lines — see CONTRIBUTING.md for the template.
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

<div align="center">
  <br />
  <strong>Built with DuckDB, Python, Next.js, and SQL window functions.</strong>
  <br />
  <sub>No Bloomberg Terminal required. 🦆</sub>
</div>
