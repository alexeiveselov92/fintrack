# FinTrack - Progress Report

## Current State
**Phase**: Dashboard MVP (v0.3.0)
**Status**: In Development
**Last Updated**: 2025-12-22
**Current Version**: 0.2.6

## What's In Progress

### Interactive Dashboard (v0.3.0)
Replacing the simple HTML report with a comprehensive 5-tab interactive dashboard:
- **Tab 1: Overview** - KPIs, Cash Reconciliation calculator, Balance/Savings Timeline
- **Tab 2: Income & Expenses** - Sankey diagram, Treemap, Expenses Timeline
- **Tab 3: Savings** - Coverage Indicator, Savings vs Planned Timeline
- **Tab 4: Budget** - Budget vs Actual bars, Alerts
- **Tab 5: Transactions** - Filterable table with export

Key new metrics:
- `uncovered_savings` = max(0, target - actual)
- `can_cover` = cash_on_hand >= uncovered_savings
- `true_discretionary` = cash_on_hand - uncovered_savings

---

## What's Done

### v0.2.5-0.2.6: Savings Analysis Improvements
- Added `cash_on_hand` = cumulative_balance - cumulative_savings
- Added `cumulative_savings_target` across all periods
- Added `savings_surplus` = cumulative_savings - target
- Gross Income vs Plan comparison
- Deductions vs Plan comparison
- Fixed report command to use new metrics

### All MVP Features Implemented (v0.1.0-v0.2.4)

**Commands Available:**
- `fintrack init <name>` - Create workspace
- `fintrack validate` - Validate configs
- `fintrack import <path>` - Import CSV transactions
- `fintrack budget [--period]` - Show budget projection
- `fintrack status [--period]` - Quick status overview
- `fintrack analyze [--period]` - Full analysis with history
- `fintrack report [--period]` - Generate HTML report
- `fintrack list transactions` - List transactions
- `fintrack list plans` - List budget plans
- `fintrack list categories` - List categories

**Core Features:**
- Transaction flags: is_savings, is_deduction, is_fixed
- Income flow: Gross → Deductions → Net → Fixed → Savings → Disposable
- Period support: day/week/month/quarter/year/custom
- Idempotent imports with file hashing
- SQLite storage with Repository pattern
- Moving average comparisons
- Variance analysis (vs plan, vs history)
- HTML reports with progress visualization

## How to Use

1. Create workspace:
   ```bash
   fintrack init my_finances
   cd my_finances
   ```

2. Edit `plans/` to add your budget plan (see example.yaml)

3. Import your transactions:
   ```bash
   fintrack import transactions/
   ```

4. View your budget and spending:
   ```bash
   fintrack budget
   fintrack status
   fintrack analyze
   fintrack report
   ```

## Files Structure
```
fintrack/
├── cli/          # 8 command modules
├── core/         # models, exceptions, constants, workspace
├── engine/       # calculator, aggregator, periods
├── io/           # csv_reader, yaml_reader/writer
├── storage/      # base.py + sqlite/ implementation
└── reports/      # HTML generator
```

## Tests
- 28 unit tests passing
- All CLI commands tested manually

## Session Log
| Date | Summary |
|------|---------|
| 2025-12-18 | Phase 1: Project setup, models, storage, init/validate |
| 2025-12-18 | Phase 2-5: Import, budget, analyze, status, report commands |
| 2025-12-18 | MVP Complete - all features working |
