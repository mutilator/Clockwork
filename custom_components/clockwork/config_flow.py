"""Config flow for Clockwork integration."""
import logging
import re
from typing import Any, Dict, Optional, Tuple, cast

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
import voluptuous as vol

from .utils import validate_offset_string
from .const import (
    DOMAIN, 
    CONF_CALCULATIONS,
    CALC_TYPE_TIMESPAN,
    CALC_TYPE_OFFSET,
    CALC_TYPE_DATETIME_OFFSET,
    CALC_TYPE_DATE_RANGE,
    CALC_TYPE_SEASON,
    CALC_TYPE_MONTH,
    CALC_TYPE_HOLIDAY,
    CALC_TYPE_BETWEEN_DATES,
    CALC_TYPE_OUTSIDE_DATES,
)

_LOGGER = logging.getLogger(__name__)


def _generate_holiday_key(name: str) -> str:
    """Generate a safe holiday key identifier from a name.
    
    Args:
        name: The holiday name
    
    Returns:
        A safe identifier (lowercase, underscores, no special chars)
    """
    # Convert to lowercase
    key = name.lower()
    # Replace spaces with underscores
    key = key.replace(" ", "_")
    # Remove any special characters except underscores
    key = re.sub(r"[^a-z0-9_]", "", key)
    # Replace multiple underscores with single underscore
    key = re.sub(r"_+", "_", key)
    # Remove leading/trailing underscores
    key = key.strip("_")
    return key


class ClockworkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Clockwork."""

    VERSION = 1

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(
                title=user_input.get("name", "Clockwork"),
                data={CONF_CALCULATIONS: []}
            )

        data_schema = vol.Schema({
            vol.Optional("name", default="Clockwork"): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
        )

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        return ClockworkOptionsFlowHandler()


class ClockworkOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Clockwork options."""

    def __init__(self):
        """Initialize the options flow."""
        self._selected_calc_index: Optional[int] = None
        self._selected_holiday_index: Optional[int] = None

    def _validate_entities_exist(self, calc_type: str, user_input: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate that referenced entities exist in the entity registry.
        
        Args:
            calc_type: The calculation type
            user_input: The user input containing entity references
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        from homeassistant.helpers import entity_registry as er
        
        entity_registry = er.async_get(self.hass)
        entity_map = {entity.entity_id: entity for entity in entity_registry.entities.values()}
        
        # Define which fields contain entity_id references by calculation type
        entity_fields = {
            CALC_TYPE_TIMESPAN: ["entity_id"],
            CALC_TYPE_OFFSET: ["entity_id"],
            CALC_TYPE_DATETIME_OFFSET: ["datetime_entity"],
            CALC_TYPE_DATE_RANGE: ["start_datetime_entity", "end_datetime_entity"],
            CALC_TYPE_SEASON: [],  # No entity dependencies
            CALC_TYPE_MONTH: [],  # No entity dependencies
            CALC_TYPE_HOLIDAY: [],  # No entity dependencies
            CALC_TYPE_BETWEEN_DATES: ["start_datetime_entity", "end_datetime_entity"],
            CALC_TYPE_OUTSIDE_DATES: ["start_datetime_entity", "end_datetime_entity"],
        }
        
        fields_to_check = entity_fields.get(calc_type, [])
        missing_entities = []
        
        for field in fields_to_check:
            entity_id = user_input.get(field, "")
            if entity_id and entity_id not in entity_map:
                missing_entities.append(entity_id)
        
        if missing_entities:
            # Build helpful error message with available entities
            sensor_entities = [e for e in entity_map if e.startswith("sensor.") or e.startswith("binary_sensor.")]
            available_sample = ", ".join(sensor_entities[:5])
            if len(sensor_entities) > 5:
                available_sample += f", ... ({len(sensor_entities)} total available)"
            
            return False, f"Entity(ies) not found: {', '.join(missing_entities)}. Available examples: {available_sample}"
        
        return True, None

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None):
        """Manage the options - show main menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options={
                "add_calculation": "Add Calculation",
                "modify_calculation": "Modify Calculation",
                "delete_calculation": "Delete Calculation",
                "custom_holiday": "Add Custom Holiday",
                "modify_custom_holiday": "Modify Custom Holiday",
                "delete_custom_holiday": "Delete Custom Holiday",
            },
        )

    async def async_step_add_calculation(self, user_input: Optional[Dict[str, Any]] = None):
        """Show submenu for adding different calculation types."""
        return self.async_show_menu(
            step_id="add_calculation",
            menu_options={
                "timespan": "Timespan Calculation",
                "offset": "Offset Calculation",
                "datetime_offset": "Datetime Offset",
                "date_range": "Date Range Duration",
                "season": "Season Detection",
                "month": "Month Detection",
                "holiday": "Holiday Countdown",
                "between_dates": "Between Dates Check",
                "outside_dates": "Outside Dates Check",
            },
        )

    async def async_step_modify_calculation(self, user_input: Optional[Dict[str, Any]] = None):
        """Select a calculation to modify."""
        # Get existing calculations
        calculations = self.config_entry.options.get(
            CONF_CALCULATIONS,
            self.config_entry.data.get(CONF_CALCULATIONS, [])
        )
        
        if not calculations:
            return self.async_abort(reason="no_calculations")
        
        if user_input is not None:
            self._selected_calc_index = int(user_input["calc_index"])
            calc = calculations[self._selected_calc_index]
            calc_type = calc.get("type")
            
            # Redirect to the appropriate modify step based on calculation type
            return await self.async_step_modify_by_type(calc_type)
        
        # Build options for SelectSelector - shows friendly names
        options = []
        for i, calc in enumerate(calculations):
            calc_type = calc.get("type", "unknown")
            name = calc.get("name", f"Calculation {i+1}")
            options.append(selector.SelectOptionDict(
                value=str(i),
                label=f"{name} ({calc_type})"
            ))
        
        data_schema = vol.Schema({
            vol.Required("calc_index"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options)
            ),
        })
        
        return self.async_show_form(
            step_id="modify_calculation",
            data_schema=data_schema,
            description_placeholders={
                "info": "Select a calculation to modify"
            }
        )

    async def async_step_modify_by_type(self, calc_type: str):
        """Route to the correct modify step based on calculation type."""
        calculations = self.config_entry.options.get(
            CONF_CALCULATIONS,
            self.config_entry.data.get(CONF_CALCULATIONS, [])
        )
        calc = calculations[self._selected_calc_index]
        
        if calc_type == CALC_TYPE_TIMESPAN:
            return await self.async_step_modify_timespan()
        elif calc_type == CALC_TYPE_OFFSET:
            return await self.async_step_modify_offset()
        elif calc_type == CALC_TYPE_DATETIME_OFFSET:
            return await self.async_step_modify_datetime_offset()
        elif calc_type == CALC_TYPE_DATE_RANGE:
            return await self.async_step_modify_date_range()
        elif calc_type == CALC_TYPE_SEASON:
            return await self.async_step_modify_season()
        elif calc_type == CALC_TYPE_MONTH:
            return await self.async_step_modify_month()
        elif calc_type == CALC_TYPE_HOLIDAY:
            return await self.async_step_modify_holiday()
        elif calc_type == CALC_TYPE_BETWEEN_DATES:
            return await self.async_step_modify_between_dates()
        elif calc_type == CALC_TYPE_OUTSIDE_DATES:
            return await self.async_step_modify_outside_dates()
        else:
            return self.async_abort(reason="unsupported_calculation_type")

    async def async_step_timespan(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle timespan calculation."""
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("entity_id"):
                errors["base"] = "missing_entity_id"
            elif (interval := user_input.get("update_interval")) is not None and interval <= 0:
                errors["update_interval"] = "interval_positive"
            else:
                # Validate that the referenced entity exists
                is_valid, error_msg = self._validate_entities_exist(CALC_TYPE_TIMESPAN, user_input)
                if not is_valid:
                    errors["entity_id"] = "entity_not_found"
                    description_placeholder = {"error": error_msg}
                    return self.async_show_form(
                        step_id="timespan",
                        data_schema=data_schema,
                        errors=errors,
                        description_placeholders=description_placeholder
                    )
                return await self._save_calculation(
                    CALC_TYPE_TIMESPAN,
                    user_input
                )

        data_schema = vol.Schema({
            vol.Required("name"): str,
            vol.Required("entity_id"): selector.EntitySelector(),
            vol.Optional("track_state", default="on"): vol.In(["on", "off", "both"]),
            vol.Optional("update_interval", default=60): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional("icon"): str,
        })

        return self.async_show_form(
            step_id="timespan",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "example": "e.g., 'binary_sensor.front_door'",
                "track_state_help": "Which state to track: 'on' (turns ON), 'off' (turns OFF), or 'both' (any state change)",
                "update_interval_help": "How often to update the timespan value (in seconds). Minimum 1 second. Default: 60 seconds."
            }
        )

    async def async_step_modify_timespan(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle modifying a timespan calculation."""
        # Get existing calculation
        calculations = self.config_entry.options.get(
            CONF_CALCULATIONS,
            self.config_entry.data.get(CONF_CALCULATIONS, [])
        )
        existing_calc = calculations[self._selected_calc_index]
        
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("entity_id"):
                errors["base"] = "missing_entity_id"
            elif (interval := user_input.get("update_interval")) is not None and interval <= 0:
                errors["update_interval"] = "interval_positive"
            else:
                assert self._selected_calc_index is not None
                return await self._update_calculation(
                    self._selected_calc_index,
                    CALC_TYPE_TIMESPAN,
                    user_input
                )

        # Pre-populate with existing values
        data_schema = vol.Schema({
            vol.Required("name", default=existing_calc.get("name", "")): str,
            vol.Required("entity_id", default=existing_calc.get("entity_id", "")): selector.EntitySelector(),
            vol.Optional("track_state", default=existing_calc.get("track_state", "on")): vol.In(["on", "off", "both"]),
            vol.Optional("update_interval", default=existing_calc.get("update_interval", 60)): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional("icon", default=existing_calc.get("icon", "")): str,
        })

        return self.async_show_form(
            step_id="modify_timespan",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "example": "e.g., 'binary_sensor.front_door'",
                "track_state_help": "Which state to track: 'on' (turns ON), 'off' (turns OFF), or 'both' (any state change)",
                "update_interval_help": "How often to update the timespan value (in seconds). Minimum 1 second. Default: 60 seconds."
            }
        )

    async def async_step_offset(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle offset calculation."""
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("entity_id"):
                errors["base"] = "missing_entity_id"
            elif not user_input.get("offset"):
                errors["base"] = "missing_offset"
            else:
                # Validate offset format
                is_valid, error_msg = validate_offset_string(user_input["offset"])
                if not is_valid:
                    errors["offset"] = "invalid_offset_format"
                elif not user_input.get("offset_mode"):
                    errors["base"] = "missing_offset_mode"
                elif user_input.get("offset_mode") == "pulse":
                    pulse_duration = user_input.get("pulse_duration")
                    if not pulse_duration:
                        errors["base"] = "missing_pulse_duration"
                    else:
                        is_valid, _ = validate_offset_string(pulse_duration)
                        if not is_valid:
                            errors["pulse_duration"] = "invalid_offset_format"
                elif not user_input.get("trigger_on"):
                    errors["base"] = "missing_trigger_on"
                
                if not errors:
                    # Validate that the referenced entity exists
                    is_valid, error_msg = self._validate_entities_exist(CALC_TYPE_OFFSET, user_input)
                    if not is_valid:
                        errors["entity_id"] = "entity_not_found"
                        description_placeholder = {"error": error_msg}
                        return self.async_show_form(
                            step_id="offset",
                            data_schema=data_schema,
                            errors=errors,
                            description_placeholders=description_placeholder
                        )
                    return await self._save_calculation(
                        CALC_TYPE_OFFSET,
                        user_input
                    )

        data_schema = vol.Schema({
            vol.Required("name"): str,
            vol.Required("entity_id"): selector.EntitySelector(),
            vol.Required("offset"): str,
            vol.Required("offset_mode", default="latch"): vol.In(["pulse", "duration", "latch"]),
            vol.Optional("pulse_duration"): str,
            vol.Required("trigger_on", default="on"): vol.In(["on", "off", "both"]),
            vol.Optional("icon"): str,
        })

        return self.async_show_form(
            step_id="offset",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "offset_example": "e.g., '1 hour', '30 minutes'"
            }
        )

    async def async_step_datetime_offset(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle datetime offset calculation."""
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("datetime_entity"):
                errors["base"] = "missing_entity_id"
            elif not user_input.get("offset"):
                errors["base"] = "missing_offset"
            else:
                # Validate offset format
                is_valid, error_msg = validate_offset_string(user_input["offset"])
                if not is_valid:
                    errors["offset"] = "invalid_offset_format"
                else:
                    # Validate that the referenced entity exists
                    is_valid, error_msg = self._validate_entities_exist(CALC_TYPE_DATETIME_OFFSET, user_input)
                    if not is_valid:
                        errors["datetime_entity"] = "entity_not_found"
                        description_placeholder = {"error": error_msg}
                        return self.async_show_form(
                            step_id="datetime_offset",
                            data_schema=data_schema,
                            errors=errors,
                            description_placeholders=description_placeholder
                        )
                    return await self._save_calculation(
                        CALC_TYPE_DATETIME_OFFSET,
                        user_input
                    )

        data_schema = vol.Schema({
            vol.Required("name"): str,
            vol.Required("datetime_entity"): selector.EntitySelector(
                {"filter": {"domain": ["time", "calendar", "input_datetime", "sensor"], "device_class": ["date", "timestamp"]}}
            ),
            vol.Required("offset"): str,
            vol.Optional("icon"): str,
        })

        return self.async_show_form(
            step_id="datetime_offset",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "entity_example": "e.g., 'input_datetime.event_start'",
                "offset_example": "e.g., '1 hour', '-30 minutes'"
            }
        )

    async def async_step_date_range(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle date range calculation."""
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("start_datetime_entity"):
                errors["base"] = "missing_start_entity"
            elif not user_input.get("end_datetime_entity"):
                errors["base"] = "missing_end_entity"
            else:
                # Validate that the referenced entities exist
                is_valid, error_msg = self._validate_entities_exist(CALC_TYPE_DATE_RANGE, user_input)
                if not is_valid:
                    errors["base"] = "entity_not_found"
                    description_placeholder = {"error": error_msg}
                    return self.async_show_form(
                        step_id="date_range",
                        data_schema=data_schema,
                        errors=errors,
                        description_placeholders=description_placeholder
                    )
                return await self._save_calculation(
                    CALC_TYPE_DATE_RANGE,
                    user_input
                )

        data_schema = vol.Schema({
            vol.Required("name"): str,
            vol.Required("start_datetime_entity"): selector.EntitySelector(
                {"filter": {"domain": ["time", "calendar", "input_datetime", "sensor"]}}
            ),
            vol.Required("end_datetime_entity"): selector.EntitySelector(
                {"filter": {"domain": ["time", "calendar", "input_datetime", "sensor"]}}
            ),
            vol.Optional("icon"): str,
        })

        return self.async_show_form(
            step_id="date_range",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_season(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle season calculation."""
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("season"):
                errors["base"] = "missing_season"
            elif user_input.get("season") not in ["spring", "summer", "autumn", "winter"]:
                errors["season"] = "invalid_season"
            else:
                return await self._save_calculation(
                    CALC_TYPE_SEASON,
                    user_input
                )

        data_schema = vol.Schema({
            vol.Required("name"): str,
            vol.Required("season"): vol.In(["spring", "summer", "autumn", "winter"]),
            vol.Required("hemisphere", default="northern"): vol.In(["northern", "southern"]),
            vol.Optional("icon"): str,
        })

        return self.async_show_form(
            step_id="season",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_month(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle month calculation."""
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("months"):
                errors["base"] = "missing_months"
            else:
                return await self._save_calculation(
                    CALC_TYPE_MONTH,
                    user_input
                )

        data_schema = vol.Schema({
            vol.Required("name"): str,
            vol.Required("months"): str,
            vol.Optional("icon"): str,
        })

        return self.async_show_form(
            step_id="month",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "example": "e.g., '12,1,2' for December, January, February"
            }
        )

    async def async_step_holiday(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle holiday calculation."""
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("holiday"):
                errors["base"] = "missing_holiday"
            else:
                return await self._save_calculation(
                    CALC_TYPE_HOLIDAY,
                    user_input
                )

        holidays = [
            "new_years_day",
            "mlk_day",
            "presidents_day",
            "memorial_day",
            "juneteenth",
            "independence_day",
            "labor_day",
            "columbus_day",
            "veterans_day",
            "thanksgiving",
            "christmas",
        ]
        
        # Add custom holidays to the list
        custom_holidays = self.config_entry.options.get("custom_holidays", [])
        for custom_holiday in custom_holidays:
            holiday_key = custom_holiday.get("key")
            if holiday_key and holiday_key not in holidays:
                holidays.append(holiday_key)

        data_schema = vol.Schema({
            vol.Required("name"): str,
            vol.Required("holiday"): vol.In(holidays),
            vol.Optional("offset", default=0): vol.Coerce(int),
            vol.Optional("icon"): str,
        })

        return self.async_show_form(
            step_id="holiday",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "holiday_help": "Select a preset holiday, or define a custom date using 'Add Custom Holiday' option, then reference it here."
            }
        )

    async def async_step_between_dates(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle between dates calculation."""
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("start_datetime_entity"):
                errors["base"] = "missing_start_entity"
            elif not user_input.get("end_datetime_entity"):
                errors["base"] = "missing_end_entity"
            else:
                # Validate that the referenced entities exist
                is_valid, error_msg = self._validate_entities_exist(CALC_TYPE_BETWEEN_DATES, user_input)
                if not is_valid:
                    errors["base"] = "entity_not_found"
                    description_placeholder = {"error": error_msg}
                    return self.async_show_form(
                        step_id="between_dates",
                        data_schema=data_schema,
                        errors=errors,
                        description_placeholders=description_placeholder
                    )
                return await self._save_calculation(
                    CALC_TYPE_BETWEEN_DATES,
                    user_input
                )

        data_schema = vol.Schema({
            vol.Required("name"): str,
            vol.Required("start_datetime_entity"): selector.EntitySelector(
                {"filter": {"domain": ["time", "calendar", "input_datetime", "sensor"], "device_class": ["date", "timestamp"]}}
            ),
            vol.Required("end_datetime_entity"): selector.EntitySelector(
                {"filter": {"domain": ["time", "calendar", "input_datetime", "sensor"], "device_class": ["date", "timestamp"]}}
            ),
            vol.Optional("icon"): str,
        })

        return self.async_show_form(
            step_id="between_dates",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_outside_dates(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle outside dates calculation."""
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("start_datetime_entity"):
                errors["base"] = "missing_start_entity"
            elif not user_input.get("end_datetime_entity"):
                errors["base"] = "missing_end_entity"
            else:
                # Validate that the referenced entities exist
                is_valid, error_msg = self._validate_entities_exist(CALC_TYPE_OUTSIDE_DATES, user_input)
                if not is_valid:
                    errors["base"] = "entity_not_found"
                    description_placeholder = {"error": error_msg}
                    return self.async_show_form(
                        step_id="outside_dates",
                        data_schema=data_schema,
                        errors=errors,
                        description_placeholders=description_placeholder
                    )
                return await self._save_calculation(
                    CALC_TYPE_OUTSIDE_DATES,
                    user_input
                )

        data_schema = vol.Schema({
            vol.Required("name"): str,
            vol.Required("start_datetime_entity"): selector.EntitySelector(
                {"filter": {"domain": ["time", "calendar", "input_datetime", "sensor"], "device_class": ["date", "timestamp"]}}
            ),
            vol.Required("end_datetime_entity"): selector.EntitySelector(
                {"filter": {"domain": ["time", "calendar", "input_datetime", "sensor"], "device_class": ["date", "timestamp"]}}
            ),
            vol.Optional("icon"): str,
        })

        return self.async_show_form(
            step_id="outside_dates",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_custom_holiday(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle custom holiday definition."""
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("holiday_type"):
                errors["base"] = "missing_holiday_type"
            else:
                # Validate type-specific fields
                holiday_type = user_input.get("holiday_type")
                try:
                    month = int(user_input.get("month", 0)) if user_input.get("month") else 0
                    if holiday_type == "fixed":
                        day_val = user_input.get("day")
                        day = int(day_val) if day_val is not None else 0
                        if not (1 <= month <= 12) or not (1 <= day <= 31):
                            errors["base"] = "invalid_fixed_date"
                    elif holiday_type == "nth_weekday":
                        occurrence_val = user_input.get("occurrence")
                        occurrence = int(occurrence_val) if occurrence_val is not None else 0
                        weekday_val = user_input.get("weekday")
                        weekday = int(weekday_val) if weekday_val is not None else -1
                        if not (1 <= month <= 12) or not (1 <= occurrence <= 5) or not (0 <= weekday <= 6):
                            errors["base"] = "invalid_nth_weekday"
                    elif holiday_type == "last_weekday":
                        weekday_val = user_input.get("weekday")
                        weekday = int(weekday_val) if weekday_val is not None else -1
                        if not (1 <= month <= 12) or not (0 <= weekday <= 6):
                            errors["base"] = "invalid_last_weekday"
                except (ValueError, TypeError):
                    errors["base"] = "invalid_number_format"
                
                if not errors:
                    return await self._save_custom_holiday(user_input)

        data_schema = vol.Schema({
            vol.Required("name"): str,
            vol.Required("holiday_type"): vol.In(["fixed", "nth_weekday", "last_weekday"]),
            vol.Required("month"): vol.All(vol.Coerce(int), vol.Range(min=1, max=12)),
            vol.Optional("day"): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1, max=31))),
            vol.Optional("occurrence"): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1, max=5))),
            vol.Optional("weekday"): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=0, max=6))),
        })

        return self.async_show_form(
            step_id="custom_holiday",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "name_help": "e.g., 'Easter Sunday' or 'My Birthday' (the identifier will be created automatically)",
                "weekday_help": "0=Monday, 1=Tuesday, ... 6=Sunday"
            }
        )

    async def async_step_modify_custom_holiday(self, user_input: Optional[Dict[str, Any]] = None):
        """Select a custom holiday to modify."""
        # Get existing custom holidays
        custom_holidays = self.config_entry.options.get("custom_holidays", [])
        
        if not custom_holidays:
            return self.async_abort(reason="no_custom_holidays")
        
        if user_input is not None:
            self._selected_holiday_index = int(user_input["holiday_index"])
            holiday = custom_holidays[self._selected_holiday_index]
            return await self.async_step_modify_custom_holiday_form()
        
        # Build options for SelectSelector - shows friendly names
        options = []
        for i, holiday in enumerate(custom_holidays):
            name = holiday.get("name", f"Holiday {i+1}")
            key = holiday.get("key", "unknown")
            options.append(selector.SelectOptionDict(
                value=str(i),
                label=f"{name} ({key})"
            ))
        
        data_schema = vol.Schema({
            vol.Required("holiday_index"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options)
            ),
        })
        
        return self.async_show_form(
            step_id="modify_custom_holiday",
            data_schema=data_schema,
            description_placeholders={
                "info": "Select a custom holiday to modify"
            }
        )

    async def async_step_modify_custom_holiday_form(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle modifying a custom holiday definition."""
        # Get existing custom holiday
        custom_holidays = self.config_entry.options.get("custom_holidays", [])
        existing_holiday = custom_holidays[self._selected_holiday_index]
        
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("holiday_type"):
                errors["base"] = "missing_holiday_type"
            else:
                # Validate type-specific fields
                holiday_type = user_input.get("holiday_type")
                try:
                    month = int(user_input.get("month", 0)) if user_input.get("month") else 0
                    if holiday_type == "fixed":
                        day_val = user_input.get("day")
                        day = int(day_val) if day_val is not None else 0
                        if not (1 <= month <= 12) or not (1 <= day <= 31):
                            errors["base"] = "invalid_fixed_date"
                    elif holiday_type == "nth_weekday":
                        occurrence_val = user_input.get("occurrence")
                        occurrence = int(occurrence_val) if occurrence_val is not None else 0
                        weekday_val = user_input.get("weekday")
                        weekday = int(weekday_val) if weekday_val is not None else -1
                        if not (1 <= month <= 12) or not (1 <= occurrence <= 5) or not (0 <= weekday <= 6):
                            errors["base"] = "invalid_nth_weekday"
                    elif holiday_type == "last_weekday":
                        weekday_val = user_input.get("weekday")
                        weekday = int(weekday_val) if weekday_val is not None else -1
                        if not (1 <= month <= 12) or not (0 <= weekday <= 6):
                            errors["base"] = "invalid_last_weekday"
                except (ValueError, TypeError):
                    errors["base"] = "invalid_number_format"
                
                if not errors:
                    assert self._selected_holiday_index is not None
                    return await self._update_custom_holiday(self._selected_holiday_index, user_input)

        data_schema = vol.Schema({
            vol.Required("name", default=existing_holiday.get("name", "")): str,
            vol.Required("holiday_type", default=existing_holiday.get("type", "fixed")): vol.In(["fixed", "nth_weekday", "last_weekday"]),
            vol.Required("month", default=existing_holiday.get("month", 1)): vol.All(vol.Coerce(int), vol.Range(min=1, max=12)),
            vol.Optional("day", default=existing_holiday.get("day")): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1, max=31))),
            vol.Optional("occurrence", default=existing_holiday.get("occurrence")): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1, max=5))),
            vol.Optional("weekday", default=existing_holiday.get("weekday")): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=0, max=6))),
        })

        return self.async_show_form(
            step_id="modify_custom_holiday_form",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "name_help": "e.g., 'Easter Sunday' or 'My Birthday' (the identifier will be created automatically)",
                "weekday_help": "0=Monday, 1=Tuesday, ... 6=Sunday"
            }
        )

    async def async_step_delete_custom_holiday(self, user_input: Optional[Dict[str, Any]] = None):
        """Select a custom holiday to delete."""
        # Get existing custom holidays
        custom_holidays = self.config_entry.options.get("custom_holidays", [])
        
        if not custom_holidays:
            return self.async_abort(reason="no_custom_holidays")
        
        if user_input is not None:
            self._selected_holiday_index = int(user_input["holiday_index"])
            return await self.async_step_delete_custom_holiday_confirm()
        
        # Build options for SelectSelector - shows friendly names
        options = []
        for i, holiday in enumerate(custom_holidays):
            name = holiday.get("name", f"Holiday {i+1}")
            key = holiday.get("key", "unknown")
            options.append(selector.SelectOptionDict(
                value=str(i),
                label=f"{name} ({key})"
            ))
        
        data_schema = vol.Schema({
            vol.Required("holiday_index"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options)
            ),
        })
        
        return self.async_show_form(
            step_id="delete_custom_holiday",
            data_schema=data_schema,
            description_placeholders={
                "info": "Select a custom holiday to delete (this will remove the holiday definition)"
            }
        )

    async def async_step_delete_custom_holiday_confirm(self, user_input: Optional[Dict[str, Any]] = None):
        """Confirm deletion of a custom holiday."""
        assert self._selected_holiday_index is not None
        if user_input is not None:
            # Get existing custom holidays
            custom_holidays = list(self.config_entry.options.get("custom_holidays", []))
            
            # Get the holiday being deleted before removing it
            holiday_index = cast(int, self._selected_holiday_index)
            if 0 <= holiday_index < len(custom_holidays):
                removed = custom_holidays[holiday_index]
                holiday_name = removed.get('name', f'Holiday {holiday_index + 1}')
                holiday_key = removed.get('key', 'unknown')
                _LOGGER.info(f"Deleting custom holiday: {holiday_name} ({holiday_key})")
                
                # Remove the holiday from the list
                custom_holidays.pop(holiday_index)
            
            # Get existing calculations
            calculations = self.config_entry.options.get(
                CONF_CALCULATIONS,
                self.config_entry.data.get(CONF_CALCULATIONS, [])
            )
            
            # Update config entry options
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options={
                    **self.config_entry.options,
                    CONF_CALCULATIONS: calculations,
                    "custom_holidays": custom_holidays
                }
            )
            
            # Reload the integration immediately
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            
            # Return to main menu
            return await self.async_step_init()
        
        # Get the holiday being deleted
        custom_holidays = self.config_entry.options.get("custom_holidays", [])
        holiday_index = self._selected_holiday_index
        holiday = custom_holidays[holiday_index] if holiday_index < len(custom_holidays) else None
        
        return self.async_show_form(
            step_id="delete_custom_holiday_confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "name": holiday.get("name", "Unknown") if holiday else "Unknown",
                "key": holiday.get("key", "unknown") if holiday else "unknown"
            }
        )

    async def async_step_modify_offset(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle modifying an offset calculation."""
        # Get existing calculation
        calculations = self.config_entry.options.get(
            CONF_CALCULATIONS,
            self.config_entry.data.get(CONF_CALCULATIONS, [])
        )
        existing_calc = calculations[self._selected_calc_index]
        
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("entity_id"):
                errors["base"] = "missing_entity_id"
            elif not user_input.get("offset"):
                errors["base"] = "missing_offset"
            else:
                is_valid, error_msg = validate_offset_string(user_input["offset"])
                if not is_valid:
                    errors["offset"] = "invalid_offset_format"
                elif not user_input.get("offset_mode"):
                    errors["base"] = "missing_offset_mode"
                elif user_input.get("offset_mode") == "pulse":
                    pulse_duration = user_input.get("pulse_duration")
                    if not pulse_duration:
                        errors["base"] = "missing_pulse_duration"
                    else:
                        is_valid, _ = validate_offset_string(pulse_duration)
                        if not is_valid:
                            errors["pulse_duration"] = "invalid_offset_format"
                elif not user_input.get("trigger_on"):
                    errors["base"] = "missing_trigger_on"
                
                if not errors:
                    assert self._selected_calc_index is not None
                    return await self._update_calculation(
                        self._selected_calc_index,
                        CALC_TYPE_OFFSET,
                        user_input
                    )

        data_schema = vol.Schema({
            vol.Required("name", default=existing_calc.get("name", "")): str,
            vol.Required("entity_id", default=existing_calc.get("entity_id", "")): selector.EntitySelector(),
            vol.Required("offset", default=existing_calc.get("offset", "")): str,
            vol.Required("offset_mode", default=existing_calc.get("offset_mode", "latch")): vol.In(["pulse", "duration", "latch"]),
            vol.Optional("pulse_duration", default=existing_calc.get("pulse_duration", "")): str,
            vol.Required("trigger_on", default=existing_calc.get("trigger_on", "on")): vol.In(["on", "off", "both"]),
            vol.Optional("icon", default=existing_calc.get("icon", "")): str,
        })

        return self.async_show_form(
            step_id="modify_offset",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "offset_example": "e.g., '1 hour', '30 minutes'"
            }
        )

    async def async_step_modify_datetime_offset(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle modifying a datetime offset calculation."""
        # Get existing calculation
        calculations = self.config_entry.options.get(
            CONF_CALCULATIONS,
            self.config_entry.data.get(CONF_CALCULATIONS, [])
        )
        existing_calc = calculations[self._selected_calc_index]
        
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("datetime_entity"):
                errors["base"] = "missing_entity_id"
            elif not user_input.get("offset"):
                errors["base"] = "missing_offset"
            else:
                is_valid, error_msg = validate_offset_string(user_input["offset"])
                if not is_valid:
                    errors["offset"] = "invalid_offset_format"
                else:
                    assert self._selected_calc_index is not None
                    return await self._update_calculation(
                        self._selected_calc_index,
                        CALC_TYPE_DATETIME_OFFSET,
                        user_input
                    )

        data_schema = vol.Schema({
            vol.Required("name", default=existing_calc.get("name", "")): str,
            vol.Required("datetime_entity", default=existing_calc.get("datetime_entity", "")): selector.EntitySelector(
                {"filter": {"domain": ["time", "calendar", "input_datetime", "sensor"], "device_class": ["date", "timestamp"]}}
            ),
            vol.Required("offset", default=existing_calc.get("offset", "")): str,
            vol.Optional("icon", default=existing_calc.get("icon", "")): str,
        })

        return self.async_show_form(
            step_id="modify_datetime_offset",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "entity_example": "e.g., 'input_datetime.event_start'",
                "offset_example": "e.g., '1 hour', '-30 minutes'"
            }
        )

    async def async_step_modify_date_range(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle modifying a date range calculation."""
        # Get existing calculation
        calculations = self.config_entry.options.get(
            CONF_CALCULATIONS,
            self.config_entry.data.get(CONF_CALCULATIONS, [])
        )
        existing_calc = calculations[self._selected_calc_index]
        
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("start_datetime_entity"):
                errors["base"] = "missing_start_entity"
            elif not user_input.get("end_datetime_entity"):
                errors["base"] = "missing_end_entity"
            else:
                assert self._selected_calc_index is not None
                return await self._update_calculation(
                    self._selected_calc_index,
                    CALC_TYPE_DATE_RANGE,
                    user_input
                )

        data_schema = vol.Schema({
            vol.Required("name", default=existing_calc.get("name", "")): str,
            vol.Required("start_datetime_entity", default=existing_calc.get("start_datetime_entity", "")): selector.EntitySelector(
                {"filter": {"domain": ["time", "calendar", "input_datetime", "sensor"], "device_class": ["date", "timestamp"]}}
            ),
            vol.Required("end_datetime_entity", default=existing_calc.get("end_datetime_entity", "")): selector.EntitySelector(
                {"filter": {"domain": ["time", "calendar", "input_datetime", "sensor"], "device_class": ["date", "timestamp"]}}
            ),
            vol.Optional("icon", default=existing_calc.get("icon", "")): str,
        })

        return self.async_show_form(
            step_id="modify_date_range",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_modify_season(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle modifying a season calculation."""
        # Get existing calculation
        calculations = self.config_entry.options.get(
            CONF_CALCULATIONS,
            self.config_entry.data.get(CONF_CALCULATIONS, [])
        )
        existing_calc = calculations[self._selected_calc_index]
        
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("season"):
                errors["base"] = "missing_season"
            else:
                assert self._selected_calc_index is not None
                return await self._update_calculation(
                    self._selected_calc_index,
                    CALC_TYPE_SEASON,
                    user_input
                )

        data_schema = vol.Schema({
            vol.Required("name", default=existing_calc.get("name", "")): str,
            vol.Required("season", default=existing_calc.get("season", "spring")): vol.In(["spring", "summer", "autumn", "winter"]),
            vol.Required("hemisphere", default=existing_calc.get("hemisphere", "northern")): vol.In(["northern", "southern"]),
            vol.Optional("icon", default=existing_calc.get("icon", "")): str,
        })

        return self.async_show_form(
            step_id="modify_season",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_modify_month(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle modifying a month calculation."""
        # Get existing calculation
        calculations = self.config_entry.options.get(
            CONF_CALCULATIONS,
            self.config_entry.data.get(CONF_CALCULATIONS, [])
        )
        existing_calc = calculations[self._selected_calc_index]
        
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("months"):
                errors["base"] = "missing_months"
            else:
                assert self._selected_calc_index is not None
                return await self._update_calculation(
                    self._selected_calc_index,
                    CALC_TYPE_MONTH,
                    user_input
                )

        data_schema = vol.Schema({
            vol.Required("name", default=existing_calc.get("name", "")): str,
            vol.Required("months", default=existing_calc.get("months", "")): str,
            vol.Optional("icon", default=existing_calc.get("icon", "")): str,
        })

        return self.async_show_form(
            step_id="modify_month",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "example": "e.g., '12,1,2' for December, January, February"
            }
        )

    async def async_step_modify_holiday(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle modifying a holiday calculation."""
        # Get existing calculation
        calculations = self.config_entry.options.get(
            CONF_CALCULATIONS,
            self.config_entry.data.get(CONF_CALCULATIONS, [])
        )
        existing_calc = calculations[self._selected_calc_index]
        
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("holiday"):
                errors["base"] = "missing_holiday"
            else:
                assert self._selected_calc_index is not None
                return await self._update_calculation(
                    self._selected_calc_index,
                    CALC_TYPE_HOLIDAY,
                    user_input
                )

        holidays = [
            "new_years_day",
            "mlk_day",
            "presidents_day",
            "memorial_day",
            "juneteenth",
            "independence_day",
            "labor_day",
            "columbus_day",
            "veterans_day",
            "thanksgiving",
            "christmas",
        ]
        
        # Add custom holidays to the list
        custom_holidays = self.config_entry.options.get("custom_holidays", [])
        for custom_holiday in custom_holidays:
            holiday_key = custom_holiday.get("key")
            if holiday_key and holiday_key not in holidays:
                holidays.append(holiday_key)

        data_schema = vol.Schema({
            vol.Required("name", default=existing_calc.get("name", "")): str,
            vol.Required("holiday", default=existing_calc.get("holiday", "")): vol.In(holidays),
            vol.Optional("offset", default=existing_calc.get("offset", 0)): vol.Coerce(int),
            vol.Optional("icon", default=existing_calc.get("icon", "")): str,
        })

        return self.async_show_form(
            step_id="modify_holiday",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "holiday_help": "Select a preset holiday, or define a custom date using 'Add Custom Holiday' option, then reference it here."
            }
        )

    async def async_step_modify_between_dates(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle modifying a between dates calculation."""
        # Get existing calculation
        calculations = self.config_entry.options.get(
            CONF_CALCULATIONS,
            self.config_entry.data.get(CONF_CALCULATIONS, [])
        )
        existing_calc = calculations[self._selected_calc_index]
        
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("start_datetime_entity"):
                errors["base"] = "missing_start_entity"
            elif not user_input.get("end_datetime_entity"):
                errors["base"] = "missing_end_entity"
            else:
                assert self._selected_calc_index is not None
                return await self._update_calculation(
                    self._selected_calc_index,
                    CALC_TYPE_BETWEEN_DATES,
                    user_input
                )

        data_schema = vol.Schema({
            vol.Required("name", default=existing_calc.get("name", "")): str,
            vol.Required("start_datetime_entity", default=existing_calc.get("start_datetime_entity", "")): selector.EntitySelector(
                {"filter": {"domain": ["time", "calendar", "input_datetime", "sensor"], "device_class": ["date", "timestamp"]}}
            ),
            vol.Required("end_datetime_entity", default=existing_calc.get("end_datetime_entity", "")): selector.EntitySelector(
                {"filter": {"domain": ["time", "calendar", "input_datetime", "sensor"], "device_class": ["date", "timestamp"]}}
            ),
            vol.Optional("icon", default=existing_calc.get("icon", "")): str,
        })

        return self.async_show_form(
            step_id="modify_between_dates",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_modify_outside_dates(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle modifying an outside dates calculation."""
        # Get existing calculation
        calculations = self.config_entry.options.get(
            CONF_CALCULATIONS,
            self.config_entry.data.get(CONF_CALCULATIONS, [])
        )
        existing_calc = calculations[self._selected_calc_index]
        
        errors = {}
        
        if user_input is not None:
            if not user_input.get("name"):
                errors["base"] = "missing_name"
            elif not user_input.get("start_datetime_entity"):
                errors["base"] = "missing_start_entity"
            elif not user_input.get("end_datetime_entity"):
                errors["base"] = "missing_end_entity"
            else:
                assert self._selected_calc_index is not None
                return await self._update_calculation(
                    self._selected_calc_index,
                    CALC_TYPE_OUTSIDE_DATES,
                    user_input
                )

        data_schema = vol.Schema({
            vol.Required("name", default=existing_calc.get("name", "")): str,
            vol.Required("start_datetime_entity", default=existing_calc.get("start_datetime_entity", "")): selector.EntitySelector(
                {"filter": {"domain": ["time", "calendar", "input_datetime", "sensor"], "device_class": ["date", "timestamp"]}}
            ),
            vol.Required("end_datetime_entity", default=existing_calc.get("end_datetime_entity", "")): selector.EntitySelector(
                {"filter": {"domain": ["time", "calendar", "input_datetime", "sensor"], "device_class": ["date", "timestamp"]}}
            ),
            vol.Optional("icon", default=existing_calc.get("icon", "")): str,
        })

        return self.async_show_form(
            step_id="modify_outside_dates",
            data_schema=data_schema,
            errors=errors,
        )

    async def _save_calculation(
        self,
        calc_type: str,
        user_input: Dict[str, Any]
    ):
        """Save the calculation and return to menu."""
        # Get existing calculations - make a copy
        calculations = list(self.config_entry.options.get(
            CONF_CALCULATIONS,
            self.config_entry.data.get(CONF_CALCULATIONS, [])
        ))
        
        # Add new calculation
        calculation = {"type": calc_type}
        calculation.update(user_input)
        calculations.append(calculation)
        
        _LOGGER.debug(f"Saving calculation: {calculation}")
        
        # Update config entry options
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            options={
                **self.config_entry.options,
                CONF_CALCULATIONS: calculations
            }
        )
        
        # Reload the integration immediately to set up the new entity
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        
        # Return to main menu
        return await self.async_step_init()

    async def _update_calculation(
        self,
        calc_index: int,
        calc_type: str,
        user_input: Dict[str, Any]
    ):
        """Update an existing calculation."""
        # Get existing calculations - make a copy
        calculations = list(self.config_entry.options.get(
            CONF_CALCULATIONS,
            self.config_entry.data.get(CONF_CALCULATIONS, [])
        ))
        
        # Update the calculation
        if 0 <= calc_index < len(calculations):
            calculation = {"type": calc_type}
            calculation.update(user_input)
            calculations[calc_index] = calculation
            
            _LOGGER.debug(f"Updating calculation at index {calc_index}: {calculation}")
            
            # Update config entry options
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options={
                    **self.config_entry.options,
                    CONF_CALCULATIONS: calculations
                }
            )
            
            # Reload the integration immediately to update the entity
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        
        # Return to main menu
        return await self.async_step_init()

    async def _update_custom_holiday(self, holiday_index: int, user_input: Dict[str, Any]):
        """Update an existing custom holiday."""
        # Get existing custom holidays - make a copy
        custom_holidays = list(self.config_entry.options.get("custom_holidays", []))
        
        # Update the holiday
        if 0 <= holiday_index < len(custom_holidays):
            # Preserve the original key or generate from name
            original_key = custom_holidays[holiday_index].get("key")
            holiday_name = user_input.get("name", "")
            
            # If name has changed, regenerate key. Otherwise keep original
            if custom_holidays[holiday_index].get("name") != holiday_name:
                holiday_key = _generate_holiday_key(holiday_name)
            else:
                holiday_key = original_key
            
            holiday = {
                "key": holiday_key,
                "name": holiday_name,
                "type": user_input.get("holiday_type"),
            }
            
            # Add type-specific fields
            if user_input.get("month"):
                holiday["month"] = user_input["month"]
            if "day" in user_input:
                holiday["day"] = user_input["day"]
            if "occurrence" in user_input:
                holiday["occurrence"] = user_input["occurrence"]
            if "weekday" in user_input and user_input["weekday"] != "":
                holiday["weekday"] = user_input["weekday"]
            
            custom_holidays[holiday_index] = holiday
            
            _LOGGER.debug(f"Updating custom holiday at index {holiday_index}: {holiday}")
            
            # Get existing calculations
            calculations = self.config_entry.options.get(
                CONF_CALCULATIONS,
                self.config_entry.data.get(CONF_CALCULATIONS, [])
            )
            
            # Update config entry options
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options={
                    **self.config_entry.options,
                    CONF_CALCULATIONS: calculations,
                    "custom_holidays": custom_holidays
                }
            )
            
            # Reload the integration immediately
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        
        # Return to main menu
        return await self.async_step_init()

    async def _save_custom_holiday(self, user_input: Dict[str, Any]):
        """Save a custom holiday definition."""
        # Get existing custom holidays - make a copy
        custom_holidays = list(self.config_entry.options.get("custom_holidays", []))
        
        # Generate safe key from name
        holiday_name = user_input.get("name", "")
        holiday_key = _generate_holiday_key(holiday_name)
        
        # Build holiday object
        holiday = {
            "key": holiday_key,
            "name": holiday_name,
            "type": user_input.get("holiday_type"),
        }
        
        # Add type-specific fields
        if user_input.get("month"):
            holiday["month"] = user_input["month"]
        if "day" in user_input:
            holiday["day"] = user_input["day"]
        if "occurrence" in user_input:
            holiday["occurrence"] = user_input["occurrence"]
        if user_input.get("weekday") is not None:
            holiday["weekday"] = user_input["weekday"]
        
        custom_holidays.append(holiday)
        
        # Get existing calculations
        calculations = self.config_entry.options.get(
            CONF_CALCULATIONS,
            self.config_entry.data.get(CONF_CALCULATIONS, [])
        )
        
        _LOGGER.debug(f"Saving custom holiday: {holiday}")
        
        # Update config entry options
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            options={
                **self.config_entry.options,
                CONF_CALCULATIONS: calculations,
                "custom_holidays": custom_holidays
            }
        )
        
        # Reload the integration immediately
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        
        # Return to main menu
        return await self.async_step_init()

    async def async_step_delete_calculation(self, user_input: Optional[Dict[str, Any]] = None):
        """Select a calculation to delete."""
        # Get existing calculations
        calculations = self.config_entry.options.get(
            CONF_CALCULATIONS,
            self.config_entry.data.get(CONF_CALCULATIONS, [])
        )
        
        if not calculations:
            return self.async_abort(reason="no_calculations")
        
        if user_input is not None:
            self._selected_calc_index = int(user_input["calc_index"])
            return await self.async_step_delete_confirm()
        
        # Build options for SelectSelector - shows friendly names
        options = []
        for i, calc in enumerate(calculations):
            calc_type = calc.get("type", "unknown")
            name = calc.get("name", f"Calculation {i+1}")
            options.append(selector.SelectOptionDict(
                value=str(i),
                label=f"{name} ({calc_type})"
            ))
        
        data_schema = vol.Schema({
            vol.Required("calc_index"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options)
            ),
        })
        
        return self.async_show_form(
            step_id="delete_calculation",
            data_schema=data_schema,
            description_placeholders={
                "info": "Select a calculation to delete (this will remove the entity from Home Assistant)"
            }
        )

    async def async_step_delete_confirm(self, user_input: Optional[Dict[str, Any]] = None):
        """Confirm deletion of a calculation."""
        if user_input is not None:
            # Get existing calculations
            calculations = list(self.config_entry.options.get(
                CONF_CALCULATIONS,
                self.config_entry.data.get(CONF_CALCULATIONS, [])
            ))
            
            # Get the calculation being deleted before removing it
            calc_index = cast(int, self._selected_calc_index)
            if 0 <= calc_index < len(calculations):
                removed = calculations[calc_index]
                calc_name = removed.get('name', f'Calculation {calc_index + 1}')
                calc_type = removed.get('type', 'unknown')
                _LOGGER.info(f"Deleting calculation: {calc_name} ({calc_type})")
                
                # Remove old entities associated with this calculation from registry
                from homeassistant.helpers import entity_registry as er
                entity_registry = er.async_get(self.hass)
                
                # Find and remove entities that were created for this calculation
                # Entities have unique_id in format: domain_entry_id_name_lowercase
                for entity_id, entity in list(entity_registry.entities.items()):
                    if entity.config_entry_id == self.config_entry.entry_id:
                        # Check if this entity's unique_id matches the removed calculation
                        entity_name = calc_name.replace(' ', '_').lower()
                        if entity_name in entity.unique_id:
                            _LOGGER.debug(f"Removing entity: {entity_id}")
                            entity_registry.async_remove(entity_id)
                
                # Remove the calculation from the list
                calculations.pop(calc_index)
            
            # Update config entry options
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options={
                    **self.config_entry.options,
                    CONF_CALCULATIONS: calculations
                }
            )
            
            # Reload the integration immediately
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            
            # Return to main menu
            return await self.async_step_init()
        
        # Get the calculation being deleted
        calculations = self.config_entry.options.get(
            CONF_CALCULATIONS,
            self.config_entry.data.get(CONF_CALCULATIONS, [])
        )
        calc_index = cast(int, self._selected_calc_index)
        calc = calculations[calc_index] if calc_index < len(calculations) else None
        
        return self.async_show_form(
            step_id="delete_confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "name": calc.get("name", "Unknown") if calc else "Unknown",
                "type": calc.get("type", "unknown") if calc else "unknown"
            }
        )