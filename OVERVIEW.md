# Open Interpreter — 代码架构总览

> 本文档是整个项目的工程地图，面向接手、扩展或二次开发的工程师。

---

## 一、项目简介

Open Interpreter 是一个 **LLM 驱动的本地代码执行 Agent**。  
用户以自然语言提出任务，LLM 生成代码，在本地解释器中安全执行，结果反馈给 LLM 驱动下一轮推理——构成一个完整的 ReAct 闭环。

```
用户自然语言 → LLM 生成代码 → 本地执行 → 输出反馈 → LLM 迭代
```

---

## 二、目录结构

```
open_interpreter/
├── OVERVIEW.md                  ← 本文件
├── README.md                    ← 快速开始
├── .gitignore
├── .env.example                 ← 环境变量模板
├── requirements.txt
│
├── src/open_interpreter/        ← 核心包
│   ├── __init__.py              ← 导出 Interpreter
│   ├── config.py                ← 配置中心（env 读取、全局常量）
│   ├── interpreter.py           ← 主编排器（Interpreter 类）
│   ├── cli.py                   ← CLI 入口（argparse）
│   │
│   ├── display/                 ← 终端 UI 层（Rich）
│   │   ├── __init__.py
│   │   ├── base_block.py        ← 抽象基类 BaseBlock
│   │   ├── code_block.py        ← CodeBlock：代码 + 输出面板
│   │   └── message_block.py     ← MessageBlock：Markdown 消息面板
│   │
│   ├── execution/               ← 代码执行层（可插拔 Executor）
│   │   ├── __init__.py
│   │   ├── base_executor.py     ← 抽象基类 BaseExecutor
│   │   ├── executor_factory.py  ← ExecutorFactory（注册 + 创建）
│   │   ├── python_executor.py   ← Python subprocess 执行器
│   │   ├── shell_executor.py    ← Shell/Bash 执行器
│   │   └── javascript_executor.py ← Node.js 执行器
│   │
│   ├── llm/                     ← LLM 客户端层（可插拔）
│   │   ├── __init__.py
│   │   ├── base_llm.py          ← 抽象基类 BaseLLMClient
│   │   ├── llm_factory.py       ← LLMFactory（注册 + 创建）
│   │   └── openai_client.py     ← OpenAI/兼容 API 客户端
│   │
│   └── utils/                   ← 通用工具
│       ├── __init__.py
│       ├── json_utils.py        ← parse_partial_json, merge_deltas
│       └── output_utils.py      ← truncate_output, fix_code_indentation
│
├── tasks/                       ← 示例任务（可直接运行）
│   ├── task_01_fibonacci.py     ← 数学计算：斐波那契 + 性能分析
│   ├── task_02_data_analysis.py ← 数据分析：CSV 统计 + 可视化
│   └── task_03_file_ops.py      ← 文件操作：批量重命名 + 目录整理
│
└── tests/                       ← 单元测试（pytest）
    ├── __init__.py
    ├── test_config.py
    ├── test_executor_factory.py
    ├── test_python_executor.py
    ├── test_json_utils.py
    └── test_output_utils.py
```

---

## 三、模块职责详解

### 3.1 `config.py` — 配置中心

**职责**：集中管理所有环境变量和全局常量，单例模式，全项目唯一入口。

| 变量 | 来源 | 默认值 | 说明 |
|------|------|--------|------|
| `OPENAI_API_KEY` | env | 必填 | OpenAI / 兼容 API Key |
| `OPENAI_MODEL` | env | `gpt-4o` | 使用的模型名称 |
| `OPENAI_BASE_URL` | env | `https://api.openai.com/v1` | API Base URL（支持代理） |
| `AUTO_RUN` | env | `False` | 是否跳过用户确认 |
| `DEBUG_MODE` | env | `False` | 是否打印 debug 信息 |
| `MAX_OUTPUT_CHARS` | env | `2000` | 执行输出最大字符数 |
| `TEMPERATURE` | env | `0.01` | LLM temperature |

**关键函数**：
- `get_config() -> Settings`：获取全局配置单例
- `Settings.validate()`：启动时验证必填项，缺失时给出明确错误

---

### 3.2 `interpreter.py` — 主编排器

**职责**：协调 LLM 客户端、代码执行器、终端显示块，实现 ReAct 循环。

```
Interpreter
├── chat(message?)          ← 公开接口，交互式或单次对话
├── respond()               ← 内部核心：LLM 调用 + 流式处理 + 执行
├── _handle_function_call() ← 处理 LLM 的 run_code 调用
├── _execute_code()         ← 委托 ExecutorFactory 执行代码
└── _end_active_block()     ← 清理 Rich Live 显示
```

**ReAct 流程**：
1. `chat()` 收集用户输入，追加到 `self.messages`
2. `respond()` 构建系统消息，调用 LLM，流式接收 delta
3. delta 流中检测 `function_call`（GPT-4 格式）或 markdown code fence（本地模型格式）
4. 函数调用完成时，经用户确认（或 `auto_run`）后执行代码
5. 执行结果追加为 `{"role": "function", ...}`，递归调用 `respond()` 继续迭代
6. `finish_reason == "stop"` 时退出循环

---

### 3.3 `execution/` — 执行层（工厂模式）

**设计模式**：工厂 + 注册表（Registry Pattern）

```python
# 注册执行器
ExecutorFactory.register("python", PythonExecutor)
ExecutorFactory.register("shell", ShellExecutor)

# 创建执行器（懒加载，同 language 复用同一实例）
executor = ExecutorFactory.create("python", debug_mode=False)
output = executor.run(code)
```

**`BaseExecutor`（抽象基类）**：

| 方法 | 说明 |
|------|------|
| `start_process()` | 启动子进程（subprocess.Popen） |
| `run(code: str) -> str` | 执行代码，返回输出字符串 |
| `add_active_line_prints(code)` | 注入行号打印语句，用于高亮当前执行行 |
| `save_and_display_stream(stream)` | 后台线程，实时捕获 stdout/stderr |
| `stop()` | 终止子进程，清理资源 |

**各执行器特性**：

| 执行器 | 启动命令 | 行号注入 | 特殊处理 |
|--------|----------|----------|----------|
| `PythonExecutor` | `python -i -q -u` | ✅ | AST 解析 + 缩进修复 |
| `ShellExecutor` | `bash` / `cmd.exe` | ⚠️ 仅单行 | 多行跳过注入 |
| `JavaScriptExecutor` | `node -i` | ✅ | `console.log` 注入 |

---

### 3.4 `llm/` — LLM 客户端层（工厂模式）

**设计模式**：工厂 + 策略（Strategy Pattern）

```python
# 注册
LLMFactory.register("openai", OpenAIClient)

# 创建
client = LLMFactory.create("openai", config=get_config())

# 调用（返回流式 chunk 生成器）
for chunk in client.stream_chat(messages, functions=[function_schema]):
    delta = chunk["choices"][0]["delta"]
    ...
```

**`BaseLLMClient`（抽象基类）**：

| 方法 | 说明 |
|------|------|
| `stream_chat(messages, functions)` | 返回流式 chunk 生成器 |
| `trim_messages(messages, model, system)` | 裁剪消息列表以适应 context window |
| `validate_config()` | 验证 API key 等配置 |

---

### 3.5 `display/` — 终端 UI 层

基于 **Rich** 库，提供实时流式显示：

| 类 | 用途 | Rich 组件 |
|----|------|-----------|
| `CodeBlock` | 代码（语法高亮）+ 输出（白底）| `Live` + `Panel` + `Syntax` |
| `MessageBlock` | LLM 文本消息（Markdown 渲染）| `Live` + `Panel` + `Markdown` |

**关键设计**：
- `update_from_message(message)` 接受流式 delta 累积后的完整消息，每次 chunk 都触发刷新
- `active_line` 高亮当前执行行（白色背景标记）
- `end()` 关闭 `Live`，防止多个 `Live` 实例冲突

---

### 3.6 `utils/` — 工具函数

**`json_utils.py`**：
- `merge_deltas(original, delta)` — 合并 OpenAI 流式 delta 到完整消息
- `parse_partial_json(s)` — 容错解析不完整 JSON（流式 function_call arguments）
- `escape_newlines_in_json_string_values(s)` — 修复 JSON 字符串中的裸换行符

**`output_utils.py`**：
- `truncate_output(data, max_chars)` — 截断过长输出，保留末尾最重要部分
- `fix_code_indentation(code)` — 修复 `python -i` 交互模式的缩进问题
- `sanitize_output(output)` — 过滤 ACTIVE_LINE / END_OF_EXECUTION 控制信息

---

## 四、数据流图

```
用户输入
   │
   ▼
┌─────────────────────────────────────────────────────────────┐
│  Interpreter.respond()                                       │
│                                                              │
│  messages → LLMClient.stream_chat() → delta chunks          │
│                    │                                         │
│           ┌────────▼────────┐                               │
│           │  function_call? │                               │
│           └────────┬────────┘                               │
│          Yes │     │ No                                      │
│              ▼     ▼                                         │
│         CodeBlock  MessageBlock                              │
│              │                                              │
│              ▼                                              │
│    ExecutorFactory.create(language)                         │
│              │                                              │
│    executor.run(code) → output                              │
│              │                                              │
│    messages.append(role="function", content=output)         │
│              │                                              │
│    respond() ← 递归                                         │
└─────────────────────────────────────────────────────────────┘
   │
   ▼
最终回复（finish_reason == "stop"）
```

---

## 五、错误处理规范

全项目统一使用 loguru，异常记录模板：

```python
import sys, traceback
from loguru import logger

try:
    ...
except Exception:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    error_message = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.error(f"[模块名] 操作失败: {error_message}")
    raise
```

日志级别规范：

| 级别 | 使用场景 |
|------|----------|
| `DEBUG` | 每条 delta、每行输出、内部状态变化 |
| `INFO` | 会话开始/结束、代码执行开始/完成 |
| `WARNING` | 用户拒绝执行、超时、输出被截断 |
| `ERROR` | 子进程崩溃、API 调用失败、JSON 解析失败 |

---

## 六、扩展指南

### 添加新执行语言

```python
# 1. 继承 BaseExecutor
class RubyExecutor(BaseExecutor):
    START_CMD = "irb"
    PRINT_CMD = 'puts "{}"'
    ...

# 2. 注册到工厂
ExecutorFactory.register("ruby", RubyExecutor)

# 3. 添加到 function_schema 的 enum 列表
"enum": ["python", "shell", "javascript", "ruby"]
```

### 添加新 LLM 后端

```python
# 1. 继承 BaseLLMClient
class AnthropicClient(BaseLLMClient):
    def stream_chat(self, messages, functions=None):
        ...

# 2. 注册到工厂
LLMFactory.register("anthropic", AnthropicClient)

# 3. 在 config.py 中添加 LLM_PROVIDER 配置项
```

---

## 七、测试覆盖

| 测试文件 | 覆盖内容 |
|----------|----------|
| `test_config.py` | 环境变量读取、缺失校验、默认值 |
| `test_executor_factory.py` | 工厂注册/创建/未知语言报错 |
| `test_python_executor.py` | 代码执行、输出捕获、超时处理、异常格式 |
| `test_json_utils.py` | merge_deltas、parse_partial_json 边界情况 |
| `test_output_utils.py` | truncate_output、fix_code_indentation |

运行测试：
```bash
pytest tests/ -v --tb=short
```

---

## 八、快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY

# 运行交互式对话
python -m open_interpreter

# 运行示例任务
python tasks/task_01_fibonacci.py
python tasks/task_02_data_analysis.py
python tasks/task_03_file_ops.py

# 运行测试
pytest tests/ -v
```