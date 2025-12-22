"""Implementation of 'fintrack report' command.

Generates interactive HTML dashboard with 5 tabs:
1. Overview - KPIs, Cash Reconciliation, Timeline charts
2. Income & Expenses - Sankey, Treemap, Expenses Timeline
3. Savings - Coverage Indicator, Savings Timeline
4. Budget - Budget vs Actual, Alerts
5. Transactions - Filterable table with export
"""

from pathlib import Path

import typer
from rich.console import Console

from fintrack.core.exceptions import WorkspaceNotFoundError
from fintrack.core.workspace import load_workspace
from fintrack.dashboard import DashboardDataProvider, generate_dashboard_html, save_dashboard
from fintrack.engine.periods import (
    format_period,
    get_current_period,
    parse_period,
)

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
    """Generate interactive HTML dashboard for a period.

    Creates a self-contained HTML file with 5 tabs:
    - Overview: KPIs, Cash Reconciliation, Balance/Savings Timeline
    - Income & Expenses: Sankey diagram, Treemap, Expenses Timeline
    - Savings: Coverage Indicator, Savings vs Target Timeline
    - Budget: Budget vs Actual bars, Category breakdown
    - Transactions: Filterable table with export
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

    # Create data provider and get dashboard data
    provider = DashboardDataProvider(ws)
    data = provider.get_dashboard_data(period_start)

    if data.current_period_summary and data.current_period_summary.transaction_count == 0:
        console.print("[yellow]No transactions found for this period[/yellow]")
        # Still generate the dashboard (it will show empty state)

    # Generate HTML
    html = generate_dashboard_html(data)

    # Determine output path
    if output:
        output_path = output
    else:
        output_path = ws.reports_dir / f"{period_str}.html"

    # Save dashboard
    save_dashboard(html, output_path)

    console.print(f"[green]Dashboard generated:[/green] {output_path}")
    console.print(f"Open in browser: file://{output_path.absolute()}")
