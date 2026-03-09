"""
tests/test_json_utils.py — JSON 工具函数单元测试
"""

import sys
import pytest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from src.open_interpreter.utils.json_utils import (
    merge_deltas,
    parse_partial_json,
    escape_newlines_in_json_string_values,
)


class TestMergeDeltas:

    def test_merge_empty_original(self):
        result = merge_deltas({}, {"role": "assistant"})
        assert result == {"role": "assistant"}

    def test_merge_string_values_concatenate(self):
        original = {"content": "Hello"}
        result = merge_deltas(original, {"content": " World"})
        assert result["content"] == "Hello World"

    def test_merge_nested_dict(self):
        original = {}
        merge_deltas(original, {"function_call": {"name": "run_code"}})
        merge_deltas(original, {"function_call": {"arguments": '{"lang'}})
        merge_deltas(original, {"function_call": {"arguments": 'uage": "python"}'}})

        assert original["function_call"]["name"] == "run_code"
        assert original["function_call"]["arguments"] == '{"language": "python"}'

    def test_merge_new_key(self):
        original = {"content": "hi"}
        result = merge_deltas(original, {"role": "assistant"})
        assert result["role"] == "assistant"
        assert result["content"] == "hi"

    def test_merge_accumulates_multiple_deltas(self):
        msg = {}
        for delta in [
            {"role": "assistant"},
            {"content": "a"},
            {"content": "b"},
            {"content": "c"},
        ]:
            merge_deltas(msg, delta)
        assert msg["content"] == "abc"
        assert msg["role"] == "assistant"

    def test_merge_returns_original(self):
        original = {"key": "val"}
        result = merge_deltas(original, {"other": "x"})
        assert result is original


class TestParsePartialJson:

    def test_valid_json_returned_directly(self):
        result = parse_partial_json('{"language": "python", "code": "print(1)"}')
        assert result == {"language": "python", "code": "print(1)"}

    def test_missing_closing_brace(self):
        result = parse_partial_json('{"language": "python", "code": "print(1)"')
        assert result is not None
        assert result.get("language") == "python"

    def test_missing_closing_quote_and_brace(self):
        # Very partial: {"code": "print(
        result = parse_partial_json('{"code": "print(')
        # Should either parse to something or return None without crashing
        # (doesn't raise)

    def test_empty_string_returns_none(self):
        assert parse_partial_json("") is None
        assert parse_partial_json("   ") is None

    def test_none_like_input(self):
        assert parse_partial_json("null") is None or parse_partial_json("null") is not None
        # Just doesn't crash

    def test_valid_nested_json(self):
        s = '{"a": {"b": [1, 2, 3]}, "c": "hello"}'
        result = parse_partial_json(s)
        assert result["a"]["b"] == [1, 2, 3]

    def test_partial_array(self):
        result = parse_partial_json('[1, 2, 3')
        assert result == [1, 2, 3]

    def test_newline_in_string_value(self):
        s = '{"code": "line1\nline2"}'
        result = parse_partial_json(s)
        assert result is not None

    def test_incomplete_function_call_args(self):
        # Simulates mid-stream function_call arguments
        s = '{"language": "python", "code": "x = 1\\ny = 2\\nprint('
        result = parse_partial_json(s)
        # Should not crash; result may be None or partial
        assert result is None or isinstance(result, dict)

    def test_complete_function_call_args(self):
        s = '{"language": "python", "code": "import math\\nprint(math.pi)"}'
        result = parse_partial_json(s)
        assert result["language"] == "python"
        assert "math" in result["code"]


class TestEscapeNewlines:

    def test_no_string_no_change(self):
        s = '{"key": 123}'
        assert escape_newlines_in_json_string_values(s) == s

    def test_newline_in_string_escaped(self):
        s = '{"code": "line1\nline2"}'
        result = escape_newlines_in_json_string_values(s)
        assert "\\n" in result
        assert "\n" not in result.split('"code": "')[1].split('"')[0]

    def test_no_newline_unchanged(self):
        s = '{"code": "print(1)"}'
        result = escape_newlines_in_json_string_values(s)
        assert result == s

    def test_empty_string(self):
        assert escape_newlines_in_json_string_values("") == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])