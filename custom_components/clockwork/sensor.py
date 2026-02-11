"""Sensor platform for Clockwork integration."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_CALCULATIONS, CALC_TYPE_TIMESPAN, CALC_TYPE_HOLIDAY, CALC_TYPE_DATETIME_OFFSET, CALC_TYPE_DATE_RANGE
from .utils import get_days_to_holiday, get_holidays, apply_offset_to_datetime, do_ranges_overlap

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Clockwork sensors."""
    # Get calculations from options first (user changes), fall back to data
    calculations = config_entry.options.get(CONF_CALCULATIONS, config_entry.data.get(CONF_CALCULATIONS, []))
    # Get custom holidays from config entry options
    custom_holidays = config_entry.options.get("custom_holidays", [])
    entities = []

    for calc in calculations:
        calc_type = calc.get("type")
        if calc_type == CALC_TYPE_TIMESPAN:
            entities.append(ClockworkTimespanSensor(calc, hass, config_entry))
        elif calc_type == CALC_TYPE_DATETIME_OFFSET:
            entities.append(ClockworkDatetimeOffsetSensor(calc, hass, config_entry))
        elif calc_type == CALC_TYPE_DATE_RANGE:
            entities.append(ClockworkDateRangeSensor(calc, hass, config_entry))
        elif calc_type == CALC_TYPE_HOLIDAY:
            entities.append(ClockworkHolidaySensor(calc, hass, custom_holidays, config_entry))

    async_add_entities(entities)


class ClockworkTimespanSensor(SensorEntity):
    """Sensor for timespan calculations."""

    def __init__(self, config: Dict[str, Any], hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self._config = config
        self.hass = hass
        self._config_entry = config_entry
        self._state = None
        self._last_change = None
        self._entity_id = config.get("entity_id")
        self._name = config.get("name", f"Timespan {self._entity_id}")
        self._update_interval = config.get("update_interval", 60)  # Default 60 seconds
        self._track_state = config.get("track_state", "on")  # Default "on" for backward compatibility
        self._remove_listener = None
        self._remove_timer = None

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{DOMAIN}_{self._config_entry.entry_id}_{self._name.replace(' ', '_').lower()}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name="Clockwork",
            manufacturer="Clockwork",
            model="Date/Time Calculator"
        )

    @property
    def state(self) -> Optional[str]:
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "seconds"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return self._config

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        @callback
        def state_change_listener(event):
            """Handle state changes."""
            new_state = event.data.get("new_state")
            if new_state:
                # Check if we should track this state change
                state_matches = False
                if self._track_state == "both":
                    # Track any state change
                    state_matches = True
                elif new_state.state == self._track_state:
                    # Track specific state
                    state_matches = True
                
                if state_matches:
                    # Store the time the entity changed to the tracked state
                    self._last_change = new_state.last_changed or dt_util.utcnow()
                else:
                    self._last_change = None
            self._update_state()

        self._remove_listener = async_track_state_change_event(
            self.hass, [self._entity_id], state_change_listener
        )

        # Initial state - get the last_changed time from the state object
        state = self.hass.states.get(self._entity_id)
        if state:
            # Check if current state matches tracked state
            state_matches = False
            if self._track_state == "both":
                # Track any state change
                state_matches = True
            elif state.state == self._track_state:
                # Track specific state
                state_matches = True
            
            if state_matches:
                # Use the last_changed timestamp from the state
                self._last_change = state.last_changed or dt_util.utcnow()
            else:
                self._last_change = None
        self._update_state()

        # Add periodic update timer to continuously update the timespan
        @callback
        def timer_callback(now=None):
            """Update state at configured interval."""
            self._update_state()

        self._remove_timer = async_track_time_interval(
            self.hass, timer_callback, timedelta(seconds=self._update_interval)
        )

    @callback
    def _update_state(self) -> None:
        """Update the sensor state."""
        if self._last_change:
            delta = dt_util.utcnow() - self._last_change
            self._state = int(delta.total_seconds())
        else:
            self._state = 0
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners."""
        if self._remove_listener:
            self._remove_listener()
        if self._remove_timer:
            self._remove_timer()


class ClockworkDateRangeSensor(SensorEntity):
    """Sensor for date range duration."""

    def __init__(self, config: Dict[str, Any], hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self._config = config
        self.hass = hass
        self._config_entry = config_entry
        self._state = None
        self._start_datetime_entity = config.get("start_datetime_entity")
        self._end_datetime_entity = config.get("end_datetime_entity")
        self._remove_listener = None

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._config.get("name", "Date Range Duration")

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{DOMAIN}_{self._config_entry.entry_id}_{self._config.get('name', 'Date Range Duration').replace(' ', '_').lower()}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name="Clockwork",
            manufacturer="Clockwork",
            model="Date/Time Calculator"
        )

    @property
    def state(self) -> Optional[int]:
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "hours"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return self._config

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        @callback
        def datetime_change_listener(event):
            """Handle datetime entity state changes."""
            self._update_state()

        self._remove_listener = async_track_state_change_event(
            self.hass, [self._start_datetime_entity, self._end_datetime_entity], datetime_change_listener
        )

        # Initial state
        self._update_state()

    @callback
    def _update_state(self) -> None:
        """Update the sensor state."""
        try:
            start_state = self.hass.states.get(self._start_datetime_entity)
            end_state = self.hass.states.get(self._end_datetime_entity)

            if start_state and end_state:
                start_datetime = dt_util.parse_datetime(start_state.state)
                end_datetime = dt_util.parse_datetime(end_state.state)
                
                if start_datetime and end_datetime:
                    current_tz = dt_util.now().tzinfo
                    
                    # Ensure all datetimes are in the same timezone (make naive datetimes aware)
                    if start_datetime.tzinfo is None:
                        start_datetime = start_datetime.replace(tzinfo=current_tz)
                    if end_datetime.tzinfo is None:
                        end_datetime = end_datetime.replace(tzinfo=current_tz)
                    
                    delta = end_datetime - start_datetime
                    # Return duration in hours
                    self._state = int(delta.total_seconds() / 3600)
                else:
                    self._state = None
            else:
                self._state = None
        except (ValueError, TypeError):
            self._state = None
        
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners."""
        if self._remove_listener:
            self._remove_listener()


class ClockworkHolidaySensor(SensorEntity):
    """Sensor for holiday calculations."""

    def __init__(self, config: Dict[str, Any], hass: HomeAssistant, custom_holidays: Optional[list] = None, config_entry: Optional[ConfigEntry] = None) -> None:
        """Initialize the sensor."""
        self._config = config
        self.hass = hass
        self._config_entry = config_entry
        self._holiday_key = config.get("holiday", "christmas")
        self._offset_days = int(config.get("offset", 0))
        self._custom_holidays = custom_holidays or []
        self._state = None
        self._remove_timer = None

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._config.get("name", f"Days to {self._holiday_key.replace('_', ' ').title()}")

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        if self._config_entry:
            return f"{DOMAIN}_{self._config_entry.entry_id}_{self._config.get('name', 'unknown').replace(' ', '_').lower()}"
        return f"{DOMAIN}_{self._holiday_key}_{self._offset_days}"

    @property
    def device_info(self) -> Optional[DeviceInfo]:
        """Return device info."""
        if self._config_entry:
            return DeviceInfo(
                identifiers={(DOMAIN, self._config_entry.entry_id)},
                name="Clockwork",
                manufacturer="Clockwork",
                model="Date/Time Calculator"
            )
        return None

    @property
    def state(self) -> Optional[int]:
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "days"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return self._config

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # Initial state
        self._update_state()

        @callback
        def check_holiday(now):
            """Check days to holiday."""
            self._update_state()

        # Check daily
        self._remove_timer = async_track_time_interval(self.hass, check_holiday, timedelta(days=1))

    @callback
    def _update_state(self) -> None:
        """Update the sensor state."""
        now = dt_util.now().date()
        days_to_holiday = get_days_to_holiday(self.hass, now, self._holiday_key, self._custom_holidays)
        
        if days_to_holiday >= 0:
            self._state = days_to_holiday + self._offset_days
        else:
            self._state = None
        
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners."""
        if self._remove_timer:
            self._remove_timer()


class ClockworkDatetimeOffsetSensor(SensorEntity):
    """Sensor for adding offset to datetime entities."""

    def __init__(self, config: Dict[str, Any], hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self._config = config
        self.hass = hass
        self._config_entry = config_entry
        self._state = None
        self._datetime_entity = config.get("datetime_entity")
        self._offset_str = config.get("offset", "0")
        self._remove_listener = None

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._config.get("name", f"Datetime Offset {self._datetime_entity}")

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{DOMAIN}_{self._config_entry.entry_id}_{self._config.get('name', 'Datetime Offset').replace(' ', '_').lower()}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name="Clockwork",
            manufacturer="Clockwork",
            model="Date/Time Calculator"
        )

    @property
    def state(self) -> Optional[str]:
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return self._config

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        @callback
        def datetime_change_listener(event):
            """Handle datetime entity state changes."""
            self._update_state()

        self._remove_listener = async_track_state_change_event(
            self.hass, [self._datetime_entity], datetime_change_listener
        )

        # Initial state
        self._update_state()

    @callback
    def _update_state(self) -> None:
        """Update the sensor state."""
        try:
            state = self.hass.states.get(self._datetime_entity)
            if state:
                base_datetime = dt_util.parse_datetime(state.state)
                if base_datetime:
                    result_datetime = apply_offset_to_datetime(base_datetime, self._offset_str)
                    self._state = result_datetime.isoformat()
                else:
                    self._state = None
            else:
                self._state = None
        except (ValueError, TypeError):
            self._state = None

        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners."""
        if self._remove_listener:
            self._remove_listener()