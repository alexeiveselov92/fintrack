"""Implementation of 'fintrack import' command.

Imports transactions from CSV files into the workspace database.
Uses idempotent import with file hashing to prevent duplicates.
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from fintrack.core.exceptions import ImportError, WorkspaceNotFoundError
from fintrack.core.workspace import load_workspace
from fintrack.io.csv_reader import compute_file_hash, read_transactions_csv

console = Console()


def import_command(
    path: Path = typer.Argument(
        ...,
        help="CSV file or directory to import",
        exists=True,
    ),
    workspace: Path = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Path to workspace (default: current directory)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force re-import even if file was already imported",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be imported without making changes",
    ),
) -> None:
    """Import transactions from CSV files.

    Imports transactions from a CSV file or all CSV files in a directory.
    Uses file hashing to ensure idempotent imports - the same file
    won't be imported twice unless --force is used.

    CSV files must have columns: date, amount, category
    Optional columns: currency, description, is_savings, is_deduction, is_fixed
    """
    try:
        ws = load_workspace(workspace)
    except WorkspaceNotFoundError:
        console.print(
            "[red]Error:[/red] No workspace found. "
            "Run 'fintrack init <name>' or use --workspace"
        )
        raise typer.Exit(1)

    # Get storage repositories
    tx_repo = ws.storage.get_transaction_repository()
    import_log = ws.storage.get_import_log_repository()

    # Determine files to import
    if path.is_file():
        files = [path]
    else:
        files = sorted(path.glob("*.csv"))
        if not files:
            console.print(f"[yellow]No CSV files found in {path}[/yellow]")
            raise typer.Exit(0)

    console.print(f"Importing transactions to workspace '{ws.name}'...\n")

    # Results tracking
    results: list[tuple[str, str, int]] = []  # (filename, status, count)
    total_imported = 0
    total_skipped = 0

    for csv_file in files:
        filename = csv_file.name

        # Check if already imported
        file_hash = compute_file_hash(csv_file)

        if not force and import_log.is_imported(file_hash):
            results.append((filename, "skipped (already imported)", 0))
            total_skipped += 1
            continue

        if dry_run:
            # Count transactions without importing
            try:
                count = sum(1 for _ in read_transactions_csv(csv_file))
                results.append((filename, f"would import {count} records", count))
            except ImportError as e:
                results.append((filename, f"error: {e.details}", 0))
            continue

        # Import transactions
        try:
            transactions = list(read_transactions_csv(csv_file))

            if not transactions:
                results.append((filename, "empty file", 0))
                continue

            # Save to database
            saved_count = tx_repo.save_batch(transactions)

            # Log the import
            import_log.log_import(str(csv_file), file_hash, saved_count)

            results.append((filename, "imported", saved_count))
            total_imported += saved_count

        except ImportError as e:
            results.append((filename, f"error: {e.details}", 0))
            if e.line_number:
                console.print(
                    f"[red]Error in {filename} at line {e.line_number}:[/red] {e.details}"
                )

    # Display results
    table = Table(title="Import Results")
    table.add_column("File", style="cyan")
    table.add_column("Status")
    table.add_column("Records", justify="right")

    for filename, status, count in results:
        if "error" in status:
            style = "red"
        elif "skipped" in status:
            style = "yellow"
        elif "would import" in status:
            style = "blue"
        else:
            style = "green"

        table.add_row(filename, f"[{style}]{status}[/{style}]", str(count) if count else "-")

    console.print(table)
    console.print()

    if dry_run:
        console.print("[blue]Dry run - no changes made[/blue]")
    else:
        console.print(f"Total: [green]{total_imported}[/green] records imported")
        if total_skipped:
            console.print(f"       [yellow]{total_skipped}[/yellow] files skipped")

        # Show total transactions in database
        total_in_db = tx_repo.count()
        console.print(f"       [cyan]{total_in_db}[/cyan] total transactions in database")
