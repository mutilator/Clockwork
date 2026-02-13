"""Tests for Clockwork diagnostics."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.clockwork.diagnostics import async_get_config_entry_diagnostics


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.title = "Test Clockwork"
    entry.version = 1
    entry.source = "user"
    entry.state = ConfigEntryState.LOADED
    entry.options = {
        "calculations": [],
        "custom_holidays": []
    }
    entry.data = {}
    return entry


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {
        "clockwork": {
            "test_entry_id": {},
            "holidays": {},
            "seasons": {}
        }
    }
    return hass


class TestDiagnosticsBasic:
    """Test basic diagnostics functionality."""

    @pytest.mark.asyncio
    async def test_diagnostics_returns_dict(self, mock_hass, mock_config_entry):
        """Test that diagnostics returns a dictionary."""
        with patch('homeassistant.helpers.entity_registry.async_get') as mock_get_er:
            mock_er = MagicMock()
            mock_er.entities = MagicMock()
            mock_er.entities.values = MagicMock(return_value=[])
            mock_get_er.return_value = mock_er
            
            result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
            
            assert isinstance(result, dict)
            assert "entry" in result
            assert "configuration" in result
            assert "calculations" in result
            assert "custom_holidays" in result
            assert "cached_data" in result
            assert "entities" in result
            assert "platforms" in result

    @pytest.mark.asyncio
    async def test_diagnostics_entry_info(self, mock_hass, mock_config_entry):
        """Test that entry information is included."""
        with patch('homeassistant.helpers.entity_registry.async_get') as mock_get_er:
            mock_er = MagicMock()
            mock_er.entities = MagicMock()
            mock_er.entities.values = MagicMock(return_value=[])
            mock_get_er.return_value = mock_er
            
            result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
            
            assert result["entry"]["title"] == "Test Clockwork"
            assert result["entry"]["version"] == 1
            assert result["entry"]["source"] == "user"
            assert result["entry"]["state"] == "loaded"

    @pytest.mark.asyncio
    async def test_diagnostics_configuration_summary(self, mock_hass, mock_config_entry):
        """Test configuration summary in diagnostics."""
        with patch('homeassistant.helpers.entity_registry.async_get') as mock_get_er:
            mock_er = MagicMock()
            mock_er.entities = MagicMock()
            mock_er.entities.values = MagicMock(return_value=[])
            mock_get_er.return_value = mock_er
            
            result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
            
            config = result["configuration"]
            assert "entry_title" in config
            assert "entry_version" in config
            assert "entry_state" in config
            assert "calculations_count" in config
            assert "custom_holidays_count" in config
            assert config["calculations_count"] == 0
            assert config["custom_holidays_count"] == 0


class TestDiagnosticsCalculations:
    """Test diagnostics with various calculation types."""

    @pytest.mark.asyncio
    async def test_diagnostics_with_timespan_calculation(self, mock_hass, mock_config_entry):
        """Test diagnostics includes timespan calculation."""
        mock_config_entry.options["calculations"] = [
            {
                "type": "timespan",
                "name": "Door Open Time",
                "entity_id": "binary_sensor.door",
                "track_state": "on",
                "update_interval": 30
            }
        ]
        
        with patch('homeassistant.helpers.entity_registry.async_get') as mock_get_er:
            mock_er = MagicMock()
            mock_er.entities = MagicMock()
            mock_er.entities.values = MagicMock(return_value=[])
            mock_get_er.return_value = mock_er
            
            result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
            
            assert len(result["calculations"]) == 1
            calc = result["calculations"][0]
            assert calc["type"] == "timespan"
            assert calc["name"] == "Door Open Time"
            assert calc["entity_id"] == "binary_sensor.door"
            assert calc["track_state"] == "on"
            assert calc["update_interval"] == 30

    @pytest.mark.asyncio
    async def test_diagnostics_with_offset_calculation(self, mock_hass, mock_config_entry):
        """Test diagnostics includes offset calculation."""
        mock_config_entry.options["calculations"] = [
            {
                "type": "offset",
                "name": "Offset Test",
                "entity_id": "binary_sensor.test",
                "offset_seconds": 3600,
                "trigger_on": "on",
                "mode": "latch"
            }
        ]
        
        with patch('homeassistant.helpers.entity_registry.async_get') as mock_get_er:
            mock_er = MagicMock()
            mock_er.entities = MagicMock()
            mock_er.entities.values = MagicMock(return_value=[])
            mock_get_er.return_value = mock_er
            
            result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
            
            assert len(result["calculations"]) == 1
            calc = result["calculations"][0]
            assert calc["type"] == "offset"

    @pytest.mark.asyncio
    async def test_diagnostics_with_season_calculation(self, mock_hass, mock_config_entry):
        """Test diagnostics includes season calculation."""
        mock_config_entry.options["calculations"] = [
            {
                "type": "season",
                "name": "Summer Season",
                "season": "summer",
                "hemisphere": "northern"
            }
        ]
        
        with patch('homeassistant.helpers.entity_registry.async_get') as mock_get_er:
            mock_er = MagicMock()
            mock_er.entities = MagicMock()
            mock_er.entities.values = MagicMock(return_value=[])
            mock_get_er.return_value = mock_er
            
            result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
            
            assert len(result["calculations"]) == 1
            calc = result["calculations"][0]
            assert calc["type"] == "season"
            assert calc["season"] == "summer"
            assert calc["hemisphere"] == "northern"

    @pytest.mark.asyncio
    async def test_diagnostics_with_holiday_calculation(self, mock_hass, mock_config_entry):
        """Test diagnostics includes holiday calculation."""
        mock_config_entry.options["calculations"] = [
            {
                "type": "holiday",
                "name": "Christmas Countdown",
                "holiday": "christmas",
                "offset": 0
            }
        ]
        
        with patch('homeassistant.helpers.entity_registry.async_get') as mock_get_er:
            mock_er = MagicMock()
            mock_er.entities = MagicMock()
            mock_er.entities.values = MagicMock(return_value=[])
            mock_get_er.return_value = mock_er
            
            result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
            
            assert len(result["calculations"]) == 1
            calc = result["calculations"][0]
            assert calc["type"] == "holiday"
            assert calc["holiday"] == "christmas"

    @pytest.mark.asyncio
    async def test_diagnostics_with_multiple_calculations(self, mock_hass, mock_config_entry):
        """Test diagnostics with multiple calculations."""
        mock_config_entry.options["calculations"] = [
            {"type": "timespan", "name": "Timespan"},
            {"type": "season", "name": "Season"},
            {"type": "holiday", "name": "Holiday"}
        ]
        
        with patch('homeassistant.helpers.entity_registry.async_get') as mock_get_er:
            mock_er = MagicMock()
            mock_er.entities = MagicMock()
            mock_er.entities.values = MagicMock(return_value=[])
            mock_get_er.return_value = mock_er
            
            result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
            
            assert len(result["calculations"]) == 3
            assert result["configuration"]["calculations_count"] == 3


class TestDiagnosticsCustomHolidays:
    """Test diagnostics with custom holidays."""

    @pytest.mark.asyncio
    async def test_diagnostics_with_custom_holidays(self, mock_hass, mock_config_entry):
        """Test diagnostics includes custom holidays."""
        mock_config_entry.options["custom_holidays"] = [
            {
                "name": "Company Birthday",
                "key": "company_birthday",
                "type": "fixed",
                "month": 6,
                "day": 15
            }
        ]
        
        with patch('homeassistant.helpers.entity_registry.async_get') as mock_get_er:
            mock_er = MagicMock()
            mock_er.entities = MagicMock()
            mock_er.entities.values = MagicMock(return_value=[])
            mock_get_er.return_value = mock_er
            
            result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
            
            assert len(result["custom_holidays"]) == 1
            holiday = result["custom_holidays"][0]
            assert holiday["name"] == "Company Birthday"
            assert holiday["key"] == "company_birthday"
            assert holiday["type"] == "fixed"
            assert holiday["month"] == 6
            assert holiday["day"] == 15

    @pytest.mark.asyncio
    async def test_diagnostics_with_multiple_custom_holidays(self, mock_hass, mock_config_entry):
        """Test diagnostics with multiple custom holidays."""
        mock_config_entry.options["custom_holidays"] = [
            {"name": "Holiday 1", "key": "holiday_1", "type": "fixed"},
            {"name": "Holiday 2", "key": "holiday_2", "type": "fixed"}
        ]
        
        with patch('homeassistant.helpers.entity_registry.async_get') as mock_get_er:
            mock_er = MagicMock()
            mock_er.entities = MagicMock()
            mock_er.entities.values = MagicMock(return_value=[])
            mock_get_er.return_value = mock_er
            
            result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
            
            assert len(result["custom_holidays"]) == 2
            assert result["configuration"]["custom_holidays_count"] == 2


class TestDiagnosticsCachedData:
    """Test diagnostics cached data information."""

    @pytest.mark.asyncio
    async def test_diagnostics_cached_data_status(self, mock_hass, mock_config_entry):
        """Test cached data status in diagnostics."""
        mock_hass.data["clockwork"]["holidays"] = {"christmas": "2024-12-25"}
        mock_hass.data["clockwork"]["seasons"] = {
            "northern": [{"month": 3, "day": 20}],
            "southern": [{"month": 9, "day": 22}]
        }
        
        with patch('homeassistant.helpers.entity_registry.async_get') as mock_get_er:
            mock_er = MagicMock()
            mock_er.entities = MagicMock()
            mock_er.entities.values = MagicMock(return_value=[])
            mock_get_er.return_value = mock_er
            
            result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
            
            cached = result["cached_data"]
            assert cached["holidays_loaded"] is True
            assert cached["holidays_count"] == 1
            assert cached["seasons_loaded"] is True
            assert "northern" in cached["seasons_hemispheres"]
            assert "southern" in cached["seasons_hemispheres"]


class TestDiagnosticsEntities:
    """Test diagnostics entity information."""

    @pytest.mark.asyncio
    async def test_diagnostics_sensor_entities(self, mock_hass, mock_config_entry):
        """Test diagnostics includes sensor entities."""
        mock_sensor_entity = MagicMock()
        mock_sensor_entity.config_entry_id = "test_entry_id"
        mock_sensor_entity.entity_id = "sensor.test_timespan"
        mock_sensor_entity.name = "Test Timespan"
        mock_sensor_entity.unique_id = "clockwork_test_entry_id_test_timespan"
        mock_sensor_entity.disabled = False
        
        with patch('homeassistant.helpers.entity_registry.async_get') as mock_get_er:
            mock_er = MagicMock()
            mock_er.entities = MagicMock()
            mock_er.entities.values = MagicMock(return_value=[mock_sensor_entity])
            mock_get_er.return_value = mock_er
            
            result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
            
            entities = result["entities"]
            assert entities["total_entities"] == 1
            assert entities["sensor_count"] == 1
            assert entities["binary_sensor_count"] == 0
            assert len(entities["entities"]) == 1
            assert entities["entities"][0]["entity_id"] == "sensor.test_timespan"

    @pytest.mark.asyncio
    async def test_diagnostics_binary_sensor_entities(self, mock_hass, mock_config_entry):
        """Test diagnostics includes binary sensor entities."""
        mock_binary_sensor = MagicMock()
        mock_binary_sensor.config_entry_id = "test_entry_id"
        mock_binary_sensor.entity_id = "binary_sensor.test_offset"
        mock_binary_sensor.name = "Test Offset"
        mock_binary_sensor.unique_id = "clockwork_test_entry_id_test_offset"
        mock_binary_sensor.disabled = False
        
        with patch('homeassistant.helpers.entity_registry.async_get') as mock_get_er:
            mock_er = MagicMock()
            mock_er.entities = MagicMock()
            mock_er.entities.values = MagicMock(return_value=[mock_binary_sensor])
            mock_get_er.return_value = mock_er
            
            result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
            
            entities = result["entities"]
            assert entities["total_entities"] == 1
            assert entities["sensor_count"] == 0
            assert entities["binary_sensor_count"] == 1

    @pytest.mark.asyncio
    async def test_diagnostics_mixed_entities(self, mock_hass, mock_config_entry):
        """Test diagnostics with mixed sensor and binary sensor entities."""
        mock_sensor = MagicMock()
        mock_sensor.config_entry_id = "test_entry_id"
        mock_sensor.entity_id = "sensor.test"
        mock_sensor.name = "Test"
        mock_sensor.unique_id = "test"
        mock_sensor.disabled = False
        
        mock_binary = MagicMock()
        mock_binary.config_entry_id = "test_entry_id"
        mock_binary.entity_id = "binary_sensor.test"
        mock_binary.name = "Test"
        mock_binary.unique_id = "test"
        mock_binary.disabled = False
        
        with patch('homeassistant.helpers.entity_registry.async_get') as mock_get_er:
            mock_er = MagicMock()
            mock_er.entities = MagicMock()
            mock_er.entities.values = MagicMock(return_value=[mock_sensor, mock_binary])
            mock_get_er.return_value = mock_er
            
            result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
            
            entities = result["entities"]
            assert entities["total_entities"] == 2
            assert entities["sensor_count"] == 1
            assert entities["binary_sensor_count"] == 1

    @pytest.mark.asyncio
    async def test_diagnostics_disabled_entities(self, mock_hass, mock_config_entry):
        """Test diagnostics includes disabled entities."""
        mock_disabled_entity = MagicMock()
        mock_disabled_entity.config_entry_id = "test_entry_id"
        mock_disabled_entity.entity_id = "sensor.test_disabled"
        mock_disabled_entity.name = "Test Disabled"
        mock_disabled_entity.unique_id = "test_disabled"
        mock_disabled_entity.disabled = True
        
        with patch('homeassistant.helpers.entity_registry.async_get') as mock_get_er:
            mock_er = MagicMock()
            mock_er.entities = MagicMock()
            mock_er.entities.values = MagicMock(return_value=[mock_disabled_entity])
            mock_get_er.return_value = mock_er
            
            result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
            
            assert result["entities"]["entities"][0]["disabled"] is True


class TestDiagnosticsPlatforms:
    """Test diagnostics platform information."""

    @pytest.mark.asyncio
    async def test_diagnostics_platforms_info(self, mock_hass, mock_config_entry):
        """Test platform information in diagnostics."""
        mock_sensor = MagicMock()
        mock_sensor.config_entry_id = "test_entry_id"
        mock_sensor.entity_id = "sensor.test"
        mock_sensor.name = "Test"
        mock_sensor.unique_id = "test"
        mock_sensor.disabled = False
        
        with patch('homeassistant.helpers.entity_registry.async_get') as mock_get_er:
            mock_er = MagicMock()
            mock_er.entities = MagicMock()
            mock_er.entities.values = MagicMock(return_value=[mock_sensor])
            mock_get_er.return_value = mock_er
            
            result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
            
            platforms = result["platforms"]
            assert "sensors_registered" in platforms
            assert "binary_sensors_registered" in platforms
            assert "device_created" in platforms
            assert platforms["sensors_registered"] == 1


class TestDiagnosticsEdgeCases:
    """Test edge cases in diagnostics."""

    @pytest.mark.asyncio
    async def test_diagnostics_empty_options(self, mock_hass, mock_config_entry):
        """Test diagnostics with empty options."""
        mock_config_entry.options = {}
        mock_hass.data["clockwork"] = {}
        
        with patch('homeassistant.helpers.entity_registry.async_get') as mock_get_er:
            mock_er = MagicMock()
            mock_er.entities = MagicMock()
            mock_er.entities.values = MagicMock(return_value=[])
            mock_get_er.return_value = mock_er
            
            result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
            
            assert isinstance(result, dict)
            assert result["configuration"]["calculations_count"] == 0

    @pytest.mark.asyncio
    async def test_diagnostics_no_matching_entities(self, mock_hass, mock_config_entry):
        """Test diagnostics when no entities match config entry."""
        other_entity = MagicMock()
        other_entity.config_entry_id = "other_entry_id"
        other_entity.entity_id = "sensor.other"
        
        with patch('homeassistant.helpers.entity_registry.async_get') as mock_get_er:
            mock_er = MagicMock()
            mock_er.entities = MagicMock()
            mock_er.entities.values = MagicMock(return_value=[other_entity])
            mock_get_er.return_value = mock_er
            
            result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
            
            assert result["entities"]["total_entities"] == 0

    @pytest.mark.asyncio
    async def test_diagnostics_with_unknown_calculation_type(self, mock_hass, mock_config_entry):
        """Test diagnostics handles unknown calculation types gracefully."""
        mock_config_entry.options["calculations"] = [
            {
                "type": "unknown_type",
                "name": "Unknown"
            }
        ]
        
        with patch('homeassistant.helpers.entity_registry.async_get') as mock_get_er:
            mock_er = MagicMock()
            mock_er.entities = MagicMock()
            mock_er.entities.values = MagicMock(return_value=[])
            mock_get_er.return_value = mock_er
            
            result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)
            
            assert len(result["calculations"]) == 1
            assert result["calculations"][0]["type"] == "unknown_type"
