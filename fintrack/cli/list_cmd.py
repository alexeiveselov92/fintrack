"""Implementation of 'fintrack list' command.

Lists transactions, plans, and categories.
"""

from datetime import date
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from fintrack.cli.utils import format_currency
from fintrack.core.exceptions import WorkspaceNotFoundError
from fintrack.core.workspace import load_workspace
from fintrack.engine.periods import (
    format_period,
    get_current_period,
    get_period_end,
    parse_period,
)

console = Console()

# Create subcommand group
list_app = typer.Typer(help="List transactions, plans, and categories")


@list_app.command(name="transactions")
def list_transactions(
    period: str = typer.Option(
        None,
        "--period",
        "-p",
        help="Filter by period (e.g., 2024-01)",
    ),
    category: str = typer.Option(
        None,
        "--category",
        "-c",
        help="Filter by category",
    ),
    fixed_only: bool = typer.Option(
        False,
        "--fixed-only",
        help="Show only fixed expenses",
    ),
    flexible_only: bool = typer.Option(
        False,
        "--flexible-only",
        help="Show only flexible expenses",
    ),
    limit: int = typer.Option(
        50,
        "--limit",
        "-n",
        help="Maximum number of transactions to show",
    ),
    workspace: Path = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Path to workspace",
    ),
) -> None:
    """List transactions with optional filters."""
    try:
        ws = load_workspace(workspace)
    except WorkspaceNotFoundError:
        console.print("[red]Error:[/red] No workspace found")
        raise typer.Exit(1)

    tx_repo = ws.storage.get_transaction_repository()

    # Determine date range
    if period:
        try:
            period_start = parse_period(period, ws.config.interval)
            period_end = get_period_end(
                period_start, ws.config.interval, ws.config.custom_interval_days
            )
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    else:
        # Last 3 months by default
        period_start, period_end = get_current_period(
            ws.config.interval, ws.config.custom_interval_days
        )
        # Go back a bit
        from fintrack.engine.periods import get_previous_periods
        prev = get_previous_periods(period_start, 2, ws.config.interval)
        if prev:
            period_start = prev[-1]

    # Get transactions
    if category:
        transactions = tx_repo.get_by_category(category, period_start, period_end)
    else:
        transactions = tx_repo.get_by_period(period_start, period_end)

    # Apply filters
    if fixed_only:
        transactions = [t for t in transactions if t.is_fixed]
    elif flexible_only:
        transactions = [t for t in transactions if not t.is_fixed and not t.is_savings and not t.is_deduction]

    # Sort by date descending
    transactions = sorted(transactions, key=lambda t: t.date, reverse=True)

    if not transactions:
        console.print("[yellow]No transactions found[/yellow]")
        raise typer.Exit(0)

    # Limit
    total = len(transactions)
    transactions = transactions[:limit]

    # Display table
    table = Table(title=f"Transactions ({len(transactions)} of {total})")
    table.add_column("Date")
    table.add_column("Category")
    table.add_column("Amount", justify="right")
    table.add_column("Description")
    table.add_column("Flags")

    for tx in transactions:
        flags = []
        if tx.is_fixed:
            flags.append("F")
        if tx.is_savings:
            flags.append("S")
        if tx.is_deduction:
            flags.append("D")

        style = ""
        if tx.amount > 0:
            style = "green"
        elif tx.is_fixed:
            style = "dim"

        table.add_row(
            str(tx.date),
            tx.category,
            f"[{style}]{format_currency(tx.amount, tx.currency)}[/{style}]" if style else format_currency(tx.amount, tx.currency),
            tx.description or "",
            " ".join(flags),
        )

    console.print(table)
    console.print()
    console.print("[dim]Flags: F=Fixed, S=Savings, D=Deduction[/dim]")


@list_app.command(name="plans")
def list_plans(
    workspace: Path = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Path to workspace",
    ),
) -> None:
    """List all budget plans."""
    try:
        ws = load_workspace(workspace)
    except WorkspaceNotFoundError:
        console.print("[red]Error:[/red] No workspace found")
        raise typer.Exit(1)

    plans = ws.plans

    if not plans:
        console.print("[yellow]No budget plans found[/yellow]")
        console.print(f"Create plans in {ws.plans_dir}/")
        raise typer.Exit(0)

    table = Table(title="Budget Plans")
    table.add_column("ID")
    table.add_column("Valid From")
    table.add_column("Valid To")
    table.add_column("Gross Income", justify="right")
    table.add_column("Net Income", justify="right")
    table.add_column("Disposable", justify="right")

    for plan in plans:
        table.add_row(
            plan.id,
            str(plan.valid_from),
            str(plan.valid_to) if plan.valid_to else "ongoing",
            format_currency(plan.gross_income, plan.income_currency),
            format_currency(plan.net_income, plan.income_currency),
            format_currency(plan.disposable_income, plan.income_currency),
        )

    console.print(table)


@list_app.command(name="categories")
def list_categories(
    fixed: bool = typer.Option(
        False,
        "--fixed",
        help="Show only fixed categories",
    ),
    flexible: bool = typer.Option(
        False,
        "--flexible",
        help="Show only flexible categories",
    ),
    workspace: Path = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Path to workspace",
    ),
) -> None:
    """List all categories with totals."""
    try:
        ws = load_workspace(workspace)
    except WorkspaceNotFoundError:
        console.print("[red]Error:[/red] No workspace found")
        raise typer.Exit(1)

    tx_repo = ws.storage.get_transaction_repository()
    categories = tx_repo.get_all_categories()

    if not categories:
        console.print("[yellow]No categories found[/yellow]")
        raise typer.Exit(0)

    # Get fixed categories from current plan
    try:
        current_start, _ = get_current_period(ws.config.interval)
        plan = ws.get_plan_for_date(current_start)
        fixed_cats = plan.fixed_categories
    except Exception:
        fixed_cats = set()

    # Filter
    if fixed:
        categories = [c for c in categories if c in fixed_cats]
    elif flexible:
        categories = [c for c in categories if c not in fixed_cats]

    console.print(f"[bold]Categories[/bold] ({len(categories)} total)")
    for cat in sorted(categories):
        marker = " [dim](fixed)[/dim]" if cat in fixed_cats else ""
        console.print(f"  • {cat}{marker}")
