"""Datetime utility functions."""

import re
from datetime import datetime, timedelta
from typing import Optional

from dateutil import parser as date_parser


def parse_flexible_datetime(date_string: str, reference_date: Optional[datetime] = None) -> Optional[datetime]:
    """Parse a flexible datetime string using various formats."""
    if not date_string:
        return None
    
    if reference_date is None:
        reference_date = datetime.now()
    
    # Clean the input string
    date_string = date_string.strip()
    
    # Try common relative terms first
    relative_patterns = {
        r'today': lambda: reference_date.replace(hour=9, minute=0, second=0, microsecond=0),
        r'tomorrow': lambda: (reference_date + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0),
        r'next week': lambda: (reference_date + timedelta(days=7)).replace(hour=9, minute=0, second=0, microsecond=0),
        r'next month': lambda: reference_date.replace(month=reference_date.month + 1 if reference_date.month < 12 else 1,
                                                     year=reference_date.year if reference_date.month < 12 else reference_date.year + 1,
                                                     hour=9, minute=0, second=0, microsecond=0),
    }
    
    for pattern, func in relative_patterns.items():
        if re.search(pattern, date_string.lower()):
            return func()
    
    # Try dateutil parser
    try:
        parsed_date = date_parser.parse(date_string, default=reference_date)
        return parsed_date
    except Exception:
        pass
    
    # Try manual patterns
    patterns = [
        r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY
        r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
        r'(\d{1,2})-(\d{1,2})-(\d{4})',  # DD-MM-YYYY
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_string)
        if match:
            try:
                groups = match.groups()
                if len(groups) == 3:
                    if pattern.startswith(r'(\d{4})'):  # YYYY-MM-DD
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    elif pattern.startswith(r'(\d{1,2})/'):  # MM/DD/YYYY
                        month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                    else:  # DD-MM-YYYY
                        day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                    
                    return datetime(year, month, day, 9, 0)  # Default to 9 AM
            except ValueError:
                continue
    
    return None


def format_human_readable(dt: datetime) -> str:
    """Format datetime in a human-readable format."""
    now = datetime.now()
    
    # Calculate time difference
    diff = dt - now
    
    if abs(diff.days) == 0:
        if diff.seconds < 3600:  # Less than 1 hour
            minutes = diff.seconds // 60
            if minutes < 1:
                return "now"
            elif minutes == 1:
                return "in 1 minute" if diff.seconds >= 0 else "1 minute ago"
            else:
                return f"in {minutes} minutes" if diff.seconds >= 0 else f"{minutes} minutes ago"
        else:  # Less than 1 day
            hours = diff.seconds // 3600
            if hours == 1:
                return "in 1 hour" if diff.seconds >= 0 else "1 hour ago"
            else:
                return f"in {hours} hours" if diff.seconds >= 0 else f"{hours} hours ago"
    
    elif abs(diff.days) == 1:
        if diff.days > 0:
            return "tomorrow"
        else:
            return "yesterday"
    
    elif abs(diff.days) < 7:
        if diff.days > 0:
            return f"in {diff.days} days"
        else:
            return f"{abs(diff.days)} days ago"
    
    else:
        # Use standard format for dates further away
        return dt.strftime("%B %d, %Y at %I:%M %p")


def get_next_occurrence(base_date: datetime, pattern: str, interval: int = 1) -> Optional[datetime]:
    """Get the next occurrence of a recurring event."""
    if pattern.lower() == "daily":
        return base_date + timedelta(days=interval)
    elif pattern.lower() == "weekly":
        return base_date + timedelta(weeks=interval)
    elif pattern.lower() == "monthly":
        # Handle month boundaries
        month = base_date.month + interval
        year = base_date.year
        while month > 12:
            month -= 12
            year += 1
        try:
            return base_date.replace(year=year, month=month)
        except ValueError:
            # Handle cases like Feb 31 -> Feb 28/29
            import calendar
            last_day = calendar.monthrange(year, month)[1]
            day = min(base_date.day, last_day)
            return base_date.replace(year=year, month=month, day=day)
    elif pattern.lower() == "yearly":
        try:
            return base_date.replace(year=base_date.year + interval)
        except ValueError:
            # Handle leap year edge case (Feb 29)
            return base_date.replace(year=base_date.year + interval, month=2, day=28)
    
    return None


def is_business_day(dt: datetime) -> bool:
    """Check if a datetime falls on a business day (Monday-Friday)."""
    return dt.weekday() < 5  # 0-4 are Monday-Friday


def get_business_days_between(start_date: datetime, end_date: datetime) -> int:
    """Count business days between two dates."""
    current_date = start_date
    business_days = 0
    
    while current_date <= end_date:
        if is_business_day(current_date):
            business_days += 1
        current_date += timedelta(days=1)
    
    return business_days