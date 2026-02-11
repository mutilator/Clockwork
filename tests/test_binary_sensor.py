"""Tests for Clockwork binary sensor entities."""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

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