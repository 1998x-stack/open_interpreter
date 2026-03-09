"""
Unit tests for configuration module
"""

import os
import tempfile
from unittest.mock import patch
from src.open_interpreter.config import Config


def test_default_config_values():
    """Test that default configuration values are set correctly"""
    config = Config()
    
    # Test default values
    assert config.OPENAI_API_KEY == ""
    assert config.OPENAI_BASE_URL == "https://api.openai.com/v1"
    assert config.MODEL == "gpt-4o"
    assert config.MAX_OUTPUT_LENGTH == 1000
    assert config.TIMEOUT_SECONDS == 30
    assert config.THEME == "dark"
    assert config.SHOW_TIMESTAMPS is True


def test_config_from_environment():
    """Test that config values can be overridden by environment variables"""
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test-key-123',
        'OPENAI_BASE_URL': 'https://test-api.example.com/v1',
        'MODEL': 'gpt-5-test',
        'MAX_OUTPUT_LENGTH': '2000',
        'TIMEOUT_SECONDS': '60',
        'THEME': 'light',
        'SHOW_TIMESTAMPS': 'false'
    }):
        config = Config()
        
        assert config.OPENAI_API_KEY == 'test-key-123'
        assert config.OPENAI_BASE_URL == 'https://test-api.example.com/v1'
        assert config.MODEL == 'gpt-5-test'
        assert config.MAX_OUTPUT_LENGTH == 2000
        assert config.TIMEOUT_SECONDS == 60
        assert config.THEME == 'light'
        assert config.SHOW_TIMESTAMPS is False


def test_config_validation():
    """Test configuration validation"""
    config = Config()
    
    # Should not raise an exception with valid values
    config.validate()
    
    # Temporarily set invalid timeout
    original_timeout = config.TIMEOUT_SECONDS
    config.TIMEOUT_SECONDS = -5
    try:
        config.validate()
        assert False, "Expected ValueError for negative timeout"
    except ValueError as e:
        assert "TIMEOUT_SECONDS must be positive" in str(e)
    
    # Restore valid value
    config.TIMEOUT_SECONDS = original_timeout
    
    # Temporarily set invalid max output length
    original_max_len = config.MAX_OUTPUT_LENGTH
    config.MAX_OUTPUT_LENGTH = 0
    try:
        config.validate()
        assert False, "Expected ValueError for zero max output length"
    except ValueError as e:
        assert "MAX_OUTPUT_LENGTH must be positive" in str(e)
    
    # Restore valid value
    config.MAX_OUTPUT_LENGTH = original_max_len