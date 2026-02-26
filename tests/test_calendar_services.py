"""Tests for Clockwork calendar services."""
import pytest
from unittest.mock import patch, MagicMock

from homeassistant.core import HomeAssistant

from custom_components.clockwork.const import DOMAIN


class TestCalendarServiceRegistration:
    """Test that calendar services are properly registered."""

    @pytest.mark.asyncio
    async def test_calendar_services_registered(self):
        """Test that delete_event, update_event, and delete_events_in_range services are registered."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        
        from custom_components.clockwork import async_setup
        
        with patch('custom_components.clockwork.async_register_admin_service') as mock_admin_service:
            await async_setup(hass, {})
            
            # Check that three services were registered
            assert mock_admin_service.call_count == 3
            
            # Verify service names
            service_calls = [call[0][2] for call in mock_admin_service.call_args_list]
            assert "delete_event" in service_calls
            assert "update_event" in service_calls
            assert "delete_events_in_range" in service_calls

    @pytest.mark.asyncio
    async def test_services_use_clockwork_domain(self):
        """Test that all services use the clockwork domain."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        
        from custom_components.clockwork import async_setup
        
        with patch('custom_components.clockwork.async_register_admin_service') as mock_admin_service:
            await async_setup(hass, {})
            
            # Verify all calls use the DOMAIN
            for call_args in mock_admin_service.call_args_list:
                assert call_args[0][0] == hass
                assert call_args[0][1] == DOMAIN

    @pytest.mark.asyncio
    async def test_delete_event_service_handler_exists(self):
        """Test that delete_event service handler is configured properly."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        
        from custom_components.clockwork import async_setup
        
        with patch('custom_components.clockwork.async_register_admin_service') as mock_admin_service:
            await async_setup(hass, {})
            
            # Find the delete_event service call
            delete_event_call = None
            for call_args in mock_admin_service.call_args_list:
                if call_args[0][2] == "delete_event":
                    delete_event_call = call_args
                    break
            
            assert delete_event_call is not None
            # Verify the handler is a callable
            handler = delete_event_call[0][3]
            assert callable(handler)

    @pytest.mark.asyncio
    async def test_update_event_service_handler_exists(self):
        """Test that update_event service handler is configured properly."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        
        from custom_components.clockwork import async_setup
        
        with patch('custom_components.clockwork.async_register_admin_service') as mock_admin_service:
            await async_setup(hass, {})
            
            # Find the update_event service call
            update_event_call = None
            for call_args in mock_admin_service.call_args_list:
                if call_args[0][2] == "update_event":
                    update_event_call = call_args
                    break
            
            assert update_event_call is not None
            # Verify the handler is a callable
            handler = update_event_call[0][3]
            assert callable(handler)

    @pytest.mark.asyncio
    async def test_delete_events_in_range_service_handler_exists(self):
        """Test that delete_events_in_range service handler is configured properly."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        
        from custom_components.clockwork import async_setup
        
        with patch('custom_components.clockwork.async_register_admin_service') as mock_admin_service:
            await async_setup(hass, {})
            
            # Find the delete_events_in_range service call
            delete_range_call = None
            for call_args in mock_admin_service.call_args_list:
                if call_args[0][2] == "delete_events_in_range":
                    delete_range_call = call_args
                    break
            
            assert delete_range_call is not None
            # Verify the handler is a callable
            handler = delete_range_call[0][3]
            assert callable(handler)
