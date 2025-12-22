# Dashboard Guide

FinTrack generates an interactive HTML dashboard with 5 tabs, providing comprehensive financial analysis.

## Generating the Dashboard

```bash
# Generate for current period
fintrack report

# Generate for specific period
fintrack report --period 2024-12

# Generate all-periods dashboard with period switcher
fintrack report --all
```

Options:
- `--period/-p`: Specify period (e.g., `2024-12`)
- `--all/-a`: Generate single HTML with all periods (dropdown to switch)
- `--output/-o`: Custom output path
- `--workspace/-w`: Workspace path

## Theme Configuration

FinTrack supports light and dark themes. Configure in `workspace.yaml`:

```yaml
name: my_finances
base_currency: EUR
interval: month
theme: dark  # Options: light (default), dark
```

Regenerate the dashboard after changing the theme:
```bash
fintrack report
```

## Dashboard Tabs

### 1. Overview

**Key Performance Indicators (KPIs):**
- **Current Balance**: Total income minus expenses (cumulative)
- **Total Savings**: Cumulative savings amount
- **Available Funds**: Cash on hand (balance minus savings)
- **Savings Gap**: Difference between target and actual savings
- **True Discretionary**: Money truly available after covering savings gap

**Coverage Indicator:**
Shows if your available funds can cover any savings shortfall:
- Green checkmark: You can cover the gap
- Warning: Cannot cover - need to catch up on savings

**Cash Reconciliation Calculator:**
Compare your actual account balances with expected available funds:
1. Enter each account/source and its balance
2. Compare total with Available Funds
3. Identify discrepancies

**Charts:**
- Balance & Savings Timeline (area chart)
- Monthly Cash Flow (bar chart)

### 2. Income & Expenses

**Sankey Diagram:**
Visual flow of money from Gross Income through:
- Deductions
- Net Income
- Fixed Expenses
- Flexible Expenses
- Savings

**Treemap:**
Category breakdown showing relative spending proportions.

**Expenses Timeline:**
Stacked area chart showing fixed vs flexible expenses over time.

**Top Expenses Table:**
Ranked list of spending categories with percentages.

### 3. Savings

**Savings Health Panel:**
- Actual vs Planned savings
- Savings Gap

**Coverage Indicator (Critical):**
- Uncovered Savings: Amount still needed to meet target
- Cash on Hand: Available funds
- Can Cover: Yes/No indicator
- True Discretionary: What you can actually spend

**Savings Timeline:**
Line chart comparing actual savings vs cumulative target over time.

**Savings Transactions:**
List of all savings deposits and withdrawals.

### 4. Budget

**Progress Bars:**
Visual progress for:
- Gross Income vs Plan
- Deductions vs Plan
- Fixed Expenses vs Budget
- Flexible Spending vs Disposable Income
- Savings vs Target

Each bar shows:
- Actual amount / Planned amount
- Variance (absolute and percentage)
- Example: `€4,500 / €5,000 (-€500, -10%)`

Color coding:
- Green: On track
- Yellow: Warning (approaching limit)
- Red: Over budget
- Purple: Exceeded (>100%) - with "Exceeded" badge

**Category Breakdown Table:**
| Column | Description |
|--------|-------------|
| Category | Category name |
| Actual | Amount spent |
| Actual % | Share of total spending |
| Planned | Budgeted amount |
| Planned % | Share of budget |
| Variance | Difference (positive = under budget) |
| Variance % | Percentage difference |

### 5. Transactions

**Filters:**
- Category dropdown
- Type (Income/Expense/Savings/Deduction)
- Text search (description/category)

**Filter Summary:**
Shows real-time stats for filtered results:
- Transaction count
- Total amount
- Income total
- Expense total

**Transactions Table:**
- Date
- Category
- Description
- Amount (color-coded)
- Flags (Savings, Deduction, Fixed)

**Export:**
Click "Export CSV" to download filtered transactions.

## Key Metrics Explained

### Coverage Indicator

The Coverage Indicator answers: "Can I cover my savings gap with available funds?"

```
uncovered_savings = max(0, savings_target - actual_savings)
can_cover = available_funds >= uncovered_savings
true_discretionary = available_funds - uncovered_savings
```

- If `can_cover = true`: You have enough cash to catch up on savings
- If `can_cover = false`: Your savings are behind and cash can't cover it

### True Discretionary

This is the money you can spend without jeopardizing savings goals:

```
True Discretionary = Cash on Hand - Uncovered Savings
```

If negative, you've already overspent relative to your savings plan.

## Charts (Plotly)

All charts are interactive:
- Hover for details
- Click legend items to show/hide series
- Zoom with scroll
- Pan by dragging
- Double-click to reset zoom

**Range Sliders:**
Historical charts (Balance Timeline, Savings Timeline, etc.) include interactive range sliders at the bottom. Drag the handles to zoom into specific date ranges.

**Section Badges:**
Charts are labeled with badges to indicate their scope:
- **Historical** (blue): Shows data across all periods
- **Current Period** (green): Shows current period data only

## All-Periods Mode

Generate a single dashboard with all periods using:

```bash
fintrack report --all
```

This creates an HTML file with:
- **Period Selector**: Dropdown in the header to switch between periods
- **Shared Timeline**: Historical charts show full timeline across all periods
- **Period-Specific Data**: KPIs, transactions, and budget update when switching periods

Useful for:
- Reviewing financial history without generating multiple reports
- Comparing performance across periods
- Quick access to any period's details

## Tips

1. **Regular Review**: Generate dashboard weekly to stay on track
2. **Cash Reconciliation**: Match accounts monthly
3. **Watch Coverage**: Green indicator = financial health
4. **Track Trends**: Use timeline charts to spot patterns
5. **Use All-Periods Mode**: For quick access to historical data
