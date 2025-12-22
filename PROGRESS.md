# FinTrack - Progress Report

## Current State
**Phase**: Dashboard Improvements (v0.3.1)
**Status**: Released
**Last Updated**: 2025-12-22
**Current Version**: 0.3.1

## What's New in v0.3.1

### Bug Fixes
- **Fixed transaction period filtering** - Transactions from other periods no longer appear in reports

### New Features
- **Theme support** - Add `theme: "dark"` to workspace.yaml for dark mode dashboard
- **All-periods mode** - Use `fintrack report --all` to generate dashboard with period switcher dropdown
- **Plotly range sliders** - Historical charts now have interactive date range sliders

### Visual Improvements
- **Section badges** - Historical charts labeled with "Historical" badge
- **Block separation** - Better visual distinction between sections
- **Budget tab improvements**:
  - Variance display with absolute and percentage values
  - >100% exceeded handling with purple bar and badge
  - Category table with actual%, planned%, variance% columns
- **Income & Expenses tab**:
  - KPI cards (Gross Income, Deductions, Net Income, Total Expenses)
  - Sankey diagram explanation text
- **Savings tab** - Total under Savings Transactions table
- **Transactions tab** - Filter summary (count, total, income, expenses)

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
