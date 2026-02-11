"""Diagnostics support for Clockwork integration.

Provides diagnostic data for troubleshooting and support.
Accessible from Settings → Devices & Services → Clockwork → Options → Diagnostics
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Provides comprehensive diagnostic information for troubleshooting:
    - Configuration summary
    - Calculation configurations
    - Cached data status
    - Entity information
    - Platform statistics

    Args:
        hass: Home Assistant instance
        entry: Config entry being diagnosed

    Returns:
        Dictionary containing diagnostic data
    """
    entry_data = hass.data[DOMAIN].get(entry.entry_id, {})

    # Build configuration summary
    config_summary = {
        "entry_title": entry.title,
        "entry_version": entry.version,
        "entry_source": entry.source,
        "entry_state": entry.state.value,
        "has_options": bool(entry.options),
        "calculations_count": len(entry.options.get("calculations", [])),
        "custom_holidays_count": len(entry.options.get("custom_holidays", [])),
    }

    # Build calculations information
    calculations = entry.options.get("calculations", [])
    calculations_info = []
    for calc in calculations:
        calc_info = {
            "name": calc.get("name", "Unnamed"),
            "type": calc.get("type", "unknown"),
            "enabled": True,  # All calculations are enabled
        }
        # Add type-specific information
        if calc.get("type") == "timespan":
            calc_info.update({
                "entity_id": calc.get("entity_id"),
                "track_state": calc.get("track_state", "on"),
                "update_interval": calc.get("update_interval", 60),
            })
        elif calc.get("type") == "offset":
            calc_info.update({
                "entity_id": calc.get("entity_id"),
                "offset_seconds": calc.get("offset_seconds", 0),
                "trigger_on": calc.get("trigger_on", "on"),
                "mode": calc.get("mode", "pulse"),
            })
        elif calc.get("type") == "datetime_offset":
            calc_info.update({
                "datetime_entity": calc.get("datetime_entity"),
                "offset": calc.get("offset", ""),
            })
        elif calc.get("type") == "date_range":
            calc_info.update({
                "start_datetime_entity": calc.get("start_datetime_entity"),
                "end_datetime_entity": calc.get("end_datetime_entity"),
            })
        elif calc.get("type") == "season":
            calc_info.update({
                "season": calc.get("season"),
                "hemisphere": calc.get("hemisphere", "northern"),
            })
        elif calc.get("type") == "month":
            calc_info.update({
                "months": calc.get("months", ""),
            })
        elif calc.get("type") == "holiday":
            calc_info.update({
                "holiday": calc.get("holiday"),
                "offset_days": calc.get("offset", 0),
            })
        elif calc.get("type") in ["between_dates", "outside_dates"]:
            calc_info.update({
                "start_datetime_entity": calc.get("start_datetime_entity"),
                "end_datetime_entity": calc.get("end_datetime_entity"),
            })

        calculations_info.append(calc_info)

    # Build custom holidays information
    custom_holidays = entry.options.get("custom_holidays", [])
    holidays_info = []
    for holiday in custom_holidays:
        holidays_info.append({
            "name": holiday.get("name", "Unnamed"),
            "key": holiday.get("key"),
            "type": holiday.get("type"),
            "month": holiday.get("month"),
            "day": holiday.get("day"),
            "occurrence": holiday.get("occurrence"),
            "weekday": holiday.get("weekday"),
        })

    # Build cached data status
    cached_data = hass.data[DOMAIN]
    cached_data_info = {
        "holidays_loaded": "holidays" in cached_data,
        "holidays_count": len(cached_data.get("holidays", {})),
        "seasons_loaded": "seasons" in cached_data,
        "seasons_hemispheres": list(cached_data.get("seasons", {}).keys()),
    }

    # Build entity information
    entities_info = {
        "total_entities": 0,
        "sensor_count": 0,
        "binary_sensor_count": 0,
        "entities": [],
    }

    # Get all entities for this config entry
    from homeassistant.helpers import entity_registry as er
    entity_registry = er.async_get(hass)

    for entity_entry in entity_registry.entities.values():
        if entity_entry.config_entry_id == entry.entry_id:
            entities_info["total_entities"] += 1
            if entity_entry.entity_id.startswith("sensor."):
                entities_info["sensor_count"] += 1
            elif entity_entry.entity_id.startswith("binary_sensor."):
                entities_info["binary_sensor_count"] += 1

            entities_info["entities"].append({
                "entity_id": entity_entry.entity_id,
                "name": entity_entry.name,
                "unique_id": entity_entry.unique_id,
                "disabled": entity_entry.disabled,
            })

    # Build platform statistics
    platforms_info = {
        "sensors_registered": entities_info["sensor_count"],
        "binary_sensors_registered": entities_info["binary_sensor_count"],
        "device_created": f"{entry.entry_id}_device" in cached_data,
    }

    return {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "source": entry.source,
            "state": entry.state.value,
        },
        "configuration": config_summary,
        "calculations": calculations_info,
        "custom_holidays": holidays_info,
        "cached_data": cached_data_info,
        "entities": entities_info,
        "platforms": platforms_info,
    }
