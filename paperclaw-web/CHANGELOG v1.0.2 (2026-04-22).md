# PaperClaw Web UI 更新日志

## v1.0.2 (2026-04-22)

### 新功能

- **跳过起始阶段选择器**：新增下拉菜单，可选择从哪个阶段开始运行
  - Stage 1: 从头开始 (包含文献搜索)
  - Stage 4: 跳过搜索 (使用本地文献库)
  - Stage 6: 跳过全部文献研究
  - Stage 9: 仅保留实验设计

### Bug 修复

- **网络限流问题**：添加阶段跳过功能，解决 arXiv/Semantic Scholar 限流问题
  - 前端：新增 Stage 选择器 (`RunControl.tsx`)
  - 后端：传递 `--from-stage` 参数 (`app.py`)

---

## v1.0.1 (2026-04-22)

### 新功能

- **阶段详情弹窗**：点击任意阶段卡片可查看该阶段的详细日志和描述
- **阶段描述说明**：为每个阶段添加中文描述说明
- **运行记录持久化**：使用 localStorage 保存运行记录，刷新页面后仍可查看历史记录
- **日志 API**：新增 `/api/logs/<run_id>/<stage_num>` 接口获取指定阶段日志

### UI 改进

- **浅色主题**：全面更新为浅色主题，提高可读性和视觉舒适度
  - 背景色：`#f8fafc`（浅灰蓝）
  - 卡片背景：`#ffffff`（白色）
  - 文字颜色：`#334155`（深灰）
  - 主色调：紫色渐变 `#6366f1` → `#8b5cf6`

### 样式优化

- 统一所有组件的颜色变量
- 优化卡片悬停效果
- 调整进度条样式
- 优化输入框和按钮交互效果

### Bug 修复

- **Docker 沙盒修复**：`researchclaw/experiment/docker_sandbox.py` 修复 Windows 系统兼容性问题
  - 添加 `platform` 模块检测
  - 新增 `_get_user_ids()` 跨平台函数
  - Windows 下使用默认容器用户 ID (1000)

---

## v1.0.0 (初始版本)

- Web UI 基础框架搭建
- React 前端 + Flask 后端架构
- 支持 11 种 LLM Provider
- 23 阶段流水线进度展示
- Dashboard 和 Results 双视图切换
