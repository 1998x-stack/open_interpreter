# Open Interpreter

> 让 LLM 在你的本地机器上真正执行代码的 Agent 框架

---

## 特性

- 🤖 **ReAct 循环**：LLM 生成代码 → 本地执行 → 结果反馈 → 迭代优化
- 🔌 **可插拔架构**：执行器（Python / Shell / JavaScript）和 LLM 后端均为工厂注册模式，轻松扩展
- 🎨 **Rich 终端 UI**：语法高亮代码块、Markdown 消息渲染、实时执行行高亮
- 🔒 **执行确认**：默认要求用户确认才执行代码（可通过 `-y` 跳过）
- 📝 **结构化日志**：全项目 loguru，统一异常格式

## 快速开始

```bash
# 1. 克隆并安装
git clone <repo>
cd open_interpreter
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，至少填入 OPENAI_API_KEY

# 3. 启动交互对话
python -m src.open_interpreter

# 4. 一次性提问
python -m src.open_interpreter --message "计算 1 到 100 的所有质数之和"

# 5. 自动执行（跳过确认）
python -m src.open_interpreter -y

# 6. 使用更快的模型
python -m src.open_interpreter --model gpt-3.5-turbo
```

## 运行示例任务

```bash
python tasks/task_01_fibonacci.py   # 斐波那契 + 性能分析
python tasks/task_02_data_analysis.py  # CSV 数据分析 + 可视化
python tasks/task_03_file_ops.py    # 文件批量操作
```

## 运行测试

```bash
pytest tests/ -v
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | API Key（必填）| — |
| `OPENAI_MODEL` | 模型名称 | `gpt-4o` |
| `OPENAI_BASE_URL` | API Base URL（支持代理）| OpenAI 官方 |
| `AUTO_RUN` | 跳过执行确认 | `false` |
| `DEBUG_MODE` | 调试模式 | `false` |

## 架构文档

详见 [OVERVIEW.md](./OVERVIEW.md)