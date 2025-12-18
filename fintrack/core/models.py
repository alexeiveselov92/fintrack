"""Domain models for FinTrack.

All financial data structures are defined here using Pydantic v2 for validation.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field, model_validator


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------


class SavingsBase(str, Enum):
    """Base for calculating savings target.

    NET_INCOME: Calculate savings from net income (before fixed expenses).
                More ambitious - motivates optimizing fixed costs.
    DISPOSABLE: Calculate savings from disposable income (after fixed expenses).
                More realistic when fixed costs cannot be reduced.
    """

    NET_INCOME = "net_income"
    DISPOSABLE = "disposable"


class IntervalType(str, Enum):
    """Period interval types for budget analysis."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    CUSTOM = "custom"


# -----------------------------------------------------------------------------
# Transaction Model
# -----------------------------------------------------------------------------


class Transaction(BaseModel):
    """A single financial transaction.

    Attributes:
        id: Unique identifier (auto-generated UUID).
        date: Transaction date.
        amount: Positive = income, negative = expense.
        currency: ISO 4217 currency code (EUR, USD, RSD).
        category: User-defined category string.
        description: Optional transaction description.
        is_savings: True if this is a savings deposit (tracked separately).
        is_deduction: True if this is a pre-income deduction (tax, social security).
        is_fixed: True if this is a fixed/recurring expense (rent, subscriptions).
        source_file: Original CSV filename for import tracking.
        created_at: Record creation timestamp.

    Flag Rules:
        - is_deduction and is_fixed are mutually exclusive.
        - is_savings can combine with others but typically used alone.
        - All flags False = flexible expense/income.
    """

    id: UUID = Field(default_factory=uuid4)
    date: date
    amount: Decimal
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    category: str = Field(min_length=1)
    description: str | None = None
    is_savings: bool = False
    is_deduction: bool = False
    is_fixed: bool = False
    source_file: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def validate_flags(self) -> "Transaction":
        """Ensure is_deduction and is_fixed are mutually exclusive."""
        if self.is_deduction and self.is_fixed:
            raise ValueError("is_deduction and is_fixed cannot both be True")
        return self


# -----------------------------------------------------------------------------
# Budget Plan Components
# -----------------------------------------------------------------------------


class DeductionItem(BaseModel):
    """A deduction from gross income (taxes, social security).

    These are taken BEFORE money reaches your account.
    """

    name: str = Field(min_length=1)
    amount: Annotated[Decimal, Field(ge=0)]


class FixedExpenseItem(BaseModel):
    """A fixed expense from net income (rent, subscriptions, loans).

    These are mandatory payments from your available money.
    """

    name: str = Field(min_length=1)
    amount: Annotated[Decimal, Field(ge=0)]
    category: str | None = None  # Optional link to transaction category


class CategoryBudget(BaseModel):
    """Planned budget for a specific category.

    If is_fixed=True, all transactions in this category are treated as fixed.
    """

    category: str = Field(min_length=1)
    amount: Annotated[Decimal, Field(ge=0)]
    is_fixed: bool = False


# -----------------------------------------------------------------------------
# Budget Plan Model
# -----------------------------------------------------------------------------


class BudgetPlan(BaseModel):
    """Financial configuration for a period.

    Contains income, deductions, fixed expenses, savings settings,
    and category budgets. Used to calculate disposable income and
    compare against actual spending.

    Income Flow:
        Gross Income
        - Deductions (taxes, before receiving money)
        = Net Income
        - Fixed Expenses (rent, subscriptions, mandatory)
        - Savings Target
        = Disposable Income (money you can actually spend freely)
    """

    id: str = Field(min_length=1)
    valid_from: date
    valid_to: date | None = None  # None = valid until next plan

    gross_income: Annotated[Decimal, Field(ge=0)]
    income_currency: str = Field(
        default="EUR", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$"
    )

    deductions: list[DeductionItem] = Field(default_factory=list)
    fixed_expenses: list[FixedExpenseItem] = Field(default_factory=list)

    savings_rate: Annotated[Decimal, Field(ge=0, le=1)] = Decimal("0.20")
    savings_base: SavingsBase = SavingsBase.NET_INCOME
    savings_amount: Annotated[Decimal, Field(ge=0)] | None = None  # Fixed amount (priority over rate)

    category_budgets: list[CategoryBudget] = Field(default_factory=list)

    @computed_field  # type: ignore[misc]
    @property
    def total_deductions(self) -> Decimal:
        """Sum of all deductions from gross income."""
        return sum((d.amount for d in self.deductions), Decimal(0))

    @computed_field  # type: ignore[misc]
    @property
    def net_income(self) -> Decimal:
        """Income after deductions (what you actually receive)."""
        return self.gross_income - self.total_deductions

    @computed_field  # type: ignore[misc]
    @property
    def total_fixed_expenses(self) -> Decimal:
        """Sum of all fixed/recurring expenses."""
        return sum((f.amount for f in self.fixed_expenses), Decimal(0))

    @computed_field  # type: ignore[misc]
    @property
    def savings_calculation_base(self) -> Decimal:
        """Base amount for savings calculation depending on settings."""
        if self.savings_base == SavingsBase.NET_INCOME:
            return self.net_income
        else:  # DISPOSABLE
            return self.net_income - self.total_fixed_expenses

    @computed_field  # type: ignore[misc]
    @property
    def savings_target(self) -> Decimal:
        """Target savings amount for the period."""
        if self.savings_amount is not None:
            return self.savings_amount
        return self.savings_calculation_base * self.savings_rate

    @computed_field  # type: ignore[misc]
    @property
    def disposable_income(self) -> Decimal:
        """Free money after fixed expenses and savings."""
        return self.net_income - self.total_fixed_expenses - self.savings_target

    @computed_field  # type: ignore[misc]
    @property
    def spending_budget(self) -> Decimal:
        """Alias for disposable_income."""
        return self.disposable_income

    @property
    def fixed_categories(self) -> set[str]:
        """Categories marked as fixed in category_budgets."""
        return {cb.category for cb in self.category_budgets if cb.is_fixed}


# -----------------------------------------------------------------------------
# Exchange Rate Model
# -----------------------------------------------------------------------------


class ExchangeRate(BaseModel):
    """Currency exchange rate for a period.

    Usage: amount_from * rate = amount_to
    Example: 100 EUR * 117.5 = 11750 RSD
    """

    from_currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    to_currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    rate: Annotated[Decimal, Field(gt=0)]
    valid_from: date
    valid_to: date | None = None


# -----------------------------------------------------------------------------
# Workspace Configuration
# -----------------------------------------------------------------------------


class WorkspaceConfig(BaseModel):
    """Configuration for a FinTrack workspace.

    A workspace is an isolated environment with its own transactions,
    plans, and settings. Similar to a dbt project.
    """

    name: str = Field(min_length=1)
    description: str | None = None

    interval: IntervalType = IntervalType.MONTH
    custom_interval_days: int | None = Field(default=None, ge=1)
    analysis_window: int = Field(default=3, ge=1)  # Periods for moving average

    base_currency: str = Field(
        default="EUR", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$"
    )
    display_currencies: list[str] = Field(default_factory=list)

    transactions_dir: str = "transactions"
    plans_dir: str = "plans"
    reports_dir: str = "reports"
    cache_db: str = ".cache/fintrack.db"

    @model_validator(mode="after")
    def validate_custom_interval(self) -> "WorkspaceConfig":
        """Ensure custom_interval_days is set when interval is CUSTOM."""
        if self.interval == IntervalType.CUSTOM and self.custom_interval_days is None:
            raise ValueError("custom_interval_days required when interval is 'custom'")
        return self


# -----------------------------------------------------------------------------
# Aggregated Data Models (for caching)
# -----------------------------------------------------------------------------


class PeriodSummary(BaseModel):
    """Aggregated transaction data for a period.

    Stored in cache for fast retrieval. Invalidated when
    transactions for the period change.
    """

    period_start: date
    period_end: date
    workspace_name: str

    # Actual figures
    total_income: Decimal = Decimal(0)
    total_expenses: Decimal = Decimal(0)  # All expenses
    total_fixed_expenses: Decimal = Decimal(0)  # is_fixed=True expenses
    total_flexible_expenses: Decimal = Decimal(0)  # Regular expenses
    total_savings: Decimal = Decimal(0)  # is_savings=True
    total_deductions: Decimal = Decimal(0)  # is_deduction=True

    # Category breakdown
    expenses_by_category: dict[str, Decimal] = Field(default_factory=dict)
    fixed_expenses_by_category: dict[str, Decimal] = Field(default_factory=dict)
    flexible_expenses_by_category: dict[str, Decimal] = Field(default_factory=dict)

    # Metadata
    transaction_count: int = 0
    last_transaction_date: date | None = None
    calculated_at: datetime = Field(default_factory=datetime.utcnow)


class CategoryAnalysis(BaseModel):
    """Analysis of a single category for a period.

    Compares actual spending against plan and historical average.
    """

    period_start: date
    category: str
    is_fixed: bool = False

    actual_amount: Decimal
    planned_amount: Decimal | None = None  # From BudgetPlan
    historical_average: Decimal | None = None  # Moving average

    # Variance (positive = under budget/savings, negative = over budget)
    variance_vs_plan: Decimal | None = None
    variance_vs_history: Decimal | None = None

    # Shares
    share_of_spending_budget: Decimal = Decimal(0)  # For flexible categories
    share_of_total_expenses: Decimal = Decimal(0)


# -----------------------------------------------------------------------------
# Budget Projection (output model)
# -----------------------------------------------------------------------------


class CategoryBudgetProjection(BaseModel):
    """Projected budget for a category."""

    category: str
    amount: Decimal
    is_fixed: bool
    share_of_budget: Decimal = Decimal(0)  # Share of disposable income


class BudgetProjection(BaseModel):
    """Complete budget projection for a period (no historical data).

    This is the output of the `budget` command when calculating
    expected budget from a BudgetPlan without actual transactions.
    """

    period: str  # "2024-01" or similar
    plan_id: str

    gross_income: Decimal
    total_deductions: Decimal
    deductions_breakdown: list[DeductionItem]
    net_income: Decimal

    total_fixed_expenses: Decimal
    fixed_expenses_breakdown: list[FixedExpenseItem]

    savings_base: SavingsBase
    savings_calculation_base: Decimal
    savings_rate: Decimal
    savings_target: Decimal

    disposable_income: Decimal

    fixed_category_budgets: list[CategoryBudgetProjection]
    flexible_category_budgets: list[CategoryBudgetProjection]

    total_allocated_flexible: Decimal
    unallocated_flexible: Decimal
