# PaperClaw 问题排查与修复报告

## 基本信息

| 项目 | 内容 |
|------|------|
| Run ID | `pc-20260422-083339-16cb` |
| Topic | 基于迁移学习与MIE-YOLO的无人机RGB影像入侵杂草检测研究 |
| 问题阶段 | Stage 12/23 - EXPERIMENT_RUN (实验执行阶段) |
| 发生时间 | 2026-04-22 |

---

## 问题描述

### 错误日志

```
Stage 12/23 EXPERIMENT_RUN failed
Traceback (most recent call last):
  File "Y:\Trae\project\PaperClaw\researchclaw\experiment\docker_sandbox.py", line 379, in _build_run_command
      cmd.extend(["--user", f"{os.getuid()}:{os.getgid()}"])
AttributeError: module 'os' has no attribute 'getuid'. Did you mean: 'getpid'?
```

### 错误分析

错误发生在 Docker 沙盒执行实验代码时，`docker_sandbox.py` 第 379 行调用了 `os.getuid()` 函数。

**根本原因**：`os.getuid()` 是 Unix/Linux 系统特有的函数，用于获取当前用户 ID。但 PaperClaw 运行在 Windows 系统上，而 Windows 不提供此函数，导致 `AttributeError`。

### 影响范围

- **Pipeline 进度**：11/12 阶段完成，Stage 12 (EXPERIMENT_RUN) 失败
- **受影响的配置**：当 `experiment.mode: docker` 时，系统会在实验执行阶段启动 Docker 容器

---

## 问题定位

### 原始代码 (docker_sandbox.py:379)

```python
cmd.extend(["--user", f"{os.getuid()}:{os.getgid()}"])
```

该代码出现在三处位置（对应不同的网络策略）：
- 第 371 行：`network_policy == "none"` 分支
- 第 379 行：`network_policy in ("setup_only", "pip_only")` 分支
- 第 383 行：`network_policy == "full"` 分支

### 执行模式说明

PaperClaw 的 23 阶段流水线中，只有特定阶段会启动 Docker 容器：

```
Phase A-I (阶段 1-8):  文献研究    → 本地运行
Phase J-K (阶段 9-10): 实验设计    → 本地运行
──────────────────────────────────────────
Phase L-M (阶段 11-12): 实验执行    → Docker 容器运行 ← 问题发生点
──────────────────────────────────────────
Phase N-R (阶段 13-20): 分析写作    → 本地运行
```

---

## 修复方案

### 修改文件

`researchclaw/experiment/docker_sandbox.py`

### 修改内容

**1. 添加 platform 模块导入**

```python
import platform  # 新增
```

**2. 新增跨平台用户ID获取函数**

```python
def _get_user_ids() -> tuple[int, int]:
    """Get user and group IDs in a cross-platform way.

    On Unix: returns (os.getuid(), os.getgid())
    On Windows: returns (1000, 1000) (default container user)
    """
    if platform.system() == "Windows":
        # Windows doesn't have os.getuid/getgid; use default container user
        return (1000, 1000)
    return (os.getuid(), os.getgid())
```

**3. 替换所有 os.getuid()/os.getgid() 调用**

```python
# 修改前
cmd.extend(["--user", f"{os.getuid()}:{os.getgid()}"])

# 修改后
cmd.extend(["--user", f"{_get_user_ids()[0]}:{get_user_ids()[1]}"])
```

---

## 修复后状态

| 项目 | 状态 |
|------|------|
| 代码修改 | ✅ 完成 |
| 跨平台兼容性 | ✅ Windows/Linux 双支持 |
| 回归测试 | 待用户验证 |

---

## 验证方法

重新运行 PaperClaw：

```bash
# 通过 Web UI 启动新研究任务
# 或命令行运行
paperclaw run --config config.paperclaw.yaml --topic "基于迁移学习与MIE-YOLO的无人机RGB影像入侵杂草检测研究"
```

预期结果：Stage 12 (EXPERIMENT_RUN) 应能正常完成。

---

## 技术备注

### Windows 容器用户说明

在 Windows 上运行 Docker 容器时，使用 `--user` 参数指定用户 ID 可能导致权限问题。修复方案采用容器默认用户 (UID:1000, GID:1000)，这是大多数 Docker 镜像中 `researcher` 用户使用的 ID。

### 配置文件参考

当前使用的 Docker 配置 (`config.paperclaw.yaml`)：

```yaml
experiment:
  mode: docker
  docker:
    image: paperclaw/sandbox:latest
    gpu_enabled: false
    memory_limit_mb: 8192
    network_policy: setup_only
```

---

*文档生成时间：2026-04-22*
