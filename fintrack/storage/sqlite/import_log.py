"""SQLite implementation of ImportLogRepository."""

import sqlite3
from datetime import datetime

from fintrack.core.exceptions import StorageError
from fintrack.storage.base import ImportLogRepository
from fintrack.storage.sqlite.database import Database


class SQLiteImportLogRepository(ImportLogRepository):
    """SQLite-based import log for idempotent file imports."""

    def __init__(self, db: Database) -> None:
        """Initialize repository with database connection.

        Args:
            db: Database instance.
        """
        self.db = db

    def is_imported(self, file_hash: str) -> bool:
        """Check if a file has already been imported."""
        sql = "SELECT 1 FROM import_log WHERE file_hash = ? LIMIT 1"
        try:
            rows = self.db.execute(sql, (file_hash,))
            return len(rows) > 0
        except sqlite3.Error as e:
            raise StorageError("is_imported", str(e))

    def log_import(
        self, file_path: str, file_hash: str, records_count: int
    ) -> None:
        """Log a successful import."""
        sql = """
            INSERT INTO import_log (file_path, file_hash, records_imported, imported_at)
            VALUES (?, ?, ?, ?)
        """
        try:
            with self.db.connection() as conn:
                conn.execute(
                    sql,
                    (file_path, file_hash, records_count, datetime.utcnow().isoformat()),
                )
        except sqlite3.Error as e:
            raise StorageError("log_import", str(e))

    def get_imported_files(self) -> list[dict[str, str | int]]:
        """Get list of all imported files."""
        sql = """
            SELECT file_path, file_hash, records_imported, imported_at
            FROM import_log
            ORDER BY imported_at DESC
        """
        try:
            rows = self.db.execute(sql)
            return [
                {
                    "file_path": row["file_path"],
                    "file_hash": row["file_hash"],
                    "records_count": row["records_imported"],
                    "imported_at": row["imported_at"],
                }
                for row in rows
            ]
        except sqlite3.Error as e:
            raise StorageError("get_imported_files", str(e))
