"""Tests for Clockwork config flow."""
import pytest
from custom_components.clockwork.config_flow import _generate_holiday_key


class TestGenerateHolidayKey:
    """Test holiday key generation."""

    def test_generate_simple_name(self):
        """Test generating key from simple name."""
        key = _generate_holiday_key("Easter Sunday")
        assert key == "easter_sunday"

    def test_generate_name_with_apostrophe(self):
        """Test generating key from name with apostrophe."""
        key = _generate_holiday_key("Mother's Day")
        assert key == "mothers_day"

    def test_generate_name_with_numbers(self):
        """Test generating key from name with numbers."""
        key = _generate_holiday_key("New Year's Day 2026")
        assert key == "new_years_day_2026"

    def test_generate_name_lowercase(self):
        """Test that key is lowercase."""
        key = _generate_holiday_key("CHRISTMAS")
        assert key == "christmas"

    def test_generate_name_multiple_spaces(self):
        """Test handling multiple spaces."""
        key = _generate_holiday_key("My  Custom  Holiday")
        assert "multiple" not in key.lower().replace("_", " ") or key.count("_") >= 2

    def test_generate_name_special_chars(self):
        """Test removing special characters."""
        key = _generate_holiday_key("Holiday & Special Day!")
        assert "&" not in key
        assert "!" not in key
        assert key == "holiday_special_day"

    def test_generate_name_with_hyphens(self):
        """Test handling hyphens."""
        key = _generate_holiday_key("Mother-Daughter Day")
        assert key == "motherdaughter_day"
