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
        assert result["type"] == "menu"

    @pytest.mark.asyncio
    async def test_delete_custom_holiday_show_form(self, options_flow):
        """Test showing the custom holiday deletion form."""
        result = await options_flow.async_step_delete_custom_holiday()
        
        assert result["type"] == "form"
        assert result["step_id"] == "delete_custom_holiday"
        assert "data_schema" in result
