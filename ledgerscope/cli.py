"""LedgerScope CLI — Typer-based command-line interface."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ledgerscope import __version__
from ledgerscope.db import get_db_path, init_db, reset_connection

app = typer.Typer(
    name="ledgerscope",
    help="SQL-native portfolio risk analytics engine.",
    no_args_is_help=True,
)
report_app = typer.Typer(help="Pre-built report shortcuts.")
db_app = typer.Typer(help="Database management commands.")
app.add_typer(report_app, name="report")
app.add_typer(db_app, name="db")

console = Console()


def _check_db_exists() -> None:
    """Check if the database exists and has data."""
    db_path = get_db_path()
    if not db_path.exists():
        console.print(
            "[red]Error:[/] No database found. "
            "Run [bold]ledgerscope ingest[/] first to import your trades."
        )
        raise typer.Exit(1)


def _format_output(rows: list, columns: list[str], fmt: str) -> None:
    """Format and print query results."""
    if fmt == "json":
        data = [dict(zip(columns, row)) for row in rows]
        console.print(json.dumps(data, indent=2, default=str))
    elif fmt == "csv":
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)
        console.print(output.getvalue())
    else:
        # Rich table format
        table = Table(show_header=True, header_style="bold teal")
        for col in columns:
            table.add_column(col)
        for row in rows:
            table.add_row(*[str(v) if v is not None else "" for v in row])
        console.print(table)


# ── Version ──────────────────────────────────────────────────────

def version_callback(value: bool) -> None:
    if value:
        console.print(f"ledgerscope {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", help="Show version.",
        callback=version_callback, is_eager=True,
    ),
) -> None:
    """LedgerScope — SQL-native portfolio risk analytics engine."""
    pass


# ── Ingest ───────────────────────────────────────────────────────

@app.command()
def ingest(
    broker: str = typer.Argument(
        help="Broker name: zerodha, robinhood, or ibkr"
    ),
    file: Path = typer.Argument(
        help="Path to the broker CSV export file"
    ),
    refresh: bool = typer.Option(
        False, "--refresh", help="Force re-fetch of all market prices"
    ),
) -> None:
    """Ingest a broker CSV export into the database."""
    from ledgerscope.ingest import get_parser
    from ledgerscope.enrich.prices import fetch_prices
    from ledgerscope.enrich.macro import fetch_macro

    if not file.exists():
        console.print(f"[red]Error:[/] File not found: {file}")
        raise typer.Exit(1)

    conn = init_db()

    # Parse and insert transactions
    console.print(f"[teal]Ingesting[/] {file.name} as [bold]{broker}[/] format...")
    parser = get_parser(broker)
    count = parser.to_transactions(file, conn)
    console.print(f"[green]✓[/] Imported {count} transactions")

    # Enrich with market data
    console.print("\n[teal]Fetching market data...[/]")
    fetch_prices(conn, refresh=refresh)

    console.print("\n[teal]Fetching macro data...[/]")
    fetch_macro(conn, refresh=refresh)

    console.print("\n[green]✓ Done![/] Run [bold]ledgerscope query 'SELECT * FROM risk_summary'[/] to see your risk metrics.")


# ── Query ────────────────────────────────────────────────────────

@app.command()
def query(
    sql: str = typer.Argument(help="SQL query to execute"),
    format: str = typer.Option(
        "table", "--format", "-f",
        help="Output format: table, csv, or json"
    ),
) -> None:
    """Execute a SQL query against the local database."""
    _check_db_exists()
    conn = init_db()

    try:
        result = conn.execute(sql)
        rows = result.fetchall()
        columns = [desc[0] for desc in result.description] if result.description else []
        _format_output(rows, columns, format)
    except Exception as e:
        console.print(f"[red]SQL Error:[/] {e}")
        raise typer.Exit(1)


# ── Report commands ──────────────────────────────────────────────

def _handle_export(export: Optional[str]) -> bool:
    if export and export.lower() == "pdf":
        from ledgerscope.report.pdf import generate_pdf_report
        console.print("[teal]Generating PDF report...[/]")
        _check_db_exists()
        conn = init_db()
        out_path = generate_pdf_report(conn)
        console.print(f"[green]✓[/] PDF report generated at [bold]{out_path}[/]")
        return True
    return False


def _run_report(view_name: str, title: str, fmt: str) -> None:
    """Helper to run a report query on a view."""
    _check_db_exists()
    conn = init_db()

    console.print(f"\n[bold teal]── {title} ──[/]\n")
    try:
        result = conn.execute(f"SELECT * FROM {view_name}")
        rows = result.fetchall()
        columns = [desc[0] for desc in result.description] if result.description else []

        if not rows:
            console.print("[dim]No data available. Import trades first.[/]")
            return

        _format_output(rows, columns, fmt)
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")


@report_app.command()
def summary(
    format: str = typer.Option("table", "--format", "-f"),
    export: Optional[str] = typer.Option(None, "--export"),
) -> None:
    """Portfolio overview: total value, cost, P&L, Sharpe."""
    if _handle_export(export): return
    _check_db_exists()
    conn = init_db()
    from ledgerscope.analytics.risk import get_portfolio_summary

    s = get_portfolio_summary(conn)
    console.print("\n[bold teal]── Portfolio Summary ──[/]\n")

    table = Table(show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    pnl_color = "green" if s.total_pnl >= 0 else "red"
    table.add_row("Holdings", str(s.num_holdings))
    table.add_row("Total Value", f"${s.total_value:,.2f}")
    table.add_row("Total Cost", f"${s.total_cost:,.2f}")
    table.add_row("Total P&L", f"[{pnl_color}]${s.total_pnl:,.2f} ({s.total_pnl_pct:+.2f}%)[/]")
    table.add_row("Portfolio Sharpe", str(s.portfolio_sharpe or "N/A"))
    console.print(table)


@report_app.command()
def risk(
    format: str = typer.Option("table", "--format", "-f"),
    export: Optional[str] = typer.Option(None, "--export"),
) -> None:
    """Full risk metrics for all holdings."""
    if _handle_export(export): return
    _run_report("risk_summary", "Risk Summary", format)


@report_app.command()
def pnl(
    format: str = typer.Option("table", "--format", "-f"),
    export: Optional[str] = typer.Option(None, "--export"),
) -> None:
    """Profit & Loss history by symbol."""
    if _handle_export(export): return
    _run_report("pnl_history", "P&L History", format)


@report_app.command()
def drawdown(
    format: str = typer.Option("table", "--format", "-f"),
    export: Optional[str] = typer.Option(None, "--export"),
) -> None:
    """Drawdown analysis for all holdings."""
    if _handle_export(export): return
    _run_report("drawdown", "Drawdown Analysis", format)


@report_app.command()
def benchmark(
    format: str = typer.Option("table", "--format", "-f"),
    export: Optional[str] = typer.Option(None, "--export"),
) -> None:
    """Portfolio vs benchmark (SPY) comparison."""
    if _handle_export(export): return
    _run_report("benchmark_comparison", "Benchmark Comparison", format)


@report_app.command()
def dividends(
    format: str = typer.Option("table", "--format", "-f"),
    export: Optional[str] = typer.Option(None, "--export"),
) -> None:
    """Dividend income history."""
    if _handle_export(export): return
    _run_report("dividend_income", "Dividend Income", format)


# ── DB commands ──────────────────────────────────────────────────

@db_app.command("path")
def db_path() -> None:
    """Print the database file path."""
    console.print(str(get_db_path()))


@db_app.command("shell")
def db_shell() -> None:
    """Open an interactive DuckDB SQL shell."""
    db_file = get_db_path()
    if not db_file.exists():
        console.print("[red]Error:[/] No database found. Run ingest first.")
        raise typer.Exit(1)
    console.print(f"[dim]Opening DuckDB shell for {db_file}...[/]")
    subprocess.run(["python", "-c", f"""
import duckdb
conn = duckdb.connect('{db_file}')
while True:
    try:
        sql = input('ledgerscope> ')
        if sql.strip().lower() in ('exit', 'quit', '.quit'):
            break
        if sql.strip():
            result = conn.execute(sql)
            print(result.fetchdf().to_string())
    except EOFError:
        break
    except Exception as e:
        print(f'Error: {{e}}')
"""])


@db_app.command("reset")
def db_reset() -> None:
    """Drop and recreate all tables and views."""
    confirm = typer.confirm(
        "This will DELETE all data. Are you sure?", abort=True
    )
    db_file = get_db_path()
    if db_file.exists():
        reset_connection()
        db_file.unlink()
        console.print("[green]✓[/] Database reset. Run [bold]ledgerscope ingest[/] to re-import.")
    else:
        console.print("[dim]No database found, nothing to reset.[/]")


# ── Enrich ───────────────────────────────────────────────────────

@app.command()
def enrich(
    refresh: bool = typer.Option(
        False, "--refresh", help="Force re-fetch of all data"
    ),
) -> None:
    """Re-fetch market price and macro data."""
    _check_db_exists()
    conn = init_db()

    from ledgerscope.enrich.prices import fetch_prices
    from ledgerscope.enrich.macro import fetch_macro

    console.print("[teal]Fetching market data...[/]")
    fetch_prices(conn, refresh=refresh)

    console.print("\n[teal]Fetching macro data...[/]")
    fetch_macro(conn, refresh=refresh)

    console.print("\n[green]✓ Done![/]")


# ── Schema ───────────────────────────────────────────────────────

@app.command()
def schema() -> None:
    """Print summary of all tables and views."""
    _check_db_exists()
    conn = init_db()

    console.print("\n[bold teal]── Tables ──[/]\n")
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' AND table_type = 'BASE TABLE'"
    ).fetchall()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Table")
    table.add_column("Rows", justify="right")

    for (tname,) in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {tname}").fetchone()[0]
        table.add_row(tname, str(count))
    console.print(table)

    console.print("\n[bold teal]── Views ──[/]\n")
    views = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' AND table_type = 'VIEW'"
    ).fetchall()

    for (vname,) in views:
        try:
            result = conn.execute(f"SELECT * FROM {vname} LIMIT 0")
            cols = [desc[0] for desc in result.description] if result.description else []
            console.print(f"  [bold]{vname}[/]: {', '.join(cols)}")
        except Exception:
            console.print(f"  [bold]{vname}[/]: [dim](error reading schema)[/]")


# ── Backtest ─────────────────────────────────────────────────────

@app.command()
def backtest(
    strategy: Path = typer.Option(
        ..., "--strategy", "-s", help="Path to SQL strategy file"
    ),
    symbol: str = typer.Option(
        ..., "--symbol", help="Ticker symbol to backtest"
    ),
    start_date: str = typer.Option(
        "2020-01-01", "--from", help="Start date (YYYY-MM-DD)"
    ),
    capital: float = typer.Option(
        10000.0, "--capital", help="Initial capital for the backtest"
    ),
) -> None:
    """Run a SQL-native backtest strategy."""
    _check_db_exists()

    if not strategy.exists():
        console.print(f"[red]Error:[/] Strategy file not found: {strategy}")
        raise typer.Exit(1)

    from ledgerscope.analytics.backtest import run_backtest

    conn = init_db()
    strategy_sql = strategy.read_text(encoding="utf-8")

    console.print(f"[teal]Running backtest[/] for [bold]{symbol}[/] from {start_date}...\n")

    try:
        result = run_backtest(
            conn=conn,
            strategy_sql=strategy_sql,
            initial_capital=capital,
            start_date=start_date,
        )

        # Display results
        table = Table(title="Backtest Results", show_header=False)
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        ret_color = "green" if result.total_return_pct >= 0 else "red"
        table.add_row("Symbol", result.symbol)
        table.add_row("Period", f"{result.start_date} → {result.end_date}")
        table.add_row("Initial Capital", f"${result.initial_capital:,.2f}")
        table.add_row("Final Value", f"[{ret_color}]${result.final_value:,.2f}[/]")
        table.add_row("Total Return", f"[{ret_color}]{result.total_return_pct:+.2f}%[/]")
        table.add_row("Annualized Return", f"{result.annualized_return_pct:+.2f}%")
        table.add_row("Sharpe Ratio", f"{result.sharpe_ratio:.4f}" if result.sharpe_ratio else "N/A")
        table.add_row("Max Drawdown", f"[red]{result.max_drawdown_pct:.2f}%[/]")
        table.add_row("Win Rate", f"{result.win_rate_pct:.1f}%")
        table.add_row("Total Trades", str(result.num_trades))

        console.print(table)
    except ValueError as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)


# ── TUI ──────────────────────────────────────────────────────────

@app.command()
def tui() -> None:
    """Launch the Textual terminal UI."""
    _check_db_exists()
    from ledgerscope.tui.app import main as tui_main
    tui_main()


# ── Serve ────────────────────────────────────────────────────────

@app.command()
def serve(
    port: int = typer.Option(8000, "--port", "-p", help="FastAPI server port"),
) -> None:
    """Start the FastAPI server and the Next.js web dashboard concurrently."""
    _check_db_exists()
    import uvicorn
    import subprocess
    import sys
    from pathlib import Path

    console.print(f"[teal]Starting LedgerScope API server[/] on http://localhost:{port}")
    
    web_dir = Path(__file__).parent.parent / "web"
    next_process = None
    if web_dir.exists():
        console.print("[teal]Starting Next.js dashboard[/] on http://localhost:3000")
        try:
            next_process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=str(web_dir),
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
        except Exception as e:
            console.print(f"[red]Warning:[/] Failed to start Next.js dashboard: {e}")

    console.print("[dim]Press Ctrl+C to stop both servers.[/]\n")
    
    try:
        uvicorn.run("ledgerscope.server:app", host="0.0.0.0", port=port, reload=False)
    finally:
        if next_process:
            console.print("\n[dim]Shutting down Next.js dashboard...[/]")
            next_process.terminate()
            next_process.wait()


if __name__ == "__main__":
    app()
