"""Clockwork timespan automation condition."""
import logging

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


class TimespanCondition(Condition):
    """Home Assistant automation condition for clockwork.timespan.
    
    Checks how long it's been since an entity last changed state.
    """

    def __init__(self, hass: HomeAssistant, config: ConfigType) -> None:
        """Initialize the condition."""
        self._hass = hass
        self.config = config
        _LOGGER.debug(f"[TIMESPAN] __init__ called with config: {config}")

    @classmethod
    async def async_validate_config(
        cls, hass: HomeAssistant, config: ConfigType
    ) -> ConfigType:
        """Validate the condition configuration (abstract method implementation)."""
        _LOGGER.debug(f"[TIMESPAN] async_validate_config called with: {config}")
        return CONDITION_SCHEMA(config)

    @classmethod
    async def async_validate_complete_config(
        cls, hass: HomeAssistant, complete_config: ConfigType
    ) -> ConfigType:
        """Validate the complete condition configuration.
        
        This validates the condition config with the proper schema.
        """
        _LOGGER.debug(f"[TIMESPAN] async_validate_complete_config called with: {complete_config}")
        
        # Validate with schema that expects options
        validated = await cls.async_validate_config(hass, complete_config)
        _LOGGER.debug(f"[TIMESPAN] async_validate_complete_config validated: {validated}")
        return validated

    async def async_get_checker(self) -> ConditionChecker:
        """Return the checker function for this condition.
        
        Home Assistant calls this and expects to get a callable that takes **kwargs.
        The checker should accept 'variables' as a kwarg.
        """
        _LOGGER.debug(f"[TIMESPAN] async_get_checker called, creating checker function")
        _LOGGER.debug(f"[TIMESPAN] self.config type: {type(self.config)}, value: {self.config}")
        
        # Extract options from ConditionConfig object
        # ConditionConfig has .options attribute with field values
        if isinstance(self.config, dict):
            options = self.config.get(CONF_OPTIONS, {})
        else:
            # ConditionConfig object with .options attribute
            options = self.config.options if hasattr(self.config, 'options') else {}
        
        _LOGGER.debug(f"[TIMESPAN] Extracted options: {options}")
        
        # Create a synchronous checker function that takes **kwargs
        def checker(**kwargs) -> bool:
            """Check the timespan condition.
            
            Home Assistant automation system will call this with variables=... kwargs.
            """
            _LOGGER.debug(f"[TIMESPAN] *** CHECKER CALLED *** with kwargs={kwargs}")
            variables = kwargs.get('variables')
            _LOGGER.debug(f"[TIMESPAN] Checker called with variables={variables}")
            
            entity_id = options.get("entity_id")
            _LOGGER.debug(f"[TIMESPAN] Evaluating condition for entity_id: {entity_id}")
            
            try:
                if not entity_id or not isinstance(entity_id, str):
                    _LOGGER.warning(f"Invalid entity_id in timespan condition: {entity_id}")
                    return False
                state = self._hass.states.get(entity_id)
                if state is None:
                    _LOGGER.warning(f"Clockwork timespan condition: Entity '{entity_id}' not found")
                    _LOGGER.debug(f"[TIMESPAN] {entity_id} not found, returning False")
                    return False
                
                _LOGGER.debug(f"[TIMESPAN] Retrieved state for {entity_id}: {state}")
                _LOGGER.debug(f"[TIMESPAN] State object: state={state.state}, attributes={state.attributes}")
                _LOGGER.debug(f"[TIMESPAN] State last_changed: {state.last_changed}")
                _LOGGER.debug(f"[TIMESPAN] State last_updated: {state.last_updated}")
                
                if state.last_changed is None:
                    _LOGGER.warning(
                        f"Clockwork timespan condition: Entity '{entity_id}' has no last_changed time. "
                        "Condition evaluates to False."
                    )
                    _LOGGER.debug(f"[TIMESPAN] {entity_id} has no last_changed, returning False")
                    return False
                
                now = dt_util.utcnow()
                _LOGGER.debug(f"[TIMESPAN] Current time (utcnow): {now}")
                
                delta = now - state.last_changed
                _LOGGER.debug(f"[TIMESPAN] Time delta: {delta}")
                
                seconds_since_change = int(delta.total_seconds())
                _LOGGER.debug(f"[TIMESPAN] Seconds since change: {seconds_since_change}")
                
                _LOGGER.debug(
                    f"Clockwork timespan: entity={entity_id}, "
                    f"seconds_since_change={seconds_since_change}, "
                    f"config={self.config}"
                )
                
                # Evaluate every operator that was supplied and require all of
                # them. The schema allows more than one, and the visual editor
                # offers all three, so "above 60 and below 300" must mean
                # between -- previously only the first operator was honoured and
                # the rest were silently ignored.
                checks = []
                if options.get("above") is not None:
                    result = seconds_since_change > options["above"]
                    _LOGGER.debug(f"[TIMESPAN] above check: {seconds_since_change} > {options['above']} = {result}")
                    checks.append(result)

                if options.get("below") is not None:
                    result = seconds_since_change < options["below"]
                    _LOGGER.debug(f"[TIMESPAN] below check: {seconds_since_change} < {options['below']} = {result}")
                    checks.append(result)

                if options.get("equal_to") is not None:
                    result = seconds_since_change == options["equal_to"]
                    _LOGGER.debug(f"[TIMESPAN] equal_to check: {seconds_since_change} == {options['equal_to']} = {result}")
                    checks.append(result)

                if not checks:
                    # No operator specified: entity exists and has last_changed
                    _LOGGER.debug("[TIMESPAN] No comparison operator specified, returning True")
                    return True

                overall = all(checks)
                _LOGGER.debug(f"[TIMESPAN] Condition result ({len(checks)} operator(s)): {overall}")
                return overall
                
            except Exception as e:
                _LOGGER.error(f"[TIMESPAN] Error evaluating condition: {e}", exc_info=True)
                return False
        
        return checker

    async def _async_check(self, **kwargs) -> bool:
        """Compatibility check entry point for newer Home Assistant versions."""
        checker = await self.async_get_checker()
        return checker(**kwargs)



    
# For backwards compatibility and testing, keep the function form
async def async_if_action(
    hass: HomeAssistant, condition_config: ConfigType, variables=None
) -> bool:
    """Function form of the condition - called by tests and direct usage."""
    _LOGGER.debug(f"[TIMESPAN] async_if_action function called with config: {condition_config}")
    condition = TimespanCondition(hass, condition_config)
    checker = await condition.async_get_checker()
    return checker(variables=variables) if variables else checker()


# Standard Home Assistant condition function name
if_action = async_if_action



