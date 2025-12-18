"""Factory for creating storage repositories.

This factory provides a single point for creating all repository instances,
making it easy to swap storage backends in the future.
"""

from pathlib import Path

from fintrack.storage.base import (
    CacheRepository,
    ImportLogRepository,
    TransactionRepository,
)
from fintrack.storage.sqlite.cache import SQLiteCacheRepository
from fintrack.storage.sqlite.database import Database, get_database
from fintrack.storage.sqlite.import_log import SQLiteImportLogRepository
from fintrack.storage.sqlite.transactions import SQLiteTransactionRepository


class StorageFactory:
    """Factory for creating storage repository instances.

    Manages database connections and provides repository instances
    for a given workspace.
    """

    def __init__(self, db_path: Path) -> None:
        """Initialize factory with database path.

        Args:
            db_path: Path to the SQLite database file.
        """
        self._db = get_database(db_path)
        self._transaction_repo: TransactionRepository | None = None
        self._cache_repo: CacheRepository | None = None
        self._import_log_repo: ImportLogRepository | None = None

    @property
    def database(self) -> Database:
        """Get the underlying database instance."""
        return self._db

    def get_transaction_repository(self) -> TransactionRepository:
        """Get or create transaction repository instance.

        Returns:
            TransactionRepository implementation.
        """
        if self._transaction_repo is None:
            self._transaction_repo = SQLiteTransactionRepository(self._db)
        return self._transaction_repo

    def get_cache_repository(self) -> CacheRepository:
        """Get or create cache repository instance.

        Returns:
            CacheRepository implementation.
        """
        if self._cache_repo is None:
            self._cache_repo = SQLiteCacheRepository(self._db)
        return self._cache_repo

    def get_import_log_repository(self) -> ImportLogRepository:
        """Get or create import log repository instance.

        Returns:
            ImportLogRepository implementation.
        """
        if self._import_log_repo is None:
            self._import_log_repo = SQLiteImportLogRepository(self._db)
        return self._import_log_repo


def create_storage(db_path: Path) -> StorageFactory:
    """Create a storage factory for the given database path.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        Configured StorageFactory instance.

    Example:
        storage = create_storage(Path(".cache/fintrack.db"))
        tx_repo = storage.get_transaction_repository()
    """
    return StorageFactory(db_path)
