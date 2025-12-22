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
        amount: Amount in workspace base_currency (for calculations).
        original_amount: Original amount if different currency (optional).
        original_currency: Original currency code if different from base (optional).
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

    Currency Handling:
        - amount is ALWAYS in workspace base_currency.
        - original_amount/original_currency store the original values if different.
        - If transaction was in base_currency, original_* fields are None.
    """

    id: UUID = Field(default_factory=uuid4)
    date: date
    amount: Decimal  # Always in workspace base_currency
    original_amount: Decimal | None = None  # Original amount if different currency
    original_currency: str | None = Field(
        default=None, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$"
    )
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

    # All amounts are in workspace base_currency
    gross_income: Annotated[Decimal, Field(ge=0)]

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
    total_savings: Decimal = Decimal(0)  # is_savings=True (current period)
    cumulative_savings: Decimal = Decimal(0)  # All-time savings up to period end
    cumulative_balance: Decimal = Decimal(0)  # All-time income - expenses (excl. savings)
    total_deductions: Decimal = Decimal(0)  # is_deduction=True

    # New computed metrics (v0.2.5+)
    cumulative_savings_target: Decimal = Decimal(0)  # Sum of savings_target from all periods
    savings_surplus: Decimal = Decimal(0)  # cumulative_savings - cumulative_target (+ = ahead, - = behind)
    cash_on_hand: Decimal = Decimal(0)  # cumulative_balance - cumulative_savings (money not in savings)

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


# -----------------------------------------------------------------------------
# Dashboard Data Models (v0.3.0+)
# -----------------------------------------------------------------------------


class PeriodDataPoint(BaseModel):
    """A single data point on the dashboard timeline.

    Contains cumulative and period-specific values for one period.
    Used for charts showing progression over time.
    """

    period_label: str  # "2024-12" or period-specific format
    period_start: date
    period_end: date

    # Cumulative values (up to end of this period)
    cumulative_savings: Decimal = Decimal(0)
    cumulative_balance: Decimal = Decimal(0)
    cumulative_savings_target: Decimal = Decimal(0)
    available_funds: Decimal = Decimal(0)  # = cash_on_hand

    # Period-specific flow
    income: Decimal = Decimal(0)
    expenses: Decimal = Decimal(0)
    net_flow: Decimal = Decimal(0)  # income - expenses
    savings_this_period: Decimal = Decimal(0)
    deductions_this_period: Decimal = Decimal(0)

    # Fixed vs flexible breakdown
    fixed_expenses: Decimal = Decimal(0)
    flexible_expenses: Decimal = Decimal(0)


class IncomeExpenseFlow(BaseModel):
    """Income/expense flow data for Sankey diagram.

    Represents a flow from source to target with an amount.
    """

    source: str  # "Gross Income", "Net Income", category name
    target: str  # "Net Income", "Savings", category name
    amount: Decimal


class DashboardData(BaseModel):
    """Complete data container for dashboard generation.

    Contains all metrics, timeline data, and transaction details
    needed to render the 5-tab interactive dashboard.
    """

    # Metadata
    workspace_name: str
    currency: str
    interval: IntervalType
    generated_at: datetime

    # Current period info
    current_period_label: str
    current_period_start: date
    current_period_end: date

    # ===== Overview KPIs =====
    current_balance: Decimal = Decimal(0)  # cumulative_balance
    total_savings: Decimal = Decimal(0)  # cumulative_savings
    available_funds: Decimal = Decimal(0)  # cash_on_hand
    planned_savings: Decimal = Decimal(0)  # cumulative_savings_target
    savings_gap: Decimal = Decimal(0)  # = planned - actual (positive = behind)

    # Coverage Indicator (new in v0.3.0)
    uncovered_savings: Decimal = Decimal(0)  # max(0, target - actual)
    can_cover: bool = True  # cash_on_hand >= uncovered_savings
    true_discretionary: Decimal = Decimal(0)  # cash_on_hand - uncovered_savings

    # Trend
    balance_prev_period: Decimal | None = None
    balance_change_pct: Decimal | None = None
    balance_change_direction: str = "flat"  # "up" | "down" | "flat"

    # ===== Timeline Data =====
    timeline: list[PeriodDataPoint] = Field(default_factory=list)

    # ===== Income & Expenses =====
    income_expense_flows: list[IncomeExpenseFlow] = Field(default_factory=list)
    expenses_by_category: dict[str, Decimal] = Field(default_factory=dict)
    income_by_category: dict[str, Decimal] = Field(default_factory=dict)

    # ===== Budget =====
    categories: list[CategoryAnalysis] = Field(default_factory=list)
    plan: BudgetPlan | None = None

    # Period summary for current period
    current_period_summary: PeriodSummary | None = None

    # ===== Transactions =====
    transactions: list[Transaction] = Field(default_factory=list)
