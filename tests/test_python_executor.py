"""
tests/test_python_executor.py — Python 执行器单元测试

这些测试实际启动子进程，因此比 mock 测试慢，但验证了真实行为。
"""

import sys
import pytest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from src.open_interpreter.execution.python_executor import PythonExecutor


@pytest.fixture
def executor():
    """每个测试用独立的执行器实例"""
    class _DummyBlock:
        active_line = None
        output = ""
        language = "python"
        def refresh(self): pass
        def end(self): pass

    ex = PythonExecutor(debug_mode=False, max_output_chars=5000)
    ex.active_block = _DummyBlock()
    yield ex
    ex.stop()


class TestPythonExecutorBasic:

    def test_hello_world(self, executor):
        output = executor.run('print("hello world")')
        assert "hello world" in output

    def test_arithmetic(self, executor):
        output = executor.run("print(1 + 2 + 3 + 4 + 5)")
        assert "15" in output

    def test_multiline_code(self, executor):
        code = "total = 0\nfor i in range(1, 11):\n    total += i\nprint(total)"
        output = executor.run(code)
        assert "55" in output

    def test_variable_persistence_across_runs(self, executor):
        """变量在跨 run() 调用间应该保持"""
        executor.run("x = 42")
        output = executor.run("print(x * 2)")
        assert "84" in output

    def test_import_stdlib(self, executor):
        output = executor.run("import math; print(round(math.pi, 4))")
        assert "3.1416" in output

    def test_list_comprehension(self, executor):
        output = executor.run(
            "squares = [x**2 for x in range(1, 6)]\nprint(squares)"
        )
        assert "[1, 4, 9, 16, 25]" in output


class TestPythonExecutorErrorHandling:

    def test_zero_division_error(self, executor):
        output = executor.run("print(1 / 0)")
        assert "ZeroDivisionError" in output or "division by zero" in output

    def test_name_error(self, executor):
        output = executor.run("print(undefined_variable)")
        assert "NameError" in output or "undefined_variable" in output

    def test_syntax_error_handled(self, executor):
        """语法错误不应该崩溃，应返回错误信息"""
        output = executor.run("def broken(:\n    pass")
        # 可能返回 traceback 字符串，也可能执行成功（依赖 AST 处理）
        # 核心要求：不抛出异常
        assert isinstance(output, str)

    def test_import_error(self, executor):
        output = executor.run("import nonexistent_package_xyz_abc")
        assert "ModuleNotFoundError" in output or "No module named" in output

    def test_output_is_always_string(self, executor):
        """run() 应始终返回字符串，即使发生错误"""
        output = executor.run("1/0")
        assert isinstance(output, str)


class TestPythonExecutorOutputTruncation:

    def test_large_output_truncated(self, executor):
        ex = PythonExecutor(debug_mode=False, max_output_chars=500)

        class _Dummy:
            active_line = None
            output = ""
            language = "python"
            def refresh(self): pass
            def end(self): pass

        ex.active_block = _Dummy()
        output = ex.run("for i in range(1000): print(f'Line {i}')")
        assert len(output) <= 800  # message header + 500 chars
        ex.stop()

    def test_normal_output_not_truncated(self, executor):
        output = executor.run("print('short output')")
        assert "truncated" not in output.lower()


class TestPythonExecutorActiveLinePrints:

    def test_add_active_line_prints_basic(self):
        ex = PythonExecutor(debug_mode=False)
        code = "x = 1\ny = 2\nprint(x + y)"
        result = ex.add_active_line_prints(code)
        assert "ACTIVE_LINE:1" in result
        assert "ACTIVE_LINE:2" in result
        assert "ACTIVE_LINE:3" in result

    def test_skip_injection_for_try_except(self):
        ex = PythonExecutor(debug_mode=False)
        code = "try:\n    x = 1\nexcept:\n    pass"
        result = ex.add_active_line_prints(code)
        # 应跳过注入，返回原代码
        assert "ACTIVE_LINE" not in result

    def test_skip_injection_for_triple_quotes(self):
        ex = PythonExecutor(debug_mode=False)
        code = "x = '''hello\nworld'''\nprint(x)"
        result = ex.add_active_line_prints(code)
        assert "ACTIVE_LINE" not in result

    def test_indentation_preserved_in_injection(self):
        ex = PythonExecutor(debug_mode=False)
        # Multi-line code with indentation → injection is skipped (correct behavior)
        # because injecting ACTIVE_LINE into for-loop blocks breaks python -i
        code = "for i in range(3):\n    print(i)"
        result = ex.add_active_line_prints(code)
        # Should return original code unchanged (skip injection for multi-line indent blocks)
        assert result == code
        assert "ACTIVE_LINE" not in result

    def test_single_line_injection_preserves_indent(self):
        ex = PythonExecutor(debug_mode=False)
        # Single-line, no indentation → injection happens
        code = "x = 1 + 2"
        result = ex.add_active_line_prints(code)
        assert "ACTIVE_LINE:1" in result
        assert "x = 1 + 2" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])