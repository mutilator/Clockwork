"""Sensor platform for Clockwork integration."""
import logging
from datetime import datetime, timedelta, date
from typing import Any, Dict, Optional, List

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_CALCULATIONS, CONF_AUTO_CREATE_HOLIDAYS, CALC_TYPE_TIMESPAN, CALC_TYPE_HOLIDAY, CALC_TYPE_DATETIME_OFFSET, CALC_TYPE_DATE_RANGE
from .utils import get_days_to_holiday, get_holidays, apply_offset_to_datetime, do_ranges_overlap, parse_datetime_or_date, get_holiday_date

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
    # Get auto-create holidays setting (defaults to True for backward compatibility)
    auto_create_holidays = config_entry.options.get(CONF_AUTO_CREATE_HOLIDAYS, True)
    
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

    # Create date sensors for holidays based on configuration
    if auto_create_holidays:
        # Create date sensors for all holidays (preloaded + custom)
        all_holidays = get_holidays(hass, custom_holidays).get("holidays", [])
    else:
        # Only create date sensors for custom holidays
        all_holidays = custom_holidays
    
    for holiday in all_holidays:
        holiday_key = holiday.get("key")
        holiday_name = holiday.get("name", holiday_key)
        if holiday_key:
            entities.append(ClockworkHolidayDateSensor(
                hass=hass,
                config_entry=config_entry,
                holiday_key=holiday_key,
                holiday_name=holiday_name,
                custom_holidays=custom_holidays
            ))

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
    def device_class(self) -> str:
        """Return the device class."""
        return SensorDeviceClass.DURATION

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:timer-outline"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attrs = dict(self._config)
        attrs["device_class"] = self.device_class
        # Add error info if source entity is missing
        if not self.hass.states.get(self._entity_id):
            attrs["_error"] = f"Source entity '{self._entity_id}' not found. It may have been deleted or renamed."
        return attrs

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        @callback
        def state_change_listener(event):
            """Handle state changes."""
            new_state = event.data.get("new_state")
            if new_state:
                # Check if we should track this state change
                state_matches = False
                if self._track_state == "any":
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
            if self._track_state == "any":
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
            try:
                delta = dt_util.utcnow() - self._last_change
                self._state = int(delta.total_seconds())
            except (ValueError, TypeError) as err:
                _LOGGER.error(f"Error calculating timespan from {self._last_change}: {err}")
                self._state = 0
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
    def device_class(self) -> str:
        """Return the device class."""
        return SensorDeviceClass.DURATION

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:timer-outline"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attrs = dict(self._config)
        attrs["device_class"] = self.device_class
        # Add error info if required entities are missing
        if not self.hass.states.get(self._start_datetime_entity):
            attrs["_error"] = f"Start datetime entity '{self._start_datetime_entity}' not found. It may have been deleted or renamed."
        elif not self.hass.states.get(self._end_datetime_entity):
            attrs["_error"] = f"End datetime entity '{self._end_datetime_entity}' not found. It may have been deleted or renamed."
        return attrs

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

            if not start_state:
                _LOGGER.warning(f"Start datetime entity '{self._start_datetime_entity}' not found")
                self._state = None
            elif not end_state:
                _LOGGER.warning(f"End datetime entity '{self._end_datetime_entity}' not found")
                self._state = None
            else:
                try:
                    start_datetime = parse_datetime_or_date(start_state.state)
                    end_datetime = parse_datetime_or_date(end_state.state)
                except (ValueError, TypeError) as parse_err:
                    _LOGGER.error(f"Failed to parse datetime states: {parse_err}")
                    self._state = None
                    self.async_write_ha_state()
                    return
                
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
        except Exception as err:
            _LOGGER.error(f"Error updating date range sensor state: {err}")
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
    def device_class(self) -> str:
        """Return the device class."""
        return SensorDeviceClass.DURATION

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:calendar-star"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attrs = dict(self._config)
        attrs["device_class"] = self.device_class
        return attrs

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
        try:
            now = dt_util.now().date()
            days_to_holiday = get_days_to_holiday(self.hass, now, self._holiday_key, self._custom_holidays)
            
            if days_to_holiday >= 0:
                self._state = days_to_holiday + self._offset_days
            else:
                _LOGGER.warning(f"Holiday '{self._holiday_key}' not found or invalid")
                self._state = None
        except Exception as err:
            _LOGGER.error(f"Error updating holiday sensor state for '{self._holiday_key}': {err}")
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
    def device_class(self) -> str:
        """Return the device class."""
        return SensorDeviceClass.TIMESTAMP

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:calendar-clock"

    @property
    def state(self) -> Optional[str]:
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attrs = dict(self._config)
        attrs["device_class"] = self.device_class
        # Add error info if source entity is missing
        if not self.hass.states.get(self._datetime_entity):
            attrs["_error"] = f"Datetime entity '{self._datetime_entity}' not found. It may have been deleted or renamed."
        return attrs

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
            if not state:
                _LOGGER.warning(f"Datetime entity '{self._datetime_entity}' not found")
                self._state = None
            else:
                try:
                    base_datetime = parse_datetime_or_date(state.state)
                except (ValueError, TypeError) as parse_err:
                    _LOGGER.error(f"Failed to parse datetime from '{self._datetime_entity}': {parse_err}")
                    self._state = None
                    self.async_write_ha_state()
                    return
                
                if base_datetime:
                    result_datetime = apply_offset_to_datetime(base_datetime, self._offset_str)
                    if result_datetime:
                        self._state = result_datetime.isoformat()
                    else:
                        _LOGGER.warning(f"Failed to apply offset '{self._offset_str}' to datetime")
                        self._state = None
                else:
                    _LOGGER.warning(f"Invalid state value '{state.state}' from entity '{self._datetime_entity}'")
                    self._state = None
        except Exception as err:
            _LOGGER.error(f"Error updating datetime offset sensor state: {err}")
            self._state = None

        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners."""
        if self._remove_listener:
            self._remove_listener()


class ClockworkHolidayDateSensor(SensorEntity):
    """Sensor for holiday dates (automatically created for all holidays)."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        holiday_key: str,
        holiday_name: str,
        custom_holidays: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Initialize the holiday date sensor."""
        self.hass = hass
        self._config_entry = config_entry
        self._holiday_key = holiday_key
        self._holiday_name = holiday_name
        self._custom_holidays = custom_holidays or []
        self._state = None
        self._remove_timer = None

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{DOMAIN.title()} {self._holiday_name} Date"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{DOMAIN}_{self._config_entry.entry_id}_holiday_{self._holiday_key}"

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
        """Return the state of the sensor (ISO date format)."""
        return self._state

    @property
    def device_class(self) -> str:
        """Return the device class."""
        return SensorDeviceClass.DATE

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:calendar"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "device_class": self.device_class,
            "holiday_key": self._holiday_key,
            "holiday_name": self._holiday_name,
        }

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # Initial state
        self._update_state()

        # Update daily at midnight
        @callback
        def update_daily(now):
            """Update the holiday date daily."""
            self._update_state()

        self._remove_timer = async_track_time_interval(
            self.hass, update_daily, timedelta(days=1)
        )

    @callback
    def _update_state(self) -> None:
        """Update the sensor state with the holiday date for current year."""
        try:
            current_year = dt_util.now().year
            holiday_date = get_holiday_date(
                self.hass,
                current_year,
                self._holiday_key,
                self._custom_holidays
            )

            if holiday_date:
                # Return ISO date format (YYYY-MM-DD)
                self._state = holiday_date.isoformat()
            else:
                _LOGGER.warning(f"Could not calculate date for holiday '{self._holiday_key}'")
                self._state = None
        except Exception as err:
            _LOGGER.error(f"Error updating holiday date sensor state for '{self._holiday_key}': {err}")
            self._state = None

        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up when entity is removed."""
        if self._remove_timer:
            self._remove_timer()
