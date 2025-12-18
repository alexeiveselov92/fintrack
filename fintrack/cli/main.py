"""Main CLI entry point for FinTrack.

This module sets up the Typer application and registers all commands.
"""

import typer
from rich.console import Console

from fintrack import __version__

# Create the main Typer application
app = typer.Typer(
    name="fintrack",
    help="Personal Finance Tracker - budget planning and expense analysis",
    add_completion=False,
    no_args_is_help=True,
)

# Console for rich output
console = Console()
err_console = Console(stderr=True)


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"fintrack version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """FinTrack - Personal Finance Tracker CLI.

    Track expenses, plan budgets, and analyze your spending patterns.
    """
    pass


# Import and register commands
from fintrack.cli.init import init_command
from fintrack.cli.validate import validate_command
from fintrack.cli.import_cmd import import_command
from fintrack.cli.budget import budget_command
from fintrack.cli.status import status_command
from fintrack.cli.analyze import analyze_command
from fintrack.cli.report import report_command
from fintrack.cli.list_cmd import list_app

app.command(name="init")(init_command)
app.command(name="validate")(validate_command)
app.command(name="import")(import_command)
app.command(name="budget")(budget_command)
app.command(name="status")(status_command)
app.command(name="analyze")(analyze_command)
app.command(name="report")(report_command)
app.add_typer(list_app, name="list")


if __name__ == "__main__":
    app()
