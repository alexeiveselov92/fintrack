"""Workspace management utilities.

Provides functions for loading workspace configuration, finding applicable
budget plans, and managing workspace state.
"""

from datetime import date
from pathlib import Path

from fintrack.core.constants import WORKSPACE_CONFIG_FILE
from fintrack.core.exceptions import NoPlanFoundError, WorkspaceNotFoundError
from fintrack.core.models import BudgetPlan, ExchangeRate, WorkspaceConfig
from fintrack.io.yaml_reader import (
    load_all_plans,
    load_exchange_rates,
    load_workspace_config,
)
from fintrack.storage.factory import StorageFactory, create_storage


class Workspace:
    """Represents a loaded FinTrack workspace.

    Provides access to configuration, budget plans, exchange rates,
    and storage repositories.
    """

    def __init__(self, path: Path) -> None:
        """Initialize workspace from a directory.

        Args:
            path: Path to workspace directory (must contain workspace.yaml).

        Raises:
            WorkspaceNotFoundError: If workspace.yaml not found.
        """
        self.path = path
        self.config = load_workspace_config(path)
        self._plans: list[BudgetPlan] | None = None
        self._rates: list[ExchangeRate] | None = None
        self._storage: StorageFactory | None = None

    @property
    def name(self) -> str:
        """Workspace name from configuration."""
        return self.config.name

    @property
    def plans_dir(self) -> Path:
        """Path to plans directory."""
        return self.path / self.config.plans_dir

    @property
    def transactions_dir(self) -> Path:
        """Path to transactions directory."""
        return self.path / self.config.transactions_dir

    @property
    def reports_dir(self) -> Path:
        """Path to reports directory."""
        return self.path / self.config.reports_dir

    @property
    def db_path(self) -> Path:
        """Path to SQLite database file."""
        return self.path / self.config.cache_db

    @property
    def plans(self) -> list[BudgetPlan]:
        """All budget plans, sorted by valid_from date."""
        if self._plans is None:
            self._plans = load_all_plans(self.plans_dir)
        return self._plans

    @property
    def rates(self) -> list[ExchangeRate]:
        """All exchange rates."""
        if self._rates is None:
            rates_file = self.path / "rates.yaml"
            self._rates = load_exchange_rates(rates_file)
        return self._rates

    @property
    def storage(self) -> StorageFactory:
        """Storage factory for repository access."""
        if self._storage is None:
            self._storage = create_storage(self.db_path)
        return self._storage

    def get_plan_for_date(self, target_date: date) -> BudgetPlan:
        """Find the applicable budget plan for a given date.

        Plans are matched by their valid_from/valid_to range.
        A plan with valid_to=None is valid until the next plan starts.

        Args:
            target_date: Date to find plan for.

        Returns:
            The applicable BudgetPlan.

        Raises:
            NoPlanFoundError: If no plan covers the target date.
        """
        applicable_plan: BudgetPlan | None = None

        for plan in self.plans:
            # Check if date is after plan start
            if plan.valid_from > target_date:
                continue

            # Check if date is before plan end (if specified)
            if plan.valid_to is not None and plan.valid_to < target_date:
                continue

            # This plan could apply - take the most recent one
            if applicable_plan is None or plan.valid_from > applicable_plan.valid_from:
                applicable_plan = plan

        if applicable_plan is None:
            raise NoPlanFoundError(target_date.isoformat())

        return applicable_plan

    def get_rate(
        self, from_currency: str, to_currency: str, target_date: date
    ) -> ExchangeRate | None:
        """Find exchange rate for a currency pair on a date.

        Args:
            from_currency: Source currency code.
            to_currency: Target currency code.
            target_date: Date for the rate.

        Returns:
            ExchangeRate if found, None otherwise.
        """
        for rate in self.rates:
            if rate.from_currency != from_currency:
                continue
            if rate.to_currency != to_currency:
                continue
            if rate.valid_from > target_date:
                continue
            if rate.valid_to is not None and rate.valid_to < target_date:
                continue
            return rate

        return None

    def reload(self) -> None:
        """Reload all configuration from disk.

        Useful after external changes to config files.
        """
        self.config = load_workspace_config(self.path)
        self._plans = None
        self._rates = None


def load_workspace(path: Path | None = None) -> Workspace:
    """Load a workspace from a directory.

    Args:
        path: Path to workspace directory. Uses current directory if None.

    Returns:
        Loaded Workspace instance.

    Raises:
        WorkspaceNotFoundError: If workspace.yaml not found.
    """
    workspace_path = path or Path.cwd()

    if not (workspace_path / WORKSPACE_CONFIG_FILE).exists():
        raise WorkspaceNotFoundError(str(workspace_path))

    return Workspace(workspace_path)


def find_workspace(start_path: Path | None = None) -> Workspace | None:
    """Find a workspace by searching up the directory tree.

    Args:
        start_path: Starting directory. Uses current directory if None.

    Returns:
        Workspace if found, None otherwise.
    """
    current = start_path or Path.cwd()

    while current != current.parent:
        if (current / WORKSPACE_CONFIG_FILE).exists():
            return Workspace(current)
        current = current.parent

    return None
