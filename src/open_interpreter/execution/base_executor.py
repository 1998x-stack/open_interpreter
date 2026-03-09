"""
execution/base_executor.py — 执行器抽象基类

所有语言执行器（Python / Shell / JavaScript 等）都继承此类。
定义了统一的接口和公共逻辑（行号注入、输出流监听、资源清理）。
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
import traceback
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from loguru import logger

from ..utils.output_utils import truncate_output

if TYPE_CHECKING:
    from ..display.base_block import BaseBlock


class BaseExecutor(ABC):
    """
    所有代码执行器的抽象基类。

    子类必须实现：
    - START_CMD  : 启动子进程的命令字符串（类属性）
    - PRINT_CMD  : 用于注入行号的打印命令模板（类属性），含 `{}` 占位符
    - add_active_line_prints(code): 向代码注入行号打印语句（可选 override）

    生命周期：
        __init__ → run(code) → [多次] → stop()
    """

    # ── 子类须定义的类属性 ───────────────────────────────────────
    START_CMD: str = ""
    PRINT_CMD: str = ""

    def __init__(self, debug_mode: bool = False, max_output_chars: int = 2000) -> None:
        self.debug_mode = debug_mode
        self.max_output_chars = max_output_chars

        self.proc: subprocess.Popen | None = None
        self.active_line: int | None = None
        self.output: str = ""
        self.active_block: "BaseBlock | None" = None

        # threading.Event：执行完成信号
        self.done: threading.Event = threading.Event()

        logger.info(f"[{self.__class__.__name__}] 初始化完成")

    # ── 公开接口 ─────────────────────────────────────────────────

    def run(self, code: str) -> str:
        """
        执行代码，返回完整输出字符串。

        Parameters
        ----------
        code : str
            待执行代码

        Returns
        -------
        str
            执行输出（stdout + stderr 合并）
        """
        logger.info(f"[{self.__class__.__name__}] 开始执行 ({len(code.splitlines())} 行代码)")

        # 确保子进程已启动
        try:
            if self.proc is None or self.proc.poll() is not None:
                self.start_process()
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logger.error(f"[{self.__class__.__name__}] start_process 失败: {error_message}")
            self.output = f"启动执行环境失败:\n{traceback.format_exc()}"
            self._update_active_block()
            time.sleep(0.1)
            return self.output

        # 重置状态
        self.output = ""
        self.done.clear()

        # 预处理代码（注入行号 + 语言特定处理）
        prepared = self._prepare_code(code)
        if prepared is None:
            # _prepare_code 内部已记录错误并设置 self.output
            return self.output

        if self.debug_mode:
            logger.debug(f"[{self.__class__.__name__}] 准备执行的代码:\n{prepared}")

        # 写入子进程 stdin
        try:
            self.proc.stdin.write(prepared)  # type: ignore[union-attr]
            self.proc.stdin.flush()          # type: ignore[union-attr]
        except BrokenPipeError:
            logger.warning(f"[{self.__class__.__name__}] BrokenPipe，尝试重启进程")
            self.start_process()
            return self.run(code)

        # 等待 END_OF_EXECUTION 信号
        self.done.wait()
        time.sleep(0.1)  # 等待显示层追上

        logger.info(
            f"[{self.__class__.__name__}] 执行完成，输出长度={len(self.output)} chars"
        )
        return self.output

    def stop(self) -> None:
        """终止子进程，释放资源。"""
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=3)
                logger.info(f"[{self.__class__.__name__}] 子进程已终止")
            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
                logger.warning(f"[{self.__class__.__name__}] 终止进程时出错: {error_message}")
                self.proc.kill()
        self.proc = None

    # ── 子进程管理 ────────────────────────────────────────────────

    def start_process(self) -> None:
        """启动语言解释器子进程，并开启 stdout/stderr 监听线程。"""
        if not self.START_CMD:
            raise NotImplementedError(f"{self.__class__.__name__} 未定义 START_CMD")

        logger.debug(f"[{self.__class__.__name__}] 启动子进程: {self.START_CMD!r}")

        self.proc = subprocess.Popen(
            self.START_CMD.split(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,          # 行缓冲
        )

        for stream in (self.proc.stdout, self.proc.stderr):
            threading.Thread(
                target=self.save_and_display_stream,
                args=(stream,),
                daemon=True,
            ).start()

        logger.debug(f"[{self.__class__.__name__}] 子进程 PID={self.proc.pid}")

    # ── 输出流监听 ────────────────────────────────────────────────

    def save_and_display_stream(self, stream) -> None:
        """
        后台线程：实时读取子进程输出流，解析控制信号，累积到 self.output。
        """
        for line in iter(stream.readline, ""):
            try:
                if self.debug_mode:
                    logger.debug(f"[{self.__class__.__name__}] stream line: {line!r}")

                line = line.strip()

                if line.startswith("ACTIVE_LINE:"):
                    self.active_line = int(line.split(":")[1])
                elif line == "END_OF_EXECUTION":
                    self.done.set()
                    self.active_line = None
                elif "KeyboardInterrupt" in line:
                    raise KeyboardInterrupt
                else:
                    self.output = (self.output + "\n" + line).strip()

                self._update_active_block()

            except KeyboardInterrupt:
                raise
            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
                logger.error(f"[{self.__class__.__name__}] 流处理异常: {error_message}")

    # ── 内部辅助 ──────────────────────────────────────────────────

    def _update_active_block(self) -> None:
        """截断输出并刷新终端显示块。"""
        self.output = truncate_output(self.output, self.max_output_chars)
        if self.active_block:
            self.active_block.active_line = self.active_line
            self.active_block.output = self.output
            self.active_block.refresh()

    def _prepare_code(self, code: str) -> str | None:
        """
        预处理代码：注入行号打印语句，添加 END_OF_EXECUTION 标记。
        子类可 override 此方法以进行语言特定处理（如 Python 的 AST 处理）。

        Returns
        -------
        str | None
            处理后的代码，或 None（处理失败，self.output 已设置错误信息）
        """
        try:
            # 注入行号打印语句
            code = self.add_active_line_prints(code)

            # 去除纯空行（防止破坏交互解释器的块结构）
            code_lines = [ln for ln in code.split("\n") if ln.strip()]
            code = "\n".join(code_lines)

            # 追加执行完成标记
            code += "\n\n" + self.PRINT_CMD.format("END_OF_EXECUTION") + "\n"
            return code
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logger.error(f"[{self.__class__.__name__}] _prepare_code 失败: {error_message}")
            self.output = traceback.format_exc()
            self._update_active_block()
            return None

    @abstractmethod
    def add_active_line_prints(self, code: str) -> str:
        """
        向代码中注入行号打印语句，用于实时高亮当前执行行。
        子类必须实现此方法。
        """
        ...