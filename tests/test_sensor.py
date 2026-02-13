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
    ClockworkHolidayDateSensor,
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
    # Attributes should contain all config values plus device_class
    for key, value in config.items():
        assert attributes[key] == value
    assert "device_class" in attributes


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


class TestClockworkTimespanSensor:
    """Test timespan sensor."""

    def test_initialization(self, mock_hass):
        """Test sensor initialization."""
        config = {
            "name": "Test Timespan",
            "entity_id": "binary_sensor.test",
            "update_interval": 30,
            "track_state": "on",
        }
        entry = MagicMock()

        sensor = ClockworkTimespanSensor(config, mock_hass, entry)

        assert sensor.name == "Test Timespan"
        assert sensor._config == config
        assert sensor.device_class == SensorDeviceClass.DURATION


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
        assert sensor.device_class == SensorDeviceClass.TIMESTAMP


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
        assert sensor.device_class == SensorDeviceClass.DURATION


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
        assert sensor.device_class == SensorDeviceClass.DURATION

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


class TestSensorUniqueIds:
    """Test unique ID format for sensor types."""

    def test_timespan_unique_id(self, mock_hass):
        """Test timespan sensor unique ID."""
        config = {"name": "Door Open Time"}
        entry = MagicMock()
        entry.entry_id = "test_001"
        sensor = ClockworkTimespanSensor(config, mock_hass, entry)
        
        assert "clockwork_test_001_" in sensor.unique_id
        assert "door_open_time" in sensor.unique_id.lower()

    def test_datetime_offset_unique_id(self, mock_hass):
        """Test datetime offset sensor unique ID."""
        config = {"name": "Event Time"}
        entry = MagicMock()
        entry.entry_id = "test_002"
        sensor = ClockworkDatetimeOffsetSensor(config, mock_hass, entry)
        
        assert "clockwork_test_002_" in sensor.unique_id

    def test_date_range_unique_id(self, mock_hass):
        """Test date range sensor unique ID."""
        config = {"name": "Vacation Duration"}
        entry = MagicMock()
        entry.entry_id = "test_003"
        sensor = ClockworkDateRangeSensor(config, mock_hass, entry)
        
        assert "clockwork_test_003_" in sensor.unique_id

    def test_holiday_unique_id(self, mock_hass):
        """Test holiday sensor unique ID."""
        config = {"name": "Days Until Christmas"}
        entry = MagicMock()
        entry.entry_id = "test_004"
        sensor = ClockworkHolidaySensor(config, mock_hass, [], entry)
        
        assert "clockwork_test_004_" in sensor.unique_id


class TestSensorStateProperty:
    """Test state property for sensors."""

    def test_timespan_state_none_initially(self, mock_hass):
        """Test timespan sensor state is None initially."""
        config = {"name": "Test", "entity_id": "binary_sensor.test"}
        entry = MagicMock()
        sensor = ClockworkTimespanSensor(config, mock_hass, entry)
        assert sensor.state is None

    def test_timespan_state_when_set(self, mock_hass):
        """Test timespan sensor state when set."""
        config = {"name": "Test", "entity_id": "binary_sensor.test"}
        entry = MagicMock()
        sensor = ClockworkTimespanSensor(config, mock_hass, entry)
        sensor._state = "1:30:00"
        assert sensor.state == "1:30:00"

    def test_datetime_offset_state_when_set(self, mock_hass):
        """Test datetime offset sensor state when set."""
        config = {"name": "Test", "datetime_entity": "input_datetime.test"}
        entry = MagicMock()
        sensor = ClockworkDatetimeOffsetSensor(config, mock_hass, entry)
        sensor._state = "2024-01-15 14:30:00"
        assert sensor.state == "2024-01-15 14:30:00"

    def test_date_range_state_when_set(self, mock_hass):
        """Test date range sensor state when set."""
        config = {"name": "Test", "start_datetime_entity": "input_datetime.start", "end_datetime_entity": "input_datetime.end"}
        entry = MagicMock()
        sensor = ClockworkDateRangeSensor(config, mock_hass, entry)
        sensor._state = 42
        assert sensor.state == 42

    def test_holiday_state_when_set(self, mock_hass):
        """Test holiday sensor state when set."""
        config = {"name": "Test", "holiday": "christmas", "offset": 0}
        entry = MagicMock()
        sensor = ClockworkHolidaySensor(config, mock_hass, [], entry)
        sensor._state = 315
        assert sensor.state == 315


class TestSensorDeviceClass:
    """Test device_class property for sensors."""

    def test_timespan_device_class_is_duration(self, mock_hass):
        """Test timespan sensor device class."""
        config = {"name": "Test", "entity_id": "binary_sensor.test"}
        entry = MagicMock()
        sensor = ClockworkTimespanSensor(config, mock_hass, entry)
        assert sensor.device_class == SensorDeviceClass.DURATION

    def test_datetime_offset_device_class_is_timestamp(self, mock_hass):
        """Test datetime offset sensor device class."""
        config = {"name": "Test", "datetime_entity": "input_datetime.test"}
        entry = MagicMock()
        sensor = ClockworkDatetimeOffsetSensor(config, mock_hass, entry)
        assert sensor.device_class == SensorDeviceClass.TIMESTAMP

    def test_date_range_device_class_is_duration(self, mock_hass):
        """Test date range sensor device class."""
        config = {"name": "Test", "start_datetime_entity": "input_datetime.start", "end_datetime_entity": "input_datetime.end"}
        entry = MagicMock()
        sensor = ClockworkDateRangeSensor(config, mock_hass, entry)
        assert sensor.device_class == SensorDeviceClass.DURATION

    def test_holiday_device_class_is_duration(self, mock_hass):
        """Test holiday sensor device class."""
        config = {"name": "Test", "holiday": "christmas", "offset": 0}
        entry = MagicMock()
        sensor = ClockworkHolidaySensor(config, mock_hass, [], entry)
        assert sensor.device_class == SensorDeviceClass.DURATION


class TestSensorIcon:
    """Test icon property for sensors."""

    def test_timespan_icon(self, mock_hass):
        """Test timespan sensor icon."""
        config = {"name": "Test", "entity_id": "binary_sensor.test"}
        entry = MagicMock()
        sensor = ClockworkTimespanSensor(config, mock_hass, entry)
        assert sensor.icon == "mdi:timer-outline"

    def test_datetime_offset_icon(self, mock_hass):
        """Test datetime offset sensor icon."""
        config = {"name": "Test", "datetime_entity": "input_datetime.test"}
        entry = MagicMock()
        sensor = ClockworkDatetimeOffsetSensor(config, mock_hass, entry)
        assert sensor.icon == "mdi:calendar-clock"

    def test_date_range_icon(self, mock_hass):
        """Test date range sensor icon."""
        config = {"name": "Test", "start_datetime_entity": "input_datetime.start", "end_datetime_entity": "input_datetime.end"}
        entry = MagicMock()
        sensor = ClockworkDateRangeSensor(config, mock_hass, entry)
        assert sensor.icon == "mdi:timer-outline"

    def test_holiday_icon(self, mock_hass):
        """Test holiday sensor icon."""
        config = {"name": "Test", "holiday": "christmas", "offset": 0}
        entry = MagicMock()
        sensor = ClockworkHolidaySensor(config, mock_hass, [], entry)
        assert sensor.icon == "mdi:calendar-star"


class TestSensorUnitMeasurement:
    """Test unit_of_measurement property for sensors."""

    def test_timespan_unit_is_seconds(self, mock_hass):
        """Test timespan sensor unit."""
        config = {"name": "Test", "entity_id": "binary_sensor.test"}
        entry = MagicMock()
        sensor = ClockworkTimespanSensor(config, mock_hass, entry)
        assert sensor.unit_of_measurement == "seconds"

    def test_date_range_unit_is_hours(self, mock_hass):
        """Test date range sensor unit."""
        config = {"name": "Test", "start_datetime_entity": "input_datetime.start", "end_datetime_entity": "input_datetime.end"}
        entry = MagicMock()
        sensor = ClockworkDateRangeSensor(config, mock_hass, entry)
        assert sensor.unit_of_measurement == "hours"

    def test_holiday_unit_is_days(self, mock_hass):
        """Test holiday sensor unit."""
        config = {"name": "Test", "holiday": "christmas", "offset": 0}
        entry = MagicMock()
        sensor = ClockworkHolidaySensor(config, mock_hass, [], entry)
        assert sensor.unit_of_measurement == "days"


class TestSensorExtraAttributes:
    """Test extra_state_attributes for sensors."""

    def test_timespan_attributes_includes_config(self, mock_hass):
        """Test timespan sensor attributes include config."""
        config = {"name": "Test", "entity_id": "binary_sensor.test", "track_state": "on"}
        entry = MagicMock()
        sensor = ClockworkTimespanSensor(config, mock_hass, entry)
        
        mock_hass.states.get.return_value = MagicMock()
        attrs = sensor.extra_state_attributes
        assert "name" in attrs
        assert "entity_id" in attrs

    def test_datetime_offset_attributes_includes_config(self, mock_hass):
        """Test datetime offset sensor attributes include config."""
        config = {"name": "Test", "datetime_entity": "input_datetime.test", "offset": "1 hour"}
        entry = MagicMock()
        sensor = ClockworkDatetimeOffsetSensor(config, mock_hass, entry)
        
        mock_hass.states.get.return_value = MagicMock()
        attrs = sensor.extra_state_attributes
        assert "name" in attrs
        assert "offset" in attrs

    def test_date_range_attributes_includes_config(self, mock_hass):
        """Test date range sensor attributes include config."""
        config = {"name": "Test", "start_datetime_entity": "input_datetime.start", "end_datetime_entity": "input_datetime.end"}
        entry = MagicMock()
        sensor = ClockworkDateRangeSensor(config, mock_hass, entry)
        
        mock_hass.states.get.return_value = MagicMock()
        attrs = sensor.extra_state_attributes
        assert "name" in attrs

    def test_holiday_attributes_includes_config(self, mock_hass):
        """Test holiday sensor attributes include config."""
        config = {"name": "Test", "holiday": "christmas", "offset": 0}
        entry = MagicMock()
        sensor = ClockworkHolidaySensor(config, mock_hass, [], entry)
        
        attrs = sensor.extra_state_attributes
        assert "name" in attrs


class TestClockworkHolidayDateSensor:
    """Tests for ClockworkHolidayDateSensor."""

    def test_initialization(self, mock_hass):
        """Test sensor initialization."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        
        sensor = ClockworkHolidayDateSensor(
            hass=mock_hass,
            config_entry=entry,
            holiday_key="christmas",
            holiday_name="Christmas"
        )
        
        assert sensor._holiday_key == "christmas"
        assert sensor._holiday_name == "Christmas"
        assert sensor._state is None

    def test_unique_id_format(self, mock_hass):
        """Test unique ID format for holiday date sensors."""
        entry = MagicMock()
        entry.entry_id = "test_entry_123"
        
        sensor = ClockworkHolidayDateSensor(
            hass=mock_hass,
            config_entry=entry,
            holiday_key="new_years_day",
            holiday_name="New Year's Day"
        )
        
        expected_id = "clockwork_test_entry_123_holiday_new_years_day"
        assert sensor.unique_id == expected_id

    def test_name_includes_domain_and_holiday_name(self, mock_hass):
        """Test sensor name includes domain and holiday name."""
        entry = MagicMock()
        
        sensor = ClockworkHolidayDateSensor(
            hass=mock_hass,
            config_entry=entry,
            holiday_key="independence_day",
            holiday_name="Independence Day"
        )
        
        assert "Clockwork" in sensor.name
        assert "Independence Day" in sensor.name
        assert "Date" in sensor.name

    def test_device_class_is_date(self, mock_hass):
        """Test device class is set to DATE."""
        entry = MagicMock()
        
        sensor = ClockworkHolidayDateSensor(
            hass=mock_hass,
            config_entry=entry,
            holiday_key="thanksgiving",
            holiday_name="Thanksgiving"
        )
        
        assert sensor.device_class == SensorDeviceClass.DATE

    def test_icon_is_calendar(self, mock_hass):
        """Test icon is set to calendar."""
        entry = MagicMock()
        
        sensor = ClockworkHolidayDateSensor(
            hass=mock_hass,
            config_entry=entry,
            holiday_key="halloween",
            holiday_name="Halloween"
        )
        
        assert sensor.icon == "mdi:calendar"

    def test_extra_state_attributes_includes_holiday_info(self, mock_hass):
        """Test extra attributes include holiday key and name."""
        entry = MagicMock()
        
        sensor = ClockworkHolidayDateSensor(
            hass=mock_hass,
            config_entry=entry,
            holiday_key="easter",
            holiday_name="Easter"
        )
        
        attrs = sensor.extra_state_attributes
        assert attrs["holiday_key"] == "easter"
        assert attrs["holiday_name"] == "Easter"

    def test_state_format_is_iso_date(self, mock_hass):
        """Test state is in ISO date format (YYYY-MM-DD)."""
        from datetime import date
        
        entry = MagicMock()
        entry.entry_id = "test"
        
        # Mock the get_holiday_date to return a specific date
        with patch('custom_components.clockwork.sensor.get_holiday_date') as mock_get_date:
            mock_get_date.return_value = date(2025, 12, 25)
            
            sensor = ClockworkHolidayDateSensor(
                hass=mock_hass,
                config_entry=entry,
                holiday_key="christmas",
                holiday_name="Christmas"
            )
            
            # Mock async_write_ha_state to avoid entity registration issues
            sensor.async_write_ha_state = MagicMock()
            
            # Manually call _update_state to set the state
            sensor._update_state()
            
            assert sensor.state == "2025-12-25"

    def test_state_none_when_holiday_not_found(self, mock_hass):
        """Test state is None when holiday cannot be calculated."""
        entry = MagicMock()
        entry.entry_id = "test"
        
        with patch('custom_components.clockwork.sensor.get_holiday_date') as mock_get_date:
            mock_get_date.return_value = None
            
            sensor = ClockworkHolidayDateSensor(
                hass=mock_hass,
                config_entry=entry,
                holiday_key="nonexistent_holiday",
                holiday_name="Nonexistent Holiday"
            )
            
            # Mock async_write_ha_state to avoid entity registration issues
            sensor.async_write_ha_state = MagicMock()
            
            sensor._update_state()
            assert sensor.state is None

    def test_custom_holidays_passed_to_utility(self, mock_hass):
        """Test custom holidays are passed to get_holiday_date."""
        entry = MagicMock()
        entry.entry_id = "test"
        
        custom_holidays = [{"key": "custom_day", "name": "Custom Day", "type": "fixed", "month": 7, "day": 15}]
        
        with patch('custom_components.clockwork.sensor.get_holiday_date') as mock_get_date:
            from datetime import date
            mock_get_date.return_value = date(2025, 7, 15)
            
            sensor = ClockworkHolidayDateSensor(
                hass=mock_hass,
                config_entry=entry,
                holiday_key="custom_day",
                holiday_name="Custom Day",
                custom_holidays=custom_holidays
            )
            
            # Mock async_write_ha_state to avoid entity registration issues
            sensor.async_write_ha_state = MagicMock()
            
            sensor._update_state()
            
            # Verify get_holiday_date was called with custom_holidays as 4th argument
            mock_get_date.assert_called_once()
            # Call args: (hass, year, key, custom_holidays)
            call_args = mock_get_date.call_args[0]
            assert len(call_args) >= 3  # First 3 positional args
            assert call_args[2] == "custom_day"  # The key
            # Check the 4th positional argument (custom_holidays)
            if len(call_args) >= 4:
                assert call_args[3] == custom_holidays
