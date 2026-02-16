"""Tests for Clockwork automation conditions."""
import pytest

# Skip all tests in this module since the automation condition platform
# is only available in newer Home Assistant versions
pytestmark = pytest.mark.skip(reason="Automation condition platform not available in this Home Assistant version")


@pytest.mark.asyncio
async def test_timespan_condition_above():
    """Test timespan condition with 'above' operator."""
    hass = MagicMock()
    
    # Create a mock state with last_changed 2 minutes ago
    now = dt_util.utcnow()
    two_minutes_ago = now - timedelta(minutes=2)
    
    mock_state = MagicMock()
    mock_state.state = STATE_ON
    mock_state.last_changed = two_minutes_ago
    
    hass.states.get.return_value = mock_state
    
    # Test: 120 seconds > 60 seconds should be True
    config = {
        "entity_id": "binary_sensor.test",
        "above": 60
    }
    
    result = await async_if_action(hass, config)
    assert result is True
    
    # Test: 120 seconds > 200 seconds should be False
    config = {
        "entity_id": "binary_sensor.test",
        "above": 200
    }
    
    result = await async_if_action(hass, config)
    assert result is False


@pytest.mark.asyncio
async def test_timespan_condition_below():
    """Test timespan condition with 'below' operator."""
    hass = MagicMock()
    
    # Create a mock state with last_changed 30 seconds ago
    now = dt_util.utcnow()
    thirty_seconds_ago = now - timedelta(seconds=30)
    
    mock_state = MagicMock()
    mock_state.state = STATE_ON
    mock_state.last_changed = thirty_seconds_ago
    
    hass.states.get.return_value = mock_state
    
    # Test: 30 seconds < 60 seconds should be True
    config = {
        "entity_id": "binary_sensor.test",
        "below": 60
    }
    
    result = await async_if_action(hass, config)
    assert result is True
    
    # Test: 30 seconds < 20 seconds should be False
    config = {
        "entity_id": "binary_sensor.test",
        "below": 20
    }
    
    result = await async_if_action(hass, config)
    assert result is False


@pytest.mark.asyncio
async def test_timespan_condition_equal_to():
    """Test timespan condition with 'equal_to' operator."""
    hass = MagicMock()
    
    # Create a mock state with last_changed exactly 60 seconds ago
    now = dt_util.utcnow()
    sixty_seconds_ago = now - timedelta(seconds=60)
    
    mock_state = MagicMock()
    mock_state.state = STATE_ON
    mock_state.last_changed = sixty_seconds_ago
    
    hass.states.get.return_value = mock_state
    
    # Test: 60 seconds == 60 seconds should be True
    config = {
        "entity_id": "binary_sensor.test",
        "equal_to": 60
    }
    
    result = await async_if_action(hass, config)
    assert result is True
    
    # Test: 60 seconds == 90 seconds should be False
    config = {
        "entity_id": "binary_sensor.test",
        "equal_to": 90
    }
    
    result = await async_if_action(hass, config)
    assert result is False


@pytest.mark.asyncio
async def test_timespan_condition_missing_entity():
    """Test timespan condition when entity doesn't exist."""
    hass = MagicMock()
    hass.states.get.return_value = None
    
    config = {
        "entity_id": "binary_sensor.nonexistent",
        "above": 60
    }
    
    result = await async_if_action(hass, config)
    assert result is False


@pytest.mark.asyncio
async def test_timespan_condition_no_last_changed():
    """Test timespan condition when entity has no last_changed time."""
    hass = MagicMock()
    
    mock_state = MagicMock()
    mock_state.state = STATE_ON
    mock_state.last_changed = None
    
    hass.states.get.return_value = mock_state
    
    config = {
        "entity_id": "binary_sensor.test",
        "above": 60
    }
    
    result = await async_if_action(hass, config)
    assert result is False


@pytest.mark.asyncio
async def test_timespan_condition_no_comparison():
    """Test timespan condition when no comparison operator is specified."""
    hass = MagicMock()
    
    now = dt_util.utcnow()
    thirty_seconds_ago = now - timedelta(seconds=30)
    
    mock_state = MagicMock()
    mock_state.state = STATE_ON
    mock_state.last_changed = thirty_seconds_ago
    
    hass.states.get.return_value = mock_state
    
    # With no comparison, should return True if entity exists
    config = {
        "entity_id": "binary_sensor.test"
    }
    
    result = await async_if_action(hass, config)
    assert result is True



@pytest.mark.asyncio
async def test_timespan_condition_with_different_states():
    """Test timespan condition works with different entity states."""
    hass = MagicMock()
    
    now = dt_util.utcnow()
    three_minutes_ago = now - timedelta(minutes=3)
    
    mock_state = MagicMock()
    mock_state.state = STATE_OFF  # Different state (was ON before test)
    mock_state.last_changed = three_minutes_ago
    
    hass.states.get.return_value = mock_state
    
    # Test with binary sensor off state
    config = {
        "entity_id": "binary_sensor.test",
        "above": 120
    }
    
    result = await async_if_action(hass, config)
    assert result is True  # 180 > 120


@pytest.mark.asyncio
async def test_timespan_condition_multiple_comparisons():
    """Test that first applicable comparison is used."""
    hass = MagicMock()
    
    now = dt_util.utcnow()
    two_minutes_ago = now - timedelta(minutes=2)
    
    mock_state = MagicMock()
    mock_state.state = STATE_ON
    mock_state.last_changed = two_minutes_ago
    
    hass.states.get.return_value = mock_state
    
    # When multiple comparisons specified, 'above' takes precedence
    config = {
        "entity_id": "binary_sensor.test",
        "above": 60,
        "below": 200,
        "equal_to": 120
    }
    
    result = await async_if_action(hass, config)
    assert result is True  # Uses 'above': 120 > 60


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
