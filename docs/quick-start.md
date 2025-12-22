# Quick Start Guide

Get up and running with FinTrack in 5 minutes.

## Installation

```bash
pip install fintrack-cli
```

## Step 1: Create a Workspace

```bash
fintrack init my_finances
cd my_finances
```

This creates:
```
my_finances/
├── workspace.yaml        # Configuration
├── plans/                # Budget plans
├── transactions/         # CSV files
├── reports/              # Generated reports
└── .cache/               # Database
```

**Optional:** Edit `workspace.yaml` to enable dark theme:
```yaml
name: my_finances
base_currency: EUR
interval: month
theme: dark  # Optional: light (default) or dark
```

## Step 2: Create a Budget Plan

Create `plans/2024-12.yaml`:

```yaml
id: "december_2024"
valid_from: "2024-12-01"

gross_income: 5000.00

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

savings_rate: 0.20
savings_base: "net_income"

category_budgets:
  - category: "food"
    amount: 400.00
  - category: "transport"
    amount: 150.00
```

## Step 3: Validate

```bash
fintrack validate
```

## Step 4: Import Transactions

Create `transactions/december.csv`:

```csv
date,amount,category,description,is_savings,is_deduction,is_fixed
2024-12-01,5000.00,salary,December salary,,,
2024-12-01,-1000.00,tax,Income tax,,true,
2024-12-01,-800.00,housing,Rent,,,true
2024-12-03,-45.50,food,Groceries,,,
2024-12-10,-500.00,savings,Savings transfer,true,,
```

Import:
```bash
fintrack import
```

## Step 5: View Status

```bash
fintrack status
```

## Step 6: Generate Dashboard

```bash
# Current period dashboard
fintrack report

# All periods in one dashboard (with period switcher)
fintrack report --all
```

Open the HTML file in your browser to see the interactive dashboard.

## Next Steps

- [Budget Planning Guide](budget-planning.md)
- [CSV Format Reference](csv-format.md)
- [Dashboard Guide](dashboard.md)
- [Commands Reference](commands.md)
