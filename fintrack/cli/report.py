"""Implementation of 'fintrack report' command.

Generates HTML reports.
"""

from pathlib import Path

import typer
from rich.console import Console

from fintrack.core.exceptions import NoPlanFoundError, WorkspaceNotFoundError
from fintrack.core.workspace import load_workspace
from fintrack.engine.aggregator import analyze_period, get_historical_summaries
from fintrack.engine.periods import (
    format_period,
    get_current_period,
    get_period_end,
    parse_period,
)
from fintrack.reports.generator import generate_report_html, save_report

console = Console()


def report_command(
    period: str = typer.Option(
        None,
        "--period",
        "-p",
        help="Period to report (default: current period)",
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: reports/<period>.html)",
    ),
    workspace: Path = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Path to workspace (default: current directory)",
    ),
) -> None:
    """Generate HTML report for a period.

    Creates a self-contained HTML file with budget overview,
    category breakdown, and progress visualization.
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

    # Get transactions
    tx_repo = ws.storage.get_transaction_repository()

    # Get historical data for averages
    from fintrack.engine.periods import get_previous_periods
    prev_periods = get_previous_periods(
        period_start,
        ws.config.analysis_window,
        ws.config.interval,
        ws.config.custom_interval_days,
    )

    earliest = prev_periods[-1] if prev_periods else period_start
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

    # Analyze
    summary, analyses = analyze_period(
        transactions=all_transactions,
        period_start=period_start,
        interval=ws.config.interval,
        workspace_name=ws.name,
        plan=plan,
        historical_summaries=historical,
        custom_days=ws.config.custom_interval_days,
    )

    if summary.transaction_count == 0:
        console.print("[yellow]No transactions found for this period[/yellow]")
        raise typer.Exit(0)

    # Generate HTML
    html = generate_report_html(
        period_str=period_str,
        workspace_name=ws.name,
        plan=plan,
        summary=summary,
        analyses=analyses,
        currency=currency,
    )

    # Determine output path
    if output:
        output_path = output
    else:
        output_path = ws.reports_dir / f"{period_str}.html"

    # Save report
    save_report(html, output_path)

    console.print(f"[green]Report generated:[/green] {output_path}")
    console.print(f"Open in browser: file://{output_path.absolute()}")
