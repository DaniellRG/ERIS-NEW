# -*- coding: utf-8 -*-
"""Tests automáticos para actions\weather_report.py"""
import pytest

from actions.weather_report import weather_action

def test_weather_action_basic():
    """Test básico para weather_action."""
    result = weather_action(parameters={}, player=None)
    assert result is not None
    assert isinstance(result, str)


def test_weather_action_action_list():
    """Test acción list/status."""
    result = weather_action(parameters={"action": "list"}, player=None)
    assert result is not None
    assert isinstance(result, str)


def test_weather_action_empty_params():
    """Test con parámetros vacíos."""
    result = weather_action(parameters=None, player=None)
    assert result is not None

