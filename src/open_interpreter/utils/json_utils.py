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
        for key, value in delta.items():
            if isinstance(value, dict):
                if key not in original:
                    original[key] = value
                else:
                    merge_deltas(original[key], value)
            else:
                if key in original:
                    original[key] += value
                else:
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

    # 1. 尝试直接解析
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # 2. 修复裸换行
    s = escape_newlines_in_json_string_values(s)

    # 3. 追踪结构，补全括号
    stack: list[str] = []
    is_inside_string = False

    for char in s:
        if char == '"':
            if stack and stack[-1] == "\\":
                stack.pop()
            else:
                is_inside_string = not is_inside_string
        elif not is_inside_string:
            if char in ("{", "["):
                stack.append(char)
            elif char in ("}", "]"):
                if stack and stack[-1] in ("{", "["):
                    stack.pop()

    if is_inside_string:
        s += '"'

    while stack:
        open_char = stack.pop()
        s += "}" if open_char == "{" else "]"

    try:
        return json.loads(s)
    except json.JSONDecodeError:
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