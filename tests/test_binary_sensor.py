"""Tests for Clockwork binary sensor entities."""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock

from homeassistant.core import HomeAssistant

from custom_components.clockwork.const import (
    CALC_TYPE_OFFSET,
    CALC_TYPE_SEASON,
    CALC_TYPE_MONTH,
    CALC_TYPE_BETWEEN_DATES,
    CALC_TYPE_OUTSIDE_DATES,
)
from custom_components.clockwork.binary_sensor import (
    ClockworkOffsetBinarySensor,
    ClockworkSeasonBinarySensor,
    ClockworkMonthBinarySensor,
    ClockworkBetweenDatesSensor,
    ClockworkOutsideDatesSensor,
)


@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {"clockwork": {"holidays": {}, "seasons": {}}}
    hass.states = MagicMock()
    hass.loop_thread_id = 1  # Mock the loop thread ID for async_write_ha_state
    hass.loop = MagicMock()  # Mock the event loop for async_track_time_interval
    return hass


@pytest.mark.asyncio
class TestClockworkOffsetBinarySensor:
    """Test offset binary sensor."""

    async def test_initialization(self, mock_hass):
        """Test sensor initialization."""
        config = {
            "name": "Test Offset",
            "entity_id": "binary_sensor.test",
            "offset": "1 hour",
            "offset_mode": "latch",
            "trigger_on": "on",
        }
        entry = MagicMock()

        sensor = ClockworkOffsetBinarySensor(config, mock_hass, entry)

        assert sensor.name == "Test Offset Active"
        assert sensor._config == config
        assert sensor._is_on is False

    async def test_unique_id_generation(self, mock_hass):
        """Test unique ID generation."""
        config = {"name": "My Offset Sensor"}
        entry = MagicMock()
        entry.entry_id = "entry_123"

        sensor = ClockworkOffsetBinarySensor(config, mock_hass, entry)

        assert sensor.unique_id == "clockwork_entry_123_my_offset_sensor"

    async def test_async_added_to_hass(self, mock_hass):
        """Test adding to hass."""
        config = {
            "name": "Test",
            "entity_id": "binary_sensor.test",
        }
        entry = MagicMock()

        sensor = ClockworkOffsetBinarySensor(config, mock_hass, entry)

        # Mock async_track_state_change_event
        with patch('custom_components.clockwork.binary_sensor.async_track_state_change_event') as mock_track:
            with patch('custom_components.clockwork.binary_sensor.async_track_time_interval') as mock_timer:
                with patch('threading.get_ident', return_value=1):  # Mock thread ID to match loop_thread_id
                    await sensor.async_added_to_hass()
                    mock_track.assert_called_once()

    def test_icon_property(self, mock_hass):
        """Test that icon property is accessible."""
        config = {
            "name": "Test Offset",
            "entity_id": "binary_sensor.test",
            "offset": "1 hour",
            "offset_mode": "latch",
            "trigger_on": "on",
        }
        entry = MagicMock()

        sensor = ClockworkOffsetBinarySensor(config, mock_hass, entry)
        
        # Should not raise AttributeError
        icon = sensor.icon
        assert icon in ["mdi:alarm", "mdi:alarm-off"]


class TestClockworkSeasonBinarySensor:
    """Test season binary sensor."""

    def test_initialization(self, mock_hass):
        """Test sensor initialization."""
        config = {
            "name": "Test Season",
            "season": "summer",
            "hemisphere": "northern",
        }
        entry = MagicMock()

        sensor = ClockworkSeasonBinarySensor(config, mock_hass, entry)

        assert sensor.name == "Test Season Summer"
        assert sensor._config == config

    def test_icon_property(self, mock_hass):
        """Test that icon property returns correct season icons."""
        entry = MagicMock()
        
        # Test each season
        seasons_icons = {
            "spring": "mdi:flower",
            "summer": "mdi:sun",
            "autumn": "mdi:leaf",
            "winter": "mdi:snowflake",
        }
        
        for season, expected_icon in seasons_icons.items():
            config = {"name": "Test", "season": season, "hemisphere": "northern"}
            sensor = ClockworkSeasonBinarySensor(config, mock_hass, entry)
            assert sensor.icon == expected_icon


class TestClockworkMonthBinarySensor:
    """Test month binary sensor."""

    def test_initialization(self, mock_hass):
        """Test sensor initialization."""
        config = {
            "name": "Test Month",
            "months": "6,7,8",
        }
        entry = MagicMock()

        sensor = ClockworkMonthBinarySensor(config, mock_hass, entry)

        assert sensor.name == "Test Month"
        assert sensor._config == config

    def test_icon_property(self, mock_hass):
        """Test that icon property is accessible without AttributeError."""
        config = {
            "name": "Test Month",
            "months": "6,7,8",
        }
        entry = MagicMock()

        sensor = ClockworkMonthBinarySensor(config, mock_hass, entry)
        
        # This should not raise AttributeError
        icon = sensor.icon
        assert icon in ["mdi:calendar-check", "mdi:calendar-blank"]


class TestClockworkBetweenDatesSensor:
    """Test between dates binary sensor."""

    def test_initialization(self, mock_hass):
        """Test sensor initialization."""
        config = {
            "name": "Test Between Dates",
            "start_datetime_entity": "input_datetime.start",
            "end_datetime_entity": "input_datetime.end",
        }
        entry = MagicMock()

        sensor = ClockworkBetweenDatesSensor(config, mock_hass, entry)

        assert sensor.name == "Test Between Dates"
        assert sensor._config == config

    def test_icon_property(self, mock_hass):
        """Test that icon property is accessible."""
        config = {
            "name": "Test Between",
            "start_datetime_entity": "input_datetime.start",
            "end_datetime_entity": "input_datetime.end",
        }
        entry = MagicMock()

        sensor = ClockworkBetweenDatesSensor(config, mock_hass, entry)
        
        # Should not raise AttributeError
        icon = sensor.icon
        assert icon in ["mdi:calendar-clock", "mdi:calendar-outline"]

    def test_error_state_attributes_missing_start(self, mock_hass):
        """Test error attribute when start entity is missing."""
        mock_hass.states.get.return_value = None
        
        config = {
            "name": "Test Between",
            "start_datetime_entity": "input_datetime.missing",
            "end_datetime_entity": "input_datetime.end",
        }
        entry = MagicMock()

        sensor = ClockworkBetweenDatesSensor(config, mock_hass, entry)
        attrs = sensor.extra_state_attributes
        
        assert "_error" in attrs
        assert "missing" in attrs["_error"]

    def test_error_state_attributes_missing_end(self, mock_hass):
        """Test error attribute when end entity is missing."""
        def mock_get(entity_id):
            return None if entity_id == "input_datetime.missing" else MagicMock()
        
        mock_hass.states.get.side_effect = mock_get
        
        config = {
            "name": "Test Between",
            "start_datetime_entity": "input_datetime.start",
            "end_datetime_entity": "input_datetime.missing",
        }
        entry = MagicMock()

        sensor = ClockworkBetweenDatesSensor(config, mock_hass, entry)
        attrs = sensor.extra_state_attributes
        
        assert "_error" in attrs
        assert "missing" in attrs["_error"]


class TestClockworkOutsideDatesSensor:
    """Test outside dates binary sensor."""

    def test_initialization(self, mock_hass):
        """Test sensor initialization."""
        config = {
            "name": "Test Outside Dates",
            "start_datetime_entity": "input_datetime.start",
            "end_datetime_entity": "input_datetime.end",
        }
        entry = MagicMock()

        sensor = ClockworkOutsideDatesSensor(config, mock_hass, entry)

        assert sensor.name == "Test Outside Dates"
        assert sensor._config == config

    def test_icon_property(self, mock_hass):
        """Test that icon property is accessible."""
        config = {
            "name": "Test Outside",
            "start_datetime_entity": "input_datetime.start",
            "end_datetime_entity": "input_datetime.end",
        }
        entry = MagicMock()

        sensor = ClockworkOutsideDatesSensor(config, mock_hass, entry)
        
        # Should not raise AttributeError
        icon = sensor.icon
        assert icon in ["mdi:calendar-remove", "mdi:calendar"]


class TestAlternateIconStates:
    """Test icon states based on actual binary sensor state."""

    def test_offset_icon_when_off(self, mock_hass):
        """Test offset sensor icon when off."""
        config = {"name": "Test Offset", "entity_id": "binary_sensor.test", "offset": "1 hour"}
        entry = MagicMock()
        sensor = ClockworkOffsetBinarySensor(config, mock_hass, entry)
        sensor._is_on = False
        assert sensor.icon == "mdi:alarm-off"

    def test_offset_icon_when_on(self, mock_hass):
        """Test offset sensor icon when on."""
        config = {"name": "Test Offset", "entity_id": "binary_sensor.test", "offset": "1 hour"}
        entry = MagicMock()
        sensor = ClockworkOffsetBinarySensor(config, mock_hass, entry)
        sensor._is_on = True
        assert sensor.icon == "mdi:alarm"

    def test_between_dates_icon_when_off(self, mock_hass):
        """Test between dates sensor icon when off."""
        config = {"name": "Test", "start_datetime_entity": "input_datetime.start", "end_datetime_entity": "input_datetime.end"}
        entry = MagicMock()
        sensor = ClockworkBetweenDatesSensor(config, mock_hass, entry)
        sensor._is_on = False
        assert sensor.icon == "mdi:calendar-outline"

    def test_between_dates_icon_when_on(self, mock_hass):
        """Test between dates sensor icon when on."""
        config = {"name": "Test", "start_datetime_entity": "input_datetime.start", "end_datetime_entity": "input_datetime.end"}
        entry = MagicMock()
        sensor = ClockworkBetweenDatesSensor(config, mock_hass, entry)
        sensor._is_on = True
        assert sensor.icon == "mdi:calendar-clock"

    def test_outside_dates_icon_when_off(self, mock_hass):
        """Test outside dates sensor icon when off."""
        config = {"name": "Test", "start_datetime_entity": "input_datetime.start", "end_datetime_entity": "input_datetime.end"}
        entry = MagicMock()
        sensor = ClockworkOutsideDatesSensor(config, mock_hass, entry)
        sensor._is_on = False
        assert sensor.icon == "mdi:calendar"

    def test_outside_dates_icon_when_on(self, mock_hass):
        """Test outside dates sensor icon when on."""
        config = {"name": "Test", "start_datetime_entity": "input_datetime.start", "end_datetime_entity": "input_datetime.end"}
        entry = MagicMock()
        sensor = ClockworkOutsideDatesSensor(config, mock_hass, entry)
        sensor._is_on = True
        assert sensor.icon == "mdi:calendar-remove"


class TestBinarySensorUniqueIds:
    """Test unique ID format for binary sensors."""

    def test_offset_unique_id_format(self, mock_hass):
        """Test offset sensor unique ID format."""
        config = {"name": "My Offset Sensor"}
        entry = MagicMock()
        entry.entry_id = "entry_123"
        sensor = ClockworkOffsetBinarySensor(config, mock_hass, entry)
        
        assert sensor.unique_id.startswith("clockwork_entry_123_")
        assert "my_offset_sensor" in sensor.unique_id

    def test_season_unique_id_format(self, mock_hass):
        """Test season sensor unique ID format."""
        config = {"name": "Summer Season"}
        entry = MagicMock()
        entry.entry_id = "test_456"
        sensor = ClockworkSeasonBinarySensor(config, mock_hass, entry)
        
        assert "clockwork_test_456_" in sensor.unique_id
        assert "summer_season" in sensor.unique_id

    def test_month_unique_id_format(self, mock_hass):
        """Test month sensor unique ID format."""
        config = {"name": "Summer Months"}
        entry = MagicMock()
        entry.entry_id = "xyz789"
        sensor = ClockworkMonthBinarySensor(config, mock_hass, entry)
        
        assert "clockwork_xyz789_" in sensor.unique_id
        assert "summer_months" in sensor.unique_id

    def test_between_dates_unique_id_format(self, mock_hass):
        """Test between dates sensor unique ID format."""
        config = {"name": "Work Hours"}
        entry = MagicMock()
        entry.entry_id = "work_001"
        sensor = ClockworkBetweenDatesSensor(config, mock_hass, entry)
        
        assert "clockwork_work_001_" in sensor.unique_id
        assert "work_hours" in sensor.unique_id

    def test_outside_dates_unique_id_format(self, mock_hass):
        """Test outside dates sensor unique ID format."""
        config = {"name": "After Hours"}
        entry = MagicMock()
        entry.entry_id = "after_001"
        sensor = ClockworkOutsideDatesSensor(config, mock_hass, entry)
        
        assert "clockwork_after_001_" in sensor.unique_id
        assert "after_hours" in sensor.unique_id


class TestBinarySensorIsOn:
    """Test is_on property for binary sensors."""

    def test_offset_is_on_false_by_default(self, mock_hass):
        """Test offset sensor is_on defaults to false."""
        config = {"name": "Test", "entity_id": "binary_sensor.test", "offset": "1 hour"}
        entry = MagicMock()
        sensor = ClockworkOffsetBinarySensor(config, mock_hass, entry)
        assert sensor.is_on is False

    def test_offset_is_on_true_when_set(self, mock_hass):
        """Test offset sensor is_on can be set to true."""
        config = {"name": "Test", "entity_id": "binary_sensor.test", "offset": "1 hour"}
        entry = MagicMock()
        sensor = ClockworkOffsetBinarySensor(config, mock_hass, entry)
        sensor._is_on = True
        assert sensor.is_on is True

    def test_season_is_on_false_by_default(self, mock_hass):
        """Test season sensor is_on defaults to false."""
        config = {"name": "Test", "season": "summer", "hemisphere": "northern"}
        entry = MagicMock()
        sensor = ClockworkSeasonBinarySensor(config, mock_hass, entry)
        assert sensor.is_on is False

    def test_month_is_on_false_by_default(self, mock_hass):
        """Test month sensor is_on defaults to false."""
        config = {"name": "Test", "months": "6,7,8"}
        entry = MagicMock()
        sensor = ClockworkMonthBinarySensor(config, mock_hass, entry)
        assert sensor.is_on is False

    def test_between_dates_is_on_false_by_default(self, mock_hass):
        """Test between dates sensor is_on defaults to false."""
        config = {"name": "Test", "start_datetime_entity": "input_datetime.start", "end_datetime_entity": "input_datetime.end"}
        entry = MagicMock()
        sensor = ClockworkBetweenDatesSensor(config, mock_hass, entry)
        assert sensor.is_on is False

    def test_outside_dates_is_on_false_by_default(self, mock_hass):
        """Test outside dates sensor is_on defaults to false."""
        config = {"name": "Test", "start_datetime_entity": "input_datetime.start", "end_datetime_entity": "input_datetime.end"}
        entry = MagicMock()
        sensor = ClockworkOutsideDatesSensor(config, mock_hass, entry)
        assert sensor.is_on is False


class TestBinarySensorExtraAttributes:
    """Test extra_state_attributes for binary sensors."""

    def test_offset_extra_attributes_contains_config(self, mock_hass):
        """Test offset sensor extra attributes contain config."""
        config = {"name": "Test", "entity_id": "binary_sensor.test", "offset": "1 hour", "offset_mode": "latch"}
        entry = MagicMock()
        sensor = ClockworkOffsetBinarySensor(config, mock_hass, entry)
        
        attrs = sensor.extra_state_attributes
        assert attrs == config

    def test_season_extra_attributes_contains_config(self, mock_hass):
        """Test season sensor extra attributes contain config."""
        config = {"name": "Test", "season": "summer", "hemisphere": "northern"}
        entry = MagicMock()
        sensor = ClockworkSeasonBinarySensor(config, mock_hass, entry)
        
        attrs = sensor.extra_state_attributes
        assert attrs == config

    def test_month_extra_attributes_contains_config(self, mock_hass):
        """Test month sensor extra attributes contain config."""
        config = {"name": "Test", "months": "6,7,8"}
        entry = MagicMock()
        sensor = ClockworkMonthBinarySensor(config, mock_hass, entry)
        
        attrs = sensor.extra_state_attributes
        assert attrs == config

    def test_between_dates_extra_attributes_contains_config(self, mock_hass):
        """Test between dates sensor extra attributes contain config."""
        config = {"name": "Test", "start_datetime_entity": "input_datetime.start", "end_datetime_entity": "input_datetime.end"}
        entry = MagicMock()
        sensor = ClockworkBetweenDatesSensor(config, mock_hass, entry)
        
        mock_hass.states.get.return_value = MagicMock()
        attrs = sensor.extra_state_attributes
        assert "name" in attrs
        assert "start_datetime_entity" in attrs

    def test_outside_dates_extra_attributes_contains_config(self, mock_hass):
        """Test outside dates sensor extra attributes contain config."""
        config = {"name": "Test", "start_datetime_entity": "input_datetime.start", "end_datetime_entity": "input_datetime.end"}
        entry = MagicMock()
        sensor = ClockworkOutsideDatesSensor(config, mock_hass, entry)
        
        mock_hass.states.get.return_value = MagicMock()
        attrs = sensor.extra_state_attributes
        assert "name" in attrs


class TestBinarySensorNameProperty:
    """Test name property for binary sensors."""

    def test_offset_name_includes_active(self, mock_hass):
        """Test offset sensor name includes 'Active'."""
        config = {"name": "Kitchen Door"}
        entry = MagicMock()
        sensor = ClockworkOffsetBinarySensor(config, mock_hass, entry)
        assert sensor.name == "Kitchen Door Active"

    def test_season_name_includes_season(self, mock_hass):
        """Test season sensor name includes season."""
        config = {"name": "Climate", "season": "winter", "hemisphere": "northern"}
        entry = MagicMock()
        sensor = ClockworkSeasonBinarySensor(config, mock_hass, entry)
        assert "Climate" in sensor.name
        assert "Winter" in sensor.name

    def test_month_name_preserved(self, mock_hass):
        """Test month sensor name is preserved."""
        config = {"name": "School Year"}
        entry = MagicMock()
        sensor = ClockworkMonthBinarySensor(config, mock_hass, entry)
        assert sensor.name == "School Year"

    def test_between_dates_name_preserved(self, mock_hass):
        """Test between dates sensor name is preserved."""
        config = {"name": "Work Hours"}
        entry = MagicMock()
        sensor = ClockworkBetweenDatesSensor(config, mock_hass, entry)
        assert sensor.name == "Work Hours"

    def test_outside_dates_name_preserved(self, mock_hass):
        """Test outside dates sensor name is preserved."""
        config = {"name": "After Hours"}
        entry = MagicMock()
        sensor = ClockworkOutsideDatesSensor(config, mock_hass, entry)
        assert sensor.name == "After Hours"


class TestSeasonBinarySensorEdgeCases:
    """Test season binary sensor edge cases."""

    def test_season_icon_mapping(self, mock_hass):
        """Test season icons are mapped correctly."""
        seasons_to_icons = {
            "spring": "mdi:flower",
            "summer": "mdi:sun",
            "autumn": "mdi:leaf",
            "fall": "mdi:leaf",
            "winter": "mdi:snowflake",
        }
        
        entry = MagicMock()
        for season, expected_icon in seasons_to_icons.items():
            config = {"name": "Test", "season": season, "hemisphere": "northern"}
            sensor = ClockworkSeasonBinarySensor(config, mock_hass, entry)
            assert sensor.icon == expected_icon

    def test_season_unknown_icon_default(self, mock_hass):
        """Test unknown season defaults to calendar icon."""
        config = {"name": "Test", "season": "unknown", "hemisphere": "northern"}
        entry = MagicMock()
        sensor = ClockworkSeasonBinarySensor(config, mock_hass, entry)
        assert sensor.icon == "mdi:calendar-today"

    def test_month_sensor_months_parsing(self, mock_hass):
        """Test month sensor parses months correctly."""
        config = {"name": "Test", "months": "1,3,5,7,9,11"}
        entry = MagicMock()
        sensor = ClockworkMonthBinarySensor(config, mock_hass, entry)
        assert sensor._months == [1, 3, 5, 7, 9, 11]

    def test_month_sensor_empty_months(self, mock_hass):
        """Test month sensor with empty months."""
        config = {"name": "Test", "months": ""}
        entry = MagicMock()
        sensor = ClockworkMonthBinarySensor(config, mock_hass, entry)
        assert sensor._months == []

    def test_month_sensor_invalid_months_ignored(self, mock_hass):
        """Test month sensor ignores invalid month values."""
        config = {"name": "Test", "months": "1,invalid,5,abc,12"}
        entry = MagicMock()
        sensor = ClockworkMonthBinarySensor(config, mock_hass, entry)
        assert sensor._months == [1, 5, 12]