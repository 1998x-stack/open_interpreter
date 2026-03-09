# 5-1 最小可用版本：50 行 Python 里的 Code Interpreter 框架

> **系列**：Series 5 · 手撸一个 Code Interpreter  
> **难度**：⭐⭐☆☆☆

---

## 动手的时刻到了

前四个系列，我们理解了 Code Interpreter 的原理：

- 它是一个 LLM + 沙箱执行 + 结果反馈的闭环
- 沙箱用 gVisor/Firecracker 隔离
- LLM 通过 Function Calling 调用工具
- ReAct 模式驱动多轮迭代

现在，让我们**从零开始实现一个可以运行的版本**。

本文的目标：用尽量少的代码，实现一个完整的 Code Interpreter 框架——能理解需求、生成代码、执行代码、反馈结果、迭代修复。

**注意**：这个版本不安全（直接使用 exec）。我们先让它能跑，Series 5-2 再加沙箱。

---

## 核心循环：50 行实现

```python
"""
最小 Code Interpreter 实现
- 不安全的 exec 沙箱（仅用于学习原理）
- 支持多轮迭代和自修复
"""

import io
import sys
import contextlib
import anthropic  # 或 openai

client = anthropic.Anthropic()
TOOLS = [
    {
        "name": "execute_python",
        "description": (
            "在 Python 环境中执行代码。"
            "适用于数值计算、数据处理、绘图等需要精确计算的任务。"
            "代码运行在有状态环境中，之前定义的变量可以继续使用。"
            "当任务需要计算时，务必使用此工具而非直接回答。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码，不包含 markdown 代码块格式"
                }
            },
            "required": ["code"]
        }
    }
]


def execute_code(code: str, namespace: dict) -> dict:
    """
    在给定 namespace 中执行代码，捕获输出
    返回 stdout、stderr 和是否成功
    """
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    with contextlib.redirect_stdout(stdout_capture), \
         contextlib.redirect_stderr(stderr_capture):
        try:
            exec(code, namespace)  # ⚠️ 不安全，仅用于学习
            return {
                "status": "success",
                "stdout": stdout_capture.getvalue(),
                "stderr": stderr_capture.getvalue()
            }
        except Exception as e:
            import traceback
            return {
                "status": "error", 
                "stdout": stdout_capture.getvalue(),
                "stderr": traceback.format_exc()
            }


def run_code_interpreter(user_query: str, max_iterations: int = 10) -> str:
    """
    主循环：ReAct 风格的 Code Interpreter
    """
    messages = [{"role": "user", "content": user_query}]
    namespace = {}  # Python 执行状态（跨迭代保持）
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- 迭代 {iteration} ---")
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            tools=TOOLS,
            messages=messages
        )
        
        # 添加 LLM 响应到历史
        messages.append({"role": "assistant", "content": response.content})
        
        # 检查停止原因
        if response.stop_reason == "end_turn":
            # LLM 决定不再调用工具，给出最终答案
            final_text = next(
                (block.text for block in response.content 
                 if hasattr(block, 'text')),
                "任务完成"
            )
            print(f"✅ 最终答案: {final_text[:200]}")
            return final_text
        
        if response.stop_reason != "tool_use":
            break
        
        # 处理所有工具调用
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            
            if block.name == "execute_python":
                code = block.input["code"]
                print(f"📝 执行代码:\n{code[:300]}...")
                
                # 执行代码
                result = execute_code(code, namespace)
                
                # 构建反馈内容
                if result["status"] == "success":
                    output = result["stdout"] or "(无输出)"
                    print(f"✅ 执行成功: {output[:200]}")
                    content = f"执行成功\n标准输出:\n{output[:2000]}"
                else:
                    print(f"❌ 执行失败: {result['stderr'][:200]}")
                    content = f"执行失败\n错误信息:\n{result['stderr'][:2000]}"
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content
                })
        
        # 把执行结果反馈给 LLM
        messages.append({"role": "user", "content": tool_results})
    
    return "已达到最大迭代次数"


# 使用示例
if __name__ == "__main__":
    # 测试 1：数学计算
    result = run_code_interpreter(
        "计算 1 到 1000 之间所有质数的总和，并统计质数个数"
    )
    
    # 测试 2：自修复能力
    result = run_code_interpreter(
        "用 pandas 创建一个示例 DataFrame，计算各列的描述性统计"
    )
    
    # 测试 3：多步任务
    result = run_code_interpreter(
        "生成 100 个随机正态分布数，计算均值和标准差，然后用 matplotlib 画直方图并保存为 histogram.png"
    )
```

---

## 运行它，观察 ReAct 循环

```bash
pip install anthropic matplotlib numpy
python minimal_interpreter.py
```

输出大概是这样：

```
--- 迭代 1 ---
📝 执行代码:
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

primes = [x for x in range(1, 1001) if is_prime(x)]
print(f"质数个数: {len(primes)}")
print(f"质数总和: {sum(primes)}")
✅ 执行成功: 质数个数: 168
质数总和: 76127

--- 迭代 2 ---
✅ 最终答案: 1 到 1000 之间共有 168 个质数，它们的总和为 76127。
```

---

## 理解这 50 行代码的关键设计

**1. `namespace` 字典的作用**

`exec(code, namespace)` 中的 `namespace` 是所有变量的存放处。每次调用 `execute_code` 都传入同一个 `namespace`，这实现了跨调用的状态保持——这就是"有状态 Kernel"的简化版实现。

**2. 消息历史的维护**

`messages` 列表记录了完整的对话历史，包括每次工具调用和执行结果。这是 ReAct 循环的记忆载体——LLM 通过这个历史了解已经做了什么、得到了什么结果。

**3. 停止条件**

循环有两个退出条件：
- `stop_reason == "end_turn"`：LLM 自己决定任务完成
- `iteration >= max_iterations`：防止无限循环

---

## 下一篇

这个最小版本能跑，但有一个致命问题：你在自己的机器上直接运行了 LLM 生成的代码！

如果 LLM 生成了 `os.system('rm -rf /')` 你就知道有多危险了。

**→ 5-2：用 Docker + FastAPI 打造安全的代码执行后端**

---
---

# 5-2 用 Docker + FastAPI 打造安全的代码执行后端

> **系列**：Series 5 · 手撸一个 Code Interpreter  
> **难度**：⭐⭐⭐☆☆

---

## 架构设计

我们要把不安全的 `exec()` 替换为真正的容器化执行。

架构分为两个服务：

```
┌─────────────────┐        HTTP        ┌──────────────────────────┐
│   Orchestrator  │ ────────────────→  │   Sandbox API Server     │
│   (LLM + ReAct) │                    │   (运行在 Docker 容器中)   │
│                 │ ←──────────────── │   /execute 接受代码执行    │
└─────────────────┘       结果         └──────────────────────────┘
```

Orchestrator 运行在宿主机，与 LLM 通信。
Sandbox API 运行在隔离的 Docker 容器中，执行实际代码。

---

## Step 1：实现 Sandbox API Server

```python
# sandbox_server.py
# 运行在 Docker 容器内的代码执行服务

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import io
import contextlib
import traceback
import signal
from typing import Optional

app = FastAPI(title="Code Execution Sandbox")


class ExecuteRequest(BaseModel):
    code: str
    timeout_seconds: int = 30


class ExecuteResponse(BaseModel):
    status: str          # "success" | "error" | "timeout"
    stdout: str
    stderr: str
    execution_time_ms: int


# 全局 namespace，跨请求保持状态（模拟 Jupyter Kernel）
_execution_namespace: dict = {}


def timeout_handler(signum, frame):
    raise TimeoutError("代码执行超时")


@app.post("/execute", response_model=ExecuteResponse)
async def execute_code(request: ExecuteRequest):
    """在沙箱中执行 Python 代码"""
    
    import time
    start_time = time.time()
    
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    
    # 设置超时信号
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(request.timeout_seconds)
    
    try:
        with contextlib.redirect_stdout(stdout_buf), \
             contextlib.redirect_stderr(stderr_buf):
            exec(request.code, _execution_namespace)
        
        signal.alarm(0)  # 取消超时
        
        return ExecuteResponse(
            status="success",
            stdout=stdout_buf.getvalue()[:5000],  # 截断
            stderr=stderr_buf.getvalue()[:1000],
            execution_time_ms=int((time.time() - start_time) * 1000)
        )
        
    except TimeoutError:
        return ExecuteResponse(
            status="timeout",
            stdout=stdout_buf.getvalue()[:5000],
            stderr=f"执行超时（>{request.timeout_seconds}秒）",
            execution_time_ms=request.timeout_seconds * 1000
        )
        
    except Exception as e:
        signal.alarm(0)
        return ExecuteResponse(
            status="error",
            stdout=stdout_buf.getvalue()[:5000],
            stderr=traceback.format_exc()[:3000],
            execution_time_ms=int((time.time() - start_time) * 1000)
        )


@app.post("/reset")
async def reset_namespace():
    """重置执行状态"""
    global _execution_namespace
    _execution_namespace = {}
    return {"status": "reset"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
```

---

## Step 2：打包成 Docker 镜像

```dockerfile
# Dockerfile.sandbox
FROM python:3.11-slim

WORKDIR /app

# 安装常用数据科学包
RUN pip install --no-cache-dir \
    pandas==2.1.0 \
    numpy==1.25.0 \
    matplotlib==3.7.0 \
    scipy==1.11.0 \
    scikit-learn==1.3.0 \
    seaborn==0.12.0 \
    fastapi==0.104.0 \
    uvicorn==0.24.0

COPY sandbox_server.py .

# 创建非 root 用户（减少权限）
RUN useradd -m -u 1000 sandbox
USER sandbox

EXPOSE 8080

CMD ["uvicorn", "sandbox_server:app", "--host", "0.0.0.0", "--port", "8080"]
```

```bash
# 构建镜像
docker build -f Dockerfile.sandbox -t code-sandbox:latest .

# 启动沙箱容器（带资源限制！）
docker run -d \
  --name sandbox-001 \
  --memory="1g" \            # 内存限制 1GB
  --cpus="0.5" \             # CPU 限制 0.5 核
  --pids-limit=50 \          # 最多 50 个进程（防 fork 炸弹）
  --network=none \            # 断网！
  --read-only \              # 只读文件系统
  --tmpfs /tmp:size=256m \   # 临时可写目录
  -p 18080:8080 \
  code-sandbox:latest
```

注意 `--network=none`：容器完全断网，无法访问互联网或内网。

---

## Step 3：Orchestrator 调用沙箱 API

```python
# orchestrator.py
# 运行在宿主机，连接 LLM 和沙箱

import httpx
import anthropic
from typing import Optional

SANDBOX_URL = "http://localhost:18080"  # 沙箱 API 地址
client = anthropic.Anthropic()

TOOLS = [
    {
        "name": "execute_python",
        "description": "在安全的 Docker 沙箱中执行 Python 代码。网络访问受限，最大执行时间 30 秒。",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python 代码"}
            },
            "required": ["code"]
        }
    }
]


async def execute_in_sandbox(code: str, timeout: int = 30) -> dict:
    """调用沙箱 API 执行代码"""
    async with httpx.AsyncClient(timeout=60) as http:
        try:
            response = await http.post(
                f"{SANDBOX_URL}/execute",
                json={"code": code, "timeout_seconds": timeout}
            )
            result = response.json()
            
            # 格式化返回给 LLM 的内容
            if result["status"] == "success":
                output = result["stdout"] or "(代码执行成功，无输出)"
                return {"content": f"✅ 执行成功（{result['execution_time_ms']}ms）:\n{output}"}
            elif result["status"] == "timeout":
                return {"content": f"⏱️ 执行超时（>{timeout}秒），已终止。请优化代码。"}
            else:
                return {"content": f"❌ 执行错误:\n{result['stderr']}"}
                
        except httpx.ConnectError:
            return {"content": "❌ 沙箱服务不可用，请检查 Docker 容器状态"}


async def run_code_interpreter(query: str) -> str:
    """使用真实沙箱的 Code Interpreter"""
    messages = [{"role": "user", "content": query}]
    
    for i in range(15):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            tools=TOOLS,
            messages=messages
        )
        
        messages.append({"role": "assistant", "content": response.content})
        
        if response.stop_reason == "end_turn":
            final = next(
                (b.text for b in response.content if hasattr(b, 'text')), 
                "完成"
            )
            return final
        
        if response.stop_reason != "tool_use":
            break
        
        tool_results = []
        for block in response.content:
            if block.type == "tool_use" and block.name == "execute_python":
                result = await execute_in_sandbox(block.input["code"])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    **result
                })
        
        messages.append({"role": "user", "content": tool_results})
    
    return "完成"


# 运行
import asyncio

async def main():
    result = await run_code_interpreter(
        "分析 1 到 100 的所有整数，找出所有回文数，计算它们的总和"
    )
    print(result)

asyncio.run(main())
```

---

## 测试安全性

```python
# 测试：危险代码是否被隔离？

# 测试 1：文件系统访问
await execute_in_sandbox("import os; print(os.listdir('/'))")
# 容器内只能看到容器文件系统，而不是宿主机

# 测试 2：网络访问
await execute_in_sandbox("import socket; s = socket.socket(); s.connect(('google.com', 80))")
# 报错：网络不可用（--network=none）

# 测试 3：Fork 炸弹
await execute_in_sandbox("import os\nwhile True: os.fork()")
# 超出 pids-limit=50，进程被强制终止

# 测试 4：内存炸弹
await execute_in_sandbox("data = []; \nwhile True: data.append(' ' * 1024 * 1024)")
# 超出 memory=1g，OOM Killer 介入
```

所有危险操作都被容器的资源限制和网络隔离阻止了。

---

# 5-3 接入 LLM：实现完整的 ReAct 代码执行 Agent

> **系列**：Series 5 · 手撸一个 Code Interpreter  
> **难度**：⭐⭐⭐⭐☆

---

## 从单工具到多工具 Agent

Series 5-2 实现了单工具（execute_python）的 Code Interpreter。

真实的 Agent 通常有多个工具协作：

```python
TOOLS = [
    {
        "name": "execute_python",
        "description": "执行 Python 代码，适合计算、数据分析、可视化",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string"}
            },
            "required": ["code"]
        }
    },
    {
        "name": "upload_file",
        "description": "告诉用户需要上传文件。当需要处理用户数据文件时使用。",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_description": {
                    "type": "string",
                    "description": "需要什么样的文件，用于告知用户"
                }
            },
            "required": ["file_description"]
        }
    },
    {
        "name": "read_uploaded_file",
        "description": "读取用户已上传的文件内容（文本文件，如 CSV、JSON、TXT）",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string"}
            },
            "required": ["filename"]
        }
    }
]
```

---

## 完整的 Agent 实现

```python
# full_agent.py
import asyncio
import os
import json
from pathlib import Path
from typing import Optional
import httpx
import anthropic

client = anthropic.Anthropic()
SANDBOX_URL = "http://localhost:18080"
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class CodeInterpreterAgent:
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self.messages = []
        self.system_prompt = """你是一个专业的数据分析和编程助手，拥有 Python 代码执行能力。

工具使用原则：
1. 任何需要精确计算的问题，必须写代码执行，不要心算
2. 数据分析任务：先探索数据结构，再逐步分析，每步确认结果
3. 当代码出错时，仔细阅读错误信息，针对性修复
4. 生成的图表保存为 /tmp/output.png（执行后用户可下载）
5. 对大数据集（>1000行），先抽样检查，再全量处理

Python 环境：
- 可用包：pandas, numpy, matplotlib, scipy, sklearn, seaborn
- 文件存储：/tmp/ 目录（可写）
- 网络：不可用

沟通原则：
- 在执行前简述计划
- 执行后解释结果含义
- 主动发现并指出数据问题"""
        
    async def chat(self, user_message: str, uploaded_file: Optional[str] = None) -> str:
        """处理一轮用户输入"""
        
        # 处理文件上传
        if uploaded_file:
            self.messages.append({
                "role": "user",
                "content": f"[用户上传了文件: {uploaded_file}]\n\n{user_message}"
            })
        else:
            self.messages.append({"role": "user", "content": user_message})
        
        # ReAct 循环
        for _ in range(20):  # 最多 20 次迭代
            response = client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=self.system_prompt,
                tools=TOOLS,
                messages=self.messages
            )
            
            self.messages.append({
                "role": "assistant",
                "content": response.content
            })
            
            # 完成
            if response.stop_reason == "end_turn":
                return self._extract_text(response.content)
            
            if response.stop_reason != "tool_use":
                break
            
            # 执行工具
            tool_results = await self._execute_tools(response.content, uploaded_file)
            self.messages.append({
                "role": "user",
                "content": tool_results
            })
        
        return "任务处理完成"
    
    async def _execute_tools(self, content_blocks, uploaded_file: Optional[str]) -> list:
        """并行执行所有工具调用"""
        tasks = []
        for block in content_blocks:
            if block.type != "tool_use":
                continue
            
            if block.name == "execute_python":
                tasks.append(self._run_execute_python(block))
            elif block.name == "read_uploaded_file":
                tasks.append(self._run_read_file(block, uploaded_file))
            elif block.name == "upload_file":
                tasks.append(self._run_upload_request(block))
        
        return await asyncio.gather(*tasks)
    
    async def _run_execute_python(self, block) -> dict:
        code = block.input["code"]
        
        # 如果有上传文件，注入文件路径信息
        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.post(
                f"{SANDBOX_URL}/execute",
                json={"code": code, "timeout_seconds": 60}
            )
            result = resp.json()
        
        if result["status"] == "success":
            output = result["stdout"][:3000] or "(无输出)"
            content = f"执行成功 ({result['execution_time_ms']}ms)\n{output}"
        elif result["status"] == "timeout":
            content = "执行超时（>60秒）。请优化算法或减少数据量。"
        else:
            content = f"执行错误:\n{result['stderr'][:2000]}"
        
        return {
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": content
        }
    
    async def _run_read_file(self, block, uploaded_file: Optional[str]) -> dict:
        filename = block.input["filename"]
        
        if not uploaded_file:
            content = "没有上传的文件。请先上传文件。"
        else:
            try:
                file_path = UPLOAD_DIR / uploaded_file
                file_content = file_path.read_text(encoding='utf-8', errors='replace')
                content = f"文件内容（前 5000 字符）:\n{file_content[:5000]}"
            except Exception as e:
                content = f"读取文件失败: {e}"
        
        return {
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": content
        }
    
    async def _run_upload_request(self, block) -> dict:
        description = block.input["file_description"]
        return {
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": f"已通知用户上传：{description}（等待用户操作）"
        }
    
    def _extract_text(self, content_blocks) -> str:
        return " ".join(
            block.text for block in content_blocks
            if hasattr(block, 'text')
        )
    
    def reset(self):
        """重置对话历史"""
        self.messages = []


# 使用示例
async def demo():
    agent = CodeInterpreterAgent()
    
    # 多轮对话
    print(await agent.chat("帮我生成一个费波那契数列的前 20 项，并分析它们的增长率"))
    print("\n" + "="*50 + "\n")
    print(await agent.chat("现在用这些数据做一个可视化，展示增长率的变化趋势"))

asyncio.run(demo())
```

---

## 关键工程细节：工具并行执行

上面代码中，`asyncio.gather(*tasks)` 实现了**并行执行多个工具调用**。

当 LLM 在一次响应中生成多个 tool_use blocks 时（比如同时要读文件和执行代码），这些操作可以并行进行，减少总等待时间。

---

# 5-4 生产化改造：限流、超时、资源配额、日志一网打尽

> **系列**：Series 5 · 手撸一个 Code Interpreter  
> **难度**：⭐⭐⭐⭐☆

---

## 从"能跑"到"可用于生产"

5-3 的 Agent 在开发环境下运行良好。但如果你要把它部署给真实用户，还需要很多硬化工作。

这是一个检查清单：

- [ ] 限流（Rate Limiting）：防止单用户滥用
- [ ] 超时控制：整体请求超时 + 单次代码执行超时
- [ ] 资源配额：每用户的 CPU/内存/存储限制
- [ ] 错误恢复：沙箱崩溃后的自动重建
- [ ] 并发控制：最大并发沙箱数限制
- [ ] 日志与监控：结构化日志、指标上报
- [ ] 优雅关闭：清理沙箱资源

---

## 限流实现

```python
# rate_limiter.py
import time
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field

@dataclass
class RateLimitConfig:
    requests_per_minute: int = 20    # 每分钟最多 20 次请求
    max_concurrent: int = 3          # 最多 3 个并发会话
    max_tokens_per_day: int = 500000 # 每天最多 50 万 token

class UserRateLimiter:
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._request_times: dict[str, list] = defaultdict(list)
        self._concurrent: dict[str, int] = defaultdict(int)
        self._semaphores: dict[str, asyncio.Semaphore] = {}
    
    def _get_semaphore(self, user_id: str) -> asyncio.Semaphore:
        if user_id not in self._semaphores:
            self._semaphores[user_id] = asyncio.Semaphore(
                self.config.max_concurrent
            )
        return self._semaphores[user_id]
    
    async def check_and_acquire(self, user_id: str) -> bool:
        """检查限流并获取执行许可，返回是否允许"""
        now = time.time()
        
        # 清理过期的请求记录（1 分钟内）
        self._request_times[user_id] = [
            t for t in self._request_times[user_id]
            if now - t < 60
        ]
        
        # 检查每分钟请求数
        if len(self._request_times[user_id]) >= self.config.requests_per_minute:
            return False
        
        # 记录本次请求
        self._request_times[user_id].append(now)
        return True
    
    def get_concurrent_semaphore(self, user_id: str) -> asyncio.Semaphore:
        return self._get_semaphore(user_id)
```

---

## 超时控制

```python
import asyncio
from functools import wraps

def with_timeout(timeout_seconds: float):
    """装饰器：给异步函数添加超时控制"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"操作超时（>{timeout_seconds}秒）。"
                    "请简化任务或分步骤执行。"
                )
        return wrapper
    return decorator


@with_timeout(300)  # 整体超时 5 分钟
async def handle_user_request(agent: CodeInterpreterAgent, query: str) -> str:
    return await agent.chat(query)
```

---

## 错误恢复：沙箱健康检查

```python
class SandboxManager:
    """管理沙箱实例的创建、监控和恢复"""
    
    def __init__(self, max_sandboxes: int = 10):
        self.max_sandboxes = max_sandboxes
        self._sandboxes: dict[str, SandboxInstance] = {}
        self._lock = asyncio.Lock()
    
    async def get_or_create(self, session_id: str) -> SandboxInstance:
        async with self._lock:
            if session_id in self._sandboxes:
                sandbox = self._sandboxes[session_id]
                
                # 健康检查
                if not await sandbox.is_healthy():
                    # 沙箱已死，重建
                    await sandbox.destroy()
                    del self._sandboxes[session_id]
                    sandbox = await self._create_new(session_id)
                    self._sandboxes[session_id] = sandbox
                
                return sandbox
            
            # 检查容量
            if len(self._sandboxes) >= self.max_sandboxes:
                # 驱逐最久未使用的沙箱
                await self._evict_oldest()
            
            sandbox = await self._create_new(session_id)
            self._sandboxes[session_id] = sandbox
            return sandbox
    
    async def _create_new(self, session_id: str) -> "SandboxInstance":
        container = DockerContainer.create(
            image="code-sandbox:latest",
            name=f"sandbox-{session_id[:8]}",
            memory_limit="1g",
            cpu_limit=0.5,
            network_disabled=True,
        )
        return SandboxInstance(session_id=session_id, container=container)
    
    async def _evict_oldest(self):
        if not self._sandboxes:
            return
        oldest_id = min(self._sandboxes, key=lambda k: self._sandboxes[k].last_used)
        await self._sandboxes[oldest_id].destroy()
        del self._sandboxes[oldest_id]
```

---

## 结构化日志

```python
import structlog
import time

logger = structlog.get_logger()

# 配置 structlog（输出 JSON 格式）
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)


class InstrumentedCodeInterpreterAgent(CodeInterpreterAgent):
    """带日志的 Code Interpreter Agent"""
    
    async def chat(self, user_message: str, user_id: str = "anonymous", **kwargs) -> str:
        start = time.time()
        iteration_count = 0
        
        log = logger.bind(
            user_id=user_id,
            message_length=len(user_message)
        )
        
        log.info("request_started")
        
        try:
            result = await super().chat(user_message, **kwargs)
            
            log.info(
                "request_completed",
                duration_ms=int((time.time() - start) * 1000),
                response_length=len(result),
                iterations=iteration_count
            )
            return result
            
        except TimeoutError as e:
            log.warning(
                "request_timeout",
                duration_ms=int((time.time() - start) * 1000)
            )
            raise
            
        except Exception as e:
            log.error(
                "request_failed",
                error_type=type(e).__name__,
                error_message=str(e)[:200],
                duration_ms=int((time.time() - start) * 1000)
            )
            raise
```

---

## 最终压测

用 `locust` 做压力测试：

```python
# locustfile.py
from locust import HttpUser, task, between

class CodeInterpreterUser(HttpUser):
    wait_time = between(2, 5)  # 每个用户请求间隔 2-5 秒
    
    @task(3)
    def simple_calculation(self):
        self.client.post("/chat", json={
            "message": "计算 1 到 100 的和",
            "session_id": self.user_id
        })
    
    @task(1)
    def data_analysis(self):
        self.client.post("/chat", json={
            "message": "生成 100 个随机数，计算统计指标",
            "session_id": self.user_id
        })
```

```bash
locust --headless -u 50 -r 5 --run-time 60s
```

**目标指标**：
- P95 延迟 < 10 秒（包含 LLM 推理时间）
- 错误率 < 1%
- 支持 50 并发用户

---

## Series 5 总结，也是全系列的终点

你已经走过了一段完整的旅程：

**Series 1**：理解了什么是 Code Interpreter，它解决了什么问题。  
**Series 2**：深入了沙箱安全的技术细节，从 exec 的威险到 Firecracker 的硬件隔离。  
**Series 3**：揭开了 LLM 与代码执行协同的机制，Function Calling、ReAct、自修复。  
**Series 4**：学习了工业级工程实践，平台选型、冷启动、多租户、可观测性。  
**Series 5**：从零实现了一个完整的 Code Interpreter，从 50 行原型到生产级服务。

最后送你一句话：

> **理解了 Code Interpreter，你理解的不只是一个工具。你理解的是 AI Agent 的核心运行机制——那个让 AI 从"说说而已"变成"真正能做事"的关键转变。**

这个转变，正在重塑整个软件工程行业。

---

*完结。全系列 22 篇文章已完成。欢迎反馈，持续修订。*
