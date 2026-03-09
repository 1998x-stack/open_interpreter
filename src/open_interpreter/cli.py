"""
cli.py — 命令行入口

支持的标志：
  -y / --yes       跳过执行确认
  -m / --model     指定模型（如 gpt-3.5-turbo）
  --message        单次非交互调用
  --debug          调试模式
  --auto-run       等同于 -y

用法：
  python -m src.open_interpreter [flags]
  python cli.py -y --message "计算圆周率前 10 位"
"""

from __future__ import annotations

import argparse
import sys

from loguru import logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Open Interpreter — LLM 驱动的本地代码执行 Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python -m src.open_interpreter\n"
            "  python -m src.open_interpreter -y\n"
            "  python -m src.open_interpreter --message '计算 1 到 100 的质数之和'\n"
            "  python -m src.open_interpreter --model gpt-3.5-turbo -y\n"
        ),
    )

    parser.add_argument(
        "-y", "--yes", "--auto-run",
        dest="auto_run",
        action="store_true",
        help="执行代码前不需要用户确认",
    )
    parser.add_argument(
        "-m", "--model",
        dest="model",
        type=str,
        default=None,
        help="指定 LLM 模型（覆盖 OPENAI_MODEL 环境变量）",
    )
    parser.add_argument(
        "--message",
        type=str,
        default=None,
        help="单次提问（非交互模式）",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="调试模式：打印详细日志",
    )
    return parser


def cli() -> None:
    """解析命令行参数，创建并启动 Interpreter。"""
    from .interpreter import Interpreter
    from .config import get_config, reset_config
    import os

    parser = build_parser()
    args = parser.parse_args()

    # 命令行参数覆盖环境变量
    if args.debug:
        os.environ["DEBUG_MODE"] = "true"
        reset_config()  # 重置 lru_cache 使新配置生效

    cfg = get_config()

    interp = Interpreter(config=cfg)

    # 覆盖配置
    if args.auto_run:
        interp.auto_run = True
    if args.model:
        interp.model = args.model
        cfg.openai_model = args.model
    if args.debug:
        interp.debug_mode = True

    logger.info(
        f"[cli] 启动: model={interp.model}, auto_run={interp.auto_run}, "
        f"debug={interp.debug_mode}"
    )

    try:
        interp.chat(message=args.message)
    except KeyboardInterrupt:
        print("\n\n再见！")
        sys.exit(0)


# ── standalone 演示 ─────────────────────────────────────────────
if __name__ == "__main__":
    cli()