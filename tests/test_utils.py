"""Tests for Clockwork utils module."""
import pytest
from datetime import datetime, timedelta, timezone
from custom_components.clockwork.utils import (
    parse_offset,
    validate_offset_string,
    is_datetime_between,
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
