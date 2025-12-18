"""Implementation of 'fintrack init' command.

Creates a new workspace with the required directory structure and
example configuration files.
"""

from pathlib import Path

import typer
from rich.console import Console

from fintrack.core.constants import (
    DEFAULT_PLANS_DIR,
    DEFAULT_REPORTS_DIR,
    DEFAULT_TRANSACTIONS_DIR,
    WORKSPACE_CONFIG_FILE,
    get_example_csv,
    get_example_plan_yaml,
    get_example_rates_yaml,
    get_example_workspace_yaml,
)
from fintrack.io.yaml_writer import write_raw_content

console = Console()


def init_command(
    name: str = typer.Argument(
        ...,
        help="Name of the workspace to create",
    ),
    interval: str = typer.Option(
        "month",
        "--interval",
        "-i",
        help="Budget interval type (day, week, month, quarter, year)",
    ),
    currency: str = typer.Option(
        "EUR",
        "--currency",
        "-c",
        help="Base currency (ISO 4217 code)",
    ),
    path: Path = typer.Option(
        None,
        "--path",
        "-p",
        help="Parent directory for workspace (default: current directory)",
    ),
) -> None:
    """Create a new FinTrack workspace.

    Creates a directory structure with example configuration files
    to help you get started with budget tracking.
    """
    # Determine workspace location
    parent = path or Path.cwd()
    workspace_dir = parent / name

    # Check if directory already exists
    if workspace_dir.exists():
        console.print(f"[red]Error:[/red] Directory '{name}' already exists")
        raise typer.Exit(1)

    try:
        # Create directory structure
        console.print(f"Creating workspace '{name}'...")

        workspace_dir.mkdir(parents=True)
        (workspace_dir / DEFAULT_TRANSACTIONS_DIR).mkdir()
        (workspace_dir / DEFAULT_PLANS_DIR).mkdir()
        (workspace_dir / DEFAULT_REPORTS_DIR).mkdir()
        (workspace_dir / ".cache").mkdir()

        # Write workspace.yaml
        write_raw_content(
            workspace_dir / WORKSPACE_CONFIG_FILE,
            get_example_workspace_yaml(name, currency.upper()),
        )

        # Write example plan
        write_raw_content(
            workspace_dir / DEFAULT_PLANS_DIR / "example.yaml",
            get_example_plan_yaml(),
        )

        # Write rates.yaml
        write_raw_content(
            workspace_dir / "rates.yaml",
            get_example_rates_yaml(),
        )

        # Write example transactions CSV
        write_raw_content(
            workspace_dir / DEFAULT_TRANSACTIONS_DIR / "example.csv",
            get_example_csv(),
        )

        # Write .gitignore for cache
        write_raw_content(
            workspace_dir / ".gitignore",
            ".cache/\nreports/*.html\n",
        )

        console.print()
        console.print("[green]Workspace created successfully![/green]")
        console.print()
        console.print("Directory structure:")
        console.print(f"  {name}/")
        console.print(f"    {WORKSPACE_CONFIG_FILE}")
        console.print(f"    rates.yaml")
        console.print(f"    {DEFAULT_PLANS_DIR}/")
        console.print(f"      example.yaml")
        console.print(f"    {DEFAULT_TRANSACTIONS_DIR}/")
        console.print(f"      example.csv")
        console.print(f"    {DEFAULT_REPORTS_DIR}/")
        console.print(f"    .cache/")
        console.print()
        console.print("Next steps:")
        console.print(f"  1. cd {name}")
        console.print("  2. Edit workspace.yaml with your settings")
        console.print("  3. Create a budget plan in plans/ directory")
        console.print("  4. Import your transactions: fintrack import transactions/")
        console.print("  5. View your budget: fintrack budget")

    except OSError as e:
        console.print(f"[red]Error creating workspace:[/red] {e}")
        raise typer.Exit(1)
