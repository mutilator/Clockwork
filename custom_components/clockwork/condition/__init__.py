"""Clockwork automation conditions platform."""
import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .timespan import CONDITION_SCHEMA, TimespanCondition, if_action, async_if_action

_LOGGER = logging.getLogger(__name__)

_LOGGER.debug("Clockwork condition platform module initialized")

__all__ = ["CONDITION_SCHEMA", "if_action", "async_if_action", "async_get_conditions", "TimespanCondition"]


async def async_get_conditions(hass: HomeAssistant) -> dict[str, Any]:
    """Return condition classes for this integration.
    
    Returns a dictionary mapping condition type to the condition class.
    """
    _LOGGER.debug("[TIMESPAN] async_get_conditions called, returning TimespanCondition class")
    return {
        "timespan": TimespanCondition,
    }

