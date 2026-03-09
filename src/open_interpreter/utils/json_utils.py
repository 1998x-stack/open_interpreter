"""
utils/json_utils.py — JSON 工具函数

- merge_deltas: 合并 OpenAI 流式 delta 到完整消息对象
- parse_partial_json: 容错解析不完整 JSON（流式 function_call arguments）
- escape_newlines_in_json_string_values: 修复 JSON 字符串中的裸换行符
"""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any

from loguru import logger


# ── merge_deltas ────────────────────────────────────────────────

def merge_deltas(original: dict, delta: dict) -> dict:
    """
    将 OpenAI 流式响应的 delta 合并进 original 消息对象。

    规则：
    - dict 类型：递归合并
    - str / 其他类型：拼接（+=）

    Examples
    --------
    >>> merge_deltas({}, {"role": "assistant"})
    {'role': 'assistant'}
    >>> merge_deltas({"content": "hello"}, {"content": " world"})
    {'content': 'hello world'}
    """
    logger.debug(f"merge_deltas: delta_keys={list(delta.keys())}")
    try:
        if original is None:
            original = {}
        for key, value in delta.items():
            if value is None:
                original[key] = None
            elif isinstance(value, dict):
                if key not in original or original[key] is None:
                    original[key] = {}
                merge_deltas(original[key], value)
            else:
                if key in original and original[key] is not None and value is not None:
                    original[key] += value
                elif value is not None:
                    original[key] = value
        return original
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.error(f"[json_utils] merge_deltas 失败: {error_message}")
        raise


# ── escape_newlines_in_json_string_values ───────────────────────

def escape_newlines_in_json_string_values(s: str) -> str:
    """
    将 JSON 字符串值内部的裸换行符转义为 \\n。

    GPT 的 function_call arguments 流式输出有时会包含未转义的换行，
    导致 json.loads 失败。此函数在解析前修复这类问题。

    Examples
    --------
    >>> s = '{"code": "print(\\"hi\\")'
    >>> escape_newlines_in_json_string_values(s) == s
    True
    """
    result: list[str] = []
    in_string = False

    for ch in s:
        if ch == '"' and (not result or result[-1] != "\\"):
            in_string = not in_string
        if in_string and ch == "\n":
            result.append("\\n")
        else:
            result.append(ch)

    return "".join(result)


# ── parse_partial_json ──────────────────────────────────────────

def parse_partial_json(s: str) -> Any | None:
    """
    尝试解析可能不完整的 JSON 字符串。

    策略：
    1. 直接 json.loads（已完整）
    2. 修复裸换行符
    3. 追踪未闭合的括号/引号，补全后再次解析
    4. 仍失败则返回 None

    Parameters
    ----------
    s : str
        待解析的字符串（可能是部分 JSON）

    Returns
    -------
    解析结果（dict / list / str 等），或 None（解析失败）

    Examples
    --------
    >>> parse_partial_json('{"language": "python", "code": "print(1)')
    is not None  # True
    """
    logger.debug(f"parse_partial_json: input_length={len(s)}")

    if not s or not s.strip():
        return None

    # Handle the most common case: just the opening part like {"language"
    # These need to be handled specially as they don't have any values yet
    if s.strip() in ('{', '{"', '{"l', '{"la', '{"lan', '{"lang', '{"langu',
                      '{"langua', '{"languag', '{"language', '{"language"',
                      '{"language":', '{"language": "'):
        # Not much we can do with these, return None but don't log as warning
        # as these are expected during streaming
        return None

    # 1. 尝试直接解析
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # 2. 修复裸换行
    s = escape_newlines_in_json_string_values(s)

    # 3. Use a proper parser to understand the JSON structure
    stack = []  # Track open braces/brackets
    in_string = False  # Track if we're inside a string
    escaped = False  # Track if the next character is escaped

    for char in s:
        if escaped:
            escaped = False
            continue

        if char == '\\':
            escaped = True
        elif char == '"' and not escaped:
            in_string = not in_string
        elif not in_string:
            if char in '{[':
                stack.append(char)
            elif char == '}' and stack and stack[-1] == '{':
                stack.pop()
            elif char == ']' and stack and stack[-1] == '[':
                stack.pop()

    # Now complete the JSON by closing all open structures
    result = s

    # If we're in a string, close it
    if in_string:
        result += '"'

    # Close any remaining open objects/arrays in reverse order
    while stack:
        top = stack.pop()
        if top == '{':
            result += '}'
        elif top == '[':
            result += ']'

    # Try parsing the completed JSON
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        # Handle specific common incomplete function call patterns for our use case
        if '"run_code"' in s or '"language"' in s or '"code"' in s:
            # This is likely a function call in progress, try to construct expected shape
            import re

            # Try to extract the key-value pairs that are complete
            result_dict = {}

            # Extract language if complete
            lang_match = re.search(r'"language"\s*:\s*"([^"]*)"', s)
            if lang_match:
                result_dict['language'] = lang_match.group(1)

            # Extract code if complete (handling potential multiline content)
            # Look for the "code": "..." pattern, being mindful of escape sequences
            code_match = re.search(r'"code"\s*:\s*"((?:[^"]|\\.)*)', s, re.DOTALL)
            if code_match:
                code_content = code_match.group(1)
                # If the match doesn't end the string or ends without closing quote,
                # it's an incomplete code value
                code_full_match = code_match.group(0)
                pos_after_code = s.find(code_full_match) + len(code_full_match)
                if pos_after_code < len(s) and s[pos_after_code-1] != '"':
                    # The code string is not closed yet, but we can still return what we have
                    result_dict['code'] = code_content
                else:
                    # Check if the string properly closes
                    remaining = s[pos_after_code:]
                    if remaining.strip().startswith(',') or remaining.strip().startswith('}'):
                        result_dict['code'] = code_content

            if result_dict:
                return result_dict

        # If the manual completion didn't work, try simpler fixes
        # Try trimming the string bit by bit until it parses
        for i in range(len(result), 0, -1):
            try:
                sub = result[:i]
                # Add back a quote if we seem to be mid-string
                if sub.count('"') % 2 == 1:  # Odd number of quotes
                    test_str = sub + '"'
                else:
                    test_str = sub

                # Try to complete brackets if needed
                temp_stack = []
                temp_in_string = False
                temp_escaped = False

                for char in test_str:
                    if temp_escaped:
                        temp_escaped = False
                        continue
                    if char == '\\':
                        temp_escaped = True
                    elif char == '"' and not temp_escaped:
                        temp_in_string = not temp_in_string
                    elif not temp_in_string:
                        if char in '{[':
                            temp_stack.append(char)
                        elif char == '}' and temp_stack and temp_stack[-1] == '{':
                            temp_stack.pop()
                        elif char == ']' and temp_stack and temp_stack[-1] == '[':
                            temp_stack.pop()

                # Complete the test string
                complete_test = test_str
                if temp_in_string and not temp_escaped:
                    complete_test += '"'
                while temp_stack:
                    top = temp_stack.pop()
                    if top == '{':
                        complete_test += '}'
                    elif top == '[':
                        complete_test += ']'

                parsed_result = json.loads(complete_test)
                if isinstance(parsed_result, dict):
                    # Verify this result makes sense for our use case
                    if 'language' in parsed_result or 'code' in parsed_result:
                        return parsed_result
            except json.JSONDecodeError:
                continue

        # Only log warning for genuinely problematic cases, not expected streaming fragments
        if len(s) > 15:  # If it's not just a short fragment
            logger.warning(f"parse_partial_json: 仍无法解析，返回 None. snippet={s[:80]!r}")

        return None


# ── standalone 演示 ─────────────────────────────────────────────
if __name__ == "__main__":
    # merge_deltas 演示
    msg: dict = {}
    for delta in [
        {"role": "assistant"},
        {"content": "Hello"},
        {"content": " world"},
        {"function_call": {"name": "run_code"}},
        {"function_call": {"arguments": '{"lan'}},
        {"function_call": {"arguments": 'guage": "python"}'}},
    ]:
        merge_deltas(msg, delta)

    print("Merged message:", json.dumps(msg, ensure_ascii=False, indent=2))

    # parse_partial_json 演示
    cases = [
        '{"language": "python", "code": "print(1)',   # missing closing }
        '{"language": "python", "code": "x = 1\ny = 2"}',  # valid
        '{"code": "',                                  # very incomplete
        "",                                            # empty
    ]
    for c in cases:
        result = parse_partial_json(c)
        print(f"Input: {c[:40]!r}  →  {result}")