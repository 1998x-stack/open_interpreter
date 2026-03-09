"""
execution/executor_factory.py — 执行器工厂

注册表 + 工厂模式：
- ExecutorFactory.register(language, cls) 注册新语言
- ExecutorFactory.create(language, **kwargs) 创建（或复用）执行器实例
- ExecutorFactory.list_languages() 查看已注册的语言

内置支持：python / shell / javascript
可通过 register() 扩展任意语言。
"""

from __future__ import annotations

import sys
import traceback
from typing import TYPE_CHECKING

from loguru import logger

from .python_executor import PythonExecutor
from .shell_executor import ShellExecutor
from .javascript_executor import JavaScriptExecutor

if TYPE_CHECKING:
    from .base_executor import BaseExecutor


class ExecutorFactory:
    """
    执行器工厂，持有一个语言→类的注册表，以及一个会话级实例缓存。

    实例缓存保证同一个 Interpreter 会话中，同一语言只启动一个子进程，
    从而实现跨 run() 调用的变量持久化（类似 Jupyter Kernel）。
    """

    # 类级注册表：language -> executor class
    _registry: dict[str, type["BaseExecutor"]] = {}

    # 实例缓存：language -> executor instance（per-session）
    _instances: dict[str, "BaseExecutor"] = {}

    # ── 注册 ──────────────────────────────────────────────────────

    @classmethod
    def register(cls, language: str, executor_cls: type["BaseExecutor"]) -> None:
        """
        注册一个执行器类到指定语言。

        Parameters
        ----------
        language : str
            语言标识（小写，如 "python"、"ruby"）
        executor_cls : type[BaseExecutor]
            执行器类（BaseExecutor 的子类）

        Examples
        --------
        >>> ExecutorFactory.register("ruby", RubyExecutor)
        """
        lang = language.lower()
        cls._registry[lang] = executor_cls
        logger.debug(f"[ExecutorFactory] 注册语言: {lang} → {executor_cls.__name__}")

    # ── 创建 / 获取 ───────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        language: str,
        debug_mode: bool = False,
        max_output_chars: int = 2000,
        reuse: bool = True,
    ) -> "BaseExecutor":
        """
        创建或复用执行器实例。

        Parameters
        ----------
        language : str
            语言标识
        debug_mode : bool
            是否开启调试模式
        max_output_chars : int
            最大输出字符数
        reuse : bool
            是否复用已有实例（默认 True，保持会话状态）

        Returns
        -------
        BaseExecutor
            执行器实例

        Raises
        ------
        ValueError
            语言未注册时抛出
        """
        lang = language.lower()

        if lang not in cls._registry:
            available = list(cls._registry.keys())
            raise ValueError(
                f"未知语言: {lang!r}。\n"
                f"已注册的语言: {available}\n"
                f"可通过 ExecutorFactory.register('{lang}', YourExecutor) 扩展。"
            )

        try:
            if reuse and lang in cls._instances:
                instance = cls._instances[lang]
                # 若子进程已死，清理并重建
                if instance.proc is not None and instance.proc.poll() is not None:
                    logger.warning(f"[ExecutorFactory] {lang} 子进程已退出，重建实例")
                    instance.stop()
                    del cls._instances[lang]
                else:
                    logger.debug(f"[ExecutorFactory] 复用已有 {lang} 执行器")
                    return instance

            executor_cls = cls._registry[lang]
            instance = executor_cls(
                debug_mode=debug_mode,
                max_output_chars=max_output_chars,
            )
            if reuse:
                cls._instances[lang] = instance

            logger.info(f"[ExecutorFactory] 创建 {lang} 执行器: {executor_cls.__name__}")
            return instance

        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logger.error(f"[ExecutorFactory] 创建 {lang} 执行器失败: {error_message}")
            raise

    # ── 批量清理 ──────────────────────────────────────────────────

    @classmethod
    def stop_all(cls) -> None:
        """终止所有活跃的执行器子进程，清理实例缓存。"""
        for lang, instance in list(cls._instances.items()):
            logger.info(f"[ExecutorFactory] 停止 {lang} 执行器")
            instance.stop()
        cls._instances.clear()

    @classmethod
    def reset(cls) -> None:
        """停止所有实例并清空注册表（主要用于测试）。"""
        cls.stop_all()
        cls._registry.clear()
        logger.debug("[ExecutorFactory] 注册表已重置")

    # ── 查询 ──────────────────────────────────────────────────────

    @classmethod
    def list_languages(cls) -> list[str]:
        """返回已注册的语言列表。"""
        return list(cls._registry.keys())

    @classmethod
    def is_registered(cls, language: str) -> bool:
        return language.lower() in cls._registry


# ── 内置语言注册 ────────────────────────────────────────────────
ExecutorFactory.register("python", PythonExecutor)
ExecutorFactory.register("shell", ShellExecutor)
ExecutorFactory.register("javascript", JavaScriptExecutor)


# ── standalone 演示 ─────────────────────────────────────────────
if __name__ == "__main__":
    print(f"已注册语言: {ExecutorFactory.list_languages()}")

    # 创建 Python 执行器
    class _DummyBlock:
        active_line = None
        output = ""
        language = "python"
        def refresh(self): pass
        def end(self): pass

    py = ExecutorFactory.create("python", debug_mode=False)
    py.active_block = _DummyBlock()  # type: ignore

    # 测试复用（应该返回同一实例）
    py2 = ExecutorFactory.create("python", reuse=True)
    print(f"Same instance: {py is py2}")  # True

    result = py.run("import math; print(math.pi)")
    print(f"π = {result.strip()}")

    # 测试未知语言
    try:
        ExecutorFactory.create("ruby")
    except ValueError as e:
        print(f"Expected error: {e}")

    ExecutorFactory.stop_all()
    print("Done.")