"""
display/code_block.py — 代码块终端显示组件

使用 Rich Live 实时渲染：
- 上半部分：语法高亮的代码，当前执行行白色背景高亮
- 下半部分：执行输出
"""

from __future__ import annotations

import sys
import traceback

from loguru import logger
from rich.box import MINIMAL
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from .base_block import BaseBlock


class CodeBlock(BaseBlock):
    """
    代码块显示组件。

    Attributes
    ----------
    language : str   编程语言（用于语法高亮）
    code     : str   当前代码内容
    output   : str   执行输出
    active_line : int | None  当前执行行号（高亮用）
    """

    def __init__(self) -> None:
        self.language: str = ""
        self.code: str = ""
        self.output: str = ""
        self.active_line: int | None = None

        self.live = Live(
            auto_refresh=False,
            console=Console(),
            vertical_overflow="visible",
        )
        self.live.start()
        logger.debug("[CodeBlock] 初始化完成")

    def update_from_message(self, message: dict) -> None:
        """从 LLM 消息对象更新代码内容并刷新显示。"""
        try:
            fc = message.get("function_call", {})
            parsed = fc.get("parsed_arguments") if isinstance(fc, dict) else None

            if parsed:
                self.language = parsed.get("language", self.language)
                self.code = parsed.get("code", self.code)
                if self.code and self.language:
                    self.refresh()
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logger.error(f"[CodeBlock] update_from_message 失败: {error_message}")

    def end(self) -> None:
        """结束代码块显示（移除光标，关闭 Live）。"""
        self.refresh(cursor=False)
        self.live.stop()
        logger.debug("[CodeBlock] 关闭")

    def refresh(self, cursor: bool = True) -> None:
        """重新渲染代码块和输出面板。"""
        try:
            # ── 代码表格 ──────────────────────────────────────────
            code_table = Table(
                show_header=False,
                show_footer=False,
                box=None,
                padding=0,
                expand=True,
            )
            code_table.add_column()

            code = self.code
            if cursor:
                code += "█"

            for i, line in enumerate(code.strip().split("\n"), start=1):
                syntax = Syntax(
                    line,
                    self.language or "text",
                    theme="monokai",
                    line_numbers=False,
                    word_wrap=True,
                )
                if i == self.active_line:
                    code_table.add_row(
                        Syntax(line, self.language or "text", theme="bw",
                               line_numbers=False, word_wrap=True),
                        style="black on white",
                    )
                else:
                    code_table.add_row(syntax)

            code_panel = Panel(code_table, box=MINIMAL, style="on #272722")

            # ── 输出面板 ──────────────────────────────────────────
            if self.output and self.output not in ("", "None"):
                output_panel = Panel(self.output, box=MINIMAL, style="#FFFFFF on #3b3b37")
            else:
                output_panel = ""  # type: ignore

            self.live.update(Group(code_panel, output_panel))
            self.live.refresh()

        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logger.error(f"[CodeBlock] refresh 失败: {error_message}")


# ── standalone 演示 ─────────────────────────────────────────────
if __name__ == "__main__":
    import time

    block = CodeBlock()
    block.language = "python"

    # 模拟流式代码到来
    sample_code = "import math\nx = math.sqrt(2)\nprint(f'sqrt(2) = {x:.4f}')"
    for i in range(len(sample_code)):
        block.code = sample_code[:i+1]
        block.refresh()
        time.sleep(0.01)

    block.active_line = 2
    block.output = "sqrt(2) = 1.4142"
    block.refresh()
    time.sleep(1)
    block.end()