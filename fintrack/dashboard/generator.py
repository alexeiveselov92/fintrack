"""HTML dashboard generator with Plotly charts.

Generates a standalone HTML file with interactive charts and tables.
"""

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from fintrack.core.models import DashboardData, IntervalType


def _decimal_to_float(obj):
    """Convert Decimal to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _format_currency(amount: Decimal, currency: str) -> str:
    """Format currency for display."""
    symbols = {"EUR": "\u20ac", "USD": "$", "GBP": "\u00a3", "RSD": "RSD "}
    symbol = symbols.get(currency, f"{currency} ")
    if amount < 0:
        return f"-{symbol}{abs(amount):,.2f}"
    return f"{symbol}{amount:,.2f}"


def _get_coverage_icon(can_cover: bool) -> str:
    """Get coverage indicator icon."""
    return "\u2713" if can_cover else "\u26a0"


def _get_coverage_text(data: DashboardData, currency: str) -> str:
    """Get coverage indicator text."""
    if data.uncovered_savings == 0:
        return "All savings targets are met!"
    if data.can_cover:
        return f"You can cover the savings gap of {_format_currency(data.uncovered_savings, currency)}"
    return f"Cannot cover savings gap of {_format_currency(data.uncovered_savings, currency)} with available {_format_currency(data.available_funds, currency)}"


def _get_interval_label(interval: IntervalType) -> str:
    """Get human-readable interval label."""
    labels = {
        IntervalType.DAY: "Day",
        IntervalType.WEEK: "Week",
        IntervalType.MONTH: "Month",
        IntervalType.QUARTER: "Quarter",
        IntervalType.YEAR: "Year",
        IntervalType.CUSTOM: "Period",
    }
    return labels.get(interval, "Period")


def generate_dashboard_html(data: DashboardData) -> str:
    """Generate complete dashboard HTML.

    Args:
        data: DashboardData with all metrics and timeline.

    Returns:
        Complete HTML string.
    """
    currency = data.currency
    interval_label = _get_interval_label(data.interval)

    # Prepare timeline data for charts
    timeline_labels = [p.period_label for p in data.timeline]
    timeline_savings = [float(p.cumulative_savings) for p in data.timeline]
    timeline_balance = [float(p.cumulative_balance) for p in data.timeline]
    timeline_available = [float(p.available_funds) for p in data.timeline]
    timeline_target = [float(p.cumulative_savings_target) for p in data.timeline]
    timeline_income = [float(p.income) for p in data.timeline]
    timeline_expenses = [float(p.expenses) for p in data.timeline]
    timeline_net = [float(p.net_flow) for p in data.timeline]
    timeline_fixed = [float(p.fixed_expenses) for p in data.timeline]
    timeline_flexible = [float(p.flexible_expenses) for p in data.timeline]

    # Prepare category data for charts
    expense_cats = sorted(
        data.expenses_by_category.items(),
        key=lambda x: x[1],
        reverse=True,
    )
    expense_labels = [c[0] for c in expense_cats]
    expense_values = [float(c[1]) for c in expense_cats]

    # Prepare Sankey data
    sankey_nodes = []
    sankey_source = []
    sankey_target = []
    sankey_value = []
    node_map: dict[str, int] = {}

    for flow in data.income_expense_flows:
        if flow.source not in node_map:
            node_map[flow.source] = len(sankey_nodes)
            sankey_nodes.append(flow.source)
        if flow.target not in node_map:
            node_map[flow.target] = len(sankey_nodes)
            sankey_nodes.append(flow.target)

        sankey_source.append(node_map[flow.source])
        sankey_target.append(node_map[flow.target])
        sankey_value.append(float(flow.amount))

    # Prepare budget data
    fixed_cats = [c for c in data.categories if c.is_fixed and c.actual_amount > 0]
    flexible_cats = [c for c in data.categories if not c.is_fixed and c.actual_amount > 0]

    # Prepare transactions data (most recent first, limit to 100)
    transactions_data = []
    for tx in sorted(data.transactions, key=lambda x: x.date, reverse=True)[:100]:
        transactions_data.append({
            "date": tx.date.isoformat(),
            "category": tx.category,
            "amount": float(tx.amount),
            "description": tx.description or "",
            "is_savings": tx.is_savings,
            "is_deduction": tx.is_deduction,
            "is_fixed": tx.is_fixed,
        })

    # Pre-compute savings transactions for Savings tab
    savings_rows_html, savings_total = _render_savings_transactions(data.transactions, currency)
    savings_total_formatted = _format_currency(savings_total, currency)
    savings_total_class = "positive" if savings_total >= 0 else "negative"

    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="{data.theme}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FinTrack Dashboard - {data.workspace_name}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        :root {{
            --primary: #2563eb;
            --primary-light: #3b82f6;
            --success: #16a34a;
            --warning: #ca8a04;
            --danger: #dc2626;
            --gray-50: #f9fafb;
            --gray-100: #f3f4f6;
            --gray-200: #e5e7eb;
            --gray-300: #d1d5db;
            --gray-500: #6b7280;
            --gray-600: #4b5563;
            --gray-700: #374151;
            --gray-800: #1f2937;
            --gray-900: #111827;
            --bg-primary: #ffffff;
            --bg-secondary: #f9fafb;
            --text-primary: #1f2937;
            --text-secondary: #6b7280;
            --border-color: #e5e7eb;
            --card-bg: #ffffff;
            --card-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        [data-theme="dark"] {{
            --primary: #3b82f6;
            --primary-light: #60a5fa;
            --success: #22c55e;
            --warning: #eab308;
            --danger: #ef4444;
            --gray-50: #0d0f12;
            --gray-100: #141619;
            --gray-200: #1e2126;
            --gray-300: #2c3039;
            --gray-500: #9ca3af;
            --gray-600: #d1d5db;
            --gray-700: #e5e7eb;
            --gray-800: #f3f4f6;
            --gray-900: #f9fafb;
            --bg-primary: #0d0f12;
            --bg-secondary: #141619;
            --text-primary: #d8d9da;
            --text-secondary: #8b8d8f;
            --border-color: #2c3039;
            --card-bg: #1e2126;
            --card-shadow: 0 1px 3px rgba(0,0,0,0.5);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.5;
            color: var(--text-primary);
            background: var(--bg-secondary);
        }}
        .header {{
            background: var(--card-bg);
            border-bottom: 1px solid var(--border-color);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ color: var(--primary); font-size: 1.5rem; }}
        .header .meta {{ color: var(--text-secondary); font-size: 0.875rem; }}

        .tabs {{
            background: var(--card-bg);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            padding: 0 2rem;
            gap: 0;
        }}
        .tab {{
            padding: 1rem 1.5rem;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            color: var(--text-secondary);
            font-weight: 500;
            transition: all 0.2s;
        }}
        .tab:hover {{ color: var(--primary); }}
        .tab.active {{
            color: var(--primary);
            border-bottom-color: var(--primary);
        }}

        .content {{ padding: 2rem; max-width: 1400px; margin: 0 auto; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}

        .cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: var(--card-shadow);
        }}
        .card-label {{ font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 0.25rem; }}
        .card-value {{ font-size: 1.75rem; font-weight: 600; }}
        .card-value.positive {{ color: var(--success); }}
        .card-value.negative {{ color: var(--danger); }}
        .card-trend {{ font-size: 0.875rem; margin-top: 0.5rem; }}
        .card-trend.up {{ color: var(--success); }}
        .card-trend.down {{ color: var(--danger); }}

        .coverage-indicator {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: var(--card-shadow);
            margin-bottom: 2rem;
        }}
        .coverage-indicator.ok {{ border-left: 4px solid var(--success); }}
        .coverage-indicator.warning {{ border-left: 4px solid var(--danger); }}
        .coverage-title {{ font-weight: 600; margin-bottom: 0.5rem; }}
        .coverage-status {{ display: flex; align-items: center; gap: 0.5rem; }}
        .coverage-status .icon {{ font-size: 1.5rem; }}
        .coverage-status.ok .icon {{ color: var(--success); }}
        .coverage-status.warning .icon {{ color: var(--danger); }}

        .chart-container {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: var(--card-shadow);
            margin-bottom: 2rem;
        }}
        .chart-title {{ font-size: 1rem; font-weight: 600; margin-bottom: 1rem; color: var(--text-primary); }}

        .section-title {{
            font-size: 1.25rem;
            font-weight: 600;
            margin: 2rem 0 1rem;
            color: var(--text-primary);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--card-bg);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: var(--card-shadow);
            margin-bottom: 2rem;
        }}
        th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--border-color); }}
        th {{ background: var(--bg-secondary); font-weight: 600; color: var(--text-primary); }}
        td.number {{ text-align: right; font-variant-numeric: tabular-nums; }}
        tr:last-child td {{ border-bottom: none; }}
        .positive {{ color: var(--success); }}
        .negative {{ color: var(--danger); }}

        .budget-bar {{
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 0.75rem;
        }}
        .budget-bar .label {{ width: 150px; font-weight: 500; color: var(--text-primary); }}
        .budget-bar .bar-container {{
            flex: 1;
            height: 24px;
            background: var(--border-color);
            border-radius: 4px;
            overflow: hidden;
            position: relative;
        }}
        .budget-bar .bar {{
            height: 100%;
            transition: width 0.3s;
        }}
        .budget-bar .bar.ok {{ background: var(--success); }}
        .budget-bar .bar.warning {{ background: var(--warning); }}
        .budget-bar .bar.danger {{ background: var(--danger); }}
        .budget-bar .bar.exceeded {{ background: #8b5cf6; }}
        .budget-bar .value {{ width: 200px; text-align: right; font-variant-numeric: tabular-nums; font-size: 0.9rem; }}
        .budget-bar .value .actual {{ font-weight: 600; }}
        .budget-bar .value .planned {{ color: var(--text-secondary); }}
        .budget-bar .value .diff {{ font-size: 0.8rem; margin-left: 0.25rem; }}
        .budget-bar .value .diff.positive {{ color: var(--success); }}
        .budget-bar .value .diff.negative {{ color: var(--danger); }}
        .budget-bar .value .diff.exceeded {{ color: #8b5cf6; }}
        .budget-badge {{
            display: inline-block;
            padding: 0.125rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
            margin-left: 0.5rem;
        }}
        .budget-badge.exceeded {{ background: #ede9fe; color: #6b21a8; }}
        .budget-badge.under {{ background: #dcfce7; color: #166534; }}
        .budget-badge.over {{ background: #fee2e2; color: #991b1b; }}

        .cash-reconciliation {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: var(--card-shadow);
            margin-bottom: 2rem;
        }}
        .cash-input-row {{
            display: flex;
            gap: 1rem;
            margin-bottom: 0.5rem;
            align-items: center;
        }}
        .cash-input-row input {{
            padding: 0.5rem;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            background: var(--bg-secondary);
            color: var(--text-primary);
        }}
        .cash-input-row input[type="text"] {{ flex: 1; }}
        .cash-input-row input[type="number"] {{ width: 150px; }}
        .cash-input-row button {{
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }}
        .btn-add {{ background: var(--primary); color: white; }}
        .btn-remove {{ background: var(--border-color); color: var(--text-secondary); }}
        .cash-total {{
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            font-weight: 600;
        }}
        .cash-comparison {{ margin-top: 0.5rem; }}

        .filters {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
            flex-wrap: wrap;
        }}
        .filters select, .filters input {{
            padding: 0.5rem;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            background: var(--bg-secondary);
            color: var(--text-primary);
        }}

        .export-btn {{
            background: var(--primary);
            color: white;
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }}

        .flag {{ display: inline-block; padding: 0.125rem 0.5rem; border-radius: 4px; font-size: 0.75rem; margin-left: 0.25rem; }}
        .flag.savings {{ background: #dbeafe; color: #1e40af; }}
        .flag.deduction {{ background: #fef3c7; color: #92400e; }}
        .flag.fixed {{ background: #f3e8ff; color: #6b21a8; }}

        .filter-summary {{
            padding: 0.75rem 1rem;
            background: var(--bg-secondary);
            border-radius: 8px;
            margin-bottom: 1rem;
            display: flex;
            gap: 2rem;
            align-items: center;
        }}
        .filter-summary .stat {{ font-weight: 500; }}
        .filter-summary .stat-value {{ font-weight: 600; color: var(--primary); }}

        .section-block {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: var(--card-shadow);
            border-left: 4px solid var(--primary);
        }}
        .section-block.historical {{
            border-left-color: #6366f1;
        }}
        .section-block.current-period {{
            border-left-color: var(--success);
        }}
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }}
        .section-header h3 {{
            margin: 0;
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-primary);
        }}
        .section-badge {{
            display: inline-block;
            font-size: 0.7rem;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .section-badge.historical {{
            background: #e0e7ff;
            color: #3730a3;
        }}
        .section-badge.current {{
            background: #d1fae5;
            color: #065f46;
        }}
        [data-theme="dark"] .section-badge.historical {{
            background: #312e81;
            color: #c7d2fe;
        }}
        [data-theme="dark"] .section-badge.current {{
            background: #064e3b;
            color: #a7f3d0;
        }}

        .period-selector {{
            display: flex;
            gap: 1rem;
            align-items: center;
            margin-bottom: 2rem;
        }}
        .period-selector select {{
            padding: 0.5rem 1rem;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            font-size: 1rem;
            background: var(--bg-secondary);
            color: var(--text-primary);
        }}

        @media (max-width: 768px) {{
            .tabs {{ overflow-x: auto; }}
            .tab {{ white-space: nowrap; }}
            .cards {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>FinTrack Dashboard</h1>
        <div class="meta">
            {data.workspace_name} &bull; {data.current_period_label} &bull;
            Generated: {data.generated_at.strftime('%Y-%m-%d %H:%M')}
        </div>
    </div>

    <div class="tabs">
        <div class="tab active" data-tab="overview">Overview</div>
        <div class="tab" data-tab="income-expenses">Income & Expenses</div>
        <div class="tab" data-tab="savings">Savings</div>
        <div class="tab" data-tab="budget">Budget</div>
        <div class="tab" data-tab="transactions">Transactions</div>
    </div>

    <div class="content">
        <!-- ===== OVERVIEW TAB ===== -->
        <div id="overview" class="tab-content active">
            <div class="cards">
                <div class="card">
                    <div class="card-label">Current Balance</div>
                    <div class="card-value">{_format_currency(data.current_balance, currency)}</div>
                    {_render_trend(data.balance_change_pct, data.balance_change_direction)}
                </div>
                <div class="card">
                    <div class="card-label">Total Savings</div>
                    <div class="card-value{' positive' if data.total_savings > 0 else ''}">{_format_currency(data.total_savings, currency)}</div>
                </div>
                <div class="card">
                    <div class="card-label">Available Funds</div>
                    <div class="card-value{' positive' if data.available_funds > 0 else ' negative' if data.available_funds < 0 else ''}">{_format_currency(data.available_funds, currency)}</div>
                </div>
                <div class="card">
                    <div class="card-label">Savings Gap</div>
                    <div class="card-value{' negative' if data.savings_gap > 0 else ' positive' if data.savings_gap < 0 else ''}">{_format_currency(data.savings_gap, currency)}</div>
                </div>
                <div class="card">
                    <div class="card-label">True Discretionary</div>
                    <div class="card-value{' positive' if data.true_discretionary > 0 else ' negative' if data.true_discretionary < 0 else ''}">{_format_currency(data.true_discretionary, currency)}</div>
                </div>
            </div>

            <div class="coverage-indicator {'ok' if data.can_cover else 'warning'}">
                <div class="coverage-title">Coverage Indicator</div>
                <div class="coverage-status {'ok' if data.can_cover else 'warning'}">
                    <span class="icon">{_get_coverage_icon(data.can_cover)}</span>
                    <span>{_get_coverage_text(data, currency)}</span>
                </div>
            </div>

            <div class="cash-reconciliation">
                <div class="chart-title">Cash Reconciliation Calculator</div>
                <div id="cash-inputs">
                    <div class="cash-input-row">
                        <input type="text" placeholder="Source (e.g., Bank Account)" class="cash-source">
                        <input type="number" placeholder="Amount" step="0.01" class="cash-amount">
                        <button class="btn-remove" onclick="removeCashRow(this)">-</button>
                    </div>
                </div>
                <button class="btn-add" onclick="addCashRow()" style="margin-top: 0.5rem;">+ Add Source</button>
                <div class="cash-total">
                    <span>Total Cash:</span>
                    <span id="cash-total-value">{currency} 0.00</span>
                </div>
                <div class="cash-comparison" id="cash-comparison">
                    Expected (Available Funds): {_format_currency(data.available_funds, currency)}
                </div>
            </div>

            <div class="section-block historical">
                <div class="section-header">
                    <h3>Balance & Savings Timeline</h3>
                    <span class="section-badge historical">Historical</span>
                </div>
                <div id="chart-timeline"></div>
            </div>

            <div class="section-block historical">
                <div class="section-header">
                    <h3>{interval_label}ly Cash Flow</h3>
                    <span class="section-badge historical">Historical</span>
                </div>
                <div id="chart-cashflow"></div>
            </div>
        </div>

        <!-- ===== INCOME & EXPENSES TAB ===== -->
        <div id="income-expenses" class="tab-content">
            <div class="cards">
                <div class="card">
                    <div class="card-label">Gross Income</div>
                    <div class="card-value positive">{_format_currency(data.plan.gross_income if data.plan else (data.current_period_summary.total_income + data.current_period_summary.total_deductions if data.current_period_summary else Decimal(0)), currency)}</div>
                </div>
                <div class="card">
                    <div class="card-label">Deductions</div>
                    <div class="card-value">{_format_currency(data.current_period_summary.total_deductions if data.current_period_summary else Decimal(0), currency)}</div>
                </div>
                <div class="card">
                    <div class="card-label">Net Income</div>
                    <div class="card-value positive">{_format_currency(data.current_period_summary.total_income if data.current_period_summary else Decimal(0), currency)}</div>
                </div>
                <div class="card">
                    <div class="card-label">Total Expenses</div>
                    <div class="card-value negative">{_format_currency(data.current_period_summary.total_expenses if data.current_period_summary else Decimal(0), currency)}</div>
                </div>
            </div>

            <div class="chart-container">
                <div class="chart-title">Income Flow (Sankey Diagram)</div>
                <p style="color: var(--text-secondary); font-size: 0.875rem; margin-bottom: 1rem;">
                    Shows money flow from Gross Income through deductions to Net Income, then to Fixed Expenses, Flexible Expenses, and Savings.
                </p>
                <div id="chart-sankey"></div>
            </div>

            <div class="chart-container">
                <div class="chart-title">Expenses by Category</div>
                <div id="chart-treemap"></div>
            </div>

            <div class="section-block historical">
                <div class="section-header">
                    <h3>Expenses Timeline (Fixed vs Flexible)</h3>
                    <span class="section-badge historical">Historical</span>
                </div>
                <div id="chart-expenses-timeline"></div>
            </div>

            <h2 class="section-title">Top Expenses</h2>
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th class="number">Amount</th>
                        <th class="number">% of Total</th>
                    </tr>
                </thead>
                <tbody>
                    {_render_expense_rows(expense_cats[:10], data.current_period_summary.total_expenses if data.current_period_summary else Decimal(0), currency)}
                </tbody>
            </table>
        </div>

        <!-- ===== SAVINGS TAB ===== -->
        <div id="savings" class="tab-content">
            <div class="cards">
                <div class="card">
                    <div class="card-label">Actual Savings</div>
                    <div class="card-value positive">{_format_currency(data.total_savings, currency)}</div>
                </div>
                <div class="card">
                    <div class="card-label">Planned Savings</div>
                    <div class="card-value">{_format_currency(data.planned_savings, currency)}</div>
                </div>
                <div class="card">
                    <div class="card-label">Savings Gap</div>
                    <div class="card-value{' negative' if data.savings_gap > 0 else ' positive'}">{_format_currency(data.savings_gap, currency)}</div>
                </div>
            </div>

            <div class="coverage-indicator {'ok' if data.can_cover else 'warning'}">
                <div class="coverage-title">Coverage Status</div>
                <div class="coverage-status {'ok' if data.can_cover else 'warning'}">
                    <span class="icon">{_get_coverage_icon(data.can_cover)}</span>
                    <div>
                        <div><strong>Uncovered Savings:</strong> {_format_currency(data.uncovered_savings, currency)}</div>
                        <div><strong>Cash on Hand:</strong> {_format_currency(data.available_funds, currency)}</div>
                        <div><strong>Can Cover:</strong> {'Yes' if data.can_cover else 'No'}</div>
                        <div><strong>True Discretionary:</strong> {_format_currency(data.true_discretionary, currency)}</div>
                    </div>
                </div>
            </div>

            <div class="section-block historical">
                <div class="section-header">
                    <h3>Savings vs Target Timeline</h3>
                    <span class="section-badge historical">Historical</span>
                </div>
                <div id="chart-savings-timeline"></div>
            </div>

            <h2 class="section-title">Savings Transactions</h2>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Category</th>
                        <th>Description</th>
                        <th class="number">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {savings_rows_html}
                </tbody>
                <tfoot>
                    <tr style="background: var(--bg-secondary); font-weight: 600;">
                        <td colspan="3">Total (This Period)</td>
                        <td class="number {savings_total_class}">{savings_total_formatted}</td>
                    </tr>
                </tfoot>
            </table>
        </div>

        <!-- ===== BUDGET TAB ===== -->
        <div id="budget" class="tab-content">
            {_render_budget_section(data, currency)}
        </div>

        <!-- ===== TRANSACTIONS TAB ===== -->
        <div id="transactions" class="tab-content">
            <div class="filters">
                <select id="filter-category">
                    <option value="">All Categories</option>
                    {_render_category_options(data.transactions)}
                </select>
                <select id="filter-type">
                    <option value="">All Types</option>
                    <option value="income">Income</option>
                    <option value="expense">Expense</option>
                    <option value="savings">Savings</option>
                    <option value="deduction">Deduction</option>
                </select>
                <input type="text" id="filter-search" placeholder="Search description...">
                <button class="export-btn" onclick="exportCSV()">Export CSV</button>
            </div>

            <div class="filter-summary">
                <span class="stat">Showing: <span id="filtered-count" class="stat-value">{len(data.transactions)}</span> transactions</span>
                <span class="stat">Total: <span id="filtered-total" class="stat-value">{currency} 0.00</span></span>
                <span class="stat">Income: <span id="filtered-income" class="stat-value positive">{currency} 0.00</span></span>
                <span class="stat">Expenses: <span id="filtered-expenses" class="stat-value negative">{currency} 0.00</span></span>
            </div>

            <table id="transactions-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Category</th>
                        <th>Description</th>
                        <th class="number">Amount</th>
                        <th>Flags</th>
                    </tr>
                </thead>
                <tbody id="transactions-body">
                </tbody>
            </table>
        </div>
    </div>

    <script>
        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {{
            tab.addEventListener('click', () => {{
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                tab.classList.add('active');
                document.getElementById(tab.dataset.tab).classList.add('active');
            }});
        }});

        // Cash Reconciliation
        const currency = '{currency}';
        const availableFunds = {float(data.available_funds)};

        function addCashRow() {{
            const container = document.getElementById('cash-inputs');
            const row = document.createElement('div');
            row.className = 'cash-input-row';
            row.innerHTML = `
                <input type="text" placeholder="Source (e.g., Bank Account)" class="cash-source">
                <input type="number" placeholder="Amount" step="0.01" class="cash-amount" onchange="updateCashTotal()">
                <button class="btn-remove" onclick="removeCashRow(this)">-</button>
            `;
            container.appendChild(row);
        }}

        function removeCashRow(btn) {{
            btn.parentElement.remove();
            updateCashTotal();
        }}

        function updateCashTotal() {{
            let total = 0;
            document.querySelectorAll('.cash-amount').forEach(input => {{
                total += parseFloat(input.value) || 0;
            }});
            document.getElementById('cash-total-value').textContent = currency + ' ' + total.toFixed(2);

            const diff = total - availableFunds;
            const comparison = document.getElementById('cash-comparison');
            if (Math.abs(diff) < 0.01) {{
                comparison.innerHTML = '<span class="positive">\\u2713 Matches expected Available Funds!</span>';
            }} else if (diff > 0) {{
                comparison.innerHTML = `<span class="positive">+${{diff.toFixed(2)}} more than expected</span>`;
            }} else {{
                comparison.innerHTML = `<span class="negative">${{diff.toFixed(2)}} less than expected</span>`;
            }}
        }}

        document.querySelectorAll('.cash-amount').forEach(input => {{
            input.addEventListener('change', updateCashTotal);
        }});

        // Charts
        const timelineLabels = {json.dumps(timeline_labels)};
        const timelineSavings = {json.dumps(timeline_savings)};
        const timelineBalance = {json.dumps(timeline_balance)};
        const timelineAvailable = {json.dumps(timeline_available)};
        const timelineTarget = {json.dumps(timeline_target)};
        const timelineIncome = {json.dumps(timeline_income)};
        const timelineExpenses = {json.dumps(timeline_expenses)};
        const timelineNet = {json.dumps(timeline_net)};
        const timelineFixed = {json.dumps(timeline_fixed)};
        const timelineFlexible = {json.dumps(timeline_flexible)};

        // Theme-aware Plotly layout (Grafana-style dark theme)
        const isDarkTheme = document.documentElement.getAttribute('data-theme') === 'dark';
        const plotBg = isDarkTheme ? '#1e2126' : '#ffffff';
        const paperBg = isDarkTheme ? '#1e2126' : '#ffffff';
        const gridColor = isDarkTheme ? '#2c3039' : '#e5e7eb';
        const textColor = isDarkTheme ? '#d8d9da' : '#1f2937';
        const plotlyLayout = {{
            paper_bgcolor: paperBg,
            plot_bgcolor: plotBg,
            font: {{ color: textColor }},
            xaxis: {{
                gridcolor: gridColor,
                linecolor: gridColor,
                tickcolor: textColor,
                zerolinecolor: gridColor,
            }},
            yaxis: {{
                gridcolor: gridColor,
                linecolor: gridColor,
                tickcolor: textColor,
                zerolinecolor: gridColor,
            }},
            legend: {{
                bgcolor: 'rgba(0,0,0,0)',
                font: {{ color: textColor }},
            }},
        }};

        // Hover template helper for currency formatting
        const currencyHover = '%{{x}}<br>%{{fullData.name}}: ' + '{currency}' + ' %{{y:,.2f}}<extra></extra>';

        // Timeline chart (with range slider for date filtering)
        Plotly.newPlot('chart-timeline', [
            {{ x: timelineLabels, y: timelineBalance, name: 'Balance', type: 'scatter', fill: 'tozeroy', line: {{ color: '#3b82f6' }}, hovertemplate: currencyHover }},
            {{ x: timelineLabels, y: timelineSavings, name: 'Savings', type: 'scatter', fill: 'tozeroy', line: {{ color: '#16a34a' }}, hovertemplate: currencyHover }},
            {{ x: timelineLabels, y: timelineAvailable, name: 'Available', type: 'scatter', line: {{ color: '#8b5cf6', dash: 'dash' }}, hovertemplate: currencyHover }},
        ], {{
            ...plotlyLayout,
            margin: {{ t: 20, r: 20, b: 80, l: 60 }},
            legend: {{ orientation: 'h', y: 1.1, bgcolor: 'rgba(0,0,0,0)', font: {{ color: textColor }} }},
            xaxis: {{
                ...plotlyLayout.xaxis,
                title: {{ text: '{interval_label}', font: {{ color: textColor }} }},
                rangeslider: {{ visible: true, thickness: 0.1, bgcolor: plotBg }},
                type: 'category'
            }},
            yaxis: {{ ...plotlyLayout.yaxis, title: {{ text: 'Amount ({currency})', font: {{ color: textColor }} }} }},
        }}, {{ responsive: true }});

        // Cash flow chart (with range slider)
        Plotly.newPlot('chart-cashflow', [
            {{ x: timelineLabels, y: timelineIncome, name: 'Income', type: 'bar', marker: {{ color: '#16a34a' }}, hovertemplate: currencyHover }},
            {{ x: timelineLabels, y: timelineExpenses.map(v => -v), name: 'Expenses', type: 'bar', marker: {{ color: '#dc2626' }}, hovertemplate: currencyHover }},
            {{ x: timelineLabels, y: timelineNet, name: 'Net Flow', type: 'scatter', line: {{ color: '#3b82f6' }}, hovertemplate: currencyHover }},
        ], {{
            ...plotlyLayout,
            barmode: 'relative',
            margin: {{ t: 20, r: 20, b: 80, l: 60 }},
            legend: {{ orientation: 'h', y: 1.1, bgcolor: 'rgba(0,0,0,0)', font: {{ color: textColor }} }},
            xaxis: {{
                ...plotlyLayout.xaxis,
                title: {{ text: '{interval_label}', font: {{ color: textColor }} }},
                rangeslider: {{ visible: true, thickness: 0.1, bgcolor: plotBg }},
                type: 'category'
            }},
            yaxis: {{ ...plotlyLayout.yaxis, title: {{ text: 'Amount ({currency})', font: {{ color: textColor }} }} }},
        }}, {{ responsive: true }});

        // Sankey
        Plotly.newPlot('chart-sankey', [{{
            type: 'sankey',
            orientation: 'h',
            node: {{
                pad: 15,
                thickness: 20,
                label: {json.dumps(sankey_nodes)},
                color: isDarkTheme ? '#3b82f6' : '#2563eb',
            }},
            link: {{
                source: {json.dumps(sankey_source)},
                target: {json.dumps(sankey_target)},
                value: {json.dumps(sankey_value)},
                color: isDarkTheme ? 'rgba(59,130,246,0.4)' : 'rgba(37,99,235,0.3)',
            }},
        }}], {{
            ...plotlyLayout,
            margin: {{ t: 20, r: 20, b: 20, l: 20 }},
        }}, {{ responsive: true }});

        // Treemap
        Plotly.newPlot('chart-treemap', [{{
            type: 'treemap',
            labels: {json.dumps(expense_labels)},
            parents: {json.dumps([''] * len(expense_labels))},
            values: {json.dumps(expense_values)},
            textinfo: 'label+value+percent root',
            textfont: {{ color: '#ffffff' }},
            hovertemplate: '%{{label}}<br>{currency} %{{value:,.2f}}<br>%{{percentRoot:.1%}}<extra></extra>',
            marker: {{
                colors: isDarkTheme ?
                    ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'] :
                    ['#2563eb', '#16a34a', '#ca8a04', '#dc2626', '#7c3aed', '#db2777', '#0891b2', '#65a30d'],
            }},
        }}], {{
            ...plotlyLayout,
            margin: {{ t: 20, r: 20, b: 20, l: 20 }},
        }}, {{ responsive: true }});

        // Expenses timeline (with range slider)
        Plotly.newPlot('chart-expenses-timeline', [
            {{ x: timelineLabels, y: timelineFixed, name: 'Fixed', type: 'bar', marker: {{ color: isDarkTheme ? '#6b7280' : '#4b5563' }}, hovertemplate: currencyHover }},
            {{ x: timelineLabels, y: timelineFlexible, name: 'Flexible', type: 'bar', marker: {{ color: '#3b82f6' }}, hovertemplate: currencyHover }},
        ], {{
            ...plotlyLayout,
            barmode: 'stack',
            margin: {{ t: 20, r: 20, b: 80, l: 60 }},
            legend: {{ orientation: 'h', y: 1.1, bgcolor: 'rgba(0,0,0,0)', font: {{ color: textColor }} }},
            xaxis: {{
                ...plotlyLayout.xaxis,
                title: {{ text: '{interval_label}', font: {{ color: textColor }} }},
                rangeslider: {{ visible: true, thickness: 0.1, bgcolor: plotBg }},
                type: 'category'
            }},
            yaxis: {{ ...plotlyLayout.yaxis, title: {{ text: 'Expenses ({currency})', font: {{ color: textColor }} }} }},
        }}, {{ responsive: true }});

        // Savings timeline (with range slider)
        Plotly.newPlot('chart-savings-timeline', [
            {{ x: timelineLabels, y: timelineSavings, name: 'Actual Savings', type: 'scatter', fill: 'tozeroy', line: {{ color: '#22c55e' }}, hovertemplate: currencyHover }},
            {{ x: timelineLabels, y: timelineTarget, name: 'Target', type: 'scatter', line: {{ color: '#ef4444', dash: 'dash' }}, hovertemplate: currencyHover }},
        ], {{
            ...plotlyLayout,
            margin: {{ t: 20, r: 20, b: 80, l: 60 }},
            legend: {{ orientation: 'h', y: 1.1, bgcolor: 'rgba(0,0,0,0)', font: {{ color: textColor }} }},
            xaxis: {{
                ...plotlyLayout.xaxis,
                title: {{ text: '{interval_label}', font: {{ color: textColor }} }},
                rangeslider: {{ visible: true, thickness: 0.1, bgcolor: plotBg }},
                type: 'category'
            }},
            yaxis: {{ ...plotlyLayout.yaxis, title: {{ text: 'Cumulative Savings ({currency})', font: {{ color: textColor }} }} }},
        }}, {{ responsive: true }});

        // Transactions
        const transactionsData = {json.dumps(transactions_data)};

        function renderTransactions(data) {{
            const tbody = document.getElementById('transactions-body');
            tbody.innerHTML = '';
            data.forEach(tx => {{
                const row = document.createElement('tr');
                let flags = '';
                if (tx.is_savings) flags += '<span class="flag savings">Savings</span>';
                if (tx.is_deduction) flags += '<span class="flag deduction">Deduction</span>';
                if (tx.is_fixed) flags += '<span class="flag fixed">Fixed</span>';

                row.innerHTML = `
                    <td>${{tx.date}}</td>
                    <td>${{tx.category}}</td>
                    <td>${{tx.description}}</td>
                    <td class="number ${{tx.amount >= 0 ? 'positive' : 'negative'}}">${{currency}} ${{tx.amount.toFixed(2)}}</td>
                    <td>${{flags}}</td>
                `;
                tbody.appendChild(row);
            }});
        }}

        function updateFilterSummary(data) {{
            const total = data.reduce((sum, tx) => sum + tx.amount, 0);
            const income = data.filter(tx => tx.amount > 0 && !tx.is_savings).reduce((sum, tx) => sum + tx.amount, 0);
            const expenses = data.filter(tx => tx.amount < 0 && !tx.is_savings && !tx.is_deduction).reduce((sum, tx) => sum + Math.abs(tx.amount), 0);

            document.getElementById('filtered-count').textContent = data.length;
            document.getElementById('filtered-total').textContent = currency + ' ' + total.toFixed(2);
            document.getElementById('filtered-income').textContent = currency + ' ' + income.toFixed(2);
            document.getElementById('filtered-expenses').textContent = currency + ' ' + expenses.toFixed(2);

            // Update colors
            document.getElementById('filtered-total').className = total >= 0 ? 'stat-value positive' : 'stat-value negative';
        }}

        function filterTransactions() {{
            const category = document.getElementById('filter-category').value;
            const type = document.getElementById('filter-type').value;
            const search = document.getElementById('filter-search').value.toLowerCase();

            let filtered = transactionsData.filter(tx => {{
                if (category && tx.category !== category) return false;
                if (type === 'income' && tx.amount <= 0) return false;
                if (type === 'expense' && (tx.amount >= 0 || tx.is_savings || tx.is_deduction)) return false;
                if (type === 'savings' && !tx.is_savings) return false;
                if (type === 'deduction' && !tx.is_deduction) return false;
                if (search && !tx.description.toLowerCase().includes(search) && !tx.category.toLowerCase().includes(search)) return false;
                return true;
            }});
            renderTransactions(filtered);
            updateFilterSummary(filtered);
        }}

        document.getElementById('filter-category').addEventListener('change', filterTransactions);
        document.getElementById('filter-type').addEventListener('change', filterTransactions);
        document.getElementById('filter-search').addEventListener('input', filterTransactions);

        renderTransactions(transactionsData);
        updateFilterSummary(transactionsData);

        function exportCSV() {{
            let csv = 'Date,Category,Description,Amount,Savings,Deduction,Fixed\\n';
            transactionsData.forEach(tx => {{
                csv += `${{tx.date}},"${{tx.category}}","${{tx.description}}",${{tx.amount}},${{tx.is_savings}},${{tx.is_deduction}},${{tx.is_fixed}}\\n`;
            }});
            const blob = new Blob([csv], {{ type: 'text/csv' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'transactions.csv';
            a.click();
        }}
    </script>
</body>
</html>
"""
    return html


def _render_trend(change_pct: Decimal | None, direction: str) -> str:
    """Render trend indicator."""
    if change_pct is None:
        return ""
    arrow = "\u2191" if direction == "up" else "\u2193" if direction == "down" else "\u2192"
    css_class = direction
    return f'<div class="card-trend {css_class}">{arrow} {abs(change_pct):.1f}% from previous</div>'


def _render_expense_rows(
    expense_cats: list[tuple[str, Decimal]],
    total: Decimal,
    currency: str,
) -> str:
    """Render expense table rows."""
    rows = []
    for cat, amount in expense_cats:
        pct = (amount / total * 100) if total > 0 else Decimal(0)
        rows.append(f"""
            <tr>
                <td>{cat}</td>
                <td class="number">{_format_currency(amount, currency)}</td>
                <td class="number">{pct:.1f}%</td>
            </tr>
        """)
    return "\n".join(rows)


def _render_savings_transactions(transactions: list, currency: str) -> tuple[str, Decimal]:
    """Render savings transactions table rows with total.

    Returns:
        Tuple of (HTML rows, total amount).
    """
    savings_txs = [tx for tx in transactions if tx.is_savings]
    savings_txs.sort(key=lambda x: x.date, reverse=True)

    total = sum(tx.amount for tx in savings_txs)

    rows = []
    for tx in savings_txs[:20]:
        css_class = "positive" if tx.amount > 0 else "negative"
        rows.append(f"""
            <tr>
                <td>{tx.date.isoformat()}</td>
                <td>{tx.category}</td>
                <td>{tx.description or '-'}</td>
                <td class="number {css_class}">{_format_currency(tx.amount, currency)}</td>
            </tr>
        """)

    if not rows:
        return "<tr><td colspan='4'>No savings transactions</td></tr>", Decimal(0)

    return "\n".join(rows), total


def _render_budget_bar(
    label: str,
    actual: Decimal,
    planned: Decimal,
    currency: str,
    is_target: bool = False,
) -> str:
    """Render a budget progress bar with variance info.

    Args:
        label: Bar label.
        actual: Actual amount.
        planned: Planned amount.
        currency: Currency code.
        is_target: If True, higher actual is better (e.g., income, savings).
                   If False, lower actual is better (e.g., expenses).
    """
    if planned == 0:
        return ""

    pct = float(actual / planned * 100)
    diff = actual - planned
    diff_pct = float(diff / planned * 100) if planned else 0

    # Determine bar class and badge
    if is_target:
        # For targets (income, savings): higher is better
        if pct >= 100:
            bar_class = "exceeded" if pct > 100 else "ok"
            badge_html = f'<span class="budget-badge exceeded">\u2713 Exceeded</span>' if pct > 100 else ''
            diff_class = "exceeded" if pct > 100 else "positive"
        elif pct >= 80:
            bar_class = "warning"
            badge_html = ""
            diff_class = "negative"
        else:
            bar_class = "danger"
            badge_html = ""
            diff_class = "negative"
    else:
        # For expenses: lower is better
        if pct <= 100:
            bar_class = "ok"
            badge_html = f'<span class="budget-badge under">\u2713 Under</span>' if pct < 90 else ''
            diff_class = "positive"
        else:
            bar_class = "danger"
            badge_html = f'<span class="budget-badge over">\u26a0 Over</span>'
            diff_class = "negative"

    # Format diff text
    if diff >= 0:
        diff_text = f"+{_format_currency(diff, currency)}, +{diff_pct:.1f}%"
    else:
        diff_text = f"{_format_currency(diff, currency)}, {diff_pct:.1f}%"

    return f"""
        <div class="budget-bar">
            <div class="label">{label}</div>
            <div class="bar-container">
                <div class="bar {bar_class}" style="width: {min(pct, 100)}%"></div>
            </div>
            <div class="value">
                <span class="actual">{_format_currency(actual, currency)}</span> /
                <span class="planned">{_format_currency(planned, currency)}</span>
                <span class="diff {diff_class}">({diff_text})</span>
                {badge_html}
            </div>
        </div>
    """


def _render_budget_section(data: DashboardData, currency: str) -> str:
    """Render budget tab content."""
    if not data.plan:
        return "<p>No budget plan available for this period.</p>"

    plan = data.plan
    summary = data.current_period_summary

    html = ""

    # Income section
    if plan.gross_income > 0:
        actual_income = summary.total_income if summary else Decimal(0)
        html += '<h2 class="section-title">Income</h2>'
        html += _render_budget_bar("Gross Income", actual_income, plan.gross_income, currency, is_target=True)

    # Deductions section
    if plan.total_deductions > 0:
        actual_ded = summary.total_deductions if summary else Decimal(0)
        html += '<h2 class="section-title">Deductions</h2>'
        html += _render_budget_bar("Total Deductions", actual_ded, plan.total_deductions, currency, is_target=False)

    # Fixed expenses section
    if plan.total_fixed_expenses > 0:
        actual_fixed = summary.total_fixed_expenses if summary else Decimal(0)
        html += '<h2 class="section-title">Fixed Expenses</h2>'
        html += _render_budget_bar("Total Fixed", actual_fixed, plan.total_fixed_expenses, currency, is_target=False)

    # Flexible spending section
    if plan.disposable_income > 0:
        actual_flex = summary.total_flexible_expenses if summary else Decimal(0)
        html += '<h2 class="section-title">Flexible Spending</h2>'
        html += _render_budget_bar("Disposable", actual_flex, plan.disposable_income, currency, is_target=False)

    # Savings section
    if plan.savings_target > 0:
        actual_savings = summary.total_savings if summary else Decimal(0)
        html += '<h2 class="section-title">Savings</h2>'
        html += _render_budget_bar("Savings Target", actual_savings, plan.savings_target, currency, is_target=True)

    # Category breakdown table - with percentages
    total_actual = sum(c.actual_amount for c in data.categories if c.actual_amount > 0)
    total_planned = sum(c.planned_amount for c in data.categories if c.planned_amount)

    html += """
    <h2 class="section-title">Category Breakdown</h2>
    <table>
        <thead>
            <tr>
                <th>Category</th>
                <th class="number">Actual</th>
                <th class="number">%</th>
                <th class="number">Planned</th>
                <th class="number">%</th>
                <th class="number">Variance</th>
                <th class="number">Var %</th>
            </tr>
        </thead>
        <tbody>
    """

    for cat in sorted(data.categories, key=lambda x: x.actual_amount, reverse=True):
        if cat.actual_amount == 0 and not cat.planned_amount:
            continue

        # Calculate percentages
        actual_pct = float(cat.actual_amount / total_actual * 100) if total_actual > 0 else 0
        planned_pct = float(cat.planned_amount / total_planned * 100) if cat.planned_amount and total_planned > 0 else 0

        # Variance
        variance_class = ""
        variance_text = "-"
        variance_pct_text = "-"
        if cat.variance_vs_plan is not None:
            var_pct = float(cat.variance_vs_plan / cat.planned_amount * 100) if cat.planned_amount else 0
            if cat.variance_vs_plan > 0:
                variance_class = "positive"
                variance_text = f"+{_format_currency(cat.variance_vs_plan, currency)}"
                variance_pct_text = f"+{var_pct:.1f}%"
            elif cat.variance_vs_plan < 0:
                variance_class = "negative"
                variance_text = _format_currency(cat.variance_vs_plan, currency)
                variance_pct_text = f"{var_pct:.1f}%"
            else:
                variance_text = _format_currency(Decimal(0), currency)
                variance_pct_text = "0.0%"

        html += f"""
            <tr>
                <td>{cat.category}{' <span class="flag fixed">Fixed</span>' if cat.is_fixed else ''}</td>
                <td class="number">{_format_currency(cat.actual_amount, currency)}</td>
                <td class="number">{actual_pct:.1f}%</td>
                <td class="number">{_format_currency(cat.planned_amount, currency) if cat.planned_amount else '-'}</td>
                <td class="number">{f'{planned_pct:.1f}%' if cat.planned_amount else '-'}</td>
                <td class="number {variance_class}">{variance_text}</td>
                <td class="number {variance_class}">{variance_pct_text}</td>
            </tr>
        """

    html += """
        </tbody>
    </table>
    """

    return html


def _render_category_options(transactions: list) -> str:
    """Render category select options."""
    categories = sorted(set(tx.category for tx in transactions))
    return "\n".join(f'<option value="{cat}">{cat}</option>' for cat in categories)


def save_dashboard(html: str, output_path: Path) -> None:
    """Save dashboard HTML to file.

    Args:
        html: HTML content.
        output_path: Output file path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


def generate_all_periods_dashboard_html(all_data: dict[str, "DashboardData"]) -> str:
    """Generate dashboard HTML with all periods data and period switcher.

    This generates a full 5-tab dashboard identical to the single-period version,
    but with a period selector dropdown that updates all tabs dynamically.

    Args:
        all_data: Dict mapping period labels to DashboardData.

    Returns:
        Complete HTML string with period switcher dropdown.
    """
    if not all_data:
        return "<html><body><p>No data available</p></body></html>"

    # Get sorted period labels (most recent first)
    periods = sorted(all_data.keys(), reverse=True)
    current_period = periods[0]
    current_data = all_data[current_period]

    currency = current_data.currency
    interval_label = _get_interval_label(current_data.interval)
    theme = current_data.theme

    # Prepare comprehensive data for all periods (for JSON embedding)
    all_periods_json: dict = {}
    for period_label, data in all_data.items():
        # Prepare transactions for this period
        tx_list = []
        for tx in sorted(data.transactions, key=lambda x: x.date, reverse=True)[:100]:
            tx_list.append({
                "date": tx.date.isoformat(),
                "category": tx.category,
                "amount": float(tx.amount),
                "description": tx.description or "",
                "is_savings": tx.is_savings,
                "is_deduction": tx.is_deduction,
                "is_fixed": tx.is_fixed,
            })

        # Prepare savings transactions
        savings_tx_list = []
        savings_total = 0.0
        for tx in sorted(data.transactions, key=lambda x: x.date, reverse=True):
            if tx.is_savings:
                savings_tx_list.append({
                    "date": tx.date.isoformat(),
                    "category": tx.category,
                    "amount": float(tx.amount),
                    "description": tx.description or "",
                })
                savings_total += float(tx.amount)

        # Prepare budget data
        summary = data.current_period_summary
        plan = data.plan
        budget_data = {
            "has_plan": plan is not None,
            "gross_income_actual": float(summary.total_income) if summary else 0,
            "gross_income_planned": float(plan.gross_income) if plan else 0,
            "deductions_actual": float(summary.total_deductions) if summary else 0,
            "deductions_planned": float(plan.total_deductions) if plan else 0,
            "fixed_actual": float(summary.total_fixed_expenses) if summary else 0,
            "fixed_planned": float(plan.total_fixed_expenses) if plan else 0,
            "flexible_actual": float(summary.total_flexible_expenses) if summary else 0,
            "flexible_planned": float(plan.disposable_income) if plan else 0,
            "savings_actual": float(summary.total_savings) if summary else 0,
            "savings_planned": float(plan.savings_target) if plan else 0,
        }

        # Prepare category breakdown
        categories_list = []
        total_actual = sum(c.actual_amount for c in data.categories if c.actual_amount > 0)
        total_planned = sum(c.planned_amount for c in data.categories if c.planned_amount)
        for cat in sorted(data.categories, key=lambda x: x.actual_amount, reverse=True):
            if cat.actual_amount == 0 and not cat.planned_amount:
                continue
            actual_pct = float(cat.actual_amount / total_actual * 100) if total_actual > 0 else 0
            planned_pct = float(cat.planned_amount / total_planned * 100) if cat.planned_amount and total_planned > 0 else 0
            variance = float(cat.variance_vs_plan) if cat.variance_vs_plan else None
            variance_pct = float(cat.variance_vs_plan / cat.planned_amount * 100) if cat.variance_vs_plan and cat.planned_amount else None
            categories_list.append({
                "category": cat.category,
                "is_fixed": cat.is_fixed,
                "actual": float(cat.actual_amount),
                "actual_pct": actual_pct,
                "planned": float(cat.planned_amount) if cat.planned_amount else None,
                "planned_pct": planned_pct,
                "variance": variance,
                "variance_pct": variance_pct,
            })

        # Prepare KPIs and all data
        all_periods_json[period_label] = {
            "kpis": {
                "current_balance": float(data.current_balance),
                "total_savings": float(data.total_savings),
                "available_funds": float(data.available_funds),
                "savings_gap": float(data.savings_gap),
                "true_discretionary": float(data.true_discretionary),
                "uncovered_savings": float(data.uncovered_savings),
                "can_cover": data.can_cover,
                "planned_savings": float(data.planned_savings),
                "gross_income": float(plan.gross_income) if plan else 0,
                "net_income": float(summary.total_income) if summary else 0,
                "total_deductions": float(summary.total_deductions) if summary else 0,
                "total_expenses": float(summary.total_expenses) if summary else 0,
            },
            "transactions": tx_list,
            "savings_transactions": savings_tx_list,
            "savings_total": savings_total,
            "budget": budget_data,
            "categories": categories_list,
            "expenses_by_category": {k: float(v) for k, v in data.expenses_by_category.items()},
            "balance_change_pct": float(data.balance_change_pct) if data.balance_change_pct else None,
            "balance_change_direction": data.balance_change_direction,
        }

    # Timeline data is shared (from the most recent period)
    timeline_labels = [p.period_label for p in current_data.timeline]
    timeline_savings = [float(p.cumulative_savings) for p in current_data.timeline]
    timeline_balance = [float(p.cumulative_balance) for p in current_data.timeline]
    timeline_available = [float(p.available_funds) for p in current_data.timeline]
    timeline_target = [float(p.cumulative_savings_target) for p in current_data.timeline]
    timeline_income = [float(p.income) for p in current_data.timeline]
    timeline_expenses = [float(p.expenses) for p in current_data.timeline]
    timeline_net = [float(p.net_flow) for p in current_data.timeline]
    timeline_fixed = [float(p.fixed_expenses) for p in current_data.timeline]
    timeline_flexible = [float(p.flexible_expenses) for p in current_data.timeline]

    # Build period options for dropdown
    period_options = "\n".join(
        f'<option value="{p}">{p}</option>' for p in periods
    )

    # Prepare Sankey data for current period (will be updated via JS)
    sankey_nodes: list[str] = []
    sankey_source: list[int] = []
    sankey_target: list[int] = []
    sankey_value: list[float] = []
    node_map: dict[str, int] = {}

    for flow in current_data.income_expense_flows:
        if flow.source not in node_map:
            node_map[flow.source] = len(sankey_nodes)
            sankey_nodes.append(flow.source)
        if flow.target not in node_map:
            node_map[flow.target] = len(sankey_nodes)
            sankey_nodes.append(flow.target)
        sankey_source.append(node_map[flow.source])
        sankey_target.append(node_map[flow.target])
        sankey_value.append(float(flow.amount))

    # Expense categories for treemap
    expense_cats = sorted(
        current_data.expenses_by_category.items(),
        key=lambda x: x[1],
        reverse=True,
    )
    expense_labels = [c[0] for c in expense_cats]
    expense_values = [float(c[1]) for c in expense_cats]

    # Generate HTML with full 5-tab interface
    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="{theme}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FinTrack Dashboard - {current_data.workspace_name} (All Periods)</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        :root {{
            --primary: #2563eb;
            --primary-light: #3b82f6;
            --success: #16a34a;
            --warning: #ca8a04;
            --danger: #dc2626;
            --bg-primary: #ffffff;
            --bg-secondary: #f9fafb;
            --text-primary: #1f2937;
            --text-secondary: #6b7280;
            --border-color: #e5e7eb;
            --card-bg: #ffffff;
            --card-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        [data-theme="dark"] {{
            --primary: #3b82f6;
            --primary-light: #60a5fa;
            --success: #22c55e;
            --warning: #eab308;
            --danger: #ef4444;
            --bg-primary: #0d0f12;
            --bg-secondary: #141619;
            --text-primary: #d8d9da;
            --text-secondary: #8b8d8f;
            --border-color: #2c3039;
            --card-bg: #1e2126;
            --card-shadow: 0 1px 3px rgba(0,0,0,0.5);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.5; color: var(--text-primary); background: var(--bg-secondary); }}
        .header {{ background: var(--card-bg); border-bottom: 1px solid var(--border-color); padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }}
        .header h1 {{ color: var(--primary); font-size: 1.5rem; }}
        .header .meta {{ display: flex; gap: 1rem; align-items: center; color: var(--text-secondary); font-size: 0.875rem; }}
        .period-dropdown {{ padding: 0.5rem 1rem; border: 1px solid var(--border-color); border-radius: 8px; font-size: 1rem; font-weight: 600; color: var(--primary); background: var(--bg-secondary); cursor: pointer; }}
        .all-periods-badge {{ background: #dbeafe; color: #1e40af; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 500; }}
        [data-theme="dark"] .all-periods-badge {{ background: #1e3a5f; color: #93c5fd; }}
        .tabs {{ background: var(--card-bg); border-bottom: 1px solid var(--border-color); display: flex; padding: 0 2rem; gap: 0; }}
        .tab {{ padding: 1rem 1.5rem; cursor: pointer; border-bottom: 2px solid transparent; color: var(--text-secondary); font-weight: 500; transition: all 0.2s; }}
        .tab:hover {{ color: var(--primary); }}
        .tab.active {{ color: var(--primary); border-bottom-color: var(--primary); }}
        .content {{ padding: 2rem; max-width: 1400px; margin: 0 auto; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
        .card {{ background: var(--card-bg); border-radius: 12px; padding: 1.5rem; box-shadow: var(--card-shadow); }}
        .card-label {{ font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 0.25rem; }}
        .card-value {{ font-size: 1.75rem; font-weight: 600; }}
        .card-value.positive {{ color: var(--success); }}
        .card-value.negative {{ color: var(--danger); }}
        .chart-container {{ background: var(--card-bg); border-radius: 12px; padding: 1.5rem; box-shadow: var(--card-shadow); margin-bottom: 2rem; }}
        .chart-title {{ font-size: 1rem; font-weight: 600; margin-bottom: 1rem; color: var(--text-primary); }}
        .section-title {{ font-size: 1.25rem; font-weight: 600; margin: 2rem 0 1rem; color: var(--text-primary); }}
        .section-block {{ background: var(--card-bg); border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; box-shadow: var(--card-shadow); border-left: 4px solid var(--primary); }}
        .section-block.historical {{ border-left-color: #6366f1; }}
        .section-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }}
        .section-header h3 {{ margin: 0; font-size: 1rem; font-weight: 600; color: var(--text-primary); }}
        .section-badge {{ display: inline-block; font-size: 0.7rem; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 500; text-transform: uppercase; }}
        .section-badge.historical {{ background: #e0e7ff; color: #3730a3; }}
        [data-theme="dark"] .section-badge.historical {{ background: #312e81; color: #c7d2fe; }}
        table {{ width: 100%; border-collapse: collapse; background: var(--card-bg); border-radius: 12px; overflow: hidden; box-shadow: var(--card-shadow); margin-bottom: 2rem; }}
        th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--border-color); }}
        th {{ background: var(--bg-secondary); font-weight: 600; color: var(--text-primary); }}
        td.number {{ text-align: right; font-variant-numeric: tabular-nums; }}
        tr:last-child td {{ border-bottom: none; }}
        .positive {{ color: var(--success); }}
        .negative {{ color: var(--danger); }}
        .flag {{ display: inline-block; padding: 0.125rem 0.5rem; border-radius: 4px; font-size: 0.75rem; margin-left: 0.25rem; }}
        .flag.savings {{ background: #dbeafe; color: #1e40af; }}
        .flag.deduction {{ background: #fef3c7; color: #92400e; }}
        .flag.fixed {{ background: #f3e8ff; color: #6b21a8; }}
        .coverage-indicator {{ background: var(--card-bg); border-radius: 12px; padding: 1.5rem; box-shadow: var(--card-shadow); margin-bottom: 2rem; }}
        .coverage-indicator.ok {{ border-left: 4px solid var(--success); }}
        .coverage-indicator.warning {{ border-left: 4px solid var(--danger); }}
        .coverage-title {{ font-weight: 600; margin-bottom: 0.5rem; }}
        .coverage-status {{ display: flex; align-items: center; gap: 0.5rem; }}
        .coverage-status .icon {{ font-size: 1.5rem; }}
        .coverage-status.ok .icon {{ color: var(--success); }}
        .coverage-status.warning .icon {{ color: var(--danger); }}
        .budget-bar {{ display: flex; align-items: center; gap: 1rem; margin-bottom: 0.75rem; }}
        .budget-bar .label {{ width: 150px; font-weight: 500; color: var(--text-primary); }}
        .budget-bar .bar-container {{ flex: 1; height: 24px; background: var(--border-color); border-radius: 4px; overflow: hidden; }}
        .budget-bar .bar {{ height: 100%; }}
        .budget-bar .bar.ok {{ background: var(--success); }}
        .budget-bar .bar.warning {{ background: var(--warning); }}
        .budget-bar .bar.danger {{ background: var(--danger); }}
        .budget-bar .bar.exceeded {{ background: #8b5cf6; }}
        .budget-bar .value {{ width: 250px; text-align: right; font-size: 0.9rem; }}
        .filters {{ display: flex; gap: 1rem; margin-bottom: 1rem; flex-wrap: wrap; }}
        .filters select, .filters input {{ padding: 0.5rem; border: 1px solid var(--border-color); border-radius: 4px; background: var(--bg-secondary); color: var(--text-primary); }}
        .export-btn {{ background: var(--primary); color: white; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; }}
        .filter-summary {{ padding: 0.75rem 1rem; background: var(--bg-secondary); border-radius: 8px; margin-bottom: 1rem; display: flex; gap: 2rem; align-items: center; }}
        .filter-summary .stat {{ font-weight: 500; }}
        .filter-summary .stat-value {{ font-weight: 600; color: var(--primary); }}
        @media (max-width: 768px) {{ .tabs {{ overflow-x: auto; }} .tab {{ white-space: nowrap; }} .cards {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="header">
        <h1>FinTrack Dashboard</h1>
        <div class="meta">
            <span class="all-periods-badge">All Periods</span>
            <select id="period-select" class="period-dropdown" onchange="switchPeriod(this.value)">
                {period_options}
            </select>
            <span>{current_data.workspace_name}</span>
        </div>
    </div>

    <div class="tabs">
        <div class="tab active" data-tab="overview">Overview</div>
        <div class="tab" data-tab="income-expenses">Income & Expenses</div>
        <div class="tab" data-tab="savings">Savings</div>
        <div class="tab" data-tab="budget">Budget</div>
        <div class="tab" data-tab="transactions">Transactions</div>
    </div>

    <div class="content">
        <!-- OVERVIEW TAB -->
        <div id="overview" class="tab-content active">
            <div class="cards">
                <div class="card"><div class="card-label">Current Balance</div><div id="kpi-balance" class="card-value"></div></div>
                <div class="card"><div class="card-label">Total Savings</div><div id="kpi-savings" class="card-value positive"></div></div>
                <div class="card"><div class="card-label">Available Funds</div><div id="kpi-available" class="card-value"></div></div>
                <div class="card"><div class="card-label">Savings Gap</div><div id="kpi-gap" class="card-value"></div></div>
                <div class="card"><div class="card-label">True Discretionary</div><div id="kpi-discretionary" class="card-value"></div></div>
            </div>
            <div id="coverage-container"></div>
            <div class="section-block historical">
                <div class="section-header"><h3>Balance & Savings Timeline</h3><span class="section-badge historical">Historical</span></div>
                <div id="chart-timeline"></div>
            </div>
            <div class="section-block historical">
                <div class="section-header"><h3>{interval_label}ly Cash Flow</h3><span class="section-badge historical">Historical</span></div>
                <div id="chart-cashflow"></div>
            </div>
        </div>

        <!-- INCOME & EXPENSES TAB -->
        <div id="income-expenses" class="tab-content">
            <div class="cards" id="income-cards"></div>
            <div class="chart-container">
                <div class="chart-title">Income Flow (Sankey Diagram)</div>
                <p style="color: var(--text-secondary); font-size: 0.875rem; margin-bottom: 1rem;">Shows money flow from Gross Income through deductions to Net Income, then to Fixed Expenses, Flexible Expenses, and Savings.</p>
                <div id="chart-sankey"></div>
            </div>
            <div class="chart-container">
                <div class="chart-title">Expenses by Category</div>
                <div id="chart-treemap"></div>
            </div>
            <div class="section-block historical">
                <div class="section-header"><h3>Expenses Timeline (Fixed vs Flexible)</h3><span class="section-badge historical">Historical</span></div>
                <div id="chart-expenses-timeline"></div>
            </div>
        </div>

        <!-- SAVINGS TAB -->
        <div id="savings" class="tab-content">
            <div class="cards" id="savings-cards"></div>
            <div id="savings-coverage-container"></div>
            <div class="section-block historical">
                <div class="section-header"><h3>Savings vs Target Timeline</h3><span class="section-badge historical">Historical</span></div>
                <div id="chart-savings-timeline"></div>
            </div>
            <h2 class="section-title">Savings Transactions</h2>
            <table><thead><tr><th>Date</th><th>Category</th><th>Description</th><th class="number">Amount</th></tr></thead><tbody id="savings-transactions-body"></tbody><tfoot id="savings-transactions-foot"></tfoot></table>
        </div>

        <!-- BUDGET TAB -->
        <div id="budget" class="tab-content">
            <div id="budget-content"></div>
        </div>

        <!-- TRANSACTIONS TAB -->
        <div id="transactions" class="tab-content">
            <div class="filters">
                <select id="filter-category"><option value="">All Categories</option></select>
                <select id="filter-type"><option value="">All Types</option><option value="income">Income</option><option value="expense">Expense</option><option value="savings">Savings</option><option value="deduction">Deduction</option></select>
                <input type="text" id="filter-search" placeholder="Search description...">
                <button class="export-btn" onclick="exportCSV()">Export CSV</button>
            </div>
            <div class="filter-summary">
                <span class="stat">Showing: <span id="filtered-count" class="stat-value">0</span> transactions</span>
                <span class="stat">Total: <span id="filtered-total" class="stat-value">{currency} 0.00</span></span>
                <span class="stat">Income: <span id="filtered-income" class="stat-value positive">{currency} 0.00</span></span>
                <span class="stat">Expenses: <span id="filtered-expenses" class="stat-value negative">{currency} 0.00</span></span>
            </div>
            <table id="transactions-table"><thead><tr><th>Date</th><th>Category</th><th>Description</th><th class="number">Amount</th><th>Flags</th></tr></thead><tbody id="transactions-body"></tbody></table>
        </div>
    </div>

    <script>
        const currency = '{currency}';
        const allPeriodsData = {json.dumps(all_periods_json, default=_decimal_to_float)};
        let currentPeriod = '{current_period}';
        let currentTransactions = [];

        // Timeline data (shared across all periods)
        const timelineLabels = {json.dumps(timeline_labels)};
        const timelineSavings = {json.dumps(timeline_savings)};
        const timelineBalance = {json.dumps(timeline_balance)};
        const timelineAvailable = {json.dumps(timeline_available)};
        const timelineTarget = {json.dumps(timeline_target)};
        const timelineIncome = {json.dumps(timeline_income)};
        const timelineExpenses = {json.dumps(timeline_expenses)};
        const timelineNet = {json.dumps(timeline_net)};
        const timelineFixed = {json.dumps(timeline_fixed)};
        const timelineFlexible = {json.dumps(timeline_flexible)};

        // Theme-aware Plotly layout
        const isDarkTheme = document.documentElement.getAttribute('data-theme') === 'dark';
        const plotBg = isDarkTheme ? '#1e2126' : '#ffffff';
        const gridColor = isDarkTheme ? '#2c3039' : '#e5e7eb';
        const textColor = isDarkTheme ? '#d8d9da' : '#1f2937';

        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {{
            tab.addEventListener('click', () => {{
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                tab.classList.add('active');
                document.getElementById(tab.dataset.tab).classList.add('active');
            }});
        }});

        function formatCurrency(amount) {{
            const sign = amount < 0 ? '-' : '';
            return sign + currency + ' ' + Math.abs(amount).toFixed(2);
        }}

        function updateOverviewTab(data) {{
            const kpis = data.kpis;
            document.getElementById('kpi-balance').textContent = formatCurrency(kpis.current_balance);
            document.getElementById('kpi-savings').textContent = formatCurrency(kpis.total_savings);
            document.getElementById('kpi-available').textContent = formatCurrency(kpis.available_funds);
            document.getElementById('kpi-gap').textContent = formatCurrency(kpis.savings_gap);
            document.getElementById('kpi-discretionary').textContent = formatCurrency(kpis.true_discretionary);
            document.getElementById('kpi-available').className = 'card-value ' + (kpis.available_funds >= 0 ? 'positive' : 'negative');
            document.getElementById('kpi-gap').className = 'card-value ' + (kpis.savings_gap > 0 ? 'negative' : 'positive');
            document.getElementById('kpi-discretionary').className = 'card-value ' + (kpis.true_discretionary >= 0 ? 'positive' : 'negative');

            // Coverage indicator
            const canCover = kpis.can_cover;
            const icon = canCover ? '\\u2713' : '\\u26a0';
            const coverText = kpis.uncovered_savings === 0 ? 'All savings targets are met!' :
                (canCover ? 'You can cover the savings gap of ' + formatCurrency(kpis.uncovered_savings) :
                'Cannot cover savings gap of ' + formatCurrency(kpis.uncovered_savings));
            document.getElementById('coverage-container').innerHTML = `
                <div class="coverage-indicator ${{canCover ? 'ok' : 'warning'}}">
                    <div class="coverage-title">Coverage Indicator</div>
                    <div class="coverage-status ${{canCover ? 'ok' : 'warning'}}">
                        <span class="icon">${{icon}}</span><span>${{coverText}}</span>
                    </div>
                </div>`;
        }}

        function updateIncomeExpensesTab(data) {{
            const kpis = data.kpis;
            document.getElementById('income-cards').innerHTML = `
                <div class="card"><div class="card-label">Gross Income</div><div class="card-value positive">${{formatCurrency(kpis.gross_income)}}</div></div>
                <div class="card"><div class="card-label">Deductions</div><div class="card-value">${{formatCurrency(kpis.total_deductions)}}</div></div>
                <div class="card"><div class="card-label">Net Income</div><div class="card-value positive">${{formatCurrency(kpis.net_income)}}</div></div>
                <div class="card"><div class="card-label">Total Expenses</div><div class="card-value negative">${{formatCurrency(kpis.total_expenses)}}</div></div>`;
        }}

        function updateSavingsTab(data) {{
            const kpis = data.kpis;
            document.getElementById('savings-cards').innerHTML = `
                <div class="card"><div class="card-label">Actual Savings</div><div class="card-value positive">${{formatCurrency(kpis.total_savings)}}</div></div>
                <div class="card"><div class="card-label">Planned Savings</div><div class="card-value">${{formatCurrency(kpis.planned_savings)}}</div></div>
                <div class="card"><div class="card-label">Savings Gap</div><div class="card-value ${{kpis.savings_gap > 0 ? 'negative' : 'positive'}}">${{formatCurrency(kpis.savings_gap)}}</div></div>`;

            const canCover = kpis.can_cover;
            const icon = canCover ? '\\u2713' : '\\u26a0';
            document.getElementById('savings-coverage-container').innerHTML = `
                <div class="coverage-indicator ${{canCover ? 'ok' : 'warning'}}">
                    <div class="coverage-title">Coverage Status</div>
                    <div class="coverage-status ${{canCover ? 'ok' : 'warning'}}">
                        <span class="icon">${{icon}}</span>
                        <div>
                            <div><strong>Uncovered Savings:</strong> ${{formatCurrency(kpis.uncovered_savings)}}</div>
                            <div><strong>Cash on Hand:</strong> ${{formatCurrency(kpis.available_funds)}}</div>
                            <div><strong>Can Cover:</strong> ${{canCover ? 'Yes' : 'No'}}</div>
                            <div><strong>True Discretionary:</strong> ${{formatCurrency(kpis.true_discretionary)}}</div>
                        </div>
                    </div>
                </div>`;

            // Savings transactions
            const tbody = document.getElementById('savings-transactions-body');
            tbody.innerHTML = '';
            data.savings_transactions.slice(0, 20).forEach(tx => {{
                const row = document.createElement('tr');
                const cls = tx.amount >= 0 ? 'positive' : 'negative';
                row.innerHTML = `<td>${{tx.date}}</td><td>${{tx.category}}</td><td>${{tx.description || '-'}}</td><td class="number ${{cls}}">${{formatCurrency(tx.amount)}}</td>`;
                tbody.appendChild(row);
            }});
            document.getElementById('savings-transactions-foot').innerHTML = `<tr style="background:var(--bg-secondary);font-weight:600;"><td colspan="3">Total (This Period)</td><td class="number ${{data.savings_total >= 0 ? 'positive' : 'negative'}}">${{formatCurrency(data.savings_total)}}</td></tr>`;
        }}

        function updateBudgetTab(data) {{
            const budget = data.budget;
            if (!budget.has_plan) {{
                document.getElementById('budget-content').innerHTML = '<p>No budget plan available for this period.</p>';
                return;
            }}
            let html = '';

            function renderBar(label, actual, planned, isTarget) {{
                if (planned === 0) return '';
                const pct = (actual / planned * 100);
                const diff = actual - planned;
                const diffPct = (diff / planned * 100);
                let barClass, diffClass;
                if (isTarget) {{
                    barClass = pct >= 100 ? (pct > 100 ? 'exceeded' : 'ok') : (pct >= 80 ? 'warning' : 'danger');
                    diffClass = pct >= 100 ? (pct > 100 ? 'exceeded' : 'positive') : 'negative';
                }} else {{
                    barClass = pct <= 100 ? 'ok' : 'danger';
                    diffClass = pct <= 100 ? 'positive' : 'negative';
                }}
                const diffText = (diff >= 0 ? '+' : '') + formatCurrency(diff) + ', ' + (diff >= 0 ? '+' : '') + diffPct.toFixed(1) + '%';
                return `<div class="budget-bar"><div class="label">${{label}}</div><div class="bar-container"><div class="bar ${{barClass}}" style="width:${{Math.min(pct, 100)}}%"></div></div><div class="value"><span style="font-weight:600">${{formatCurrency(actual)}}</span> / ${{formatCurrency(planned)}} <span class="${{diffClass}}" style="font-size:0.8rem">(${{diffText}})</span></div></div>`;
            }}

            if (budget.gross_income_planned > 0) html += '<h2 class="section-title">Income</h2>' + renderBar('Gross Income', budget.gross_income_actual, budget.gross_income_planned, true);
            if (budget.deductions_planned > 0) html += '<h2 class="section-title">Deductions</h2>' + renderBar('Total Deductions', budget.deductions_actual, budget.deductions_planned, false);
            if (budget.fixed_planned > 0) html += '<h2 class="section-title">Fixed Expenses</h2>' + renderBar('Total Fixed', budget.fixed_actual, budget.fixed_planned, false);
            if (budget.flexible_planned > 0) html += '<h2 class="section-title">Flexible Spending</h2>' + renderBar('Disposable', budget.flexible_actual, budget.flexible_planned, false);
            if (budget.savings_planned > 0) html += '<h2 class="section-title">Savings</h2>' + renderBar('Savings Target', budget.savings_actual, budget.savings_planned, true);

            // Category breakdown
            if (data.categories && data.categories.length > 0) {{
                html += '<h2 class="section-title">Category Breakdown</h2><table><thead><tr><th>Category</th><th class="number">Actual</th><th class="number">%</th><th class="number">Planned</th><th class="number">%</th><th class="number">Variance</th><th class="number">Var %</th></tr></thead><tbody>';
                data.categories.forEach(cat => {{
                    const varClass = cat.variance !== null ? (cat.variance > 0 ? 'positive' : (cat.variance < 0 ? 'negative' : '')) : '';
                    const varText = cat.variance !== null ? (cat.variance > 0 ? '+' : '') + formatCurrency(cat.variance) : '-';
                    const varPctText = cat.variance_pct !== null ? (cat.variance_pct > 0 ? '+' : '') + cat.variance_pct.toFixed(1) + '%' : '-';
                    html += `<tr><td>${{cat.category}}${{cat.is_fixed ? ' <span class="flag fixed">Fixed</span>' : ''}}</td><td class="number">${{formatCurrency(cat.actual)}}</td><td class="number">${{cat.actual_pct.toFixed(1)}}%</td><td class="number">${{cat.planned !== null ? formatCurrency(cat.planned) : '-'}}</td><td class="number">${{cat.planned !== null ? cat.planned_pct.toFixed(1) + '%' : '-'}}</td><td class="number ${{varClass}}">${{varText}}</td><td class="number ${{varClass}}">${{varPctText}}</td></tr>`;
                }});
                html += '</tbody></table>';
            }}
            document.getElementById('budget-content').innerHTML = html;
        }}

        function updateTransactionsTab(data) {{
            currentTransactions = data.transactions;
            // Update category filter
            const categories = [...new Set(data.transactions.map(tx => tx.category))].sort();
            const select = document.getElementById('filter-category');
            select.innerHTML = '<option value="">All Categories</option>' + categories.map(c => `<option value="${{c}}">${{c}}</option>`).join('');
            filterTransactions();
        }}

        function filterTransactions() {{
            const category = document.getElementById('filter-category').value;
            const type = document.getElementById('filter-type').value;
            const search = document.getElementById('filter-search').value.toLowerCase();

            let filtered = currentTransactions.filter(tx => {{
                if (category && tx.category !== category) return false;
                if (type === 'income' && tx.amount <= 0) return false;
                if (type === 'expense' && (tx.amount >= 0 || tx.is_savings || tx.is_deduction)) return false;
                if (type === 'savings' && !tx.is_savings) return false;
                if (type === 'deduction' && !tx.is_deduction) return false;
                if (search && !tx.description.toLowerCase().includes(search) && !tx.category.toLowerCase().includes(search)) return false;
                return true;
            }});

            const tbody = document.getElementById('transactions-body');
            tbody.innerHTML = '';
            filtered.forEach(tx => {{
                const row = document.createElement('tr');
                let flags = '';
                if (tx.is_savings) flags += '<span class="flag savings">Savings</span>';
                if (tx.is_deduction) flags += '<span class="flag deduction">Deduction</span>';
                if (tx.is_fixed) flags += '<span class="flag fixed">Fixed</span>';
                row.innerHTML = `<td>${{tx.date}}</td><td>${{tx.category}}</td><td>${{tx.description}}</td><td class="number ${{tx.amount >= 0 ? 'positive' : 'negative'}}">${{formatCurrency(tx.amount)}}</td><td>${{flags}}</td>`;
                tbody.appendChild(row);
            }});

            // Update summary
            const total = filtered.reduce((sum, tx) => sum + tx.amount, 0);
            const income = filtered.filter(tx => tx.amount > 0 && !tx.is_savings).reduce((sum, tx) => sum + tx.amount, 0);
            const expenses = filtered.filter(tx => tx.amount < 0 && !tx.is_savings && !tx.is_deduction).reduce((sum, tx) => sum + Math.abs(tx.amount), 0);
            document.getElementById('filtered-count').textContent = filtered.length;
            document.getElementById('filtered-total').textContent = formatCurrency(total);
            document.getElementById('filtered-total').className = 'stat-value ' + (total >= 0 ? 'positive' : 'negative');
            document.getElementById('filtered-income').textContent = formatCurrency(income);
            document.getElementById('filtered-expenses').textContent = formatCurrency(expenses);
        }}

        document.getElementById('filter-category').addEventListener('change', filterTransactions);
        document.getElementById('filter-type').addEventListener('change', filterTransactions);
        document.getElementById('filter-search').addEventListener('input', filterTransactions);

        function exportCSV() {{
            let csv = 'Date,Category,Description,Amount,Savings,Deduction,Fixed\\n';
            currentTransactions.forEach(tx => {{ csv += `${{tx.date}},"${{tx.category}}","${{tx.description}}",${{tx.amount}},${{tx.is_savings}},${{tx.is_deduction}},${{tx.is_fixed}}\\n`; }});
            const blob = new Blob([csv], {{ type: 'text/csv' }});
            const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'transactions.csv'; a.click();
        }}

        function switchPeriod(period) {{
            currentPeriod = period;
            const data = allPeriodsData[period];
            if (!data) return;
            updateOverviewTab(data);
            updateIncomeExpensesTab(data);
            updateSavingsTab(data);
            updateBudgetTab(data);
            updateTransactionsTab(data);
        }}

        // Hover template helper for currency formatting
        const currencyHover = '%{{x}}<br>%{{fullData.name}}: ' + currency + ' %{{y:,.2f}}<extra></extra>';

        // Initialize all historical charts with formatted hover
        Plotly.newPlot('chart-timeline', [
            {{ x: timelineLabels, y: timelineBalance, name: 'Balance', type: 'scatter', fill: 'tozeroy', line: {{ color: '#3b82f6' }}, hovertemplate: currencyHover }},
            {{ x: timelineLabels, y: timelineSavings, name: 'Savings', type: 'scatter', fill: 'tozeroy', line: {{ color: '#22c55e' }}, hovertemplate: currencyHover }},
            {{ x: timelineLabels, y: timelineAvailable, name: 'Available', type: 'scatter', line: {{ color: '#8b5cf6', dash: 'dash' }}, hovertemplate: currencyHover }},
        ], {{ paper_bgcolor: plotBg, plot_bgcolor: plotBg, font: {{ color: textColor }}, margin: {{ t: 20, r: 20, b: 80, l: 60 }}, legend: {{ orientation: 'h', y: 1.1, bgcolor: 'rgba(0,0,0,0)', font: {{ color: textColor }} }}, xaxis: {{ title: {{ text: '{interval_label}', font: {{ color: textColor }} }}, rangeslider: {{ visible: true, thickness: 0.1, bgcolor: plotBg }}, type: 'category', gridcolor: gridColor, linecolor: gridColor }}, yaxis: {{ title: {{ text: 'Amount ({currency})', font: {{ color: textColor }} }}, gridcolor: gridColor, linecolor: gridColor }} }}, {{ responsive: true }});

        Plotly.newPlot('chart-cashflow', [
            {{ x: timelineLabels, y: timelineIncome, name: 'Income', type: 'bar', marker: {{ color: '#22c55e' }}, hovertemplate: currencyHover }},
            {{ x: timelineLabels, y: timelineExpenses.map(v => -v), name: 'Expenses', type: 'bar', marker: {{ color: '#ef4444' }}, hovertemplate: currencyHover }},
            {{ x: timelineLabels, y: timelineNet, name: 'Net Flow', type: 'scatter', line: {{ color: '#3b82f6' }}, hovertemplate: currencyHover }},
        ], {{ paper_bgcolor: plotBg, plot_bgcolor: plotBg, font: {{ color: textColor }}, barmode: 'relative', margin: {{ t: 20, r: 20, b: 80, l: 60 }}, legend: {{ orientation: 'h', y: 1.1, bgcolor: 'rgba(0,0,0,0)', font: {{ color: textColor }} }}, xaxis: {{ title: {{ text: '{interval_label}', font: {{ color: textColor }} }}, rangeslider: {{ visible: true, thickness: 0.1, bgcolor: plotBg }}, type: 'category', gridcolor: gridColor, linecolor: gridColor }}, yaxis: {{ title: {{ text: 'Amount ({currency})', font: {{ color: textColor }} }}, gridcolor: gridColor, linecolor: gridColor }} }}, {{ responsive: true }});

        Plotly.newPlot('chart-sankey', [{{ type: 'sankey', orientation: 'h', node: {{ pad: 15, thickness: 20, label: {json.dumps(sankey_nodes)}, color: isDarkTheme ? '#3b82f6' : '#2563eb' }}, link: {{ source: {json.dumps(sankey_source)}, target: {json.dumps(sankey_target)}, value: {json.dumps(sankey_value)}, color: isDarkTheme ? 'rgba(59,130,246,0.4)' : 'rgba(37,99,235,0.3)' }}, valueformat: ',.2f', valuesuffix: '' }}], {{ paper_bgcolor: plotBg, plot_bgcolor: plotBg, font: {{ color: textColor }}, margin: {{ t: 20, r: 20, b: 20, l: 20 }} }}, {{ responsive: true }});

        Plotly.newPlot('chart-treemap', [{{ type: 'treemap', labels: {json.dumps(expense_labels)}, parents: {json.dumps([''] * len(expense_labels))}, values: {json.dumps(expense_values)}, textinfo: 'label+value+percent root', textfont: {{ color: '#ffffff' }}, hovertemplate: '%{{label}}<br>' + currency + ' %{{value:,.2f}}<br>%{{percentRoot:.1%}}<extra></extra>', marker: {{ colors: isDarkTheme ? ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'] : ['#2563eb', '#16a34a', '#ca8a04', '#dc2626', '#7c3aed', '#db2777', '#0891b2', '#65a30d'] }} }}], {{ paper_bgcolor: plotBg, plot_bgcolor: plotBg, font: {{ color: textColor }}, margin: {{ t: 20, r: 20, b: 20, l: 20 }} }}, {{ responsive: true }});

        Plotly.newPlot('chart-expenses-timeline', [
            {{ x: timelineLabels, y: timelineFixed, name: 'Fixed', type: 'bar', marker: {{ color: isDarkTheme ? '#6b7280' : '#4b5563' }}, hovertemplate: currencyHover }},
            {{ x: timelineLabels, y: timelineFlexible, name: 'Flexible', type: 'bar', marker: {{ color: '#3b82f6' }}, hovertemplate: currencyHover }},
        ], {{ paper_bgcolor: plotBg, plot_bgcolor: plotBg, font: {{ color: textColor }}, barmode: 'stack', margin: {{ t: 20, r: 20, b: 80, l: 60 }}, legend: {{ orientation: 'h', y: 1.1, bgcolor: 'rgba(0,0,0,0)', font: {{ color: textColor }} }}, xaxis: {{ title: {{ text: '{interval_label}', font: {{ color: textColor }} }}, rangeslider: {{ visible: true, thickness: 0.1, bgcolor: plotBg }}, type: 'category', gridcolor: gridColor, linecolor: gridColor }}, yaxis: {{ title: {{ text: 'Expenses ({currency})', font: {{ color: textColor }} }}, gridcolor: gridColor, linecolor: gridColor }} }}, {{ responsive: true }});

        Plotly.newPlot('chart-savings-timeline', [
            {{ x: timelineLabels, y: timelineSavings, name: 'Actual Savings', type: 'scatter', fill: 'tozeroy', line: {{ color: '#22c55e' }}, hovertemplate: currencyHover }},
            {{ x: timelineLabels, y: timelineTarget, name: 'Target', type: 'scatter', line: {{ color: '#ef4444', dash: 'dash' }}, hovertemplate: currencyHover }},
        ], {{ paper_bgcolor: plotBg, plot_bgcolor: plotBg, font: {{ color: textColor }}, margin: {{ t: 20, r: 20, b: 80, l: 60 }}, legend: {{ orientation: 'h', y: 1.1, bgcolor: 'rgba(0,0,0,0)', font: {{ color: textColor }} }}, xaxis: {{ title: {{ text: '{interval_label}', font: {{ color: textColor }} }}, rangeslider: {{ visible: true, thickness: 0.1, bgcolor: plotBg }}, type: 'category', gridcolor: gridColor, linecolor: gridColor }}, yaxis: {{ title: {{ text: 'Cumulative Savings ({currency})', font: {{ color: textColor }} }}, gridcolor: gridColor, linecolor: gridColor }} }}, {{ responsive: true }});

        // Initialize with current period data
        switchPeriod(currentPeriod);
    </script>
</body>
</html>
"""
    return html
