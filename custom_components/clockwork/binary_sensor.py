"""Binary sensor platform for Clockwork integration."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_CALCULATIONS, CALC_TYPE_OFFSET, CALC_TYPE_SEASON, CALC_TYPE_MONTH, CALC_TYPE_BETWEEN_DATES, CALC_TYPE_OUTSIDE_DATES
from .utils import is_in_season, parse_offset, is_datetime_between, parse_datetime_or_date

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Clockwork binary sensors."""
    # Get calculations from options first (user changes), fall back to data
    calculations = config_entry.options.get(CONF_CALCULATIONS, config_entry.data.get(CONF_CALCULATIONS, []))
    _LOGGER.debug(f"Binary sensor setup with {len(calculations)} calculations: {[c.get('type') for c in calculations]}")
    entities = []

    for calc in calculations:
        calc_type = calc.get("type")
        _LOGGER.debug(f"Processing calculation: type={calc_type}, name={calc.get('name')}")
        if calc_type == CALC_TYPE_OFFSET:
            entities.append(ClockworkOffsetBinarySensor(calc, hass, config_entry))
        elif calc_type == CALC_TYPE_SEASON:
            _LOGGER.debug(f"Adding season sensor for {calc.get('name')}")
            entities.append(ClockworkSeasonBinarySensor(calc, hass, config_entry))
        elif calc_type == CALC_TYPE_MONTH:
            entities.append(ClockworkMonthBinarySensor(calc, hass, config_entry))
        elif calc_type == CALC_TYPE_BETWEEN_DATES:
            entities.append(ClockworkBetweenDatesSensor(calc, hass, config_entry))
        elif calc_type == CALC_TYPE_OUTSIDE_DATES:
            entities.append(ClockworkOutsideDatesSensor(calc, hass, config_entry))

    _LOGGER.debug(f"Adding {len(entities)} binary sensor entities")
    async_add_entities(entities)


class ClockworkOffsetBinarySensor(BinarySensorEntity):
    """Binary sensor for offset calculations."""

    def __init__(self, config: Dict[str, Any], hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        self._config = config
        self.hass = hass
        self._config_entry = config_entry
        self._is_on = False
        self._trigger_time = None
        self._offset_seconds = parse_offset(config.get("offset", "0"))
        self._pulse_duration_seconds = parse_offset(config.get("pulse_duration", str(self._offset_seconds)))
        self._entity_id = config.get("entity_id")
        self._mode = config.get("offset_mode", "latch")  # pulse, duration, or latch
        self._trigger_on = config.get("trigger_on", "on")  # on or off (for duration mode)
        self._source_is_on = False
        self._remove_listener = None

    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        return f"{self._config.get('name', 'Offset')} Active"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{DOMAIN}_{self._config_entry.entry_id}_{self._config.get('name', 'Offset Binary').replace(' ', '_').lower()}"

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
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._is_on

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:alarm" if self._is_on else "mdi:alarm-off"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attrs = dict(self._config)
        # Add error info if source entity is missing
        if self._entity_id and not self.hass.states.get(self._entity_id):
            attrs["_error"] = f"Source entity '{self._entity_id}' not found. It may have been deleted or renamed."
        return attrs

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        @callback
        def state_change_listener(event):
            """Handle state changes."""
            new_state = event.data.get("new_state")
            if new_state and new_state.state == "on":
                self._source_is_on = True
                # Only trigger on this event if we're listening for "on" state
                if self._trigger_on == "on" or self._trigger_on == "both":
                    self._trigger_time = dt_util.utcnow() + timedelta(seconds=self._offset_seconds)
                self._update_state()
            elif new_state and new_state.state == "off":
                self._source_is_on = False
                # Only trigger on this event if we're listening for "off" state
                if self._trigger_on == "off" or self._trigger_on == "both":
                    self._trigger_time = dt_util.utcnow() + timedelta(seconds=self._offset_seconds)
                    self._update_state()
                elif self._mode == "duration":
                    # In duration mode with trigger_on="on", turn off when source turns off
                    self._trigger_time = None
                    self._is_on = False
                    self.async_write_ha_state()
                elif self._mode == "pulse":
                    # In pulse mode, cancel trigger
                    self._trigger_time = None
                    self._is_on = False
                    self.async_write_ha_state()

        self._remove_listener = async_track_state_change_event(
            self.hass, [self._entity_id] if self._entity_id else [], state_change_listener
        )

        # Check periodically
        @callback
        def check_trigger(now):
            """Check if trigger time has passed."""
            self._update_state()

        # Schedule check every minute, but can be improved with event
        self._remove_listener = async_track_time_interval(self.hass, check_trigger, timedelta(minutes=1))

    @callback
    def _update_state(self) -> None:
        """Update the sensor state based on mode."""
        try:
            now = dt_util.utcnow()
            
            if self._mode == "pulse":
                # Pulse mode: ON for pulse_duration seconds after trigger, then OFF
                if self._trigger_time:
                    pulse_end_time = self._trigger_time + timedelta(seconds=self._pulse_duration_seconds)
                    self._is_on = self._trigger_time <= now < pulse_end_time
                    # Clear trigger after pulse ends
                    if now >= pulse_end_time:
                        self._trigger_time = None
                else:
                    self._is_on = False
            
            elif self._mode == "duration":
                # Duration mode: ON when offset reached after trigger event
                # Stays ON while the source state matches trigger condition
                if self._trigger_time and now >= self._trigger_time:
                    # Check if we should stay on based on trigger_on and current state
                    if self._trigger_on == "on" and self._source_is_on:
                        self._is_on = True
                    elif self._trigger_on == "off" and not self._source_is_on:
                        self._is_on = True
                    elif self._trigger_on == "both":
                        self._is_on = True
                    else:
                        self._is_on = False
                else:
                    self._is_on = False
            
            else:  # latch mode (default)
                # Latch mode: ON when offset reached after trigger event, stays ON indefinitely
                if self._trigger_time and now >= self._trigger_time:
                    self._is_on = True
                else:
                    self._is_on = False
        except (ValueError, TypeError, AttributeError) as err:
            _LOGGER.error(f"Error updating offset binary sensor state: {err}")
            self._is_on = False
        
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners when entity is removed."""
        if self._remove_listener:
            self._remove_listener()


class ClockworkSeasonBinarySensor(BinarySensorEntity):
    """Binary sensor for season detection."""

    def __init__(self, config: Dict[str, Any], hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        self._config = config
        self.hass = hass
        self._config_entry = config_entry
        self._season = config.get("season", "").lower()
        self._hemisphere = config.get("hemisphere", "northern").lower()
        self._is_on = False
        self._remove_listener = None

    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        return f"{self._config.get('name', 'Season')} {self._season.title()}"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{DOMAIN}_{self._config_entry.entry_id}_{self._config.get('name', 'unknown').replace(' ', '_').lower()}"

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
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._is_on

    @property
    def icon(self) -> str:
        """Return the icon."""
        seasons_icons = {
            "spring": "mdi:flower",
            "summer": "mdi:sun",
            "autumn": "mdi:leaf",
            "fall": "mdi:leaf",
            "winter": "mdi:snowflake",
        }
        return seasons_icons.get(self._season, "mdi:calendar-today")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return self._config

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # Initial state
        self._update_state()

        @callback
        def check_season(now):
            """Check if current date is in season."""
            self._update_state()

        # Check daily
        self._remove_listener = async_track_time_interval(self.hass, check_season, timedelta(days=1))

    @callback
    def _update_state(self) -> None:
        """Update the sensor state."""
        try:
            now = dt_util.now().date()
            self._is_on = is_in_season(self.hass, now, self._season, self._hemisphere)
        except Exception as err:
            _LOGGER.error(f"Error updating season binary sensor state for '{self._season}': {err}")
            self._is_on = False
        
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners when entity is removed."""
        if self._remove_listener:
            self._remove_listener()


class ClockworkMonthBinarySensor(BinarySensorEntity):
    """Binary sensor for month detection."""

    def __init__(self, config: Dict[str, Any], hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        self._config = config
        self.hass = hass
        self._config_entry = config_entry
        self._months = [int(m) for m in config.get("months", "").split(",") if m.strip().isdigit()]
        self._is_on = False
        self._remove_listener = None

    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        return self._config.get("name", "Month Check")

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{DOMAIN}_{self._config_entry.entry_id}_{self._config.get('name', 'unknown').replace(' ', '_').lower()}"

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
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._is_on

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:calendar-check" if self.is_on else "mdi:calendar-blank"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return self._config

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # Initial state
        self._update_state()

        @callback
        def check_month(now):
            """Check if current month is in list."""
            self._update_state()

        # Check daily
        self._remove_listener = async_track_time_interval(self.hass, check_month, timedelta(days=1))

    @callback
    def _update_state(self) -> None:
        """Update the sensor state."""
        try:
            if not self._months:
                _LOGGER.warning("No months configured for month binary sensor")
                self._is_on = False
            else:
                now = dt_util.now()
                self._is_on = now.month in self._months
        except (ValueError, TypeError, AttributeError) as err:
            _LOGGER.error(f"Error updating month binary sensor state: {err}")
            self._is_on = False
        
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners when entity is removed."""
        if self._remove_listener:
            self._remove_listener()


class ClockworkBetweenDatesSensor(BinarySensorEntity):
    """Binary sensor that is on when current time is between two datetime entities/helpers."""

    def __init__(self, config: Dict[str, Any], hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        self._config = config
        self.hass = hass
        self._config_entry = config_entry
        self._is_on = False
        self._start_datetime_entity = config.get("start_datetime_entity")
        self._end_datetime_entity = config.get("end_datetime_entity")
        self._remove_listener = None

    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        return self._config.get("name", "Between Dates")

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{DOMAIN}_{self._config_entry.entry_id}_{self._config.get('name', 'Offset Binary').replace(' ', '_').lower()}"

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
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._is_on

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:calendar-clock" if self._is_on else "mdi:calendar-outline"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attrs = dict(self._config)
        # Add error info if required entities are missing
        if self._start_datetime_entity and not self.hass.states.get(self._start_datetime_entity):
            attrs["_error"] = f"Start datetime entity '{self._start_datetime_entity}' not found. It may have been deleted or renamed."
        elif self._end_datetime_entity and not self.hass.states.get(self._end_datetime_entity):
            attrs["_error"] = f"End datetime entity '{self._end_datetime_entity}' not found. It may have been deleted or renamed."
        return attrs

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        @callback
        def datetime_change_listener(event):
            """Handle datetime entity state changes."""
            self._update_state()

        # Listen to both entities
        entity_ids = [e for e in [self._start_datetime_entity, self._end_datetime_entity] if e]
        self._remove_listener = async_track_state_change_event(
            self.hass, entity_ids, datetime_change_listener
        )

        # Check periodically (every minute)
        @callback
        def check_between(now):
            """Check if current time is between the dates."""
            self._update_state()

        self._remove_timer = async_track_time_interval(self.hass, check_between, timedelta(minutes=1))
        
        # Initial state
        self._update_state()

    @callback
    def _update_state(self) -> None:
        """Update the sensor state."""
        try:
            start_state = self.hass.states.get(self._start_datetime_entity) if self._start_datetime_entity else None
            end_state = self.hass.states.get(self._end_datetime_entity) if self._end_datetime_entity else None

            _LOGGER.debug(f"Between Dates '{self.name}' - Start entity state: {start_state}")
            _LOGGER.debug(f"Between Dates '{self.name}' - End entity state: {end_state}")

            if not start_state:
                _LOGGER.warning(f"Between Dates '{self.name}' - Start datetime entity '{self._start_datetime_entity}' not found")
                self._is_on = False
            elif not end_state:
                _LOGGER.warning(f"Between Dates '{self.name}' - End datetime entity '{self._end_datetime_entity}' not found")
                self._is_on = False
            else:
                try:
                    start_datetime = parse_datetime_or_date(start_state.state)
                    end_datetime = parse_datetime_or_date(end_state.state)
                except (ValueError, TypeError) as parse_err:
                    _LOGGER.error(f"Between Dates '{self.name}' - Failed to parse datetime states: {parse_err}")
                    self._is_on = False
                    self.async_write_ha_state()
                    return
                
                _LOGGER.debug(f"Between Dates '{self.name}' - Parsed start_datetime: {start_datetime}")
                _LOGGER.debug(f"Between Dates '{self.name}' - Parsed end_datetime: {end_datetime}")
                
                if start_datetime and end_datetime:
                    current_datetime = dt_util.now()
                    _LOGGER.debug(f"Between Dates '{self.name}' - Current datetime: {current_datetime}")
                    
                    # Ensure all datetimes are in the same timezone (make naive datetimes aware)
                    if start_datetime.tzinfo is None:
                        start_datetime = start_datetime.replace(tzinfo=current_datetime.tzinfo)
                        _LOGGER.debug(f"Between Dates '{self.name}' - Made start_datetime timezone-aware: {start_datetime}")
                    if end_datetime.tzinfo is None:
                        end_datetime = end_datetime.replace(tzinfo=current_datetime.tzinfo)
                        _LOGGER.debug(f"Between Dates '{self.name}' - Made end_datetime timezone-aware: {end_datetime}")
                    
                    self._is_on = is_datetime_between(current_datetime, start_datetime, end_datetime)
                    _LOGGER.debug(f"Between Dates '{self.name}' - Result: {self._is_on}")
                else:
                    _LOGGER.warning(f"Between Dates '{self.name}' - Failed to parse datetimes: start={start_datetime}, end={end_datetime}")
                    self._is_on = False
        except (AttributeError, RuntimeError) as err:
            _LOGGER.error(f"Between Dates '{self.name}' - Unexpected error: {err}")
            self._is_on = False
        
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners when entity is removed."""
        if self._remove_listener:
            self._remove_listener()
        if self._remove_timer:
            self._remove_timer()


class ClockworkOutsideDatesSensor(BinarySensorEntity):
    """Binary sensor that is on when current time is OUTSIDE two datetime entities/helpers."""

    def __init__(self, config: Dict[str, Any], hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        self._config = config
        self.hass = hass
        self._config_entry = config_entry
        self._is_on = False
        self._start_datetime_entity = config.get("start_datetime_entity")
        self._end_datetime_entity = config.get("end_datetime_entity")
        self._remove_listener = None
        self._remove_timer = None

    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        return self._config.get("name", "Outside Dates")

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{DOMAIN}_{self._config_entry.entry_id}_{self._config.get('name', 'Offset Binary').replace(' ', '_').lower()}"

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
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._is_on

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:calendar-remove" if self._is_on else "mdi:calendar"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attrs = dict(self._config)
        # Add error info if required entities are missing
        if self._start_datetime_entity and not self.hass.states.get(self._start_datetime_entity):
            attrs["_error"] = f"Start datetime entity '{self._start_datetime_entity}' not found. It may have been deleted or renamed."
        elif self._end_datetime_entity and not self.hass.states.get(self._end_datetime_entity):
            attrs["_error"] = f"End datetime entity '{self._end_datetime_entity}' not found. It may have been deleted or renamed."
        return attrs

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        @callback
        def datetime_change_listener(event):
            """Handle datetime entity state changes."""
            self._update_state()

        # Listen to both entities
        entity_ids = [e for e in [self._start_datetime_entity, self._end_datetime_entity] if e]
        self._remove_listener = async_track_state_change_event(
            self.hass, entity_ids, datetime_change_listener
        )

        # Check periodically (every minute)
        @callback
        def check_outside(now):
            """Check if current time is outside the dates."""
            self._update_state()

        self._remove_timer = async_track_time_interval(self.hass, check_outside, timedelta(minutes=1))
        
        # Initial state
        self._update_state()

    @callback
    def _update_state(self) -> None:
        """Update the sensor state."""
        try:
            start_state = self.hass.states.get(self._start_datetime_entity) if self._start_datetime_entity else None
            end_state = self.hass.states.get(self._end_datetime_entity) if self._end_datetime_entity else None

            if not start_state:
                _LOGGER.warning(f"Outside Dates '{self.name}' - Start datetime entity '{self._start_datetime_entity}' not found")
                self._is_on = False
            elif not end_state:
                _LOGGER.warning(f"Outside Dates '{self.name}' - End datetime entity '{self._end_datetime_entity}' not found")
                self._is_on = False
            else:
                try:
                    start_datetime = parse_datetime_or_date(start_state.state)
                    end_datetime = parse_datetime_or_date(end_state.state)
                except (ValueError, TypeError) as parse_err:
                    _LOGGER.error(f"Outside Dates '{self.name}' - Failed to parse datetime states: {parse_err}")
                    self._is_on = False
                    self.async_write_ha_state()
                    return
                
                if start_datetime and end_datetime:
                    current_datetime = dt_util.now()
                    
                    # Ensure all datetimes are in the same timezone (make naive datetimes aware)
                    if start_datetime.tzinfo is None:
                        start_datetime = start_datetime.replace(tzinfo=current_datetime.tzinfo)
                    if end_datetime.tzinfo is None:
                        end_datetime = end_datetime.replace(tzinfo=current_datetime.tzinfo)
                    
                    # True if OUTSIDE the range (not between)
                    self._is_on = not is_datetime_between(current_datetime, start_datetime, end_datetime)
                else:
                    _LOGGER.warning(f"Outside Dates '{self.name}' - Failed to parse datetimes: start={start_datetime}, end={end_datetime}")
                    self._is_on = False
        except (AttributeError, RuntimeError) as err:
            _LOGGER.error(f"Outside Dates '{self.name}' - Unexpected error: {err}")
            self._is_on = False
        
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners when entity is removed."""
        if self._remove_listener:
            self._remove_listener()
        if self._remove_timer:
            self._remove_timer()