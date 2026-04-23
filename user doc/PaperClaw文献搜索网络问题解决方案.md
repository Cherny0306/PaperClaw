# PaperClaw 文献搜索网络问题解决方案

> 本文档介绍 PaperClaw 在文献搜索阶段遇到的网络限流问题及本地解决方案。

---

## 一、问题描述

### 1.1 错误日志

```
Stage 04: LITERATURE_COLLECT failed

arXiv HTTP error: Page request resulted in HTTP 429
S2 rate-limited (429). Waiting 2.4s (attempt 1/3)...
S2 circuit breaker TRIPPED after 3 consecutive 429s. Cooldown: 120s
arXiv circuit breaker TRIPPED (trip #1, cooldown 180s)
S2 circuit breaker OPEN (probe failed)

DuckDuckGo search failed: <urlopen error timed out>
```

### 1.2 问题原因

| 服务 | 问题类型 | 原因 |
|------|----------|------|
| **arXiv** | HTTP 429 | 请求频率超过 API 限制 |
| **Semantic Scholar** | 429 + 熔断 | 短时间内请求过多 |
| **DuckDuckGo** | 超时 | 无网络访问或 DNS 问题 |

---

## 二、网络需求分析

### 2.1 组件依赖

| 组件/阶段 | 是否需要科学上网 | 说明 |
|-----------|-----------------|------|
| **LLM API** | | |
| DeepSeek | 不需要 | 国内可用 |
| 智谱AI (GLM) | 不需要 | 国内可用 |
| 通义千问 (Qwen) | 不需要 | 国内可用 |
| OpenAI / Claude | 需要 | 国际 API |
| OpenRouter / Novita | 需要 | 国际 API |
| **文献搜索** | | |
| arXiv | 需要 | 国际数据库，频繁请求会限流 |
| Semantic Scholar | 需要 | 国际数据库，API 限制 |
| Google Scholar | 需要 | 国际服务，完全禁止爬虫 |
| **其他** | | |
| GitHub | 建议开启 | 代码搜索 |
| Docker Hub | 建议开启 | 拉取镜像 |
| HuggingFace | 建议开启 | 模型下载 |

### 2.2 限流机制

- **arXiv**: 每 3 秒最多 1 次请求，超出返回 429
- **Semantic Scholar**: 每分钟约 1000 次请求限制
- **DuckDuckGo**: 无代理容易超时

---

## 三、解决方案

### 方案 1：配置代理（推荐）

在 `config.paperclaw.yaml` 中添加代理配置：

```yaml
research:
  proxy_url: "http://127.0.0.1:7890"  # 修改为你的代理端口
```

**常见代理端口：**
- Clash: 7890
- V2Ray: 10809
- Shadowsocks: 1080

### 方案 2：使用国内模型（推荐）

配置使用国内 LLM 提供商，无需科学上网：

```yaml
llm:
  provider: "zhipu"           # 智谱AI
  primary_model: "glm-4"
  base_url: "https://open.bigmodel.cn/api/paas/v4"
  api_key: "your-api-key"
```

**可选国内模型：**

| 提供商 | Provider | 模型 | Base URL |
|--------|----------|------|----------|
| 智谱AI | zhipu | glm-4 | https://open.bigmodel.cn/api/paas/v4 |
| DeepSeek | deepseek | deepseek-chat | https://api.deepseek.com/v1 |
| 通义千问 | qwen | qwen-plus | https://dashscope.aliyuncs.com/compatible-mode/v1 |
| 文心一言 | ernie | ernie-4.0-8k | https://qianfan.baidubce.com/v2 |
| 混元 | hunyuan | hunyuan-pro | https://hunyuan.cloud.tencent.com/v2 |

### 方案 3：准备本地文献库（离线模式）

将文献提前下载到本地，PaperClaw 会优先使用本地文献。

#### 3.1 目录结构

```
docs/kb/
├── references/              # BibTeX 文献文件
│   ├── collected.bib       # 系统收集的文献 (138篇)
│   ├── pdf_library.bib    # Web of Science 下载的文献 (25篇)
│   └── custom.bib         # 手动添加的示例文献 (~20篇)
├── pdfs/                   # PDF 全文
│   ├── paper1.pdf
│   ├── paper2.pdf
│   └── ... (共25篇)
└── ...
```

#### 3.2 添加文献方法

**方法 A：从 Web of Science 下载**

1. 在 Web of Science 搜索相关关键词
2. 导出 BibTeX 格式
3. 放入 `docs/kb/references/` 目录

**方法 B：从 arXiv 手动下载**

1. 访问 https://arxiv.org
2. 搜索论文，点击 **Cite** → **BibTeX**
3. 保存到 `docs/kb/references/custom.bib`

**方法 C：复制已收集的文献**

将之前运行收集的文献复制到本地：

```bash
# 从 artifacts 目录复制
copy "artifacts\pc-xxxxx-xx\stage-04\references.bib" "docs\kb\references\collected.bib"
```

#### 3.3 当前本地文献库状态

| 文件 | 来源 | 数量 |
|------|------|------|
| collected.bib | 系统运行收集 | 138篇 |
| pdf_library.bib | Web of Science | 25篇 |
| custom.bib | 手动添加示例 | ~20篇 |
| **总计** | | **约 183 篇** |

### 方案 4：跳过文献搜索阶段

如果网络完全不通，可以直接从 Stage 6 开始：

```bash
paperclaw run --topic "你的研究主题" --from-stage 6
```

**阶段说明：**
- Stage 1-5: 文献研究（需要网络）
- Stage 6+: 知识提取、假设生成（主要依赖 LLM）

### 方案 5：减少搜索频率

修改配置文件降低请求频率：

```yaml
research:
  daily_paper_count: 5      # 减少搜索数量
  max_retries: 5            # 增加重试次数
  rate_limit_wait_sec: 5    # 增加等待时间
```

---

## 四、配置示例

### 4.1 国内模式配置（无需科学上网）

```yaml
llm:
  provider: "zhipu"
  base_url: "https://open.bigmodel.cn/api/paas/v4"
  api_key: "your-glm-api-key"
  primary_model: "glm-4"

research:
  domains:
    - machine-learning
  daily_paper_count: 3

knowledge_base:
  backend: "markdown"
  root: "docs/kb"
```

### 4.2 国际模式配置（需要代理）

```yaml
llm:
  provider: "openai"
  base_url: "https://api.openai.com/v1"
  api_key: "your-openai-api-key"
  primary_model: "gpt-4o"

research:
  proxy_url: "http://127.0.0.1:7890"
  domains:
    - machine-learning
    - computer-vision
  daily_paper_count: 10

knowledge_base:
  backend: "markdown"
  root: "docs/kb"
```

---

## 五、快速开始指南

### 5.1 推荐配置

1. **使用国内 LLM**（智谱AI/DeepSeek/通义千问）
2. **准备本地文献库**（已准备 183 篇）
3. **配置代理**（可选，用于 arXiv/Semantic Scholar）

### 5.2 运行命令

**方式 A：使用 Web UI（推荐）**

```bash
# 启动后端
cd paperclaw-web/backend
python app.py

# 启动前端（新窗口）
cd paperclaw-web/frontend
npm run dev
```

然后在浏览器打开 http://localhost:5173

**方式 B：命令行**

```bash
# 使用本地文献库
paperclaw run --config config.paperclaw.yaml --topic "你的研究主题"

# 跳过文献搜索
paperclaw run --config config.paperclaw.yaml --topic "你的研究主题" --from-stage 6
```

---

## 六、常见问题

### Q1: arXiv 返回 429 错误？

**A:** 这是正常的限流保护。解决方案：
1. 配置代理
2. 减少搜索频率
3. 使用本地文献库

### Q2: DuckDuckGo 超时？

**A:** 网络连接问题。解决方案：
1. 配置代理
2. 使用国内搜索引擎替代

### Q3: Semantic Scholar 熔断？

**A:** 请求过于频繁。PaperClaw 内置熔断器会自动等待恢复。

### Q4: 如何判断是否需要科学上网？

**A:** 如果使用国内 LLM 模型（如智谱AI、DeepSeek），只需要：
- 文献搜索时科学上网
- 下载 Docker 镜像时科学上网

实验代码执行阶段完全离线运行。

---

## 七、更新日志

| 日期 | 内容 |
|------|------|
| 2026-04-22 | 初始创建文档，记录 arXiv/S2/DuckDuckGo 限流问题及解决方案 |

---

*文档生成时间：2026-04-22*
