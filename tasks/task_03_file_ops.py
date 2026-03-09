"""
tasks/task_03_file_ops.py — 示例任务 3：文件批量操作与目录管理

任务描述：
  让 Open Interpreter 完成一系列文件系统操作：
  1. 创建测试目录结构
  2. 生成多种格式的测试文件（.txt / .py / .json）
  3. 批量统计文件信息
  4. 按文件类型归类（移动到子目录）
  5. 生成目录清单报告

此任务演示：
  - os / pathlib 文件操作
  - Shell 命令执行（ls / find）
  - 文件读写
  - 综合 Python + Shell 混合执行
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")

from loguru import logger
from src.open_interpreter import Interpreter


TASK = """
请用 Python 完成以下文件管理任务（所有操作在当前目录下的 test_workspace/ 中进行）：

**步骤 1：创建测试环境**
在当前目录创建 test_workspace/ 目录，在其中创建以下文件：
- notes_001.txt, notes_002.txt, notes_003.txt（内容：随机 3 句英文句子）
- script_001.py, script_002.py（内容：简单的 Python hello world）
- config_001.json, config_002.json（内容：{"name": "test", "version": "1.0"}）
- README.md（内容：# Test Workspace\\n\\nThis is a test.）

**步骤 2：统计文件信息**
遍历 test_workspace/ 中的所有文件，打印一个表格：
文件名 | 扩展名 | 大小(bytes) | 修改时间
按文件名排序。

**步骤 3：按类型归类**
在 test_workspace/ 中创建子目录：texts/, scripts/, configs/, docs/
将 .txt 文件移到 texts/，.py 文件移到 scripts/，.json 文件移到 configs/，.md 文件移到 docs/。
移动后打印每个操作的确认信息。

**步骤 4：生成汇总报告**
打印最终目录结构（用缩进树形格式），并统计每个子目录的文件数量和总大小。
"""


def main() -> None:
    logger.info("=== 任务 3：文件批量操作与目录管理 ===")

    interp = Interpreter()
    interp.auto_run = True

    messages = interp.chat(TASK, return_messages=True)

    if messages:
        code_runs = sum(1 for m in messages if m.get("role") == "function")
        logger.info(f"任务完成：共 {len(messages)} 条消息，执行了 {code_runs} 次代码")

        # 验证文件结构是否生成
        ws = Path("test_workspace")
        if ws.exists():
            all_files = list(ws.rglob("*"))
            logger.info(
                f"test_workspace/ 中共 {len([f for f in all_files if f.is_file()])} 个文件"
            )
        else:
            logger.warning("test_workspace/ 未被创建")

    logger.info("=== 任务 3 结束 ===")


if __name__ == "__main__":
    main()