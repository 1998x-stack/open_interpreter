"""
display/base_block.py — 终端显示块抽象基类

CodeBlock 和 MessageBlock 的共同接口。
"""

from __future__ import annotations
from abc import ABC, abstractmethod


class BaseBlock(ABC):
    """终端显示块基类（Rich Live 包装）。"""

    active_line: int | None = None
    output: str = ""

    @abstractmethod
    def update_from_message(self, message: dict) -> None:
        """根据最新消息更新显示内容。"""
        ...

    @abstractmethod
    def refresh(self, cursor: bool = True) -> None:
        """刷新终端显示。"""
        ...

    @abstractmethod
    def end(self) -> None:
        """关闭 Rich Live，释放终端控制权。"""
        ...