"""Implementation of 'fintrack validate' command.

Validates workspace configuration files and reports any errors.
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from fintrack.core.constants import WORKSPACE_CONFIG_FILE
from fintrack.core.exceptions import InvalidConfigError, WorkspaceNotFoundError
from fintrack.io.yaml_reader import (
    load_all_plans,
    load_exchange_rates,
    load_workspace_config,
)

console = Console()


class ValidationResult:
    """Accumulates validation results."""

    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []  # (file, message)
        self.warnings: list[tuple[str, str]] = []

    def add_error(self, file: str, message: str) -> None:
        """Add an error."""
        self.errors.append((file, message))

    def add_warning(self, file: str, message: str) -> None:
        """Add a warning."""
        self.warnings.append((file, message))

    @property
    def is_valid(self) -> bool:
        """Return True if no errors."""
        return len(self.errors) == 0


def validate_workspace_config(workspace_path: Path, result: ValidationResult) -> None:
    """Validate workspace.yaml configuration."""
    try:
        config = load_workspace_config(workspace_path)

        # Check directories exist
        tx_dir = workspace_path / config.transactions_dir
        if not tx_dir.exists():
            result.add_warning(
                WORKSPACE_CONFIG_FILE,
                f"Transactions directory does not exist: {config.transactions_dir}",
            )

        plans_dir = workspace_path / config.plans_dir
        if not plans_dir.exists():
            result.add_warning(
                WORKSPACE_CONFIG_FILE,
                f"Plans directory does not exist: {config.plans_dir}",
            )

        reports_dir = workspace_path / config.reports_dir
        if not reports_dir.exists():
            result.add_warning(
                WORKSPACE_CONFIG_FILE,
                f"Reports directory does not exist: {config.reports_dir}",
            )

    except WorkspaceNotFoundError:
        result.add_error(WORKSPACE_CONFIG_FILE, "File not found")
    except InvalidConfigError as e:
        result.add_error(WORKSPACE_CONFIG_FILE, e.details)


def validate_budget_plans(workspace_path: Path, result: ValidationResult) -> None:
    """Validate all budget plan files."""
    try:
        config = load_workspace_config(workspace_path)
        plans_dir = workspace_path / config.plans_dir

        if not plans_dir.exists():
            return

        plans = load_all_plans(plans_dir)

        # Check for overlapping plan periods
        for i, plan in enumerate(plans):
            for j, other_plan in enumerate(plans[i + 1 :], start=i + 1):
                # Check if periods overlap
                plan_end = plan.valid_to or other_plan.valid_from
                if plan.valid_from < other_plan.valid_from <= plan_end:
                    if plan.valid_to is not None:
                        result.add_error(
                            f"plans/{plan.id}",
                            f"Period overlaps with plan '{other_plan.id}'",
                        )

        # Validate each plan
        for plan in plans:
            # Check category budgets match fixed expenses
            fixed_categories = {
                fe.category for fe in plan.fixed_expenses if fe.category
            }
            budget_fixed_categories = {
                cb.category for cb in plan.category_budgets if cb.is_fixed
            }

            missing = fixed_categories - budget_fixed_categories
            if missing:
                result.add_warning(
                    f"plans/{plan.id}",
                    f"Fixed expense categories without matching budget: {missing}",
                )

            # Check total category budgets vs disposable income
            flexible_total = sum(
                cb.amount for cb in plan.category_budgets if not cb.is_fixed
            )
            if flexible_total > plan.disposable_income:
                result.add_warning(
                    f"plans/{plan.id}",
                    f"Category budgets ({flexible_total}) exceed disposable income ({plan.disposable_income})",
                )

    except InvalidConfigError as e:
        result.add_error(e.file_path, e.details)
    except WorkspaceNotFoundError:
        pass  # Already handled


def validate_exchange_rates(workspace_path: Path, result: ValidationResult) -> None:
    """Validate rates.yaml configuration."""
    rates_file = workspace_path / "rates.yaml"
    if not rates_file.exists():
        return  # Optional file

    try:
        load_exchange_rates(rates_file)
    except InvalidConfigError as e:
        result.add_error("rates.yaml", e.details)


def validate_command(
    workspace: Path = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Path to workspace (default: current directory)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed validation information",
    ),
) -> None:
    """Validate workspace configuration files.

    Checks workspace.yaml, budget plans, and exchange rates for errors.
    Reports any issues found with suggestions for fixes.
    """
    workspace_path = workspace or Path.cwd()

    # Check if workspace.yaml exists
    if not (workspace_path / WORKSPACE_CONFIG_FILE).exists():
        console.print(
            f"[red]Error:[/red] No workspace found at {workspace_path}\n"
            f"Run 'fintrack init <name>' to create a new workspace"
        )
        raise typer.Exit(1)

    console.print(f"Validating workspace at {workspace_path}...\n")

    result = ValidationResult()

    # Run all validations
    validate_workspace_config(workspace_path, result)
    validate_budget_plans(workspace_path, result)
    validate_exchange_rates(workspace_path, result)

    # Display results
    if result.errors:
        console.print("[red]Errors found:[/red]")
        table = Table(show_header=True, header_style="bold red")
        table.add_column("File")
        table.add_column("Issue")

        for file, message in result.errors:
            table.add_row(file, message)

        console.print(table)
        console.print()

    if result.warnings:
        console.print("[yellow]Warnings:[/yellow]")
        table = Table(show_header=True, header_style="bold yellow")
        table.add_column("File")
        table.add_column("Issue")

        for file, message in result.warnings:
            table.add_row(file, message)

        console.print(table)
        console.print()

    # Summary
    if result.is_valid:
        if result.warnings:
            console.print(
                f"[green]Validation passed[/green] with {len(result.warnings)} warning(s)"
            )
        else:
            console.print("[green]Validation passed[/green] - all checks OK")
    else:
        console.print(
            f"[red]Validation failed[/red] - {len(result.errors)} error(s) found"
        )
        raise typer.Exit(1)
