# Budget Planning Guide

Learn how to create and manage budget plans in FinTrack.

## Income Flow Model

FinTrack uses a top-down income flow:

```
Gross Income
  - Deductions (taxes, social security)
= Net Income
  - Fixed Expenses (rent, utilities, subscriptions)
  - Savings Target
= Disposable Income (money you can spend freely)
```

## Creating a Budget Plan

Create a YAML file in the `plans/` directory:

```yaml
id: "january_2025"
valid_from: "2025-01-01"
# valid_to: "2025-01-31"  # Optional end date

gross_income: 5000.00

deductions:
  - name: "income_tax"
    amount: 1000.00
  - name: "social_security"
    amount: 200.00

fixed_expenses:
  - name: "rent"
    amount: 800.00
    category: "housing"     # Links to transaction category
  - name: "utilities"
    amount: 150.00
    category: "utilities"
  - name: "subscriptions"
    amount: 50.00
    category: "subscriptions"

# Savings configuration (choose one approach)
savings_rate: 0.20          # 20% of savings_base
savings_base: "net_income"  # or "disposable"
# savings_amount: 500.00    # Or fixed amount (overrides rate)

# Budget limits per flexible category
category_budgets:
  - category: "food"
    amount: 400.00
  - category: "transport"
    amount: 150.00
  - category: "entertainment"
    amount: 100.00
```

## Plan Fields

### Required Fields

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `valid_from` | Start date (YYYY-MM-DD) |
| `gross_income` | Total income before deductions |

### Optional Fields

| Field | Default | Description |
|-------|---------|-------------|
| `valid_to` | None | End date (plan valid until next plan) |
| `deductions` | [] | List of pre-income deductions |
| `fixed_expenses` | [] | List of fixed/recurring expenses |
| `savings_rate` | 0.20 | Percentage of savings_base |
| `savings_base` | net_income | Base for savings calculation |
| `savings_amount` | None | Fixed savings (overrides rate) |
| `category_budgets` | [] | Budget limits per category |

## Savings Configuration

### Option 1: Percentage-based

```yaml
savings_rate: 0.20          # 20%
savings_base: "net_income"  # or "disposable"
```

- `net_income`: More ambitious, motivates reducing fixed costs
- `disposable`: More realistic when fixed costs are unavoidable

### Option 2: Fixed Amount

```yaml
savings_amount: 500.00
```

This overrides `savings_rate` if both are specified.

## Category Budgets

Link budget limits to transaction categories:

```yaml
category_budgets:
  - category: "food"
    amount: 400.00
    is_fixed: false     # Optional, default false
  - category: "housing"
    amount: 800.00
    is_fixed: true      # Mark as fixed expense
```

## Multiple Plans

Create plans for different periods:

```
plans/
├── 2024-11.yaml    # November 2024
├── 2024-12.yaml    # December 2024
└── 2025-01.yaml    # January 2025
```

FinTrack automatically selects the appropriate plan based on transaction dates.

## Plan Transitions

When income or expenses change, create a new plan:

```yaml
# plans/2025-02.yaml (after raise)
id: "february_2025_raise"
valid_from: "2025-02-01"
gross_income: 5500.00  # New salary
# ... rest of configuration
```

## Validation

Always validate after creating/editing plans:

```bash
fintrack validate
```

This checks:
- YAML syntax
- Required fields
- Valid date formats
- Logical consistency

## Tips

1. **One plan per major change**: Create new plans when income or expenses change significantly
2. **Match categories**: Use consistent category names between plans and transactions
3. **Review monthly**: Update category budgets based on actual spending patterns
4. **Start conservative**: Begin with realistic budgets, tighten gradually
