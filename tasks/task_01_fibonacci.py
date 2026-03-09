"""
tasks/task_01_fibonacci.py — 示例任务 1：斐波那契数列与性能分析

任务描述：
  用 Open Interpreter 完成一个多步数学分析任务：
  1. 生成斐波那契数列前 30 项
  2. 分析黄金比例收敛性（相邻项之比趋近 φ）
  3. 对比递归 vs 迭代实现的性能
  4. 打印漂亮的分析报告

此任务演示：
  - LLM 规划多步任务
  - 多轮代码执行（跨 run() 调用状态保持）
  - 自动导入库、性能测量
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ── 路径设置（确保在项目根目录运行时也能找到包）──────────────────
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")

from loguru import logger
from src.open_interpreter import Interpreter


TASK = """
请完成以下 Python 数学分析任务：

1. **生成斐波那契数列**：计算前 30 项，打印带序号的列表。

2. **黄金比例分析**：计算相邻项之比（F(n+1)/F(n)），打印每一项的比值，
   并指出从第几项开始，比值与黄金比例 φ≈1.61803398 的误差小于 0.0001。

3. **性能对比**：分别用递归（lru_cache 加速）和迭代方式计算 F(40)，
   各运行 1000 次，比较平均耗时（用 timeit 模块）。

4. **报告**：用 print 打印一份简洁的分析总结，包含：
   - 第 30 项的值
   - 黄金比例收敛的项数
   - 两种方法的平均耗时对比（单位：微秒）
"""


def main() -> None:
    logger.info("=== 任务 1：斐波那契数列与性能分析 ===")

    interp = Interpreter()
    interp.auto_run = True   # 示例任务自动执行

    messages = interp.chat(TASK, return_messages=True)

    # 打印消息统计
    if messages:
        roles = [m.get("role") for m in messages]
        code_runs = roles.count("function")
        logger.info(
            f"任务完成：共 {len(messages)} 条消息，"
            f"执行了 {code_runs} 次代码"
        )

    logger.info("=== 任务 1 结束 ===")


if __name__ == "__main__":
    main()