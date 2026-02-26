"""Clockwork last_triggered automation condition."""
import logging
from datetime import datetime

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.condition import Condition, ConditionChecker
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

CONF_OPTIONS = "options"

# Define the options schema separately (fields that go into options)
_OPTIONS_SCHEMA_DICT = {
    vol.Required("entity_id"): cv.entity_id,
    vol.Optional("above"): vol.Coerce(int),
    vol.Optional("below"): vol.Coerce(int),
    vol.Optional("equal_to"): vol.Coerce(int),
}

# Main schema requires options dict wrapper
CONDITION_SCHEMA = vol.Schema(
    {
        vol.Required("condition"): cv.string,
        vol.Required(CONF_OPTIONS): vol.All(
            vol.Schema(_OPTIONS_SCHEMA_DICT),
            # At least one operator must be specified
            cv.has_at_least_one_key("above", "below", "equal_to"),
        ),
        # Standard Home Assistant automation fields
        vol.Optional("alias"): cv.string,
        vol.Optional("enabled"): cv.boolean,
    }
)


class LastTriggeredCondition(Condition):
    """Home Assistant automation condition for clockwork.last_triggered.

    Checks how long it's been since an automation was last triggered.
    """

    def __init__(self, hass: HomeAssistant, config: ConfigType) -> None:
        """Initialize the condition."""
        # Config may be ConfigType or ConditionConfig, cast to dict for parent class
        super().__init__(hass, dict(config) if not isinstance(config, dict) else config)  # type: ignore
        self.config = config
        _LOGGER.debug(f"[LAST_TRIGGERED] __init__ called with config: {config}")

    @classmethod
    async def async_validate_config(
        cls, hass: HomeAssistant, config: ConfigType
    ) -> ConfigType:
        """Validate the condition configuration (abstract method implementation)."""
        _LOGGER.debug(f"[LAST_TRIGGERED] async_validate_config called with: {config}")
        return CONDITION_SCHEMA(config)

    @classmethod
    async def async_validate_complete_config(
        cls, hass: HomeAssistant, complete_config: ConfigType
    ) -> ConfigType:
        """Validate the complete condition configuration.

        This validates the condition config with the proper schema.
        """
        _LOGGER.debug(f"[LAST_TRIGGERED] async_validate_complete_config called with: {complete_config}")

        # Validate with schema that expects options
        validated = await cls.async_validate_config(hass, complete_config)
        _LOGGER.debug(f"[LAST_TRIGGERED] async_validate_complete_config validated: {validated}")
        return validated

    async def async_get_checker(self) -> ConditionChecker:
        """Return the checker function for this condition.

        Home Assistant calls this and expects to get a callable that takes **kwargs.
        The checker should accept 'variables' as a kwarg.
        """
        _LOGGER.debug(f"[LAST_TRIGGERED] async_get_checker called, creating checker function")
        _LOGGER.debug(f"[LAST_TRIGGERED] self.config type: {type(self.config)}, value: {self.config}")

        # Extract options from ConditionConfig object
        # ConditionConfig has .options attribute with field values
        if isinstance(self.config, dict):
            options = self.config.get(CONF_OPTIONS, {})
        else:
            # ConditionConfig object with .options attribute
            options = self.config.options if hasattr(self.config, 'options') else {}

        _LOGGER.debug(f"[LAST_TRIGGERED] Extracted options: {options}")

        # Create a synchronous checker function that takes **kwargs
        def checker(**kwargs) -> bool:
            """Check the last_triggered condition.

            Home Assistant automation system will call this with variables=... kwargs.
            """
            _LOGGER.debug(f"[LAST_TRIGGERED] *** CHECKER CALLED *** with kwargs={kwargs}")
            variables = kwargs.get('variables')
            _LOGGER.debug(f"[LAST_TRIGGERED] Checker called with variables={variables}")

            entity_id = options.get("entity_id")
            _LOGGER.debug(f"[LAST_TRIGGERED] Evaluating condition for entity_id: {entity_id}")

            try:
                if not entity_id or not isinstance(entity_id, str):
                    _LOGGER.warning(f"Invalid entity_id in last_triggered condition: {entity_id}")
                    return False
                state = self._hass.states.get(entity_id)
                if state is None:
                    _LOGGER.warning(f"Clockwork last_triggered condition: Entity '{entity_id}' not found")
                    _LOGGER.debug(f"[LAST_TRIGGERED] {entity_id} not found, returning False")
                    return False

                _LOGGER.debug(f"[LAST_TRIGGERED] Retrieved state for {entity_id}: {state}")
                _LOGGER.debug(f"[LAST_TRIGGERED] State object: state={state.state}, attributes={state.attributes}")

                # Get last_triggered from attributes
                last_triggered = state.attributes.get("last_triggered")
                if last_triggered is None:
                    _LOGGER.warning(
                        f"Clockwork last_triggered condition: Entity '{entity_id}' has no last_triggered attribute. "
                        "Condition evaluates to False."
                    )
                    _LOGGER.debug(f"[LAST_TRIGGERED] {entity_id} has no last_triggered, returning False")
                    return False

                _LOGGER.debug(f"[LAST_TRIGGERED] State last_triggered: {last_triggered}")

                # Convert last_triggered to datetime if it's a string
                if isinstance(last_triggered, str):
                    try:
                        last_triggered = dt_util.parse_datetime(last_triggered)
                        if last_triggered is None:
                            _LOGGER.warning(f"Clockwork last_triggered condition: Could not parse last_triggered timestamp '{state.attributes.get('last_triggered')}'")
                            return False
                    except (ValueError, TypeError) as e:
                        _LOGGER.warning(f"Clockwork last_triggered condition: Error parsing last_triggered timestamp: {e}")
                        return False
                elif not isinstance(last_triggered, datetime):
                    _LOGGER.warning(f"Clockwork last_triggered condition: last_triggered is not a datetime object: {type(last_triggered)}")
                    return False

                now = dt_util.utcnow()
                _LOGGER.debug(f"[LAST_TRIGGERED] Current time (utcnow): {now}")

                delta = now - last_triggered
                _LOGGER.debug(f"[LAST_TRIGGERED] Time delta: {delta}")

                seconds_since_trigger = int(delta.total_seconds())
                _LOGGER.debug(f"[LAST_TRIGGERED] Seconds since last trigger: {seconds_since_trigger}")

                _LOGGER.debug(
                    f"Clockwork last_triggered: entity={entity_id}, "
                    f"seconds_since_trigger={seconds_since_trigger}, "
                    f"config={self.config}"
                )

                # Check comparisons
                if "above" in options:
                    threshold = options["above"]
                    result = seconds_since_trigger > threshold
                    _LOGGER.debug(f"[LAST_TRIGGERED] above check: {seconds_since_trigger} > {threshold} = {result}")
                    return result

                if "below" in options:
                    threshold = options["below"]
                    result = seconds_since_trigger < threshold
                    _LOGGER.debug(f"[LAST_TRIGGERED] below check: {seconds_since_trigger} < {threshold} = {result}")
                    return result

                if "equal_to" in options:
                    threshold = options["equal_to"]
                    result = seconds_since_trigger == threshold
                    _LOGGER.debug(f"[LAST_TRIGGERED] equal_to check: {seconds_since_trigger} == {threshold} = {result}")
                    return result

                # Should not reach here due to schema validation
                _LOGGER.error(f"[LAST_TRIGGERED] No comparison operator found in options: {options}")
                return False

            except Exception as e:
                _LOGGER.error(f"[LAST_TRIGGERED] Unexpected error evaluating condition: {e}")
                return False

        return checker