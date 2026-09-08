"""Tests for Clockwork automation conditions."""
import pytest
from datetime import timedelta
from unittest.mock import MagicMock

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.util import dt as dt_util

from custom_components.clockwork.condition.last_triggered import LastTriggeredCondition
from custom_components.clockwork.condition.timespan import async_if_action


def _timespan_config(**options):
    """Build a condition config in the options-wrapped shape HA 2026.5+ uses."""
    return {"condition": "clockwork.timespan", "options": options}


def _hass_with_state(seconds_ago, state=STATE_ON):
    """Mock hass whose entity last changed `seconds_ago` seconds ago."""
    hass = MagicMock()
    mock_state = MagicMock()
    mock_state.state = state
    mock_state.last_changed = dt_util.utcnow() - timedelta(seconds=seconds_ago)
    hass.states.get.return_value = mock_state
    return hass


@pytest.mark.asyncio
async def test_timespan_condition_above():
    """Test timespan condition with 'above' operator."""
    hass = _hass_with_state(120)

    assert await async_if_action(hass, _timespan_config(entity_id="binary_sensor.test", above=60)) is True
    assert await async_if_action(hass, _timespan_config(entity_id="binary_sensor.test", above=200)) is False


@pytest.mark.asyncio
async def test_timespan_condition_below():
    """Test timespan condition with 'below' operator."""
    hass = _hass_with_state(30)

    assert await async_if_action(hass, _timespan_config(entity_id="binary_sensor.test", below=60)) is True
    assert await async_if_action(hass, _timespan_config(entity_id="binary_sensor.test", below=20)) is False


@pytest.mark.asyncio
async def test_timespan_condition_equal_to():
    """Test timespan condition with 'equal_to' operator."""
    hass = _hass_with_state(60)

    assert await async_if_action(hass, _timespan_config(entity_id="binary_sensor.test", equal_to=60)) is True
    assert await async_if_action(hass, _timespan_config(entity_id="binary_sensor.test", equal_to=90)) is False


@pytest.mark.asyncio
async def test_timespan_condition_missing_entity():
    """Test timespan condition when entity doesn't exist."""
    hass = MagicMock()
    hass.states.get.return_value = None

    config = _timespan_config(entity_id="binary_sensor.nonexistent", above=60)
    assert await async_if_action(hass, config) is False


@pytest.mark.asyncio
async def test_timespan_condition_no_last_changed():
    """Test timespan condition when entity has no last_changed time."""
    hass = MagicMock()
    mock_state = MagicMock()
    mock_state.state = STATE_ON
    mock_state.last_changed = None
    hass.states.get.return_value = mock_state

    config = _timespan_config(entity_id="binary_sensor.test", above=60)
    assert await async_if_action(hass, config) is False


@pytest.mark.asyncio
async def test_timespan_condition_no_comparison():
    """With no comparison operator, an existing entity satisfies the condition."""
    hass = _hass_with_state(30)

    config = _timespan_config(entity_id="binary_sensor.test")
    assert await async_if_action(hass, config) is True


@pytest.mark.asyncio
async def test_timespan_condition_with_different_states():
    """Test timespan condition works regardless of the entity's state value."""
    hass = _hass_with_state(180, state=STATE_OFF)

    config = _timespan_config(entity_id="binary_sensor.test", above=120)
    assert await async_if_action(hass, config) is True


@pytest.mark.asyncio
async def test_timespan_condition_combines_all_operators():
    """Every supplied operator must hold, so above+below reads as 'between'."""
    hass = _hass_with_state(120)

    # 120 is inside (60, 200)
    config = _timespan_config(entity_id="binary_sensor.test", above=60, below=200)
    assert await async_if_action(hass, config) is True

    # 120 satisfies above=60 but not below=100. Under the old "first operator
    # wins" behaviour this incorrectly returned True.
    config = _timespan_config(entity_id="binary_sensor.test", above=60, below=100)
    assert await async_if_action(hass, config) is False

    # Likewise a failing equal_to must not be masked by a passing above.
    config = _timespan_config(entity_id="binary_sensor.test", above=60, equal_to=999)
    assert await async_if_action(hass, config) is False


@pytest.mark.asyncio
async def test_timespan_condition_ignores_null_operators():
    """Operators left blank in the UI are skipped, not compared against None."""
    hass = _hass_with_state(120)

    config = _timespan_config(entity_id="binary_sensor.test", above=60, below=None, equal_to=None)
    assert await async_if_action(hass, config) is True


async def _last_triggered_result(hass, **options):
    """Evaluate the last_triggered condition with the given options."""
    condition = LastTriggeredCondition(
        hass, {"condition": "clockwork.last_triggered", "options": options}
    )
    checker = await condition.async_get_checker()
    return checker()


def _hass_with_last_triggered(seconds_ago):
    """Mock hass whose automation last triggered `seconds_ago` seconds ago."""
    hass = MagicMock()
    mock_state = MagicMock()
    mock_state.state = STATE_ON
    mock_state.attributes = {
        "last_triggered": (dt_util.utcnow() - timedelta(seconds=seconds_ago)).isoformat()
    }
    hass.states.get.return_value = mock_state
    return hass


@pytest.mark.asyncio
async def test_last_triggered_above_and_below():
    """last_triggered honours every operator supplied, not just the first."""
    hass = _hass_with_last_triggered(120)

    assert await _last_triggered_result(hass, entity_id="automation.test", above=60) is True
    assert await _last_triggered_result(hass, entity_id="automation.test", above=60, below=200) is True
    # Would have returned True when only 'above' was evaluated.
    assert await _last_triggered_result(hass, entity_id="automation.test", above=60, below=100) is False


@pytest.mark.asyncio
async def test_last_triggered_missing_attribute():
    """An automation that has never run evaluates to False."""
    hass = MagicMock()
    mock_state = MagicMock()
    mock_state.attributes = {}
    hass.states.get.return_value = mock_state

    assert await _last_triggered_result(hass, entity_id="automation.test", above=60) is False


@pytest.mark.asyncio
async def test_last_triggered_ignores_null_operators():
    """A blank operator field must not be compared against None."""
    hass = _hass_with_last_triggered(120)

    result = await _last_triggered_result(
        hass, entity_id="automation.test", above=60, below=None, equal_to=None
    )
    assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
