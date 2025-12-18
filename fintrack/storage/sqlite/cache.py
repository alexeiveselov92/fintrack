"""SQLite implementation of CacheRepository."""

import json
import sqlite3
from datetime import date, datetime
from decimal import Decimal

from fintrack.core.exceptions import StorageError
from fintrack.core.models import CategoryAnalysis, PeriodSummary
from fintrack.storage.base import CacheRepository
from fintrack.storage.sqlite.database import Database


class SQLiteCacheRepository(CacheRepository):
    """SQLite-based cache for aggregated data."""

    def __init__(self, db: Database) -> None:
        """Initialize repository with database connection.

        Args:
            db: Database instance.
        """
        self.db = db

    def _parse_decimal_dict(self, json_str: str | None) -> dict[str, Decimal]:
        """Parse JSON string to dict with Decimal values."""
        if not json_str:
            return {}
        data = json.loads(json_str)
        return {k: Decimal(str(v)) for k, v in data.items()}

    def _serialize_decimal_dict(self, data: dict[str, Decimal]) -> str:
        """Serialize dict with Decimal values to JSON string."""
        return json.dumps({k: str(v) for k, v in data.items()})

    def get_period_summary(
        self, period_start: date, workspace: str
    ) -> PeriodSummary | None:
        """Get cached period summary."""
        sql = """
            SELECT * FROM period_summaries
            WHERE period_start = ? AND workspace_name = ?
        """
        try:
            rows = self.db.execute(sql, (period_start.isoformat(), workspace))
            if not rows:
                return None

            row = rows[0]
            return PeriodSummary(
                period_start=date.fromisoformat(row["period_start"]),
                period_end=date.fromisoformat(row["period_end"]),
                workspace_name=row["workspace_name"],
                total_income=Decimal(str(row["total_income"] or 0)),
                total_expenses=Decimal(str(row["total_expenses"] or 0)),
                total_fixed_expenses=Decimal(str(row["total_fixed_expenses"] or 0)),
                total_flexible_expenses=Decimal(str(row["total_flexible_expenses"] or 0)),
                total_savings=Decimal(str(row["total_savings"] or 0)),
                total_deductions=Decimal(str(row["total_deductions"] or 0)),
                expenses_by_category=self._parse_decimal_dict(
                    row["expenses_by_category"]
                ),
                fixed_expenses_by_category=self._parse_decimal_dict(
                    row["fixed_expenses_by_category"]
                ),
                flexible_expenses_by_category=self._parse_decimal_dict(
                    row["flexible_expenses_by_category"]
                ),
                transaction_count=row["transaction_count"] or 0,
                last_transaction_date=(
                    date.fromisoformat(row["last_transaction_date"])
                    if row["last_transaction_date"]
                    else None
                ),
                calculated_at=datetime.fromisoformat(row["calculated_at"]),
            )
        except sqlite3.Error as e:
            raise StorageError("get_period_summary", str(e))

    def save_period_summary(self, summary: PeriodSummary) -> None:
        """Save period summary to cache."""
        sql = """
            INSERT OR REPLACE INTO period_summaries
            (period_start, period_end, workspace_name, total_income, total_expenses,
             total_fixed_expenses, total_flexible_expenses, total_savings,
             total_deductions, expenses_by_category, fixed_expenses_by_category,
             flexible_expenses_by_category, transaction_count, last_transaction_date,
             calculated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self.db.connection() as conn:
                conn.execute(
                    sql,
                    (
                        summary.period_start.isoformat(),
                        summary.period_end.isoformat(),
                        summary.workspace_name,
                        str(summary.total_income),
                        str(summary.total_expenses),
                        str(summary.total_fixed_expenses),
                        str(summary.total_flexible_expenses),
                        str(summary.total_savings),
                        str(summary.total_deductions),
                        self._serialize_decimal_dict(summary.expenses_by_category),
                        self._serialize_decimal_dict(summary.fixed_expenses_by_category),
                        self._serialize_decimal_dict(summary.flexible_expenses_by_category),
                        summary.transaction_count,
                        (
                            summary.last_transaction_date.isoformat()
                            if summary.last_transaction_date
                            else None
                        ),
                        summary.calculated_at.isoformat(),
                    ),
                )
        except sqlite3.Error as e:
            raise StorageError("save_period_summary", str(e))

    def get_category_analysis(
        self, period_start: date, category: str, workspace: str
    ) -> CategoryAnalysis | None:
        """Get cached category analysis."""
        sql = """
            SELECT * FROM category_analysis
            WHERE period_start = ? AND category = ? AND workspace_name = ?
        """
        try:
            rows = self.db.execute(
                sql, (period_start.isoformat(), category, workspace)
            )
            if not rows:
                return None

            row = rows[0]
            return CategoryAnalysis(
                period_start=date.fromisoformat(row["period_start"]),
                category=row["category"],
                is_fixed=bool(row["is_fixed"]),
                actual_amount=Decimal(str(row["actual_amount"])),
                planned_amount=(
                    Decimal(str(row["planned_amount"]))
                    if row["planned_amount"]
                    else None
                ),
                historical_average=(
                    Decimal(str(row["historical_average"]))
                    if row["historical_average"]
                    else None
                ),
                variance_vs_plan=(
                    Decimal(str(row["variance_vs_plan"]))
                    if row["variance_vs_plan"]
                    else None
                ),
                variance_vs_history=(
                    Decimal(str(row["variance_vs_history"]))
                    if row["variance_vs_history"]
                    else None
                ),
                share_of_spending_budget=Decimal(
                    str(row["share_of_spending_budget"] or 0)
                ),
                share_of_total_expenses=Decimal(
                    str(row["share_of_total_expenses"] or 0)
                ),
            )
        except sqlite3.Error as e:
            raise StorageError("get_category_analysis", str(e))

    def save_category_analysis(
        self, analysis: CategoryAnalysis, workspace: str
    ) -> None:
        """Save category analysis to cache."""
        sql = """
            INSERT OR REPLACE INTO category_analysis
            (period_start, category, workspace_name, is_fixed, actual_amount,
             planned_amount, historical_average, variance_vs_plan, variance_vs_history,
             share_of_spending_budget, share_of_total_expenses, calculated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self.db.connection() as conn:
                conn.execute(
                    sql,
                    (
                        analysis.period_start.isoformat(),
                        analysis.category,
                        workspace,
                        analysis.is_fixed,
                        str(analysis.actual_amount),
                        str(analysis.planned_amount) if analysis.planned_amount else None,
                        (
                            str(analysis.historical_average)
                            if analysis.historical_average
                            else None
                        ),
                        (
                            str(analysis.variance_vs_plan)
                            if analysis.variance_vs_plan
                            else None
                        ),
                        (
                            str(analysis.variance_vs_history)
                            if analysis.variance_vs_history
                            else None
                        ),
                        str(analysis.share_of_spending_budget),
                        str(analysis.share_of_total_expenses),
                        datetime.utcnow().isoformat(),
                    ),
                )
        except sqlite3.Error as e:
            raise StorageError("save_category_analysis", str(e))

    def invalidate_period(self, period_start: date, workspace: str) -> None:
        """Invalidate cache for a specific period."""
        try:
            with self.db.connection() as conn:
                conn.execute(
                    "DELETE FROM period_summaries WHERE period_start = ? AND workspace_name = ?",
                    (period_start.isoformat(), workspace),
                )
                conn.execute(
                    "DELETE FROM category_analysis WHERE period_start = ? AND workspace_name = ?",
                    (period_start.isoformat(), workspace),
                )
        except sqlite3.Error as e:
            raise StorageError("invalidate_period", str(e))

    def invalidate_all(self, workspace: str) -> None:
        """Invalidate all cached data for a workspace."""
        try:
            with self.db.connection() as conn:
                conn.execute(
                    "DELETE FROM period_summaries WHERE workspace_name = ?",
                    (workspace,),
                )
                conn.execute(
                    "DELETE FROM category_analysis WHERE workspace_name = ?",
                    (workspace,),
                )
        except sqlite3.Error as e:
            raise StorageError("invalidate_all", str(e))
