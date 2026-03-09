"""
Unit tests for executor factory
"""

import pytest
from src.open_interpreter.execution.executor_factory import ExecutorFactory
from src.open_interpreter.execution.base_executor import BaseExecutor
from src.open_interpreter.execution.python_executor import PythonExecutor
from src.open_interpreter.execution.shell_executor import ShellExecutor
from src.open_interpreter.execution.javascript_executor import JavascriptExecutor


def test_create_python_executor():
    """Test creating Python executor"""
    executor = ExecutorFactory.create("python")
    assert isinstance(executor, PythonExecutor)
    assert isinstance(executor, BaseExecutor)


def test_create_shell_executor():
    """Test creating Shell executor"""
    executor = ExecutorFactory.create("shell")
    assert isinstance(executor, ShellExecutor)
    assert isinstance(executor, BaseExecutor)


def test_create_javascript_executor():
    """Test creating JavaScript executor"""
    executor = ExecutorFactory.create("javascript")
    assert isinstance(executor, JavascriptExecutor)
    assert isinstance(executor, BaseExecutor)


def test_executor_aliases():
    """Test executor aliases work correctly"""
    # Bash should map to ShellExecutor
    bash_executor = ExecutorFactory.create("bash")
    assert isinstance(bash_executor, ShellExecutor)
    
    # JS should map to JavascriptExecutor
    js_executor = ExecutorFactory.create("js")
    assert isinstance(js_executor, JavascriptExecutor)


def test_unknown_executor_raises_error():
    """Test that requesting unknown executor raises error"""
    with pytest.raises(ValueError, match="Unknown executor type: nonexistent"):
        ExecutorFactory.create("nonexistent")


def test_case_insensitive_creation():
    """Test that executor creation is case insensitive"""
    executor = ExecutorFactory.create("PYTHON")
    assert isinstance(executor, PythonExecutor)
    
    executor = ExecutorFactory.create("Shell")
    assert isinstance(executor, ShellExecutor)


def test_register_custom_executor():
    """Test registering and creating a custom executor"""
    class CustomExecutor(BaseExecutor):
        def execute(self, code: str, timeout=None):
            return {"success": True, "stdout": "custom", "stderr": ""}
        
        def validate_syntax(self, code: str) -> bool:
            return True
        
        def get_environment_info(self):
            return {"type": "custom"}
    
    # Register the custom executor
    ExecutorFactory.register("custom", CustomExecutor)
    
    # Create and test it
    executor = ExecutorFactory.create("custom")
    assert isinstance(executor, CustomExecutor)
    assert isinstance(executor, BaseExecutor)