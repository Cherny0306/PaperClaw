# PaperClaw Web UI 更新日志

## v1.0.3 (2026-04-22)

### 新功能

- **运行记录删除功能**：为 Recent Runs 和 Results View 添加删除按钮
  - 删除按钮位于任务卡片右上角，红色圆形 ✕ 图标
  - 悬停在卡片上时显示删除按钮
  - 点击删除后同步清理后端 artifacts 目录（日志、阶段输出、交付物）
  - 同时更新前端 localStorage 和后端 recent_runs 列表

### 后端改动

- **新增 API**：`DELETE /api/runs/<run_id>`
  - 删除指定运行的所有文件（artifacts 目录）
  - 从内存中的 recent_runs 列表中移除

### 文件变更

**前端**
- `src/App.tsx` - 添加 `handleDeleteRun` 异步删除函数
- `src/components/Dashboard.tsx` - 添加删除按钮和回调
- `src/components/ResultsView.tsx` - 添加删除按钮和回调
- `src/components/Dashboard.css` - 添加 `.delete-btn` 样式
- `src/components/ResultsView.css` - 添加 `.delete-btn` 样式

**后端**
- `backend/app.py` - 新增 `delete_run()` API 端点

---
