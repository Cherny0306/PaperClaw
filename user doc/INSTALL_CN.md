# PaperClaw 安装与配置流程

## 环境要求

| 要求 | 说明 |
|------|------|
| Python | 3.11+（推荐 3.12/3.13，3.14 可能有兼容性风险） |
| Docker | Docker Desktop（用于代码沙箱隔离执行） |
| 内存 | 建议 16GB+（运行大型模型和 Docker 容器） |
| 磁盘 | 建议 20GB+ 可用空间 |
| LLM API Key | DeepSeek/OpenAI/Anthropic 等 |

---

## 第一步：检查环境

在开始安装前，先验证你的环境是否满足要求。

```bash
# 进入项目目录
cd y:\Trae\project\PaperClaw

# 检查Python版本（必须是 3.11+）
python --version
# 预期输出类似：Python 3.12.3

# 检查Docker是否安装
docker --version
# 预期输出类似：Docker version 27.5.1, build 9f0776a

# 检查Docker是否运行中（必须有输出）
docker ps
# 如果报错：error during connect... 说明Docker未启动
```

### ⚠️ 注意事项

- **Docker Desktop 必须保持运行状态**，PaperClaw 使用 Docker 作为代码执行沙箱
- 如果 `docker ps` 报错，Windows 用户请从开始菜单启动 "Docker Desktop"
- 等待 Docker 完全启动（约 1-2 分钟），确认任务栏图标不再闪烁

---

## Docker 部署原理（选读）

了解 PaperClaw 如何使用 Docker 有助于排查问题和优化使用体验。

### 架构概述

```
┌─────────────────────────────────────────────────────────────┐
│                    PaperClaw Pipeline                        │
│                                                             │
│  LLM (DeepSeek/OpenAI)                                      │
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

### 三阶段执行模型

PaperClaw 在 Docker 容器中按三阶段执行实验代码：

| 阶段 | 执行内容 | 触发条件 |
|------|----------|----------|
| **Phase 0** | `pip install -r requirements.txt` | 工作目录存在 `requirements.txt` |
| **Phase 1** | `python3 setup.py` | 工作目录存在 `setup.py`（用于下载数据集） |
| **Phase 2** | `python3 main.py` | 主实验脚本执行 |

### 网络策略

PaperClaw 支持细粒度的网络控制策略：

| 策略 | 含义 | 使用场景 |
|------|------|----------|
| `full` | 全程网络可用 | 需要在线下载数据的实验 |
| `setup_only` | Phase 0-1 可联网，Phase 2 断网 | 下载数据集后执行本地实验 |
| `pip_only` | 仅 Phase 0 可联网 | 仅需要安装包 |
| `none` | 完全断网 | 安全要求极高的执行环境 |

### 内置预装包

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

### 镜像体系

PaperClaw 针对不同领域提供了专用 Docker 镜像：

| 镜像 | 用途 |
|------|------|
| `researchclaw/sandbox-generic:latest` | 通用 ML/通用场景 |
| `researchclaw/sandbox-math:latest` | 数学优化 |
| `researchclaw/sandbox-physics:latest` | 物理模拟 |
| `researchclaw/sandbox-biology:latest` | 生物信息 |
| `researchclaw/sandbox-chemistry:latest` | 化学分子 |
| `researchclaw/sandbox-economics:latest` | 经济金融 |
| `researchclaw/sandbox-security:latest` | 安全检测 |

### 工作流程

```
1. 用户启动 PaperClaw 研究任务
        │
        ▼
2. LLM 生成 Python 代码（实验代码）
        │
        ▼
3. DockerSandbox.run() 被调用
        │
        ▼
4. 创建临时目录 _docker_run_N/
   - 写入 main.py
   - 注入 experiment_harness.py（指标收集）
        │
        ▼
5. docker run 执行 entrypoint.sh
        │
        ├── Phase 0: pip install（如需要）
        ├── Phase 1: setup.py（如需要）
        └── Phase 2: main.py
        │
        ▼
6. 收集 stdout/stderr 和 metrics
        │
        ▼
7. 返回 SandboxResult 给 Pipeline
```

### GPU 支持

如果你的机器有 NVIDIA GPU 并安装了 NVIDIA Container Toolkit：

```yaml
# config.paperclaw.yaml
experiment:
  mode: docker
  docker:
    gpu_enabled: true  # 启用 GPU 穿透
```

PaperClaw 会自动检测并添加 `--gpus all` 参数到 `docker run` 命令。

### 资源限制

默认资源限制（可在配置中修改）：

| 资源 | 默认值 |
|------|--------|
| 内存 | 8GB (`--memory=8192m`) |
| 共享内存 | 2GB (`--shm-size=2048m`) |

---

## 第二步：创建虚拟环境（重要）

为避免污染全局 Python 环境，**强烈建议使用虚拟环境**。

### 什么是虚拟环境？

虚拟环境是一个独立的 Python 运行环境，所有安装的包都只在这个环境内生效，不会影响全局 Python 和其他项目。

### 创建虚拟环境

```bash
# 使用当前默认 Python 创建虚拟环境
python -m venv .venv

# 或者指定 Python 版本（如果安装了多个 Python 版本）
py -3.12 -m venv .venv
```

### 激活虚拟环境

```bash
# Windows CMD
.venv\Scripts\activate.bat

# Windows PowerShell（可能需要先执行）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.venv\Scripts\Activate.ps1

# Linux/Mac
source .venv/bin/activate
```

### ✅ 验证激活成功

激活后，终端提示符会显示 `(.venv)` 前缀：

```
(.venv) y:\Trae\project\PaperClaw>
```

### ⚠️ 注意事项

- **每次新开终端都需要重新激活虚拟环境**
- 如果提示 "Cannot be loaded because running scripts is disabled"，在 PowerShell 中执行：
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

---

## 第三步：安装依赖

### 激活虚拟环境后执行

```bash
# 安装核心依赖（最小安装）
pip install -e .

# 安装全部依赖（含 Web、可选功能）
pip install -e ".[all]"

# 如果 [all] 安装失败，逐个安装
pip install pyyaml rich arxiv numpy
pip install httpx scholarly crawl4ai tavily-python PyMuPDF
```

### 依赖说明

| 依赖组 | 包含内容 | 用途 |
|--------|----------|------|
| 核心 | pyyaml, rich, arxiv, numpy | 基础功能 |
| anthropic | httpx | Anthropic API 支持 |
| web | scholarly, crawl4ai, tavily-python | 文献检索、网络爬虫 |
| pdf | PyMuPDF | PDF 处理 |
| all | 上述全部 | 完整功能 |

### ⚠️ 注意事项

- **安装过程可能需要几分钟**，取决于网络速度
- 如果遇到网络问题，可以换国内镜像源：
  ```bash
  pip install -e ".[all]" -i https://pypi.tuna.tsinghua.edu.cn/simple
  ```
- 某些依赖（如 PyMuPDF）需要编译工具链，Windows 用户可能需要 Visual Studio Build Tools

---

## 第四步：配置 API Key

### 复制配置文件

```bash
copy config.paperclaw.example.yaml config.paperclaw.yaml
```

### 编辑配置文件

用任意文本编辑器打开 `config.paperclaw.yaml`，修改以下内容：

```yaml
llm:
  provider: deepseek    # LLM 提供商
  api_key: "your-api-key-here"  # 替换为你的 API Key
```

### 支持的 LLM Provider

| Provider | 模型 | 说明 | 获取地址 |
|----------|------|------|----------|
| deepseek | deepseek-chat | 推荐，免费额度多 | https://platform.deepseek.com |
| openai | gpt-4o, gpt-4 | 通用强大 | https://platform.openai.com |
| anthropic | claude-3.5-sonnet | 推理能力强 | https://anthropic.com |

### ⚠️ 注意事项

- **API Key 不要泄露给他人**，也不要提交到 Git
- `config.paperclaw.yaml` 已在 `.gitignore` 中，不会被提交
- 如果使用 DeepSeek，推荐先充值 10-20 元，API 调用更稳定

---

## 第五步：验证安装

```bash
# 检查 paperclaw 命令是否可用
paperclaw --help

# 或使用 Python 模块方式
python -m paperclaw --help
```

### 预期输出

```
usage: paperclaw [-h] [--config CONFIG] [--verbose] [topic]

PaperClaw - 面向学术科研工作者的高能动性AI自动化辅助系统

positional arguments:
  topic                 研究主题

options:
  -h, --help            显示帮助信息
  --config CONFIG       配置文件路径
  --verbose             详细输出模式
```

---

## 第六步：启动 Web UI（可选）

如果不想使用命令行，可以使用 Web 界面。

### 后端服务（终端1）

```bash
cd paperclaw-web\backend
pip install -r requirements.txt
python app.py
```

### 前端服务（终端2）

```bash
# 确认虚拟环境已激活
cd paperclaw-web\frontend
npm install
npm run dev
```

### 访问界面

打开浏览器访问：**http://localhost:5173**

### ⚠️ 注意事项

- **后端必须先启动**，前端才能正常连接
- 如果端口 5173 被占用，Vite 会自动切换到其他端口，注意看终端输出
- Web UI 中的 API Key 会保存在浏览器 localStorage 中

---

## 快速命令汇总

```bash
# 完整安装流程
cd y:\Trae\project\PaperClaw

# 1. 创建虚拟环境
python -m venv .venv

# 2. 激活虚拟环境
.venv\Scripts\activate.bat

# 3. 安装依赖
pip install -e ".[all]"

# 4. 复制并编辑配置文件
copy config.paperclaw.example.yaml config.paperclaw.yaml
# 编辑 config.paperclaw.yaml，填入 API Key

# 5. 验证安装
paperclaw --help
```

---

## 常见问题

### Q1: pip install 失败，提示 "Microsoft Visual C++ 14.0 is required"？

**A:** 安装 [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/)，勾选 "C++ 桌面开发"。

---

### Q2: Docker 相关错误 "error during connect"？

**A:** 确保 Docker Desktop 已启动并运行。等待完全启动后，在终端执行 `docker ps` 确认。

---

### Q3: 提示 "command not found: paperclaw"？

**A:** 确保虚拟环境已激活（提示符前有 `(.venv)`），然后重新安装：
```bash
pip install -e .
```

---

### Q4: 虚拟环境目录 .venv 太大？

**A:** .venv 只包含你安装的包，不影响全局环境。如果需要删除，直接删除整个目录即可。

---

### Q5: API 调用很慢或失败？

**A:**
1. 检查 API Key 是否正确
2. 检查网络连接
3. DeepSeek 有每日免费额度，用完需要充值
4. 尝试切换 provider

---

## 下一步

安装配置完成后，可以开始你的第一次研究：

```bash
# 命令行方式（基础研究）
paperclaw "LLM applications in code generation"

# 命令行方式（指定配置文件）
paperclaw --config config.paperclaw.yaml "大语言模型在医学诊断中的应用"

# Web UI 方式
# 浏览器访问 http://localhost:5173
```

---

## 目录结构说明

安装后，项目目录结构：

```
PaperClaw/
├── .venv/                    # 虚拟环境（隔离的 Python 环境）
├── paperclaw-web/            # Web UI
│   ├── backend/              # 后端 API
│   └── frontend/             # 前端界面
├── researchclaw/             # 核心研究引擎
├── config.paperclaw.yaml     # 配置文件（包含 API Key）
├── INSTALL_CN.md             # 本文档
└── ...
```
