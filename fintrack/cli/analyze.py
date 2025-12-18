"""Implementation of 'fintrack analyze' command.

Full analysis with historical comparison and variance reporting.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from fintrack.cli.utils import format_currency
from fintrack.core.exceptions import NoPlanFoundError, WorkspaceNotFoundError
from fintrack.core.workspace import load_workspace
from fintrack.engine.aggregator import analyze_period, get_historical_summaries
from fintrack.engine.periods import (
    format_period,
    get_current_period,
    get_period_end,
    parse_period,
)

console = Console()


def format_variance(amount: Decimal | None, currency: str) -> str:
    """Format variance with color coding."""
    if amount is None:
        return "-"
    if amount > 0:
        return f"[green]+{format_currency(amount, currency)}[/green]"
    elif amount < 0:
        return f"[red]{format_currency(amount, currency)}[/red]"
    return format_currency(amount, currency)


def analyze_command(
    period: str = typer.Option(
        None,
        "--period",
        "-p",
        help="Period to analyze (default: current period)",
    ),
    category: str = typer.Option(
        None,
        "--category",
        "-c",
        help="Filter by category",
    ),
    workspace: Path = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Path to workspace (default: current directory)",
    ),
) -> None:
    """Analyze spending with historical comparison.

    Shows detailed breakdown of actual vs planned spending,
    comparison with historical averages, and variance analysis.
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

    period_str = format_period(period_start, ws.config.interval)
    period_end = get_period_end(
        period_start, ws.config.interval, ws.config.custom_interval_days
    )

    # Get plan
    try:
        plan = ws.get_plan_for_date(period_start)
        currency = plan.income_currency
    except NoPlanFoundError:
        plan = None
        currency = ws.config.base_currency

    # Get all transactions
    tx_repo = ws.storage.get_transaction_repository()

    # For historical analysis, we need more transactions
    # Get transactions for analysis window + current period
    from fintrack.engine.periods import get_previous_periods
    prev_periods = get_previous_periods(
        period_start,
        ws.config.analysis_window,
        ws.config.interval,
        ws.config.custom_interval_days,
    )

    if prev_periods:
        earliest = prev_periods[-1]
    else:
        earliest = period_start

    all_transactions = tx_repo.get_by_period(earliest, period_end)

    # Get historical summaries
    historical = get_historical_summaries(
        transactions=all_transactions,
        period_start=period_start,
        window=ws.config.analysis_window,
        interval=ws.config.interval,
        workspace_name=ws.name,
        plan=plan,
        custom_days=ws.config.custom_interval_days,
    )

    # Analyze period
    summary, analyses = analyze_period(
        transactions=all_transactions,
        period_start=period_start,
        interval=ws.config.interval,
        workspace_name=ws.name,
        plan=plan,
        historical_summaries=historical,
        custom_days=ws.config.custom_interval_days,
    )

    # Filter by category if specified
    if category:
        analyses = [a for a in analyses if a.category.lower() == category.lower()]
        if not analyses:
            console.print(f"[yellow]No data for category '{category}'[/yellow]")
            raise typer.Exit(0)

    # Display header
    console.print()
    console.print(
        Panel(
            f"[bold]Analysis for {period_str}[/bold]\n"
            f"Comparing against {ws.config.analysis_window}-period average",
            style="cyan",
        )
    )
    console.print()

    # No data case
    if summary.transaction_count == 0:
        console.print("[yellow]No transactions found for this period[/yellow]")
        raise typer.Exit(0)

    # Overview
    if plan:
        console.print(f"[bold]Disposable Income:[/bold] {format_currency(plan.disposable_income, currency)}")
        console.print()

    # Fixed categories table
    fixed_analyses = [a for a in analyses if a.is_fixed and a.actual_amount > 0]
    if fixed_analyses:
        console.print("[bold]Fixed Categories[/bold] (variance from plan)")

        table = Table(show_header=True, header_style="bold")
        table.add_column("Category")
        table.add_column("Actual", justify="right")
        table.add_column("Planned", justify="right")
        table.add_column("Variance", justify="right")

        total_fixed_actual = Decimal(0)
        total_fixed_planned = Decimal(0)

        for a in sorted(fixed_analyses, key=lambda x: x.actual_amount, reverse=True):
            total_fixed_actual += a.actual_amount
            if a.planned_amount:
                total_fixed_planned += a.planned_amount

            table.add_row(
                a.category,
                format_currency(a.actual_amount, currency),
                format_currency(a.planned_amount, currency) if a.planned_amount else "-",
                format_variance(a.variance_vs_plan, currency),
            )

        # Total row
        total_variance = total_fixed_planned - total_fixed_actual if total_fixed_planned else None
        table.add_row(
            "[bold]Total Fixed[/bold]",
            f"[bold]{format_currency(total_fixed_actual, currency)}[/bold]",
            f"[bold]{format_currency(total_fixed_planned, currency)}[/bold]" if total_fixed_planned else "-",
            format_variance(total_variance, currency) if total_variance else "-",
            style="dim",
        )

        console.print(table)
        console.print()

    # Flexible categories table
    flexible_analyses = [a for a in analyses if not a.is_fixed and a.actual_amount > 0]
    if flexible_analyses:
        console.print("[bold]Flexible Categories[/bold] (vs plan and historical average)")

        table = Table(show_header=True, header_style="bold")
        table.add_column("Category")
        table.add_column("Actual", justify="right")
        table.add_column("Planned", justify="right")
        table.add_column(f"Avg({ws.config.analysis_window})", justify="right")
        table.add_column("vs Plan", justify="right")
        table.add_column("vs Avg", justify="right")

        total_flex_actual = Decimal(0)
        total_flex_planned = Decimal(0)

        for a in sorted(flexible_analyses, key=lambda x: x.actual_amount, reverse=True):
            total_flex_actual += a.actual_amount
            if a.planned_amount:
                total_flex_planned += a.planned_amount

            table.add_row(
                a.category,
                format_currency(a.actual_amount, currency),
                format_currency(a.planned_amount, currency) if a.planned_amount else "-",
                format_currency(a.historical_average, currency) if a.historical_average else "-",
                format_variance(a.variance_vs_plan, currency),
                format_variance(a.variance_vs_history, currency),
            )

        # Total row
        total_variance = total_flex_planned - total_flex_actual if total_flex_planned else None
        table.add_row(
            "[bold]Total Flexible[/bold]",
            f"[bold]{format_currency(total_flex_actual, currency)}[/bold]",
            f"[bold]{format_currency(total_flex_planned, currency)}[/bold]" if total_flex_planned else "-",
            "",
            format_variance(total_variance, currency) if total_variance else "-",
            "",
            style="dim",
        )

        console.print(table)
        console.print()

    # Savings
    console.print("[bold]Savings[/bold]")
    if plan:
        console.print(f"  Target:      {format_currency(plan.savings_target, currency):>12}")
    console.print(f"  Actual:      {format_currency(summary.total_savings, currency):>12}")
    if plan and plan.savings_target > 0:
        achievement = (summary.total_savings / plan.savings_target * 100)
        console.print(f"  Achievement: {achievement:.1f}%")
    console.print()

    # Summary
    console.print("[bold]Summary[/bold]")
    if plan:
        fixed_diff = plan.total_fixed_expenses - summary.total_fixed_expenses
        console.print(f"  Fixed budget:    {format_variance(fixed_diff, currency)} from plan")

        flex_remaining = plan.disposable_income - summary.total_flexible_expenses
        if flex_remaining >= 0:
            console.print(f"  Flexible budget: [green]{format_currency(flex_remaining, currency)}[/green] remaining")
        else:
            console.print(f"  Flexible budget: [red]{format_currency(abs(flex_remaining), currency)}[/red] over")

        if plan.savings_target > 0:
            savings_diff = summary.total_savings - plan.savings_target
            if savings_diff >= 0:
                console.print(f"  Savings:         [green]+{format_currency(savings_diff, currency)}[/green] above target")
            else:
                console.print(f"  Savings:         [red]{format_currency(savings_diff, currency)}[/red] below target")

    console.print()
    console.print(f"[dim]Total transactions: {summary.transaction_count}[/dim]")
