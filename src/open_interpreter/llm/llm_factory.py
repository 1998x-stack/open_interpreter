"""
llm/llm_factory.py — LLM 客户端工厂

与 ExecutorFactory 对称：注册表 + 工厂，解耦 LLM 后端实现。
内置注册：openai（支持 OpenAI 及兼容 API）
"""

from __future__ import annotations

import sys
import traceback
from typing import TYPE_CHECKING

from loguru import logger

from .openai_client import OpenAIClient

if TYPE_CHECKING:
    from ..config import Settings
    from .base_llm import BaseLLMClient


class LLMFactory:
    """
    LLM 客户端工厂。

    Examples
    --------
    >>> client = LLMFactory.create("openai", config=get_config())
    >>> for chunk in client.stream_chat(messages):
    ...     process(chunk)
    """

    _registry: dict[str, type["BaseLLMClient"]] = {}

    @classmethod
    def register(cls, provider: str, client_cls: type["BaseLLMClient"]) -> None:
        """注册 LLM 客户端类。"""
        cls._registry[provider.lower()] = client_cls
        logger.debug(f"[LLMFactory] 注册 provider: {provider} → {client_cls.__name__}")

    @classmethod
    def create(cls, provider: str, config: "Settings") -> "BaseLLMClient":
        """
        创建 LLM 客户端实例。

        Parameters
        ----------
        provider : str
            LLM 后端标识（如 "openai"）
        config : Settings
            全局配置对象

        Returns
        -------
        BaseLLMClient

        Raises
        ------
        ValueError
            provider 未注册时
        """
        key = provider.lower()

        if key not in cls._registry:
            available = list(cls._registry.keys())
            raise ValueError(
                f"未知 LLM provider: {key!r}。\n"
                f"已注册: {available}\n"
                "可通过 LLMFactory.register('mybackend', MyClient) 扩展。"
            )

        try:
            client_cls = cls._registry[key]
            instance = client_cls(config=config)
            logger.info(f"[LLMFactory] 创建 {key} 客户端: {client_cls.__name__}")
            return instance
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logger.error(f"[LLMFactory] 创建 {key} 客户端失败: {error_message}")
            raise

    @classmethod
    def list_providers(cls) -> list[str]:
        return list(cls._registry.keys())


# ── 内置注册 ────────────────────────────────────────────────────
LLMFactory.register("openai", OpenAIClient)


# ── standalone 演示 ─────────────────────────────────────────────
if __name__ == "__main__":
    print(f"已注册 LLM providers: {LLMFactory.list_providers()}")

    try:
        LLMFactory.create("anthropic", config=None)  # type: ignore
    except ValueError as e:
        print(f"Expected error: {e}")