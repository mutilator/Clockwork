"""Tests for Clockwork calendar services."""
import pytest
from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant

from custom_components.clockwork.const import DOMAIN


async def _setup_and_collect_registrations():
    """Run async_setup against a mock hass and return its service registrations.

    Returns a dict of service name -> handler.
    """
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.services = MagicMock()

    from custom_components.clockwork import async_setup

    assert await async_setup(hass, {}) is True

    registrations = {}
    for call_args in hass.services.async_register.call_args_list:
        domain, service, handler = call_args[0][0], call_args[0][1], call_args[0][2]
        assert domain == DOMAIN
        registrations[service] = handler
    return registrations


class TestCalendarServiceRegistration:
    """Test that calendar services are properly registered."""

    @pytest.mark.asyncio
    async def test_calendar_services_registered(self):
        """delete_event, update_event and delete_events_in_range are registered."""
        registrations = await _setup_and_collect_registrations()

        assert set(registrations) == {
            "delete_event",
            "update_event",
            "delete_events_in_range",
        }

    @pytest.mark.asyncio
    async def test_services_use_clockwork_domain(self):
        """All services register under the clockwork domain."""
        # _setup_and_collect_registrations asserts the domain on every call.
        assert await _setup_and_collect_registrations()

    @pytest.mark.asyncio
    async def test_services_are_registered_for_non_admins(self):
        """Calendar services are deliberately callable by non-admin users.

        They are registered with hass.services.async_register rather than
        async_register_admin_service; regressing that would lock out non-admins.
        """
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        hass.services = MagicMock()

        import custom_components.clockwork as clockwork

        assert not hasattr(clockwork, "async_register_admin_service")

        await clockwork.async_setup(hass, {})
        assert hass.services.async_register.call_count == 3

    @pytest.mark.asyncio
    async def test_delete_event_service_handler_exists(self):
        """delete_event is wired to a callable handler."""
        registrations = await _setup_and_collect_registrations()

        assert callable(registrations["delete_event"])

    @pytest.mark.asyncio
    async def test_update_event_service_handler_exists(self):
        """update_event is wired to a callable handler."""
        registrations = await _setup_and_collect_registrations()

        assert callable(registrations["update_event"])

    @pytest.mark.asyncio
    async def test_delete_events_in_range_service_handler_exists(self):
        """delete_events_in_range is wired to a callable handler."""
        registrations = await _setup_and_collect_registrations()

        assert callable(registrations["delete_events_in_range"])
