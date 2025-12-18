"""SQLite database connection and schema management."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from fintrack.core.exceptions import StorageError

# SQL schema for FinTrack tables
SCHEMA = """
-- Imported transactions
CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    date DATE NOT NULL,
    amount DECIMAL NOT NULL,
    currency TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    is_savings BOOLEAN DEFAULT FALSE,
    is_deduction BOOLEAN DEFAULT FALSE,
    is_fixed BOOLEAN DEFAULT FALSE,
    source_file TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, amount, currency, category, description)
);

CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);

-- Import log for idempotency
CREATE TABLE IF NOT EXISTS import_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL UNIQUE,
    records_imported INTEGER,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Period summary cache
CREATE TABLE IF NOT EXISTS period_summaries (
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    workspace_name TEXT NOT NULL,
    total_income DECIMAL,
    total_expenses DECIMAL,
    total_fixed_expenses DECIMAL,
    total_flexible_expenses DECIMAL,
    total_savings DECIMAL,
    total_deductions DECIMAL,
    expenses_by_category JSON,
    fixed_expenses_by_category JSON,
    flexible_expenses_by_category JSON,
    transaction_count INTEGER,
    last_transaction_date DATE,
    calculated_at TIMESTAMP,
    PRIMARY KEY (period_start, workspace_name)
);

-- Category analysis cache
CREATE TABLE IF NOT EXISTS category_analysis (
    period_start DATE NOT NULL,
    category TEXT NOT NULL,
    workspace_name TEXT NOT NULL,
    is_fixed BOOLEAN DEFAULT FALSE,
    actual_amount DECIMAL,
    planned_amount DECIMAL,
    historical_average DECIMAL,
    variance_vs_plan DECIMAL,
    variance_vs_history DECIMAL,
    share_of_spending_budget DECIMAL,
    share_of_total_expenses DECIMAL,
    calculated_at TIMESTAMP,
    PRIMARY KEY (period_start, category, workspace_name)
);
"""


class Database:
    """SQLite database manager with connection pooling.

    Manages database connections, schema initialization, and provides
    a context manager for safe transaction handling.
    """

    def __init__(self, db_path: Path) -> None:
        """Initialize database manager.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._ensure_directory()
        self._init_schema()

    def _ensure_directory(self) -> None:
        """Create database directory if it doesn't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Create a new database connection with proper settings."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_schema(self) -> None:
        """Initialize database schema if not exists."""
        try:
            with self.connection() as conn:
                conn.executescript(SCHEMA)
        except sqlite3.Error as e:
            raise StorageError("schema_init", str(e))

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Context manager for database connections.

        Yields:
            SQLite connection with automatic commit/rollback.

        Example:
            with db.connection() as conn:
                conn.execute("INSERT INTO ...")
        """
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Execute a query and return results.

        Args:
            sql: SQL query string.
            params: Query parameters.

        Returns:
            List of result rows.
        """
        with self.connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall()

    def execute_many(self, sql: str, params_list: list[tuple]) -> int:
        """Execute a query with multiple parameter sets.

        Args:
            sql: SQL query string with placeholders.
            params_list: List of parameter tuples.

        Returns:
            Number of rows affected.
        """
        with self.connection() as conn:
            cursor = conn.executemany(sql, params_list)
            return cursor.rowcount


def get_database(db_path: Path) -> Database:
    """Get a Database instance for the given path.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        Initialized Database instance.
    """
    return Database(db_path)
