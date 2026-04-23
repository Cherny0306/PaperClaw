# PaperClaw 安装配置完整流程总结

## 环境信息
- **操作系统**: Windows 11 Home China
- **Python 版本**: 3.14.2
- **Docker**: Docker Desktop 29.1.3

---

## 第一步：创建虚拟环境

**命令：**
```bash
cd y:/Trae/project/PaperClaw
python -m venv .venv
```

**结果：** ✅ 成功

---

## 第二步：安装依赖

### 2.1 首次安装失败

**命令：**
```bash
.venv\Scripts\pip.exe install -e ".[all]"
```

**错误：**
```
FileNotFoundError: Forced include not found: Y:\Trae\project\PaperClaw\paperclaw\templates\styles
```

**原因：** pyproject.toml 中引用了不存在的 `paperclaw/templates/styles` 目录

**修复：**
修改 pyproject.toml 删除不存在的路径引用：
```toml
[tool.hatch.build.targets.wheel.force-include]
"researchclaw/templates/styles" = "researchclaw/templates/styles"
```

### 2.2 基础安装成功

```bash
.venv\Scripts\pip.exe install -e .
```
✅ 成功

### 2.3 可选依赖安装（跳过 crawl4ai）

**命令：**
```bash
.venv\Scripts\pip.exe install httpx scholarly tavily-python PyMuPDF huggingface-hub matplotlib scipy
```
✅ 成功（lxml 从 wheel 安装）

---

## 第三步：修复入口点配置

**问题：** `paperclaw` 只是文件而非包，导致 `paperclaw.cli:main` 入口点无法工作

**错误：**
```
Y:\Trae\project\PaperClaw\.venv\Scripts\python.exe: No module named paperclaw
```

**修复：** 修改 pyproject.toml
```toml
[project.scripts]
paperclaw = "researchclaw.cli:main"
researchclaw = "researchclaw.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["researchclaw", "sibyl", "arc"]
```

**验证：**
```bash
paperclaw --help
```
✅ 正常显示帮助信息

---

## 第四步：配置 MiniMax API

### 4.1 首次配置错误

**API Key 类型错误：** 填入了 Token Plan Key 而非 API Key

**修复：** 使用正确的 `sk-api-xxx` 格式的 API Key

### 4.2 最终配置 config.paperclaw.yaml

```yaml
llm:
  provider: "openai-compatible"
  base_url: "https://api.minimax.chat/v1"
  api_key: "sk-api-xxxx"
  primary_model: "MiniMax-Text-01"
```

**测试：**
```bash
curl 测试 -> HTTP 200 ✅
```

### 4.3 LLM 端点 404 警告说明

`doctor` 检查报告 `llm_connectivity: HTTP 404`，但实际 API 完全正常。

**原因：** health.py 检查 `/models` 端点，但 MiniMax 使用 `/chat/completions` 端点

---

## 第五步：Docker 部署

### 5.1 默认镜像拉取失败

**命令：**
```bash
docker pull researchclaw/sandbox-generic:latest
```

**错误：**
```
403 Forbidden - unexpected status from HEAD request
```

### 5.2 切换为 mildhedgehog/researchclaw

**命令：**
```bash
docker pull mildhedgehog/researchclaw:latest
```
✅ 成功

### 5.3 构建本地镜像

**命令：**
```bash
docker build -f researchclaw/docker/Dockerfile.generic -t paperclaw/sandbox:latest researchclaw/docker/
```
✅ 成功 (1.18GB)

### 5.4 最终 Docker 配置

```yaml
experiment:
  mode: "docker"
docker:
  image: "paperclaw/sandbox:latest"
  gpu_enabled: false
  memory_limit_mb: 8192
  network_policy: "setup_only"
```

---

## 第六步：修复 MiniMax JSON 模式兼容性问题

### 问题

运行 `paperclaw run` 时报错：
```
Model MiniMax-Text-01 failed: HTTP Error 400: Bad Request
```

### 根因

MiniMax 不支持 `response_format: {"type": "json_object"}` 参数

### 修复

修改 researchclaw/llm/client.py 第352-371行：

```python
if json_mode:
    # Many OpenAI-compatible proxies serving Claude models don't
    # support the response_format parameter and return HTTP 400.
    # Also MiniMax doesn't support response_format.
    # Fall back to a system-prompt injection for these models.
    _json_hint = (
        "You MUST respond with valid JSON only. "
        "Do not include any text outside the JSON object."
    )
    # Check for models that don't support response_format
    _needs_json_hint = (
        model.startswith("claude") or
        "minimax" in model.lower() or
        "deepseek" in model.lower()
    )
    if _needs_json_hint:
        # Prepend to existing system message or add as new one
        if msgs and msgs[0]["role"] == "system":
            msgs[0]["content"] = (
                _json_hint + "\n\n" + msgs[0]["content"]
            )
        else:
            msgs.insert(
                0, {"role": "system", "content": _json_hint}
            )
    else:
        body["response_format"] = {"type": "json_object"}
```

---

## 第七步：最终运行测试

**命令：**
```bash
paperclaw run --topic "LLM applications in code generation" --skip-preflight --auto-approve
```

**结果：**
| 阶段 | 状态 |
|------|------|
| TOPIC_INIT | ✅ |
| PROBLEM_DECOMPOSE | ✅ |
| SEARCH_STRATEGY | ✅ (修复后) |
| WEB_CONTEXT | ✅ |
| LITERATURE_REVIEW | ✅ |
| SYNTHESIS | ✅ |
| HYPOTHESIS_GENERATION | ✅ |

**生成文件：**
```
artifacts/pc-20260421-085501-7a1f73/
├── stage-01/goal.md
├── stage-02/problem_tree.md
├── stage-04/web_context.md
├── stage-06/cards/*.md
├── stage-07/synthesis.md
└── stage-08/hypotheses.md
```

---

## 最终配置状态

| 项目 | 值 |
|------|-----|
| Python | 3.14.2 |
| 虚拟环境 | `.venv` |
| LLM Provider | MiniMax-Text-01 |
| API URL | `https://api.minimax.chat/v1` |
| 实验模式 | Docker |
| Docker 镜像 | `paperclaw/sandbox:latest` (本地构建) |

---

## Doctor 检查结果

```
[OK] python_version: Python 3.14.2
[OK] yaml_import: PyYAML import ok
[OK] config_valid: Config validation ok
[WARN] llm_connectivity: HTTP 404 (误报，实际正常)
[WARN] api_key_valid: HTTP 404 (误报，实际正常)
[OK] matplotlib: matplotlib import ok
[OK] experiment_mode: docker
[OK] docker_runtime: Docker OK
```

---

## 修改的文件清单

1. **pyproject.toml** - 修复 force-include 路径和入口点配置
2. **config.paperclaw.yaml** - 添加到 .gitignore 避免泄露 API Key
3. **researchclaw/llm/client.py** - 添加 MiniMax JSON 模式兼容处理
4. **researchclaw/llm/__init__.py** - 添加 provider presets
5. **INSTALLATION_SUMMARY.md** - 安装配置文档（本文档）
6. **.gitignore** - 添加 config.paperclaw.yaml 到敏感文件列表