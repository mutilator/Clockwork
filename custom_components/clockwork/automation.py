"""Automation conditions for Clockwork integration.

This module maintains backward compatibility. The actual condition logic
has been moved to conditions/timespan.py, which is the proper Home Assistant platform.
"""
from .condition.timespan import CONDITION_SCHEMA, async_if_action, if_action

__all__ = ["CONDITION_SCHEMA", "async_if_action", "if_action"]




