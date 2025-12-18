# FinTrack

**Personal Finance Tracker CLI** - Budget planning and expense analysis tool.

[![PyPI version](https://badge.fury.io/py/fintrack-cli.svg)](https://pypi.org/project/fintrack-cli/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Budget Planning**: Define income, deductions, fixed expenses, and savings goals
- **Transaction Import**: Import transactions from CSV files with idempotent processing
- **Expense Analysis**: Compare actual spending against budget with variance analysis
- **Historical Comparison**: Track spending patterns with moving averages
- **HTML Reports**: Generate beautiful reports with progress visualization
- **Flexible Periods**: Support for day, week, month, quarter, year, or custom intervals

## Key Concepts

FinTrack separates your finances into clear categories:

```
Gross Income
  - Deductions (taxes, social security)
= Net Income
  - Fixed Expenses (rent, utilities, subscriptions)
  - Savings Target
= Disposable Income (money you can actually spend)
```

**Transaction Flags** - each transaction can have flags:
- `is_deduction`: Pre-income deductions (taxes, social security) - subtracted from gross income
- `is_fixed`: Fixed/recurring expenses (rent, subscriptions) - subtracted from net income
- `is_savings`: Money transferred to savings - tracked separately

## Installation

```bash
pip install fintrack-cli
```

### Alternative: From GitHub (latest development version)

```bash
pip install git+https://github.com/alexeiveselov92/fintrack.git
```

### Alternative: Local Development

```bash
git clone https://github.com/alexeiveselov92/fintrack.git
cd fintrack
pip install -e .
```

### Verify Installation

```bash
fintrack --help
```

## Quick Start

### Step 1: Create a Workspace

```bash
fintrack init my_finances
cd my_finances
```

This creates:
```
my_finances/
├── workspace.yaml        # Workspace configuration
├── plans/                # Budget plan files (empty)
├── transactions/         # CSV transaction files (empty)
├── reports/              # Generated HTML reports (empty)
└── .cache/               # SQLite database (created on import)
```

### Step 2: Create Your Budget Plan

Create a file `plans/2024-12.yaml`:

```yaml
# Unique identifier for this budget plan
id: "december_2024"

# When this plan becomes active
valid_from: "2024-12-01"

# Your gross monthly income (before any deductions)
gross_income: 5000.00
income_currency: "EUR"

# Pre-tax deductions (subtracted from gross to get net income)
deductions:
  - name: "income_tax"
    amount: 1000.00
  - name: "social_security"
    amount: 200.00

# Fixed monthly expenses (rent, subscriptions, etc.)
fixed_expenses:
  - name: "rent"
    amount: 800.00
    category: "housing"
  - name: "utilities"
    amount: 150.00
    category: "utilities"

# Savings: specify rate OR fixed amount
savings_rate: 0.20  # 20% of savings_base
savings_base: "net_income"  # or "disposable_income"
# savings_amount: 500.00  # Or fixed amount (takes priority over rate)

# Budget limits per category (for flexible spending)
category_budgets:
  - category: "food"
    amount: 400.00
  - category: "transport"
    amount: 150.00
  - category: "entertainment"
    amount: 100.00
  - category: "health"
    amount: 50.00
```

### Step 3: Validate Your Configuration

```bash
fintrack validate
```

Expected output:
```
Validation Results
==================

Workspace: OK
  Path: /path/to/my_finances

Budget Plans:
  plans/2024-12.yaml: OK
    ID: december_2024
    Valid from: 2024-12-01
    Gross: 5000.00 EUR
    Net: 3800.00 EUR
    Disposable: 2040.00 EUR
```

### Step 4: Import Your Transactions

Create a CSV file `transactions/december.csv`:

```csv
date,amount,currency,category,description,is_savings,is_deduction,is_fixed
2024-12-01,5000.00,EUR,salary,December salary,false,false,false
2024-12-01,-1000.00,EUR,tax,Income tax,false,true,false
2024-12-01,-200.00,EUR,social,Social security,false,true,false
2024-12-01,-800.00,EUR,housing,Monthly rent,false,false,true
2024-12-02,-150.00,EUR,utilities,Electricity + water,false,false,true
2024-12-03,-45.50,EUR,food,Weekly groceries,false,false,false
2024-12-05,-12.00,EUR,transport,Bus ticket,false,false,false
2024-12-07,-85.00,EUR,food,Restaurant dinner,false,false,false
2024-12-10,-500.00,EUR,savings,Monthly savings transfer,true,false,false
2024-12-15,-30.00,EUR,entertainment,Netflix + Spotify,false,false,true
2024-12-18,-50.00,EUR,food,Groceries,false,false,false
2024-12-20,-25.00,EUR,health,Pharmacy,false,false,false
```

Import the transactions:

```bash
fintrack import transactions/
```

Output:
```
Import Results
==============

File: transactions/december.csv
  Transactions: 12
  New: 12
  Duplicates: 0

Total imported: 12
```

**Note**: Import is idempotent - running it again won't create duplicates.

### Step 5: View Your Budget

```bash
fintrack budget
```

Shows your budget plan projection:
```
Budget Plan: december_2024
==========================
Period: December 2024

Income Flow
-----------
Gross Income:        5,000.00 EUR
- Deductions:       -1,200.00 EUR
  = Net Income:      3,800.00 EUR
- Fixed Expenses:     -950.00 EUR
- Savings Target:     -760.00 EUR
  = Disposable:      2,090.00 EUR

Category Budgets
----------------
housing:        800.00 EUR (fixed)
utilities:      200.00 EUR (fixed)
food:           400.00 EUR
transport:      150.00 EUR
entertainment:  100.00 EUR
health:          50.00 EUR
```

### Step 6: Check Current Status

```bash
fintrack status
```

Shows actual spending vs budget:
```
Status: December 2024
=====================

Budget Progress
---------------
Disposable Budget:  2,090.00 EUR
Variable Spent:       247.50 EUR
Remaining:          1,842.50 EUR (88.2%)

Category Status
---------------
food:           180.50 / 400.00 EUR (45.1%) - On track
transport:       12.00 / 150.00 EUR (8.0%)  - On track
entertainment:   30.00 / 100.00 EUR (30.0%) - On track
health:          25.00 /  50.00 EUR (50.0%) - On track

Savings Progress
----------------
Target:   760.00 EUR
Actual:   500.00 EUR (65.8%)
```

### Step 7: Full Analysis

```bash
fintrack analyze
```

Shows detailed analysis with historical comparison.

### Step 8: Generate HTML Report

```bash
fintrack report
```

Creates a visual HTML report in `reports/` directory.

## CSV Format Reference

### Required Columns

| Column | Type | Description |
|--------|------|-------------|
| `date` | YYYY-MM-DD | Transaction date |
| `amount` | Decimal | Amount (positive = income, negative = expense) |
| `currency` | String | Currency code (EUR, USD, etc.) |
| `category` | String | Category name |

### Optional Columns

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `description` | String | empty | Transaction description |
| `is_savings` | Boolean | false | Mark as savings transfer |
| `is_deduction` | Boolean | false | Mark as pre-tax deduction |
| `is_fixed` | Boolean | false | Mark as fixed expense |

### Boolean Values

These values are treated as `true`: `true`, `True`, `TRUE`, `1`, `yes`, `Yes`, `YES`

Everything else (including empty) is treated as `false`.

### Example: Different Transaction Types

```csv
date,amount,currency,category,description,is_savings,is_deduction,is_fixed
# Income (positive amount)
2024-12-01,5000.00,EUR,salary,Monthly salary,,,

# Tax deduction (negative, is_deduction=true)
2024-12-01,-1000.00,EUR,tax,Income tax,,true,

# Fixed expense (negative, is_fixed=true)
2024-12-01,-800.00,EUR,housing,Rent,,,true

# Savings (negative, is_savings=true)
2024-12-15,-500.00,EUR,savings,Emergency fund,true,,

# Variable expense (negative, no flags)
2024-12-10,-45.00,EUR,food,Groceries,,,
```

## Commands Reference

### `fintrack init <name>`

Create a new workspace.

```bash
fintrack init my_finances
```

### `fintrack validate`

Validate workspace configuration and budget plans.

```bash
fintrack validate
```

### `fintrack import <path>`

Import transactions from CSV file(s).

```bash
# Import single file
fintrack import transactions/december.csv

# Import all files in directory
fintrack import transactions/

# Force re-import (ignore duplicates check)
fintrack import transactions/ --force
```

### `fintrack budget`

Show budget projection from plan.

```bash
# Current month
fintrack budget

# Specific period
fintrack budget --period 2024-12
fintrack budget --period 2024-Q4
fintrack budget --period 2024
```

### `fintrack status`

Show current spending status vs budget.

```bash
fintrack status
fintrack status --period 2024-12
```

### `fintrack analyze`

Full analysis with historical comparison.

```bash
fintrack analyze
fintrack analyze --period 2024-12
fintrack analyze --history 6  # Compare with last 6 periods
```

### `fintrack report`

Generate HTML report.

```bash
fintrack report
fintrack report --output my_report.html
fintrack report --period 2024-12
```

### `fintrack list`

List various items.

```bash
fintrack list transactions
fintrack list transactions --period 2024-12
fintrack list transactions --category food
fintrack list plans
fintrack list categories
```

## Period Formats

| Format | Example | Description |
|--------|---------|-------------|
| Month | `2024-12` | December 2024 |
| Quarter | `2024-Q4` | Q4 2024 (Oct-Dec) |
| Year | `2024` | Full year 2024 |
| Day | `2024-12-15` | Specific day |
| Week | `2024-W50` | Week 50 of 2024 |
| Range | `2024-12-01:2024-12-31` | Custom date range |

## Multi-Currency Support (Optional)

Create `rates.yaml` in workspace root:

```yaml
base_currency: "EUR"
rates:
  USD: 0.92  # 1 USD = 0.92 EUR
  GBP: 1.17  # 1 GBP = 1.17 EUR
```

## Workspace Structure

```
my_finances/
├── workspace.yaml        # Workspace configuration
├── plans/                # Budget plan files
│   ├── 2024-11.yaml
│   └── 2024-12.yaml
├── rates.yaml            # Exchange rates (optional)
├── transactions/         # CSV transaction files
│   ├── november.csv
│   └── december.csv
├── reports/              # Generated HTML reports
│   └── report_2024-12.html
└── .cache/               # SQLite database
    └── fintrack.db
```

## Tips

1. **Start simple**: Begin with basic categories, add more as needed
2. **One plan per month**: Create monthly budget plans to track changes
3. **Consistent categories**: Use same category names in plans and transactions
4. **Regular imports**: Import transactions weekly to stay on track
5. **Review reports**: Generate HTML reports for visual analysis

## Troubleshooting

### "No budget plan found for period"

Create a budget plan with `valid_from` date before your transaction dates.

### "Validation failed"

Run `fintrack validate` to see detailed error messages for your config files.

### "Import shows 0 new transactions"

The file was already imported. Use `--force` to re-import.

### CSV encoding issues

Ensure your CSV file is UTF-8 encoded.

## Development

```bash
# Clone repository
git clone https://github.com/alexeiveselov92/fintrack.git
cd fintrack

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check fintrack
mypy fintrack
```

## License

MIT License - see [LICENSE](LICENSE) file.

## Author

Alexei Veselov ([@alexeiveselov92](https://github.com/alexeiveselov92))
