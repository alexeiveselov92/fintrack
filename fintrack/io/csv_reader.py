"""CSV file reading and parsing for transactions."""

import csv
import hashlib
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterator

from fintrack.core.exceptions import ImportError
from fintrack.core.models import Transaction


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file contents.

    Args:
        file_path: Path to file.

    Returns:
        Hex-encoded SHA256 hash string.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def parse_bool(value: str) -> bool:
    """Parse boolean from CSV string.

    Args:
        value: String value from CSV.

    Returns:
        True if value indicates true, False otherwise.
    """
    if not value or value.strip() == "":
        return False
    return value.strip().lower() in ("true", "1", "yes", "y")


def parse_transaction_row(
    row: dict[str, str], line_number: int, source_file: str
) -> Transaction:
    """Parse a single CSV row into a Transaction.

    Args:
        row: Dictionary from csv.DictReader.
        line_number: Line number for error reporting.
        source_file: Source filename for tracking.

    Returns:
        Parsed Transaction object.

    Raises:
        ImportError: If row data is invalid.
    """
    try:
        # Parse required fields
        date_str = row.get("date", "").strip()
        if not date_str:
            raise ImportError(source_file, "Missing date", line_number)

        try:
            tx_date = date.fromisoformat(date_str)
        except ValueError:
            raise ImportError(
                source_file, f"Invalid date format: {date_str}", line_number
            )

        amount_str = row.get("amount", "").strip()
        if not amount_str:
            raise ImportError(source_file, "Missing amount", line_number)

        try:
            amount = Decimal(amount_str)
        except InvalidOperation:
            raise ImportError(
                source_file, f"Invalid amount: {amount_str}", line_number
            )

        currency = row.get("currency", "EUR").strip().upper()
        if len(currency) != 3:
            raise ImportError(
                source_file, f"Invalid currency code: {currency}", line_number
            )

        category = row.get("category", "").strip()
        if not category:
            raise ImportError(source_file, "Missing category", line_number)

        # Parse optional fields
        description = row.get("description", "").strip() or None
        is_savings = parse_bool(row.get("is_savings", ""))
        is_deduction = parse_bool(row.get("is_deduction", ""))
        is_fixed = parse_bool(row.get("is_fixed", ""))

        # Validate flag combinations
        if is_deduction and is_fixed:
            raise ImportError(
                source_file,
                "is_deduction and is_fixed cannot both be true",
                line_number,
            )

        return Transaction(
            date=tx_date,
            amount=amount,
            currency=currency,
            category=category,
            description=description,
            is_savings=is_savings,
            is_deduction=is_deduction,
            is_fixed=is_fixed,
            source_file=source_file,
        )

    except ImportError:
        raise
    except Exception as e:
        raise ImportError(source_file, str(e), line_number)


def read_transactions_csv(file_path: Path) -> Iterator[Transaction]:
    """Read transactions from a CSV file.

    Args:
        file_path: Path to CSV file.

    Yields:
        Transaction objects parsed from CSV rows.

    Raises:
        ImportError: If file cannot be read or contains invalid data.
    """
    if not file_path.exists():
        raise ImportError(str(file_path), "File does not exist")

    try:
        with open(file_path, newline="", encoding="utf-8") as f:
            # Try to detect delimiter
            sample = f.read(1024)
            f.seek(0)

            # Use csv.Sniffer or default to comma
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            except csv.Error:
                dialect = csv.excel  # type: ignore

            reader = csv.DictReader(f, dialect=dialect)

            # Validate required columns
            if reader.fieldnames is None:
                raise ImportError(str(file_path), "Empty or invalid CSV file")

            required = {"date", "amount", "category"}
            fieldnames_lower = {f.lower().strip() for f in reader.fieldnames}
            missing = required - fieldnames_lower

            if missing:
                raise ImportError(
                    str(file_path), f"Missing required columns: {missing}"
                )

            # Normalize fieldnames (lowercase, stripped)
            fieldname_map = {f: f.lower().strip() for f in reader.fieldnames}

            for line_num, row in enumerate(reader, start=2):
                # Normalize row keys
                normalized_row = {
                    fieldname_map.get(k, k.lower().strip()): v
                    for k, v in row.items()
                    if k is not None
                }
                yield parse_transaction_row(
                    normalized_row, line_num, file_path.name
                )

    except ImportError:
        raise
    except UnicodeDecodeError:
        raise ImportError(str(file_path), "File encoding error (expected UTF-8)")
    except Exception as e:
        raise ImportError(str(file_path), f"Failed to read file: {e}")


def read_all_csv_files(directory: Path) -> Iterator[tuple[Path, Iterator[Transaction]]]:
    """Read all CSV files from a directory.

    Args:
        directory: Path to directory containing CSV files.

    Yields:
        Tuples of (file_path, transaction_iterator).
    """
    if not directory.exists():
        return

    for csv_file in sorted(directory.glob("*.csv")):
        if csv_file.name.startswith("."):
            continue  # Skip hidden files
        yield csv_file, read_transactions_csv(csv_file)
