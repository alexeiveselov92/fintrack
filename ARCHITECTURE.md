# FinTrack Architecture

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INPUT                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
            │ plans/*.yaml│  │transactions/│  │ rates.yaml  │
            │             │  │   *.csv     │  │  (optional) │
            │ Budget Plan │  │ Transactions│  │  Exchange   │
            └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
                   │                │                │
                   │                ▼                │
                   │    ┌───────────────────┐        │
                   │    │  fintrack import  │        │
                   │    └─────────┬─────────┘        │
                   │              │                  │
                   │              ▼                  │
                   │    ┌───────────────────┐        │
                   │    │ .cache/fintrack.db│◄───────┘
                   │    │     (SQLite)      │
                   │    │                   │
                   │    │ • transactions    │
                   │    │ • import_log      │
                   │    │ • cache           │
                   │    └─────────┬─────────┘
                   │              │
                   └──────┬───────┘
                          │
                          ▼
            ┌─────────────────────────────┐
            │      CALCULATION ENGINE     │
            │                             │
            │  BudgetPlan + Transactions  │
            │           ↓                 │
            │     PeriodSummary          │
            │     CategoryAnalysis       │
            └──────────────┬──────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │   status    │ │   analyze   │ │   report    │
    │  (console)  │ │  (console)  │ │   (HTML)    │
    └─────────────┘ └─────────────┘ └─────────────┘
```

---

## Income Flow Calculation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BUDGET PLAN                                        │
│                         (plans/*.yaml)                                       │
└─────────────────────────────────────────────────────────────────────────────┘

    GROSS INCOME                         5,000.00 EUR
         │
         │  ┌──────────────────────────────────────┐
         ├──┤ DEDUCTIONS (is_deduction=true)       │
         │  │   • income_tax:      1,000.00        │
         │  │   • social_security:   200.00        │
         │  │   ─────────────────────────────      │
         │  │   Total:             1,200.00        │
         │  └──────────────────────────────────────┘
         ▼
    NET INCOME                           3,800.00 EUR
    (gross - deductions)
         │
         │  ┌──────────────────────────────────────┐
         ├──┤ FIXED EXPENSES (is_fixed=true)       │
         │  │   • rent:              800.00        │
         │  │   • utilities:         150.00        │
         │  │   • internet:           30.00        │
         │  │   ─────────────────────────────      │
         │  │   Total:               980.00        │
         │  └──────────────────────────────────────┘
         │
         │  ┌──────────────────────────────────────┐
         ├──┤ SAVINGS TARGET                       │
         │  │   Option A: savings_rate × base      │
         │  │     20% × 3,800 = 760.00             │
         │  │   Option B: savings_amount (fixed)   │
         │  │     savings_amount: 500.00           │
         │  └──────────────────────────────────────┘
         ▼
    DISPOSABLE INCOME                    2,060.00 EUR
    (net - fixed - savings)
         │
         │  ┌──────────────────────────────────────┐
         └──┤ CATEGORY BUDGETS (flexible spending) │
            │   • food:           400.00           │
            │   • transport:      150.00           │
            │   • entertainment:  100.00           │
            │   • health:          50.00           │
            └──────────────────────────────────────┘
```

---

## Transaction Classification

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TRANSACTION FLAGS                                    │
└─────────────────────────────────────────────────────────────────────────────┘

Each transaction has 3 boolean flags:

┌─────────────┬──────────────────────────────────────────────────────────────┐
│ FLAG        │ MEANING                                                      │
├─────────────┼──────────────────────────────────────────────────────────────┤
│is_deduction │ Pre-tax/pre-income deduction (taxes, social security)       │
│             │ Subtracted from GROSS to calculate NET                       │
├─────────────┼──────────────────────────────────────────────────────────────┤
│is_fixed     │ Fixed/recurring expense (rent, subscriptions)               │
│             │ Subtracted from NET, not counted as variable spending        │
├─────────────┼──────────────────────────────────────────────────────────────┤
│is_savings   │ Money transferred to savings account                         │
│             │ Tracked separately, counts toward savings goal               │
└─────────────┴──────────────────────────────────────────────────────────────┘

RULES:
  • is_deduction + is_fixed = INVALID (mutually exclusive)
  • is_savings can combine with others
  • No flags = variable/flexible expense


TRANSACTION FLOW:

  ┌────────────────────┐
  │   CSV Transaction  │
  │                    │
  │ amount: -1000.00   │
  │ is_deduction: true │
  └─────────┬──────────┘
            │
            ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                    CLASSIFICATION                            │
  │                                                              │
  │  is_deduction=true? ──► Deduction (affects net income)       │
  │          │                                                   │
  │          ▼ no                                                │
  │  is_fixed=true? ──────► Fixed Expense (mandatory payment)    │
  │          │                                                   │
  │          ▼ no                                                │
  │  is_savings=true? ────► Savings (toward goal)                │
  │          │                                                   │
  │          ▼ no                                                │
  │  amount > 0? ─────────► Income                               │
  │          │                                                   │
  │          ▼ no                                                │
  │  ─────────────────────► Variable Expense (flexible spending) │
  └─────────────────────────────────────────────────────────────┘
```

---

## Period Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PERIOD SUMMARY                                       │
│                    (fintrack status / analyze)                               │
└─────────────────────────────────────────────────────────────────────────────┘

For period 2024-12:

┌─────────────────────────────────────────────────────────────────┐
│ 1. LOAD DATA                                                    │
│                                                                 │
│    Budget Plan ◄── plans/2024-12.yaml (or latest valid_from)   │
│    Transactions ◄── SELECT * FROM transactions                 │
│                     WHERE date >= '2024-12-01'                  │
│                     AND date < '2025-01-01'                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. AGGREGATE TRANSACTIONS                                       │
│                                                                 │
│    total_income     = SUM(amount) WHERE amount > 0              │
│    total_deductions = SUM(amount) WHERE is_deduction = true     │
│    total_fixed      = SUM(amount) WHERE is_fixed = true         │
│    total_savings    = SUM(amount) WHERE is_savings = true       │
│    total_variable   = SUM(amount) WHERE none of above           │
│                                                                 │
│    Per category:                                                │
│    category_spent[cat] = SUM(amount) GROUP BY category          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. COMPARE TO BUDGET                                            │
│                                                                 │
│    For each category:                                           │
│                                                                 │
│    budget    = plan.category_budgets[category].amount           │
│    spent     = ABS(category_spent[category])                    │
│    remaining = budget - spent                                   │
│    progress  = spent / budget × 100%                            │
│                                                                 │
│    variance  = budget - spent                                   │
│      • positive = under budget (good)                           │
│      • negative = over budget (warning)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. CALCULATE STATUS                                             │
│                                                                 │
│    Disposable Budget:    2,060.00 (from plan)                   │
│    Variable Spent:         450.00 (sum of flexible expenses)    │
│    Remaining:            1,610.00                               │
│    Progress:               21.8%                                │
│                                                                 │
│    Savings Target:         760.00 (from plan)                   │
│    Actual Savings:         500.00 (is_savings transactions)     │
│    Savings Progress:       65.8%                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Historical Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      HISTORICAL COMPARISON                                   │
│                      (fintrack analyze --history N)                          │
└─────────────────────────────────────────────────────────────────────────────┘

Example: analyze --history 3 (compare with last 3 periods)

┌─────────┬──────────┬──────────┬──────────┬──────────┬─────────────┐
│Category │ Oct 2024 │ Nov 2024 │ Dec 2024 │ Average  │ vs Average  │
├─────────┼──────────┼──────────┼──────────┼──────────┼─────────────┤
│food     │   380.00 │   420.00 │   450.00 │   416.67 │ +33.33 (8%) │
│transport│   120.00 │   150.00 │   100.00 │   123.33 │ -23.33(-19%)│
│entertain│    80.00 │   100.00 │   150.00 │   110.00 │ +40.00(36%) │
└─────────┴──────────┴──────────┴──────────┴──────────┴─────────────┘

CALCULATION:

┌─────────────────────────────────────────────────────────────────┐
│ Moving Average (N periods):                                     │
│                                                                 │
│   avg = (period[n-1] + period[n-2] + ... + period[n-N]) / N     │
│                                                                 │
│ Variance from Average:                                          │
│                                                                 │
│   variance = current_period - avg                               │
│   variance_pct = (current_period - avg) / avg × 100%            │
│                                                                 │
│ Trend Detection:                                                │
│                                                                 │
│   If variance_pct > +20%  → "Increasing ↑"                      │
│   If variance_pct < -20%  → "Decreasing ↓"                      │
│   Otherwise               → "Stable ─"                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Storage Schema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SQLite Database                                      │
│                       .cache/fintrack.db                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TABLE: transactions                                             │
├─────────────────────────────────────────────────────────────────┤
│ id            TEXT PRIMARY KEY  (UUID)                          │
│ date          TEXT              (YYYY-MM-DD)                    │
│ amount        TEXT              (Decimal as string)             │
│ currency      TEXT              (EUR, USD, etc.)                │
│ category      TEXT                                              │
│ description   TEXT                                              │
│ is_savings    INTEGER           (0 or 1)                        │
│ is_deduction  INTEGER           (0 or 1)                        │
│ is_fixed      INTEGER           (0 or 1)                        │
│ source_file   TEXT              (original CSV path)             │
│ created_at    TEXT              (ISO timestamp)                 │
├─────────────────────────────────────────────────────────────────┤
│ UNIQUE(date, amount, currency, category, description)          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TABLE: import_log                                               │
├─────────────────────────────────────────────────────────────────┤
│ id               INTEGER PRIMARY KEY                            │
│ file_path        TEXT              (full path to CSV)           │
│ file_hash        TEXT UNIQUE       (SHA256 of content)          │
│ records_imported INTEGER           (count)                      │
│ imported_at      TEXT              (ISO timestamp)              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TABLE: cache                                                    │
├─────────────────────────────────────────────────────────────────┤
│ key              TEXT PRIMARY KEY  (workspace:period:type)      │
│ value            TEXT              (JSON serialized data)       │
│ created_at       TEXT              (ISO timestamp)              │
│ expires_at       TEXT              (ISO timestamp)              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Command Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLI COMMANDS                                       │
└─────────────────────────────────────────────────────────────────────────────┘

fintrack init <name>
    │
    └──► Create workspace structure
         ├── workspace.yaml
         ├── plans/
         ├── transactions/
         ├── reports/
         └── .cache/

fintrack validate
    │
    └──► Parse & validate all YAML files
         ├── workspace.yaml → WorkspaceConfig model
         ├── plans/*.yaml → BudgetPlan models
         └── rates.yaml → ExchangeRate models

fintrack import [path]
    │
    ├──► Compute SHA256 hash of file
    ├──► Check import_log (skip if already imported)
    ├──► Parse CSV → Transaction models
    ├──► Save to SQLite (INSERT OR IGNORE)
    └──► Log to import_log

fintrack budget [--period]
    │
    ├──► Find BudgetPlan for period (by valid_from)
    └──► Display plan projections (no transactions needed)

fintrack status [--period]
    │
    ├──► Load BudgetPlan
    ├──► Query transactions for period
    ├──► Aggregate by category
    ├──► Compare to budget
    └──► Display current status

fintrack analyze [--period] [--history N]
    │
    ├──► Load BudgetPlan
    ├──► Query transactions for current + N previous periods
    ├──► Calculate moving averages
    ├──► Calculate variance
    └──► Display analysis with trends

fintrack report [--period]
    │
    ├──► Run full analysis
    ├──► Render Jinja2 HTML template
    └──► Save to reports/report_YYYY-MM.html

fintrack list imports
    │
    └──► Query import_log table
         └── Display: file, records, date, hash

fintrack cache clear --confirm
    │
    ├──► DELETE FROM transactions
    └──► DELETE FROM import_log

fintrack cache reset <file>
    │
    ├──► DELETE FROM transactions WHERE source_file LIKE '%file%'
    └──► DELETE FROM import_log WHERE file_path LIKE '%file%'
```

---

## Multi-Currency (Optional)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CURRENCY CONVERSION                                  │
│                           (rates.yaml)                                       │
└─────────────────────────────────────────────────────────────────────────────┘

rates.yaml:
┌────────────────────────────────────┐
│ base_currency: "EUR"               │
│ rates:                             │
│   USD: 0.92   # 1 USD = 0.92 EUR   │
│   GBP: 1.17   # 1 GBP = 1.17 EUR   │
│   RSD: 0.0085 # 1 RSD = 0.0085 EUR │
└────────────────────────────────────┘

Conversion:
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Transaction: 100 USD                                           │
│                                                                 │
│  To base currency (EUR):                                        │
│    100 USD × 0.92 = 92.00 EUR                                   │
│                                                                 │
│  All aggregations use base currency for consistency             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```
