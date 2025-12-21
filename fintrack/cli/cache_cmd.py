"""Implementation of 'fintrack cache' command.

Manage import cache: clear all data or reset specific files.
"""

from pathlib import Path

import typer
from rich.console import Console

from fintrack.core.exceptions import WorkspaceNotFoundError
from fintrack.core.workspace import load_workspace

console = Console()

# Create subcommand group
cache_app = typer.Typer(help="Manage import cache and data")


@cache_app.command(name="clear")
def cache_clear(
    confirm: bool = typer.Option(
        False,
        "--confirm",
        "-y",
        help="Confirm deletion (required)",
    ),
    workspace: Path = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Path to workspace",
    ),
) -> None:
    """Clear all transactions and import history.

    This deletes ALL data from the database. Use with caution.
    Requires --confirm flag to execute.
    """
    try:
        ws = load_workspace(workspace)
    except WorkspaceNotFoundError:
        console.print("[red]Error:[/red] No workspace found")
        raise typer.Exit(1)

    tx_repo = ws.storage.get_transaction_repository()
    import_log = ws.storage.get_import_log_repository()

    # Show current counts
    tx_count = tx_repo.count()
    imports = import_log.get_imported_files()
    import_count = len(imports)

    if tx_count == 0 and import_count == 0:
        console.print("[yellow]Database is already empty[/yellow]")
        raise typer.Exit(0)

    console.print(f"Current data: [cyan]{tx_count}[/cyan] transactions, [cyan]{import_count}[/cyan] imported files")

    if not confirm:
        console.print()
        console.print("[yellow]This will delete ALL data![/yellow]")
        console.print("Run with [bold]--confirm[/bold] to proceed")
        raise typer.Exit(0)

    # Delete everything
    deleted_tx = tx_repo.delete_all()
    deleted_imports = import_log.clear_all()

    console.print()
    console.print(f"[green]Deleted:[/green] {deleted_tx} transactions, {deleted_imports} import records")
    console.print("[dim]Run 'fintrack import' to re-import data[/dim]")


@cache_app.command(name="reset")
def cache_reset(
    filename: str = typer.Argument(
        ...,
        help="Filename to reset (e.g., 'december.csv')",
    ),
    workspace: Path = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Path to workspace",
    ),
) -> None:
    """Reset a specific file to allow re-import.

    Deletes the import log entry and associated transactions for the file.
    After reset, the file can be imported again.
    """
    try:
        ws = load_workspace(workspace)
    except WorkspaceNotFoundError:
        console.print("[red]Error:[/red] No workspace found")
        raise typer.Exit(1)

    tx_repo = ws.storage.get_transaction_repository()
    import_log = ws.storage.get_import_log_repository()

    # Check if file exists in import log
    imports = import_log.get_imported_files()
    matching = [i for i in imports if filename in str(i["file_path"])]

    if not matching:
        console.print(f"[yellow]No import found matching '{filename}'[/yellow]")
        console.print("Run 'fintrack list imports' to see imported files")
        raise typer.Exit(1)

    # Delete transactions from this source
    deleted_tx = tx_repo.delete_by_source(filename)

    # Delete import log entry
    deleted_import = import_log.delete_by_file(filename)

    console.print(f"[green]Reset:[/green] {filename}")
    console.print(f"  Deleted: {deleted_tx} transactions")
    if deleted_import:
        console.print("  Cleared import log entry")
    console.print()
    console.print("[dim]Run 'fintrack import' to re-import the file[/dim]")
