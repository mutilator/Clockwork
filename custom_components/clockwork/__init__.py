"""Clockwork integration for Home Assistant."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, PLATFORMS, CONF_CALCULATIONS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Clockwork from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    calculations = entry.options.get(CONF_CALCULATIONS, entry.data.get(CONF_CALCULATIONS, []))
    hass.data[DOMAIN][entry.entry_id] = calculations

    # Reconcile entities: remove any that don't match configured calculations
    entity_registry = er.async_get(hass)
    
    # Build a set of configured calculation names (normalized for matching)
    configured_names = {calc.get('name', '').replace(' ', '_').lower() for calc in calculations}
    _LOGGER.debug(f"Reconciliation: Configured calculation names: {configured_names}")
    
    # Find and remove entities that don't match any configured calculation
    for entity_id, entity in list(entity_registry.entities.items()):
        if entity.config_entry_id == entry.entry_id:
            # Extract the calculation name from unique_id
            # Format: domain_entry_id_calc_name
            if entity.unique_id:
                # Remove the domain and entry_id prefix to get just the calculation name
                # unique_id starts with "clockwork_<entry_id>_<calc_name>"
                prefix = f"{DOMAIN}_{entry.entry_id}_"
                if entity.unique_id.startswith(prefix):
                    entity_calc_name = entity.unique_id[len(prefix):]
                    _LOGGER.debug(f"Entity {entity_id}: unique_id={entity.unique_id}, extracted_name={entity_calc_name}, in_config={entity_calc_name in configured_names}")
                    
                    # Check if this entity's calculation exists in config
                    if entity_calc_name not in configured_names:
                        _LOGGER.info(f"Removing orphaned entity {entity_id} (calculation '{entity_calc_name}' not in config)")
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