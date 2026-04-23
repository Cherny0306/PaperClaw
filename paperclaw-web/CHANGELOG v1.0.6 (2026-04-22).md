# PaperClaw Web UI 更新日志

## v1.0.6 (2026-04-22)

### 核心改进：删除任务时同步清理后端缓存

**问题修复**：
- ✅ 删除任务时检查是否正在运行，防止误删除
- ✅ 删除成功后清理后端 `current_run` 和 `recent_runs` 缓存
- ✅ 删除成功后清理前端 `localStorage` 缓存
- ✅ 添加删除确认对话框，防止误操作
- ✅ 改进错误提示，区分不同失败原因

### 后端改动

**改进 API**：
- `DELETE /api/runs/<run_id>` - 删除运行任务
  - ✅ 检查任务是否正在运行，正在运行则拒绝删除
  - ✅ 删除 artifacts 目录
  - ✅ 清理 `recent_runs` 内存缓存
  - ✅ 清理 `current_run`（如果是当前运行）
  - ✅ 添加详细日志输出

**新增 API**：
- `POST /api/runs/<run_id>/stop` - 停止正在运行的任务
  - 标记任务为停止状态
  - 清空 `current_run`
  - 返回停止的运行信息

### 前端改动

**App.tsx**：
- `handleDeleteRun` 函数改进：
  - 检查后端响应状态
  - 处理 `is_running` 错误情况
  - 删除成功后清理 `currentRun` 状态
  - 删除成功后清理 `localStorage`
  - 添加成功/失败提示

**Dashboard.tsx**：
- `handleDelete` 函数改进：
  - 添加确认对话框
  - 显示将被删除的内容说明
  - 异步等待删除完成

### 删除流程

```
用户点击删除按钮
    ↓
显示确认对话框
    ↓
用户确认
    ↓
调用 DELETE /api/runs/<run_id>
    ↓
后端检查：
  ├─ 正在运行？ → 返回错误 → 提示用户
  └─ 未运行     → 继续
    ↓
删除 artifacts 目录
    ↓
清理后端缓存：
  ├─ recent_runs 内存
  └─ current_run（如果匹配）
    ↓
清理前端缓存：
  ├─ runs 状态
  ├─ currentRun 状态
  └─ localStorage
    ↓
显示删除成功
```

### API 响应示例

**成功删除**：
```json
{
  "success": true,
  "message": "Run pc-20260422-015539-8ed6f9 deleted successfully",
  "run_id": "pc-20260422-015539-8ed6f9"
}
```

**任务正在运行**：
```json
{
  "error": "Cannot delete running task. Please wait for it to complete or stop it first.",
  "is_running": true
}
```

**任务不存在**：
```json
{
  "error": "Run not found"
}
```

### 错误处理

| 场景 | 后端处理 | 前端提示 |
|------|---------|---------|
| 任务正在运行 | 返回 400 + is_running=true | "无法删除正在运行的任务。请等待任务完成或先停止它。" |
| artifacts 不存在 | 返回 404 | "删除失败: Run not found" |
| 后端服务异常 | 返回 500 | "删除失败，请检查后端服务是否正常运行" |
| 删除成功 | 返回 200 | (控制台日志) |

### 缓存清理详情

**后端缓存清理**：
```python
# 1. 删除 artifacts 目录
shutil.rmtree(run_dir)

# 2. 清理 recent_runs 内存
global recent_runs
recent_runs = [r for r in recent_runs if r.get('run_id') != run_id]

# 3. 清理 current_run（如果匹配）
global current_run
if current_run and current_run.get('run_id') == run_id:
    current_run = None
```

**前端缓存清理**：
```typescript
// 1. 从 runs 状态中移除
setRuns(prev => prev.filter(r => r.run_id !== runId))

// 2. 清空 currentRun（如果匹配）
if (currentRun && currentRun.run_id === runId) {
  setCurrentRun(null)
}

// 3. 清理 localStorage
const savedRuns = localStorage.getItem('paperclaw_runs')
if (savedRuns) {
  const parsedRuns = JSON.parse(savedRuns)
  const filteredRuns = parsedRuns.filter(r => r.run_id !== runId)
  localStorage.setItem('paperclaw_runs', JSON.stringify(filteredRuns))
}
```

### 安全特性

**防止误删除**：
- ✅ 二次确认对话框
- ✅ 运行中任务保护
- ✅ 明确的删除内容说明

**防止数据不一致**：
- ✅ 后端先删除文件，再清理缓存
- ✅ 前端等待后端成功后，再清理本地状态
- ✅ 所有清理操作都有日志记录

### 使用示例

**正常删除**：
```
1. 用户点击历史记录卡片的 ✕ 按钮
2. 弹出确认对话框
3. 用户点击"确定"
4. 调用后端 API 删除
5. 清理所有缓存
6. 记录从列表中消失
```

**删除运行中的任务**：
```
1. 用户点击 ✕ 按钮
2. 弹出确认对话框
3. 用户点击"确定"
4. 后端检测到任务正在运行
5. 返回错误提示
6. 前端显示：无法删除正在运行的任务
7. 记录保留在列表中
```

### 文件变更

**后端**：
- `backend/app.py`
  - 改进 `delete_run()` - 添加运行检查、清理 current_run
  - 新增 `stop_run()` API - 停止正在运行的任务

**前端**：
- `src/App.tsx` - 改进 `handleDeleteRun()` - 错误处理、缓存清理
- `src/components/Dashboard.tsx` - 添加删除确认对话框

### 测试建议

**测试步骤**：
1. 创建一个测试运行
2. 等待它完成或手动停止
3. 点击删除按钮
4. 确认对话框显示正确
5. 确认删除后检查：
   - artifacts 目录是否被删除
   - 刷新页面后记录是否消失
   - localStorage 是否被清理
6. 尝试删除正在运行的任务（应该被阻止）

**验证要点**：
- ✅ 删除确认对话框正确显示
- ✅ 删除成功后所有缓存被清理
- ✅ 刷新页面后已删除的记录不会出现
- ✅ 正在运行的任务无法被删除
- ✅ 错误提示清晰明确

### 已知限制

- 停止运行中的任务（`/api/runs/<id>/stop`）目前只是标记停止，不会真正终止后端进程
- 如果后端重启，正在运行的任务会显示为 failed，此时可以删除（但 artifacts 目录仍然存在）

### 下一步计划

- [ ] 实现真正的进程停止功能
- [ ] 添加批量删除功能
- [ ] 添加删除历史记录（软删除）
- [ ] 添加回收站功能（可恢复删除）
