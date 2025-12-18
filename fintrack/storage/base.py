"""Abstract repository interfaces for FinTrack storage layer.

These interfaces define the contract for data access. Concrete implementations
(SQLite, PostgreSQL, etc.) must implement these interfaces.

This abstraction allows swapping storage backends without changing business logic.
"""

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from fintrack.core.models import CategoryAnalysis, PeriodSummary, Transaction


class TransactionRepository(ABC):
    """Abstract repository for transaction storage and retrieval."""

    @abstractmethod
    def save(self, transaction: Transaction) -> None:
        """Save a single transaction.

        Args:
            transaction: Transaction to save.

        Raises:
            StorageError: If save operation fails.
        """
        ...

    @abstractmethod
    def save_batch(self, transactions: list[Transaction]) -> int:
        """Save multiple transactions in a batch.

        Args:
            transactions: List of transactions to save.

        Returns:
            Number of transactions successfully saved (excluding duplicates).

        Raises:
            StorageError: If batch save fails.
        """
        ...

    @abstractmethod
    def get_by_period(self, start: date, end: date) -> list[Transaction]:
        """Get all transactions within a date range.

        Args:
            start: Start date (inclusive).
            end: End date (exclusive).

        Returns:
            List of transactions in the period.
        """
        ...

    @abstractmethod
    def get_by_category(
        self,
        category: str,
        start: date | None = None,
        end: date | None = None,
    ) -> list[Transaction]:
        """Get transactions by category, optionally filtered by date.

        Args:
            category: Category name to filter by.
            start: Optional start date (inclusive).
            end: Optional end date (exclusive).

        Returns:
            List of matching transactions.
        """
        ...

    @abstractmethod
    def exists(
        self,
        tx_date: date,
        amount: Decimal,
        currency: str,
        category: str,
        description: str | None,
    ) -> bool:
        """Check if a transaction already exists (for deduplication).

        Args:
            tx_date: Transaction date.
            amount: Transaction amount.
            currency: Currency code.
            category: Category name.
            description: Optional description.

        Returns:
            True if a matching transaction exists.
        """
        ...

    @abstractmethod
    def get_all_categories(self) -> list[str]:
        """Get all unique category names.

        Returns:
            Sorted list of unique categories.
        """
        ...

    @abstractmethod
    def count(self) -> int:
        """Get total number of transactions.

        Returns:
            Total transaction count.
        """
        ...


class CacheRepository(ABC):
    """Abstract repository for caching aggregated data."""

    @abstractmethod
    def get_period_summary(
        self, period_start: date, workspace: str
    ) -> PeriodSummary | None:
        """Get cached period summary.

        Args:
            period_start: Start date of the period.
            workspace: Workspace name.

        Returns:
            Cached PeriodSummary or None if not cached.
        """
        ...

    @abstractmethod
    def save_period_summary(self, summary: PeriodSummary) -> None:
        """Save period summary to cache.

        Args:
            summary: PeriodSummary to cache.
        """
        ...

    @abstractmethod
    def get_category_analysis(
        self, period_start: date, category: str, workspace: str
    ) -> CategoryAnalysis | None:
        """Get cached category analysis.

        Args:
            period_start: Start date of the period.
            category: Category name.
            workspace: Workspace name.

        Returns:
            Cached CategoryAnalysis or None if not cached.
        """
        ...

    @abstractmethod
    def save_category_analysis(self, analysis: CategoryAnalysis, workspace: str) -> None:
        """Save category analysis to cache.

        Args:
            analysis: CategoryAnalysis to cache.
            workspace: Workspace name.
        """
        ...

    @abstractmethod
    def invalidate_period(self, period_start: date, workspace: str) -> None:
        """Invalidate cache for a specific period.

        Args:
            period_start: Start date of the period to invalidate.
            workspace: Workspace name.
        """
        ...

    @abstractmethod
    def invalidate_all(self, workspace: str) -> None:
        """Invalidate all cached data for a workspace.

        Args:
            workspace: Workspace name.
        """
        ...


class ImportLogRepository(ABC):
    """Abstract repository for tracking imported files."""

    @abstractmethod
    def is_imported(self, file_hash: str) -> bool:
        """Check if a file has already been imported.

        Args:
            file_hash: SHA256 hash of the file content.

        Returns:
            True if the file was previously imported.
        """
        ...

    @abstractmethod
    def log_import(
        self, file_path: str, file_hash: str, records_count: int
    ) -> None:
        """Log a successful import.

        Args:
            file_path: Path to the imported file.
            file_hash: SHA256 hash of the file content.
            records_count: Number of records imported.
        """
        ...

    @abstractmethod
    def get_imported_files(self) -> list[dict[str, str | int]]:
        """Get list of all imported files.

        Returns:
            List of dicts with file_path, file_hash, records_count, imported_at.
        """
        ...
