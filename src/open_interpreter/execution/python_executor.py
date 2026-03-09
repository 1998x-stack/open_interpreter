"""
execution/python_executor.py — Python 代码执行器

使用 `python -i -q -u`（交互、安静、无缓冲）模式运行 Python 代码。
特性：
- AST 解析 + astor 还原，统一代码格式
- 修复缩进（python -i 的缩进块需要空行分隔）
- 跳过行号注入的特殊情况（try/except / 三引号字符串）
"""

from __future__ import annotations

import ast
import sys
import traceback

from loguru import logger

try:
    import astor
    HAS_ASTOR = True
except ImportError:
    HAS_ASTOR = False
    logger.warning("[python_executor] astor 未安装，跳过 AST 规范化（pip install astor）")

from .base_executor import BaseExecutor
from ..utils.output_utils import fix_code_indentation


class PythonExecutor(BaseExecutor):
    """
    Python 代码执行器。

    通过 subprocess 运行 `python -i -q -u`，保持交互会话状态，
    允许跨多次 run() 调用共享变量（类似 Jupyter Kernel）。
    """

    START_CMD = f"{sys.executable} -i -q -u"
    PRINT_CMD = 'print("{}")'

    # ── 行号注入 ──────────────────────────────────────────────────

    def add_active_line_prints(self, code: str) -> str:
        """
        在每行代码前注入 `print("ACTIVE_LINE:<n>")` 语句。

        跳过注入的情况（注入会破坏 python -i 的交互语法）：
        - 含 try / except 块
        - 含三引号多行字符串
        - 含 `[\\n` 或 `{\\n`（多行 list/dict literal）
        - 含 for / while / if / with / def / class（多行缩进块）
        """
        skip_triggers = (
            "try", "except", "'''", '"""', "[\n", "{\n",
            # 多行缩进块：注入会破坏 python -i 的块结构识别
            "\n    ", "\n\t",
        )
        if any(trigger in code for trigger in skip_triggers):
            logger.debug("[python_executor] 跳过行号注入（含特殊语法或多行缩进块）")
            return code

        code_lines = code.strip().split("\n")
        modified: list[str] = []

        for i, line in enumerate(code_lines):
            # 找到当前行的前导空白（用下一个非空行的缩进）
            leading_whitespace = ""
            for next_line in code_lines[i:]:
                if next_line.strip():
                    leading_whitespace = next_line[: len(next_line) - len(next_line.lstrip())]
                    break

            print_line = leading_whitespace + self.PRINT_CMD.format(f"ACTIVE_LINE:{i + 1}")
            modified.append(print_line)
            modified.append(line)

        return "\n".join(modified)

    def _prepare_code(self, code: str) -> str | None:
        """
        Python 特有预处理顺序：
        1. AST 解析 + astor 还原（格式规范化）
        2. 行号注入（add_active_line_prints）
        3. 剥除空白行（防止块内空行终止 python -i 的缩进块）
        4. fix_code_indentation（在块结束后添加终止空行，python -i 需要它）
        5. 追加 END_OF_EXECUTION 标记
        """
        try:
            # 1. AST 规范化
            if HAS_ASTOR:
                try:
                    parsed_ast = ast.parse(code)
                    code = astor.to_source(parsed_ast)
                    logger.debug("[python_executor] AST 规范化成功")
                except SyntaxError:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
                    logger.warning(f"[python_executor] AST 解析失败: {error_message}")
                    self.output = traceback.format_exc()
                    self._update_active_block()
                    import time; time.sleep(0.1)
                    return None

            # 2. 行号注入（在 AST 规范化之后，此时代码无多余空行）
            code = self.add_active_line_prints(code)

            # 3. 剥除空白行（防止块内空行在 python -i 中提前结束块）
            code_lines = [ln for ln in code.split("\n") if ln.strip()]
            code = "\n".join(code_lines)

            # 4. 修复缩进：在缩进块结束后添加空行（python -i 需要此空行识别块结束）
            code = fix_code_indentation(code)

            # 5. 追加执行完成标记
            code += "\n\n" + self.PRINT_CMD.format("END_OF_EXECUTION") + "\n"

            return code

        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logger.error(f"[python_executor] _prepare_code 失败: {error_message}")
            self.output = traceback.format_exc()
            self._update_active_block()
            return None


# ── standalone 演示 ─────────────────────────────────────────────
if __name__ == "__main__":
    from ..display.code_block import CodeBlock

    executor = PythonExecutor(debug_mode=False)

    # 创建一个简单的显示块（standalone 模式下使用哑块）
    class _DummyBlock:
        active_line = None
        output = ""
        code = ""
        language = "python"
        def refresh(self): pass
        def end(self): pass

    executor.active_block = _DummyBlock()  # type: ignore

    print("=== 测试 1：基本计算 ===")
    out = executor.run("x = sum(range(101))\nprint(f'Sum 1-100 = {x}')")
    print(f"Output: {out!r}\n")

    print("=== 测试 2：跨调用状态保持 ===")
    executor.run("data = [1, 2, 3, 4, 5]")
    out = executor.run("print(f'data = {data}, sum = {sum(data)}')")
    print(f"Output: {out!r}\n")

    print("=== 测试 3：错误处理 ===")
    out = executor.run("1 / 0")
    print(f"Output (error): {out!r}\n")

    executor.stop()
    print("Done.")