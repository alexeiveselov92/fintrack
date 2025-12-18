"""SQLite implementation of TransactionRepository."""

import sqlite3
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fintrack.core.exceptions import StorageError
from fintrack.core.models import Transaction
from fintrack.storage.base import TransactionRepository
from fintrack.storage.sqlite.database import Database


class SQLiteTransactionRepository(TransactionRepository):
    """SQLite-based transaction storage."""

    def __init__(self, db: Database) -> None:
        """Initialize repository with database connection.

        Args:
            db: Database instance.
        """
        self.db = db

    def _row_to_transaction(self, row: sqlite3.Row) -> Transaction:
        """Convert database row to Transaction model."""
        return Transaction(
            id=UUID(row["id"]),
            date=date.fromisoformat(row["date"]),
            amount=Decimal(str(row["amount"])),
            currency=row["currency"],
            category=row["category"],
            description=row["description"],
            is_savings=bool(row["is_savings"]),
            is_deduction=bool(row["is_deduction"]),
            is_fixed=bool(row["is_fixed"]),
            source_file=row["source_file"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _transaction_to_params(self, tx: Transaction) -> tuple:
        """Convert Transaction to database parameters."""
        return (
            str(tx.id),
            tx.date.isoformat(),
            str(tx.amount),
            tx.currency,
            tx.category,
            tx.description,
            tx.is_savings,
            tx.is_deduction,
            tx.is_fixed,
            tx.source_file,
            tx.created_at.isoformat(),
        )

    def save(self, transaction: Transaction) -> None:
        """Save a single transaction."""
        sql = """
            INSERT OR IGNORE INTO transactions
            (id, date, amount, currency, category, description,
             is_savings, is_deduction, is_fixed, source_file, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self.db.connection() as conn:
                conn.execute(sql, self._transaction_to_params(transaction))
        except sqlite3.Error as e:
            raise StorageError("save_transaction", str(e))

    def save_batch(self, transactions: list[Transaction]) -> int:
        """Save multiple transactions, skipping duplicates."""
        if not transactions:
            return 0

        sql = """
            INSERT OR IGNORE INTO transactions
            (id, date, amount, currency, category, description,
             is_savings, is_deduction, is_fixed, source_file, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = [self._transaction_to_params(tx) for tx in transactions]

        try:
            with self.db.connection() as conn:
                cursor = conn.executemany(sql, params)
                return cursor.rowcount
        except sqlite3.Error as e:
            raise StorageError("save_batch", str(e))

    def get_by_period(self, start: date, end: date) -> list[Transaction]:
        """Get transactions within a date range."""
        sql = """
            SELECT * FROM transactions
            WHERE date >= ? AND date < ?
            ORDER BY date, created_at
        """
        try:
            rows = self.db.execute(sql, (start.isoformat(), end.isoformat()))
            return [self._row_to_transaction(row) for row in rows]
        except sqlite3.Error as e:
            raise StorageError("get_by_period", str(e))

    def get_by_category(
        self,
        category: str,
        start: date | None = None,
        end: date | None = None,
    ) -> list[Transaction]:
        """Get transactions by category with optional date filter."""
        if start and end:
            sql = """
                SELECT * FROM transactions
                WHERE category = ? AND date >= ? AND date < ?
                ORDER BY date
            """
            params: tuple = (category, start.isoformat(), end.isoformat())
        elif start:
            sql = """
                SELECT * FROM transactions
                WHERE category = ? AND date >= ?
                ORDER BY date
            """
            params = (category, start.isoformat())
        elif end:
            sql = """
                SELECT * FROM transactions
                WHERE category = ? AND date < ?
                ORDER BY date
            """
            params = (category, end.isoformat())
        else:
            sql = """
                SELECT * FROM transactions
                WHERE category = ?
                ORDER BY date
            """
            params = (category,)

        try:
            rows = self.db.execute(sql, params)
            return [self._row_to_transaction(row) for row in rows]
        except sqlite3.Error as e:
            raise StorageError("get_by_category", str(e))

    def exists(
        self,
        tx_date: date,
        amount: Decimal,
        currency: str,
        category: str,
        description: str | None,
    ) -> bool:
        """Check if a matching transaction exists."""
        if description:
            sql = """
                SELECT 1 FROM transactions
                WHERE date = ? AND amount = ? AND currency = ?
                AND category = ? AND description = ?
                LIMIT 1
            """
            params: tuple = (
                tx_date.isoformat(),
                str(amount),
                currency,
                category,
                description,
            )
        else:
            sql = """
                SELECT 1 FROM transactions
                WHERE date = ? AND amount = ? AND currency = ?
                AND category = ? AND description IS NULL
                LIMIT 1
            """
            params = (tx_date.isoformat(), str(amount), currency, category)

        try:
            rows = self.db.execute(sql, params)
            return len(rows) > 0
        except sqlite3.Error as e:
            raise StorageError("exists_check", str(e))

    def get_all_categories(self) -> list[str]:
        """Get all unique category names."""
        sql = "SELECT DISTINCT category FROM transactions ORDER BY category"
        try:
            rows = self.db.execute(sql)
            return [row["category"] for row in rows]
        except sqlite3.Error as e:
            raise StorageError("get_categories", str(e))

    def count(self) -> int:
        """Get total number of transactions."""
        sql = "SELECT COUNT(*) as cnt FROM transactions"
        try:
            rows = self.db.execute(sql)
            return int(rows[0]["cnt"])
        except sqlite3.Error as e:
            raise StorageError("count", str(e))
