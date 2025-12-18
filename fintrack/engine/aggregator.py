"""Transaction aggregation and analysis engine.

Aggregates transactions by period, calculates moving averages,
and performs variance analysis against budget plans.
"""

from datetime import date
from decimal import Decimal
from typing import Sequence

from fintrack.core.models import (
    BudgetPlan,
    CategoryAnalysis,
    IntervalType,
    PeriodSummary,
    Transaction,
)
from fintrack.engine.calculator import aggregate_transactions, calculate_variance
from fintrack.engine.periods import get_period_end, get_previous_periods


def get_period_summary(
    transactions: list[Transaction],
    period_start: date,
    interval: IntervalType,
    workspace_name: str,
    plan: BudgetPlan | None = None,
    custom_days: int | None = None,
) -> PeriodSummary:
    """Get aggregated summary for a period.

    Args:
        transactions: All transactions (will be filtered by period).
        period_start: Start of period.
        interval: Period interval type.
        workspace_name: Workspace name.
        plan: Optional BudgetPlan for determining fixed categories.
        custom_days: Days for custom interval.

    Returns:
        Aggregated PeriodSummary.
    """
    period_end = get_period_end(period_start, interval, custom_days)
    fixed_categories = plan.fixed_categories if plan else set()

    return aggregate_transactions(
        transactions=transactions,
        period_start=period_start,
        period_end=period_end,
        workspace_name=workspace_name,
        fixed_categories=fixed_categories,
    )


def calculate_moving_average(
    category: str,
    period_summaries: Sequence[PeriodSummary],
    is_fixed: bool = False,
) -> Decimal | None:
    """Calculate moving average for a category across periods.

    Args:
        category: Category name.
        period_summaries: List of PeriodSummary objects.
        is_fixed: Whether to use fixed or flexible expenses.

    Returns:
        Average amount or None if no data.
    """
    amounts = []

    for summary in period_summaries:
        if is_fixed:
            amount = summary.fixed_expenses_by_category.get(category, Decimal(0))
        else:
            amount = summary.flexible_expenses_by_category.get(category, Decimal(0))

        if amount > 0:
            amounts.append(amount)

    if not amounts:
        return None

    return sum(amounts) / len(amounts)


def analyze_category(
    category: str,
    actual_amount: Decimal,
    is_fixed: bool,
    plan: BudgetPlan | None,
    historical_average: Decimal | None,
    spending_budget: Decimal,
    total_expenses: Decimal,
    period_start: date,
) -> CategoryAnalysis:
    """Analyze a single category.

    Args:
        category: Category name.
        actual_amount: Actual amount spent.
        is_fixed: Whether category is fixed.
        plan: BudgetPlan for getting planned amount.
        historical_average: Moving average from previous periods.
        spending_budget: Total disposable income.
        total_expenses: Total expenses for share calculation.
        period_start: Period start date.

    Returns:
        CategoryAnalysis with all calculations.
    """
    # Get planned amount from plan
    planned_amount: Decimal | None = None
    if plan:
        for cb in plan.category_budgets:
            if cb.category == category:
                planned_amount = cb.amount
                break

    # Calculate variances
    variance_vs_plan = calculate_variance(actual_amount, planned_amount)
    variance_vs_history = calculate_variance(actual_amount, historical_average)

    # Calculate shares
    share_of_budget = Decimal(0)
    if not is_fixed and spending_budget > 0:
        share_of_budget = actual_amount / spending_budget

    share_of_total = Decimal(0)
    if total_expenses > 0:
        share_of_total = actual_amount / total_expenses

    return CategoryAnalysis(
        period_start=period_start,
        category=category,
        is_fixed=is_fixed,
        actual_amount=actual_amount,
        planned_amount=planned_amount,
        historical_average=historical_average,
        variance_vs_plan=variance_vs_plan,
        variance_vs_history=variance_vs_history,
        share_of_spending_budget=share_of_budget,
        share_of_total_expenses=share_of_total,
    )


def analyze_period(
    transactions: list[Transaction],
    period_start: date,
    interval: IntervalType,
    workspace_name: str,
    plan: BudgetPlan | None,
    historical_summaries: list[PeriodSummary] | None = None,
    custom_days: int | None = None,
) -> tuple[PeriodSummary, list[CategoryAnalysis]]:
    """Perform full analysis of a period.

    Args:
        transactions: All transactions.
        period_start: Start of period to analyze.
        interval: Period interval type.
        workspace_name: Workspace name.
        plan: BudgetPlan for the period.
        historical_summaries: Previous period summaries for averages.
        custom_days: Days for custom interval.

    Returns:
        Tuple of (PeriodSummary, list of CategoryAnalysis).
    """
    # Get current period summary
    summary = get_period_summary(
        transactions=transactions,
        period_start=period_start,
        interval=interval,
        workspace_name=workspace_name,
        plan=plan,
        custom_days=custom_days,
    )

    # Calculate spending budget
    spending_budget = plan.disposable_income if plan else Decimal(0)

    # Analyze each category
    analyses: list[CategoryAnalysis] = []

    # Get all categories (from summary and plan)
    all_categories = set(summary.expenses_by_category.keys())
    if plan:
        for cb in plan.category_budgets:
            all_categories.add(cb.category)

    for category in sorted(all_categories):
        # Determine if fixed
        is_fixed = category in summary.fixed_expenses_by_category
        if plan and category in plan.fixed_categories:
            is_fixed = True

        # Get actual amount
        if is_fixed:
            actual = summary.fixed_expenses_by_category.get(category, Decimal(0))
        else:
            actual = summary.flexible_expenses_by_category.get(category, Decimal(0))

        # Calculate historical average
        historical_avg: Decimal | None = None
        if historical_summaries:
            historical_avg = calculate_moving_average(
                category, historical_summaries, is_fixed
            )

        analysis = analyze_category(
            category=category,
            actual_amount=actual,
            is_fixed=is_fixed,
            plan=plan,
            historical_average=historical_avg,
            spending_budget=spending_budget,
            total_expenses=summary.total_expenses,
            period_start=period_start,
        )
        analyses.append(analysis)

    return summary, analyses


def get_historical_summaries(
    transactions: list[Transaction],
    period_start: date,
    window: int,
    interval: IntervalType,
    workspace_name: str,
    plan: BudgetPlan | None = None,
    custom_days: int | None = None,
) -> list[PeriodSummary]:
    """Get summaries for previous periods (for moving average).

    Args:
        transactions: All transactions.
        period_start: Current period start.
        window: Number of previous periods.
        interval: Period interval type.
        workspace_name: Workspace name.
        plan: BudgetPlan for fixed categories.
        custom_days: Days for custom interval.

    Returns:
        List of PeriodSummary for previous periods.
    """
    previous_starts = get_previous_periods(period_start, window, interval, custom_days)
    summaries = []

    for prev_start in previous_starts:
        summary = get_period_summary(
            transactions=transactions,
            period_start=prev_start,
            interval=interval,
            workspace_name=workspace_name,
            plan=plan,
            custom_days=custom_days,
        )
        if summary.transaction_count > 0:
            summaries.append(summary)

    return summaries
