"""Budget calculation engine.

Calculates budget projections from BudgetPlan configurations
and actual spending from transaction data.
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from fintrack.core.models import (
    BudgetPlan,
    BudgetProjection,
    CategoryBudgetProjection,
    IntervalType,
    PeriodSummary,
    Transaction,
)
from fintrack.engine.periods import format_period, get_period_end, get_period_start

if TYPE_CHECKING:
    from collections.abc import Callable


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
        if tx.is_savings:
            # Savings transfer (positive = deposit, negative = withdrawal)
            total_savings += tx.amount

        elif tx.is_deduction:
            # Deduction from gross
            total_deductions += abs(tx.amount)

        elif tx.amount > 0:
            # Income
            total_income += tx.amount

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


def calculate_cumulative_savings(
    transactions: list[Transaction],
    up_to_date: date,
) -> Decimal:
    """Calculate total savings from beginning up to given date (inclusive).

    Sums all is_savings=True transactions from the start of time
    up to and including the specified date.

    Sign convention:
        - Positive amount = money deposited to savings
        - Negative amount = money withdrawn from savings

    Args:
        transactions: All transactions to consider.
        up_to_date: End date (inclusive) for calculation.

    Returns:
        Total cumulative savings amount (can be negative if more withdrawn than deposited).
    """
    return sum(
        (tx.amount for tx in transactions if tx.is_savings and tx.date <= up_to_date),
        Decimal(0),
    )


def calculate_cumulative_balance(
    transactions: list[Transaction],
    up_to_date: date,
) -> Decimal:
    """Calculate cumulative balance (income - expenses) excluding savings transactions.

    This shows how much "cash flow" money has accumulated over time,
    ignoring savings transfers which are tracked separately.

    Args:
        transactions: All transactions to consider.
        up_to_date: End date (inclusive) for calculation.

    Returns:
        Cumulative balance (positive = surplus, negative = deficit).
    """
    balance = Decimal(0)
    for tx in transactions:
        if tx.date > up_to_date:
            continue
        if tx.is_savings:
            continue  # Exclude savings transfers
        balance += tx.amount  # Income positive, expenses negative
    return balance


def calculate_cash_on_hand(
    cumulative_balance: Decimal,
    cumulative_savings: Decimal,
) -> Decimal:
    """Calculate cash on hand (money not in savings account).

    This represents money available for spending that hasn't been
    transferred to savings.

    Args:
        cumulative_balance: Total income - expenses (excluding savings transfers).
        cumulative_savings: Total savings deposits - withdrawals.

    Returns:
        Cash on hand (can be negative if overspent).
    """
    return cumulative_balance - cumulative_savings


def calculate_savings_surplus(
    cumulative_savings: Decimal,
    cumulative_target: Decimal,
) -> Decimal:
    """Calculate savings surplus/deficit vs cumulative target.

    Positive = ahead of savings plan (saved more than required).
    Negative = behind savings plan (saved less than required).

    Args:
        cumulative_savings: Total savings accumulated.
        cumulative_target: Total savings that should have been accumulated.

    Returns:
        Surplus (positive) or deficit (negative).
    """
    return cumulative_savings - cumulative_target


def calculate_cumulative_savings_target(
    period_end: date,
    first_transaction_date: date,
    interval: IntervalType,
    get_plan_for_date: "Callable[[date], BudgetPlan | None]",
    custom_days: int | None = None,
) -> Decimal:
    """Calculate cumulative savings target from first transaction to period end.

    Iterates through all periods from the first transaction date up to
    (and including) the given period, summing savings_target from applicable plans.

    Args:
        period_end: End date of current period (inclusive).
        first_transaction_date: Date of first transaction in workspace.
        interval: Period interval type.
        get_plan_for_date: Function to get applicable plan for a date.
        custom_days: Custom interval days if interval is CUSTOM.

    Returns:
        Total savings target for all periods up to and including current.
    """
    total_target = Decimal(0)

    # Start from the period containing the first transaction
    current_start = get_period_start(first_transaction_date, interval, custom_days)

    while current_start <= period_end:
        try:
            plan = get_plan_for_date(current_start)
            if plan:
                total_target += plan.savings_target
        except Exception:
            # No plan for this period, skip
            pass

        # Move to next period
        current_end = get_period_end(current_start, interval, custom_days)
        current_start = current_end

    return total_target


def calculate_uncovered_savings(
    cumulative_savings_target: Decimal,
    cumulative_savings: Decimal,
) -> Decimal:
    """Calculate uncovered savings (shortfall vs target).

    This represents how much savings the user still needs to accumulate
    to meet their cumulative target. Returns 0 if target is met or exceeded.

    Args:
        cumulative_savings_target: Total required savings by now.
        cumulative_savings: Total actual savings accumulated.

    Returns:
        Uncovered amount (>= 0). Zero means target is met.
    """
    return max(Decimal(0), cumulative_savings_target - cumulative_savings)


def calculate_true_discretionary(
    cash_on_hand: Decimal,
    uncovered_savings: Decimal,
) -> Decimal:
    """Calculate true discretionary funds available.

    This represents money that can truly be spent freely without
    jeopardizing savings goals. If uncovered_savings is positive,
    that amount should ideally be transferred to savings first.

    Args:
        cash_on_hand: Available cash not in savings.
        uncovered_savings: Amount still needed to meet savings target.

    Returns:
        True discretionary amount (can be negative if cash insufficient).
    """
    return cash_on_hand - uncovered_savings


def can_cover_savings_gap(
    cash_on_hand: Decimal,
    uncovered_savings: Decimal,
) -> bool:
    """Check if cash on hand can cover the savings gap.

    Args:
        cash_on_hand: Available cash not in savings.
        uncovered_savings: Amount still needed to meet savings target.

    Returns:
        True if cash is sufficient to cover the gap.
    """
    return cash_on_hand >= uncovered_savings
