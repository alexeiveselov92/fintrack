# FinTrack - Task List

## Current: Interactive Dashboard (v0.3.0)

Replacing `fintrack report` with a comprehensive 5-tab interactive dashboard.

### Phase 1: Data Layer
- [ ] Add `uncovered_savings`, `true_discretionary` to calculator.py
- [ ] Create `DashboardData`, `PeriodDataPoint` models
- [ ] Create `fintrack/dashboard/` module
- [ ] Implement `DashboardDataProvider` class
- [ ] Create timeline data generator (all periods)

### Phase 2: HTML Templates (Jinja2 + Plotly)
- [ ] Base layout with 5 tabs (vanilla JS switching)
- [ ] Overview tab (KPIs + Cash Reconciliation + Charts)
- [ ] Income & Expenses tab (Sankey + Treemap + Timeline)
- [ ] Savings tab (Coverage Indicator + Timeline)
- [ ] Budget tab (Bullet bars + Table + Alerts)
- [ ] Transactions tab (Filters + Table + Export)

### Phase 3: Integration
- [ ] Replace `fintrack report` with new dashboard
- [ ] Remove old `reports/generator.py`
- [ ] Add tests
- [ ] Update version to 0.3.0

---

## Previous Releases - COMPLETED

## Phase 1: Foundation - COMPLETED
- [x] Project structure with pyproject.toml
- [x] Pydantic models (Transaction, BudgetPlan, etc.)
- [x] Storage abstractions + SQLite implementation
- [x] CLI commands: init, validate
- [x] Unit tests (28 tests passing)

## Phase 2: Import - COMPLETED
- [x] CSV reader with validation
- [x] Idempotent import (SHA256 hashing)
- [x] `fintrack import` command

## Phase 3: Budget Calculations - COMPLETED
- [x] Budget calculator from BudgetPlan
- [x] Period utilities (day/week/month/quarter/year/custom)
- [x] `fintrack budget` command
- [x] `fintrack status` command

## Phase 4: Analytics - COMPLETED
- [x] Transaction aggregation by period
- [x] Moving average calculations
- [x] Variance analysis (vs plan and history)
- [x] `fintrack analyze` command

## Phase 5: Reports - COMPLETED
- [x] HTML report generator with progress bars
- [x] `fintrack report` command
- [x] `fintrack list` subcommands (transactions, plans, categories)

---

## Future Improvements (Post-MVP)
- [ ] Currency conversion using rates.yaml
- [ ] `fintrack add` for interactive transaction entry
- [ ] Bank statement import parsers
- [ ] Cache invalidation on file changes
- [ ] More detailed error messages
- [ ] Demo workspace with sample data
