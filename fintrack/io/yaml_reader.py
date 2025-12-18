"""YAML file reading utilities for FinTrack configurations."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError as PydanticValidationError

from fintrack.core.exceptions import InvalidConfigError, WorkspaceNotFoundError
from fintrack.core.models import BudgetPlan, ExchangeRate, WorkspaceConfig


def _convert_decimals(data: Any) -> Any:
    """Recursively convert floats to Decimals in parsed YAML data."""
    if isinstance(data, dict):
        return {k: _convert_decimals(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_convert_decimals(item) for item in data]
    elif isinstance(data, float):
        return Decimal(str(data))
    return data


def load_yaml_file(file_path: Path) -> dict[str, Any]:
    """Load and parse a YAML file.

    Args:
        file_path: Path to the YAML file.

    Returns:
        Parsed YAML content as a dictionary.

    Raises:
        InvalidConfigError: If file doesn't exist or is invalid YAML.
    """
    if not file_path.exists():
        raise InvalidConfigError(str(file_path), "File does not exist")

    try:
        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data is None:
                return {}
            return _convert_decimals(data)
    except yaml.YAMLError as e:
        raise InvalidConfigError(str(file_path), f"Invalid YAML: {e}")


def load_workspace_config(workspace_path: Path) -> WorkspaceConfig:
    """Load workspace configuration from workspace.yaml.

    Args:
        workspace_path: Path to the workspace directory.

    Returns:
        Validated WorkspaceConfig object.

    Raises:
        WorkspaceNotFoundError: If workspace.yaml doesn't exist.
        InvalidConfigError: If configuration is invalid.
    """
    config_file = workspace_path / "workspace.yaml"
    if not config_file.exists():
        raise WorkspaceNotFoundError(str(workspace_path))

    data = load_yaml_file(config_file)

    try:
        return WorkspaceConfig(**data)
    except PydanticValidationError as e:
        errors = "; ".join(f"{err['loc']}: {err['msg']}" for err in e.errors())
        raise InvalidConfigError(str(config_file), errors)


def load_budget_plan(plan_file: Path) -> BudgetPlan:
    """Load a budget plan from a YAML file.

    Args:
        plan_file: Path to the plan YAML file.

    Returns:
        Validated BudgetPlan object.

    Raises:
        InvalidConfigError: If plan file is invalid.
    """
    data = load_yaml_file(plan_file)

    # Convert date strings to date objects if needed
    for field in ["valid_from", "valid_to"]:
        if field in data and isinstance(data[field], str):
            try:
                data[field] = date.fromisoformat(data[field])
            except ValueError:
                raise InvalidConfigError(
                    str(plan_file), f"Invalid date format for {field}"
                )

    try:
        return BudgetPlan(**data)
    except PydanticValidationError as e:
        errors = "; ".join(f"{err['loc']}: {err['msg']}" for err in e.errors())
        raise InvalidConfigError(str(plan_file), errors)


def load_all_plans(plans_dir: Path) -> list[BudgetPlan]:
    """Load all budget plans from a directory.

    Args:
        plans_dir: Path to the plans directory.

    Returns:
        List of BudgetPlan objects sorted by valid_from date.

    Raises:
        InvalidConfigError: If any plan file is invalid.
    """
    if not plans_dir.exists():
        return []

    plans = []
    for plan_file in sorted(plans_dir.glob("*.yaml")):
        if plan_file.name.startswith("example"):
            continue  # Skip example files
        plans.append(load_budget_plan(plan_file))

    return sorted(plans, key=lambda p: p.valid_from)


def load_exchange_rates(rates_file: Path) -> list[ExchangeRate]:
    """Load exchange rates from rates.yaml.

    Args:
        rates_file: Path to the rates.yaml file.

    Returns:
        List of ExchangeRate objects.

    Raises:
        InvalidConfigError: If rates file is invalid.
    """
    if not rates_file.exists():
        return []

    data = load_yaml_file(rates_file)
    rates_data = data.get("rates", [])

    rates = []
    for i, rate_data in enumerate(rates_data):
        # Convert date strings
        for field in ["valid_from", "valid_to"]:
            if field in rate_data and isinstance(rate_data[field], str):
                try:
                    rate_data[field] = date.fromisoformat(rate_data[field])
                except ValueError:
                    raise InvalidConfigError(
                        str(rates_file), f"Invalid date format in rate {i + 1}"
                    )

        try:
            rates.append(ExchangeRate(**rate_data))
        except PydanticValidationError as e:
            errors = "; ".join(f"{err['loc']}: {err['msg']}" for err in e.errors())
            raise InvalidConfigError(str(rates_file), f"Rate {i + 1}: {errors}")

    return rates
