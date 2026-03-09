# 3-1 Function Calling 不是魔法——结构化输出背后的设计哲学

> **系列**：Series 3 · LLM 的手与眼  
> **难度**：⭐⭐⭐☆☆

---

## 一个困扰早期 AI 工程师的难题

2022 年，当你想让 GPT-3 "调用一个函数"时，你需要这样：

```
System: 你是一个助手。当你需要查询天气时，在回复中写：
[TOOL: weather]
city: 北京
[END_TOOL]

User: 北京今天天气怎么样？
```

然后你祈祷 GPT-3 真的按格式输出，然后写一个正则表达式去解析它，然后发现有时候它会在 `[TOOL]` 标签之前写一堆废话，然后你的解析失败……

这是"Prompt 工程"时代的痛苦。工具调用是脆弱的、不可靠的、充满 edge case 的。

**2023 年 6 月，OpenAI 发布 Function Calling，这个时代结束了。**

---

## 什么让 Function Calling 可靠？

答案是：**将工具调用从"对话生成"中分离出来，作为独立的结构化输出**。

### 传统方式（对话内嵌工具调用）

```
模型输出（文本）：
"我需要查询天气。[TOOL: weather] city: 北京 [END_TOOL] 让我看看结果..."
```

问题：模型有自由"说其他的话"，工具调用与普通文本混杂，解析困难。

### Function Calling（结构化独立输出）

```json
// 模型的输出有两个独立字段：
{
  "content": null,           // 文本内容（此时为空）
  "tool_calls": [            // 工具调用（独立字段）
    {
      "id": "call_001",
      "type": "function",
      "function": {
        "name": "get_weather",
        "arguments": "{\"city\": \"北京\"}"
      }
    }
  ]
}
```

模型要么输出 `content`（普通文本），要么输出 `tool_calls`（工具调用），这两者在 API 层面是互斥的——消除了二义性。

---

## JSON Schema 的工程智慧

工具定义用 JSON Schema 描述，这不是随意的选择：

**1. JSON Schema 是标准的**

它不是 OpenAI 发明的，是 IETF 标准（draft-07 最广泛支持）。工程师熟悉它，有大量工具可以验证和生成它。

**2. JSON Schema 可以被 LLM 理解**

训练数据中有大量 JSON Schema，LLM 知道如何根据 Schema 生成符合要求的 JSON。

**3. JSON Schema 可以做类型约束**

```json
{
  "type": "object",
  "properties": {
    "code": {
      "type": "string",
      "description": "要执行的 Python 代码，不包含任何 markdown 格式"
    },
    "language": {
      "type": "string",
      "enum": ["python", "javascript"],
      "description": "编程语言"
    },
    "timeout": {
      "type": "integer",
      "minimum": 1,
      "maximum": 120,
      "description": "最大执行时间（秒）"
    }
  },
  "required": ["code"]
}
```

这个 Schema 不仅描述了参数，还约束了合法值的范围。当 LLM 输出不符合 Schema 的内容时，系统可以拒绝并要求重试。

---

## Structured Outputs：更进一步的约束

2024 年，OpenAI 推出了 **Structured Outputs**（结构化输出），本质是让模型输出**保证符合特定 JSON Schema** 的文本——通过修改模型解码过程中的 token 采样来实现。

```python
from openai import OpenAI
from pydantic import BaseModel

class CodeExecution(BaseModel):
    code: str
    explanation: str
    expected_output: str

client = OpenAI()
response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[{"role": "user", "content": "写一个计算阶乘的函数"}],
    response_format=CodeExecution,
)
result = response.choices[0].message.parsed
# result.code, result.explanation, result.expected_output 都是有类型的
```

这让 LLM 的输出第一次真正可以作为强类型的数据结构使用。

---

## Tool Description 的炼金术

Function Calling 解决了**格式**的问题，但工具**什么时候被选择**，仍然取决于工具描述的质量。

这是一门艺术，也是一门工程：

### 糟糕的描述

```json
"description": "执行代码"
```

LLM 不知道这个工具的边界，在不该用的时候会用，该用的时候可能不用。

### 专业的描述

```json
"description": "在安全的 Python 沙箱中执行代码。适用场景：\n- 数值计算（比心算更可靠）\n- 数据处理和分析（pandas, numpy）\n- 数据可视化（matplotlib, seaborn, plotly）\n- 字符串处理和格式转换\n- 算法测试和验证\n\n不适用场景：\n- 访问互联网（网络隔离）\n- 长时间运行任务（>2分钟超时）\n- GPU 计算\n\n执行环境：Python 3.11，预装 pandas/numpy/matplotlib/scipy/sklearn。用户文件在 /uploaded/ 目录。"
```

这个描述告诉 LLM：这个工具能做什么、不能做什么、什么时候该用它。

**工具描述的质量，是 Agent 质量上限的决定因素之一。**

---

## 下一篇

知道了工具是怎么定义和调用的，接下来的问题是：一次工具调用不够怎么办？LLM 怎么在多次调用之间保持推理的连贯性？

**→ 3-2：ReAct 模式：思考-行动-观察死循环的威力**

---
---

# 3-2 ReAct 模式：思考-行动-观察死循环的威力

> **系列**：Series 3 · LLM 的手与眼  
> **难度**：⭐⭐⭐☆☆

---

## 为什么一次工具调用不够？

考虑这个任务：

> "分析 sales.csv，找出销售额最高的 5 个城市，画出它们的月度趋势对比图，并指出哪个城市的增长最稳定。"

这个任务需要至少：

1. 加载并探索数据（了解列名、数据类型、空值情况）
2. 按城市聚合，找 Top 5
3. 提取 Top 5 城市的月度数据
4. 画折线图
5. 计算增长稳定性（可能需要多种统计方法）
6. 综合分析

每一步都可能失败，每一步的结果都影响下一步的决策。这不是一次工具调用能完成的——这需要一个**推理-执行-观察**的循环。

这就是 **ReAct 模式**。

---

## ReAct 是什么？

ReAct（**Re**asoning + **Act**ing）是 2022 年 Google Research 提出的一种 LLM 推理框架（论文：*ReAct: Synergizing Reasoning and Acting in Language Models*）。

核心思想：让 LLM 在推理和行动之间**交替进行**：

```
Thought:  [内部推理，分析当前状态，决定下一步]
Action:   [调用工具，执行操作]
Observation: [观察工具执行结果]
Thought:  [根据观察更新推理...]
Action:   [再次行动...]
...
Final Answer: [完成任务]
```

---

## 一次完整的 ReAct 执行演示

任务：分析 sales.csv

```
Thought: 我需要先了解数据的结构和质量，然后才能进行分析。让我先加载数据看看基本情况。

Action: code_interpreter
Input:
  import pandas as pd
  df = pd.read_csv('/uploaded/sales.csv')
  print(f"Shape: {df.shape}")
  print(f"Columns: {list(df.columns)}")
  print(f"Data types:\n{df.dtypes}")
  print(f"\nFirst 3 rows:\n{df.head(3)}")
  print(f"\nNull values:\n{df.isnull().sum()}")

Observation:
  Shape: (15420, 6)
  Columns: ['date', 'city', 'product', 'sales', 'quantity', 'price']
  Data types:
  date       object
  city       object
  ...
  sales     float64
  
  First 3 rows:
  date        city    product  sales  quantity  price
  2023-01-03  上海     电视机   2580    1        2580
  ...
  
  Null values:
  date      0
  city      0
  sales     23

Thought: 数据有 15420 行 6 列，sales 列有 23 个空值需要处理。date 列是 object 类型，需要转换为 datetime。现在找 Top 5 销售城市。

Action: code_interpreter
Input:
  # 清洗数据
  df = df.dropna(subset=['sales'])
  df['date'] = pd.to_datetime(df['date'])
  df['month'] = df['date'].dt.to_period('M')
  
  # Top 5 城市
  top5_cities = df.groupby('city')['sales'].sum().nlargest(5).index.tolist()
  print(f"Top 5 城市: {top5_cities}")
  
  # 月度趋势数据
  monthly = df[df['city'].isin(top5_cities)].groupby(['month', 'city'])['sales'].sum().unstack()
  print(f"\n月度数据形状: {monthly.shape}")
  print(monthly.head())

Observation:
  Top 5 城市: ['上海', '北京', '深圳', '广州', '杭州']
  
  月度数据形状: (12, 5)
  city          上海      北京     深圳     广州     杭州
  month
  2023-01  450000  380000  320000  290000  210000
  ...

Thought: 完美。现在画折线图，然后计算增长稳定性。稳定性可以用月环比增长率的标准差来衡量——标准差越小，增长越稳定。

Action: code_interpreter
Input:
  import matplotlib.pyplot as plt
  import matplotlib
  matplotlib.rcParams['font.family'] = 'SimHei'
  
  fig, ax = plt.subplots(figsize=(12, 6))
  
  colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6']
  for i, city in enumerate(top5_cities):
      ax.plot(range(len(monthly)), monthly[city].values, 
              label=city, color=colors[i], linewidth=2, marker='o')
  
  ax.set_xticks(range(len(monthly)))
  ax.set_xticklabels([str(m) for m in monthly.index], rotation=45)
  ax.set_title('Top 5 城市月度销售趋势（2023年）', fontsize=14, fontweight='bold')
  ax.set_ylabel('销售额（元）')
  ax.legend()
  ax.grid(True, alpha=0.3)
  plt.tight_layout()
  plt.savefig('/generated/sales_trend.png', dpi=150)
  print("图表已保存")
  
  # 计算增长稳定性（月环比增长率的标准差）
  for city in top5_cities:
      growth_rates = monthly[city].pct_change().dropna()
      stability = growth_rates.std()
      print(f"{city}: 增长率标准差 = {stability:.3f}")

Observation:
  图表已保存
  上海: 增长率标准差 = 0.082
  北京: 增长率标准差 = 0.071
  深圳: 增长率标准差 = 0.143
  广州: 增长率标准差 = 0.095
  杭州: 增长率标准差 = 0.068

Thought: 增长最稳定的是杭州（标准差 0.068 最小），其次是北京（0.071）。现在我可以给出完整的分析结论了。

Final Answer:
根据 2023 年销售数据分析（附图）：

**Top 5 销售城市**（按全年总销售额）：
上海、北京、深圳、广州、杭州

**增长稳定性排名**（月环比增长率标准差，越低越稳定）：
1. 杭州 (0.068) ← 最稳定
2. 北京 (0.071)
3. 上海 (0.082)
4. 广州 (0.095)
5. 深圳 (0.143)

**结论**：虽然深圳的某些月份增长很快，但波动也最大；**杭州**的增长最为稳定均衡，值得重点关注。
```

---

## ReAct 的关键设计原则

从上面的例子可以提炼出几个关键原则：

**1. Thought 是自由的，Action 是结构化的**

`Thought` 是 LLM 的自由文本推理，可以包含任何想法；`Action` 必须是格式化的工具调用。这种分离让 LLM 既有推理的灵活性，又有行动的可靠性。

**2. 每次 Action 尽量单一**

不要在一次 Action 里塞太多逻辑。步骤清晰，失败后容易定位问题。

**3. Observation 必须被"消化"**

LLM 看到 Observation 后，应该在下一个 Thought 中明确体现对观察结果的理解，而不是直接进行下一步 Action。

**4. 错误是学习机会**

当代码报错时，LLM 不应该"假装没看到"，而应该在 Thought 中分析错误原因，在下一个 Action 中修正。

---

## ReAct vs Chain-of-Thought

| 特性 | Chain-of-Thought (CoT) | ReAct |
|------|------------------------|-------|
| 推理方式 | 纯文本思维链 | 思维链 + 工具调用 |
| 信息来源 | 仅模型内部知识 | 内部知识 + 外部工具 |
| 适用场景 | 逻辑推理、数学 | 需要实际执行的任务 |
| 可验证性 | 低（结果无法外部验证） | 高（执行结果是客观的）|
| 幻觉风险 | 高 | 低（计算结果有代码保证）|

ReAct 不是 CoT 的替代，而是增强：先 CoT 规划，然后 ReAct 执行。

---

## 下一篇

ReAct 的精髓是"失败→观察→修正"。但这个修正过程的细节是什么？当代码出错时，LLM 到底在"看"什么？

**→ 3-3：代码自修复：当 LLM 看到 Traceback 会发生什么？**

---
---

# 3-3 代码自修复：当 LLM 看到 Traceback 会发生什么？

> **系列**：Series 3 · LLM 的手与眼  
> **难度**：⭐⭐⭐☆☆

---

## 一个让人惊讶的事实

大多数人以为 Code Interpreter 里的代码"第一次就能跑通"。

实际上，OpenAI 内部数据（来自他们的研究博客）显示，**大约 40% 的代码执行会经历至少一次错误和重试**。

Code Interpreter 的真正魔力，不是"写出正确的代码"，而是"写出错了能自己修"。

---

## 自修复的三类场景

### 场景一：ModuleNotFoundError（模块缺失）

```
Action: import plotly.express as px
Observation: ModuleNotFoundError: No module named 'plotly'

Thought: plotly 未预装，需要先安装
Action: !pip install plotly -q
Observation: Successfully installed plotly-5.18.0

Action: import plotly.express as px
Observation: [成功]
```

这是最简单的自修复场景。LLM 看到错误信息，识别出"模块未安装"的模式，执行安装命令，再重试。

### 场景二：ValueError/TypeError（数据问题）

```
Action: 
  df['date'] = pd.to_datetime(df['date'])
  df.groupby('date')['sales'].sum().plot()

Observation:
  ValueError: Mixed types in column 'date', could not convert

Thought: date 列有混合类型，可能有非日期字符串。需要用 errors='coerce' 参数，
        并检查有多少无效值。

Action:
  df['date'] = pd.to_datetime(df['date'], errors='coerce')
  invalid_count = df['date'].isna().sum()
  print(f"无效日期数量: {invalid_count}")
  df_clean = df.dropna(subset=['date'])
  print(f"清洗后数据量: {len(df_clean)}")
  df_clean.groupby('date')['sales'].sum().plot()

Observation:
  无效日期数量: 8
  清洗后数据量: 15412
  [图表生成成功]
```

### 场景三：逻辑错误（执行成功但结果不对）

这是最难修复的场景，因为没有 Traceback，LLM 需要通过推理发现问题：

```
Action:
  # 计算月均增长率
  monthly_growth = monthly['sales'].pct_change().mean()
  print(f"月均增长率: {monthly_growth:.2%}")

Observation:
  月均增长率: 150.23%

Thought: 150% 的月均增长率明显不合理。pct_change() 的第一个值是 NaN，
        mean() 默认跳过 NaN，但如果数据有零值会导致除零，产生异常大的增长率。
        我需要检查原始数据是否有异常值。

Action:
  print(monthly['sales'].head(10))
  print(monthly['sales'].describe())
  # 检查是否有零值
  print(f"零值行数: {(monthly['sales'] == 0).sum()}")

Observation:
  2023-01    0.0
  2023-02    450000.0
  ...
  零值行数: 1

Thought: 1月份销售额为 0，是数据问题。从2月开始计算增长率。

Action:
  monthly_clean = monthly['sales'][monthly['sales'] > 0]
  monthly_growth = monthly_clean.pct_change().dropna().mean()
  print(f"月均增长率（排除零值）: {monthly_growth:.2%}")

Observation:
  月均增长率（排除零值）: 3.47%
```

---

## LLM 是如何"读懂" Traceback 的？

Python 的 Traceback 是结构化的：

```
Traceback (most recent call last):
  File "<ipython-input>", line 3, in <module>
    result = df.merge(df2, on='user_id', how='left')
  File "/usr/lib/python3/pandas/core/reshape/merge.py", line 108, in merge
    ...
KeyError: 'user_id'
```

这个 Traceback 包含了：

1. **错误类型**：`KeyError`
2. **错误位置**：哪一行代码
3. **错误原因**：`'user_id'` 这个 key 不存在
4. **调用栈**：完整的调用路径

LLM 能够"读懂"这些信息，因为：

- 训练数据中有大量 Python 代码和 Traceback 的配对
- LLM 学会了错误类型与可能原因之间的对应关系
- Traceback 的结构是固定的，LLM 能可靠地解析

---

## 自修复的边界：LLM 修不好的情况

不是所有错误都能自动修复。以下场景会让自修复失效：

**1. 错误过于笼统（Ambiguous Error）**

```
RuntimeError: CUDA error: device-side assert triggered
```

这个错误不包含足够的诊断信息，LLM 只能猜测。

**2. 错误在逻辑上需要外部知识**

```
ValueError: The target variable has only 1 unique class. Cannot train classifier.
```

这个错误需要 LLM 理解数据集的业务含义，才能判断是数据问题还是代码问题。

**3. 无限重试循环**

某些情况下，LLM 会陷入"修复→新错误→再修复→原错误"的循环。需要设置最大重试次数（通常 3-5 次）和人工干预机制。

---

## 设计一个好的错误反馈机制

如果你在构建自己的 Code Interpreter，以下是错误反馈的最佳实践：

```python
def format_execution_result(stdout, stderr, error=None):
    """格式化执行结果，让 LLM 能最高效地处理"""
    
    if error is None:
        # 成功：返回标准输出（截断过长的输出）
        result = truncate(stdout, max_chars=3000)
        return {"status": "success", "output": result}
    
    else:
        # 失败：提供完整错误信息 + 相关代码片段
        return {
            "status": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": format_traceback(error),
            # 关键：告诉 LLM 错误发生在哪一行
            "failed_line": extract_failed_line(error),
            "suggestion": get_error_hint(error)  # 可选：规则匹配的修复建议
        }

def get_error_hint(error):
    """基于错误类型给出修复提示"""
    hints = {
        "ModuleNotFoundError": "可能需要 pip install 安装模块",
        "KeyError": "检查列名是否正确，可以用 df.columns 查看",
        "MemoryError": "数据集可能太大，尝试分块处理",
        "TimeoutError": "执行超时，考虑优化代码性能",
    }
    return hints.get(type(error).__name__, "")
```

**关键设计原则**：给 LLM 的错误信息应该**足够精确**（包含位置和原因），但不应该**过度冗长**（不要塞入整个调用栈，只需要最相关的几行）。

---

## 下一篇

代码自修复解决了"单次出错"的问题。但当任务非常长（需要 20+ 轮执行），上下文窗口怎么管理？

**→ 3-4：多轮迭代与上下文压缩：长任务的工程挑战**

---
---

# 3-4 多轮迭代与上下文压缩：长任务的工程挑战

> **系列**：Series 3 · LLM 的手与眼  
> **难度**：⭐⭐⭐⭐☆

---

## 一个 Token 的悲剧

假设你在用 Code Interpreter 做一个复杂的数据科学任务：

- 10 轮数据清洗（每轮输出约 500 tokens）
- 5 轮特征工程（每轮约 300 tokens）
- 8 轮模型训练与调参（每轮约 800 tokens）
- 3 轮可视化（每轮约 200 tokens）

总对话历史：26 轮 × 平均 ~600 tokens = **~15,600 tokens**

加上 system prompt（~1000 tokens）、用户消息（~3000 tokens）、LLM 的 thought（~6000 tokens）……

**你的上下文窗口已经用了 25,600 tokens，还有 100,000 tokens 剩余（GPT-4o: 128K）。**

看起来还行？但随着任务深入，这个数字会持续增长。而且，更重要的问题是：**LLM 真的需要记住第 2 轮的清洗细节吗？**

---

## 上下文的价值不均等

并不是所有的对话历史都同等重要。

```
高价值信息（应该保留）：
  - 用户的最终目标（"分析销售趋势"）
  - 已发现的关键数据特征（"date 列有空值"）
  - 已确认的数据结构（"columns: date, city, sales"）
  - 当前任务状态（"已完成清洗，正在进行可视化"）

低价值信息（可以压缩）：
  - 第 3 轮 print(df.head()) 的完整输出
  - 已被解决的错误的详细 Traceback
  - 探索性的中间结果（已被更好的结果覆盖）
  - 反复出现的类似命令
```

上下文压缩的目标：**保留高价值信息，压缩或丢弃低价值信息**。

---

## 三种上下文管理策略

### 策略一：滑动窗口（Sliding Window）

保留最近 N 轮对话，丢弃更早的历史。

```python
def apply_sliding_window(messages, max_turns=10):
    # 保留 system message + 最近 max_turns 轮对话
    system_msgs = [m for m in messages if m['role'] == 'system']
    conversation = [m for m in messages if m['role'] != 'system']
    
    if len(conversation) > max_turns * 2:  # 每轮 2 条消息（user + assistant）
        conversation = conversation[-(max_turns * 2):]
    
    return system_msgs + conversation
```

**优点**：简单，零额外 LLM 调用  
**缺点**：早期的重要信息可能被丢弃（比如第 1 轮发现的数据结构）

### 策略二：智能摘要（Summarization）

当对话超过阈值时，用 LLM 生成摘要替换早期消息：

```python
async def compress_history(messages, threshold_tokens=50000):
    if count_tokens(messages) < threshold_tokens:
        return messages
    
    # 保留最近 5 轮，压缩更早的历史
    recent = messages[-10:]  # 最近 5 轮（每轮 user + assistant）
    to_compress = messages[1:-10]  # 系统消息后的其余部分
    
    summary_prompt = f"""
    请将以下 Code Interpreter 对话历史压缩为一个简洁的状态摘要，包含：
    1. 分析目标
    2. 数据基本信息（列名、类型、大小）
    3. 已完成的步骤及主要发现
    4. 当前数据的状态（已做了哪些清洗/转换）
    5. 尚未完成的任务
    
    对话历史：
    {format_messages(to_compress)}
    """
    
    summary = await llm.complete(summary_prompt)
    
    return [
        messages[0],  # 系统消息
        {"role": "assistant", "content": f"[对话历史摘要]\n{summary}"},
        *recent
    ]
```

**优点**：保留关键信息，上下文利用率高  
**缺点**：额外的 LLM 调用（成本和延迟）；摘要可能丢失细节

### 策略三：结构化状态（Structured State）

不依赖对话历史，而是维护一个显式的"分析状态"对象：

```python
analysis_state = {
    "goal": "分析销售数据的月度趋势",
    "data": {
        "file": "sales.csv",
        "shape": [15420, 6],
        "columns": ["date", "city", "product", "sales", "quantity", "price"],
        "cleaned": True,
        "date_range": "2023-01 ~ 2023-12"
    },
    "completed_steps": [
        "数据加载",
        "缺失值处理（23行空值已删除）",
        "date列类型转换",
        "Top 5 城市识别：上海/北京/深圳/广州/杭州"
    ],
    "current_step": "绘制月度趋势图",
    "outputs": ["sales_trend.png"]
}

# 在每次请求中，将状态注入 system prompt
system_prompt = f"""
你是数据分析助手。当前分析状态：
{json.dumps(analysis_state, ensure_ascii=False, indent=2)}

继续完成当前步骤：{analysis_state['current_step']}
"""
```

**优点**：最精确，不依赖自然语言摘要的质量  
**缺点**：需要系统层维护状态，实现复杂

---

## 执行结果截断：一个被低估的工程细节

即使上下文管理得当，**单次执行结果过大**仍是常见问题：

```python
# 这行代码的输出可能有 50,000 字节
print(df)  # 打印整个 DataFrame

# 经过截断处理后
MAX_OUTPUT_TOKENS = 2000

def format_output(stdout: str, max_tokens: int = MAX_OUTPUT_TOKENS) -> str:
    if count_tokens(stdout) <= max_tokens:
        return stdout
    
    # 策略：保留开头和结尾，中间用省略号
    lines = stdout.split('\n')
    if len(lines) > 50:
        head = '\n'.join(lines[:25])
        tail = '\n'.join(lines[-10:])
        omitted = len(lines) - 35
        return f"{head}\n\n... [{omitted} 行已省略，总计 {len(lines)} 行] ...\n\n{tail}"
    
    # 按字符截断
    chars = max_tokens * 4  # 粗略估算
    return stdout[:chars] + f"\n... [输出已截断，原始长度: {len(stdout)} 字符]"
```

**关键原则**：截断时要告诉 LLM"已截断"，不然 LLM 会以为输出就那么多，可能做出错误判断。

---

## 图像的特殊处理

当代码生成图表时，有两种处理方式：

**方式 A：文件引用（推荐）**
```json
{"type": "file_id", "file_id": "gen-trend-001"}
```
LLM 看到文件 ID，用户界面显示图片。LLM 本身如果是 multimodal，可以"看到"并分析图片内容。

**方式 B：Base64 嵌入（高 token 消耗）**
一张 150dpi 的图表约 100-500KB，Base64 后约 133-667KB，转为 token 约 33K-166K tokens——直接塞爆上下文。

**最佳实践**：图像始终用文件引用，不嵌入原始 Base64 内容。

---

## Series 3 总结

你现在理解了 LLM 与代码执行的完整协同机制：

- **Function Calling**：将工具调用从对话中分离，实现结构化、可靠的工具调度
- **ReAct 模式**：Thought-Action-Observation 循环，让 LLM 能进行真正的多步推理
- **自修复机制**：错误 Traceback 是 LLM 的"感官"，驱动自动纠错
- **上下文管理**：滑动窗口/摘要/结构化状态，应对长任务的 token 压力

你已经拥有了理解 Code Interpreter 全貌所需的所有知识。接下来，让我们看看真实世界里，这些技术是如何工程化落地的。

**→ 进入 Series 4：工业级 Code Interpreter 的工程实践**

---

*技术延伸：Amazon Bedrock Session Management API 提供了结构化状态管理的云原生实现，包括 session checkpoint、replay 和 IAM/KMS 集成。如果你在 AWS 生态构建长会话 Agent，这是值得深入研究的方向。*
