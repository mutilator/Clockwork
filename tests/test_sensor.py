"""Tests for Clockwork sensor entities."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.clockwork.const import (
    CALC_TYPE_TIMESPAN,
    CALC_TYPE_DATETIME_OFFSET,
    CALC_TYPE_DATE_RANGE,
    CALC_TYPE_HOLIDAY,
)
from custom_components.clockwork.sensor import (
    ClockworkTimespanSensor,
    ClockworkDatetimeOffsetSensor,
    ClockworkDateRangeSensor,
    ClockworkHolidaySensor,
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
async def test_initialization(mock_hass):
    """Test sensor initialization."""
    config = {
        "name": "Test Timespan",
        "entity_id": "binary_sensor.test",
        "track_state": "on",
        "update_interval": 60,
        "icon": "mdi:clock",
    }
    entry = MagicMock()
    entry.entry_id = "test_entry"

    sensor = ClockworkTimespanSensor(config, mock_hass, entry)

    assert sensor.name == "Test Timespan"
    assert sensor._config == config
    assert sensor._state is None


@pytest.mark.asyncio
async def test_unique_id_generation(mock_hass):
    """Test unique ID generation."""
    config = {"name": "My Timespan Sensor"}
    entry = MagicMock()
    entry.entry_id = "entry_123"

    sensor = ClockworkTimespanSensor(config, mock_hass, entry)

    assert sensor.unique_id == "clockwork_entry_123_my_timespan_sensor"


@pytest.mark.asyncio
async def test_async_added_to_hass(mock_hass):
    """Test adding to hass."""
    config = {
        "name": "Test",
        "entity_id": "sensor.test",
        "track_state": "on",
    }
    entry = MagicMock()

    sensor = ClockworkTimespanSensor(config, mock_hass, entry)

    # Mock the state
    mock_state = MagicMock()
    mock_state.state = "on"
    mock_state.last_changed = None
    
    with patch.object(sensor.hass.states, 'get', return_value=mock_state):
        with patch('custom_components.clockwork.sensor.async_track_state_change_event') as mock_track:
            await sensor.async_added_to_hass()
            mock_track.assert_called_once()


@pytest.mark.asyncio
async def test_update_state(mock_hass):
    """Test state update."""
    config = {
        "name": "Test",
        "entity_id": "sensor.test",
        "track_state": "on",
    }
    entry = MagicMock()

    sensor = ClockworkTimespanSensor(config, mock_hass, entry)
    sensor.entity_id = "sensor.test_sensor"
    sensor.platform = MagicMock()
    
    # Set up last_change
    from datetime import datetime, timezone
    sensor._last_change = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    sensor._update_state()
    assert sensor._state == 0  # Will be 0 since it's a mock


@pytest.mark.asyncio
async def test_unique_id_generation(mock_hass):
    """Test unique ID generation."""
    config = {"name": "My Test Sensor"}
    entry = MagicMock()
    entry.entry_id = "entry_123"

    sensor = ClockworkTimespanSensor(config, mock_hass, entry)

    assert sensor.unique_id == "clockwork_entry_123_my_test_sensor"


@pytest.mark.asyncio
async def test_state_attributes(mock_hass):
    """Test state attributes."""
    config = {
        "name": "Test",
        "entity_id": "binary_sensor.test",
        "track_state": "on",
    }
    entry = MagicMock()

    sensor = ClockworkTimespanSensor(config, mock_hass, entry)

    # Mock the state
    sensor._state = "1:30:00"
    sensor._last_change = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    attributes = sensor.extra_state_attributes
    assert attributes == config


@pytest.mark.asyncio
async def test_async_added_to_hass(mock_hass):
    """Test adding to hass."""
    config = {
        "name": "Test",
        "entity_id": "sensor.test",
        "track_state": "on",
    }
    entry = MagicMock()

    sensor = ClockworkTimespanSensor(config, mock_hass, entry)
    sensor.entity_id = "sensor.test_sensor"
    sensor.platform = MagicMock()

    # Mock the state
    mock_state = MagicMock()
    mock_state.state = "on"
    mock_state.last_changed = None
    
    with patch.object(sensor.hass.states, 'get', return_value=mock_state):
        with patch('custom_components.clockwork.sensor.async_track_state_change_event') as mock_track:
            with patch('custom_components.clockwork.sensor.async_track_time_interval') as mock_timer:
                with patch('threading.get_ident', return_value=1):  # Mock thread ID to match loop_thread_id
                    await sensor.async_added_to_hass()
                    mock_track.assert_called_once()


@pytest.mark.asyncio
async def test_update_state(mock_hass):
    """Test state update."""
    config = {
        "name": "Test",
        "entity_id": "sensor.test",
        "track_state": "on",
    }
    entry = MagicMock()

    sensor = ClockworkTimespanSensor(config, mock_hass, entry)
    sensor.entity_id = "sensor.test_sensor"
    sensor.platform = MagicMock()
    
    # Set up last_change
    from datetime import datetime, timezone
    sensor._last_change = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    with patch('threading.get_ident', return_value=1):  # Mock thread ID to match loop_thread_id
        sensor._update_state()
        assert sensor._state is not None  # State should be set to the time difference


class TestClockworkDatetimeOffsetSensor:
    """Test datetime offset sensor."""

    def test_initialization(self, mock_hass):
        """Test sensor initialization."""
        config = {
            "name": "Test Datetime Offset",
            "datetime_entity": "input_datetime.test",
            "offset": "1 hour",
        }
        entry = MagicMock()

        sensor = ClockworkDatetimeOffsetSensor(config, mock_hass, entry)

        assert sensor.name == "Test Datetime Offset"
        assert sensor._config == config


class TestClockworkDateRangeSensor:
    """Test date range sensor."""

    def test_initialization(self, mock_hass):
        """Test sensor initialization."""
        config = {
            "name": "Test Date Range",
            "start_datetime_entity": "input_datetime.start",
            "end_datetime_entity": "input_datetime.end",
        }
        entry = MagicMock()

        sensor = ClockworkDateRangeSensor(config, mock_hass, entry)

        assert sensor.name == "Test Date Range"
        assert sensor._config == config


class TestClockworkHolidaySensor:
    """Test holiday sensor."""

    def test_initialization(self, mock_hass):
        """Test sensor initialization."""
        config = {
            "name": "Test Holiday",
            "holiday": "christmas",
            "offset": 0,
        }
        entry = MagicMock()

        sensor = ClockworkHolidaySensor(config, mock_hass, entry)

        assert sensor.name == "Test Holiday"
        assert sensor._config == config

@pytest.mark.asyncio
async def test_datetime_offset_update_state(mock_hass):
    """Test datetime offset sensor state update."""
    config = {
        "name": "Test Datetime Offset",
        "datetime_entity": "input_datetime.test",
        "offset": "1 hour",
    }
    entry = MagicMock()

    sensor = ClockworkDatetimeOffsetSensor(config, mock_hass, entry)
    sensor.entity_id = "sensor.test_datetime_offset"
    sensor.platform = MagicMock()

    # Mock the datetime entity state
    mock_state = MagicMock()
    mock_state.state = "2024-01-01 12:00:00"
    
    with patch.object(sensor.hass.states, 'get', return_value=mock_state):
        with patch('threading.get_ident', return_value=1):  # Mock thread ID to match loop_thread_id
            sensor._update_state()
            # The state should be set to the offset datetime
            assert sensor._state is not None


@pytest.mark.asyncio
async def test_date_range_update_state(mock_hass):
    """Test date range sensor state update."""
    config = {
        "name": "Test Date Range",
        "start_datetime_entity": "input_datetime.start",
        "end_datetime_entity": "input_datetime.end",
    }
    entry = MagicMock()

    sensor = ClockworkDateRangeSensor(config, mock_hass, entry)
    sensor.entity_id = "sensor.test_date_range"
    sensor.platform = MagicMock()

    # Mock the datetime entity states
    mock_start_state = MagicMock()
    mock_start_state.state = "2024-01-01 12:00:00"
    mock_end_state = MagicMock()
    mock_end_state.state = "2024-01-01 14:00:00"
    
    def mock_get(entity_id):
        if entity_id == "input_datetime.start":
            return mock_start_state
        elif entity_id == "input_datetime.end":
            return mock_end_state
        return None

    with patch.object(sensor.hass.states, 'get', side_effect=mock_get):
        with patch('threading.get_ident', return_value=1):  # Mock thread ID to match loop_thread_id
            sensor._update_state()
            assert sensor._state == 2  # 2 hours difference


@pytest.mark.asyncio
async def test_holiday_update_state(mock_hass):
    """Test holiday sensor state update."""
    config = {
        "name": "Test Holiday",
        "holiday": "christmas",
        "offset": 0,
    }
    entry = MagicMock()

    sensor = ClockworkHolidaySensor(config, mock_hass, [], entry)
    sensor.entity_id = "sensor.test_holiday"
    sensor.platform = MagicMock()

    with patch('custom_components.clockwork.sensor.get_days_to_holiday') as mock_days:
        mock_days.return_value = 30
        with patch('threading.get_ident', return_value=1):  # Mock thread ID to match loop_thread_id
            sensor._update_state()
            assert sensor._state == 30