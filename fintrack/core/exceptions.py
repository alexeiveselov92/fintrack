"""Custom exceptions for FinTrack.

All application-specific errors inherit from FintrackError.
CLI commands catch these and display user-friendly messages.
"""


class FintrackError(Exception):
    """Base exception for all FinTrack errors."""

    pass


class WorkspaceNotFoundError(FintrackError):
    """Raised when workspace.yaml is not found in the current directory."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path
        msg = "Workspace not found"
        if path:
            msg = f"Workspace not found at: {path}"
        super().__init__(msg)


class InvalidConfigError(FintrackError):
    """Raised when a configuration file is invalid.

    Attributes:
        file_path: Path to the invalid config file.
        details: Specific validation error details.
    """

    def __init__(self, file_path: str, details: str) -> None:
        self.file_path = file_path
        self.details = details
        super().__init__(f"Invalid config in {file_path}: {details}")


class NoPlanFoundError(FintrackError):
    """Raised when no BudgetPlan is found for a given period.

    Attributes:
        period: The period string (e.g., "2024-01") for which no plan exists.
    """

    def __init__(self, period: str) -> None:
        self.period = period
        super().__init__(f"No budget plan found for period: {period}")


class CurrencyConversionError(FintrackError):
    """Raised when currency conversion cannot be performed.

    Attributes:
        from_currency: Source currency code.
        to_currency: Target currency code.
        date: Date for which rate was needed.
    """

    def __init__(self, from_currency: str, to_currency: str, date: str | None = None) -> None:
        self.from_currency = from_currency
        self.to_currency = to_currency
        self.date = date
        msg = f"No exchange rate found: {from_currency} -> {to_currency}"
        if date:
            msg += f" for date {date}"
        super().__init__(msg)


class ImportError(FintrackError):
    """Raised when transaction import fails.

    Attributes:
        file_path: Path to the file being imported.
        details: Specific error details.
        line_number: Line number where error occurred (if applicable).
    """

    def __init__(
        self, file_path: str, details: str, line_number: int | None = None
    ) -> None:
        self.file_path = file_path
        self.details = details
        self.line_number = line_number
        msg = f"Import failed for {file_path}: {details}"
        if line_number:
            msg = f"Import failed for {file_path} at line {line_number}: {details}"
        super().__init__(msg)


class StorageError(FintrackError):
    """Raised when storage operations fail.

    Attributes:
        operation: The operation that failed (e.g., "save", "query").
        details: Specific error details.
    """

    def __init__(self, operation: str, details: str) -> None:
        self.operation = operation
        self.details = details
        super().__init__(f"Storage error during {operation}: {details}")


class ValidationError(FintrackError):
    """Raised when validation of user data fails.

    Attributes:
        field: The field that failed validation.
        value: The invalid value.
        reason: Why validation failed.
    """

    def __init__(self, field: str, value: str, reason: str) -> None:
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"Invalid {field} '{value}': {reason}")
