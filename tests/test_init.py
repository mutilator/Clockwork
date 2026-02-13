"""Tests for Clockwork integration setup."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.clockwork import (
    async_setup_entry,
    async_unload_entry,
)
from custom_components.clockwork.const import DOMAIN


@pytest.mark.asyncio
async def test_async_setup_entry():
    """Test setting up the integration."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.async_add_executor_job = AsyncMock(return_value={})
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()
    hass.bus = MagicMock()

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.options = {"calculations": []}
    entry.data = {}
    entry.add_update_listener = MagicMock()

    with patch('homeassistant.helpers.entity_registry.async_get') as mock_er, \
         patch('homeassistant.helpers.device_registry.async_get') as mock_dr:

        mock_er.return_value.entities = {}
        mock_dr.return_value.async_get_or_create = MagicMock()

        result = await async_setup_entry(hass, entry)
        assert result is True
        # Verify service was registered
        hass.services.async_register.assert_called_once()
        # Verify the service was registered with correct domain and name
        call_args = hass.services.async_register.call_args
        assert call_args[0][0] == DOMAIN
        assert call_args[0][1] == "scan_automations"


@pytest.mark.asyncio
async def test_async_unload_entry():
    """Test unloading the integration."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {"test_entry": []}}
    hass.config_entries = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    result = await async_unload_entry(hass, entry)
    assert result is True