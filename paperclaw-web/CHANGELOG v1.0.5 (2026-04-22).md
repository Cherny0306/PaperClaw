# PaperClaw Web UI 更新日志

## v1.0.5 (2026-04-22)

### 核心改进：刷新页面后历史任务恢复

**问题修复**：
- ✅ 刷新页面后可以正确加载历史运行记录
- ✅ 后端重启后自动从 artifacts 目录扫描所有历史运行
- ✅ 继续运行功能现在可以正确识别可恢复的任务
- ✅ 状态判断逻辑优化，支持更多恢复场景

### 后端改动

**新增 API**：
- `GET /api/runs` - 获取所有历史运行记录（从 artifacts 目录扫描）
  - 扫描所有 `pc-*` 目录
  - 从 `checkpoint.json` 读取实际完成阶段
  - 智能判断运行状态（running/completed/failed）
  - 返回最多 100 个历史运行

**改进 API**：
- `GET /api/status` - 现在会自动扫描 artifacts 目录
  - 不再依赖内存中的 `recent_runs`
  - 后端重启后也能正确返回历史记录
  - 自动合并当前运行状态

**改进功能**：
- `POST /api/runs/<run_id>/resume` - 断点续传优化
  - 从 `pipeline_summary.json` 读取原始主题
  - 改进错误处理和日志输出
  - 更准确的断点位置判断

### 前端改动

**App.tsx**：
- 移除对 localStorage 的主要依赖
- 刷新页面时调用 `/api/runs` 加载完整历史
- 保留 localStorage 作为离线降级方案
- 轮询间隔从 1 秒调整为 2 秒，减少服务器压力

**Dashboard.tsx**：
- 改进继续运行按钮的判断逻辑：
  ```typescript
  // 旧逻辑：只有 failed 且未完成才显示
  canResume = status === 'failed' && current_stage < total_stages

  // 新逻辑：非运行状态 + 有已完成的阶段
  canResume = status !== 'running' &&
              (status === 'failed' || current_stage < total_stages) &&
              current_stage > 0
  ```
- 添加"启动中..."加载状态
- 添加"运行中..."状态徽章
- 改进按钮提示文本

**Dashboard.css**：
- 新增 `.running-badge` 样式（脉冲动画）
- 新增 `.resume-btn:disabled` 样式
- 新增 `@keyframes pulse` 动画

### 数据流架构

```
刷新页面后的数据流：
┌─────────┐      ┌──────────┐      ┌─────────────┐
│ Browser │ ───► │ /api/runs│ ───► │ artifacts/  │
└─────────┘      └──────────┘      └─────────────┘
                      │                     │
                      ▼                     ▼
              ┌──────────────┐    ┌────────────────┐
              │ 扫描所有 pc-* │    │ checkpoint.json│
              │ 目录          │    │ heartbeat.json │
              └──────────────┘    │ summary.json   │
                      │            └────────────────┘
                      ▼
              ┌──────────────┐
              │ 返回完整列表  │
              └──────────────┘
                      │
                      ▼
              ┌──────────────┐
              │ 前端显示     │
              │ - 状态徽章   │
              │ - 继续按钮   │
              │ - 统计信息   │
              └──────────────┘
```

### 状态判断逻辑

| checkpoint.last_completed_stage | 实际状态 | 是否可继续 |
|-------------------------------|---------|-----------|
| 0                             | 未开始  | ❌        |
| 1-22                          | 已完成N阶段 | ✅    |
| 23                            | 已完成  | ✅（全完成）|
| running（在 current_run 中）  | 运行中  | ❌（已在运行）|

### 使用场景

**场景 1：刷新页面**
```
用户刷新页面
  ↓
前端调用 /api/runs
  ↓
后端扫描 artifacts/ 目录
  ↓
返回所有历史运行（包括之前被遗忘的）
  ↓
前端正确显示所有运行状态
```

**场景 2：后端重启后继续任务**
```
后端重启（内存状态丢失）
  ↓
用户打开前端页面
  ↓
调用 /api/runs 获取历史
  ↓
点击"继续运行"按钮
  ↓
后端从 checkpoint 读取断点
  ↓
从下一阶段继续执行
```

**场景 3：中断后恢复**
```
运行在阶段 5 中断
  ↓
checkpoint 记录：last_completed_stage = 4
  ↓
用户点击"继续运行"
  ↓
从阶段 5 (LITERATURE_SCREEN) 继续执行
  ↓
保留已完成阶段 1-4 的输出
```

### 文件变更

**后端**：
- `backend/app.py`
  - 新增 `STAGE_NUM_TO_NAME` 映射
  - 新增 `scan_artifacts_for_runs()` 函数
  - 改进 `get_status()` API
  - 新增 `get_all_runs()` API
  - 改进 `resume_run()` API

**前端**：
- `src/App.tsx` - 改进初始化和轮询逻辑
- `src/components/Dashboard.tsx` - 改进继续运行判断
- `src/components/Dashboard.css` - 新增样式

### 技术细节

**扫描 artifacts 目录的算法**：
1. 遍历 `artifacts/` 目录下所有 `pc-*` 子目录
2. 读取每个目录的 `checkpoint.json` 获取 `last_completed_stage`
3. 根据 `last_completed_stage` 判断状态：
   - 23 → completed
   - 1-22 → failed（可继续）
   - 0 → not started
4. 检查 `current_run` 是否包含此 run_id → running
5. 从 `pipeline_summary.json` 读取 topic
6. 按 `last_modified` 时间倒序排列

**断点续传的工作流程**：
1. 读取 `checkpoint.json` 获取 `last_completed_name`
2. 阶段名称映射到下一阶段（如 PAPER_OUTLINE → PAPER_DRAFT）
3. 复制已完成的阶段目录到新运行（如果需要）
4. 从指定阶段启动，跳过已完成的阶段

### 测试建议

**测试步骤**：
1. 启动后端和前端
2. 创建一个新运行，让它运行到某个阶段后手动停止
3. 刷新浏览器页面
4. 验证历史记录是否正确显示
5. 点击"继续运行"按钮
6. 验证是否从正确的阶段继续执行

**验证要点**：
- ✅ 刷新后历史记录完整
- ✅ 状态徽章正确显示（running/completed/failed）
- ✅ 继续按钮在合适的时机显示
- ✅ 继续运行后阶段正确衔接
- ✅ 已完成的阶段输出被保留

---

**已知限制**：
- 后端重启后，正在运行的任务会显示为 failed，需要手动继续
- 如果 checkpoint.json 文件损坏，该运行无法继续
- 最多返回 100 个历史运行（可在 `get_all_runs()` 中调整）

**下一步计划**：
- [ ] 添加运行记录搜索功能
- [ ] 添加运行记录分页
- [ ] 支持批量删除历史记录
- [ ] 添加运行记录导出功能
