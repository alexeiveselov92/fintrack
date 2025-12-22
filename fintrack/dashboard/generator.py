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

    html = f"""<!DOCTYPE html>
<html lang="en">
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
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.5;
            color: var(--gray-800);
            background: var(--gray-50);
        }}
        .header {{
            background: white;
            border-bottom: 1px solid var(--gray-200);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ color: var(--primary); font-size: 1.5rem; }}
        .header .meta {{ color: var(--gray-500); font-size: 0.875rem; }}

        .tabs {{
            background: white;
            border-bottom: 1px solid var(--gray-200);
            display: flex;
            padding: 0 2rem;
            gap: 0;
        }}
        .tab {{
            padding: 1rem 1.5rem;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            color: var(--gray-600);
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
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .card-label {{ font-size: 0.875rem; color: var(--gray-500); margin-bottom: 0.25rem; }}
        .card-value {{ font-size: 1.75rem; font-weight: 600; }}
        .card-value.positive {{ color: var(--success); }}
        .card-value.negative {{ color: var(--danger); }}
        .card-trend {{ font-size: 0.875rem; margin-top: 0.5rem; }}
        .card-trend.up {{ color: var(--success); }}
        .card-trend.down {{ color: var(--danger); }}

        .coverage-indicator {{
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
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
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }}
        .chart-title {{ font-size: 1rem; font-weight: 600; margin-bottom: 1rem; color: var(--gray-700); }}

        .section-title {{
            font-size: 1.25rem;
            font-weight: 600;
            margin: 2rem 0 1rem;
            color: var(--gray-800);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }}
        th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--gray-200); }}
        th {{ background: var(--gray-50); font-weight: 600; color: var(--gray-700); }}
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
        .budget-bar .label {{ width: 150px; font-weight: 500; }}
        .budget-bar .bar-container {{
            flex: 1;
            height: 24px;
            background: var(--gray-200);
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
        .budget-bar .value {{ width: 150px; text-align: right; font-variant-numeric: tabular-nums; }}

        .cash-reconciliation {{
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
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
            border: 1px solid var(--gray-300);
            border-radius: 4px;
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
        .btn-remove {{ background: var(--gray-200); color: var(--gray-700); }}
        .cash-total {{
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid var(--gray-200);
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
            border: 1px solid var(--gray-300);
            border-radius: 4px;
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

        .period-selector {{
            display: flex;
            gap: 1rem;
            align-items: center;
            margin-bottom: 2rem;
        }}
        .period-selector select {{
            padding: 0.5rem 1rem;
            border: 1px solid var(--gray-300);
            border-radius: 4px;
            font-size: 1rem;
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

            <div class="chart-container">
                <div class="chart-title">Balance & Savings Timeline</div>
                <div id="chart-timeline"></div>
            </div>

            <div class="chart-container">
                <div class="chart-title">{interval_label}ly Cash Flow</div>
                <div id="chart-cashflow"></div>
            </div>
        </div>

        <!-- ===== INCOME & EXPENSES TAB ===== -->
        <div id="income-expenses" class="tab-content">
            <div class="chart-container">
                <div class="chart-title">Income Flow</div>
                <div id="chart-sankey"></div>
            </div>

            <div class="chart-container">
                <div class="chart-title">Expenses by Category</div>
                <div id="chart-treemap"></div>
            </div>

            <div class="chart-container">
                <div class="chart-title">Expenses Timeline (Fixed vs Flexible)</div>
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

            <div class="chart-container">
                <div class="chart-title">Savings vs Target Timeline</div>
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
                    {_render_savings_transactions(data.transactions, currency)}
                </tbody>
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

        // Timeline chart
        Plotly.newPlot('chart-timeline', [
            {{ x: timelineLabels, y: timelineBalance, name: 'Balance', type: 'scatter', fill: 'tozeroy', line: {{ color: '#3b82f6' }} }},
            {{ x: timelineLabels, y: timelineSavings, name: 'Savings', type: 'scatter', fill: 'tozeroy', line: {{ color: '#16a34a' }} }},
            {{ x: timelineLabels, y: timelineAvailable, name: 'Available', type: 'scatter', line: {{ color: '#8b5cf6', dash: 'dash' }} }},
        ], {{
            margin: {{ t: 20, r: 20, b: 40, l: 60 }},
            legend: {{ orientation: 'h', y: 1.1 }},
            xaxis: {{ title: '{interval_label}' }},
            yaxis: {{ title: 'Amount ({currency})' }},
        }}, {{ responsive: true }});

        // Cash flow chart
        Plotly.newPlot('chart-cashflow', [
            {{ x: timelineLabels, y: timelineIncome, name: 'Income', type: 'bar', marker: {{ color: '#16a34a' }} }},
            {{ x: timelineLabels, y: timelineExpenses.map(v => -v), name: 'Expenses', type: 'bar', marker: {{ color: '#dc2626' }} }},
            {{ x: timelineLabels, y: timelineNet, name: 'Net Flow', type: 'scatter', line: {{ color: '#3b82f6' }} }},
        ], {{
            barmode: 'relative',
            margin: {{ t: 20, r: 20, b: 40, l: 60 }},
            legend: {{ orientation: 'h', y: 1.1 }},
            xaxis: {{ title: '{interval_label}' }},
            yaxis: {{ title: 'Amount ({currency})' }},
        }}, {{ responsive: true }});

        // Sankey
        Plotly.newPlot('chart-sankey', [{{
            type: 'sankey',
            orientation: 'h',
            node: {{
                pad: 15,
                thickness: 20,
                label: {json.dumps(sankey_nodes)},
            }},
            link: {{
                source: {json.dumps(sankey_source)},
                target: {json.dumps(sankey_target)},
                value: {json.dumps(sankey_value)},
            }},
        }}], {{
            margin: {{ t: 20, r: 20, b: 20, l: 20 }},
        }}, {{ responsive: true }});

        // Treemap
        Plotly.newPlot('chart-treemap', [{{
            type: 'treemap',
            labels: {json.dumps(expense_labels)},
            parents: {json.dumps([''] * len(expense_labels))},
            values: {json.dumps(expense_values)},
            textinfo: 'label+value+percent root',
        }}], {{
            margin: {{ t: 20, r: 20, b: 20, l: 20 }},
        }}, {{ responsive: true }});

        // Expenses timeline
        Plotly.newPlot('chart-expenses-timeline', [
            {{ x: timelineLabels, y: timelineFixed, name: 'Fixed', type: 'bar', marker: {{ color: '#6b7280' }} }},
            {{ x: timelineLabels, y: timelineFlexible, name: 'Flexible', type: 'bar', marker: {{ color: '#3b82f6' }} }},
        ], {{
            barmode: 'stack',
            margin: {{ t: 20, r: 20, b: 40, l: 60 }},
            legend: {{ orientation: 'h', y: 1.1 }},
            xaxis: {{ title: '{interval_label}' }},
            yaxis: {{ title: 'Expenses ({currency})' }},
        }}, {{ responsive: true }});

        // Savings timeline
        Plotly.newPlot('chart-savings-timeline', [
            {{ x: timelineLabels, y: timelineSavings, name: 'Actual Savings', type: 'scatter', fill: 'tozeroy', line: {{ color: '#16a34a' }} }},
            {{ x: timelineLabels, y: timelineTarget, name: 'Target', type: 'scatter', line: {{ color: '#dc2626', dash: 'dash' }} }},
        ], {{
            margin: {{ t: 20, r: 20, b: 40, l: 60 }},
            legend: {{ orientation: 'h', y: 1.1 }},
            xaxis: {{ title: '{interval_label}' }},
            yaxis: {{ title: 'Cumulative Savings ({currency})' }},
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
        }}

        document.getElementById('filter-category').addEventListener('change', filterTransactions);
        document.getElementById('filter-type').addEventListener('change', filterTransactions);
        document.getElementById('filter-search').addEventListener('input', filterTransactions);

        renderTransactions(transactionsData);

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


def _render_savings_transactions(transactions: list, currency: str) -> str:
    """Render savings transactions table rows."""
    savings_txs = [tx for tx in transactions if tx.is_savings]
    savings_txs.sort(key=lambda x: x.date, reverse=True)

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
    return "\n".join(rows) if rows else "<tr><td colspan='4'>No savings transactions</td></tr>"


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
        pct = float(actual_income / plan.gross_income * 100) if plan.gross_income > 0 else 0
        bar_class = "ok" if pct >= 100 else "warning" if pct >= 80 else "danger"
        html += f"""
        <h2 class="section-title">Income</h2>
        <div class="budget-bar">
            <div class="label">Gross Income</div>
            <div class="bar-container">
                <div class="bar {bar_class}" style="width: {min(pct, 100)}%"></div>
            </div>
            <div class="value">{_format_currency(actual_income, currency)} / {_format_currency(plan.gross_income, currency)}</div>
        </div>
        """

    # Deductions section
    if plan.total_deductions > 0:
        actual_ded = summary.total_deductions if summary else Decimal(0)
        pct = float(actual_ded / plan.total_deductions * 100) if plan.total_deductions > 0 else 0
        bar_class = "ok" if pct <= 100 else "danger"
        html += f"""
        <h2 class="section-title">Deductions</h2>
        <div class="budget-bar">
            <div class="label">Total Deductions</div>
            <div class="bar-container">
                <div class="bar {bar_class}" style="width: {min(pct, 100)}%"></div>
            </div>
            <div class="value">{_format_currency(actual_ded, currency)} / {_format_currency(plan.total_deductions, currency)}</div>
        </div>
        """

    # Fixed expenses section
    if plan.total_fixed_expenses > 0:
        actual_fixed = summary.total_fixed_expenses if summary else Decimal(0)
        pct = float(actual_fixed / plan.total_fixed_expenses * 100) if plan.total_fixed_expenses > 0 else 0
        bar_class = "ok" if pct <= 100 else "danger"
        html += f"""
        <h2 class="section-title">Fixed Expenses</h2>
        <div class="budget-bar">
            <div class="label">Total Fixed</div>
            <div class="bar-container">
                <div class="bar {bar_class}" style="width: {min(pct, 100)}%"></div>
            </div>
            <div class="value">{_format_currency(actual_fixed, currency)} / {_format_currency(plan.total_fixed_expenses, currency)}</div>
        </div>
        """

    # Flexible spending section
    if plan.disposable_income > 0:
        actual_flex = summary.total_flexible_expenses if summary else Decimal(0)
        pct = float(actual_flex / plan.disposable_income * 100) if plan.disposable_income > 0 else 0
        bar_class = "ok" if pct <= 80 else "warning" if pct <= 100 else "danger"
        html += f"""
        <h2 class="section-title">Flexible Spending</h2>
        <div class="budget-bar">
            <div class="label">Disposable</div>
            <div class="bar-container">
                <div class="bar {bar_class}" style="width: {min(pct, 100)}%"></div>
            </div>
            <div class="value">{_format_currency(actual_flex, currency)} / {_format_currency(plan.disposable_income, currency)}</div>
        </div>
        """

    # Savings section
    if plan.savings_target > 0:
        actual_savings = summary.total_savings if summary else Decimal(0)
        pct = float(actual_savings / plan.savings_target * 100) if plan.savings_target > 0 else 0
        bar_class = "ok" if pct >= 100 else "warning" if pct >= 50 else "danger"
        html += f"""
        <h2 class="section-title">Savings</h2>
        <div class="budget-bar">
            <div class="label">Savings Target</div>
            <div class="bar-container">
                <div class="bar {bar_class}" style="width: {min(pct, 100)}%"></div>
            </div>
            <div class="value">{_format_currency(actual_savings, currency)} / {_format_currency(plan.savings_target, currency)}</div>
        </div>
        """

    # Category breakdown table
    html += """
    <h2 class="section-title">Category Breakdown</h2>
    <table>
        <thead>
            <tr>
                <th>Category</th>
                <th class="number">Actual</th>
                <th class="number">Planned</th>
                <th class="number">Variance</th>
            </tr>
        </thead>
        <tbody>
    """

    for cat in sorted(data.categories, key=lambda x: x.actual_amount, reverse=True):
        if cat.actual_amount == 0 and not cat.planned_amount:
            continue
        variance_class = ""
        variance_text = "-"
        if cat.variance_vs_plan is not None:
            if cat.variance_vs_plan > 0:
                variance_class = "positive"
                variance_text = f"+{_format_currency(cat.variance_vs_plan, currency)}"
            elif cat.variance_vs_plan < 0:
                variance_class = "negative"
                variance_text = _format_currency(cat.variance_vs_plan, currency)
            else:
                variance_text = _format_currency(Decimal(0), currency)

        html += f"""
            <tr>
                <td>{cat.category}{' <span class="flag fixed">Fixed</span>' if cat.is_fixed else ''}</td>
                <td class="number">{_format_currency(cat.actual_amount, currency)}</td>
                <td class="number">{_format_currency(cat.planned_amount, currency) if cat.planned_amount else '-'}</td>
                <td class="number {variance_class}">{variance_text}</td>
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
