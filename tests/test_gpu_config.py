"""Tests for core/gpu_config.py"""
import os
from unittest.mock import patch, mock_open
import json


def test_configure_gpu_enabled():
    from core.gpu_config import configure_gpu
    config = {"gpu_acceleration": True}
    with patch("builtins.open", mock_open(read_data=json.dumps(config))):
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=json.dumps(config)):
                configure_gpu()
    assert os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "").startswith("--ignore-gpu-blocklist")


def test_configure_gpu_disabled():
    from core.gpu_config import configure_gpu
    config = {"gpu_acceleration": False}
    with patch("builtins.open", mock_open(read_data=json.dumps(config))):
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=json.dumps(config)):
                configure_gpu()
    assert "low-end-device-mode" in os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")


def test_configure_gpu_missing_config():
    from core.gpu_config import configure_gpu
    with patch("pathlib.Path.exists", return_value=False):
        configure_gpu()  # Should not crash
