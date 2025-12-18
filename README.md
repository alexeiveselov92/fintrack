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

## Installation

```bash
pip install fintrack-cli
```

## Quick Start

### 1. Create a Workspace

```bash
fintrack init my_finances
cd my_finances
```

### 2. Create a Budget Plan

Edit `plans/2024-12.yaml`:

```yaml
id: "december_2024"
valid_from: "2024-12-01"

gross_income: 5000.00
income_currency: "EUR"

deductions:
  - name: "income_tax"
    amount: 1000.00
  - name: "social_security"
    amount: 200.00

fixed_expenses:
  - name: "rent"
    amount: 800.00
    category: "housing"
  - name: "utilities"
    amount: 150.00
    category: "utilities"

savings_rate: 0.20  # 20% savings goal
savings_base: "net_income"

category_budgets:
  - category: "housing"
    amount: 800.00
    is_fixed: true
  - category: "food"
    amount: 400.00
  - category: "transport"
    amount: 150.00
```

### 3. Import Transactions

Create a CSV file in `transactions/`:

```csv
date,amount,currency,category,description,is_savings,is_deduction,is_fixed
2024-12-01,-800.00,EUR,housing,Monthly rent,,,true
2024-12-02,-50.00,EUR,food,Groceries,,,
2024-12-10,5000.00,EUR,salary,December salary,,,
2024-12-10,-1000.00,EUR,tax,Income tax,,true,
2024-12-15,-500.00,EUR,savings,Monthly savings,true,,
```

Import:

```bash
fintrack import transactions/
```

### 4. Analyze Your Finances

```bash
# View budget projection
fintrack budget

# Quick status overview
fintrack status

# Detailed analysis with history
fintrack analyze

# Generate HTML report
fintrack report
```

## Commands

| Command | Description |
|---------|-------------|
| `fintrack init <name>` | Create a new workspace |
| `fintrack validate` | Validate configuration files |
| `fintrack import <path>` | Import transactions from CSV |
| `fintrack budget [--period]` | Show budget projection |
| `fintrack status [--period]` | Show current period status |
| `fintrack analyze [--period]` | Full analysis with comparisons |
| `fintrack report [--period]` | Generate HTML report |
| `fintrack list transactions` | List transactions |
| `fintrack list plans` | List budget plans |
| `fintrack list categories` | List categories |

## Transaction Flags

- `is_fixed`: Fixed/recurring expense (rent, subscriptions)
- `is_savings`: Money transferred to savings
- `is_deduction`: Pre-income deduction (taxes)

## Workspace Structure

```
my_finances/
├── workspace.yaml        # Workspace configuration
├── plans/                # Budget plan files
│   └── 2024-12.yaml
├── rates.yaml            # Exchange rates (optional)
├── transactions/         # CSV transaction files
│   └── december.csv
├── reports/              # Generated HTML reports
└── .cache/               # SQLite database
```

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
