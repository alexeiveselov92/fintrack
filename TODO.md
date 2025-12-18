# FinTrack - Task List

## MVP Complete!

All core features are implemented and working.

---

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
