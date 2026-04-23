# PaperClaw Docker 使用说明

## 概述

PaperClaw 采用本地 + Docker 混合执行模式。当配置 `experiment.mode: docker` 时，系统会在实验执行阶段自动启动 Docker 容器，在隔离环境中运行实验代码。

## 执行模式

| 模式 | 说明 | 使用场景 |
|------|------|----------|
| `sandbox` | 本地沙盒执行 | 开发调试、快速测试 |
| `docker` | **Docker 容器执行** | 生产环境、GPU 实验、依赖隔离 |
| `ssh_remote` | SSH 远程服务器执行 | GPU 集群、高性能计算 |
| `simulated` | 模拟模式 | 仅开发调试 |

---

## Docker 自动启动时机

PaperClaw 的 23 阶段流水线中，只有特定阶段会启动 Docker 容器：

```
Phase A-I (阶段 1-8):  文献研究    → 本地运行
Phase J-K (阶段 9-10): 实验设计    → 本地运行
──────────────────────────────────────────
Phase L-M (阶段 11-12): 实验执行    → Docker 容器运行 ← 自动启动
──────────────────────────────────────────
Phase N-R (阶段 13-20): 分析写作    → 本地运行
Phase S-U (阶段 21-23): 最终化    → 本地运行
```

**Docker 仅在阶段 11-12（资源规划 + 实验执行）自动启动。**

---

## 配置项详解

### 基础配置

```yaml
experiment:
  mode: docker                    # 启用 Docker 模式
  time_budget_sec: 300           # 实验超时时间（秒）
  max_iterations: 10             # 最大迭代次数
```

### Docker 详细配置

```yaml
experiment:
  docker:
    image: "paperclaw/sandbox:latest"  # Docker 镜像
    gpu_enabled: false                 # 是否启用 GPU 穿透
    memory_limit_mb: 8192             # 内存限制 (MB)
    shm_size_mb: 2048                  # 共享内存大小 (MB)
    network_policy: "setup_only"      # 网络策略
    auto_install_deps: true           # 自动安装依赖
    keep_containers: false             # 完成后删除容器
```

### 网络策略

| 策略 | 含义 | 使用场景 |
|------|------|----------|
| `none` | 完全断网 | 高安全要求环境 |
| `setup_only` | Phase 0-1 可联网 | 下载数据集后本地执行 |
| `pip_only` | 仅 Phase 0 可联网 | 仅需安装包 |
| `full` | 全程网络可用 | 需要在线下载数据 |

---

## Docker 镜像体系

PaperClaw 提供针对不同领域的专用镜像：

| 镜像 | 用途 | 大小 |
|------|------|------|
| `paperclaw/sandbox:latest` | 通用 ML/通用场景 | ~1.2GB |
| `paperclaw/sandbox:math` | 数学优化 | ~1GB |
| `paperclaw/sandbox:physics` | 物理模拟 | ~1.5GB |
| `paperclaw/sandbox:biology` | 生物信息 | ~1.3GB |
| `paperclaw/sandbox:chemistry` | 化学分子 | ~1.4GB |
| `researchclaw/sandbox-generic:latest` | 通用场景（研究版） | ~2.3GB |

### 预装包

Docker 镜像已预装大量常用 ML/科研包，**无需在 requirements.txt 中声明**：

```python
# PyTorch 生态
torch, torchvision, torchaudio, torchdiffeq

# 科学计算
numpy, scipy, sklearn, pandas, matplotlib, seaborn

# ML 框架
transformers, datasets, accelerate, peft, trl, timm

# 其他
gymnasium, networkx, tqdm, h5py, tensorboard, wandb, optuna
```

---

## 三阶段执行模型

PaperClaw 在 Docker 容器中按三阶段执行实验代码：

| 阶段 | 执行内容 | 触发条件 |
|------|----------|----------|
| **Phase 0** | `pip install -r requirements.txt` | 工作目录存在 `requirements.txt` |
| **Phase 1** | `python setup.py` | 工作目录存在 `setup.py`（用于下载数据集） |
| **Phase 2** | `python main.py` | 主实验脚本执行 |

---

## 工作流程

```
1. 用户启动 PaperClaw 研究任务
        │
        ▼
2. LLM 生成 Python 代码（实验代码）
        │
        ▼
3. 到达实验执行阶段 (Phase 11-12)
        │
        ▼
4. DockerSandbox.run() 被调用
        │
        ▼
5. 创建临时目录 _docker_run_N/
   - 写入 main.py
   - 注入 experiment_harness.py（指标收集）
        │
        ▼
6. docker run 执行 entrypoint.sh
        ├── Phase 0: pip install（如需要）
        ├── Phase 1: setup.py（如需要）
        └── Phase 2: main.py
        │
        ▼
7. 收集 stdout/stderr 和 metrics
        │
        ▼
8. 返回 SandboxResult 给 Pipeline
```

---

## GPU 支持

如果你的机器有 NVIDIA GPU 并安装了 NVIDIA Container Toolkit：

```yaml
experiment:
  docker:
    gpu_enabled: true  # 启用 GPU 穿透
```

PaperClaw 会自动检测并添加 `--gpus all` 参数到 `docker run` 命令。

---

## 查看 Docker 状态

### 查看运行中的容器

```bash
docker ps
```

### 查看所有容器（包括已停止）

```bash
docker ps -a
```

**示例输出：**
```
CONTAINER ID   IMAGE                                                                  COMMAND                  CREATED       STATUS                      PORTS     NAMES
95fa72702af8   registry.cn-guangzhou.aliyuncs.com/prompt-optimizer/prompt-optimizer   "/docker-entrypoint..."   7 weeks ago   Exited (137) 17 hours ago             prompt-optimizer
90e3d588a156   ghcr.io/f/prompts.chat                                                 "sleep infinity"         7 weeks ago   Exited (137) 7 weeks ago              prompts3
18aa7eb237d5   ghcr.io/f/prompts.chat                                                 "tail -f nul"            7 weeks ago   Exited (1) 7 weeks ago                prompts2
37df8e8bd602   ghcr.io/f/prompts.chat                                                 "/bootstrap.sh"          7 weeks ago   Exited (2) 7 weeks ago                prompts
```

### 查看 PaperClaw 专用镜像

```bash
docker images | grep paperclaw
```

**示例输出：**
```
paperclaw/sandbox:latest    bfd3c8979a7f    1.18GB    282MB
```

### 查看容器日志

```bash
# 查看最新日志
docker logs <container_id>

# 实时跟踪日志
docker logs -f <container_id>
```

---

## 资源限制

默认资源限制（可在配置中修改）：

| 资源 | 默认值 |
|------|--------|
| 内存 | 8GB (`--memory=8192m`) |
| 共享内存 | 2GB (`--shm-size=2048m`) |

---

## 常见问题

### Q1: Docker 容器启动失败？

**A:** 检查 Docker Desktop 是否正在运行：
```bash
docker ps
```
如果报错 `error during connect`，需要启动 Docker Desktop。

### Q2: GPU 不可用？

**A:** 确保安装了 NVIDIA Container Toolkit：
```bash
docker run --gpus all nvidia/cuda:11.8-base nvidia-smi
```

### Q3: 容器内存不足？

**A:** 在配置中增加内存限制：
```yaml
experiment:
  docker:
    memory_limit_mb: 16384  # 增加到 16GB
```

### Q4: 网络访问被阻止？

**A:** 根据需要调整网络策略：
```yaml
experiment:
  docker:
    network_policy: "full"  # 全程网络可用
```

### Q5: 如何查看当前使用的镜像？

**A:** 检查配置文件或运行：
```bash
docker images | grep sandbox
```

---

## 快速参考

### 启动 PaperClaw（Docker 模式）

```bash
paperclaw run --config config.paperclaw.yaml --topic "你的研究主题"
```

### 查看容器状态

```bash
docker ps -a --format "table {{.ID}}\t{{.Image}}\t{{.Status}}"
```

### 清理已停止的容器

```bash
docker container prune -f
```

### 手动拉取最新镜像

```bash
docker pull paperclaw/sandbox:latest
```

---

## 配置文件示例

完整 Docker 配置示例：

```yaml
experiment:
  mode: docker
  time_budget_sec: 600
  max_iterations: 5

  docker:
    image: "paperclaw/sandbox:latest"
    gpu_enabled: true
    memory_limit_mb: 16384
    shm_size_mb: 4096
    network_policy: "setup_only"
    auto_install_deps: true
    keep_containers: false
```

---

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    PaperClaw Pipeline                        │
│                                                             │
│  LLM (DeepSeek/OpenAI/GLM)                                  │
│       │                                                     │
│       ▼                                                     │
│  生成代码 ──────────────────────────────────────────────┐  │
│                                                      │     │
└──────────────────────────────────────────────────────┼─────┘
                                                       │
                               ┌────────────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │   Docker Sandbox    │
                    │                     │
                    │  ┌───────────────┐  │
                    │  │  Container    │  │
                    │  │               │  │
                    │  │  Phase 0: pip │  │
                    │  │  Phase 1: setup│ │
                    │  │  Phase 2: run  │  │
                    │  │               │  │
                    │  └───────────────┘  │
                    └─────────────────────┘
```

---

*最后更新：2026-04-22*
