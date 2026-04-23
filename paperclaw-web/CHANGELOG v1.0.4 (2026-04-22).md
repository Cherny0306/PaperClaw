# PaperClaw Web UI 更新日志

## v1.0.4 (2026-04-22)

### 新功能

- **模型选择下拉菜单**：为每个 LLM 厂商添加了不同型号模型的选择功能
  - 智谱 AI (GLM)：GLM-4-Plus、GLM-4-Flash、GLM-4-Air、GLM-4-0520
  - DeepSeek：DeepSeek-V3、DeepSeek-Coder
  - OpenAI：GPT-4o、GPT-4o Mini、GPT-4 Turbo、GPT-3.5 Turbo
  - Anthropic Claude：Claude 3.5 Sonnet、Claude 3.5 Haiku、Claude 3 Opus
  - 以及其他厂商的多种模型选择

- **运行记录统计信息展示**：在 Recent Runs 中添加可展开的统计详情
  - 点击"查看详情"展开统计面板
  - 显示 API 调用次数、Token 消耗量、预估成本、使用模型
  - 自动从后端获取并缓存统计数据

- **断点续传功能**：失败的运行记录可以继续执行
  - 对于失败且未完成的运行显示"▶ 继续运行"按钮
  - 点击后从断点位置自动恢复执行
  - 保持原有的运行目录和已完成的阶段输出

- **可拖拽模型统计面板**：添加实时显示模型使用情况的悬浮面板
  - 显示当前模型、API 调用次数、上下文长度
  - 显示 Token 消耗（输入/输出/总计）和预估成本
  - 显示已调用的工具列表
  - 可拖拽移动位置，支持收起/展开

### 后端改动

- **新增 API**：`POST /api/runs/<run_id>/resume`
  - 从断点继续运行指定的研究任务
  - 读取 checkpoint.json 确定断点位置
  - 保持原有运行目录和已完成的阶段

- **改进 API**：`GET /api/stats/<run_id>`
  - 从运行目录读取统计信息
  - 返回 API 调用次数、Token 消耗、预估成本等

- **配置同步**：前端选择的模型和厂商同步写入主配置文件
  - 后端接收并使用用户选择的模型
  - 支持厂商切换时自动选择该厂商的推荐模型

### 文件变更

**前端**
- `src/App.tsx` - 添加 handleResumeRun 函数，传递 onResumeRun 回调
- `src/components/Dashboard.tsx` - 添加统计详情展示、继续运行按钮、展开/收起功能
- `src/components/Dashboard.css` - 添加统计面板样式、操作按钮样式
- `src/components/StatsPanel.tsx` - 新增可拖拽的统计面板组件
- `src/components/StatsPanel.css` - 新增统计面板样式
- `src/components/RunControl.tsx` - 添加模型选择下拉菜单，每个厂商配置可用模型列表

**后端**
- `backend/app.py` - 添加 resume_run API、改进 stats API、支持模型参数传递

### 技术改进

- 使用 `PYTHONUNBUFFERED=1` 和 `-u` 标志确保 Python 输出实时捕获
- 改进日志解析，支持正确显示阶段进度信息
- 添加运行状态持久化，支持断点续传

---
