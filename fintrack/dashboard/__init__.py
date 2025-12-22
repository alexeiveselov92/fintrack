"""Dashboard module for interactive HTML report generation.

This module provides the data layer and HTML generation for the
5-tab interactive financial dashboard.

Tabs:
    1. Overview - KPIs, Cash Reconciliation, Timeline charts
    2. Income & Expenses - Sankey, Treemap, Expenses Timeline
    3. Savings - Coverage Indicator, Savings Timeline
    4. Budget - Budget vs Actual, Alerts
    5. Transactions - Filterable table with export
"""

from fintrack.dashboard.data_provider import DashboardDataProvider
from fintrack.dashboard.generator import generate_dashboard_html, save_dashboard

__all__ = [
    "DashboardDataProvider",
    "generate_dashboard_html",
    "save_dashboard",
]
