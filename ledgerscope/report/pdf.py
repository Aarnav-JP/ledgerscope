from __future__ import annotations

import base64
import io
import os
from datetime import datetime
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from ledgerscope.analytics.risk import (
    get_benchmark,
    get_dividends,
    get_drawdown,
    get_holdings,
    get_pnl_history,
    get_portfolio_summary,
    get_risk_summary,
)


def get_template_dir() -> Path:
    """Return the path to the HTML templates directory."""
    return Path(__file__).parent / "templates"


def generate_portfolio_chart(conn: duckdb.DuckDBPyConnection) -> str:
    """Generate a matplotlib chart of portfolio value over time.
    Returns the chart embedded as a base64 string.
    """
    # Sum market value by date across all holdings
    rows = conn.execute("""
        SELECT date, SUM(market_value) as total_value
        FROM pnl_history
        GROUP BY date
        ORDER BY date
    """).fetchall()

    if not rows:
        return ""

    dates = [row[0] for row in rows]
    values = [row[1] for row in rows]

    # Create figure
    plt.figure(figsize=(10, 4))
    plt.plot(dates, values, color="#00D4AA", linewidth=2)
    plt.fill_between(dates, values, color="#00D4AA", alpha=0.1) # type: ignore
    
    # Minimal styling
    plt.gca().spines["top"].set_visible(False)
    plt.gca().spines["right"].set_visible(False)
    plt.gca().spines["left"].set_color("#1E2430")
    plt.gca().spines["bottom"].set_color("#1E2430")
    plt.gca().tick_params(colors="#5A6478")
    plt.title("Portfolio Value Over Time", loc="left", color="#1E2430", fontweight="bold")
    plt.grid(axis="y", linestyle="--", alpha=0.3)
    
    # Save to base64
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close()
    
    # Convert base64 to string
    encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def generate_pdf_report(conn: duckdb.DuckDBPyConnection, output_path: str = "portfolio_report.pdf") -> str:
    """Generate a PDF portfolio review document."""
    
    summary = get_portfolio_summary(conn)
    holdings = get_holdings(conn)
    risk_metrics = get_risk_summary(conn)
    drawdowns = {d.symbol: d.max_drawdown for d in get_drawdown(conn)}
    benchmarks = get_benchmark(conn)
    dividends = get_dividends(conn)
    
    # Current prices & PnL for holdings table
    enrichments = {}
    for h in holdings:
        result = conn.execute("SELECT close FROM prices WHERE symbol = ? ORDER BY date DESC LIMIT 1", [h.symbol]).fetchone()
        current_price = result[0] if result else h.avg_cost
        market_value = h.shares * current_price
        unrealized = market_value - (h.shares * h.avg_cost)
        enrichments[h.symbol] = {
            "current_price": current_price,
            "market_value": market_value,
            "unrealized_pnl": unrealized
        }
        
    chart_base64 = generate_portfolio_chart(conn)

    # Context for template
    context = {
        "date": datetime.now().strftime("%B %d, %Y"),
        "summary": summary,
        "holdings": holdings,
        "enrichments": enrichments,
        "risk_metrics": risk_metrics,
        "drawdowns": drawdowns,
        "benchmarks": benchmarks,
        "dividends": dividends,
        "chart_base64": chart_base64,
    }

    env = Environment(loader=FileSystemLoader(str(get_template_dir())))
    # Custom formatters
    env.filters["currency"] = lambda value: f"${value:,.2f}" if value is not None else ""
    env.filters["percent"] = lambda value: f"{value * 100:,.2f}%" if value is not None else ""
    env.filters["abs"] = abs
    
    template = env.get_template("report.html")
    html_content = template.render(**context)

    # Render PDF
    html = HTML(string=html_content)
    html.write_pdf(output_path)
    
    return str(Path(output_path).absolute())

