"""Constants and default values for FinTrack."""

from decimal import Decimal
from pathlib import Path

# -----------------------------------------------------------------------------
# File Names
# -----------------------------------------------------------------------------

WORKSPACE_CONFIG_FILE = "workspace.yaml"
RATES_FILE = "rates.yaml"
CACHE_DIR = ".cache"
DEFAULT_CACHE_DB = ".cache/fintrack.db"

# -----------------------------------------------------------------------------
# Default Directories
# -----------------------------------------------------------------------------

DEFAULT_TRANSACTIONS_DIR = "transactions"
DEFAULT_PLANS_DIR = "plans"
DEFAULT_REPORTS_DIR = "reports"

# -----------------------------------------------------------------------------
# Default Values
# -----------------------------------------------------------------------------

DEFAULT_CURRENCY = "EUR"
DEFAULT_SAVINGS_RATE = Decimal("0.20")  # 20%
DEFAULT_ANALYSIS_WINDOW = 3  # periods for moving average

# -----------------------------------------------------------------------------
# Period File Naming Patterns
# -----------------------------------------------------------------------------

# Maps IntervalType to strftime format for plan file names
PERIOD_FILE_PATTERNS: dict[str, str] = {
    "day": "%Y-%m-%d",  # 2024-01-15.yaml
    "week": "%Y-W%W",  # 2024-W03.yaml
    "month": "%Y-%m",  # 2024-01.yaml
    "quarter": "%Y-Q{quarter}",  # 2024-Q1.yaml (special handling needed)
    "year": "%Y",  # 2024.yaml
    "custom": "%Y-%m-%d",  # 2024-01-15.yaml (by start date)
}

# -----------------------------------------------------------------------------
# CSV Column Names
# -----------------------------------------------------------------------------

CSV_COLUMNS = [
    "date",
    "amount",
    "currency",
    "category",
    "description",
    "is_savings",
    "is_deduction",
    "is_fixed",
]

CSV_REQUIRED_COLUMNS = ["date", "amount", "currency", "category"]

# -----------------------------------------------------------------------------
# Supported Currencies
# -----------------------------------------------------------------------------

COMMON_CURRENCIES = [
    "EUR",
    "USD",
    "GBP",
    "CHF",
    "RSD",
    "RUB",
    "JPY",
    "CNY",
    "CAD",
    "AUD",
]

# -----------------------------------------------------------------------------
# Template Workspace Content
# -----------------------------------------------------------------------------


def get_example_workspace_yaml(name: str, currency: str = "EUR") -> str:
    """Generate example workspace.yaml content."""
    return f'''name: "{name}"
description: "Personal finance workspace"

interval: "month"
analysis_window: 3

base_currency: "{currency}"
display_currencies: []

transactions_dir: "transactions"
plans_dir: "plans"
reports_dir: "reports"
cache_db: ".cache/fintrack.db"
'''


def get_example_plan_yaml() -> str:
    """Generate example budget plan content."""
    return '''id: "plan_example"
valid_from: "2024-01-01"
valid_to: null

gross_income: 5000.00
income_currency: "EUR"

# Deductions from gross income (before you receive money)
deductions:
  - name: "income_tax"
    amount: 1000.00
  - name: "social_security"
    amount: 200.00

# Fixed expenses from net income (mandatory payments)
fixed_expenses:
  - name: "rent"
    amount: 800.00
    category: "housing"
  - name: "utilities"
    amount: 150.00
    category: "utilities"
  - name: "internet"
    amount: 30.00
    category: "subscriptions"

# Savings settings
savings_rate: 0.20  # 20%
savings_base: "net_income"  # or "disposable"

# Category budgets
category_budgets:
  # Fixed categories
  - category: "housing"
    amount: 800.00
    is_fixed: true
  - category: "utilities"
    amount: 150.00
    is_fixed: true

  # Flexible categories
  - category: "food"
    amount: 400.00
  - category: "transport"
    amount: 150.00
  - category: "entertainment"
    amount: 150.00
'''


def get_example_rates_yaml() -> str:
    """Generate example rates.yaml content."""
    return '''rates:
  - from_currency: "EUR"
    to_currency: "RSD"
    rate: 117.5
    valid_from: "2024-01-01"
    valid_to: null

  - from_currency: "USD"
    to_currency: "EUR"
    rate: 0.92
    valid_from: "2024-01-01"
    valid_to: null
'''


def get_example_csv() -> str:
    """Generate example transactions CSV content."""
    return '''date,amount,currency,category,description,is_savings,is_deduction,is_fixed
2024-01-01,-800.00,EUR,housing,Monthly rent,,,true
2024-01-02,-45.50,EUR,food,Grocery store,,,
2024-01-03,-30.00,EUR,subscriptions,Internet,,,true
2024-01-05,-12.00,EUR,transport,Bus ticket,,,
2024-01-10,5000.00,EUR,salary,January salary,,,
2024-01-10,-1000.00,EUR,tax,Income tax,,true,
2024-01-15,-500.00,EUR,savings,Monthly savings,true,,
2024-01-20,-85.00,EUR,entertainment,Concert tickets,,,
'''
