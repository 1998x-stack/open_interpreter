"""
config.py — 全局配置中心

从环境变量 / .env 文件读取所有配置，对外暴露单例 `get_config()`。
支持的环境变量见 .env.example。
"""

from __future__ import annotations

import os
import sys
import traceback
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# ── 加载 .env（项目根目录）──────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[2]  # src/open_interpreter/config.py → root
load_dotenv(_PROJECT_ROOT / ".env", override=False)


# ── 日志格式（全项目统一）──────────────────────────────────────
def _setup_logger(debug: bool = False) -> None:
    logger.remove()
    level = "DEBUG" if debug else "INFO"
    logger.add(
        sys.stdout,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level:<8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
    )


# ── 配置数据类 ──────────────────────────────────────────────────
@dataclass
class Settings:
    # LLM
    openai_api_key: str = field(default="")
    openai_model: str = field(default="gpt-4o")
    openai_base_url: str = field(default="https://api.openai.com/v1")
    llm_provider: str = field(default="openai")
    temperature: float = field(default=0.01)

    # 行为
    auto_run: bool = field(default=False)
    debug_mode: bool = field(default=False)
    max_output_chars: int = field(default=2000)

    def validate(self) -> None:
        """
        启动时校验必填配置。缺失时抛出 ValueError，给出明确提示。
        """
        if not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY 未设置。\n"
                "请在 .env 文件或环境变量中设置:\n"
                "  export OPENAI_API_KEY=sk-xxx\n"
                "或在项目根目录创建 .env 文件（参考 .env.example）。"
            )

    def __post_init__(self) -> None:
        _setup_logger(self.debug_mode)
        logger.debug(
            f"Settings loaded: model={self.openai_model}, "
            f"base_url={self.openai_base_url}, "
            f"auto_run={self.auto_run}, debug={self.debug_mode}"
        )


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_config() -> Settings:
    """
    返回全局配置单例。首次调用时从环境变量构建，之后缓存复用。
    """
    try:
        settings = Settings(
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
            openai_base_url=os.environ.get(
                "OPENAI_BASE_URL", "https://api.openai.com/v1"
            ),
            llm_provider=os.environ.get("LLM_PROVIDER", "openai"),
            temperature=float(os.environ.get("TEMPERATURE", "0.01")),
            auto_run=_parse_bool(os.environ.get("AUTO_RUN", "false")),
            debug_mode=_parse_bool(os.environ.get("DEBUG_MODE", "false")),
            max_output_chars=int(os.environ.get("MAX_OUTPUT_CHARS", "2000")),
        )
        return settings
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.error(f"[config] 配置加载失败: {error_message}")
        raise


def reset_config() -> None:
    """清除 lru_cache，用于测试中重置配置。"""
    get_config.cache_clear()


# ── standalone 演示 ─────────────────────────────────────────────
if __name__ == "__main__":
    cfg = get_config()
    print(f"Model       : {cfg.openai_model}")
    print(f"Base URL    : {cfg.openai_base_url}")
    print(f"Auto Run    : {cfg.auto_run}")
    print(f"Debug Mode  : {cfg.debug_mode}")
    print(f"Max Output  : {cfg.max_output_chars} chars")
    print(f"API Key set : {'yes' if cfg.openai_api_key else 'NO — please set OPENAI_API_KEY'}")