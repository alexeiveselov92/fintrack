"""HTML report generation."""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from fintrack.core.models import BudgetPlan, CategoryAnalysis, PeriodSummary


def format_currency_html(amount: Decimal, currency: str = "EUR") -> str:
    """Format currency for HTML display."""
    symbols = {"EUR": "€", "USD": "$", "GBP": "£", "RSD": "RSD "}
    symbol = symbols.get(currency, f"{currency} ")
    if amount < 0:
        return f'<span class="negative">-{symbol}{abs(amount):,.2f}</span>'
    return f"{symbol}{amount:,.2f}"


def format_variance_html(amount: Decimal | None, currency: str = "EUR") -> str:
    """Format variance with color classes."""
    if amount is None:
        return "-"
    if amount > 0:
        return f'<span class="positive">+{format_currency_html(amount, currency)}</span>'
    elif amount < 0:
        return f'<span class="negative">{format_currency_html(amount, currency)}</span>'
    return format_currency_html(amount, currency)


def generate_report_html(
    period_str: str,
    workspace_name: str,
    plan: BudgetPlan | None,
    summary: PeriodSummary,
    analyses: list[CategoryAnalysis],
    currency: str = "EUR",
) -> str:
    """Generate HTML report content.

    Args:
        period_str: Period string for display.
        workspace_name: Workspace name.
        plan: BudgetPlan if available.
        summary: PeriodSummary with aggregated data.
        analyses: List of CategoryAnalysis.
        currency: Currency code.

    Returns:
        HTML string.
    """
    # Separate fixed and flexible
    fixed_analyses = [a for a in analyses if a.is_fixed and a.actual_amount > 0]
    flexible_analyses = [a for a in analyses if not a.is_fixed and a.actual_amount > 0]

    # Calculate totals
    total_fixed = sum(a.actual_amount for a in fixed_analyses)
    total_flexible = sum(a.actual_amount for a in flexible_analyses)

    # Calculate progress percentages
    fixed_pct = 0
    flexible_pct = 0
    savings_pct = 0

    if plan:
        if plan.total_fixed_expenses > 0:
            fixed_pct = float(total_fixed / plan.total_fixed_expenses * 100)
        if plan.disposable_income > 0:
            flexible_pct = float(total_flexible / plan.disposable_income * 100)
        if plan.savings_target > 0:
            savings_pct = float(summary.total_savings / plan.savings_target * 100)

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FinTrack Report - {period_str}</title>
    <style>
        :root {{
            --primary: #2563eb;
            --success: #16a34a;
            --warning: #ca8a04;
            --danger: #dc2626;
            --gray-50: #f9fafb;
            --gray-100: #f3f4f6;
            --gray-200: #e5e7eb;
            --gray-600: #4b5563;
            --gray-800: #1f2937;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.5;
            color: var(--gray-800);
            background: var(--gray-50);
            padding: 2rem;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        h1 {{ color: var(--primary); margin-bottom: 0.5rem; }}
        h2 {{ color: var(--gray-800); margin: 1.5rem 0 1rem; border-bottom: 2px solid var(--gray-200); padding-bottom: 0.5rem; }}
        .meta {{ color: var(--gray-600); margin-bottom: 2rem; }}
        .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
        .card {{
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .card-label {{ font-size: 0.875rem; color: var(--gray-600); margin-bottom: 0.25rem; }}
        .card-value {{ font-size: 1.5rem; font-weight: 600; }}
        .card-value.positive {{ color: var(--success); }}
        .card-value.negative {{ color: var(--danger); }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 1.5rem; }}
        th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--gray-200); }}
        th {{ background: var(--gray-100); font-weight: 600; }}
        td.number {{ text-align: right; font-variant-numeric: tabular-nums; }}
        tr:last-child td {{ border-bottom: none; }}
        .positive {{ color: var(--success); }}
        .negative {{ color: var(--danger); }}
        .progress-bar {{ background: var(--gray-200); border-radius: 4px; height: 8px; overflow: hidden; }}
        .progress-fill {{ height: 100%; transition: width 0.3s; }}
        .progress-fill.ok {{ background: var(--success); }}
        .progress-fill.warning {{ background: var(--warning); }}
        .progress-fill.danger {{ background: var(--danger); }}
        .summary-box {{ background: white; border-radius: 8px; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .footer {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--gray-200); color: var(--gray-600); font-size: 0.875rem; }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .card, table, .summary-box {{ box-shadow: none; border: 1px solid var(--gray-200); }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Financial Report</h1>
        <p class="meta">
            {workspace_name} &bull; Period: {period_str} &bull;
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </p>

        <div class="cards">
            <div class="card">
                <div class="card-label">Total Income</div>
                <div class="card-value">{format_currency_html(summary.total_income, currency)}</div>
            </div>
            <div class="card">
                <div class="card-label">Total Expenses</div>
                <div class="card-value">{format_currency_html(summary.total_expenses, currency)}</div>
            </div>
            <div class="card">
                <div class="card-label">Savings</div>
                <div class="card-value {'positive' if summary.total_savings > 0 else ''}">{format_currency_html(summary.total_savings, currency)}</div>
            </div>
            {"<div class='card'><div class='card-label'>Disposable Budget</div><div class='card-value'>" + format_currency_html(plan.disposable_income, currency) + "</div></div>" if plan else ""}
        </div>
"""

    # Progress bars if plan exists
    if plan:
        html += f"""
        <h2>Budget Progress</h2>
        <div class="summary-box">
            <div style="margin-bottom: 1rem;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                    <span>Fixed Expenses</span>
                    <span>{format_currency_html(total_fixed, currency)} / {format_currency_html(plan.total_fixed_expenses, currency)} ({fixed_pct:.0f}%)</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill {'ok' if fixed_pct <= 100 else 'danger'}" style="width: {min(fixed_pct, 100)}%"></div>
                </div>
            </div>
            <div style="margin-bottom: 1rem;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                    <span>Flexible Spending</span>
                    <span>{format_currency_html(total_flexible, currency)} / {format_currency_html(plan.disposable_income, currency)} ({flexible_pct:.0f}%)</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill {'ok' if flexible_pct <= 80 else 'warning' if flexible_pct <= 100 else 'danger'}" style="width: {min(flexible_pct, 100)}%"></div>
                </div>
            </div>
            <div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                    <span>Savings Target</span>
                    <span>{format_currency_html(summary.total_savings, currency)} / {format_currency_html(plan.savings_target, currency)} ({savings_pct:.0f}%)</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill {'ok' if savings_pct >= 100 else 'warning' if savings_pct >= 50 else 'danger'}" style="width: {min(savings_pct, 100)}%"></div>
                </div>
            </div>
        </div>
"""

    # Fixed categories table
    if fixed_analyses:
        html += """
        <h2>Fixed Expenses</h2>
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
        for a in sorted(fixed_analyses, key=lambda x: x.actual_amount, reverse=True):
            html += f"""
                <tr>
                    <td>{a.category}</td>
                    <td class="number">{format_currency_html(a.actual_amount, currency)}</td>
                    <td class="number">{format_currency_html(a.planned_amount, currency) if a.planned_amount else '-'}</td>
                    <td class="number">{format_variance_html(a.variance_vs_plan, currency)}</td>
                </tr>
"""
        html += """
            </tbody>
        </table>
"""

    # Flexible categories table
    if flexible_analyses:
        html += """
        <h2>Flexible Expenses</h2>
        <table>
            <thead>
                <tr>
                    <th>Category</th>
                    <th class="number">Actual</th>
                    <th class="number">Planned</th>
                    <th class="number">Average</th>
                    <th class="number">vs Plan</th>
                </tr>
            </thead>
            <tbody>
"""
        for a in sorted(flexible_analyses, key=lambda x: x.actual_amount, reverse=True):
            html += f"""
                <tr>
                    <td>{a.category}</td>
                    <td class="number">{format_currency_html(a.actual_amount, currency)}</td>
                    <td class="number">{format_currency_html(a.planned_amount, currency) if a.planned_amount else '-'}</td>
                    <td class="number">{format_currency_html(a.historical_average, currency) if a.historical_average else '-'}</td>
                    <td class="number">{format_variance_html(a.variance_vs_plan, currency)}</td>
                </tr>
"""
        html += """
            </tbody>
        </table>
"""

    html += f"""
        <div class="footer">
            <p>FinTrack &bull; {summary.transaction_count} transactions analyzed</p>
        </div>
    </div>
</body>
</html>
"""

    return html


def save_report(html: str, output_path: Path) -> None:
    """Save HTML report to file.

    Args:
        html: HTML content.
        output_path: Output file path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
