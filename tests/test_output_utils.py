"""
tests/test_output_utils.py — 输出处理工具单元测试
"""

import sys
import pytest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from src.open_interpreter.utils.output_utils import (
    truncate_output,
    fix_code_indentation,
    sanitize_output,
)


class TestTruncateOutput:

    def test_short_output_unchanged(self):
        data = "Hello World"
        assert truncate_output(data, max_chars=100) == data

    def test_exact_limit_unchanged(self):
        data = "x" * 100
        assert truncate_output(data, max_chars=100) == data

    def test_long_output_truncated(self):
        data = "a" * 3000
        result = truncate_output(data, max_chars=100)
        assert "Output truncated" in result
        assert len(result) < len(data)

    def test_truncated_preserves_tail(self):
        data = "START" + "x" * 3000 + "END"
        result = truncate_output(data, max_chars=200)
        assert "END" in result
        assert "START" not in result  # START is truncated away

    def test_double_truncation_message_not_doubled(self):
        """连续两次截断不应该叠加前缀（第二次截断时先剥离旧前缀）"""
        data = "x" * 3000
        result1 = truncate_output(data, max_chars=100)
        # result1 = "Output truncated...prefix\n\n" + "x"*100
        assert "Output truncated" in result1

        # 第二次截断：先剥离 result1 中的前缀，剩余恰好 100 字符，不再触发截断
        # 所以 result2 = "x" * 100，不含截断前缀 — 这是正确行为
        result2 = truncate_output(result1, max_chars=100)
        # 核心保证：result2 不包含两个截断前缀（前缀被剥离后不再叠加）
        assert result2.count("Output truncated") <= 1

    def test_empty_string(self):
        assert truncate_output("", max_chars=100) == ""

    def test_custom_max_chars(self):
        data = "a" * 500
        result = truncate_output(data, max_chars=50)
        assert len(result) <= 200  # message header + 50 chars


class TestFixCodeIndentation:

    def test_simple_for_loop(self):
        code = "for i in range(3):\n    print(i)\nprint('done')"
        result = fix_code_indentation(code)
        # 缩进块后应插入空行
        lines = result.split("\n")
        # 找到 print('done') 前是否有空行
        done_idx = next(i for i, l in enumerate(lines) if "print('done')" in l)
        assert lines[done_idx - 1] == ""

    def test_no_indent_no_change_needed(self):
        code = "x = 1\ny = 2\nprint(x + y)"
        result = fix_code_indentation(code)
        # 没有缩进块，不需要额外空行，行数不变
        assert result.count("\n") == code.count("\n")

    def test_preserves_code_content(self):
        code = "for i in range(5):\n    print(i)\nresult = 42"
        result = fix_code_indentation(code)
        assert "for i in range(5):" in result
        assert "    print(i)" in result
        assert "result = 42" in result

    def test_empty_string(self):
        assert fix_code_indentation("") == ""

    def test_single_line(self):
        code = "print('hello')"
        result = fix_code_indentation(code)
        assert result == code

    def test_nested_indentation(self):
        code = "class Foo:\n    def bar(self):\n        return 1\nfoo = Foo()"
        result = fix_code_indentation(code)
        assert "class Foo:" in result
        assert "foo = Foo()" in result


class TestSanitizeOutput:

    def test_removes_active_line(self):
        raw = "ACTIVE_LINE:1\nhello\nACTIVE_LINE:2\nworld"
        result = sanitize_output(raw)
        assert "ACTIVE_LINE" not in result
        assert "hello" in result
        assert "world" in result

    def test_removes_end_of_execution(self):
        raw = "some output\nEND_OF_EXECUTION"
        result = sanitize_output(raw)
        assert "END_OF_EXECUTION" not in result
        assert "some output" in result

    def test_mixed_markers(self):
        raw = "ACTIVE_LINE:1\nfirst line\nACTIVE_LINE:2\nsecond line\nEND_OF_EXECUTION"
        result = sanitize_output(raw)
        assert result == "first line\nsecond line"

    def test_empty_string(self):
        assert sanitize_output("") == ""

    def test_no_markers_unchanged(self):
        raw = "Hello World\nNo markers here"
        result = sanitize_output(raw)
        assert result == raw.strip()

    def test_only_markers_returns_empty(self):
        raw = "ACTIVE_LINE:1\nEND_OF_EXECUTION"
        result = sanitize_output(raw)
        assert result == ""

    def test_whitespace_stripped(self):
        raw = "  ACTIVE_LINE:1  \n  output  \n  END_OF_EXECUTION  "
        result = sanitize_output(raw)
        assert "ACTIVE_LINE" not in result
        assert "END_OF_EXECUTION" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])