"""
display/message_block.py — LLM 文本消息显示组件

使用 Rich Live 实时渲染 Markdown 格式的 LLM 消息。
区分 LLM 消息中的 markdown 代码块（渲染为 text 样式，避免与 CodeBlock 混淆）。
"""

from __future__ import annotations

import re
import sys
import traceback

from loguru import logger
from rich.box import MINIMAL
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

from .base_block import BaseBlock


class MessageBlock(BaseBlock):
    """LLM 文本消息显示组件（Markdown 渲染）。"""

    def __init__(self) -> None:
        self.content: str = ""
        self.live = Live(auto_refresh=False, console=Console())
        self.live.start()
        logger.debug("[MessageBlock] 初始化完成")

    def update_from_message(self, message: dict) -> None:
        """从 LLM 消息对象更新内容并刷新。"""
        try:
            self.content = message.get("content", "")
            if self.content:
                self.refresh()
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logger.error(f"[MessageBlock] update_from_message 失败: {error_message}")

    def end(self) -> None:
        self.refresh(cursor=False)
        self.live.stop()
        logger.debug("[MessageBlock] 关闭")

    def refresh(self, cursor: bool = True) -> None:
        try:
            content = _textify_markdown_code_blocks(self.content)
            if cursor:
                content += "█"

            markdown = Markdown(content)
            panel = Panel(markdown, box=MINIMAL)
            self.live.update(panel)
            self.live.refresh()
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logger.error(f"[MessageBlock] refresh 失败: {error_message}")


def _textify_markdown_code_blocks(text: str) -> str:
    """
    将 markdown 中的代码块语言标记替换为 "text"，使其呈现为黑白样式，
    与彩色的 CodeBlock 区分开来。

    Examples
    --------
    >>> _textify_markdown_code_blocks("```python\\nprint(1)\\n```")
    '```text\\nprint(1)\\n```'
    """
    replacement = "```text"
    lines = text.split("\n")
    inside_code_block = False

    for i, line in enumerate(lines):
        if re.match(r"^```(\w*)$", line.strip()):
            inside_code_block = not inside_code_block
            if inside_code_block:
                lines[i] = replacement

    return "\n".join(lines)


# ── standalone 演示 ─────────────────────────────────────────────
if __name__ == "__main__":
    import time

    block = MessageBlock()

    sample = (
        "# 分析结果\n\n"
        "数据加载成功，共 **1,234 行**。\n\n"
        "以下是示例代码：\n\n"
        "```python\n"
        "import pandas as pd\n"
        "df = pd.read_csv('data.csv')\n"
        "```\n\n"
        "分析完成 ✅"
    )

    for i in range(len(sample)):
        block.content = sample[:i+1]
        block.refresh()
        time.sleep(0.005)

    time.sleep(1)
    block.end()