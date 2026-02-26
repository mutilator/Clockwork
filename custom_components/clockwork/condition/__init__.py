"""Clockwork automation conditions platform."""
import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .timespan import CONDITION_SCHEMA as TIMESPAN_CONDITION_SCHEMA, TimespanCondition, if_action, async_if_action
from .last_triggered import CONDITION_SCHEMA as LAST_TRIGGERED_CONDITION_SCHEMA, LastTriggeredCondition

_LOGGER = logging.getLogger(__name__)

_LOGGER.debug("Clockwork condition platform module initialized")

__all__ = [
    "TIMESPAN_CONDITION_SCHEMA",
    "LAST_TRIGGERED_CONDITION_SCHEMA",
    "TimespanCondition",
    "LastTriggeredCondition",
    "if_action",
    "async_if_action",
    "async_get_conditions",
]


async def async_get_conditions(hass: HomeAssistant) -> dict[str, Any]:
    """Return condition classes for this integration.

    Returns a dictionary mapping condition type to the condition class.
    """
    _LOGGER.debug("[CONDITIONS] async_get_conditions called, returning condition classes")
    return {
        "timespan": TimespanCondition,
        "last_triggered": LastTriggeredCondition,
    }

