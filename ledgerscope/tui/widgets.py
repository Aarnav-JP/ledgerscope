from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static

class MetricCard(Static):
    """A card displaying a single KPI metric."""

    def __init__(self, title: str, value: str, delta: str = "", id: str | None = None) -> None:
        super().__init__(id=id)
        self.title_text = title
        self.value_text = value
        self.delta_text = delta

    def compose(self) -> ComposeResult:
        with Vertical(classes="metric-card"):
            yield Static(self.title_text, classes="metric-title")
            yield Static(self.value_text, classes="metric-value")
            if self.delta_text:
                yield Static(self.delta_text, classes="metric-delta")

    def update_values(self, value: str, delta: str = "") -> None:
        self.value_text = value
        self.delta_text = delta
        self.query_one(".metric-value", Static).update(value)
        if self.delta_text:
            delta_widget = self.query(".metric-delta")
            if delta_widget:
                delta_widget.first().update(delta)

def format_currency(value: float) -> str:
    """Format a float as currency."""
    return f"${value:,.2f}"

def format_percentage(value: float) -> str:
    """Format a float as percentage."""
    return f"{value:,.2f}%"

def get_color_class(value: float | None) -> str:
    """Return styling class based on value sign."""
    if value is None:
        return ""
    if value > 0:
        return "positive"
    elif value < 0:
        return "negative"
    return "neutral"
