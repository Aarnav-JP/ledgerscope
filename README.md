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

## 🚀 Quickstart

### Installation

```bash
# Clone and install
git clone https://github.com/Aarnav-JP/ledgerscope.git
cd ledgerscope
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
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
