"""Budget calculation engine.

Calculates budget projections from BudgetPlan configurations
and actual spending from transaction data.
"""

from datetime import date
from decimal import Decimal

from fintrack.core.models import (
    BudgetPlan,
    BudgetProjection,
    CategoryBudgetProjection,
    PeriodSummary,
    Transaction,
)
from fintrack.engine.periods import format_period, get_period_end
from fintrack.core.models import IntervalType


def calculate_budget_projection(
    plan: BudgetPlan,
    period_start: date,
    interval: IntervalType,
) -> BudgetProjection:
    """Calculate budget projection from a BudgetPlan.

    This is the "no historical data" scenario - pure projection
    based on plan configuration.

    Args:
        plan: BudgetPlan configuration.
        period_start: Start of the period.
        interval: Period interval type.

    Returns:
        BudgetProjection with all calculated values.
    """
    period_str = format_period(period_start, interval)

    # Separate fixed and flexible category budgets
    fixed_budgets = []
    flexible_budgets = []
    total_flexible = Decimal(0)

    for cb in plan.category_budgets:
        share = (
            cb.amount / plan.disposable_income * 100
            if plan.disposable_income > 0
            else Decimal(0)
        )
        projection = CategoryBudgetProjection(
            category=cb.category,
            amount=cb.amount,
            is_fixed=cb.is_fixed,
            share_of_budget=share.quantize(Decimal("0.1")),
        )

        if cb.is_fixed:
            fixed_budgets.append(projection)
        else:
            flexible_budgets.append(projection)
            total_flexible += cb.amount

    unallocated = plan.disposable_income - total_flexible

    return BudgetProjection(
        period=period_str,
        plan_id=plan.id,
        gross_income=plan.gross_income,
        total_deductions=plan.total_deductions,
        deductions_breakdown=list(plan.deductions),
        net_income=plan.net_income,
        total_fixed_expenses=plan.total_fixed_expenses,
        fixed_expenses_breakdown=list(plan.fixed_expenses),
        savings_base=plan.savings_base,
        savings_calculation_base=plan.savings_calculation_base,
        savings_rate=plan.savings_rate,
        savings_target=plan.savings_target,
        disposable_income=plan.disposable_income,
        fixed_category_budgets=fixed_budgets,
        flexible_category_budgets=flexible_budgets,
        total_allocated_flexible=total_flexible,
        unallocated_flexible=unallocated,
    )


def aggregate_transactions(
    transactions: list[Transaction],
    period_start: date,
    period_end: date,
    workspace_name: str,
    fixed_categories: set[str] | None = None,
) -> PeriodSummary:
    """Aggregate transactions for a period into a summary.

    Args:
        transactions: List of transactions to aggregate.
        period_start: Period start date.
        period_end: Period end date.
        workspace_name: Workspace name for the summary.
        fixed_categories: Set of category names that are considered fixed.

    Returns:
        PeriodSummary with aggregated data.
    """
    if fixed_categories is None:
        fixed_categories = set()

    total_income = Decimal(0)
    total_expenses = Decimal(0)
    total_fixed = Decimal(0)
    total_flexible = Decimal(0)
    total_savings = Decimal(0)
    total_deductions = Decimal(0)

    expenses_by_category: dict[str, Decimal] = {}
    fixed_by_category: dict[str, Decimal] = {}
    flexible_by_category: dict[str, Decimal] = {}

    last_date: date | None = None
    count = 0

    for tx in transactions:
        # Skip if outside period
        if tx.date < period_start or tx.date >= period_end:
            continue

        count += 1
        if last_date is None or tx.date > last_date:
            last_date = tx.date

        # Handle by type
        if tx.amount > 0 and not tx.is_deduction:
            # Income
            total_income += tx.amount

        elif tx.is_deduction:
            # Deduction from gross
            total_deductions += abs(tx.amount)

        elif tx.is_savings:
            # Savings transfer
            total_savings += abs(tx.amount)

        else:
            # Expense
            amount = abs(tx.amount)
            total_expenses += amount

            # Add to category totals
            cat = tx.category
            expenses_by_category[cat] = expenses_by_category.get(cat, Decimal(0)) + amount

            # Determine if fixed or flexible
            is_fixed = tx.is_fixed or cat in fixed_categories

            if is_fixed:
                total_fixed += amount
                fixed_by_category[cat] = fixed_by_category.get(cat, Decimal(0)) + amount
            else:
                total_flexible += amount
                flexible_by_category[cat] = flexible_by_category.get(cat, Decimal(0)) + amount

    return PeriodSummary(
        period_start=period_start,
        period_end=period_end,
        workspace_name=workspace_name,
        total_income=total_income,
        total_expenses=total_expenses,
        total_fixed_expenses=total_fixed,
        total_flexible_expenses=total_flexible,
        total_savings=total_savings,
        total_deductions=total_deductions,
        expenses_by_category=expenses_by_category,
        fixed_expenses_by_category=fixed_by_category,
        flexible_expenses_by_category=flexible_by_category,
        transaction_count=count,
        last_transaction_date=last_date,
    )


def calculate_variance(actual: Decimal, planned: Decimal | None) -> Decimal | None:
    """Calculate variance between actual and planned.

    Positive = under budget (good)
    Negative = over budget (bad)

    Args:
        actual: Actual amount spent.
        planned: Planned amount (None if not planned).

    Returns:
        Variance amount or None if no plan.
    """
    if planned is None:
        return None
    return planned - actual


def calculate_category_share(
    amount: Decimal,
    total: Decimal,
) -> Decimal:
    """Calculate category's share of total.

    Args:
        amount: Category amount.
        total: Total amount.

    Returns:
        Share as decimal (0.25 = 25%).
    """
    if total <= 0:
        return Decimal(0)
    return (amount / total).quantize(Decimal("0.0001"))
