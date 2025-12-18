"""Tests for Pydantic models."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from fintrack.core.models import (
    BudgetPlan,
    CategoryBudget,
    DeductionItem,
    ExchangeRate,
    FixedExpenseItem,
    IntervalType,
    SavingsBase,
    Transaction,
    WorkspaceConfig,
)


class TestTransaction:
    """Tests for Transaction model."""

    def test_create_basic_transaction(self) -> None:
        """Test creating a basic expense transaction."""
        tx = Transaction(
            date=date(2024, 1, 15),
            amount=Decimal("-50.00"),
            currency="EUR",
            category="food",
        )
        assert tx.amount == Decimal("-50.00")
        assert tx.is_savings is False
        assert tx.is_deduction is False
        assert tx.is_fixed is False

    def test_transaction_auto_id(self) -> None:
        """Test that UUID is auto-generated."""
        tx = Transaction(
            date=date(2024, 1, 15),
            amount=Decimal("-50.00"),
            currency="EUR",
            category="food",
        )
        assert tx.id is not None

    def test_transaction_flags_mutually_exclusive(self) -> None:
        """Test that is_deduction and is_fixed cannot both be True."""
        with pytest.raises(ValidationError) as exc_info:
            Transaction(
                date=date(2024, 1, 15),
                amount=Decimal("-100.00"),
                currency="EUR",
                category="test",
                is_deduction=True,
                is_fixed=True,
            )
        assert "cannot both be True" in str(exc_info.value)

    def test_transaction_savings_flag(self) -> None:
        """Test savings flag can be set independently."""
        tx = Transaction(
            date=date(2024, 1, 15),
            amount=Decimal("-500.00"),
            currency="EUR",
            category="savings",
            is_savings=True,
        )
        assert tx.is_savings is True
        assert tx.is_fixed is False

    def test_transaction_fixed_flag(self) -> None:
        """Test fixed expense flag."""
        tx = Transaction(
            date=date(2024, 1, 1),
            amount=Decimal("-800.00"),
            currency="EUR",
            category="housing",
            is_fixed=True,
        )
        assert tx.is_fixed is True
        assert tx.is_deduction is False

    def test_transaction_currency_validation(self) -> None:
        """Test currency code must be 3 uppercase letters."""
        with pytest.raises(ValidationError):
            Transaction(
                date=date(2024, 1, 15),
                amount=Decimal("-50.00"),
                currency="euro",  # lowercase
                category="food",
            )

    def test_transaction_category_required(self) -> None:
        """Test category is required and non-empty."""
        with pytest.raises(ValidationError):
            Transaction(
                date=date(2024, 1, 15),
                amount=Decimal("-50.00"),
                currency="EUR",
                category="",
            )


class TestBudgetPlan:
    """Tests for BudgetPlan model and calculations."""

    def test_budget_plan_basic(self, sample_budget_plan: BudgetPlan) -> None:
        """Test basic budget plan creation."""
        assert sample_budget_plan.gross_income == Decimal("5000.00")
        assert len(sample_budget_plan.deductions) == 2
        assert len(sample_budget_plan.fixed_expenses) == 3

    def test_total_deductions_calculation(self, sample_budget_plan: BudgetPlan) -> None:
        """Test total_deductions computed property."""
        # 1000 (tax) + 200 (social) = 1200
        assert sample_budget_plan.total_deductions == Decimal("1200.00")

    def test_net_income_calculation(self, sample_budget_plan: BudgetPlan) -> None:
        """Test net_income computed property."""
        # 5000 - 1200 = 3800
        assert sample_budget_plan.net_income == Decimal("3800.00")

    def test_total_fixed_expenses_calculation(self, sample_budget_plan: BudgetPlan) -> None:
        """Test total_fixed_expenses computed property."""
        # 800 (rent) + 150 (utilities) + 30 (internet) = 980
        assert sample_budget_plan.total_fixed_expenses == Decimal("980.00")

    def test_savings_target_from_net_income(self, sample_budget_plan: BudgetPlan) -> None:
        """Test savings target calculation from net income."""
        # savings_base = NET_INCOME, so base = 3800
        # 3800 * 0.20 = 760
        assert sample_budget_plan.savings_base == SavingsBase.NET_INCOME
        assert sample_budget_plan.savings_calculation_base == Decimal("3800.00")
        assert sample_budget_plan.savings_target == Decimal("760.00")

    def test_savings_target_from_disposable(self) -> None:
        """Test savings target calculation from disposable income."""
        plan = BudgetPlan(
            id="test",
            valid_from=date(2024, 1, 1),
            gross_income=Decimal("5000.00"),
            deductions=[DeductionItem(name="tax", amount=Decimal("1200.00"))],
            fixed_expenses=[FixedExpenseItem(name="rent", amount=Decimal("1000.00"))],
            savings_rate=Decimal("0.20"),
            savings_base=SavingsBase.DISPOSABLE,
        )
        # Net income: 5000 - 1200 = 3800
        # Disposable before savings: 3800 - 1000 = 2800
        # Savings: 2800 * 0.20 = 560
        assert plan.savings_calculation_base == Decimal("2800.00")
        assert plan.savings_target == Decimal("560.00")

    def test_disposable_income_calculation(self, sample_budget_plan: BudgetPlan) -> None:
        """Test disposable_income computed property."""
        # Net: 3800, Fixed: 980, Savings: 760
        # Disposable: 3800 - 980 - 760 = 2060
        assert sample_budget_plan.disposable_income == Decimal("2060.00")

    def test_spending_budget_alias(self, sample_budget_plan: BudgetPlan) -> None:
        """Test spending_budget is alias for disposable_income."""
        assert sample_budget_plan.spending_budget == sample_budget_plan.disposable_income

    def test_fixed_categories_property(self, sample_budget_plan: BudgetPlan) -> None:
        """Test fixed_categories returns correct set."""
        fixed = sample_budget_plan.fixed_categories
        assert "housing" in fixed
        assert "utilities" in fixed
        assert "food" not in fixed

    def test_savings_rate_validation(self) -> None:
        """Test savings rate must be between 0 and 1."""
        with pytest.raises(ValidationError):
            BudgetPlan(
                id="test",
                valid_from=date(2024, 1, 1),
                gross_income=Decimal("5000.00"),
                savings_rate=Decimal("1.5"),  # > 1
            )

    def test_savings_amount_overrides_rate(self) -> None:
        """Test savings_amount takes priority over savings_rate."""
        plan = BudgetPlan(
            id="test",
            valid_from=date(2024, 1, 1),
            gross_income=Decimal("5000.00"),
            savings_rate=Decimal("0.20"),  # Would be 1000 from 5000
            savings_amount=Decimal("500.00"),  # But this takes priority
        )
        assert plan.savings_target == Decimal("500.00")
        assert plan.disposable_income == Decimal("4500.00")  # 5000 - 500

    def test_savings_amount_none_uses_rate(self) -> None:
        """Test savings_rate is used when savings_amount is None."""
        plan = BudgetPlan(
            id="test",
            valid_from=date(2024, 1, 1),
            gross_income=Decimal("5000.00"),
            savings_rate=Decimal("0.10"),
            savings_amount=None,  # Explicit None
        )
        # 5000 * 0.10 = 500
        assert plan.savings_target == Decimal("500.00")


class TestExchangeRate:
    """Tests for ExchangeRate model."""

    def test_exchange_rate_basic(self) -> None:
        """Test basic exchange rate creation."""
        rate = ExchangeRate(
            from_currency="EUR",
            to_currency="RSD",
            rate=Decimal("117.5"),
            valid_from=date(2024, 1, 1),
        )
        assert rate.rate == Decimal("117.5")
        assert rate.valid_to is None

    def test_exchange_rate_positive(self) -> None:
        """Test rate must be positive."""
        with pytest.raises(ValidationError):
            ExchangeRate(
                from_currency="EUR",
                to_currency="RSD",
                rate=Decimal("0"),
                valid_from=date(2024, 1, 1),
            )


class TestWorkspaceConfig:
    """Tests for WorkspaceConfig model."""

    def test_workspace_config_defaults(self) -> None:
        """Test default values are applied."""
        config = WorkspaceConfig(name="test")
        assert config.interval == IntervalType.MONTH
        assert config.base_currency == "EUR"
        assert config.analysis_window == 3
        assert config.transactions_dir == "transactions"

    def test_workspace_custom_interval_requires_days(self) -> None:
        """Test custom interval requires custom_interval_days."""
        with pytest.raises(ValidationError) as exc_info:
            WorkspaceConfig(
                name="test",
                interval=IntervalType.CUSTOM,
                # missing custom_interval_days
            )
        assert "custom_interval_days required" in str(exc_info.value)

    def test_workspace_custom_interval_with_days(self) -> None:
        """Test custom interval with days specified."""
        config = WorkspaceConfig(
            name="test",
            interval=IntervalType.CUSTOM,
            custom_interval_days=14,
        )
        assert config.custom_interval_days == 14


class TestDeductionItem:
    """Tests for DeductionItem model."""

    def test_deduction_item_basic(self) -> None:
        """Test basic deduction item."""
        item = DeductionItem(name="tax", amount=Decimal("1000.00"))
        assert item.name == "tax"
        assert item.amount == Decimal("1000.00")

    def test_deduction_amount_non_negative(self) -> None:
        """Test amount cannot be negative."""
        with pytest.raises(ValidationError):
            DeductionItem(name="tax", amount=Decimal("-100.00"))


class TestFixedExpenseItem:
    """Tests for FixedExpenseItem model."""

    def test_fixed_expense_with_category(self) -> None:
        """Test fixed expense with category link."""
        item = FixedExpenseItem(
            name="rent",
            amount=Decimal("800.00"),
            category="housing",
        )
        assert item.category == "housing"

    def test_fixed_expense_without_category(self) -> None:
        """Test fixed expense without category is valid."""
        item = FixedExpenseItem(name="misc", amount=Decimal("50.00"))
        assert item.category is None


class TestCategoryBudget:
    """Tests for CategoryBudget model."""

    def test_category_budget_flexible(self) -> None:
        """Test flexible category budget (default)."""
        budget = CategoryBudget(category="food", amount=Decimal("400.00"))
        assert budget.is_fixed is False

    def test_category_budget_fixed(self) -> None:
        """Test fixed category budget."""
        budget = CategoryBudget(
            category="housing",
            amount=Decimal("800.00"),
            is_fixed=True,
        )
        assert budget.is_fixed is True
