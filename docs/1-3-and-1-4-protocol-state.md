# 1-3 LLM 与代码执行：两个世界的对话协议

> **系列**：Series 1 · 从一个问题出发  
> **难度**：⭐⭐⭐☆☆

---

## 一个思想实验

假设你雇了一个程序员，但你们不会说同一种语言。你只会中文，他只会 Python。

你怎么让他工作？

你必须设计一套**协议**：

- 你用中文描述需求
- 他用某种固定格式告诉你"我要写代码了"
- 他写代码并执行
- 他用某种固定格式把结果反馈给你
- 你看结果，继续用中文给下一步指令

**这就是 Function Calling / Tool Use 协议的本质。**

---

## Function Calling 的设计哲学

在 2023 年 6 月 OpenAI 发布 Function Calling 之前，让 LLM 调用工具的方式非常原始：

```
System Prompt：
"当你需要执行代码时，在你的回复中用这个格式：
[CODE]
# 这里写代码
[/CODE]
然后我会帮你执行并把结果告诉你。"
```

这种方式有明显的缺点：

1. **格式不稳定**：LLM 可能在 `[CODE]` 里夹杂文字解释
2. **参数复杂时难以解析**：如果工具需要多个参数，解析就是一场灾难
3. **无法区分工具**：如果有多个工具，怎么告诉 LLM 它调用的是哪个？

Function Calling 用 **JSON Schema** 解决了这些问题。

---

## JSON Schema：结构化输出的锚点

### 工具定义

工具（Tool）需要用 JSON Schema 描述它的接口：

```json
{
  "type": "function",
  "function": {
    "name": "code_interpreter",
    "description": "在沙箱中执行 Python 代码并返回结果",
    "parameters": {
      "type": "object",
      "properties": {
        "code": {
          "type": "string",
          "description": "要执行的 Python 代码"
        }
      },
      "required": ["code"]
    }
  }
}
```

这个 Schema 被放入 LLM 的请求中。LLM 的训练让它"懂得"：当它想调用工具时，输出一个**符合这个 Schema 的 JSON 对象**，而不是普通文本。

### LLM 输出格式

当 LLM 决定调用工具时，它的输出是：

```json
{
  "role": "assistant",
  "content": null,
  "tool_calls": [
    {
      "id": "call_abc123",
      "type": "function",
      "function": {
        "name": "code_interpreter",
        "arguments": "{\"code\": \"import math\\nprint(math.pi)\"}"
      }
    }
  ]
}
```

注意：`arguments` 是一个 **JSON 字符串**（而不是直接的 JSON 对象）。这是 OpenAI 的设计，原因是支持流式输出（Streaming）时可以逐 token 输出 arguments 字符串。

### 结果注入格式

执行完后，结果通过 `tool` 角色的消息注入回对话：

```json
{
  "role": "tool",
  "tool_call_id": "call_abc123",
  "content": "3.141592653589793"
}
```

---

## 多工具场景的路由机制

Code Interpreter 通常不是系统中唯一的工具。真实的 Agent 系统里可能同时有：

- `code_interpreter`：执行 Python
- `web_search`：搜索互联网
- `file_search`：检索上传的文档
- `send_email`：发送邮件
- 自定义工具...

LLM 如何知道这次应该用哪个？

这取决于两件事：

**1. 工具描述的质量（Tool Description）**

工具描述是 LLM 选择工具的唯一依据。描述写得越精准，LLM 选择越准确。

```json
// 差的描述
"description": "运行代码"

// 好的描述
"description": "在安全沙箱中执行 Python 代码，适用于：数值计算、数据处理（pandas/numpy）、图表生成（matplotlib）、文件格式转换。不适用于：访问互联网、长时间任务（>2分钟）。"
```

**2. 上下文（User Message + System Prompt）**

如果用户说"搜索一下最新的 GDP 数据"，LLM 会倾向于选 `web_search`；如果说"计算这份数据的标准差"，会倾向于 `code_interpreter`。

**并行调用（Parallel Tool Calls）**

GPT-4 和 Claude 3+ 都支持在一次回复中生成多个 tool call，它们会并行执行：

```json
"tool_calls": [
  {"id": "call_001", "name": "code_interpreter", "arguments": "..."},
  {"id": "call_002", "name": "code_interpreter", "arguments": "..."}
]
```

这对于需要同时分析多个数据集的场景很有用。

---

## Anthropic Claude 的 Tool Use 差异

Claude 的 Tool Use 与 OpenAI 的 Function Calling 设计类似，但有几处差异值得注意：

```xml
<!-- Claude 的工具调用格式（XML-based） -->
<tool_use>
  <name>code_interpreter</name>
  <input>
    <code>print("hello world")</code>
  </input>
</tool_use>
```

以及通过 `tool_result` block 返回结果：

```python
{
    "role": "user",
    "content": [
        {
            "type": "tool_result",
            "tool_use_id": "toolu_abc",
            "content": "hello world\n"
        }
    ]
}
```

虽然格式不同，但协议的设计哲学是一致的：**把工具调用从"对话"中分离出来，变成一种可以被程序稳定解析的结构化输出**。

---

## 协议之外：Prompt 工程的隐秘作用

一个常被忽视的事实：**LLM 知道调用 code_interpreter 工具，有一半是靠 System Prompt 教会的**。

一个好的 Code Interpreter System Prompt 大概长这样：

```
You are a data analysis assistant with access to a Python code execution environment.

When solving problems that require calculation or data processing:
1. ALWAYS write and execute code rather than attempting mental arithmetic
2. Show your reasoning before writing code
3. When code fails, analyze the error message and fix the code
4. For large DataFrames, only print the first few rows or summary statistics
5. When creating visualizations, always save to a file and reference it
6. You have access to: pandas, numpy, matplotlib, scipy, sklearn, and standard library

The user's uploaded files are available at /uploaded/<filename>.
```

这个 prompt 在做几件重要的事：

1. **确立身份**：你是一个数据分析助手
2. **强制使用代码**：碰到计算，一定要写代码，不要心算
3. **规范行为**：报错后要修复，大数据集要截断输出
4. **告知环境**：可用的库、文件路径

System Prompt 的质量，直接决定了 Code Interpreter 的使用体验。

---

## 一个常见的误解澄清

很多人以为：LLM 会自动知道什么时候用 code_interpreter。

实际上，这个决策是**有成本的**，而且并不总是正确的。

LLM 可能会：
- 对于简单的加减法，直接回答而不用代码（这是正确的行为）
- 对于复杂的统计，却用文字描述而不写代码（这是错误的行为）
- 过度使用代码，把本来可以直接回答的问题也走一遍执行循环（浪费延迟）

解决方案是在 System Prompt 中明确指定何时必须用代码，以及通过 `tool_choice` 参数强制 LLM 调用特定工具：

```json
"tool_choice": {"type": "tool", "name": "code_interpreter"}
// 或
"tool_choice": "auto"  // LLM 自行决定
```

---

## 下一篇

你理解了代码是怎么生成的，也理解了结果是怎么反馈的。但有一个问题还没有回答：

你在第 1 轮对话里定义的 `df`，在第 5 轮对话里还存在吗？
会话超时之后，我的分析中间结果去哪了？

**→ 1-4：状态、会话与上下文：Code Interpreter 的"记忆"机制**

---
---

# 1-4 状态、会话与上下文：Code Interpreter 的"记忆"机制

> **系列**：Series 1 · 从一个问题出发  
> **难度**：⭐⭐⭐☆☆

---

## 一个让人抓狂的体验

你在 ChatGPT Code Interpreter 里花了 10 分钟做数据分析：

- 加载了一个 200MB 的数据集
- 做了几轮清洗和特征工程
- 训练了一个模型
- 正准备生成最终报告

然后你发现页面有点卡，刷新了一下。

再问它"继续刚才的分析"。

**它说：我不知道你说的是什么。**

所有变量、所有中间结果，消失了。

这是 Code Interpreter 最常见的用户投诉之一。理解为什么会发生这件事，需要你搞清楚"状态"在这个系统中是怎么存在的。

---

## 三层"记忆"：它们互不相同

Code Interpreter 系统中，有三种不同性质的"记忆"，很多人把它们混淆了：

### 第一层：LLM 的对话上下文（Context Window）

这是 LLM 看到的东西——所有的消息历史，包括用户输入、LLM 回复、tool call 记录和 tool result。

**性质：**
- 存在于 LLM 的推理过程中
- 以 token 为单位，有容量上限（GPT-4o: ~128K tokens）
- 对话历史越长，消耗 token 越多
- **不包含** Python 变量的实际值

**关键误解**：LLM 的上下文里保存的是"第 3 轮你 print 了 df.head() 的结果"，而不是 `df` 这个变量本身。

### 第二层：Jupyter Kernel 的执行状态（Kernel Namespace）

这是 Python 运行时的内存——所有 `import` 的模块、定义的变量、训练好的模型。

**性质：**
- 存在于沙箱 Kernel 进程的内存中
- 与 LLM 的上下文**互相独立**
- 会话内持久（多轮执行共享同一 Kernel）
- 会话结束（超时或主动关闭）后**永久消失**

**关键特性**：这就是为什么你在第 1 轮 `df = pd.read_csv(...)` 之后，第 5 轮仍然可以直接使用 `df`。

### 第三层：沙箱文件系统（Sandbox FS）

这是沙箱内的磁盘文件——上传的文件、生成的图表、保存的模型。

**性质：**
- 存在于沙箱的虚拟文件系统中
- 可在同一会话的多次执行中访问
- 会话结束后清除（除非显式导出）
- 用户上传的文件通常只读挂载

---

## 会话生命周期详解

```
                    创建会话
                       │
                  ┌────▼────┐
                  │ Active  │  ← Kernel 运行中，变量存活
                  └────┬────┘
                       │ 30-60 分钟无活动
                  ┌────▼────┐
                  │  Idle   │  ← Kernel 可能被暂停（取决于实现）
                  └────┬────┘
                       │ 超出最大时长 or 主动关闭
                  ┌────▼────┐
                  │Terminated│ ← Kernel 内存清空，文件删除
                  └─────────┘
```

**各平台的超时策略：**

| 平台 | 最大会话时长 | 超时策略 |
|------|------------|----------|
| OpenAI ChatGPT | ~1 小时 | "Session expired" 提示 |
| OpenAI API (container) | 可配置 | container_id 失效 |
| E2B | 24 小时 | 自动终止 |
| Northflank | 无限制 | 手动或按需终止 |
| AWS AgentCore | 8 小时 | 三态转换（Active/Idle/Terminated）|

---

## 会话超时后发生了什么？

当会话超时，用户还在继续对话时，系统通常有两种策略：

**策略 A：静默重启（Silent Restart）**

重新创建一个空的 Kernel，继续对话。用户会发现之前的变量消失了，代码报 `NameError`。

这是最常见也最让用户困惑的体验。

**策略 B：显式告知（Explicit Notification）**

在 LLM 的 System Prompt 中注入会话状态信息，让 LLM 主动告知用户：

```
System: "Note: The code execution environment has been reset. 
Variables from previous executions are no longer available. 
Inform the user if they reference previous results."
```

**用户能做什么？**

如果你需要跨越可能的会话重置继续工作，最佳实践是在每次分析结束时**显式保存状态**：

```python
# 在每轮关键计算后保存
import pickle
with open('/generated/session_state.pkl', 'wb') as f:
    pickle.dump({
        'df': df,
        'model': trained_model,
        'params': best_params
    }, f)
print("状态已保存")
```

---

## 上下文窗口的压力

随着对话变长，LLM 的上下文窗口会面临压力。

每次代码执行都会产生结果文本，这些文本被追加到 messages 中。如果：

- 每轮 print 了大量数据（比如 `print(df)`）
- 进行了很多轮执行（20+ 轮）
- 错误信息很长

上下文就会逼近 token 上限。

这时系统（或 LLM 自己）需要做**上下文压缩**：

**方法一：截断早期消息**

删除最早的对话轮次，保留最新的上下文。风险：LLM 可能丢失对任务目标的记忆。

**方法二：摘要压缩**

用另一个 LLM 调用，将之前的对话历史压缩成摘要，替换原始消息。

```python
# 伪代码：自动压缩上下文
if total_tokens > threshold:
    summary = summarize_llm(messages[:-5])  # 压缩除最近5轮外的历史
    messages = [{"role": "system", "content": summary}] + messages[-5:]
```

**方法三：结果截断（最常见）**

限制每次执行结果的最大长度。这是最简单的工程方案。

```python
MAX_OUTPUT_CHARS = 5000

def truncate_output(output: str) -> str:
    if len(output) > MAX_OUTPUT_CHARS:
        return output[:MAX_OUTPUT_CHARS] + "\n...[输出已截断]"
    return output
```

---

## 文件的特殊地位

在三层记忆中，**文件是唯一能跨越会话持续存在的东西**（如果你及时下载的话）。

这就是为什么 Code Interpreter 总是鼓励你：

- 用 `plt.savefig()` 保存图表而不是 `plt.show()`
- 用 `df.to_csv()` 保存处理后的数据
- 用 `model.save()` 保存训练好的模型

因为这些文件可以被用户下载到本地，也可以在后续对话中被重新上传使用——即使 Kernel 已经重置，文件还在。

---

## 一个工程设计的取舍

你可能会问：为什么不把 Kernel 状态持久化到数据库？这样会话重置后还能恢复？

这个思路是合理的，但有几个挑战：

1. **序列化难度**：Python 对象（尤其是 ML 模型、自定义类）的序列化非常复杂
2. **安全性**：持久化的 Kernel 状态可能携带敏感数据，存储需要加密
3. **成本**：序列化/反序列化大型对象（几 GB 的模型）本身就很耗时
4. **版本兼容**：恢复后的环境库版本可能不同

这就是为什么大多数 Code Interpreter 选择"轻状态"设计——会话内有状态，会话间无状态。

这个设计的代价，用户已经切身体会了。

---

## Series 1 总结

至此，你对 Code Interpreter 的基础认知已经完整：

- **是什么**：LLM + 沙箱执行 + 结果反馈的闭环系统
- **怎么运行**：7 阶段执行管道
- **如何通信**：Function Calling / Tool Use JSON 协议
- **怎么记忆**：三层异质状态（上下文/Kernel/文件系统）

接下来，让我们深入那个你每天依赖却从未真正了解的黑盒：

**沙箱是怎么做到"让任意代码安全运行"的？**

**→ 进入 Series 2：那堵看不见的墙——沙箱安全隔离深度解析**

---

*写给想进一步探索的读者：会话状态持久化是 AI Coding Agent 领域最活跃的工程课题之一。E2B 的沙箱快照（Snapshot）功能、AWS AgentCore Memory API，都是这个方向的实际探索。*
