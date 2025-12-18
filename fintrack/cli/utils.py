"""CLI utility functions for formatting and display."""

from decimal import Decimal
from pathlib import Path

from rich.console import Console
from rich.table import Table

from fintrack.core.constants import WORKSPACE_CONFIG_FILE
from fintrack.core.exceptions import WorkspaceNotFoundError
from fintrack.core.models import WorkspaceConfig
from fintrack.io.yaml_reader import load_workspace_config

console = Console()
err_console = Console(stderr=True)


def format_currency(amount: Decimal, currency: str = "EUR") -> str:
    """Format a decimal amount with currency symbol.

    Args:
        amount: The amount to format.
        currency: ISO 4217 currency code.

    Returns:
        Formatted string like "€1,234.56" or "-€500.00".
    """
    symbols = {
        "EUR": "€",
        "USD": "$",
        "GBP": "£",
        "RSD": "RSD ",
        "RUB": "₽",
        "JPY": "¥",
        "CHF": "CHF ",
    }
    symbol = symbols.get(currency, f"{currency} ")

    if amount < 0:
        return f"-{symbol}{abs(amount):,.2f}"
    return f"{symbol}{amount:,.2f}"


def format_percentage(value: Decimal, decimals: int = 1) -> str:
    """Format a decimal as percentage.

    Args:
        value: Decimal value (0.20 = 20%).
        decimals: Number of decimal places.

    Returns:
        Formatted string like "20.0%".
    """
    return f"{float(value) * 100:.{decimals}f}%"


def get_workspace(workspace_path: Path | None = None) -> tuple[Path, WorkspaceConfig]:
    """Load workspace configuration from a path.

    Args:
        workspace_path: Optional path to workspace. Uses cwd if None.

    Returns:
        Tuple of (workspace_path, WorkspaceConfig).

    Raises:
        WorkspaceNotFoundError: If no workspace.yaml found.
    """
    path = workspace_path or Path.cwd()

    if not (path / WORKSPACE_CONFIG_FILE).exists():
        raise WorkspaceNotFoundError(str(path))

    config = load_workspace_config(path)
    return path, config


def print_error(message: str) -> None:
    """Print an error message to stderr."""
    err_console.print(f"[red]Error:[/red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]Warning:[/yellow] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]{message}[/green]")


def create_summary_table(title: str) -> Table:
    """Create a styled table for summary display.

    Args:
        title: Table title.

    Returns:
        Configured Rich Table.
    """
    table = Table(
        title=title,
        show_header=True,
        header_style="bold",
        title_style="bold cyan",
    )
    return table
