# 1-2 你的代码是怎么"跑"起来的？——执行管道全解析

> **系列**：Series 1 · 从一个问题出发  
> **难度**：⭐⭐☆☆☆

---

## 一个你从未想过的问题

你在 ChatGPT 里上传了一个 100MB 的 CSV，打了几行字：

> "帮我分析一下各省份的销售趋势，画出折线图。"

然后你等了大概 8 秒，看到了一张图和一段分析。

这 8 秒里，发生了什么？

我不是在说"AI 理解了你的意思"这种模糊的描述。我是说，**在工程层面，数据从你的浏览器出发，经历了哪些节点，最终变成那张图？**

这条管道，是本文的主题。

---

## 完整执行管道：7 个阶段

让我们把这 8 秒拆开，逐帧分析：

```
用户输入 + 文件上传
        │
        ▼
[Phase 1] 请求路由与上下文构建
        │
        ▼
[Phase 2] LLM 推理：意图理解与代码生成
        │
        ▼
[Phase 3] Tool Call 解析与分发
        │
        ▼
[Phase 4] 沙箱调度与代码注入
        │
        ▼
[Phase 5] Jupyter Kernel 执行
        │
        ▼
[Phase 6] 执行结果捕获与格式化
        │
        ▼
[Phase 7] 结果反馈给 LLM，生成最终回复
```

下面逐一解析。

---

## Phase 1：请求路由与上下文构建

当你点击发送，你的请求不是直接到 LLM 的。

首先，**你上传的文件被处理**：

1. 文件被上传到服务器存储（对象存储或临时 blob）
2. 生成一个文件 ID（如 `file-abc123`）
3. 文件被挂载或注册到即将创建的沙箱环境中

然后，**会话上下文被构建**：

- 当前对话历史（所有之前的 messages）
- 可用工具列表（包括 `code_interpreter`）
- 工具配置（沙箱 container ID 或 auto 模式）
- 系统提示（告诉 LLM 它可以使用代码工具）

最终，一个完整的请求 payload 被构建并发往 LLM 服务：

```json
{
  "model": "gpt-4o",
  "messages": [
    {"role": "system", "content": "You are a data analysis assistant..."},
    {"role": "user", "content": "帮我分析各省份的销售趋势，画出折线图。"},
  ],
  "tools": [
    {
      "type": "code_interpreter",
      "container": {
        "type": "auto",
        "file_ids": ["file-abc123"]
      }
    }
  ]
}
```

---

## Phase 2：LLM 推理——意图理解与代码生成

LLM 收到请求后，开始做两件事：

**第一：理解意图**

- 用户想要什么？（分析 + 可视化）
- 数据在哪里？（上传的文件 `file-abc123`，会被映射到沙箱内的路径）
- 需要什么库？（pandas 处理数据，matplotlib 画图）
- 有什么陷阱？（数据可能有空值、编码问题、日期格式等）

**第二：生成代码**

LLM 输出的不是纯文本，而是一个 **tool call**：

```json
{
  "type": "tool_use",
  "id": "call_xyz789",
  "name": "code_interpreter",
  "input": {
    "code": "import pandas as pd\nimport matplotlib.pyplot as plt\n\ndf = pd.read_csv('/uploaded/file-abc123.csv')\n\n# 解析省份和日期列\ndf['date'] = pd.to_datetime(df['date'])\ndf['month'] = df['date'].dt.to_period('M')\n\n# 按省份和月份汇总\nmonthly_sales = df.groupby(['province', 'month'])['sales'].sum().unstack(level=0)\n\n# 绘图\nfig, ax = plt.subplots(figsize=(12, 6))\nmonthly_sales.plot(ax=ax)\nax.set_title('各省份月度销售趋势')\nax.set_xlabel('月份')\nax.set_ylabel('销售额')\nplt.tight_layout()\nplt.savefig('/generated/sales_trend.png', dpi=150)\nprint('图表已生成')\nprint(df.groupby('province')['sales'].sum().sort_values(ascending=False).head(10))"
  }
}
```

注意两个细节：

1. 文件路径 `/uploaded/file-abc123.csv` 是**预定义的沙箱内路径**，由系统在 Phase 1 设置
2. 输出图表路径 `/generated/` 是沙箱内的**结果存放目录**

---

## Phase 3：Tool Call 解析与分发

系统（不是 LLM，是编排层）收到 LLM 的响应后：

1. 识别这是一个 `code_interpreter` tool call
2. 提取代码字符串
3. 决定路由到哪个沙箱（新建 or 复用已有会话）

这个编排层是整个系统的"交通警察"，它决定：

- 是否需要创建新的沙箱容器
- 这个 tool call 是否属于某个已有 session
- 代码的安全预检（可选）

---

## Phase 4：沙箱调度与代码注入

沙箱调度器接到任务后：

**如果是新会话：**

```
1. 从空闲池取出一个预热的沙箱实例（或冷启动一个新的）
2. 将用户文件挂载到 /uploaded/ 目录
3. 初始化 Jupyter Kernel
4. 记录 session_id，建立心跳机制
```

**如果是已有会话：**

```
1. 定位到该 session_id 对应的沙箱实例
2. 确认 Kernel 仍存活
3. 直接注入代码（保留之前定义的变量）
```

代码注入方式本质上是通过 **Jupyter Kernel 的 ZMQ 消息协议**：

```python
# 伪代码：执行管理层如何向 Kernel 发送代码
kernel_client.execute_interactive(
    code=tool_call.code,
    timeout=120,  # 2 分钟超时
    output_hook=capture_output
)
```

---

## Phase 5：Jupyter Kernel 执行

这是整个管道中最"朴实"的一步，也是最重要的一步。

Jupyter Kernel（本质是一个 IPython 进程）收到代码后：

1. 解析 Python 语法
2. 在当前 namespace 中执行（保留之前轮次的变量）
3. 收集所有输出：
   - `stdout`（print 的内容）
   - `stderr`（报错信息）
   - `display_data`（plt.show() 的图像等富媒体）
   - 文件系统变更（savefig 写入的文件）

**Jupyter Kernel 的有状态性，是 Code Interpreter 能进行多轮迭代分析的核心。**

```python
# 第 1 轮：加载数据
df = pd.read_csv('data.csv')  # df 被保存在 Kernel 的 namespace

# 第 2 轮（同一 Kernel，df 仍然存在）
df['new_col'] = df['a'] / df['b']  # 无需重新加载

# 第 3 轮
print(df['new_col'].describe())  # 继续使用
```

如果每次都要重新加载数据，分析一个 500MB 的文件需要每轮等 10 秒——这显然不可接受。

---

## Phase 6：执行结果捕获与格式化

Kernel 执行完毕后，结果需要被**格式化成 LLM 可以"读懂"的格式**。

这是一个被严重低估的工程细节。

**文本输出**：直接作为字符串返回，但要注意**截断策略**——如果 `print` 了一个 10000 行的 DataFrame，全部塞进 LLM 上下文会炸 token 限制。

**图像输出**：
- 方式 A：Base64 编码后直接嵌入结果（适合 multimodal LLM）
- 方式 B：存为文件，返回文件 ID + URL（更省 token）

**文件输出**：
- 记录生成文件的路径、MIME 类型
- 对用户暴露下载链接
- 文件 ID 可以在后续 LLM 调用中被引用

典型的结果格式：

```json
{
  "type": "tool_result",
  "tool_use_id": "call_xyz789",
  "content": [
    {
      "type": "text",
      "text": "图表已生成\n省份销售排名:\n广东    58000000\n浙江    42000000\n..."
    },
    {
      "type": "image",
      "source": {
        "type": "file_id",
        "file_id": "generated-file-trend-001"
      }
    }
  ]
}
```

---

## Phase 7：结果反馈与最终回复生成

执行结果被追加到对话历史中，再次发给 LLM：

```
[messages]
  - user: "帮我分析..."
  - assistant: [tool_use call]
  - tool_result: [执行结果 + 图像]
```

LLM 此时"看到"了图表内容和数字，可以进行：

- 自然语言描述趋势
- 指出异常值
- 提出下一步分析建议
- 如果代码报错，自动修改并重试

LLM 输出最终回复，完成一次完整的 ReAct 循环。

---

## 时序图总结

```
User        Frontend     LLM API      Orchestrator    Sandbox
 │              │            │              │             │
 │─── 文件上传 ─→│            │              │             │
 │              │──── 请求 ──→│              │             │
 │              │            │─── tool call─→│             │
 │              │            │              │─── 执行代码 ─→│
 │              │            │              │             │（Jupyter运行）
 │              │            │              │←── 执行结果 ─│
 │              │            │←── tool result│             │
 │              │            │（LLM看到结果，生成回复）      │
 │              │←── 最终回复 ─│              │             │
 │←── 显示 ──────│            │              │             │
```

---

## 一个容易被忽视的真相

整个管道中，LLM 只参与了 **Phase 2** 和 **Phase 7** 两个环节。

其余的文件上传、沙箱调度、Kernel 执行、结果捕获——全是**传统软件工程**，跟"AI"没有直接关系。

这告诉我们一件重要的事：

> **Code Interpreter 的质量，有一半取决于工程，而不是模型。**

当你的 Code Interpreter 用起来很慢、经常出错、结果截断——很可能是工程层出了问题，不是模型不够聪明。

---

## 下一篇

管道明白了。但 LLM 是怎么"知道"自己该写代码的？那个从自然语言到 JSON 的 tool call 格式，背后是怎么设计的？

**→ 1-3：LLM 与代码执行：两个世界的对话协议**

---

*延伸思考：如果你要设计一个支持 10 万并发用户的 Code Interpreter 服务，Phase 4 的沙箱调度会是最大瓶颈。具体的工程策略，见 Series 4。*
