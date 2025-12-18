"""YAML file writing utilities for FinTrack configurations."""

from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml


class DecimalDumper(yaml.SafeDumper):
    """YAML Dumper that handles Decimal types."""

    pass


def _decimal_representer(dumper: yaml.SafeDumper, data: Decimal) -> yaml.ScalarNode:
    """Represent Decimal as a float in YAML."""
    return dumper.represent_float(float(data))


DecimalDumper.add_representer(Decimal, _decimal_representer)


def write_yaml_file(file_path: Path, data: dict[str, Any]) -> None:
    """Write data to a YAML file.

    Args:
        file_path: Path to the output file.
        data: Dictionary to write as YAML.

    Note:
        Creates parent directories if they don't exist.
        Uses safe YAML dumping with proper Decimal handling.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            Dumper=DecimalDumper,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )


def write_raw_content(file_path: Path, content: str) -> None:
    """Write raw string content to a file.

    Useful for writing template files with comments preserved.

    Args:
        file_path: Path to the output file.
        content: String content to write.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
