"""Tests for Clockwork utils module."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from pathlib import Path
import yaml
from custom_components.clockwork.utils import (
    parse_offset,
    validate_offset_string,
    is_datetime_between,
    scan_automations_for_time_usage,
)


class TestParseOffset:
    """Test parse_offset function."""

    def test_parse_offset_single_unit(self):
        """Test parsing single unit offsets."""
        assert parse_offset("1 second") == 1
        assert parse_offset("1 minute") == 60
        assert parse_offset("1 hour") == 3600
        assert parse_offset("1 day") == 86400
        assert parse_offset("1 week") == 604800

    def test_parse_offset_multiple_values(self):
        """Test parsing multiple values."""
        assert parse_offset("2 hours") == 7200
        assert parse_offset("30 minutes") == 1800
        assert parse_offset("7 days") == 604800
        assert parse_offset("2 weeks") == 1209600

    def test_parse_offset_whitespace(self):
        """Test parsing with extra whitespace."""
        assert parse_offset("  1 hour  ") == 3600
        assert parse_offset("1  hour") == 3600

    def test_parse_offset_singular_units(self):
        """Test parsing singular units."""
        assert parse_offset("1 second") == 1
        assert parse_offset("1 minute") == 60
        assert parse_offset("1 hour") == 3600

    def test_parse_offset_plurals(self):
        """Test parsing plural units."""
        assert parse_offset("5 seconds") == 5
        assert parse_offset("10 minutes") == 600
        assert parse_offset("3 hours") == 10800


class TestValidateOffsetString:
    """Test validate_offset_string function."""

    def test_validate_valid_offsets(self):
        """Test validation of valid offset strings."""
        assert validate_offset_string("1 hour") == (True, None)
        assert validate_offset_string("30 minutes") == (True, None)
        assert validate_offset_string("2 days") == (True, None)
        assert validate_offset_string("1 week") == (True, None)

    def test_validate_empty_string(self):
        """Test validation of empty string."""
        is_valid, error = validate_offset_string("")
        assert not is_valid
        assert error is not None

    def test_validate_none(self):
        """Test validation of None."""
        is_valid, error = validate_offset_string(None)
        assert not is_valid
        assert error is not None

    def test_validate_zero_value(self):
        """Test validation of zero value."""
        is_valid, error = validate_offset_string("0 hours")
        assert not is_valid
        assert "non-zero" in error.lower()

    def test_validate_negative_value(self):
        """Test validation of negative value (used for datetime_offset)."""
        is_valid, error = validate_offset_string("-1 hour")
        assert is_valid
        assert error is None

    def test_validate_invalid_unit(self):
        """Test validation of invalid unit."""
        is_valid, error = validate_offset_string("1 year")
        assert not is_valid
        assert error is not None

    def test_validate_malformed_string(self):
        """Test validation of malformed string."""
        is_valid, error = validate_offset_string("abc def")
        assert not is_valid
        assert error is not None


class TestIsDatetimeBetween:
    """Test is_datetime_between function."""

    def test_datetime_between_simple(self):
        """Test simple datetime between check."""
        start = datetime(2026, 2, 10, 3, 0, 0)
        end = datetime(2026, 2, 10, 23, 59, 59)
        check = datetime(2026, 2, 10, 12, 0, 0)
        assert is_datetime_between(check, start, end)

    def test_datetime_between_before_range(self):
        """Test datetime before range."""
        start = datetime(2026, 2, 10, 3, 0, 0)
        end = datetime(2026, 2, 10, 23, 59, 59)
        check = datetime(2026, 2, 10, 2, 0, 0)
        assert not is_datetime_between(check, start, end)

    def test_datetime_between_after_range(self):
        """Test datetime after range."""
        start = datetime(2026, 2, 10, 3, 0, 0)
        end = datetime(2026, 2, 10, 23, 59, 59)
        check = datetime(2026, 2, 11, 1, 0, 0)
        assert not is_datetime_between(check, start, end)

    def test_datetime_between_on_start(self):
        """Test datetime at start boundary."""
        start = datetime(2026, 2, 10, 3, 0, 0)
        end = datetime(2026, 2, 10, 23, 59, 59)
        check = datetime(2026, 2, 10, 3, 0, 0)
        assert is_datetime_between(check, start, end)

    def test_datetime_between_on_end(self):
        """Test datetime at end boundary."""
        start = datetime(2026, 2, 10, 3, 0, 0)
        end = datetime(2026, 2, 10, 23, 59, 59)
        check = datetime(2026, 2, 10, 23, 59, 59)
        assert is_datetime_between(check, start, end)

    def test_datetime_between_recurring_daily(self):
        """Test recurring daily time range (same date on entities, different check date)."""
        start = datetime(2026, 2, 10, 4, 0, 0)  # 4am
        end = datetime(2026, 2, 10, 23, 0, 0)   # 11pm
        # Check on different date at 9pm - should be within range
        check = datetime(2026, 2, 11, 21, 0, 0)
        assert is_datetime_between(check, start, end)

    def test_datetime_between_recurring_outside_range(self):
        """Test recurring daily range outside hours."""
        start = datetime(2026, 2, 10, 4, 0, 0)  # 4am
        end = datetime(2026, 2, 10, 23, 0, 0)   # 11pm
        # Check on different date at 2am - outside range
        check = datetime(2026, 2, 11, 2, 0, 0)
        assert not is_datetime_between(check, start, end)

    def test_datetime_between_overnight_range(self):
        """Test overnight range (start after end time)."""
        start = datetime(2026, 2, 10, 22, 0, 0)  # 10pm
        end = datetime(2026, 2, 10, 4, 0, 0)     # 4am
        # Check at 11pm - should be in range
        check = datetime(2026, 2, 11, 23, 0, 0)
        assert is_datetime_between(check, start, end)

    def test_datetime_between_overnight_before_midnight(self):
        """Test overnight range before midnight."""
        start = datetime(2026, 2, 10, 22, 0, 0)  # 10pm
        end = datetime(2026, 2, 10, 4, 0, 0)     # 4am
        # Check at 3am - should be in range
        check = datetime(2026, 2, 11, 3, 0, 0)
        assert is_datetime_between(check, start, end)

    def test_datetime_between_overnight_outside_range(self):
        """Test overnight range outside hours."""
        start = datetime(2026, 2, 10, 22, 0, 0)  # 10pm
        end = datetime(2026, 2, 10, 4, 0, 0)     # 4am
        # Check at 10am - should be outside range
        check = datetime(2026, 2, 11, 10, 0, 0)
        assert not is_datetime_between(check, start, end)

    def test_datetime_between_timezone_aware(self):
        """Test with timezone-aware datetimes."""
        tz = timezone.utc
        start = datetime(2026, 2, 10, 3, 0, 0, tzinfo=tz)
        end = datetime(2026, 2, 10, 23, 59, 59, tzinfo=tz)
        check = datetime(2026, 2, 10, 12, 0, 0, tzinfo=tz)
        assert is_datetime_between(check, start, end)

    def test_datetime_between_multiday_range(self):
        """Test multi-day datetime range."""
        start = datetime(2026, 2, 10, 10, 0, 0)
        end = datetime(2026, 2, 15, 18, 0, 0)
        # Check in the middle
        check = datetime(2026, 2, 12, 12, 0, 0)
        assert is_datetime_between(check, start, end)

    def test_datetime_between_multiday_before(self):
        """Test multi-day range before start."""
        start = datetime(2026, 2, 10, 10, 0, 0)
        end = datetime(2026, 2, 15, 18, 0, 0)
        check = datetime(2026, 2, 9, 12, 0, 0)
        assert not is_datetime_between(check, start, end)

    def test_datetime_between_multiday_after(self):
        """Test multi-day range after end."""
        start = datetime(2026, 2, 10, 10, 0, 0)
        end = datetime(2026, 2, 15, 18, 0, 0)
        check = datetime(2026, 2, 16, 12, 0, 0)
        assert not is_datetime_between(check, start, end)


class TestScanAutomations:
    """Test scan_automations_for_time_usage function."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = MagicMock()
        hass.config.path.return_value = "/config"
        return hass

    def test_scan_automations_basic(self, mock_hass):
        """Test automation scanning returns proper structure."""
        # Basic integration test - function is called and doesn't crash
        result = scan_automations_for_time_usage(mock_hass)
        
        # Should always have automations key
        assert "automations" in result
        assert isinstance(result["automations"], list)


class TestHolidayCalculations:
    """Test holiday date calculation functions."""

    def test_get_nth_weekday_first_occurrence(self):
        """Test getting first occurrence of a weekday in month."""
        from custom_components.clockwork.utils import _get_nth_weekday
        
        # First Monday of January 2026 is January 5
        result = _get_nth_weekday(2026, 1, 1, 0)
        from datetime import date
        assert result == date(2026, 1, 5)

    def test_get_nth_weekday_third_occurrence(self):
        """Test getting third occurrence of a weekday."""
        from custom_components.clockwork.utils import _get_nth_weekday
        
        # Third Thursday of November 2026
        result = _get_nth_weekday(2026, 11, 3, 3)
        from datetime import date
        # November 19, 2026 should be a Thursday
        assert result is not None
        assert result.month == 11

    def test_get_nth_weekday_beyond_available(self):
        """Test getting occurrence beyond available weeks."""
        from custom_components.clockwork.utils import _get_nth_weekday
        
        # Try to get 6th Monday in January (won't exist)
        result = _get_nth_weekday(2026, 1, 6, 0)
        assert result is None

    def test_get_last_weekday(self):
        """Test getting last occurrence of weekday in month."""
        from custom_components.clockwork.utils import _get_last_weekday
        
        # Last Friday of December 2026
        result = _get_last_weekday(2026, 12, 4)
        from datetime import date
        assert result is not None
        assert result.month == 12
        assert result.day > 24  # Last Friday should be late in month

    def test_get_last_weekday_february_leap_year(self):
        """Test last weekday in February leap year."""
        from custom_components.clockwork.utils import _get_last_weekday
        
        # 2024 is a leap year, last day is Feb 29
        result = _get_last_weekday(2024, 2, 6)  # Sunday
        from datetime import date
        assert result is not None
        assert result.year == 2024
        assert result.month == 2

    def test_get_holiday_date_fixed_holiday(self):
        """Test getting fixed holiday date."""
        from custom_components.clockwork.utils import get_holiday_date
        from unittest.mock import MagicMock
        
        hass = MagicMock()
        hass.data = {
            "clockwork": {
                "holidays": {
                    "holidays": [
                        {"key": "christmas", "type": "fixed", "month": 12, "day": 25}
                    ]
                }
            }
        }
        
        from datetime import date
        result = get_holiday_date(hass, 2026, "christmas")
        assert result == date(2026, 12, 25)

    def test_get_holiday_date_nth_weekday_holiday(self):
        """Test getting nth_weekday holiday."""
        from custom_components.clockwork.utils import get_holiday_date
        from unittest.mock import MagicMock
        
        hass = MagicMock()
        hass.data = {
            "clockwork": {
                "holidays": {
                    "holidays": [
                        {
                            "key": "thanksgiving",
                            "type": "nth_weekday",
                            "month": 11,
                            "occurrence": 4,
                            "weekday": 3  # Thursday
                        }
                    ]
                }
            }
        }
        
        result = get_holiday_date(hass, 2026, "thanksgiving")
        assert result is not None
        assert result.month == 11

    def test_get_holiday_date_nonexistent_key(self):
        """Test getting nonexistent holiday."""
        from custom_components.clockwork.utils import get_holiday_date
        from unittest.mock import MagicMock
        
        hass = MagicMock()
        hass.data = {
            "clockwork": {
                "holidays": {
                    "holidays": []
                }
            }
        }
        
        result = get_holiday_date(hass, 2026, "nonexistent")
        assert result is None


class TestGetDaysToHoliday:
    """Test get_days_to_holiday function."""

    def test_days_to_holiday_future_date(self):
        """Test days to future holiday."""
        from custom_components.clockwork.utils import get_days_to_holiday
        from unittest.mock import MagicMock
        from datetime import date
        
        hass = MagicMock()
        hass.data = {
            "clockwork": {
                "holidays": {
                    "holidays": [
                        {"key": "test", "type": "fixed", "month": 12, "day": 25}
                    ]
                }
            }
        }
        
        # Today is Jan 1, Christmas is Dec 25
        today = date(2026, 1, 1)
        days = get_days_to_holiday(hass, today, "test")
        assert days == 358

    def test_days_to_holiday_today(self):
        """Test days when today is the holiday."""
        from custom_components.clockwork.utils import get_days_to_holiday
        from unittest.mock import MagicMock
        from datetime import date
        
        hass = MagicMock()
        hass.data = {
            "clockwork": {
                "holidays": {
                    "holidays": [
                        {"key": "test", "type": "fixed", "month": 1, "day": 1}
                    ]
                }
            }
        }
        
        today = date(2026, 1, 1)
        days = get_days_to_holiday(hass, today, "test")
        assert days == 0

    def test_days_to_holiday_passed_rolls_to_next_year(self):
        """Test past holiday rolls to next year."""
        from custom_components.clockwork.utils import get_days_to_holiday
        from unittest.mock import MagicMock
        from datetime import date
        
        hass = MagicMock()
        hass.data = {
            "clockwork": {
                "holidays": {
                    "holidays": [
                        {"key": "test", "type": "fixed", "month": 1, "day": 1}
                    ]
                }
            }
        }
        
        # Today is Jan 2, New Year passed
        today = date(2026, 1, 2)
        days = get_days_to_holiday(hass, today, "test")
        assert days == 364  # Days until Jan 1, 2027


class TestIsInSeasonWrapping:
    """Test is_in_season with wrapping logic."""

    def test_season_wrap_around_year_winter_northern(self):
        """Test winter wrapping (December to February)."""
        from custom_components.clockwork.utils import is_in_season
        from unittest.mock import MagicMock
        from datetime import date
        
        hass = MagicMock()
        hass.data = {
            "clockwork": {
                "seasons": {
                    "northern": [
                        {
                            "key": "winter",
                            "start_month": 12,
                            "start_day": 21,
                            "end_month": 2,
                            "end_day": 28,
                        }
                    ]
                }
            }
        }
        
        # December 25 should be in winter
        assert is_in_season(hass, date(2026, 12, 25), "winter", "northern") is True
        
        # January 15 should be in winter
        assert is_in_season(hass, date(2026, 1, 15), "winter", "northern") is True
        
        # February 15 should be in winter
        assert is_in_season(hass, date(2026, 2, 15), "winter", "northern") is True
        
        # March 15 should not be in winter
        assert is_in_season(hass, date(2026, 3, 15), "winter", "northern") is False

    def test_season_non_wrapping_summer(self):
        """Test summer not wrapping."""
        from custom_components.clockwork.utils import is_in_season
        from unittest.mock import MagicMock
        from datetime import date
        
        hass = MagicMock()
        hass.data = {
            "clockwork": {
                "seasons": {
                    "northern": [
                        {
                            "key": "summer",
                            "start_month": 6,
                            "start_day": 21,
                            "end_month": 9,
                            "end_day": 20,
                        }
                    ]
                }
            }
        }
        
        # June 21 should be in summer
        assert is_in_season(hass, date(2026, 6, 21), "summer", "northern") is True
        
        # July 15 should be in summer
        assert is_in_season(hass, date(2026, 7, 15), "summer", "northern") is True
        
        # Sepember 20 should be in summer
        assert is_in_season(hass, date(2026, 9, 20), "summer", "northern") is True
        
        # May 1 should not be in summer
        assert is_in_season(hass, date(2026, 5, 1), "summer", "northern") is False

    def test_season_feb_29_leap_year(self):
        """Test season boundary on Feb 29 in leap year."""
        from custom_components.clockwork.utils import is_in_season
        from unittest.mock import MagicMock
        from datetime import date
        
        hass = MagicMock()
        hass.data = {
            "clockwork": {
                "seasons": {
                    "northern": [
                        {
                            "key": "test",
                            "start_month": 1,
                            "start_day": 1,
                            "end_month": 2,
                            "end_day": 29,
                        }
                    ]
                }
            }
        }
        
        # 2024 is leap year, Feb 29 exists
        assert is_in_season(hass, date(2024, 2, 29), "test", "northern") is True

    def test_season_feb_28_non_leap_year(self):
        """Test season boundary on Feb 28 in non-leap year."""
        from custom_components.clockwork.utils import is_in_season
        from unittest.mock import MagicMock
        from datetime import date
        
        hass = MagicMock()
        hass.data = {
            "clockwork": {
                "seasons": {
                    "northern": [
                        {
                            "key": "test",
                            "start_month": 1,
                            "start_day": 1,
                            "end_month": 2,
                            "end_day": 29,
                        }
                    ]
                }
            }
        }
        
        # 2026 is not a leap year, Feb 29 doesn't exist
        assert is_in_season(hass, date(2026, 2, 28), "test", "northern") is True

    def test_season_southern_hemisphere(self):
        """Test southern hemisphere season."""
        from custom_components.clockwork.utils import is_in_season
        from unittest.mock import MagicMock
        from datetime import date
        
        hass = MagicMock()
        hass.data = {
            "clockwork": {
                "seasons": {
                    "southern": [
                        {
                            "key": "winter",
                            "start_month": 6,
                            "start_day": 21,
                            "end_month": 8,
                            "end_day": 28,
                        }
                    ]
                }
            }
        }
        
        # June 21 should be winter in southern hemisphere
        assert is_in_season(hass, date(2026, 6, 21), "winter", "southern") is True


class TestOffsetParseEdgeCases:
    """Test parse_offset with various edge cases."""

    def test_parse_offset_negative_value(self):
        """Test parsing negative offset."""
        # Negative values might be supported for reverse counting
        result = parse_offset("-5 minutes")
        assert result == -300

    def test_parse_offset_zero_value(self):
        """Test parsing zero offset."""
        result = parse_offset("0 seconds")
        assert result == 0

    def test_parse_offset_large_value(self):
        """Test parsing large offset."""
        result = parse_offset("365 days")
        assert result == 31536000

    def test_parse_offset_float_value(self):
        """Test that float values don't work (int conversion)."""
        result = parse_offset("1.5 hours")
        assert result == 0  # Should fail on int() conversion

    def test_parse_offset_case_insensitive(self):
        """Test case insensitivity."""
        assert parse_offset("5 MINUTES") == 300
        assert parse_offset("5 Minutes") == 300
        assert parse_offset("5 HOURS") == 18000

    def test_parse_offset_plurals_and_singulars(self):
        """Test both plural and singular units."""
        assert parse_offset("1 second") == 1
        assert parse_offset("1 seconds") == 1
        assert parse_offset("2 hour") == 7200
        assert parse_offset("2 hours") == 7200

    def test_parse_offset_combined_units(self):
        """Test that only single unit is parsed."""
        # This should only parse the first unit
        result = parse_offset("1 hour 30 minutes")
        assert result == 3600  # Just the hour part


class TestValidateOffsetString:
    """Test validate_offset_string function."""

    def test_validate_valid_format(self):
        """Test validation of valid format."""
        from custom_components.clockwork.utils import validate_offset_string
        
        is_valid, error = validate_offset_string("5 minutes")
        assert is_valid is True
        assert error is None

    def test_validate_invalid_unit(self):
        """Test validation with invalid unit."""
        from custom_components.clockwork.utils import validate_offset_string
        
        is_valid, error = validate_offset_string("5 fortnights")
        assert is_valid is False
        assert error is not None

    def test_validate_missing_unit(self):
        """Test validation with missing unit."""
        from custom_components.clockwork.utils import validate_offset_string
        
        is_valid, error = validate_offset_string("5")
        assert is_valid is False
        assert error is not None

    def test_validate_none_input(self):
        """Test validation with None input."""
        from custom_components.clockwork.utils import validate_offset_string
        
        is_valid, error = validate_offset_string(None)
        assert is_valid is False
        assert error is not None

    def test_validate_empty_string(self):
        """Test validation with empty string."""
        from custom_components.clockwork.utils import validate_offset_string
        
        is_valid, error = validate_offset_string("")
        assert is_valid is False
        assert error is not None

    def test_validate_non_integer_value(self):
        """Test validation with non-integer value."""
        from custom_components.clockwork.utils import validate_offset_string
        
        is_valid, error = validate_offset_string("abc minutes")
        assert is_valid is False
        assert error is not None
