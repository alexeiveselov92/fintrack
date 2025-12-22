"""Dashboard data provider.

Collects and transforms all data needed for dashboard generation.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from fintrack.core.models import (
    BudgetPlan,
    CategoryAnalysis,
    DashboardData,
    IncomeExpenseFlow,
    IntervalType,
    PeriodDataPoint,
    PeriodSummary,
    Transaction,
)
from fintrack.engine.calculator import (
    aggregate_transactions,
    calculate_cash_on_hand,
    calculate_cumulative_balance,
    calculate_cumulative_savings,
    calculate_cumulative_savings_target,
    calculate_savings_surplus,
    calculate_true_discretionary,
    calculate_uncovered_savings,
    can_cover_savings_gap,
)
from fintrack.engine.periods import (
    format_period,
    get_current_period,
    get_period_end,
    get_period_start,
    iterate_periods,
)

if TYPE_CHECKING:
    from fintrack.core.workspace import Workspace


class DashboardDataProvider:
    """Provides all data needed for dashboard generation.

    Collects transactions, calculates metrics, and builds timeline
    data for the interactive dashboard.
    """

    def __init__(self, workspace: "Workspace"):
        """Initialize data provider.

        Args:
            workspace: The workspace to get data from.
        """
        self.ws = workspace
        self.tx_repo = workspace.storage.get_transaction_repository()

    def get_plan_for_date(self, target_date: date) -> BudgetPlan | None:
        """Get applicable plan for a date, returning None on error."""
        try:
            return self.ws.get_plan_for_date(target_date)
        except Exception:
            return None

    def get_dashboard_data(self, period_start: date | None = None) -> DashboardData:
        """Get complete dashboard data.

        Args:
            period_start: Start of the period to analyze. If None, uses current period.

        Returns:
            DashboardData with all metrics and timeline.
        """
        interval = self.ws.config.interval
        custom_days = self.ws.config.custom_interval_days
        currency = self.ws.config.base_currency

        # Determine current period
        if period_start is None:
            period_start, _ = get_current_period(interval, custom_days)

        period_end = get_period_end(period_start, interval, custom_days)
        period_label = format_period(period_start, interval)

        # Get all transactions
        all_transactions = self.tx_repo.get_all()

        if not all_transactions:
            # Return empty dashboard
            return DashboardData(
                workspace_name=self.ws.name,
                currency=currency,
                interval=interval,
                generated_at=datetime.now(),
                theme=self.ws.config.theme,
                current_period_label=period_label,
                current_period_start=period_start,
                current_period_end=period_end,
            )

        # Get first transaction date
        first_tx_date = min(tx.date for tx in all_transactions)

        # Get plan for current period
        plan = self.get_plan_for_date(period_start)
        fixed_categories = plan.fixed_categories if plan else set()

        # Calculate timeline data (from first transaction to current period)
        timeline = self._build_timeline(
            all_transactions=all_transactions,
            first_tx_date=first_tx_date,
            current_period_end=period_end,
            interval=interval,
            custom_days=custom_days,
            fixed_categories=fixed_categories,
        )

        # Get current period summary
        last_day_of_period = period_end - timedelta(days=1)
        current_summary = aggregate_transactions(
            transactions=all_transactions,
            period_start=period_start,
            period_end=period_end,
            workspace_name=self.ws.name,
            fixed_categories=fixed_categories,
        )

        # Calculate cumulative values for current period
        cumulative_savings = calculate_cumulative_savings(all_transactions, last_day_of_period)
        cumulative_balance = calculate_cumulative_balance(all_transactions, last_day_of_period)
        cash_on_hand = calculate_cash_on_hand(cumulative_balance, cumulative_savings)

        # Calculate cumulative savings target
        cumulative_target = calculate_cumulative_savings_target(
            period_end=last_day_of_period,
            first_transaction_date=first_tx_date,
            interval=interval,
            get_plan_for_date=self.get_plan_for_date,
            custom_days=custom_days,
        )

        savings_surplus = calculate_savings_surplus(cumulative_savings, cumulative_target)

        # Coverage indicator calculations
        uncovered = calculate_uncovered_savings(cumulative_target, cumulative_savings)
        can_cover = can_cover_savings_gap(cash_on_hand, uncovered)
        true_discretionary = calculate_true_discretionary(cash_on_hand, uncovered)

        # Calculate trend (compare to previous period)
        balance_prev = None
        balance_change_pct = None
        balance_change_direction = "flat"

        if len(timeline) >= 2:
            prev_point = timeline[-2]
            balance_prev = prev_point.cumulative_balance
            if balance_prev != Decimal(0):
                change = cumulative_balance - balance_prev
                balance_change_pct = (change / abs(balance_prev) * 100).quantize(Decimal("0.1"))
                if balance_change_pct > 0:
                    balance_change_direction = "up"
                elif balance_change_pct < 0:
                    balance_change_direction = "down"

        # Build category analyses
        categories = self._build_category_analyses(
            summary=current_summary,
            plan=plan,
            period_start=period_start,
        )

        # Build income/expense flows for Sankey
        flows = self._build_income_expense_flows(
            summary=current_summary,
            plan=plan,
        )

        # Build expense/income by category
        expenses_by_cat = dict(current_summary.expenses_by_category)
        income_by_cat: dict[str, Decimal] = {}

        # For income, group by category from transactions
        for tx in all_transactions:
            if tx.date < period_start or tx.date >= period_end:
                continue
            if tx.amount > 0 and not tx.is_savings:
                cat = tx.category
                income_by_cat[cat] = income_by_cat.get(cat, Decimal(0)) + tx.amount

        # Update current summary with cumulative values
        current_summary.cumulative_savings = cumulative_savings
        current_summary.cumulative_balance = cumulative_balance
        current_summary.cumulative_savings_target = cumulative_target
        current_summary.savings_surplus = savings_surplus
        current_summary.cash_on_hand = cash_on_hand

        # Filter transactions for current period only (FIX for bug where all periods were shown)
        period_transactions = [
            tx for tx in all_transactions
            if period_start <= tx.date < period_end
        ]

        return DashboardData(
            workspace_name=self.ws.name,
            currency=currency,
            interval=interval,
            generated_at=datetime.now(),
            theme=self.ws.config.theme,
            current_period_label=period_label,
            current_period_start=period_start,
            current_period_end=period_end,
            # KPIs
            current_balance=cumulative_balance,
            total_savings=cumulative_savings,
            available_funds=cash_on_hand,
            planned_savings=cumulative_target,
            savings_gap=cumulative_target - cumulative_savings,  # positive = behind
            # Coverage
            uncovered_savings=uncovered,
            can_cover=can_cover,
            true_discretionary=true_discretionary,
            # Trend
            balance_prev_period=balance_prev,
            balance_change_pct=balance_change_pct,
            balance_change_direction=balance_change_direction,
            # Timeline
            timeline=timeline,
            # Income & Expenses
            income_expense_flows=flows,
            expenses_by_category=expenses_by_cat,
            income_by_category=income_by_cat,
            # Budget
            categories=categories,
            plan=plan,
            current_period_summary=current_summary,
            # Transactions (filtered for current period only)
            transactions=period_transactions,
        )

    def _build_timeline(
        self,
        all_transactions: list[Transaction],
        first_tx_date: date,
        current_period_end: date,
        interval: IntervalType,
        custom_days: int | None,
        fixed_categories: set[str],
    ) -> list[PeriodDataPoint]:
        """Build timeline data from first transaction to current period.

        Args:
            all_transactions: All transactions.
            first_tx_date: Date of first transaction.
            current_period_end: End of current period.
            interval: Period interval type.
            custom_days: Custom interval days.
            fixed_categories: Set of fixed category names.

        Returns:
            List of PeriodDataPoint for each period.
        """
        timeline: list[PeriodDataPoint] = []

        # Start from the period containing the first transaction
        start_period = get_period_start(first_tx_date, interval, custom_days)

        for period_start, period_end in iterate_periods(
            start_period, current_period_end, interval, custom_days
        ):
            period_label = format_period(period_start, interval)
            last_day = period_end - timedelta(days=1)

            # Aggregate for this period
            summary = aggregate_transactions(
                transactions=all_transactions,
                period_start=period_start,
                period_end=period_end,
                workspace_name=self.ws.name,
                fixed_categories=fixed_categories,
            )

            # Calculate cumulative values up to this period
            cumulative_savings = calculate_cumulative_savings(all_transactions, last_day)
            cumulative_balance = calculate_cumulative_balance(all_transactions, last_day)
            cash_on_hand = calculate_cash_on_hand(cumulative_balance, cumulative_savings)

            # Calculate cumulative target
            cumulative_target = calculate_cumulative_savings_target(
                period_end=last_day,
                first_transaction_date=first_tx_date,
                interval=interval,
                get_plan_for_date=self.get_plan_for_date,
                custom_days=custom_days,
            )

            timeline.append(
                PeriodDataPoint(
                    period_label=period_label,
                    period_start=period_start,
                    period_end=period_end,
                    # Cumulative
                    cumulative_savings=cumulative_savings,
                    cumulative_balance=cumulative_balance,
                    cumulative_savings_target=cumulative_target,
                    available_funds=cash_on_hand,
                    # Period flow
                    income=summary.total_income,
                    expenses=summary.total_expenses,
                    net_flow=summary.total_income - summary.total_expenses,
                    savings_this_period=summary.total_savings,
                    deductions_this_period=summary.total_deductions,
                    # Fixed/flexible
                    fixed_expenses=summary.total_fixed_expenses,
                    flexible_expenses=summary.total_flexible_expenses,
                )
            )

        return timeline

    def _build_category_analyses(
        self,
        summary: PeriodSummary,
        plan: BudgetPlan | None,
        period_start: date,
    ) -> list[CategoryAnalysis]:
        """Build category analyses for current period.

        Args:
            summary: Period summary with category breakdown.
            plan: Budget plan (if any).
            period_start: Period start date.

        Returns:
            List of CategoryAnalysis.
        """
        analyses: list[CategoryAnalysis] = []
        spending_budget = plan.disposable_income if plan else Decimal(0)

        # Collect all categories
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

            # Get planned amount
            planned: Decimal | None = None
            if plan:
                for cb in plan.category_budgets:
                    if cb.category == category:
                        planned = cb.amount
                        break

            # Calculate variance
            variance_vs_plan = (planned - actual) if planned else None

            # Calculate shares
            share_of_budget = Decimal(0)
            if not is_fixed and spending_budget > 0:
                share_of_budget = actual / spending_budget

            share_of_total = Decimal(0)
            if summary.total_expenses > 0:
                share_of_total = actual / summary.total_expenses

            analyses.append(
                CategoryAnalysis(
                    period_start=period_start,
                    category=category,
                    is_fixed=is_fixed,
                    actual_amount=actual,
                    planned_amount=planned,
                    historical_average=None,  # Not computing history here
                    variance_vs_plan=variance_vs_plan,
                    variance_vs_history=None,
                    share_of_spending_budget=share_of_budget,
                    share_of_total_expenses=share_of_total,
                )
            )

        return analyses

    def _build_income_expense_flows(
        self,
        summary: PeriodSummary,
        plan: BudgetPlan | None,
    ) -> list[IncomeExpenseFlow]:
        """Build income/expense flow data for Sankey diagram.

        Shows flow from Gross Income -> Deductions -> Net Income ->
        Fixed/Flexible/Savings.

        Args:
            summary: Period summary with totals.
            plan: Budget plan (if any).

        Returns:
            List of IncomeExpenseFlow for Sankey.
        """
        flows: list[IncomeExpenseFlow] = []

        # Use plan values if available, otherwise use actual
        if plan:
            gross = plan.gross_income
            deductions = plan.total_deductions
            net = plan.net_income
        else:
            gross = summary.total_income + summary.total_deductions
            deductions = summary.total_deductions
            net = summary.total_income

        # Gross -> Deductions
        if deductions > 0:
            flows.append(IncomeExpenseFlow(
                source="Gross Income",
                target="Deductions",
                amount=deductions,
            ))

        # Gross -> Net (remainder after deductions)
        if net > 0:
            flows.append(IncomeExpenseFlow(
                source="Gross Income",
                target="Net Income",
                amount=net,
            ))

        # Net -> Fixed Expenses
        if summary.total_fixed_expenses > 0:
            flows.append(IncomeExpenseFlow(
                source="Net Income",
                target="Fixed Expenses",
                amount=summary.total_fixed_expenses,
            ))

        # Net -> Flexible Expenses
        if summary.total_flexible_expenses > 0:
            flows.append(IncomeExpenseFlow(
                source="Net Income",
                target="Flexible Expenses",
                amount=summary.total_flexible_expenses,
            ))

        # Net -> Savings
        if summary.total_savings > 0:
            flows.append(IncomeExpenseFlow(
                source="Net Income",
                target="Savings",
                amount=summary.total_savings,
            ))

        # Add category-level flows for expenses
        for category, amount in sorted(
            summary.fixed_expenses_by_category.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]:  # Top 5
            flows.append(IncomeExpenseFlow(
                source="Fixed Expenses",
                target=category,
                amount=amount,
            ))

        for category, amount in sorted(
            summary.flexible_expenses_by_category.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]:  # Top 5
            flows.append(IncomeExpenseFlow(
                source="Flexible Expenses",
                target=category,
                amount=amount,
            ))

        return flows

    def get_all_periods_data(self) -> dict[str, DashboardData]:
        """Get dashboard data for all periods with transactions.

        Returns:
            Dict mapping period label to DashboardData for that period.
        """
        interval = self.ws.config.interval
        custom_days = self.ws.config.custom_interval_days

        # Get all transactions
        all_transactions = self.tx_repo.get_all()
        if not all_transactions:
            return {}

        # Get first and last transaction dates
        first_tx_date = min(tx.date for tx in all_transactions)
        last_tx_date = max(tx.date for tx in all_transactions)

        # Get period boundaries
        first_period = get_period_start(first_tx_date, interval, custom_days)

        # Get current period (or last transaction period)
        current_period, current_end = get_current_period(interval, custom_days)
        if last_tx_date > current_end:
            # If there are future transactions, extend to include them
            last_period = get_period_start(last_tx_date, interval, custom_days)
        else:
            last_period = current_period

        # Generate data for each period
        all_data: dict[str, DashboardData] = {}

        for period_start, period_end in iterate_periods(
            first_period,
            get_period_end(last_period, interval, custom_days),
            interval,
            custom_days,
        ):
            period_label = format_period(period_start, interval)
            data = self.get_dashboard_data(period_start)
            all_data[period_label] = data

        return all_data
