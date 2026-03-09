"""
interpreter.py — 主编排器

Interpreter 类：协调 LLM 客户端、代码执行器、终端显示块，
实现 Thought → Action → Observation 的 ReAct 闭环。

对外接口：
    interp = Interpreter()
    interp.chat()                  # 交互式对话
    interp.chat("计算质数之和")     # 单次调用
    msgs = interp.chat("...", return_messages=True)
"""

from __future__ import annotations

import getpass
import os
import platform
import sys
import traceback
from typing import Optional

from loguru import logger
from rich import print as rprint
from rich.markdown import Markdown

from .config import Settings, get_config
from .display.code_block import CodeBlock
from .display.message_block import MessageBlock
from .execution.executor_factory import ExecutorFactory
from .llm.llm_factory import LLMFactory
from .utils.json_utils import merge_deltas, parse_partial_json


# ── Function Schema（告诉 LLM 可用的工具）────────────────────────
FUNCTION_SCHEMA = {
    "name": "run_code",
    "description": (
        "Executes code in various programming languages and returns the output. "
        "Use this for any computation, data processing, file operations, or tasks "
        "requiring precise calculation."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "language": {
                "type": "string",
                "description": "The programming language.",
                "enum": ["python", "shell", "javascript"],
            },
            "code": {
                "type": "string",
                "description": "The code to execute.",
            },
        },
        "required": ["language", "code"],
    },
}

_MISSING_API_KEY_MSG = """
**OpenAI API key not found.**

Set the environment variable:
```
export OPENAI_API_KEY=sk-xxx
```
Or create a `.env` file (see `.env.example`).

---
"""

_CONFIRM_MODE_MSG = """
**Open Interpreter** will ask for approval before running code.

Use `interpreter -y` to bypass this, or set `AUTO_RUN=true` in `.env`.

Press `CTRL-C` to exit.
---
"""


class Interpreter:
    """
    Open Interpreter 主编排器。

    Attributes
    ----------
    messages : list[dict]
        完整对话历史（包含 user / assistant / function 消息）
    auto_run : bool
        True → 跳过执行确认
    debug_mode : bool
        True → 打印详细调试信息
    model : str
        LLM 模型名称（覆盖 config 中的默认值）
    """

    def __init__(self, config: Optional[Settings] = None) -> None:
        self._config = config or get_config()

        self.messages: list[dict] = []
        self.auto_run: bool = self._config.auto_run
        self.debug_mode: bool = self._config.debug_mode
        self.model: str = self._config.openai_model

        # 加载 system message
        here = os.path.abspath(os.path.dirname(__file__))
        system_msg_path = os.path.join(here, "system_message.txt")
        if os.path.exists(system_msg_path):
            with open(system_msg_path, "r", encoding="utf-8") as f:
                self.system_message: str = f.read().strip()
        else:
            self.system_message = (
                "You are Open Interpreter, a world-class programmer. "
                "Complete any goal by executing code. "
                "Always write and run code to perform computations or file operations."
            )

        # LLM 客户端（懒初始化）
        self._llm_client = None

        # 当前显示块（CodeBlock 或 MessageBlock）
        self.active_block: Optional[CodeBlock | MessageBlock] = None

        logger.info(
            f"[Interpreter] 初始化完成: model={self.model}, "
            f"auto_run={self.auto_run}, debug={self.debug_mode}"
        )

    # ── 公开接口 ─────────────────────────────────────────────────

    @property
    def llm_client(self):
        if self._llm_client is None:
            self._llm_client = LLMFactory.create(
                self._config.llm_provider, config=self._config
            )
        return self._llm_client

    def chat(
        self,
        message: Optional[str] = None,
        return_messages: bool = False,
    ) -> Optional[list[dict]]:
        """
        启动对话。

        Parameters
        ----------
        message : str | None
            - 提供字符串：单次非交互对话
            - None：交互式 REPL 循环
        return_messages : bool
            是否返回完整消息历史

        Returns
        -------
        list[dict] | None
            当 return_messages=True 时返回消息历史
        """
        # 验证 API key
        try:
            self._config.validate()
        except ValueError:
            rprint("", Markdown(_MISSING_API_KEY_MSG), "")
            api_key = input("请输入 OpenAI API Key（本次会话）:\n").strip()
            if not api_key:
                raise
            self._config.openai_api_key = api_key
            # 重建 LLM 客户端
            self._llm_client = None

        if not self.auto_run:
            rprint("", Markdown(_CONFIRM_MODE_MSG), "")

        if message is not None:
            # 单次调用模式
            self.messages.append({"role": "user", "content": message})
            self._respond()
        else:
            # 交互式 REPL
            import readline
            while True:
                try:
                    user_input = input("> ").strip()
                except EOFError:
                    break
                except KeyboardInterrupt:
                    print()
                    logger.info("[Interpreter] KeyboardInterrupt，退出")
                    break

                if not user_input:
                    continue

                readline.add_history(user_input)
                self.messages.append({"role": "user", "content": user_input})

                try:
                    self._respond()
                except KeyboardInterrupt:
                    pass
                finally:
                    self._end_active_block()

        if return_messages:
            return self.messages
        return None

    def reset(self) -> None:
        """清空消息历史，重置执行器。"""
        self.messages = []
        ExecutorFactory.stop_all()
        logger.info("[Interpreter] 已重置")

    def load(self, messages: list[dict]) -> None:
        """加载外部消息历史（用于恢复会话）。"""
        self.messages = messages

    # ── 核心：LLM 调用 + 流式处理 ────────────────────────────────

    def _respond(self) -> None:
        """
        调用 LLM，处理流式响应，执行代码（如需），递归迭代。
        这是 ReAct 循环的核心。
        """
        # 构建系统消息（含用户环境信息）
        system_message = self.system_message + "\n\n" + self._get_env_info()

        # 裁剪消息历史以适应 context window
        messages = self.llm_client.trim_messages(
            self.messages, self.model, system_message=system_message
        )

        full_messages = [{"role": "system", "content": system_message}] + messages

        if self.debug_mode:
            logger.debug(f"[Interpreter] 发送给 LLM 的消息数: {len(full_messages)}")

        # 调用 LLM（流式）
        try:
            response = self.llm_client.stream_chat(
                messages=full_messages,
                functions=[FUNCTION_SCHEMA],
            )
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logger.error(f"[Interpreter] LLM 调用失败: {error_message}")
            print(f"\n[错误] LLM 调用失败: {traceback.format_exc()}")
            return

        # ── 处理流式 chunks ──────────────────────────────────────
        self.messages.append({})  # 占位，随 delta 累积填充
        in_function_call = False
        self.active_block = None

        for chunk in response:
            try:
                delta = chunk["choices"][0]["delta"]
                self.messages[-1] = merge_deltas(self.messages[-1], delta)

                # 检测是否进入 function call
                in_fc_now = self.messages[-1] and "function_call" in self.messages[-1]

                if in_fc_now:
                    if not in_function_call:
                        # 刚进入 function call → 切换到 CodeBlock
                        self._end_active_block()
                        last_role = self.messages[-2]["role"] if len(self.messages) >= 2 else ""
                        if last_role in ("user", "function"):
                            print()
                        self.active_block = CodeBlock()
                    in_function_call = True

                    # 解析 function_call.arguments（流式 JSON）
                    fc = self.messages[-1].get("function_call", {})
                    if fc and "arguments" in fc:
                        parsed = parse_partial_json(fc["arguments"])
                        if parsed:
                            self.messages[-1]["function_call"]["parsed_arguments"] = parsed
                        else:
                            # 如果解析失败但有基础字段，则尝试构建基础结构
                            arguments_str = fc["arguments"]
                            if '"language"' in arguments_str or '"code"' in arguments_str:
                                # Attempt to extract language and code if they're partially present
                                import re
                                extracted = {}
                                # Look for language pattern: "language": "xyz"
                                lang_match = re.search(r'"language"\s*:\s*"([^"]*)"', arguments_str)
                                if lang_match:
                                    extracted["language"] = lang_match.group(1)

                                # Look for code pattern: "code": "some code..."
                                code_match = re.search(r'"code"\s*:\s*"((?:[^"]|\\.)*)', arguments_str, re.DOTALL)
                                if code_match:
                                    # This extracts the code value up to the point we have
                                    extracted["code"] = code_match.group(1)

                                if extracted:
                                    self.messages[-1]["function_call"]["parsed_arguments"] = extracted

                else:
                    if in_function_call:
                        # 刚离开 function call
                        pass
                    in_function_call = False

                    if self.active_block is None:
                        self.active_block = MessageBlock()

                # 更新显示
                if self.active_block:
                    self.active_block.update_from_message(self.messages[-1])

                # 检查完成
                finish_reason = chunk["choices"][0].get("finish_reason")
                if finish_reason == "function_call":
                    self._handle_function_call()
                    return
                elif finish_reason and finish_reason != "function_call":
                    # 正常结束
                    self._end_active_block()
                    return

            except KeyboardInterrupt:
                self._end_active_block()
                raise
            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
                logger.error(f"[Interpreter] chunk 处理异常: {error_message}")

    def _handle_function_call(self) -> None:
        """
        处理 LLM 的 run_code 函数调用：
        1. 提示用户确认（若非 auto_run）
        2. 获取/创建对应语言的执行器
        3. 执行代码，将结果追加到消息历史
        4. 递归调用 _respond() 继续迭代
        """
        try:
            fc = self.messages[-1].get("function_call", {})

            # First try to get pre-parsed arguments (may have been parsed during streaming)
            parsed = fc.get("parsed_arguments", {}) if fc else {}

            # If no parsed arguments are available, try to parse the raw arguments now
            if not parsed and fc and "arguments" in fc:
                parsed = parse_partial_json(fc["arguments"]) or {}

            # As a last resort, try to parse the arguments from the message directly if fc is None
            if not parsed and not fc:
                full_message = self.messages[-1]
                if "function_call" in full_message and isinstance(full_message["function_call"], dict):
                    fc_alt = full_message["function_call"]
                    if "arguments" in fc_alt:
                        parsed = parse_partial_json(fc_alt["arguments"]) or {}

            # Check if the function_call field itself is None, and handle it differently
            if fc is None:
                # This could indicate that there was a parsing issue during streaming
                # Check the entire message for code
                message_content = self.messages[-1]
                # If the code is in the content field instead of function_call
                if "content" in message_content and message_content["content"]:
                    # Look for Python code patterns in the content
                    import re
                    content = message_content["content"]
                    # Look for Python code blocks in markdown format or just raw Python
                    python_code_pattern = r"(?<!\\)`{3}(?:python)?\n(.*?)\n`{3}|^(\s*def\s+\w+\s*\(|\s*import\s+\w+|\s*for\s+.*:|\s*if\s+.*:|\s*class\s+\w+\s*:)"
                    if re.search(python_code_pattern, content, re.MULTILINE | re.DOTALL):
                        # This looks like it should have been a code execution
                        # Since we can't run it directly from content, warn and return
                        logger.warning("[Interpreter] Detected Python code in content field instead of function call")
                        logger.debug(f"[Interpreter] Content: {content}")
                        return

            language = parsed.get("language", "python")
            code = parsed.get("code", "")

            if not code:
                logger.warning("[Interpreter] function_call 无代码内容，跳过")
                # Print the actual content to debug
                logger.debug(f"[Interpreter] function_call content: {self.messages[-1]}")
                return

            # 用户确认
            if not self.auto_run:
                self._end_active_block()
                saved_language = language
                saved_code = code

                response = input("  是否执行此代码? (y/n)\n\n  ").strip().lower()
                print()

                if response != "y":
                    logger.info("[Interpreter] 用户拒绝执行")
                    self.messages.append({
                        "role": "function",
                        "name": "run_code",
                        "content": "User decided not to run this code.",
                    })
                    return

                # 重建 CodeBlock 以显示将要执行的代码
                self.active_block = CodeBlock()
                self.active_block.language = saved_language
                self.active_block.code = saved_code
                self.active_block.refresh()
                language = saved_language
                code = saved_code

            # 获取执行器
            executor = ExecutorFactory.create(
                language,
                debug_mode=self.debug_mode,
                max_output_chars=self._config.max_output_chars,
            )
            executor.active_block = self.active_block

            # 执行
            logger.info(f"[Interpreter] 执行 {language} 代码 ({len(code.splitlines())} 行)")
            output = executor.run(code)

            # 结束显示
            self._end_active_block()

            # 将执行结果追加到消息历史
            self.messages.append({
                "role": "function",
                "name": "run_code",
                "content": output or "(no output)",
            })

            logger.info(f"[Interpreter] 代码执行完成，输出长度={len(output or '')} chars")

            # 递归继续迭代
            self._respond()

        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logger.error(f"[Interpreter] _handle_function_call 失败: {error_message}")
            self._end_active_block()
            self.messages.append({
                "role": "function",
                "name": "run_code",
                "content": f"执行失败:\n{traceback.format_exc()}",
            })

    def _end_active_block(self) -> None:
        if self.active_block:
            try:
                self.active_block.end()
            except Exception:
                pass
            self.active_block = None

    def _get_env_info(self) -> str:
        """获取用户环境信息，注入到 system message。"""
        try:
            info = "[User Info]\n"
            info += f"Name: {getpass.getuser()}\n"
            info += f"CWD: {os.getcwd()}\n"
            info += f"OS: {platform.system()} {platform.release()}\n"
            info += f"Python: {sys.version.split()[0]}"
            return info
        except Exception:
            return ""


# ── standalone 演示 ─────────────────────────────────────────────
if __name__ == "__main__":
    interp = Interpreter()
    interp.auto_run = True  # 演示时跳过确认

    result = interp.chat(
        "用 Python 计算 1 到 100 的所有质数，打印质数列表和总和。",
        return_messages=True,
    )

    if result:
        print(f"\n共 {len(result)} 条消息")