"""
tests/test_executor_factory.py — ExecutorFactory 单元测试
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from src.open_interpreter.execution.base_executor import BaseExecutor
from src.open_interpreter.execution.executor_factory import ExecutorFactory
from src.open_interpreter.execution.python_executor import PythonExecutor
from src.open_interpreter.execution.shell_executor import ShellExecutor


@pytest.fixture(autouse=True)
def reset_factory():
    """每个测试前重置工厂状态，避免测试间污染"""
    # 保存原始注册表
    original_registry = dict(ExecutorFactory._registry)
    original_instances = dict(ExecutorFactory._instances)

    yield

    # 停止所有测试中创建的实例
    for lang, inst in list(ExecutorFactory._instances.items()):
        if lang not in original_instances:
            try:
                inst.stop()
            except Exception:
                pass

    # 恢复原始状态
    ExecutorFactory._registry = original_registry
    ExecutorFactory._instances = original_instances


class TestExecutorFactoryRegistration:

    def test_builtin_languages_registered(self):
        languages = ExecutorFactory.list_languages()
        assert "python" in languages
        assert "shell" in languages
        assert "javascript" in languages

    def test_register_custom_language(self):
        class DummyExecutor(BaseExecutor):
            START_CMD = "echo"
            PRINT_CMD = 'echo "{}"'
            def add_active_line_prints(self, code): return code

        ExecutorFactory.register("dummy", DummyExecutor)
        assert ExecutorFactory.is_registered("dummy")
        assert "dummy" in ExecutorFactory.list_languages()

    def test_register_overrides_existing(self):
        class NewPythonExecutor(BaseExecutor):
            START_CMD = "python3"
            PRINT_CMD = 'print("{}")'
            def add_active_line_prints(self, code): return code

        ExecutorFactory.register("python", NewPythonExecutor)
        assert ExecutorFactory._registry["python"] is NewPythonExecutor

    def test_is_registered_case_insensitive(self):
        assert ExecutorFactory.is_registered("Python")
        assert ExecutorFactory.is_registered("SHELL")
        assert ExecutorFactory.is_registered("python")

    def test_unknown_language_not_registered(self):
        assert not ExecutorFactory.is_registered("ruby")
        assert not ExecutorFactory.is_registered("rust")


class TestExecutorFactoryCreate:

    def test_create_unknown_raises_value_error(self):
        with pytest.raises(ValueError, match="未知语言"):
            ExecutorFactory.create("ruby")

    def test_create_python_returns_python_executor(self):
        executor = ExecutorFactory.create("python", reuse=False)
        assert isinstance(executor, PythonExecutor)
        executor.stop()

    def test_create_shell_returns_shell_executor(self):
        executor = ExecutorFactory.create("shell", reuse=False)
        assert isinstance(executor, ShellExecutor)
        executor.stop()

    def test_reuse_returns_same_instance(self):
        e1 = ExecutorFactory.create("python", reuse=True)
        e2 = ExecutorFactory.create("python", reuse=True)
        assert e1 is e2
        ExecutorFactory.stop_all()

    def test_no_reuse_returns_different_instance(self):
        e1 = ExecutorFactory.create("python", reuse=False)
        e2 = ExecutorFactory.create("python", reuse=False)
        assert e1 is not e2
        e1.stop()
        e2.stop()

    def test_create_propagates_debug_mode(self):
        executor = ExecutorFactory.create("python", debug_mode=True, reuse=False)
        assert executor.debug_mode is True
        executor.stop()

    def test_create_propagates_max_output_chars(self):
        executor = ExecutorFactory.create("python", max_output_chars=999, reuse=False)
        assert executor.max_output_chars == 999
        executor.stop()

    def test_error_message_includes_available_languages(self):
        with pytest.raises(ValueError) as exc_info:
            ExecutorFactory.create("cobol")
        assert "python" in str(exc_info.value).lower() or "已注册" in str(exc_info.value)


class TestExecutorFactoryLifecycle:

    def test_stop_all_clears_instances(self):
        ExecutorFactory.create("python", reuse=True)
        assert len(ExecutorFactory._instances) >= 1
        ExecutorFactory.stop_all()
        assert len(ExecutorFactory._instances) == 0

    def test_reset_clears_registry(self):
        original_count = len(ExecutorFactory._registry)
        ExecutorFactory.reset()
        assert len(ExecutorFactory._registry) == 0

        # 恢复（fixture 会处理）


if __name__ == "__main__":
    pytest.main([__file__, "-v"])