"""Clockwork integration for Home Assistant."""
import logging
import json
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, PLATFORMS, CONF_CALCULATIONS, CONF_AUTO_CREATE_HOLIDAYS, SERVICE_SCAN_AUTOMATIONS
from .diagnostics import async_get_config_entry_diagnostics
from .utils import scan_automations_for_time_usage

_LOGGER = logging.getLogger(__name__)


def _load_json_file(filename: str) -> dict:
    """Load a JSON file from the component directory synchronously."""
    file_path = Path(__file__).parent / filename
    with open(file_path, 'r') as f:
        return json.load(f)


async def _load_json_async(hass: HomeAssistant, filename: str) -> dict:
    """Load a JSON file asynchronously using the executor."""
    return await hass.async_add_executor_job(_load_json_file, filename)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Clockwork from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    calculations = entry.options.get(CONF_CALCULATIONS, entry.data.get(CONF_CALCULATIONS, []))
    hass.data[DOMAIN][entry.entry_id] = calculations

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