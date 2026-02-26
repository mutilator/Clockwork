"""Clockwork integration for Home Assistant."""
import logging
import json
import datetime
import dataclasses
from pathlib import Path
from collections.abc import Iterable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import Platform
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.components.calendar import CalendarEntity, CalendarEntityFeature
from homeassistant.components.calendar.const import DOMAIN as CALENDAR_DOMAIN
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from homeassistant.util.json import JsonValueType
from homeassistant.core import ServiceResponse, SupportsResponse

from .const import DOMAIN, PLATFORMS, CONF_CALCULATIONS, CONF_AUTO_CREATE_HOLIDAYS, SERVICE_SCAN_AUTOMATIONS
from .diagnostics import async_get_config_entry_diagnostics
from .utils import scan_automations_for_time_usage

_LOGGER = logging.getLogger(__name__)

# Service constants for calendar operations
SERVICE_GET_EVENTS = "get_events"
SERVICE_DELETE_EVENT = "delete_event"
SERVICE_UPDATE_EVENT = "update_event"
SERVICE_DELETE_EVENTS_IN_RANGE = "delete_events_in_range"

CONF_CALENDAR_ID = "calendar_id"
CONF_EVENT_ID = "event_id"
CONF_START_DATE = "start_date"
CONF_END_DATE = "end_date"
CONF_RECURRENCE_ID = "recurrence_id"
CONF_RECURRENCE_RANGE = "recurrence_range"

# Import condition module to register automation conditions (only if platform is available)
try:
    from . import condition  # noqa: F401
except ImportError:
    _LOGGER.debug("Automation condition platform not available in this Home Assistant version")


def _list_events_dict_factory(
    obj: Iterable[tuple[str, Any]],
) -> dict[str, JsonValueType]:
    """Convert CalendarEvent dataclass items to dictionary of attributes."""
    result: dict[str, str] = {}
    for name, value in obj:
        if isinstance(value, (datetime.datetime, datetime.date)):
            result[name] = value.isoformat()
        elif value is not None:
            result[name] = str(value)
    
    # Filter to keep only important fields
    return {
        k: v for k, v in result.items() 
        if k in {"start", "end", "summary", "description", "location", "uid", "recurrence_id", "recurrence_range"}
    }


def _load_json_file(filename: str) -> dict:
    """Load a JSON file from the component directory synchronously."""
    file_path = Path(__file__).parent / filename
    with open(file_path, 'r') as f:
        return json.load(f)


async def _load_json_async(hass: HomeAssistant, filename: str) -> dict:
    """Load a JSON file asynchronously using the executor."""
    return await hass.async_add_executor_job(_load_json_file, filename)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Clockwork integration at component level.
    
    This ensures the conditions platform is loaded and registered.
    """
    _LOGGER.info("Setting up Clockwork integration")
    
    # Import and verify condition module is loaded
    try:
        from . import condition as condition_module
        _LOGGER.info(f"Clockwork condition module loaded: {condition_module}")
        _LOGGER.info(f"Clockwork if_action function available: {hasattr(condition_module, 'if_action')}")
        _LOGGER.info(f"Clockwork CONDITION_SCHEMA available: {hasattr(condition_module, 'CONDITION_SCHEMA')}")
    except Exception as err:
        _LOGGER.error(f"Error loading Clockwork condition module: {err}", exc_info=True)
    
    # Register calendar services
    async def async_delete_event(call: ServiceCall) -> None:
        """Delete a calendar event."""
        try:
            calendar_id = call.data[CONF_CALENDAR_ID]
            event_id = call.data[CONF_EVENT_ID]
            recurrence_id = call.data.get(CONF_RECURRENCE_ID)
            recurrence_range = call.data.get(CONF_RECURRENCE_RANGE)
        except KeyError as e:
            raise HomeAssistantError(f"Missing parameter: {str(e)}")

        calendar_entity = next(
            (entity for entity in hass.data.get("entity_components", {}).get(CALENDAR_DOMAIN, {}).get("entities", [])
             if getattr(entity, "entity_id", None) == calendar_id),
            None
        )

        if calendar_entity is None:
            raise HomeAssistantError(f"Calendar entity {calendar_id} not found")

        if not calendar_entity.supported_features or not calendar_entity.supported_features & CalendarEntityFeature.DELETE_EVENT:
            raise HomeAssistantError("Calendar does not support deleting events")

        try:
            await calendar_entity.async_delete_event(
                event_id,
                recurrence_id=recurrence_id,
                recurrence_range=recurrence_range,
            )
            _LOGGER.info("Event %s deleted", event_id)
        except Exception as e:
            _LOGGER.error("Error deleting event: %s", e)
            raise HomeAssistantError(f"Failed to delete event: {str(e)}")

    async def async_update_event(call: ServiceCall) -> None:
        """Update a calendar event."""
        try:
            calendar_id = call.data[CONF_CALENDAR_ID]
            event_id = call.data[CONF_EVENT_ID]
            event_data = call.data.get("event", {})
            recurrence_id = call.data.get(CONF_RECURRENCE_ID)
            recurrence_range = call.data.get(CONF_RECURRENCE_RANGE)
        except KeyError as e:
            raise HomeAssistantError(f"Missing parameter: {str(e)}")

        calendar_entity = next(
            (entity for entity in hass.data.get("entity_components", {}).get(CALENDAR_DOMAIN, {}).get("entities", [])
             if getattr(entity, "entity_id", None) == calendar_id),
            None
        )

        if calendar_entity is None:
            raise HomeAssistantError(f"Calendar entity {calendar_id} not found")

        if not calendar_entity.supported_features or not calendar_entity.supported_features & CalendarEntityFeature.UPDATE_EVENT:
            raise HomeAssistantError("Calendar does not support updating events")

        try:
            await calendar_entity.async_update_event(
                event_id,
                event_data,
                recurrence_id=recurrence_id,
                recurrence_range=recurrence_range,
            )
            _LOGGER.info("Event %s updated", event_id)
        except Exception as e:
            _LOGGER.error("Error updating event: %s", e)
            raise HomeAssistantError(f"Failed to update event: {str(e)}")

    async def async_delete_events_in_range(call: ServiceCall) -> None:
        """Delete all events within a date range."""
        try:
            calendar_id = call.data[CONF_CALENDAR_ID]
            start_date = dt_util.as_local(datetime.datetime.fromisoformat(call.data[CONF_START_DATE])).date()
            end_date = dt_util.as_local(datetime.datetime.fromisoformat(call.data[CONF_END_DATE])).date()
        except KeyError as e:
            raise HomeAssistantError(f"Missing parameter: {str(e)}")

        calendar_entity = next(
            (entity for entity in hass.data.get("entity_components", {}).get(CALENDAR_DOMAIN, {}).get("entities", [])
             if getattr(entity, "entity_id", None) == calendar_id),
            None
        )

        if calendar_entity is None:
            raise HomeAssistantError(f"Calendar entity {calendar_id} not found")

        if not calendar_entity.supported_features or not calendar_entity.supported_features & CalendarEntityFeature.DELETE_EVENT:
            raise HomeAssistantError("Calendar does not support deleting events")

        try:
            dt_start = dt_util.as_local(datetime.datetime.combine(start_date, datetime.time.min))
            dt_end = dt_util.as_local(datetime.datetime.combine(end_date + datetime.timedelta(days=1), datetime.time.min))
            events = await calendar_entity.async_get_events(hass, dt_start, dt_end)
            deleted_count = 0

            for event in events:
                event_start = event.start
                event_end = event.end

                if isinstance(event_start, datetime.datetime):
                    event_start_date = event_start.date()
                else:
                    event_start_date = event_start

                if isinstance(event_end, datetime.datetime):
                    event_end_date = event_end.date()
                    if event_end.hour == 0 and event_end.minute == 0 and event_end.second == 0:
                        event_end_date = (event_end - datetime.timedelta(days=1)).date()
                else:
                    event_end_date = event_end - datetime.timedelta(days=1)

                if event_end_date < start_date or event_start_date > end_date:
                    continue

                try:
                    await calendar_entity.async_delete_event(event.uid)
                    _LOGGER.info("Event %s deleted", event.uid)
                    deleted_count += 1
                except Exception as event_error:
                    _LOGGER.warning("Could not delete event %s: %s", event.uid, event_error)

            _LOGGER.info("Deleted %d events in range", deleted_count)
        except Exception as e:
            _LOGGER.error("Error deleting events in range: %s", e)
            raise HomeAssistantError(f"Failed to delete events: {str(e)}")

    # Register the services
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_DELETE_EVENT,
        async_delete_event,
        schema=None
    )
    
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_UPDATE_EVENT,
        async_update_event,
        schema=None
    )
    
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_DELETE_EVENTS_IN_RANGE,
        async_delete_events_in_range,
        schema=None
    )
    
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Clockwork from a config entry."""
    _LOGGER.info(f"Setting up Clockwork config entry: {entry.entry_id}")
    
    # Ensure condition platform is loaded
    try:
        from . import condition as condition_module
        _LOGGER.info("Clockwork condition platform verified for this entry")
    except Exception as err:
        _LOGGER.warning(f"Could not verify conditions platform: {err}")
    
    hass.data.setdefault(DOMAIN, {})
    calculations = entry.options.get(CONF_CALCULATIONS, entry.data.get(CONF_CALCULATIONS, []))
    hass.data[DOMAIN][entry.entry_id] = calculations
    
    _LOGGER.debug(f"Setup entry {entry.entry_id}: {len(calculations)} calculations configured")

    # Load JSON files once at setup time and cache them in hass.data
    # This avoids blocking I/O operations in async contexts by using executor
    if "holidays" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["holidays"] = await _load_json_async(hass, "holidays.json")
    if "seasons" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["seasons"] = await _load_json_async(hass, "seasons.json")

    # Reconcile entities: remove any that don't match configured calculations
    entity_registry = er.async_get(hass)
    
    # Build a set of configured calculation names (normalized for matching)
    configured_names = {calc.get('name', '').replace(' ', '_').lower() for calc in calculations}
    _LOGGER.debug(f"Reconciliation: Configured calculation names: {configured_names}")
    
    # Get settings for holiday sensor handling
    auto_create_holidays = entry.options.get(CONF_AUTO_CREATE_HOLIDAYS, True)
    custom_holidays = entry.options.get("custom_holidays", [])
    custom_holiday_keys = {h.get("key") for h in custom_holidays if h.get("key")}
    _LOGGER.debug(f"Reconciliation: auto_create_holidays={auto_create_holidays}, custom_holiday_keys={custom_holiday_keys}")
    
    # Find and remove entities that don't match any configured calculation
    # (Holiday date sensors are auto-created and should not be removed based on calculations)
    for entity_id, entity in list(entity_registry.entities.items()):
        if entity.config_entry_id == entry.entry_id:
            # Extract the calculation name from unique_id
            # Format: domain_entry_id_calc_name or domain_entry_id_holiday_key
            if entity.unique_id:
                # Remove the domain and entry_id prefix to get just the calculation name
                # unique_id starts with "clockwork_<entry_id>_<calc_name>" or "clockwork_<entry_id>_holiday_<key>"
                prefix = f"{DOMAIN}_{entry.entry_id}_"
                if entity.unique_id.startswith(prefix):
                    entity_suffix = entity.unique_id[len(prefix):]
                    
                    # Handle auto-created holiday date sensors
                    if entity_suffix.startswith("holiday_"):
                        holiday_key = entity_suffix[8:]  # Remove "holiday_" prefix
                        
                        # If auto_create is disabled and this is NOT a custom holiday, remove it
                        if not auto_create_holidays and holiday_key not in custom_holiday_keys:
                            _LOGGER.info(f"Removing auto-created holiday sensor {entity_id} (auto_create_holidays is disabled)")
                            entity_registry.async_remove(entity_id)
                        else:
                            _LOGGER.debug(f"Entity {entity_id}: Keeping holiday sensor (auto_create={auto_create_holidays}, is_custom={holiday_key in custom_holiday_keys})")
                        continue
                    
                    # For calculation-based entities, check if the calculation exists
                    _LOGGER.debug(f"Entity {entity_id}: unique_id={entity.unique_id}, extracted_name={entity_suffix}, in_config={entity_suffix in configured_names}")
                    
                    if entity_suffix not in configured_names:
                        _LOGGER.info(f"Removing orphaned entity {entity_id} (calculation '{entity_suffix}' not in config)")
                        entity_registry.async_remove(entity_id)
                elif entity.device_id is None:
                    # Also remove entities without device_id (from previous versions)
                    _LOGGER.info(f"Removing orphaned entity without device: {entity_id}")
                    entity_registry.async_remove(entity_id)

    # Create device for this integration
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name="Clockwork",
        manufacturer="Clockwork",
        model="Date/Time Calculator"
    )
    
    # Store device info in hass.data for access by entity platforms
    hass.data[DOMAIN][f"{entry.entry_id}_device"] = device

    # Forward the setup to the platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen for options updates
    entry.async_on_unload(
        entry.add_update_listener(async_update_options)
    )

    # Register service to scan automations for time usage
    async def handle_scan_automations(call):
        """Handle the scan automations service call.
        
        Returns results directly and also fires an event for backward compatibility.
        """
        result = scan_automations_for_time_usage(hass)
        _LOGGER.info(f"Scan automations service: Found {len(result['automations'])} automations with time/date patterns")
        
        # Fire event for backward compatibility (listeners can still use this)
        hass.bus.async_fire(
            f"{DOMAIN}_automations_scanned",
            {"automations": result['automations']}
        )
        
        # Return results directly (new approach)
        return result
    
    # Register the service
    hass.services.async_register(
        DOMAIN,
        SERVICE_SCAN_AUTOMATIONS,
        handle_scan_automations,
        supports_response="only"  # This service returns data
    )

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok