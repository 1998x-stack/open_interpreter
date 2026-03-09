"""
execution/javascript_executor.py — JavaScript / Node.js 代码执行器

使用 `node -i`（交互模式）执行 JavaScript 代码。
需要系统已安装 Node.js。
"""

from __future__ import annotations

import shutil
import sys
import traceback

from loguru import logger

from .base_executor import BaseExecutor


class JavaScriptExecutor(BaseExecutor):
    """
    JavaScript 代码执行器（Node.js -i 交互模式）。

    与 PythonExecutor 类似，支持跨 run() 调用的会话状态保持。
    """

    START_CMD = "node -i"
    PRINT_CMD = 'console.log("{}")'

    def __init__(self, **kwargs) -> None:
        # 检查 node 是否可用
        if not shutil.which("node"):
            logger.warning(
                "[javascript_executor] 未找到 node 命令。"
                "请安装 Node.js: https://nodejs.org"
            )
        super().__init__(**kwargs)

    def add_active_line_prints(self, code: str) -> str:
        """注入 console.log("ACTIVE_LINE:<n>") 行号打印。"""
        # 跳过含特殊语法的情况
        skip_triggers = ("try", "catch", "`",)  # 模板字符串也跳过
        if any(t in code for t in skip_triggers):
            logger.debug("[javascript_executor] 跳过行号注入（含特殊语法）")
            return code

        code_lines = code.strip().split("\n")
        modified: list[str] = []

        for i, line in enumerate(code_lines):
            leading_whitespace = ""
            for next_line in code_lines[i:]:
                if next_line.strip():
                    leading_whitespace = next_line[: len(next_line) - len(next_line.lstrip())]
                    break

            print_line = leading_whitespace + self.PRINT_CMD.format(f"ACTIVE_LINE:{i + 1}")
            modified.append(print_line)
            modified.append(line)

        return "\n".join(modified)


# ── standalone 演示 ─────────────────────────────────────────────
if __name__ == "__main__":
    import shutil

    if not shutil.which("node"):
        print("Node.js 未安装，跳过演示")
        sys.exit(0)

    executor = JavaScriptExecutor(debug_mode=False)

    class _DummyBlock:
        active_line = None
        output = ""
        language = "javascript"
        def refresh(self): pass
        def end(self): pass

    executor.active_block = _DummyBlock()  # type: ignore

    print("=== JS 测试 1：基本运算 ===")
    out = executor.run("console.log(1 + 2 + 3)")
    print(f"Output: {out!r}\n")

    print("=== JS 测试 2：数组操作 ===")
    out = executor.run("const arr = [1,2,3,4,5]; console.log(arr.reduce((a,b)=>a+b, 0))")
    print(f"Output: {out!r}\n")

    executor.stop()