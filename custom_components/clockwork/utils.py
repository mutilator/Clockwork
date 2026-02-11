"""Utility functions for Clockwork date and time calculations."""
import json
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

_HOLIDAYS_CACHE: Optional[Dict] = None
_SEASONS_CACHE: Optional[Dict] = None


def _load_json_file(filename: str) -> Dict:
    """Load a JSON file from the component directory."""
    file_path = Path(__file__).parent / filename
    with open(file_path, 'r') as f:
        return json.load(f)


def get_holidays(custom_holidays: Optional[List[Dict]] = None) -> Dict:
    """Get holidays data from cache or load from file, merged with custom holidays.
    
    Args:
        custom_holidays: Optional list of custom holiday definitions to merge
    
    Returns:
        Dictionary with merged holidays
    """
    global _HOLIDAYS_CACHE
    if _HOLIDAYS_CACHE is None:
        _HOLIDAYS_CACHE = _load_json_file("holidays.json")
    
    # Create a copy to avoid modifying cache
    result = _HOLIDAYS_CACHE.copy()
    holidays_list = result.get("holidays", []).copy()
    
    # Merge custom holidays if provided
    if custom_holidays:
        holidays_list.extend(custom_holidays)
    
    result["holidays"] = holidays_list
    return result


def get_seasons() -> Dict:
    """Get seasons data from cache or load from file."""
    global _SEASONS_CACHE
    if _SEASONS_CACHE is None:
        _SEASONS_CACHE = _load_json_file("seasons.json")
    return _SEASONS_CACHE


def get_holiday_date(target_year: int, holiday_key: str, custom_holidays: Optional[List[Dict]] = None) -> Optional[date]:
    """Calculate the date for a given holiday in a specific year.
    
    Args:
        target_year: Year to calculate for
        holiday_key: Holiday key to look up
        custom_holidays: Optional list of custom holiday definitions
    """
    holidays = get_holidays(custom_holidays)
    
    for holiday in holidays.get("holidays", []):
        if holiday["key"] == holiday_key:
            holiday_type = holiday.get("type")
            month = holiday.get("month")
            
            if holiday_type == "fixed":
                day = holiday.get("day")
                return date(target_year, month, day)
            
            elif holiday_type == "nth_weekday":
                # Calculate Nth occurrence of weekday in month
                occurrence = holiday.get("occurrence")
                target_weekday = holiday.get("weekday")
                return _get_nth_weekday(target_year, month, occurrence, target_weekday)
            
            elif holiday_type == "last_weekday":
                # Calculate last occurrence of weekday in month
                target_weekday = holiday.get("weekday")
                return _get_last_weekday(target_year, month, target_weekday)
    
    return None


def _get_nth_weekday(year: int, month: int, occurrence: int, weekday: int) -> Optional[date]:
    """Get the nth occurrence of a weekday in a month.
    
    Args:
        year: Year
        month: Month (1-12)
        occurrence: Which occurrence (1-5)
        weekday: Weekday (0=Monday, 6=Sunday)
    """
    from calendar import monthcalendar
    
    cal = monthcalendar(year, month)
    count = 0
    
    for week in cal:
        if week[weekday] == 0:  # Day not in this month
            continue
        count += 1
        if count == occurrence:
            return date(year, month, week[weekday])
    
    return None


def _get_last_weekday(year: int, month: int, weekday: int) -> Optional[date]:
    """Get the last occurrence of a weekday in a month.
    
    Args:
        year: Year
        month: Month (1-12)
        weekday: Weekday (0=Monday, 6=Sunday)
    """
    from calendar import monthcalendar
    
    cal = monthcalendar(year, month)
    
    for week in reversed(cal):
        if week[weekday] != 0:  # Day is in this month
            return date(year, month, week[weekday])
    
    return None


def is_in_season(check_date: date, season_key: str) -> bool:
    """Check if a date falls within a given season.
    
    Args:
        check_date: Date to check
        season_key: Season key (spring, summer, autumn, winter)
    """
    seasons = get_seasons()
    
    for season in seasons.get("seasons", []):
        if season["key"] == season_key:
            start_month = season.get("start_month")
            start_day = season.get("start_day")
            end_month = season.get("end_month")
            end_day = season.get("end_day")
            
            # Convert to date format for comparison
            start_date = date(check_date.year, start_month, start_day)
            end_date = date(check_date.year, end_month, end_day)
            
            # Handle seasons that wrap around the year (winter)
            if start_month > end_month:
                # Season wraps over year boundary
                return check_date >= start_date or check_date <= end_date
            else:
                # Normal season
                return start_date <= check_date <= end_date
    
    return False


def get_days_to_holiday(today: date, holiday_key: str, custom_holidays: Optional[List[Dict]] = None) -> int:
    """Calculate days until the next occurrence of a holiday.
    
    Args:
        today: Reference date (usually today)
        holiday_key: Holiday key
        custom_holidays: Optional list of custom holiday definitions
    
    Returns:
        Number of days until holiday. Returns 0 if today is the holiday.
        Returns negative number if holiday has passed and won't occur again this year.
    """
    holiday_date = get_holiday_date(today.year, holiday_key, custom_holidays)
    
    if holiday_date is None:
        return -1
    
    delta = (holiday_date - today).days
    
    # If holiday has passed, return days to next year's holiday
    if delta < 0:
        next_year_holiday = get_holiday_date(today.year + 1, holiday_key, custom_holidays)
        if next_year_holiday:
            delta = (next_year_holiday - today).days
    
    return delta


def parse_offset(offset_str: str) -> int:
    """Parse offset string like '1 hour' to seconds.
    
    Args:
        offset_str: Offset string (e.g., '1 hour', '30 minutes', '2 days')
    
    Returns:
        Offset in seconds
    """
    if not offset_str:
        return 0
    
    parts = str(offset_str).strip().split()
    if len(parts) < 2:
        return 0
    
    try:
        value = int(parts[0])
        unit = parts[1].lower().rstrip('s')
        
        conversions = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
            "week": 604800,
        }
        
        return value * conversions.get(unit, 0)
    except (ValueError, IndexError):
        return 0


def validate_offset_string(offset_str: str) -> Tuple[bool, Optional[str]]:
    """Validate that an offset string can be parsed correctly.
    
    Args:
        offset_str: Offset string to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not offset_str or not isinstance(offset_str, str):
        return False, "Offset is required"
    
    offset_str = str(offset_str).strip()
    parts = offset_str.split()
    
    if len(parts) < 2:
        return False, "Format must be like '1 hour' or '30 minutes'"
    
    try:
        value = int(parts[0])
        if value == 0:
            return False, "Offset value must be greater than 0"
        unit = parts[1].lower().rstrip('s')
        
        valid_units = ["second", "minute", "hour", "day", "week"]
        if unit not in valid_units:
            return False, f"Invalid unit '{parts[1]}'. Valid units are: {', '.join(valid_units)}"
        
        return True, None
    except (ValueError, IndexError):
        return False, "Format must be like '1 hour' or '30 minutes'"


def is_datetime_between(check_datetime: datetime, start_datetime: datetime, end_datetime: datetime) -> bool:
    """Check if a datetime falls between two datetimes.
    
    Handles both fixed date ranges and recurring daily time ranges.
    If start and end are on different dates than the check datetime,
    compares only the time components for daily recurring ranges.
    Also handles overnight ranges (e.g., 11pm to 4am).
    
    Args:
        check_datetime: Datetime to check
        start_datetime: Start of range
        end_datetime: End of range
    
    Returns:
        True if check_datetime is between start and end (inclusive)
    """
    import logging
    _LOGGER = logging.getLogger(__name__)
    
    # If start and end are on the same date
    if start_datetime.date() == end_datetime.date():
        _LOGGER.debug(f"is_datetime_between: Start and end on same date ({start_datetime.date()})")
        
        # If check datetime is also on the same date, do full comparison
        if check_datetime.date() == start_datetime.date():
            result = start_datetime <= check_datetime <= end_datetime
            _LOGGER.debug(f"is_datetime_between: Full datetime comparison - {start_datetime} <= {check_datetime} <= {end_datetime} = {result}")
            return result
        
        # Different date - treat as daily recurring range, compare times only
        check_time = check_datetime.time()
        start_time = start_datetime.time()
        end_time = end_datetime.time()
        
        _LOGGER.debug(f"is_datetime_between: Recurring daily range - Check time: {check_time}, Start time: {start_time}, End time: {end_time}")
        
        # Handle overnight ranges (e.g., 11pm to 4am)
        if start_time <= end_time:
            result = start_time <= check_time <= end_time
            _LOGGER.debug(f"is_datetime_between: Normal range - {start_time} <= {check_time} <= {end_time} = {result}")
            return result
        else:
            result = check_time >= start_time or check_time <= end_time
            _LOGGER.debug(f"is_datetime_between: Overnight range - {check_time} >= {start_time} OR {check_time} <= {end_time} = {result}")
            return result
    
    # Start and end on different dates - normal full datetime comparison
    result = start_datetime <= check_datetime <= end_datetime
    _LOGGER.debug(f"is_datetime_between: Multi-day range - {start_datetime} <= {check_datetime} <= {end_datetime} = {result}")
    return result


def do_ranges_overlap(
    range1_start: datetime, 
    range1_end: datetime, 
    range2_start: datetime, 
    range2_end: datetime
) -> bool:
    """Check if two datetime ranges overlap.
    
    Args:
        range1_start: Start of first range
        range1_end: End of first range
        range2_start: Start of second range
        range2_end: End of second range
    
    Returns:
        True if the ranges overlap at any point
    """
    # Two ranges overlap if one doesn't end before the other starts
    return not (range1_end < range2_start or range2_end < range1_start)


def get_range_overlap(
    range1_start: datetime, 
    range1_end: datetime, 
    range2_start: datetime, 
    range2_end: datetime
) -> Optional[tuple]:
    """Get the overlapping portion of two datetime ranges.
    
    Args:
        range1_start: Start of first range
        range1_end: End of first range
        range2_start: Start of second range
        range2_end: End of second range
    
    Returns:
        Tuple of (overlap_start, overlap_end) if ranges overlap, None otherwise
    """
    if not do_ranges_overlap(range1_start, range1_end, range2_start, range2_end):
        return None
    
    overlap_start = max(range1_start, range2_start)
    overlap_end = min(range1_end, range2_end)
    
    return (overlap_start, overlap_end)


def apply_offset_to_datetime(base_datetime: datetime, offset_str: str) -> Optional[datetime]:
    """Apply an offset string to a datetime.
    
    Args:
        base_datetime: Base datetime
        offset_str: Offset string (e.g., '1 hour', '-30 minutes')
    
    Returns:
        New datetime with offset applied, or None if offset parsing fails
    """
    if not offset_str:
        return base_datetime
    
    # Parse offset including negative values
    parts = str(offset_str).strip().split()
    if len(parts) < 2:
        return base_datetime
    
    try:
        value = int(parts[0])
        unit = parts[1].lower().rstrip('s')
        
        conversions = {
            "second": lambda v: timedelta(seconds=v),
            "minute": lambda v: timedelta(minutes=v),
            "hour": lambda v: timedelta(hours=v),
            "day": lambda v: timedelta(days=v),
            "week": lambda v: timedelta(weeks=v),
        }
        
        if unit in conversions:
            delta = conversions[unit](value)
            return base_datetime + delta
    except (ValueError, IndexError):
        pass
    
    return base_datetime