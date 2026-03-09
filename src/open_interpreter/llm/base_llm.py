"""
llm/base_llm.py — LLM 客户端抽象基类

所有 LLM 后端（OpenAI、Anthropic、本地模型等）都继承此类。
定义统一接口，使 Interpreter 与具体 LLM 实现解耦。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generator, TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import Settings


class BaseLLMClient(ABC):
    """
    LLM 客户端抽象基类。

    子类须实现：
    - stream_chat(messages, functions) → Generator
    - validate_config()
    """

    def __init__(self, config: "Settings") -> None:
        self.config = config
        self.validate_config()

    @abstractmethod
    def stream_chat(
        self,
        messages: list[dict],
        functions: list[dict] | None = None,
    ) -> Generator[dict, None, None]:
        """
        向 LLM 发送消息，返回流式 chunk 生成器。

        每个 chunk 格式（OpenAI-compatible）：
        {
            "choices": [
                {
                    "delta": {"role"?, "content"?, "function_call"?},
                    "finish_reason": null | "stop" | "function_call"
                }
            ]
        }

        Parameters
        ----------
        messages : list[dict]
            对话历史，格式同 OpenAI messages
        functions : list[dict] | None
            Function schema 列表，None 表示不使用工具

        Yields
        ------
        dict
            OpenAI-compatible chunk
        """
        ...

    @abstractmethod
    def validate_config(self) -> None:
        """验证配置是否齐全（如 API key），不合法时抛出异常。"""
        ...

    def trim_messages(
        self,
        messages: list[dict],
        model: str,
        system_message: str = "",
    ) -> list[dict]:
        """
        裁剪消息列表以适应模型的 context window。
        默认实现：直接返回原列表（子类可 override）。
        """
        return messages