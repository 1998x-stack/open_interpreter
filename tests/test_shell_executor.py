"""
Unit tests for Shell executor
"""

import os
from src.open_interpreter.execution.shell_executor import ShellExecutor


def test_execute_simple_shell_command():
    """Test executing a simple shell command"""
    executor = ShellExecutor()
    result = executor.execute("echo 'Hello, World!'")
    
    assert result["success"] is True
    assert result["stdout"].strip() == "Hello, World!"
    assert result["stderr"] == ""
    assert result["language"] == "shell"


def test_execute_shell_with_multiple_commands():
    """Test executing multiple shell commands"""
    executor = ShellExecutor()
    result = executor.execute("echo 'First'; echo 'Second'")
    
    assert result["success"] is True
    stdout_lines = result["stdout"].strip().split('\n')
    assert "First" in stdout_lines
    assert "Second" in stdout_lines
    assert result["stderr"] == ""
    assert result["language"] == "shell"


def test_execute_shell_command_with_error():
    """Test executing a shell command that produces an error"""
    executor = ShellExecutor()
    result = executor.execute("ls /nonexistent_directory_12345")
    
    assert result["success"] is False
    assert result["return_code"] != 0
    assert result["language"] == "shell"


def test_validate_syntax_non_empty():
    """Test that shell validation accepts non-empty commands"""
    executor = ShellExecutor()
    
    # Should accept non-empty commands
    assert executor.validate_syntax("echo hello") is True
    assert executor.validate_syntax("ls -la") is True


def test_validate_syntax_empty():
    """Test that shell validation rejects empty commands"""
    executor = ShellExecutor()
    
    # Should reject empty commands
    assert executor.validate_syntax("") is False
    assert executor.validate_syntax("   ") is False  # Just whitespace


def test_get_environment_info():
    """Test getting shell environment information"""
    executor = ShellExecutor()
    info = executor.get_environment_info()
    
    # Should contain basic environment info
    assert "shell" in info
    assert "platform" in info
    assert "user" in info
    assert "home_directory" in info