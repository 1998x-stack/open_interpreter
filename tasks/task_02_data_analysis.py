"""
tasks/task_02_data_analysis.py — 示例任务 2：数据分析与可视化

任务描述：
  让 Open Interpreter 完成一个完整的数据分析流程：
  1. 生成模拟销售数据（CSV）
  2. 数据探索与清洗
  3. 统计分析（描述统计、分组聚合）
  4. 可视化（折线图 + 柱状图）
  5. 数据洞察报告

此任务演示：
  - 文件生成 + 读取
  - pandas 数据分析
  - matplotlib 可视化
  - 多轮迭代分析
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
请完成以下数据分析任务：

**步骤 1：生成数据**
用 Python 生成一份 2023 年的模拟月度销售数据 CSV，
包含列：month（1-12）, region（华北/华东/华南/西部）, product（A/B/C）, sales（随机整数 10000-100000）, quantity（随机整数 100-1000）。
共生成 144 行（12 月 × 4 地区 × 3 产品），保存为 sales_2023.csv。

**步骤 2：数据探索**
读取 CSV，打印：
- 数据形状、列名、数据类型
- 每列的缺失值数量
- sales 列的描述统计（均值、中位数、标准差、最大最小值）

**步骤 3：分组分析**
- 按地区汇总全年总销售额，排序打印
- 按产品汇总全年总销售额，排序打印
- 找出销售额最高的月份和最低的月份

**步骤 4：生成报告**
打印一份 5 点的数据洞察报告，基于上面的分析结果。
"""


def main() -> None:
    logger.info("=== 任务 2：数据分析与可视化 ===")

    interp = Interpreter()
    interp.auto_run = True

    messages = interp.chat(TASK, return_messages=True)

    if messages:
        code_runs = sum(1 for m in messages if m.get("role") == "function")
        logger.info(f"任务完成：共 {len(messages)} 条消息，执行了 {code_runs} 次代码")

        # 检查是否生成了 CSV 文件
        csv_path = Path("sales_2023.csv")
        if csv_path.exists():
            logger.info(f"生成的 CSV 文件大小: {csv_path.stat().st_size} bytes")

    logger.info("=== 任务 2 结束 ===")


if __name__ == "__main__":
    main()