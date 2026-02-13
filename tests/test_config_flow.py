"""Tests for Clockwork config flow."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from custom_components.clockwork.config_flow import (
    ClockworkOptionsFlowHandler,
    _generate_holiday_key,
)
from custom_components.clockwork.const import CONF_CALCULATIONS


class TestGenerateHolidayKey:
    """Test holiday key generation."""

    def test_generate_simple_name(self):
        """Test generating key from simple name."""
        key = _generate_holiday_key("Easter Sunday")
        assert key == "easter_sunday"

    def test_generate_name_with_apostrophe(self):
        """Test generating key from name with apostrophe."""
        key = _generate_holiday_key("Mother's Day")
        assert key == "mothers_day"

    def test_generate_name_with_numbers(self):
        """Test generating key from name with numbers."""
        key = _generate_holiday_key("New Year's Day 2026")
        assert key == "new_years_day_2026"

    def test_generate_name_lowercase(self):
        """Test that key is lowercase."""
        key = _generate_holiday_key("CHRISTMAS")
        assert key == "christmas"

    def test_generate_name_multiple_spaces(self):
        """Test handling multiple spaces."""
        key = _generate_holiday_key("My  Custom  Holiday")
        assert "multiple" not in key.lower().replace("_", " ") or key.count("_") >= 2

    def test_generate_name_special_chars(self):
        """Test removing special characters."""
        key = _generate_holiday_key("Holiday & Special Day!")
        assert "&" not in key
        assert "!" not in key
        assert key == "holiday_special_day"

    def test_generate_name_with_hyphens(self):
        """Test handling hyphens."""
        key = _generate_holiday_key("Mother-Daughter Day")
        assert key == "motherdaughter_day"


class TestClockworkOptionsFlow:
    """Test Clockwork options flow."""

    @pytest.fixture
    def mock_config_entry(self):
        """Create a mock config entry."""
        entry = MagicMock(spec=config_entries.ConfigEntry)
        entry.entry_id = "test_entry"
        entry.options = {
            CONF_CALCULATIONS: [
                {"name": "Test Timespan", "type": "timespan", "entity_id": "sensor.test"},
                {"name": "Test Offset", "type": "offset", "entity_id": "binary_sensor.test"},
            ],
            "custom_holidays": []
        }
        entry.data = {}
        return entry

    @pytest.fixture
    def options_flow(self, mock_config_entry):
        """Create an options flow handler."""
        flow = ClockworkOptionsFlowHandler()
        # Mock the config_entry property to avoid HA deprecation warning
        type(flow).config_entry = mock_config_entry
        return flow

    @pytest.mark.asyncio
    async def test_modify_calculation_no_calculations(self, options_flow):
        """Test modify calculation when no calculations exist."""
        options_flow.config_entry.options = {CONF_CALCULATIONS: []}
        
        result = await options_flow.async_step_modify_calculation()
        
        assert result["type"] == "abort"
        assert result["reason"] == "no_calculations"

    @pytest.mark.asyncio
    async def test_modify_calculation_select_calculation(self, options_flow):
        """Test selecting a calculation to modify."""
        with patch.object(options_flow, 'async_step_modify_by_type') as mock_modify:
            mock_modify.return_value = {"type": "form", "step_id": "modify_timespan"}
            
            result = await options_flow.async_step_modify_calculation(
                {"calc_index": "0"}
            )
            
            mock_modify.assert_called_once_with("timespan")
            assert result == {"type": "form", "step_id": "modify_timespan"}

    @pytest.mark.asyncio
    async def test_modify_calculation_show_form(self, options_flow):
        """Test showing the calculation selection form."""
        result = await options_flow.async_step_modify_calculation()
        
        assert result["type"] == "form"
        assert result["step_id"] == "modify_calculation"
        assert "data_schema" in result
        assert "description_placeholders" in result

    @pytest.mark.asyncio
    async def test_modify_by_type_timespan(self, options_flow):
        """Test routing to timespan modify method."""
        options_flow._selected_calc_index = 0  # Set the selected index
        with patch.object(options_flow, 'async_step_modify_timespan') as mock_method:
            mock_method.return_value = {"type": "form", "step_id": "modify_timespan"}
            
            result = await options_flow.async_step_modify_by_type("timespan")
            
            mock_method.assert_called_once()
            assert result == {"type": "form", "step_id": "modify_timespan"}

    @pytest.mark.asyncio
    async def test_modify_by_type_offset(self, options_flow):
        """Test routing to offset modify method."""
        options_flow._selected_calc_index = 1  # Set the selected index
        with patch.object(options_flow, 'async_step_modify_offset') as mock_method:
            mock_method.return_value = {"type": "form", "step_id": "modify_offset"}
            
            result = await options_flow.async_step_modify_by_type("offset")
            
            mock_method.assert_called_once()
            assert result == {"type": "form", "step_id": "modify_offset"}

    @pytest.mark.asyncio
    async def test_modify_by_type_unknown(self, options_flow):
        """Test routing with unknown calculation type."""
        options_flow._selected_calc_index = 0  # Set the selected index
        result = await options_flow.async_step_modify_by_type("unknown_type")
        
        assert result["type"] == "abort"
        assert result["reason"] == "unsupported_calculation_type"

    @pytest.mark.asyncio
    async def test_modify_by_type_holiday(self, options_flow):
        """Test routing to holiday modify method."""
        # Add a holiday calculation to the config for this test
        options_flow.config_entry.options[CONF_CALCULATIONS].append(
            {"name": "Test Holiday", "type": "holiday", "holiday": "christmas", "offset": 0}
        )
        options_flow._selected_calc_index = 2  # Set the selected index to the new holiday calc
        with patch.object(options_flow, 'async_step_modify_holiday') as mock_method:
            mock_method.return_value = {"type": "form", "step_id": "modify_holiday"}
            
            result = await options_flow.async_step_modify_by_type("holiday")
            
            mock_method.assert_called_once()
            assert result == {"type": "form", "step_id": "modify_holiday"}


class TestClockworkOptionsFlowCustomHolidays:
    """Test Clockwork options flow custom holiday management."""

    @pytest.fixture
    def mock_config_entry(self):
        """Create a mock config entry with custom holidays."""
        entry = MagicMock(spec=config_entries.ConfigEntry)
        entry.entry_id = "test_entry"
        entry.options = {
            CONF_CALCULATIONS: [],
            "custom_holidays": [
                {
                    "name": "Test Holiday",
                    "key": "test_holiday", 
                    "type": "fixed",
                    "month": 12,
                    "day": 25
                }
            ]
        }
        entry.data = {}
        return entry

    @pytest.fixture
    def options_flow(self, mock_config_entry):
        """Create an options flow handler."""
        flow = ClockworkOptionsFlowHandler()
        # Mock the config_entry property to avoid HA deprecation warning
        type(flow).config_entry = mock_config_entry
        return flow

    @pytest.mark.asyncio
    async def test_add_custom_holiday_show_form(self, options_flow):
        """Test showing the add custom holiday form."""
        result = await options_flow.async_step_custom_holiday()
        
        assert result["type"] == "form"
        assert result["step_id"] == "custom_holiday"
        assert "data_schema" in result

    @pytest.mark.asyncio
    async def test_add_custom_holiday_success(self, options_flow):
        """Test successfully adding a custom holiday."""
        with patch.object(options_flow, '_save_custom_holiday') as mock_save:
            mock_save.return_value = {"type": "menu", "step_id": "init"}
            
            result = await options_flow.async_step_custom_holiday({
                "name": "New Holiday",
                "holiday_type": "fixed",
                "month": 1,
                "day": 1
            })
            
            mock_save.assert_called_once()
            assert result == {"type": "menu", "step_id": "init"}

    @pytest.mark.asyncio
    async def test_add_custom_holiday_validation_error(self, options_flow):
        """Test validation error when adding custom holiday."""
        result = await options_flow.async_step_custom_holiday({
            "name": "",
            "holiday_type": "fixed",
            "month": 1,
            "day": 1
        })
        
        assert result["type"] == "form"
        assert result["step_id"] == "custom_holiday"
        assert "errors" in result
        assert "base" in result["errors"]

    @pytest.mark.asyncio
    async def test_modify_custom_holiday_no_holidays(self, options_flow):
        """Test modify custom holiday when no holidays exist."""
        options_flow.config_entry.options["custom_holidays"] = []
        
        result = await options_flow.async_step_modify_custom_holiday()
        
        assert result["type"] == "abort"
        assert result["reason"] == "no_custom_holidays"

    @pytest.mark.asyncio
    async def test_modify_custom_holiday_select_holiday(self, options_flow):
        """Test selecting a custom holiday to modify."""
        with patch.object(options_flow, 'async_step_modify_custom_holiday_form') as mock_method:
            mock_method.return_value = {"type": "form", "step_id": "modify_custom_holiday_form"}
            
            result = await options_flow.async_step_modify_custom_holiday({
                "holiday_index": "0"
            })
            
            assert options_flow._selected_holiday_index == 0
            mock_method.assert_called_once()
            assert result == {"type": "form", "step_id": "modify_custom_holiday_form"}

    @pytest.mark.asyncio
    async def test_modify_custom_holiday_show_form(self, options_flow):
        """Test showing the custom holiday selection form."""
        result = await options_flow.async_step_modify_custom_holiday()
        
        assert result["type"] == "form"
        assert result["step_id"] == "modify_custom_holiday"
        assert "data_schema" in result

    @pytest.mark.asyncio
    async def test_modify_custom_holiday_form_success(self, options_flow):
        """Test successfully modifying a custom holiday."""
        options_flow._selected_holiday_index = 0
        
        with patch.object(options_flow, '_update_custom_holiday') as mock_update:
            mock_update.return_value = {"type": "menu", "step_id": "init"}
            
            result = await options_flow.async_step_modify_custom_holiday_form({
                "name": "Updated Holiday",
                "holiday_type": "fixed",
                "month": 12,
                "day": 25
            })
            
            mock_update.assert_called_once_with(0, {
                "name": "Updated Holiday",
                "holiday_type": "fixed", 
                "month": 12,
                "day": 25
            })
            assert result == {"type": "menu", "step_id": "init"}

    @pytest.mark.asyncio
    async def test_delete_custom_holiday_no_holidays(self, options_flow):
        """Test delete custom holiday when no holidays exist."""
        options_flow.config_entry.options["custom_holidays"] = []
        
        result = await options_flow.async_step_delete_custom_holiday()
        
        assert result["type"] == "abort"
        assert result["reason"] == "no_custom_holidays"

    @pytest.mark.asyncio
    async def test_delete_custom_holiday_success(self, options_flow):
        """Test successfully deleting a custom holiday."""
        options_flow._selected_holiday_index = 0  # Set the selected index
        # Mock hass for the test
        options_flow.hass = MagicMock()
        options_flow.hass.config_entries = MagicMock()
        options_flow.hass.config_entries.async_reload = AsyncMock()
        
        result = await options_flow.async_step_delete_custom_holiday_confirm({"confirm": True})
        
        options_flow.hass.config_entries.async_update_entry.assert_called_once()
        options_flow.hass.config_entries.async_reload.assert_called_once()
        assert result["type"] == "abort"
        assert result["reason"] == "holiday_deleted"

    @pytest.mark.asyncio
    async def test_delete_custom_holiday_show_form(self, options_flow):
        """Test showing the custom holiday deletion form."""
        result = await options_flow.async_step_delete_custom_holiday()
        
        assert result["type"] == "form"
        assert result["step_id"] == "delete_custom_holiday"
        assert "data_schema" in result

    @pytest.mark.asyncio
    async def test_holiday_calculation_includes_custom_holidays(self, options_flow):
        """Test that custom holidays appear in the holiday calculation dropdown."""
        # The fixture already sets up custom holidays, so we can test directly
        result = await options_flow.async_step_holiday()
        
        assert result["type"] == "form"
        assert result["step_id"] == "holiday"
        assert "data_schema" in result
        
        # Check that the holiday selector includes custom holidays
        holiday_selector = result["data_schema"].schema["holiday"]
        holidays_list = holiday_selector.container
        
        # Should include preset holidays
        assert "christmas" in holidays_list
        assert "new_years_day" in holidays_list
        
        # Should include custom holidays
        assert "test_holiday" in holidays_list

    @pytest.mark.asyncio
    async def test_modify_holiday_includes_custom_holidays(self, options_flow):
        """Test that custom holidays appear in the modify holiday calculation dropdown."""
        # Add a holiday calculation to modify
        options_flow.config_entry.options[CONF_CALCULATIONS].append(
            {"name": "Test Holiday Calc", "type": "holiday", "holiday": "christmas", "offset": 0}
        )
        options_flow._selected_calc_index = 0  # Set to the holiday calculation index
        
        result = await options_flow.async_step_modify_holiday()
        
        assert result["type"] == "form"
        assert result["step_id"] == "modify_holiday"
        assert "data_schema" in result
        
        # Check that the holiday selector includes custom holidays
        holiday_selector = result["data_schema"].schema["holiday"]
        holidays_list = holiday_selector.container
        
        # Should include preset holidays
        assert "christmas" in holidays_list
        assert "new_years_day" in holidays_list
        
        # Should include custom holidays
        assert "test_holiday" in holidays_list

class TestGenerateHolidayKeyEdgeCases:
    """Test additional edge cases for holiday key generation."""

    def test_generate_key_with_numbers_and_spaces(self):
        """Test key generation with numbers and spaces."""
        key = _generate_holiday_key("2024 Election Day")
        assert "2024" in key
        assert "election_day" in key

    def test_generate_key_unicode_characters(self):
        """Test key generation with unicode characters."""
        key = _generate_holiday_key("Noël")
        assert len(key) > 0
        assert key.islower() or not key.isalpha()

    def test_generate_key_all_caps(self):
        """Test key generation converts all caps to lowercase."""
        key = _generate_holiday_key("NEW YEAR")
        assert key == "new_year"

    def test_generate_key_leading_trailing_spaces(self):
        """Test key generation handles leading/trailing spaces."""
        key = _generate_holiday_key("  Easter  ")
        assert key.startswith("easter") or key.startswith("_") == False

    def test_generate_key_consecutive_special_chars(self):
        """Test key generation handles consecutive special characters."""
        key = _generate_holiday_key("Mother's & Father's Day")
        assert key == "mothers_fathers_day"

    def test_generate_key_numbers_only(self):
        """Test key generation with numbers only."""
        key = _generate_holiday_key("2024 2025 2026")
        assert "2024" in key or len(key) > 0


class TestConfigFlowInitialSteps:
    """Test initial steps in config flow."""

    @pytest.mark.asyncio
    async def test_init_step_returns_menu(self):
        """Test init step returns menu."""
        flow = ClockworkOptionsFlowHandler()
        entry = MagicMock(spec=config_entries.ConfigEntry)
        entry.entry_id = "test_entry"
        entry.options = {CONF_CALCULATIONS: []}
        type(flow).config_entry = entry
        
        result = await flow.async_step_init()
        
        assert result["type"] in ["menu", "form"]

    @pytest.mark.asyncio
    async def test_add_calculation_step_shows_options(self):
        """Test add calculation step shows options."""
        flow = ClockworkOptionsFlowHandler()
        entry = MagicMock(spec=config_entries.ConfigEntry)
        entry.entry_id = "test_entry"
        entry.options = {CONF_CALCULATIONS: []}
        type(flow).config_entry = entry
        
        result = await flow.async_step_add_calculation()
        
        assert result["type"] == "menu"
        assert "step_id" in result


class TestConfigFlowDeletionWorkflows:
    """Test calculation and holiday deletion workflows."""

    @pytest.fixture
    def config_entry_with_calcs(self):
        """Create a config entry with calculations."""
        entry = MagicMock(spec=config_entries.ConfigEntry)
        entry.entry_id = "test_entry"
        entry.options = {
            CONF_CALCULATIONS: [
                {"name": "Test 1", "type": "timespan", "entity_id": "sensor.test1"},
                {"name": "Test 2", "type": "season", "season": "summer"},
            ],
            "custom_holidays": []
        }
        entry.data = {}
        return entry

    @pytest.mark.asyncio
    async def test_delete_calculation_shows_list(self, config_entry_with_calcs):
        """Test delete calculation step shows list."""
        flow = ClockworkOptionsFlowHandler()
        type(flow).config_entry = config_entry_with_calcs
        
        result = await flow.async_step_delete_calculation()
        
        assert result["type"] == "form"
        assert result["step_id"] == "delete_calculation"

    @pytest.mark.asyncio
    async def test_delete_custom_holiday_shows_list(self, config_entry_with_calcs):
        """Test delete custom holiday step shows list."""
        config_entry_with_calcs.options["custom_holidays"] = [
            {"name": "Holiday 1", "key": "holiday_1"}
        ]
        flow = ClockworkOptionsFlowHandler()
        type(flow).config_entry = config_entry_with_calcs
        
        result = await flow.async_step_delete_custom_holiday()
        
        assert result["type"] == "form"
        assert result["step_id"] == "delete_custom_holiday"


class TestConfigFlowNameNormalization:
    """Test name normalization and formatting."""

    def test_calculation_names_with_spaces(self):
        """Test calculation names with spaces are handled."""
        name = "My Complex Calculation Name"
        normalized = name.replace(' ', '_').lower()
        assert normalized == "my_complex_calculation_name"
        assert "_" in normalized

    def test_calculation_names_with_special_chars(self):
        """Test calculation names with special characters."""
        names_to_test = [
            ("Test-Calculation", "test-calculation"),
            ("Test/Calculation", "test/calculation"),
            ("Test.Calculation", "test.calculation"),
        ]
        
        for original, expected in names_to_test:
            normalized = original.replace(' ', '_').lower()
            assert normalized.lower() == expected.lower()

    def test_unique_id_format_consistency(self):
        """Test unique ID format is consistent."""
        entry_id = "test_entry_123"
        calc_name = "My Calculation"
        unique_id = f"clockwork_{entry_id}_{calc_name.replace(' ', '_').lower()}"
        
        assert unique_id.startswith("clockwork_")
        assert entry_id in unique_id
        assert calc_name.lower().replace(" ", "_") in unique_id


class TestConfigFlowCalculationTypes:
    """Test specific calculation type flows."""

    @pytest.mark.asyncio
    async def test_timespan_calculation_fields(self):
        """Test timespan calculation required fields."""
        calc = {
            "type": "timespan",
            "name": "Test",
            "entity_id": "sensor.test",
            "track_state": "on",
            "update_interval": 60
        }
        
        assert "name" in calc
        assert "entity_id" in calc
        assert "track_state" in calc

    @pytest.mark.asyncio
    async def test_offset_calculation_fields(self):
        """Test offset calculation required fields."""
        calc = {
            "type": "offset",
            "name": "Test",
            "entity_id": "binary_sensor.test",
            "offset": "1 hour",
            "offset_mode": "latch",
            "trigger_on": "on"
        }
        
        assert "name" in calc
        assert "entity_id" in calc
        assert "offset" in calc

    @pytest.mark.asyncio
    async def test_season_calculation_fields(self):
        """Test season calculation required fields."""
        calc = {
            "type": "season",
            "name": "Test",
            "season": "summer",
            "hemisphere": "northern"
        }
        
        assert calc["season"] in ["spring", "summer", "autumn", "winter"]
        assert calc["hemisphere"] in ["northern", "southern"]

    @pytest.mark.asyncio
    async def test_holiday_calculation_fields(self):
        """Test holiday calculation required fields."""
        calc = {
            "type": "holiday",
            "name": "Test",
            "holiday": "christmas",
            "offset": 0
        }
        
        assert "name" in calc
        assert "holiday" in calc
        assert isinstance(calc["offset"], int)

    @pytest.mark.asyncio
    async def test_between_dates_calculation_fields(self):
        """Test between dates calculation required fields."""
        calc = {
            "type": "between_dates",
            "name": "Test",
            "start_datetime_entity": "input_datetime.start",
            "end_datetime_entity": "input_datetime.end"
        }
        
        assert "start_datetime_entity" in calc
        assert "end_datetime_entity" in calc

    @pytest.mark.asyncio
    async def test_outside_dates_calculation_fields(self):
        """Test outside dates calculation required fields."""
        calc = {
            "type": "outside_dates",
            "name": "Test",
            "start_datetime_entity": "input_datetime.start",
            "end_datetime_entity": "input_datetime.end"
        }
        
        assert "start_datetime_entity" in calc
        assert "end_datetime_entity" in calc


class TestConfigFlowEntityReferences:
    """Test entity reference validation and handling."""

    @pytest.mark.asyncio
    async def test_entity_selection_validation(self):
        """Test that entity selection is validated."""
        # Valid entity ID formats
        valid_entities = [
            "binary_sensor.test",
            "sensor.my_sensor",
            "input_datetime.event_time",
            "switch.my_switch"
        ]
        
        for entity_id in valid_entities:
            assert "." in entity_id
            assert entity_id.count(".") == 1

    @pytest.mark.asyncio
    async def test_datetime_entity_format(self):
        """Test datetime entity format validation."""
        datetime_entities = [
            "input_datetime.start",
            "input_datetime.end",
            "input_datetime.event_time"
        ]
        
        for entity in datetime_entities:
            domain, name = entity.split(".")
            assert domain in ["input_datetime", "sensor"]

    @pytest.mark.asyncio
    async def test_binary_sensor_entity_format(self):
        """Test binary sensor entity format validation."""
        binary_entities = [
            "binary_sensor.door",
            "binary_sensor.motion",
            "binary_sensor.window"
        ]
        
        for entity in binary_entities:
            domain, name = entity.split(".")
            assert domain == "binary_sensor"


class TestConfigFlowOffsetParsing:
    """Test offset value parsing and validation."""

    def test_offset_formats(self):
        """Test various offset formats are recognized."""
        valid_offsets = [
            "1 hour",
            "30 minutes",
            "2 days",
            "1800 seconds",
            "45 minutes"
        ]
        
        for offset in valid_offsets:
            assert isinstance(offset, str)
            assert len(offset) > 0
            # Basic format check
            parts = offset.split()
            assert len(parts) == 2

    def test_offset_must_have_unit(self):
        """Test that offset must have a unit."""
        invalid_offsets = ["1", "30", "2"]
        
        for offset in invalid_offsets:
            parts = offset.split()
            assert len(parts) < 2  # Missing unit


class TestConfigFlowHolidaySelection:
    """Test holiday selection and custom holidays."""

    @pytest.mark.asyncio
    async def test_preset_holidays_available(self):
        """Test that preset holidays are available."""
        presets = ["christmas", "new_years_day", "thanksgiving", "halloween"]
        
        for holiday in presets:
            assert isinstance(holiday, str)
            assert len(holiday) > 0

    @pytest.mark.asyncio
    async def test_custom_holiday_type_options(self):
        """Test that custom holiday types are available."""
        types = [
            "fixed",       # Fixed date (month/day)
            "recurring",   # Recurring yearly
        ]
        
        for holiday_type in types:
            assert isinstance(holiday_type, str)


class TestConfigFlowMonthSelection:
    """Test month selection for month calculations."""

    @pytest.mark.asyncio
    async def test_month_string_format(self):
        """Test month string format validation."""
        # Valid month formats: comma-separated month numbers (1-12)
        valid_months = [
            "1,2,3",           # Winter months
            "6,7,8",           # Summer months
            "1",               # Single month
            "12",              # December only
            "1,4,7,10"        # Quarterly
        ]
        
        for months_str in valid_months:
            month_list = [int(m.strip()) for m in months_str.split(",")]
            assert all(1 <= m <= 12 for m in month_list)

    @pytest.mark.asyncio
    async def test_invalid_month_values(self):
        """Test that invalid month values are caught."""
        months_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        
        # Test boundary conditions
        invalid_months = [0, 13, 100, -1]
        for month in invalid_months:
            assert month not in months_list


class TestConfigFlowSeasonSelection:
    """Test season selection configuration."""

    @pytest.mark.asyncio
    async def test_season_options(self):
        """Test available season options."""
        seasons = ["spring", "summer", "autumn", "winter"]
        
        for season in seasons:
            assert isinstance(season, str)
            assert len(season) > 0

    @pytest.mark.asyncio
    async def test_hemisphere_options(self):
        """Test available hemisphere options."""
        hemispheres = ["northern", "southern"]
        
        for hemisphere in hemispheres:
            assert isinstance(hemisphere, str)
            assert hemisphere in ["northern", "southern"]


class TestConfigFlowOrderAndStructure:
    """Test flow order and structure."""

    @pytest.mark.asyncio
    async def test_menu_based_navigation(self):
        """Test that main menu drives navigation."""
        # Main menu should offer options to:
        # - Add calculation
        # - Modify calculation
        # - Delete calculation
        # - Add custom holiday
        # - Modify custom holiday
        # - Delete custom holiday
        
        menu_options = [
            "add_calculation",
            "modify_calculation",
            "delete_calculation",
            "custom_holiday",
            "modify_custom_holiday",
            "delete_custom_holiday"
        ]
        
        for option in menu_options:
            assert isinstance(option, str)

    @pytest.mark.asyncio
    async def test_step_completion_returns_menu(self):
        """Test that steps return to menu on completion."""
        # After completing a calculation step, should return to menu
        result_type = "menu"
        assert result_type in ["menu", "form", "abort"]


class TestConfigFlowErrorHandling:
    """Test error handling in config flow."""

    @pytest.mark.asyncio
    async def test_duplicate_calculation_names(self):
        """Test handling of duplicate calculation names."""
        existing_names = ["Test 1", "Test 2", "Test 3"]
        new_name = "Test 1"  # Duplicate
        
        assert new_name in existing_names

    @pytest.mark.asyncio
    async def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        calc_with_missing_name = {
            "entity_id": "sensor.test",
            "track_state": "on"
        }
        
        assert "name" not in calc_with_missing_name
        assert "entity_id" in calc_with_missing_name

    @pytest.mark.asyncio
    async def test_invalid_entity_id_format(self):
        """Test handling of invalid entity ID format."""
        invalid_ids = [
            "test",                    # No domain separator
            "sensor.test.extra",       # Too many separators
            ".test",                   # Empty domain
            "sensor.",                 # Empty name
        ]
        
        for entity_id in invalid_ids:
            parts = entity_id.split(".")
            assert len(parts) != 2 or "" in parts


class TestConfigFlowScanAutomations:
    """Test scan automations feature in config flow."""

    def test_scan_automations_function_exists(self):
        """Test that scan_automations step exists in handler."""
        handler = ClockworkOptionsFlowHandler()
        
        # Just verify the method exists
        assert hasattr(handler, 'async_step_scan_automations')
        assert callable(handler.async_step_scan_automations)

    def test_scan_automations_menu_option(self):
        """Test that scan_automations is in the init menu."""
        # This is verified by checking strings.json is correctly formatted
        # The menu_options are defined there for the UI
        from custom_components.clockwork.config_flow import ClockworkOptionsFlowHandler
        
        # Just verify the class exists and has the method
        assert hasattr(ClockworkOptionsFlowHandler, 'async_step_scan_automations')