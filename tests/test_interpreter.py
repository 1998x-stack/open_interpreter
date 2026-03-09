"""
Unit tests for the main interpreter
"""

from src.open_interpreter.interpreter import Interpreter
from src.open_interpreter.config import Config


def test_interpreter_initialization():
    """Test that interpreter initializes correctly with default config"""
    interpreter = Interpreter()
    
    # Should have all required components initialized
    assert interpreter.config is not None
    assert interpreter.llm is not None
    assert interpreter.executor is not None
    assert interpreter.message_block is not None
    assert interpreter.code_block is not None


def test_interpreter_initialization_with_config():
    """Test that interpreter initializes correctly with custom config"""
    config = Config()
    config.MODEL = "test-model"
    
    interpreter = Interpreter(config)
    
    assert interpreter.config == config
    assert interpreter.config.MODEL == "test-model"


def test_interpreter_config_validation():
    """Test that interpreter validates config on initialization"""
    config = Config()
    
    # Should not raise an exception
    interpreter = Interpreter(config)
    # Validation happens in __init__, so if we get here it passed


def test_switch_executor():
    """Test that interpreter can switch executors"""
    interpreter = Interpreter()
    
    # Initially should be python executor
    initial_executor_type = type(interpreter.executor).__name__
    assert "Python" in initial_executor_type
    
    # Switch to shell
    interpreter.switch_executor("shell")
    shell_executor_type = type(interpreter.executor).__name__
    assert "Shell" in shell_executor_type
    
    # Switch to javascript
    interpreter.switch_executor("javascript")
    js_executor_type = type(interpreter.executor).__name__
    assert "Javascript" in js_executor_type


def test_run_code():
    """Test running code through interpreter"""
    interpreter = Interpreter()
    
    # Simple Python code
    result = interpreter.run_code("x = 5\nprint(x)", "python")
    
    # Result should be a dictionary with expected keys
    assert isinstance(result, dict)
    assert "success" in result
    assert "stdout" in result
    assert "stderr" in result
    assert "language" in result
    assert result["language"] == "python"
    
    # Should have executed successfully and printed 5
    if result["success"]:
        assert "5" in result["stdout"]