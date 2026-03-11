from __future__ import annotations

import duckdb
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import DataTable, Header, Footer, TabbedContent, TabPane, Input
from textual.binding import Binding

from ledgerscope.db import get_connection
from ledgerscope.analytics.risk import (
    get_portfolio_summary,
    get_risk_summary,
    get_holdings,
    get_drawdown
)
from ledgerscope.tui.widgets import MetricCard, format_currency, format_percentage, get_color_class


class OverviewScreen(Container):
    """The Overview screen showing portfolio summary and top holdings."""

    def compose(self) -> ComposeResult:
        with Horizontal(id="metrics-container"):
            yield MetricCard("Total Value", "$0.00", id="metric-value")
            yield MetricCard("Total P&L", "$0.00", id="metric-pnl")
            yield MetricCard("P&L %", "0.00%", id="metric-pnl-pct")
            yield MetricCard("Portfolio Sharpe", "0.00", id="metric-sharpe")
        
        yield DataTable(id="top-holdings-table")

    def on_mount(self) -> None:
        table = self.query_one("#top-holdings-table", DataTable)
        table.add_columns("Symbol", "Shares", "Avg Cost", "Last Trade Date")
        self.refresh_data()
        self.set_interval(60, self.refresh_data)

    def refresh_data(self) -> None:
        try:
            conn = get_connection()
            summary = get_portfolio_summary(conn)
            holdings = get_holdings(conn)

            # Update metrics
            self.query_one("#metric-value", MetricCard).update_values(format_currency(summary.total_value))
            
            pnl_color = get_color_class(summary.total_pnl)
            pnl_str = f"[{pnl_color}]{format_currency(summary.total_pnl)}[/{pnl_color}]"
            self.query_one("#metric-pnl", MetricCard).update_values(pnl_str)

            pnl_pct_str = f"[{pnl_color}]{format_percentage(summary.total_pnl_pct)}[/{pnl_color}]"
            self.query_one("#metric-pnl-pct", MetricCard).update_values(pnl_pct_str)

            sharpe_str = f"{summary.portfolio_sharpe:.4f}" if summary.portfolio_sharpe is not None else "N/A"
            if summary.portfolio_sharpe is not None:
                s_color = get_color_class(summary.portfolio_sharpe)
                sharpe_str = f"[{s_color}]{sharpe_str}[/{s_color}]"
            self.query_one("#metric-sharpe", MetricCard).update_values(sharpe_str)

            # Update table
            # Top 5 by value
            holdings_with_value = []
            for h in holdings:
                result = conn.execute("SELECT close FROM prices WHERE symbol = ? ORDER BY date DESC LIMIT 1", [h.symbol]).fetchone()
                price = result[0] if result else h.avg_cost
                val = h.shares * price
                holdings_with_value.append((val, h))
            
            holdings_with_value.sort(key=lambda x: x[0], reverse=True)
            top_5 = holdings_with_value[:5]

            table = self.query_one("#top-holdings-table", DataTable)
            table.clear()
            for _, h in top_5:
                table.add_row(h.symbol, f"{h.shares:.4f}", format_currency(h.avg_cost), str(h.last_trade_date))
        except Exception as e:
            self.app.log(f"Error refreshing overview data: {e}")


class RiskDashboardScreen(Container):
    """The Risk Dashboard showing full risk metrics per holding."""

    def compose(self) -> ComposeResult:
        yield DataTable(id="risk-table")

    def on_mount(self) -> None:
        table = self.query_one("#risk-table", DataTable)
        table.add_columns("Symbol", "Shares", "Avg Cost", "Sharpe", "Ann. Vol", "Worst Day", "Ann. Return", "Max Drawdown")
        self.refresh_data()

    def refresh_data(self) -> None:
        try:
            conn = get_connection()
            risk_metrics = get_risk_summary(conn)
            drawdowns = {d.symbol: d.max_drawdown for d in get_drawdown(conn)}
            
            table = self.query_one("#risk-table", DataTable)
            table.clear()
            for rm in risk_metrics:
                dd = drawdowns.get(rm.symbol, 0.0)
                
                # Format Sharpe
                sharpe_str = f"{rm.sharpe:.4f}" if rm.sharpe is not None else "N/A"
                if rm.sharpe is not None:
                    # teal for positive, red for negative
                    color = "teal" if rm.sharpe > 0 else "red" if rm.sharpe < 0 else "white"
                    sharpe_str = f"[{color}]{sharpe_str}[/{color}]"
                
                table.add_row(
                    rm.symbol,
                    f"{rm.shares:.4f}",
                    format_currency(rm.avg_cost),
                    sharpe_str,
                    format_percentage(rm.annual_vol * 100) if rm.annual_vol else "N/A",
                    format_percentage(rm.worst_day * 100) if rm.worst_day else "N/A",
                    format_percentage(rm.annual_return * 100) if rm.annual_return else "N/A",
                    format_percentage(dd * 100)
                )
        except Exception as e:
            self.app.log(f"Error refreshing risk data: {e}")


class SqlConsoleScreen(Container):
    """SQL Console for executing raw queries."""

    def __init__(self) -> None:
        super().__init__()
        self.history: list[str] = []
        self.history_index: int = -1

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Input(placeholder="Enter SQL query (e.g. SELECT * FROM risk_summary)", id="sql-input")
            yield DataTable(id="sql-results")

    async def on_input_submitted(self, message: Input.Submitted) -> None:
        query = message.value.strip()
        if not query:
            return

        self.history.append(query)
        self.history_index = len(self.history)
        
        table = self.query_one("#sql-results", DataTable)
        table.clear(columns=True)
        
        try:
            conn = get_connection()
            # To handle duckdb error cleanly without crashing Textual
            result = conn.execute(query)
            desc = result.description
            if desc:
                cols = [d[0] for d in desc]
                table.add_columns(*cols)
                rows = result.fetchall()
                for row in rows:
                    table.add_row(*[str(val) for val in row])
            else:
                table.add_columns("Result")
                table.add_row("Query executed successfully (no results).")
        except Exception as e:
            table.add_columns("Error")
            table.add_row(str(e))
        
        message.input.value = ""

    def on_input_changed(self, message: Input.Changed) -> None:
        pass

    # Basic history navigation
    def action_history_up(self) -> None:
        if self.history and self.history_index > 0:
            self.history_index -= 1
            self.query_one("#sql-input", Input).value = self.history[self.history_index]

    def action_history_down(self) -> None:
        if self.history and self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.query_one("#sql-input", Input).value = self.history[self.history_index]
        elif self.history_index == len(self.history) - 1:
            self.history_index = len(self.history)
            self.query_one("#sql-input", Input).value = ""

    def on_mount(self) -> None:
        input_widget = self.query_one("#sql-input", Input)
        # Bind keys for history
        self.app.bind("up", "history_up")
        self.app.bind("down", "history_down")


class LedgerScopeApp(App):
    """Main Textual application for LedgerScope."""

    CSS = """
    TabbedContent {
        height: 100%;
    }
    
    #metrics-container {
        height: auto;
        layout: horizontal;
        margin-bottom: 1;
    }
    
    .metric-card {
        width: 1fr;
        height: 5;
        border: solid $primary;
        padding: 1 2;
        margin: 0 1;
        content-align: center middle;
    }
    
    .metric-title {
        color: $text-muted;
        text-style: bold;
    }
    
    .metric-value {
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("tab", "next_tab", "Next Tab")
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(id="tabs"):
            with TabPane("Overview", id="tab-overview"):
                yield OverviewScreen()
            with TabPane("Risk Dashboard", id="tab-risk"):
                yield RiskDashboardScreen()
            with TabPane("SQL Console", id="tab-sql"):
                yield SqlConsoleScreen()
        yield Footer()

    def action_next_tab(self) -> None:
        tabs = self.query_one(TabbedContent)
        active = tabs.active
        # Find index and go next
        pane_ids = ["tab-overview", "tab-risk", "tab-sql"]
        try:
            idx = pane_ids.index(active)
            next_idx = (idx + 1) % len(pane_ids)
            tabs.active = pane_ids[next_idx]
        except ValueError:
            pass

    def action_history_up(self) -> None:
        active_tab = self.query_one(TabbedContent).active
        if active_tab == "tab-sql":
             self.query_one(SqlConsoleScreen).action_history_up()

    def action_history_down(self) -> None:
        active_tab = self.query_one(TabbedContent).active
        if active_tab == "tab-sql":
             self.query_one(SqlConsoleScreen).action_history_down()


def main() -> None:
    app = LedgerScopeApp()
    app.run()

if __name__ == "__main__":
    main()
