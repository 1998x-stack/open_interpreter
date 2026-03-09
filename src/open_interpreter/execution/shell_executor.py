"""
execution/shell_executor.py — Shell/Bash 代码执行器

使用系统 shell（Linux/Mac: $SHELL 或 bash，Windows: cmd.exe）执行代码。
限制：
- 行号注入仅对单行代码有效
- 多行代码、含循环的代码跳过行号注入
"""

from __future__ import annotations

import os
import platform
import sys
import traceback

from loguru import logger

from .base_executor import BaseExecutor


def _get_shell_cmd() -> str:
    if platform.system() == "Windows":
        return "cmd.exe"
    return os.environ.get("SHELL", "bash")


class ShellExecutor(BaseExecutor):
    """
    Shell/Bash 代码执行器。

    注意：Shell 执行器无法跨 run() 调用保持状态
    （不像 Python -i 的交互会话）。每次执行是相对独立的。
    """

    START_CMD = _get_shell_cmd()
    PRINT_CMD = 'echo "{}"'

    def add_active_line_prints(self, code: str) -> str:
        """
        Shell 行号注入的限制较多，以下情况直接返回原代码：
        - 多行代码（行数 > 1）
        - 含 for / do / done 关键字（循环）
        - 任何行以空白字符开头（缩进块）
        """
        code_lines = code.strip().split("\n")

        skip_triggers = ("for", "do", "done", "while", "if", "then", "fi")
        if len(code_lines) > 1:
            logger.debug("[shell_executor] 跳过行号注入（多行代码）")
            return code
        if any(kw in code for kw in skip_triggers):
            logger.debug("[shell_executor] 跳过行号注入（含控制语句）")
            return code
        for line in code_lines:
            if line.startswith(" ") or line.startswith("\t"):
                logger.debug("[shell_executor] 跳过行号注入（含缩进行）")
                return code

        # 单行：注入
        modified: list[str] = []
        for i, line in enumerate(code_lines):
            modified.append(self.PRINT_CMD.format(f"ACTIVE_LINE:{i + 1}"))
            modified.append(line)

        return "\n".join(modified)


# ── standalone 演示 ─────────────────────────────────────────────
if __name__ == "__main__":
    executor = ShellExecutor(debug_mode=False)

    class _DummyBlock:
        active_line = None
        output = ""
        language = "shell"
        def refresh(self): pass
        def end(self): pass

    executor.active_block = _DummyBlock()  # type: ignore

    print("=== Shell 测试 1：echo ===")
    out = executor.run('echo "Hello from shell"')
    print(f"Output: {out!r}\n")

    print("=== Shell 测试 2：pwd ===")
    out = executor.run("pwd")
    print(f"Output: {out!r}\n")

    executor.stop()