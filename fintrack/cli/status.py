"""Implementation of 'fintrack status' command.

Shows current period status with progress indicators.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn

from fintrack.cli.utils import format_currency, format_percentage
from fintrack.core.exceptions import NoPlanFoundError, WorkspaceNotFoundError
from fintrack.core.workspace import load_workspace
from fintrack.engine.aggregator import get_period_summary
from fintrack.engine.periods import (
    days_remaining_in_period,
    format_period,
    get_current_period,
    parse_period,
)

console = Console()


def status_command(
    period: str = typer.Option(
        None,
        "--period",
        "-p",
        help="Period to show (default: current period)",
    ),
    workspace: Path = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Path to workspace (default: current directory)",
    ),
) -> None:
    """Show current period status.

    Displays a quick overview of spending progress, savings,
    and any warnings about budget overruns.
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

    # Get plan if available (currency always from workspace config)
    currency = ws.config.base_currency
    try:
        plan = ws.get_plan_for_date(period_start)
    except NoPlanFoundError:
        plan = None

    # Get transactions
    tx_repo = ws.storage.get_transaction_repository()
    from fintrack.engine.periods import get_period_end
    period_end = get_period_end(period_start, ws.config.interval, ws.config.custom_interval_days)
    transactions = tx_repo.get_by_period(period_start, period_end)

    # Get all transactions for cumulative calculations
    all_transactions = tx_repo.get_all()

    # Get first transaction date for cumulative target calculation
    first_tx_date = min((tx.date for tx in all_transactions), default=None) if all_transactions else None

    # Create a safe get_plan_for_date callback
    def safe_get_plan(d: date) -> "BudgetPlan | None":
        try:
            return ws.get_plan_for_date(d)
        except Exception:
            return None

    # Get summary
    summary = get_period_summary(
        transactions=transactions,
        period_start=period_start,
        interval=ws.config.interval,
        workspace_name=ws.name,
        plan=plan,
        custom_days=ws.config.custom_interval_days,
        all_transactions=all_transactions,
        get_plan_for_date=safe_get_plan,
        first_transaction_date=first_tx_date,
    )

    # Calculate days remaining
    days_left = days_remaining_in_period(
        period_start, ws.config.interval, ws.config.custom_interval_days
    )

    # Display header
    console.print()
    title = f"Status for {period_str}"
    if days_left > 0:
        title += f" ({days_left} days remaining)"
    console.print(Panel(f"[bold]{title}[/bold]", style="cyan"))
    console.print()

    # No data case
    if summary.transaction_count == 0:
        console.print("[yellow]No transactions found for this period[/yellow]")
        if plan:
            console.print(f"\nBudget plan: {plan.id}")
            console.print(f"Disposable income: {format_currency(plan.disposable_income, currency)}")
        raise typer.Exit(0)

    warnings: list[str] = []

    # Gross Income (vs Plan) - show if plan has gross income
    if plan and plan.gross_income > 0:
        console.print("[bold]Gross Income (vs Plan)[/bold]")
        planned_income = plan.gross_income
        actual_income = summary.total_income
        income_pct = (actual_income / planned_income * 100) if planned_income > 0 else Decimal(0)
        variance = actual_income - planned_income

        console.print(f"  Plan:      {format_currency(planned_income, currency):>12}")
        console.print(f"  Actual:    {format_currency(actual_income, currency):>12}  ({income_pct:.1f}%)")

        if variance >= 0:
            console.print(f"  [green]Variance:    +{format_currency(variance, currency):>11}[/green]  (above plan)")
        else:
            console.print(f"  [red]Variance:    {format_currency(variance, currency):>12}[/red]  (below plan)")
            warnings.append(f"Actual income below plan by {format_currency(abs(variance), currency)}")
        console.print()

    # Deductions (vs Plan) - show if plan has deductions
    if plan and plan.total_deductions > 0:
        console.print("[bold]Deductions (vs Plan)[/bold]")
        planned_ded = plan.total_deductions
        actual_ded = summary.total_deductions
        ded_pct = (actual_ded / planned_ded * 100) if planned_ded > 0 else Decimal(0)
        variance = planned_ded - actual_ded

        console.print(f"  Plan:      {format_currency(planned_ded, currency):>12}")
        console.print(f"  Actual:    {format_currency(actual_ded, currency):>12}  ({ded_pct:.1f}%)")

        if variance >= 0:
            console.print(f"  [green]Variance:    +{format_currency(variance, currency):>11}[/green]  (under plan)")
        else:
            console.print(f"  [red]Variance:    {format_currency(variance, currency):>12}[/red]  (over plan)")
            warnings.append(f"Deductions over plan by {format_currency(abs(variance), currency)}")
        console.print()

    # Fixed expenses progress
    if plan and plan.total_fixed_expenses > 0:
        console.print("[bold]Fixed Expenses[/bold]")
        fixed_pct = (summary.total_fixed_expenses / plan.total_fixed_expenses * 100) if plan.total_fixed_expenses > 0 else Decimal(0)

        console.print(f"  Budget:  {format_currency(plan.total_fixed_expenses, currency):>12}")
        console.print(f"  Spent:   {format_currency(summary.total_fixed_expenses, currency):>12}  ({fixed_pct:.1f}%)")

        if fixed_pct > 100:
            console.print(f"  [red]Over budget by {format_currency(summary.total_fixed_expenses - plan.total_fixed_expenses, currency)}[/red]")
            warnings.append(f"Fixed expenses over budget by {format_currency(summary.total_fixed_expenses - plan.total_fixed_expenses, currency)}")
        elif fixed_pct >= 100:
            console.print("  [green]✓ On target[/green]")
        console.print()

    # Flexible spending progress
    if plan:
        console.print("[bold]Flexible Spending[/bold]")
        disposable = plan.disposable_income
        spent = summary.total_flexible_expenses
        remaining = disposable - spent
        pct = (spent / disposable * 100) if disposable > 0 else Decimal(0)

        console.print(f"  Budget (disposable): {format_currency(disposable, currency):>12}")
        console.print(f"  Spent so far:        {format_currency(spent, currency):>12}  ({pct:.1f}%)")

        if remaining >= 0:
            console.print(f"  [green]Remaining:             {format_currency(remaining, currency):>12}[/green]")
        else:
            console.print(f"  [red]Over budget:           {format_currency(abs(remaining), currency):>12}[/red]")
            warnings.append(f"Flexible spending over budget by {format_currency(abs(remaining), currency)}")
        console.print()

    # Savings & Balance
    console.print("[bold]Savings & Balance[/bold]")

    # Period savings
    if plan and plan.savings_target > 0:
        saved = summary.total_savings
        target = plan.savings_target
        pct = (saved / target * 100) if target > 0 else Decimal(0)
        console.print(f"  Target (period):        {format_currency(target, currency):>12}")
        console.print(f"  Saved (period):         {format_currency(saved, currency):>12}  ({pct:.1f}%)")
        if pct >= 100:
            console.print("  [green]✓ Target reached![/green]")
        elif days_left == 0:
            shortfall = target - saved
            console.print(f"  [red]Shortfall: {format_currency(shortfall, currency)}[/red]")
            warnings.append(f"Savings target missed by {format_currency(shortfall, currency)}")
    else:
        console.print(f"  Saved (period):         {format_currency(summary.total_savings, currency):>12}")

    # Cumulative values - always show
    console.print(f"  Cumulative Savings:     {format_currency(summary.cumulative_savings, currency):>12}")

    # Cumulative target and surplus - only if we have it
    if summary.cumulative_savings_target > 0:
        console.print(f"  Cumulative Target:      {format_currency(summary.cumulative_savings_target, currency):>12}")
        if summary.savings_surplus >= 0:
            console.print(f"  [green]Savings Surplus:        +{format_currency(summary.savings_surplus, currency):>11}[/green]  (ahead)")
        else:
            console.print(f"  [red]Savings Deficit:         {format_currency(summary.savings_surplus, currency):>12}[/red]  (behind)")
            warnings.append(f"Behind savings plan by {format_currency(abs(summary.savings_surplus), currency)}")

    # Cash on hand and cumulative balance
    console.print(f"  Cumulative Balance:     {format_currency(summary.cumulative_balance, currency):>12}")
    console.print(f"  Cash on Hand:           {format_currency(summary.cash_on_hand, currency):>12}")
    console.print()

    # Category breakdown (top spenders)
    if summary.expenses_by_category:
        console.print("[bold]Top Categories[/bold]")
        sorted_cats = sorted(
            summary.expenses_by_category.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        for cat, amount in sorted_cats:
            pct = (amount / summary.total_expenses * 100) if summary.total_expenses > 0 else Decimal(0)
            is_fixed = cat in summary.fixed_expenses_by_category
            marker = "[dim](fixed)[/dim]" if is_fixed else ""
            console.print(f"  {cat}: {format_currency(amount, currency):>12} ({pct:.1f}%) {marker}")
        console.print()

    # Warnings
    if warnings:
        console.print("[bold yellow]⚠ Warnings[/bold yellow]")
        for w in warnings:
            console.print(f"  - {w}")
        console.print()

    # Summary line
    console.print(f"[dim]Transactions: {summary.transaction_count}[/dim]")
    if summary.last_transaction_date:
        console.print(f"[dim]Last transaction: {summary.last_transaction_date}[/dim]")
