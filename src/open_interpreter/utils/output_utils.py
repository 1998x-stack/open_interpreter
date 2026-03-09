"""
utils/output_utils.py — 执行输出处理工具

- truncate_output: 截断过长的执行输出
- fix_code_indentation: 修复 `python -i` 交互模式的缩进问题
- sanitize_output: 过滤控制标记（ACTIVE_LINE / END_OF_EXECUTION）
"""

from __future__ import annotations

import sys
import traceback

from loguru import logger


# ── truncate_output ─────────────────────────────────────────────

def truncate_output(data: str, max_chars: int = 2000) -> str:
    """
    若输出超过 max_chars，保留末尾最重要的部分，前缀加截断提示。

    Parameters
    ----------
    data : str
        原始执行输出
    max_chars : int
        最大保留字符数，默认 2000

    Returns
    -------
    str
        截断后的输出

    Examples
    --------
    >>> truncate_output("a" * 3000, max_chars=100)[:40]
    'Output truncated. Showing the last 100 c'
    """
    try:
        message = f"Output truncated. Showing the last {max_chars} characters.\n\n"

        # 去掉上一次已加的截断提示，避免重复叠加
        if data.startswith(message):
            data = data[len(message):]

        if len(data) > max_chars:
            logger.warning(
                f"[output_utils] 输出超过 {max_chars} 字符，已截断 (原始长度={len(data)})"
            )
            data = message + data[-max_chars:]

        return data
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.error(f"[output_utils] truncate_output 失败: {error_message}")
        raise


# ── fix_code_indentation ─────────────────────────────────────────

def fix_code_indentation(code: str) -> str:
    """
    为 `python -i` 交互模式修复代码缩进。

    `python -i` 要求缩进块结束后有一个空行，否则无法识别块结束。
    此函数在每个缩进块（was_indented → not indented）之间插入空行。

    Parameters
    ----------
    code : str
        原始 Python 代码

    Returns
    -------
    str
        修复后的代码

    Examples
    --------
    >>> code = "for i in range(3):\\n    print(i)\\nprint('done')"
    >>> "\\n" in fix_code_indentation(code)
    True
    """
    try:
        lines = code.split("\n")
        fixed_lines: list[str] = []
        was_indented = False

        for line in lines:
            current_indent = len(line) - len(line.lstrip())
            if current_indent == 0 and was_indented:
                fixed_lines.append("")  # 缩进块后插入空行
            fixed_lines.append(line)
            was_indented = current_indent > 0

        return "\n".join(fixed_lines)
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.error(f"[output_utils] fix_code_indentation 失败: {error_message}")
        raise


# ── sanitize_output ──────────────────────────────────────────────

def sanitize_output(raw: str) -> str:
    """
    过滤执行引擎注入的控制标记，返回纯净的用户可见输出。

    控制标记：
    - `ACTIVE_LINE:<n>` — 行号高亮信号
    - `END_OF_EXECUTION`  — 执行完成信号

    Parameters
    ----------
    raw : str
        包含控制标记的原始输出流内容

    Returns
    -------
    str
        过滤后的可读输出
    """
    try:
        lines = []
        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("ACTIVE_LINE:"):
                continue
            if stripped == "END_OF_EXECUTION":
                continue
            lines.append(line)
        return "\n".join(lines).strip()
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.error(f"[output_utils] sanitize_output 失败: {error_message}")
        raise


# ── standalone 演示 ─────────────────────────────────────────────
if __name__ == "__main__":
    # truncate_output
    long_output = "\n".join(f"Line {i}" for i in range(500))
    truncated = truncate_output(long_output, max_chars=200)
    print(f"Truncated output (first 100 chars):\n{truncated[:100]}\n")

    # fix_code_indentation
    code = "for i in range(3):\n    print(i)\nprint('done')"
    fixed = fix_code_indentation(code)
    print(f"Fixed indentation:\n{fixed}\n")

    # sanitize_output
    raw = "ACTIVE_LINE:1\nhello\nACTIVE_LINE:2\nworld\nEND_OF_EXECUTION"
    clean = sanitize_output(raw)
    print(f"Sanitized: {clean!r}")