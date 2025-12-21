"""Tests for calculator functions."""

from datetime import date
from decimal import Decimal

from fintrack.core.models import Transaction
from fintrack.engine.calculator import (
    aggregate_transactions,
    calculate_cumulative_balance,
    calculate_cumulative_savings,
)


class TestCalculateCumulativeSavings:
    """Tests for calculate_cumulative_savings function.

    Sign convention:
        - Positive amount = money deposited to savings
        - Negative amount = money withdrawn from savings
    """

    def test_empty_transactions(self) -> None:
        """Test with no transactions."""
        result = calculate_cumulative_savings([], date(2024, 1, 31))
        assert result == Decimal(0)

    def test_no_savings_transactions(self) -> None:
        """Test when no transactions have is_savings=True."""
        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                amount=Decimal("-50.00"),
                category="food",
            ),
            Transaction(
                date=date(2024, 1, 20),
                amount=Decimal("5000.00"),
                category="salary",
            ),
        ]
        result = calculate_cumulative_savings(transactions, date(2024, 1, 31))
        assert result == Decimal(0)

    def test_single_savings_deposit(self) -> None:
        """Test with a single savings deposit (positive amount)."""
        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                amount=Decimal("500.00"),  # Deposited to savings
                category="savings",
                is_savings=True,
            ),
        ]
        result = calculate_cumulative_savings(transactions, date(2024, 1, 31))
        assert result == Decimal("500.00")

    def test_single_savings_withdrawal(self) -> None:
        """Test with a single savings withdrawal (negative amount)."""
        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                amount=Decimal("-300.00"),  # Withdrew from savings
                category="savings",
                is_savings=True,
            ),
        ]
        result = calculate_cumulative_savings(transactions, date(2024, 1, 31))
        assert result == Decimal("-300.00")

    def test_multiple_savings_deposits(self) -> None:
        """Test with multiple savings deposits."""
        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                amount=Decimal("500.00"),
                category="savings",
                is_savings=True,
            ),
            Transaction(
                date=date(2024, 2, 15),
                amount=Decimal("600.00"),
                category="savings",
                is_savings=True,
            ),
            Transaction(
                date=date(2024, 3, 15),
                amount=Decimal("700.00"),
                category="savings",
                is_savings=True,
            ),
        ]
        result = calculate_cumulative_savings(transactions, date(2024, 3, 31))
        assert result == Decimal("1800.00")

    def test_deposits_and_withdrawals(self) -> None:
        """Test with mix of deposits and withdrawals."""
        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                amount=Decimal("1000.00"),  # Deposited
                category="savings",
                is_savings=True,
            ),
            Transaction(
                date=date(2024, 2, 15),
                amount=Decimal("-300.00"),  # Withdrew
                category="savings",
                is_savings=True,
            ),
            Transaction(
                date=date(2024, 3, 15),
                amount=Decimal("500.00"),  # Deposited
                category="savings",
                is_savings=True,
            ),
        ]
        # 1000 - 300 + 500 = 1200
        result = calculate_cumulative_savings(transactions, date(2024, 3, 31))
        assert result == Decimal("1200.00")

    def test_cumulative_up_to_date(self) -> None:
        """Test that only transactions up to given date are included."""
        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                amount=Decimal("500.00"),
                category="savings",
                is_savings=True,
            ),
            Transaction(
                date=date(2024, 2, 15),
                amount=Decimal("600.00"),
                category="savings",
                is_savings=True,
            ),
            Transaction(
                date=date(2024, 3, 15),
                amount=Decimal("700.00"),
                category="savings",
                is_savings=True,
            ),
        ]
        # Only include January and February
        result = calculate_cumulative_savings(transactions, date(2024, 2, 28))
        assert result == Decimal("1100.00")

    def test_includes_savings_on_exact_date(self) -> None:
        """Test that transaction on exact date is included."""
        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                amount=Decimal("500.00"),
                category="savings",
                is_savings=True,
            ),
            Transaction(
                date=date(2024, 1, 31),
                amount=Decimal("600.00"),
                category="savings",
                is_savings=True,
            ),
        ]
        result = calculate_cumulative_savings(transactions, date(2024, 1, 31))
        assert result == Decimal("1100.00")

    def test_excludes_future_savings(self) -> None:
        """Test that future transactions are excluded."""
        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                amount=Decimal("500.00"),
                category="savings",
                is_savings=True,
            ),
            Transaction(
                date=date(2024, 2, 15),
                amount=Decimal("600.00"),
                category="savings",
                is_savings=True,
            ),
        ]
        result = calculate_cumulative_savings(transactions, date(2024, 1, 31))
        assert result == Decimal("500.00")

    def test_mixed_transactions(self) -> None:
        """Test with mix of savings and non-savings transactions."""
        transactions = [
            Transaction(
                date=date(2024, 1, 10),
                amount=Decimal("5000.00"),
                category="salary",
            ),
            Transaction(
                date=date(2024, 1, 15),
                amount=Decimal("500.00"),  # Saved
                category="savings",
                is_savings=True,
            ),
            Transaction(
                date=date(2024, 1, 20),
                amount=Decimal("-100.00"),
                category="food",
            ),
            Transaction(
                date=date(2024, 2, 15),
                amount=Decimal("600.00"),  # Saved
                category="savings",
                is_savings=True,
            ),
            Transaction(
                date=date(2024, 2, 20),
                amount=Decimal("-200.00"),
                category="entertainment",
            ),
        ]
        result = calculate_cumulative_savings(transactions, date(2024, 2, 28))
        assert result == Decimal("1100.00")


class TestCalculateCumulativeBalance:
    """Tests for calculate_cumulative_balance function.

    Calculates income - expenses excluding savings transactions.
    """

    def test_empty_transactions(self) -> None:
        """Test with no transactions."""
        result = calculate_cumulative_balance([], date(2024, 1, 31))
        assert result == Decimal(0)

    def test_income_only(self) -> None:
        """Test with income only."""
        transactions = [
            Transaction(
                date=date(2024, 1, 10),
                amount=Decimal("5000.00"),
                category="salary",
            ),
        ]
        result = calculate_cumulative_balance(transactions, date(2024, 1, 31))
        assert result == Decimal("5000.00")

    def test_expenses_only(self) -> None:
        """Test with expenses only."""
        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                amount=Decimal("-100.00"),
                category="food",
            ),
            Transaction(
                date=date(2024, 1, 20),
                amount=Decimal("-200.00"),
                category="transport",
            ),
        ]
        result = calculate_cumulative_balance(transactions, date(2024, 1, 31))
        assert result == Decimal("-300.00")

    def test_income_minus_expenses(self) -> None:
        """Test balance calculation."""
        transactions = [
            Transaction(
                date=date(2024, 1, 10),
                amount=Decimal("5000.00"),
                category="salary",
            ),
            Transaction(
                date=date(2024, 1, 15),
                amount=Decimal("-100.00"),
                category="food",
            ),
            Transaction(
                date=date(2024, 1, 20),
                amount=Decimal("-200.00"),
                category="transport",
            ),
        ]
        # 5000 - 100 - 200 = 4700
        result = calculate_cumulative_balance(transactions, date(2024, 1, 31))
        assert result == Decimal("4700.00")

    def test_excludes_savings_transactions(self) -> None:
        """Test that is_savings transactions are excluded from balance."""
        transactions = [
            Transaction(
                date=date(2024, 1, 10),
                amount=Decimal("5000.00"),
                category="salary",
            ),
            Transaction(
                date=date(2024, 1, 15),
                amount=Decimal("1000.00"),  # Saved - should be excluded
                category="savings",
                is_savings=True,
            ),
            Transaction(
                date=date(2024, 1, 20),
                amount=Decimal("-100.00"),
                category="food",
            ),
        ]
        # 5000 - 100 = 4900 (savings excluded)
        result = calculate_cumulative_balance(transactions, date(2024, 1, 31))
        assert result == Decimal("4900.00")

    def test_excludes_savings_withdrawals(self) -> None:
        """Test that savings withdrawals are also excluded."""
        transactions = [
            Transaction(
                date=date(2024, 1, 10),
                amount=Decimal("5000.00"),
                category="salary",
            ),
            Transaction(
                date=date(2024, 1, 15),
                amount=Decimal("-500.00"),  # Withdrew from savings - excluded
                category="savings",
                is_savings=True,
            ),
            Transaction(
                date=date(2024, 1, 20),
                amount=Decimal("-100.00"),
                category="food",
            ),
        ]
        # 5000 - 100 = 4900 (savings withdrawal excluded)
        result = calculate_cumulative_balance(transactions, date(2024, 1, 31))
        assert result == Decimal("4900.00")

    def test_up_to_date(self) -> None:
        """Test cumulative up to specific date."""
        transactions = [
            Transaction(
                date=date(2024, 1, 10),
                amount=Decimal("5000.00"),
                category="salary",
            ),
            Transaction(
                date=date(2024, 1, 15),
                amount=Decimal("-100.00"),
                category="food",
            ),
            Transaction(
                date=date(2024, 2, 10),
                amount=Decimal("5000.00"),  # Future - excluded
                category="salary",
            ),
        ]
        # Only January: 5000 - 100 = 4900
        result = calculate_cumulative_balance(transactions, date(2024, 1, 31))
        assert result == Decimal("4900.00")


class TestAggregateTransactions:
    """Tests for aggregate_transactions function."""

    def test_empty_transactions(self) -> None:
        """Test with no transactions."""
        summary = aggregate_transactions(
            transactions=[],
            period_start=date(2024, 1, 1),
            period_end=date(2024, 2, 1),
            workspace_name="test",
        )
        assert summary.transaction_count == 0
        assert summary.total_income == Decimal(0)
        assert summary.total_expenses == Decimal(0)

    def test_basic_aggregation(self) -> None:
        """Test basic income/expense aggregation."""
        transactions = [
            Transaction(
                date=date(2024, 1, 10),
                amount=Decimal("5000.00"),
                category="salary",
            ),
            Transaction(
                date=date(2024, 1, 15),
                amount=Decimal("-100.00"),
                category="food",
            ),
            Transaction(
                date=date(2024, 1, 20),
                amount=Decimal("-50.00"),
                category="transport",
            ),
        ]
        summary = aggregate_transactions(
            transactions=transactions,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 2, 1),
            workspace_name="test",
        )
        assert summary.transaction_count == 3
        assert summary.total_income == Decimal("5000.00")
        assert summary.total_expenses == Decimal("150.00")

    def test_savings_tracked_separately(self) -> None:
        """Test that savings are tracked separately from expenses."""
        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                amount=Decimal("-500.00"),
                category="savings",
                is_savings=True,
            ),
            Transaction(
                date=date(2024, 1, 20),
                amount=Decimal("-100.00"),
                category="food",
            ),
        ]
        summary = aggregate_transactions(
            transactions=transactions,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 2, 1),
            workspace_name="test",
        )
        assert summary.total_savings == Decimal("500.00")
        assert summary.total_expenses == Decimal("100.00")
