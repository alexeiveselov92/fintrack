"""Pytest fixtures for FinTrack tests."""

import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from fintrack.core.models import (
    BudgetPlan,
    CategoryBudget,
    DeductionItem,
    FixedExpenseItem,
    SavingsBase,
    Transaction,
    WorkspaceConfig,
)


@pytest.fixture
def sample_transaction() -> Transaction:
    """Create a sample transaction for testing."""
    return Transaction(
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        currency="EUR",
        category="food",
        description="Grocery shopping",
    )


@pytest.fixture
def sample_income_transaction() -> Transaction:
    """Create a sample income transaction."""
    return Transaction(
        date=date(2024, 1, 10),
        amount=Decimal("5000.00"),
        currency="EUR",
        category="salary",
        description="Monthly salary",
    )


@pytest.fixture
def sample_deduction_transaction() -> Transaction:
    """Create a sample deduction transaction."""
    return Transaction(
        date=date(2024, 1, 10),
        amount=Decimal("-1000.00"),
        currency="EUR",
        category="tax",
        description="Income tax",
        is_deduction=True,
    )


@pytest.fixture
def sample_fixed_transaction() -> Transaction:
    """Create a sample fixed expense transaction."""
    return Transaction(
        date=date(2024, 1, 1),
        amount=Decimal("-800.00"),
        currency="EUR",
        category="housing",
        description="Monthly rent",
        is_fixed=True,
    )


@pytest.fixture
def sample_savings_transaction() -> Transaction:
    """Create a sample savings transaction."""
    return Transaction(
        date=date(2024, 1, 15),
        amount=Decimal("-500.00"),
        currency="EUR",
        category="savings",
        description="Monthly savings",
        is_savings=True,
    )


@pytest.fixture
def sample_budget_plan() -> BudgetPlan:
    """Create a sample budget plan for testing."""
    return BudgetPlan(
        id="test_plan_2024_01",
        valid_from=date(2024, 1, 1),
        valid_to=None,
        gross_income=Decimal("5000.00"),
        income_currency="EUR",
        deductions=[
            DeductionItem(name="income_tax", amount=Decimal("1000.00")),
            DeductionItem(name="social_security", amount=Decimal("200.00")),
        ],
        fixed_expenses=[
            FixedExpenseItem(name="rent", amount=Decimal("800.00"), category="housing"),
            FixedExpenseItem(name="utilities", amount=Decimal("150.00"), category="utilities"),
            FixedExpenseItem(name="internet", amount=Decimal("30.00"), category="subscriptions"),
        ],
        savings_rate=Decimal("0.20"),
        savings_base=SavingsBase.NET_INCOME,
        category_budgets=[
            CategoryBudget(category="housing", amount=Decimal("800.00"), is_fixed=True),
            CategoryBudget(category="utilities", amount=Decimal("150.00"), is_fixed=True),
            CategoryBudget(category="food", amount=Decimal("400.00")),
            CategoryBudget(category="transport", amount=Decimal("150.00")),
        ],
    )


@pytest.fixture
def sample_workspace_config() -> WorkspaceConfig:
    """Create a sample workspace configuration."""
    return WorkspaceConfig(
        name="test_workspace",
        description="Test workspace for unit tests",
        base_currency="EUR",
    )


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace directory structure."""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir()
    (workspace / "transactions").mkdir()
    (workspace / "plans").mkdir()
    (workspace / "reports").mkdir()
    (workspace / ".cache").mkdir()

    # Write workspace.yaml
    workspace_yaml = workspace / "workspace.yaml"
    workspace_yaml.write_text('''
name: "test_workspace"
description: "Test workspace"
interval: "month"
base_currency: "EUR"
''')

    return workspace
