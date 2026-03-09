"""
llm/openai_client.py — OpenAI / 兼容 API 客户端

支持：
- 官方 OpenAI API（gpt-4o、gpt-4-turbo、gpt-3.5-turbo 等）
- 任何 OpenAI-compatible API（通过 OPENAI_BASE_URL 配置，如 Azure、本地 vLLM）
- Function Calling / Tool Use（run_code 工具）
- 流式响应（stream=True）
"""

from __future__ import annotations

import sys
import traceback
from typing import Generator, TYPE_CHECKING

from loguru import logger

try:
    from openai import OpenAI
    from openai import AuthenticationError, RateLimitError, APIConnectionError
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    logger.error("[openai_client] openai 包未安装，请执行: pip install openai")

if TYPE_CHECKING:
    from ..config import Settings

from .base_llm import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """
    OpenAI / 兼容 API 客户端。

    通过 OPENAI_BASE_URL 支持任意兼容 OpenAI 格式的后端（如 Azure、vLLM、Ollama 等）。
    """

    def __init__(self, config: "Settings") -> None:
        super().__init__(config)
        self._client: "OpenAI | None" = None

    def validate_config(self) -> None:
        """验证 API key 存在。"""
        if not self.config.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY 未设置。\n"
                "请在 .env 文件中设置 OPENAI_API_KEY=sk-xxx"
            )
        if not HAS_OPENAI:
            raise ImportError("openai 包未安装，请执行: pip install openai>=1.30.0")

    @property
    def client(self) -> "OpenAI":
        """懒初始化 OpenAI 客户端（支持 base_url 覆盖）。"""
        if self._client is None:
            self._client = OpenAI(
                api_key=self.config.openai_api_key,
                base_url=self.config.openai_base_url,
            )
            logger.debug(
                f"[openai_client] 客户端初始化: model={self.config.openai_model}, "
                f"base_url={self.config.openai_base_url}"
            )
        return self._client

    def stream_chat(
        self,
        messages: list[dict],
        functions: list[dict] | None = None,
    ) -> Generator[dict, None, None]:
        """
        调用 OpenAI Chat Completions API（流式）。

        Parameters
        ----------
        messages : list[dict]
            OpenAI 格式的对话历史
        functions : list[dict] | None
            Function schema 列表

        Yields
        ------
        dict
            OpenAI streaming chunk（已转为 dict）
        """
        logger.info(
            f"[openai_client] 请求 LLM: model={self.config.openai_model}, "
            f"messages_count={len(messages)}, "
            f"functions={'yes' if functions else 'no'}"
        )

        kwargs: dict = {
            "model": self.config.openai_model,
            "messages": messages,
            "stream": True,
            "temperature": self.config.temperature,
        }

        if functions:
            kwargs["functions"] = functions
            kwargs["function_call"] = "auto"

        try:
            response = self.client.chat.completions.create(**kwargs)

            for chunk in response:
                # 将 Pydantic 对象转为 dict（兼容下游逻辑）
                yield chunk.model_dump()

        except AuthenticationError:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logger.error(f"[openai_client] API 认证失败（检查 OPENAI_API_KEY）: {error_message}")
            raise
        except RateLimitError:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logger.error(f"[openai_client] 请求频率超限: {error_message}")
            raise
        except APIConnectionError:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logger.error(f"[openai_client] 网络连接失败（检查 OPENAI_BASE_URL）: {error_message}")
            raise
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logger.error(f"[openai_client] LLM 调用异常: {error_message}")
            raise

    def trim_messages(
        self,
        messages: list[dict],
        model: str,
        system_message: str = "",
    ) -> list[dict]:
        """
        使用 tokentrim 裁剪消息以适应 context window。
        若 tokentrim 不可用，直接返回原消息列表。
        """
        try:
            import tokentrim as tt
            return tt.trim(messages, model, system_message=system_message)
        except ImportError:
            logger.warning("[openai_client] tokentrim 未安装，跳过消息裁剪")
            return messages
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logger.warning(f"[openai_client] trim_messages 失败，使用原始消息: {error_message}")
            return messages


# ── standalone 演示 ─────────────────────────────────────────────
if __name__ == "__main__":
    import os
    from ..config import get_config

    cfg = get_config()
    try:
        cfg.validate()
    except ValueError as e:
        print(f"配置错误: {e}")
        sys.exit(1)

    client = OpenAIClient(config=cfg)

    messages = [
        {"role": "user", "content": "用一句话解释什么是 Code Interpreter。"}
    ]

    print("LLM 回复（流式）：")
    content = ""
    for chunk in client.stream_chat(messages):
        delta = chunk["choices"][0]["delta"]
        if delta.get("content"):
            print(delta["content"], end="", flush=True)
            content += delta["content"]
    print()