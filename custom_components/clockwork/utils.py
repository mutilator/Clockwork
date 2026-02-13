"""Utility functions for Clockwork date and time calculations."""
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def parse_datetime_or_date(value: str) -> Optional[datetime]:
    """Parse a datetime or date string, treating date-only as midnight.
    
    Handles both:
    - Full datetime: "2025-11-15T00:00:00" or "2025-11-15T12:30:45+02:00"
    - Date only: "2025-12-30" (treated as "2025-12-30T00:00:00")
    
    Args:
        value: String representation of datetime or date
    
    Returns:
        datetime object with time set to 00:00:00 if input is date-only, or None if parsing fails
    """
    if not value:
        return None
    
    # First try to parse as a full datetime
    dt = dt_util.parse_datetime(value)
    if dt is not None:
        return dt
    
    # If that fails, try to parse as a date and convert to datetime at midnight
    try:
        # Try parsing as ISO date format (YYYY-MM-DD)
        parsed_date = datetime.strptime(value.strip(), "%Y-%m-%d").date()
        # Convert to datetime at midnight
        return datetime.combine(parsed_date, datetime.min.time())
    except (ValueError, TypeError):
        _LOGGER.debug(f"Could not parse datetime or date from: {value}")
        return None



def get_holidays(hass: "HomeAssistant", custom_holidays: Optional[List[Dict]] = None) -> Dict:
    """Get holidays data from hass.data, merged with custom holidays.
    
    Args:
        hass: Home Assistant instance
        custom_holidays: Optional list of custom holiday definitions to merge
    
    Returns:
        Dictionary with merged holidays
    """
    # Get cached holidays from hass.data (loaded at integration setup)
    holidays_data = hass.data[DOMAIN].get("holidays", {"holidays": []})

    
    # Create a copy to avoid modifying cache
    result = holidays_data.copy()
    holidays_list = result.get("holidays", []).copy()
    
    # Merge custom holidays if provided
    if custom_holidays:
        holidays_list.extend(custom_holidays)
    
    result["holidays"] = holidays_list
    return result


def get_seasons(hass: "HomeAssistant") -> Dict:
    """Get seasons data from hass.data.
    
    Args:
        hass: Home Assistant instance
    """
    # Get cached seasons from hass.data (loaded at integration setup)
    return hass.data[DOMAIN].get("seasons", {"seasons": []})


def get_holiday_date(hass: "HomeAssistant", target_year: int, holiday_key: str, custom_holidays: Optional[List[Dict]] = None) -> Optional[date]:
    """Calculate the date for a given holiday in a specific year.
    
    Args:
        hass: Home Assistant instance
        target_year: Year to calculate for
        holiday_key: Holiday key to look up
        custom_holidays: Optional list of custom holiday definitions
    """
    holidays = get_holidays(hass, custom_holidays)
    
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


def is_in_season(hass: "HomeAssistant", check_date: date, season_key: str, hemisphere: str = "northern") -> bool:
    """Check if a date falls within a given season.
    
    Args:
        hass: Home Assistant instance
        check_date: Date to check
        season_key: Season key (spring, summer, autumn, winter)
        hemisphere: Hemisphere ("northern" or "southern"), defaults to "northern"
    """
    seasons_data = get_seasons(hass)
    seasons_list = seasons_data.get(hemisphere, [])
    
    for season in seasons_list:
        if season["key"] == season_key:
            start_month = season.get("start_month")
            start_day = season.get("start_day")
            end_month = season.get("end_month")
            end_day = season.get("end_day")
            
            # Convert to date format for comparison
            start_date = date(check_date.year, start_month, start_day)
            
            # Handle end_date, accounting for leap years (e.g., Feb 29)
            try:
                end_date = date(check_date.year, end_month, end_day)
            except ValueError:
                # If date is invalid (e.g., Feb 29 in non-leap year), use last day of month
                if end_month == 2:
                    # February: use 28 for non-leap years, 29 for leap years
                    end_date = date(check_date.year, 2, 28)
                else:
                    # Other months: fallback to day 1 of next month minus 1
                    from calendar import monthrange
                    last_day = monthrange(check_date.year, end_month)[1]
                    end_date = date(check_date.year, end_month, last_day)
            
            # Handle seasons that wrap around the year (winter)
            if start_month > end_month:
                # Season wraps over year boundary
                return check_date >= start_date or check_date <= end_date
            else:
                # Normal season
                return start_date <= check_date <= end_date
    
    return False


def get_days_to_holiday(hass: "HomeAssistant", today: date, holiday_key: str, custom_holidays: Optional[List[Dict]] = None) -> int:
    """Calculate days until the next occurrence of a holiday.
    
    Args:
        hass: Home Assistant instance
        today: Reference date (usually today)
        holiday_key: Holiday key
        custom_holidays: Optional list of custom holiday definitions
    
    Returns:
        Number of days until holiday. Returns 0 if today is the holiday.
        Returns negative number if holiday has passed and won't occur again this year.
    """
    holiday_date = get_holiday_date(hass, today.year, holiday_key, custom_holidays)
    
    if holiday_date is None:
        return -1
    
    delta = (holiday_date - today).days
    
    # If holiday has passed, return days to next year's holiday
    if delta < 0:
        next_year_holiday = get_holiday_date(hass, today.year + 1, holiday_key, custom_holidays)
        if next_year_holiday:
            delta = (next_year_holiday - today).days
    
    return delta


def parse_offset(offset_str: str) -> int:
    """Parse offset string like '1 hour' to seconds.
    
    Args:
        offset_str: Offset string (e.g., '1 hour', '30 minutes', '2 days')
    
    Returns:
        Offset in seconds, or 0 if parsing fails
    """
    if not offset_str:
        return 0
    
    try:
        parts = str(offset_str).strip().split()
        if len(parts) < 2:
            _LOGGER.warning(f"Invalid offset format '{offset_str}': expected 'value unit' format")
            return 0
        
        value = int(parts[0])
        unit = parts[1].lower().rstrip('s')
        
        conversions = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
            "week": 604800,
        }
        
        if unit not in conversions:
            _LOGGER.warning(f"Unknown time unit '{unit}' in offset string '{offset_str}'. Valid units: second, minute, hour, day, week")
            return 0
        
        return value * conversions[unit]
    except (ValueError, IndexError, AttributeError, TypeError) as err:
        _LOGGER.error(f"Error parsing offset '{offset_str}': {err}")
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
    
    try:
        offset_str = str(offset_str).strip()
        if not offset_str:
            return False, "Offset cannot be empty"
        
        parts = offset_str.split()
        
        if len(parts) < 2:
            return False, "Format must be like '1 hour' or '30 minutes' (e.g., '-2 days', '1 hour')"
        
        if len(parts) > 2:
            return False, "Offset must contain only value and unit (e.g., '1 hour'), not extra words"
        
        try:
            value = int(parts[0])
        except ValueError:
            return False, f"Offset value must be an integer, got '{parts[0]}'"
        
        if value == 0:
            return False, "Offset value must be non-zero (greater or less than 0)"
        
        unit = parts[1].lower().rstrip('s')
        
        valid_units = ["second", "minute", "hour", "day", "week"]
        if unit not in valid_units:
            return False, f"Invalid time unit '{parts[1]}'. Valid units are: {', '.join(valid_units)}"
        
        return True, None
    except (AttributeError, TypeError) as err:
        _LOGGER.error(f"Error validating offset string: {err}")
        return False, f"Invalid offset format: {err}"


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
    
    Raises:
        ValueError: If any datetime argument is None
    """
    if check_datetime is None or start_datetime is None or end_datetime is None:
        _LOGGER.error(f"is_datetime_between called with None values: check={check_datetime}, start={start_datetime}, end={end_datetime}")
        raise ValueError("All datetime arguments must be provided (not None)")
    
    try:
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
    except (AttributeError, TypeError) as err:
        _LOGGER.error(f"Error checking if datetime is between ranges: {err}")
        raise


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
    
    Raises:
        ValueError: If any datetime argument is None or invalid
    """
    if None in (range1_start, range1_end, range2_start, range2_end):
        _LOGGER.error(f"do_ranges_overlap called with None values: r1_start={range1_start}, r1_end={range1_end}, r2_start={range2_start}, r2_end={range2_end}")
        raise ValueError("All range datetime arguments must be provided (not None)")
    
    try:
        if range1_start > range1_end or range2_start > range2_end:
            _LOGGER.warning(f"Range has start > end: range1=({range1_start}, {range1_end}), range2=({range2_start}, {range2_end})")
        
        # Two ranges overlap if one doesn't end before the other starts
        return not (range1_end < range2_start or range2_end < range1_start)
    except TypeError as err:
        _LOGGER.error(f"Error checking if ranges overlap: {err}")
        raise ValueError("Invalid datetime arguments in range comparison") from err


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
        New datetime with offset applied, or base_datetime if offset parsing fails
    """
    if base_datetime is None:
        _LOGGER.error("Cannot apply offset: base_datetime is None")
        return None
    
    if not offset_str:
        return base_datetime
    
    # Parse offset including negative values
    try:
        parts = str(offset_str).strip().split()
        if len(parts) < 2:
            _LOGGER.warning(f"Invalid offset format '{offset_str}': expected 'value unit' format (e.g., '1 hour')")
            return base_datetime
        
        value = int(parts[0])
        unit = parts[1].lower().rstrip('s')
        
        conversions = {
            "second": lambda v: timedelta(seconds=v),
            "minute": lambda v: timedelta(minutes=v),
            "hour": lambda v: timedelta(hours=v),
            "day": lambda v: timedelta(days=v),
            "week": lambda v: timedelta(weeks=v),
        }
        
        if unit not in conversions:
            _LOGGER.warning(f"Unknown time unit '{unit}' in offset string '{offset_str}'. Valid units: second, minute, hour, day, week")
            return base_datetime
            
        delta = conversions[unit](value)
        return base_datetime + delta
    except (ValueError, IndexError, AttributeError, TypeError) as err:
        _LOGGER.error(f"Error applying offset '{offset_str}' to datetime: {err}")
        return base_datetime


def scan_automations_for_time_usage(hass: "HomeAssistant") -> Dict[str, dict]:
    """Scan automations.yaml for automations using date/time functions.
    
    Searches for common date/time patterns in automation triggers and conditions.
    
    Args:
        hass: Home Assistant instance
        
    Returns:
        Dictionary with 'automations' list containing matched automations
        Format: {
            'automations': [
                {
                    'id': 'automation_id',
                    'alias': 'Automation Alias',
                    'patterns': ['list', 'of', 'patterns', 'found']
                },
                ...
            ]
        }
    """
    import re
    import yaml
    from pathlib import Path
    
    # Patterns to search for in automation content
    time_patterns = {
        'at': r'\bat:',  # at: trigger
        'platform_time': r'\bplatform:\s*time',  # platform: time
        'condition_time': r'\bcondition:\s*time',  # condition: time
        'before': r'\b(before|after|weekday):\s*',  # before/after/weekday condition
        'now_function': r'\bnow\(\)',  # now() function
        'utcnow_function': r'\butcnow\(\)',  # utcnow() function
        'relative_date': r'\b(trigger\.(yesterday|tomorrow))',  # relative dates
        'time_field': r'\b(hour|minute|second|month|day|year|date|time):\s*',  # time fields
        'timestamp': r'\b(timestamp|epoch)\b',  # timestamp references
    }
    
    result = {'automations': []}
    
    try:
        # Try to load automations.yaml from config directory
        config_dir = hass.config.path()
        automations_path = Path(config_dir) / "automations.yaml"
        
        if not automations_path.exists():
            _LOGGER.debug("automations.yaml not found, no automations to scan")
            return result
        
        with open(automations_path, 'r') as f:
            content = f.read()
        
        # Parse YAML
        try:
            automations = yaml.safe_load(content) or []
        except yaml.YAMLError as err:
            _LOGGER.error(f"Error parsing automations.yaml: {err}")
            return result
        
        # Ensure automations is a list
        if not isinstance(automations, list):
            automations = [automations] if automations else []
        
        # Search each automation for time patterns
        for automation in automations:
            if not isinstance(automation, dict):
                continue
                
            auto_id = automation.get('id', '')
            auto_alias = automation.get('alias', auto_id)
            
            # Convert automation to string for pattern matching
            auto_str = str(automation).lower()
            
            # Find all matching patterns
            found_patterns = []
            for pattern_name, pattern_regex in time_patterns.items():
                if re.search(pattern_regex, auto_str, re.IGNORECASE):
                    found_patterns.append(pattern_name)
            
            # Add to results if any patterns found
            if found_patterns:
                result['automations'].append({
                    'id': auto_id,
                    'alias': auto_alias,
                    'patterns': found_patterns
                })
        
        _LOGGER.debug(f"Found {len(result['automations'])} automations with time/date patterns")
        return result
        
    except Exception as err:
        _LOGGER.error(f"Error scanning automations.yaml: {err}")
        return result