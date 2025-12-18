# FinTrack - Personal Finance Tracker CLI

## Quick Start for New Sessions
1. Read this file for project overview
2. Check `PROGRESS.md` for current state
3. Check `TODO.md` for next tasks
4. Full spec in `TECHNICAL_SPECIFICATION.md`

## Tech Stack
- Python 3.11+ with pip/uv
- CLI: Typer | Validation: Pydantic v2 | Config: PyYAML
- Storage: SQLite (Repository pattern for abstraction)
- Reports: Jinja2 HTML templates

## Architecture Overview
- **dbt-inspired**: isolated Workspaces with own configs/data
- **Idempotent**: all operations repeatable without side effects
- **Layered**: CLI -> Engine -> Storage

## Core Domain Concepts
- **Transaction flags**: `is_savings`, `is_deduction`, `is_fixed`
- **Income flow**: Gross -> Deductions -> Net -> Fixed -> Savings -> Disposable
- **Periods**: day/week/month/quarter/year/custom intervals
- **Key metric**: Disposable Income (money user can actually control)

## CLI Commands
```
init <name>              Create workspace
validate                 Validate configs
import <path>            Import CSV transactions
budget [--period]        Budget projection
status [--period]        Quick status
analyze [--period]       Full analysis
report [--period]        HTML report
list transactions        List transactions
list plans               List budget plans
list categories          List categories
```

## Workspace Structure
```
my_finances/
  workspace.yaml          # Config
  plans/*.yaml            # Budget plans by period
  rates.yaml              # Exchange rates
  transactions/*.csv      # Transaction data
  reports/*.html          # Generated reports
  .cache/fintrack.db      # SQLite database
```

## Code Layout
```
fintrack/
  cli/        # Typer commands
  core/       # models.py, exceptions.py, constants.py, workspace.py
  engine/     # calculator.py, aggregator.py, periods.py
  storage/    # base.py, factory.py, sqlite/
  io/         # csv_reader.py, yaml_reader.py, yaml_writer.py
  reports/    # generator.py
```

## Development Status
**MVP COMPLETE** - All core features implemented and tested.

## Running
```bash
source .venv/bin/activate
fintrack --help
pytest tests/
```
