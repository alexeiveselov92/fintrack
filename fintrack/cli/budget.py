"""Implementation of 'fintrack budget' command.

Shows budget projection based on BudgetPlan configuration.
"""

from datetime import date
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from fintrack.cli.utils import format_currency, format_percentage
from fintrack.core.exceptions import NoPlanFoundError, WorkspaceNotFoundError
from fintrack.core.workspace import load_workspace
from fintrack.engine.calculator import calculate_budget_projection
from fintrack.engine.periods import (
    format_period,
    get_current_period,
    parse_period,
)

console = Console()


def budget_command(
    period: str = typer.Option(
        None,
        "--period",
        "-p",
        help="Period to show (e.g., 2024-01 for month). Default: current period",
    ),
    workspace: Path = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Path to workspace (default: current directory)",
    ),
) -> None:
    """Show budget projection for a period.

    Calculates expected budget breakdown based on your BudgetPlan
    configuration. Shows income, deductions, fixed expenses,
    savings target, and disposable income.

    This is a projection without actual transaction data.
    Use 'fintrack analyze' to compare against actual spending.
    """
    try:
        ws = load_workspace(workspace)
    except WorkspaceNotFoundError:
        console.print(
            "[red]Error:[/red] No workspace found. "
            "Run 'fintrack init <name>' or use --workspace"
        )
        raise typer.Exit(1)

    # Determine period
    if period:
        try:
            period_start = parse_period(period, ws.config.interval)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    else:
        period_start, _ = get_current_period(
            ws.config.interval, ws.config.custom_interval_days
        )

    # Get applicable plan
    try:
        plan = ws.get_plan_for_date(period_start)
    except NoPlanFoundError:
        console.print(
            f"[red]Error:[/red] No budget plan found for period "
            f"{format_period(period_start, ws.config.interval)}\n"
            f"Create a plan in {ws.plans_dir}/"
        )
        raise typer.Exit(1)

    # Calculate projection
    projection = calculate_budget_projection(plan, period_start, ws.config.interval)
    currency = plan.income_currency

    # Display header
    console.print()
    console.print(
        Panel(
            f"[bold]Budget Projection for {projection.period}[/bold]\n"
            f"Plan: {projection.plan_id}",
            style="cyan",
        )
    )
    console.print()

    # Income section
    console.print("[bold]Income[/bold]")
    console.print(f"  Gross income:              {format_currency(projection.gross_income, currency):>15}")

    if projection.deductions_breakdown:
        console.print("  Deductions:")
        for d in projection.deductions_breakdown:
            console.print(f"    - {d.name}:{' ' * (18 - len(d.name))}{format_currency(d.amount, currency):>15}")
        console.print(f"  [dim]Total deductions:          {format_currency(projection.total_deductions, currency):>15}[/dim]")

    console.print("  " + "─" * 40)
    console.print(f"  [bold]Net income:                {format_currency(projection.net_income, currency):>15}[/bold]")
    console.print()

    # Fixed expenses section
    if projection.fixed_expenses_breakdown:
        console.print("[bold]Fixed Expenses[/bold] (from net income)")
        for f in projection.fixed_expenses_breakdown:
            cat_str = f" [{f.category}]" if f.category else ""
            console.print(f"    - {f.name}:{' ' * (18 - len(f.name))}{format_currency(f.amount, currency):>15}{cat_str}")
        console.print(f"  [dim]Total fixed:               {format_currency(projection.total_fixed_expenses, currency):>15}[/dim]")
        console.print()

    # Savings section
    console.print("[bold]Savings[/bold]")
    base_label = "net income" if projection.savings_base.value == "net_income" else "disposable"
    console.print(f"  Calculation base ({base_label}): {format_currency(projection.savings_calculation_base, currency):>15}")
    console.print(f"  Target rate:               {format_percentage(projection.savings_rate):>15}")
    console.print(f"  [green]Target amount:             {format_currency(projection.savings_target, currency):>15}[/green]")
    console.print()

    # Disposable income - THE KEY NUMBER
    console.print("═" * 50)
    console.print(
        f"[bold green]Disposable Income:         {format_currency(projection.disposable_income, currency):>15}[/bold green]"
    )
    console.print("═" * 50)
    console.print()

    # Category budgets
    if projection.flexible_category_budgets:
        console.print("[bold]Flexible Category Budgets[/bold] (from disposable)")

        table = Table(show_header=True, header_style="dim")
        table.add_column("Category")
        table.add_column("Budget", justify="right")
        table.add_column("Share", justify="right")

        for cb in projection.flexible_category_budgets:
            table.add_row(
                cb.category,
                format_currency(cb.amount, currency),
                f"{cb.share_of_budget:.1f}%",
            )

        table.add_row(
            "[dim]Total allocated[/dim]",
            f"[dim]{format_currency(projection.total_allocated_flexible, currency)}[/dim]",
            "",
        )

        if projection.unallocated_flexible > 0:
            table.add_row(
                "[yellow]Unallocated[/yellow]",
                f"[yellow]{format_currency(projection.unallocated_flexible, currency)}[/yellow]",
                "",
            )

        console.print(table)
        console.print()

    # Fixed category budgets (if any)
    if projection.fixed_category_budgets:
        console.print("[bold]Fixed Category Budgets[/bold]")
        for cb in projection.fixed_category_budgets:
            console.print(f"  {cb.category}: {format_currency(cb.amount, currency)}")
        console.print()
