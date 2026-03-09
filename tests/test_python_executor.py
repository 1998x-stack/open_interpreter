"""
Unit tests for Python executor
"""

import sys
from src.open_interpreter.execution.python_executor import PythonExecutor


def test_execute_simple_python_code():
    """Test executing simple Python code"""
    executor = PythonExecutor()
    result = executor.execute("print('Hello, World!')")
    
    assert result["success"] is True
    assert result["stdout"].strip() == "Hello, World!"
    assert result["stderr"] == ""
    assert result["language"] == "python"


def test_execute_python_with_return_value():
    """Test executing Python code that returns a value"""
    executor = PythonExecutor()
    result = executor.execute("x = 5\ny = 10\nprint(x + y)")
    
    assert result["success"] is True
    assert result["stdout"].strip() == "15"
    assert result["stderr"] == ""
    assert result["language"] == "python"


def test_execute_python_with_error():
    """Test executing Python code that produces an error"""
    executor = PythonExecutor()
    result = executor.execute("print(undefined_variable)")
    
    assert result["success"] is False
    assert result["return_code"] != 0
    assert "NameError" in result["stderr"]
    assert result["language"] == "python"


def test_validate_syntax_valid():
    """Test syntax validation for valid Python code"""
    executor = PythonExecutor()
    valid_code = "x = 5\nprint(x)\nif True:\n    print('test')"
    
    assert executor.validate_syntax(valid_code) is True


def test_validate_syntax_invalid():
    """Test syntax validation for invalid Python code"""
    executor = PythonExecutor()
    invalid_code = "x = 5\nprint(x\nif True:\n    print 'test'"
    
    assert executor.validate_syntax(invalid_code) is False


def test_get_environment_info():
    """Test getting Python environment information"""
    executor = PythonExecutor()
    info = executor.get_environment_info()
    
    assert "version" in info
    assert "executable" in info
    assert "platform" in info
    assert sys.version == info["version"]