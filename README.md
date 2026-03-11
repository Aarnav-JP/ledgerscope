<div align="center">
  <h1>LedgerScope</h1>
  <p>SQL-Native Portfolio Risk Analytics Engine</p>
  
  [![CI](https://github.com/aarnavjp/ledgerscope/actions/workflows/ci.yml/badge.svg)](https://github.com/aarnavjp/ledgerscope/actions/workflows/ci.yml)
  [![PyPI](https://img.shields.io/pypi/v/ledgerscope)](https://pypi.org/project/ledgerscope/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
</div>

<br />

**LedgerScope** is an open-source CLI tool and web dashboard for quantitative portfolio analytics. It ingests brokerage trade exports, enriches them with free live market and macroeconomic data from Yahoo Finance and the FRED API, stores everything locally in a lightning-fast [DuckDB](https://duckdb.org/) database, and calculates institutional-grade risk metrics including Sharpe Ratio, Maximum Drawdown, and Beta using pure SQL window functions.

**No cloud accounts. No $24k/year Bloomberg Terminal. No data leaving your machine.**

![LedgerScope Demo](demo.gif) *(Imagine an asciinema demo here showing fast CLI execution)*

## 🚀 Quickstart (5 Minutes)

1. **Install LedgerScope via pip:**
   ```bash
   pip install ledgerscope
   ```

2. **Download your trades:** Export your closed orders/tradebook from your broker (e.g. Zerodha, Robinhood, IBKR) as a CSV file.

3. **Ingest the data:**
   ```bash
   ledgerscope ingest zerodha trades.csv
   ```
   *LedgerScope normalizes the trades, downloads the necessary historical prices locally, and applies migrations.*

4. **Query your portfolio:**
   ```bash
   ledgerscope query 'SELECT * FROM risk_summary'
   ```
   Or use the built-in UI:
   ```bash
   # Terminal UI
   ledgerscope tui
   
   # Web Dashboard
   ledgerscope serve
   ```

## 📈 Supported Brokers

LedgerScope uses an abstract architecture for parsing trades. Currently supported brokers:
- `zerodha`: Parses `tradebook.csv` exports.
- `robinhood`: Parses `account_activity.csv`.
- `ibkr`: Parses Interactive Brokers' Flex Query CSV format.

Want your broker supported? It takes ~50 lines of Python. See [CONTRIBUTING.md](CONTRIBUTING.md).

## 🛠️ Features

* **Embedded DuckDB OLAP Engine:** Run sub-second queries across multi-year portfolios.
* **SQL-Native Backtesting:** Express trading strategies purely via SQL window functions (`ledgerscope backtest`).
* **Multi-Broker Normalization:** Bring in datasets from multiple brokers effortlessly.
* **Automatic Data Enrichment:** Daily prices automatically pulled and cached locally as Parquet files.
* **Textual CLI Dashboard:** Monitor risk, positions, and run SQL directly from your terminal (`ledgerscope tui`).
* **Next.js Web Dashboard:** Beautiful web overview locally without API keys (`ledgerscope serve`).
* **PDF Report Generator:** Export a high-quality PDF to review performance.

## 📖 CLI Reference

* `ledgerscope ingest <broker> <file.csv>` – Ingest trades to local DB
* `ledgerscope query "<sql>"` – Run SQL against local analytics views
* `ledgerscope tui` – Launch the Terminal UI
* `ledgerscope serve` – Launch the Web Dashboard server
* `ledgerscope backtest --strategy script.sql --symbol AAPL` – Run backtesting engine
* `ledgerscope report summary` – View high-level P&L and metrics
* `ledgerscope report risk --export pdf` – Calculate Sharpe ratios & generate a PDF Report
* `ledgerscope db shell` – Open an interactive DuckDB sql prompt
* `ledgerscope enrich --refresh` – Force-refresh market data using YFinance & FRED API

## 🤝 Contributing

We welcome pull requests! See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add a new broker parser or new SQL views.

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
