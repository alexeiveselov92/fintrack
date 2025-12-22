# FinTrack

**Personal Finance Tracker CLI** - Budget planning and expense analysis tool.

[![PyPI version](https://badge.fury.io/py/fintrack-cli.svg)](https://pypi.org/project/fintrack-cli/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Budget Planning**: Define income, deductions, fixed expenses, and savings goals
- **Transaction Import**: Import transactions from CSV with idempotent processing
- **Interactive Dashboard**: 5-tab HTML dashboard with Plotly charts and range sliders
- **Dark/Light Theme**: Toggle dashboard theme in workspace configuration
- **All-Periods View**: Single dashboard with period switcher dropdown
- **Savings Coverage**: Track if available funds can cover savings gaps
- **Expense Analysis**: Compare spending against budget with variance analysis
- **Flexible Periods**: Support for day, week, month, quarter, year, or custom intervals

## Installation

```bash
pip install fintrack-cli
```

## Quick Start

```bash
# Create workspace
fintrack init my_finances
cd my_finances

# Create budget plan in plans/2024-12.yaml
# Import transactions from transactions/*.csv
fintrack import

# View status and generate dashboard
fintrack status
fintrack report
```

See [Quick Start Guide](docs/quick-start.md) for detailed steps.

## Key Concepts

```
Gross Income
  - Deductions (taxes, social security)
= Net Income
  - Fixed Expenses (rent, utilities, subscriptions)
  - Savings Target
= Disposable Income (money you can actually spend)
```

**Transaction Flags:**
- `is_deduction`: Pre-income deductions (taxes)
- `is_fixed`: Fixed/recurring expenses (rent)
- `is_savings`: Savings transfers

## Commands

| Command | Description |
|---------|-------------|
| `fintrack init <name>` | Create new workspace |
| `fintrack validate` | Validate configuration |
| `fintrack import [path]` | Import CSV transactions |
| `fintrack budget` | Show budget projection |
| `fintrack status` | Quick spending overview |
| `fintrack analyze` | Full analysis with history |
| `fintrack report` | Generate HTML dashboard |
| `fintrack list <type>` | List transactions/plans/categories |

## Dashboard

`fintrack report` generates an interactive HTML dashboard with 5 tabs:

1. **Overview** - KPIs, Cash Reconciliation, Timeline charts
2. **Income & Expenses** - Sankey diagram, Category Treemap
3. **Savings** - Coverage Indicator, Savings vs Target
4. **Budget** - Budget vs Actual progress bars with variance display
5. **Transactions** - Filterable table with totals and CSV export

### Dashboard Options

```bash
# Generate dashboard for current period
fintrack report

# Generate dashboard for specific period
fintrack report --period 2024-11

# Generate all-periods dashboard with period switcher
fintrack report --all
```

The `--all` flag creates a single HTML file with a dropdown to switch between all periods.

### Dark Theme

Add `theme: "dark"` to your `workspace.yaml`:

```yaml
name: my_finances
base_currency: EUR
interval: month
theme: dark  # Options: light (default), dark
```

Then regenerate the dashboard: `fintrack report`

See [Dashboard Guide](docs/dashboard.md) for details.

## Documentation

- [Quick Start Guide](docs/quick-start.md)
- [Budget Planning Guide](docs/budget-planning.md)
- [Dashboard Guide](docs/dashboard.md)

## CSV Format

```csv
date,amount,category,description,is_savings,is_deduction,is_fixed
2024-12-01,5000.00,salary,Monthly salary,,,
2024-12-01,-1000.00,tax,Income tax,,true,
2024-12-01,-800.00,housing,Rent,,,true
2024-12-10,-500.00,savings,Savings transfer,true,,
2024-12-15,-45.00,food,Groceries,,,
```

**Notes:**
- All amounts in workspace `base_currency`
- Positive = income, Negative = expense
- Boolean flags: `true`/`false` or `1`/`0`

## Budget Plan Example

```yaml
id: "december_2024"
valid_from: "2024-12-01"

gross_income: 5000.00

deductions:
  - name: "income_tax"
    amount: 1000.00

fixed_expenses:
  - name: "rent"
    amount: 800.00
    category: "housing"

savings_rate: 0.20
savings_base: "net_income"

category_budgets:
  - category: "food"
    amount: 400.00
```

## Development

```bash
git clone https://github.com/alexeiveselov92/fintrack.git
cd fintrack
pip install -e ".[dev]"
pytest
```

## License

MIT License - see [LICENSE](LICENSE) file.

## Author

Alexei Veselov ([@alexeiveselov92](https://github.com/alexeiveselov92))
