"""Period utilities for date range calculations.

Handles different interval types (day, week, month, quarter, year, custom)
and provides utilities for period navigation and formatting.
"""

from calendar import monthrange
from datetime import date, timedelta
from typing import Iterator

from fintrack.core.models import IntervalType


def get_period_start(target_date: date, interval: IntervalType, custom_days: int | None = None) -> date:
    """Get the start date of the period containing target_date.

    Args:
        target_date: Date to find period for.
        interval: Period interval type.
        custom_days: Days for custom interval (required if interval is CUSTOM).

    Returns:
        Start date of the period.
    """
    if interval == IntervalType.DAY:
        return target_date

    elif interval == IntervalType.WEEK:
        # Week starts on Monday (ISO standard)
        return target_date - timedelta(days=target_date.weekday())

    elif interval == IntervalType.MONTH:
        return date(target_date.year, target_date.month, 1)

    elif interval == IntervalType.QUARTER:
        quarter = (target_date.month - 1) // 3
        quarter_start_month = quarter * 3 + 1
        return date(target_date.year, quarter_start_month, 1)

    elif interval == IntervalType.YEAR:
        return date(target_date.year, 1, 1)

    elif interval == IntervalType.CUSTOM:
        if custom_days is None:
            raise ValueError("custom_days required for CUSTOM interval")
        # Use a fixed epoch for custom periods
        epoch = date(2020, 1, 1)
        days_since_epoch = (target_date - epoch).days
        period_number = days_since_epoch // custom_days
        return epoch + timedelta(days=period_number * custom_days)

    raise ValueError(f"Unknown interval type: {interval}")


def get_period_end(period_start: date, interval: IntervalType, custom_days: int | None = None) -> date:
    """Get the end date (exclusive) of a period.

    Args:
        period_start: Start date of the period.
        interval: Period interval type.
        custom_days: Days for custom interval.

    Returns:
        End date (exclusive) of the period.
    """
    if interval == IntervalType.DAY:
        return period_start + timedelta(days=1)

    elif interval == IntervalType.WEEK:
        return period_start + timedelta(days=7)

    elif interval == IntervalType.MONTH:
        if period_start.month == 12:
            return date(period_start.year + 1, 1, 1)
        return date(period_start.year, period_start.month + 1, 1)

    elif interval == IntervalType.QUARTER:
        month = period_start.month + 3
        year = period_start.year
        if month > 12:
            month -= 12
            year += 1
        return date(year, month, 1)

    elif interval == IntervalType.YEAR:
        return date(period_start.year + 1, 1, 1)

    elif interval == IntervalType.CUSTOM:
        if custom_days is None:
            raise ValueError("custom_days required for CUSTOM interval")
        return period_start + timedelta(days=custom_days)

    raise ValueError(f"Unknown interval type: {interval}")


def format_period(period_start: date, interval: IntervalType) -> str:
    """Format a period start date for display.

    Args:
        period_start: Start date of the period.
        interval: Period interval type.

    Returns:
        Human-readable period string.
    """
    if interval == IntervalType.DAY:
        return period_start.strftime("%Y-%m-%d")

    elif interval == IntervalType.WEEK:
        week_num = period_start.isocalendar()[1]
        return f"{period_start.year}-W{week_num:02d}"

    elif interval == IntervalType.MONTH:
        return period_start.strftime("%Y-%m")

    elif interval == IntervalType.QUARTER:
        quarter = (period_start.month - 1) // 3 + 1
        return f"{period_start.year}-Q{quarter}"

    elif interval == IntervalType.YEAR:
        return str(period_start.year)

    elif interval == IntervalType.CUSTOM:
        return period_start.strftime("%Y-%m-%d")

    return period_start.isoformat()


def parse_period(period_str: str, interval: IntervalType) -> date:
    """Parse a period string to its start date.

    Args:
        period_str: Period string (e.g., "2024-01", "2024-Q1", "2024-W03").
        interval: Expected interval type.

    Returns:
        Start date of the period.

    Raises:
        ValueError: If period string is invalid.
    """
    try:
        if interval == IntervalType.DAY:
            return date.fromisoformat(period_str)

        elif interval == IntervalType.WEEK:
            # Format: YYYY-WNN
            if "-W" in period_str:
                year, week = period_str.split("-W")
                # Get first day of ISO week
                jan_4 = date(int(year), 1, 4)
                start_of_week_1 = jan_4 - timedelta(days=jan_4.weekday())
                return start_of_week_1 + timedelta(weeks=int(week) - 1)
            raise ValueError(f"Invalid week format: {period_str}")

        elif interval == IntervalType.MONTH:
            # Format: YYYY-MM
            parts = period_str.split("-")
            return date(int(parts[0]), int(parts[1]), 1)

        elif interval == IntervalType.QUARTER:
            # Format: YYYY-QN
            if "-Q" in period_str:
                year, quarter = period_str.split("-Q")
                month = (int(quarter) - 1) * 3 + 1
                return date(int(year), month, 1)
            raise ValueError(f"Invalid quarter format: {period_str}")

        elif interval == IntervalType.YEAR:
            # Format: YYYY
            return date(int(period_str), 1, 1)

        elif interval == IntervalType.CUSTOM:
            return date.fromisoformat(period_str)

    except (ValueError, IndexError) as e:
        raise ValueError(f"Cannot parse period '{period_str}': {e}")

    raise ValueError(f"Unknown interval type: {interval}")


def iterate_periods(
    start: date,
    end: date,
    interval: IntervalType,
    custom_days: int | None = None,
) -> Iterator[tuple[date, date]]:
    """Iterate over periods between two dates.

    Args:
        start: Start date (inclusive).
        end: End date (exclusive).
        interval: Period interval type.
        custom_days: Days for custom interval.

    Yields:
        Tuples of (period_start, period_end) dates.
    """
    current = get_period_start(start, interval, custom_days)

    while current < end:
        period_end = get_period_end(current, interval, custom_days)
        yield current, period_end
        current = period_end


def get_previous_periods(
    period_start: date,
    count: int,
    interval: IntervalType,
    custom_days: int | None = None,
) -> list[date]:
    """Get start dates of N previous periods.

    Args:
        period_start: Current period start.
        count: Number of previous periods.
        interval: Period interval type.
        custom_days: Days for custom interval.

    Returns:
        List of period start dates, most recent first.
    """
    periods = []
    current = period_start

    for _ in range(count):
        # Go back one period
        if interval == IntervalType.DAY:
            current = current - timedelta(days=1)
        elif interval == IntervalType.WEEK:
            current = current - timedelta(weeks=1)
        elif interval == IntervalType.MONTH:
            if current.month == 1:
                current = date(current.year - 1, 12, 1)
            else:
                current = date(current.year, current.month - 1, 1)
        elif interval == IntervalType.QUARTER:
            month = current.month - 3
            year = current.year
            if month < 1:
                month += 12
                year -= 1
            current = date(year, month, 1)
        elif interval == IntervalType.YEAR:
            current = date(current.year - 1, 1, 1)
        elif interval == IntervalType.CUSTOM:
            if custom_days is None:
                raise ValueError("custom_days required for CUSTOM interval")
            current = current - timedelta(days=custom_days)

        periods.append(current)

    return periods


def get_current_period(interval: IntervalType, custom_days: int | None = None) -> tuple[date, date]:
    """Get the current period boundaries.

    Args:
        interval: Period interval type.
        custom_days: Days for custom interval.

    Returns:
        Tuple of (period_start, period_end).
    """
    today = date.today()
    start = get_period_start(today, interval, custom_days)
    end = get_period_end(start, interval, custom_days)
    return start, end


def days_remaining_in_period(
    period_start: date,
    interval: IntervalType,
    custom_days: int | None = None,
) -> int:
    """Calculate days remaining in the current period.

    Args:
        period_start: Start of the period.
        interval: Period interval type.
        custom_days: Days for custom interval.

    Returns:
        Number of days remaining (0 if period has ended).
    """
    period_end = get_period_end(period_start, interval, custom_days)
    today = date.today()

    if today >= period_end:
        return 0

    return (period_end - today).days
