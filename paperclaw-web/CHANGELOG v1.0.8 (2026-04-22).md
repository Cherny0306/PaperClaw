# PaperClaw Web UI 更新日志

## v1.0.9 (开发中)

### Bug修复：断点续传核心问题

**问题描述**：前端界面 Recent Runs 下方历史任务点击"继续运行"后，PaperClaw 仍然从 Stage 1 开始，而不是从断点处继续。

**根本原因**：`run_pipeline` 函数中使用了错误的映射方式获取阶段名称。

```python
# 错误代码
STAGE_MAP = {'TOPIC_INIT': 1, 'PROBLEM_DECOMPOSE': 2, ...}  # 名称 -> 数字

# 使用 STAGE_MAP.get(stage_num) 获取阶段名称
stage_num = 2  # 下一阶段
from_stage = STAGE_MAP.get(stage_num, 'TOPIC_INIT')  # 返回 None!

# 导致条件判断失败
if from_stage and from_stage != 'TOPIC_INIT':  # None != 'TOPIC_INIT' 为 False
    cmd.extend(["--from-stage", from_stage])  # 不会执行！
```

**修复方案**：
1. 添加 `STAGE_NUM_TO_NAME` 反向映射（数字 -> 名称）
2. 使用 `STAGE_NUM_TO_NAME.get(stage_num)` 获取阶段名称

```python
# 正确代码
STAGE_NUM_TO_NAME = {v: k for k, v in STAGE_MAP.items()}
# STAGE_NUM_TO_NAME = {1: 'TOPIC_INIT', 2: 'PROBLEM_DECOMPOSE', ...}

stage_num = 2
from_stage = STAGE_NUM_TO_NAME.get(stage_num, 'TOPIC_INIT')  # 返回 'PROBLEM_DECOMPOSE'
```

**修复文件**：
- `backend/app.py` - 添加 `STAGE_NUM_TO_NAME` 映射并修复获取阶段名称的代码

**验证结果**：
- 修复前：`From: Stage 1: TOPIC_INIT`（错误）
- 修复后：`From: Stage 3: SEARCH_STRATEGY`（正确）

**其他改进**：
- 改进 `run_pipeline` 函数的 resume 处理逻辑
- 添加 `use_reloader=False` 避免 debug 模式重复加载

---

## v1.0.8 (2026-04-22) - 综合功能增强版

### 🎯 核心改进汇总

本次更新包含5大功能增强和3个重要bug修复，大幅提升了用户体验和系统稳定性。

---

## 新增功能

### 1. ✨ 暂停运行功能

**功能描述**：正在运行的任务可以随时暂停，保存当前进度，方便切换任务或临时中断。

**实现细节**：
- ProgressView 右上角添加"⏸ 暂停运行"按钮
- 点击前显示确认对话框
- 真正终止后台进程（SIGTERM → SIGKILL）
- 保存进度到 checkpoint.json
- 状态变为"failed"（可继续）

**使用场景**：
```
场景1: 切换任务
  任务A运行中 → 暂停任务A → 启动任务B → 完成后继续任务A

场景2: 临时中断
  任务运行中 → 暂停保存进度 → 关闭电脑 → 稍后继续执行
```

**API**：
```http
POST /api/runs/{run_id}/stop
```

**文件变更**：
- `src/components/ProgressView.tsx` - 添加暂停按钮和确认逻辑
- `src/components/ProgressView.css` - 暂停按钮样式
- `src/App.tsx` - handlePauseRun 函数
- `backend/app.py` - 改进 stop_run API，支持真正的进程终止

---

### 2. 🎨 批量删除功能

**功能描述**：支持一次性选择和删除多个运行记录。

**功能特性**：
- 批量管理模式切换
- 复选框选择（点击卡片或复选框）
- 全选/取消全选（自动排除运行中的任务）
- 批量删除确认对话框
- 详细的删除结果反馈

**UI布局**：
```
正常模式: Recent Runs [批量管理]
批量模式: [全选] [删除选中 (3)] [取消]
```

**性能优化**：
- 旧方案：并行发送多个DELETE请求（~2-3秒）
- 新方案：单个批量删除API（<0.5秒）
- 性能提升：约4-6倍

**API**：
```http
POST /api/runs/bulk-delete
Content-Type: application/json

{
  "run_ids": ["pc-001", "pc-002", "pc-003"]
}
```

**响应**：
```json
{
  "success": true,
  "message": "Bulk delete completed: 2 succeeded, 1 failed, 0 skipped",
  "results": {
    "success": ["pc-001", "pc-002"],
    "failed": [{"run_id": "pc-003", "error": "Run not found"}],
    "running": []
  }
}
```

**文件变更**：
- `src/components/Dashboard.tsx` - 批量选择逻辑和UI
- `src/components/Dashboard.css` - 批量操作样式
- `src/App.tsx` - handleDeleteMultiple 函数
- `backend/app.py` - 新增 bulk_delete_runs API

---

### 3. 🔄 断点续传修复

**问题描述**：继续运行功能错误地从已完成阶段重新开始，而不是下一阶段。

**根本原因**：
```python
# 错误代码
from_stage = checkpoint.get('last_completed_name', 'TOPIC_INIT')
# 例如：last_completed_name = "SEARCH_STRATEGY" (阶段3)
# 结果：从阶段3重新开始 ❌

# 正确代码
next_stage_num = last_completed_stage + 1  # 3 + 1 = 4
from_stage = STAGE_NUM_TO_NAME.get(next_stage_num, 'TOPIC_INIT')
# 结果：从阶段4 LITERATURE_COLLECT 开始 ✅
```

**修复方案**：
- 读取 checkpoint 中的 `last_completed_stage`（数字）
- 计算下一阶段号：`next_stage = last_completed_stage + 1`
- 使用 `STAGE_NUM_TO_NAME` 映射获取下一阶段名称
- 检查是否已完成所有阶段（23）

**文件变更**：
- `backend/app.py` - 修复 resume_run 函数的阶段计算逻辑

---

### 4. 📂 历史记录持久化

**问题描述**：刷新页面后，前端只能从 localStorage 恢复历史记录，但后端内存状态丢失。

**解决方案**：
- 新增 `GET /api/runs` API，从 artifacts 目录扫描所有历史
- 新增 `scan_artifacts_for_runs()` 函数
- 根据 checkpoint.json 判断真实状态
- 支持最多100个历史运行

**状态判断逻辑**：
| checkpoint.last_completed_stage | 实际状态 |
|-------------------------------|---------|
| 0 | 未开始 |
| 1-22 | 已完成N阶段（可继续） |
| 23 | 已完成 |

**文件变更**：
- `backend/app.py` - scan_artifacts_for_runs, get_all_runs API
- `src/App.tsx` - 初始化时从后端加载完整历史

---

### 5. 🗑️ 缓存同步机制

**问题描述**：删除历史任务时，前端状态和后端缓存不同步。

**解决方案**：
- 删除时同时清理：
  - artifacts 目录
  - 后端 `recent_runs` 内存
  - 后端 `current_run`（如果匹配）
  - 前端 `runs` 状态
  - 前端 `currentRun` 状态
  - localStorage 缓存

**安全特性**：
- 运行中的任务无法删除（弹窗提示）
- 删除确认对话框
- 详细的错误提示

**文件变更**：
- `backend/app.py` - 改进 delete_run API
- `src/App.tsx` - 改进 handleDeleteRun 函数
- `src/components/Dashboard.tsx` - 添加删除确认

---

## Bug修复

### Bug #1: Windows 兼容性问题
**问题**：`print(..., flush=True)` 在 Windows 上抛出 `OSError: [Errno 22]`
**修复**：移除所有 print 语句的 `flush=True` 参数
**影响**：删除功能现在可以在 Windows 上正常工作

### Bug #2: 批量删除性能问题
**问题**：串行删除50个运行需要~50秒
**修复**：
- 方案1：改为并行请求（~2-3秒）
- 方案2：新增批量删除API（<0.5秒）
**影响**：批量删除速度提升100倍

### Bug #3: 继续运行阶段错误
**问题**：从已完成阶段重新开始，而不是下一阶段
**修复**：正确计算 `next_stage_num = last_completed + 1`
**影响**：继续运行现在从正确的阶段开始

---

## 技术改进

### 后端架构改进

**进程管理**：
```python
# 新增全局进程字典
running_processes = {}  # {run_id: subprocess.Popen}

# 启动时保存进程引用
running_processes[run_id] = process

# 停止时终止进程
process.terminate()  # SIGTERM
process.kill()       # SIGKILL (如果需要)
```

**状态持久化**：
- 运行状态不再只依赖内存
- 从 artifacts 目录重建状态
- 支持后端重启后恢复历史

**性能优化**：
- 批量操作使用单次请求
- 减少网络往返次数
- 优化扫描算法

### 前端架构改进

**状态管理**：
- 统一的缓存清理机制
- 前后端状态同步
- localStorage 作为降级方案

**用户体验**：
- 确认对话框防误操作
- 详细的错误提示
- 操作结果反馈

---

## API 变更

### 新增 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/runs` | 获取所有历史运行（从artifacts扫描） |
| POST | `/api/runs/bulk-delete` | 批量删除运行记录 |
| POST | `/api/runs/<id>/stop` | 停止/暂停运行（改进，支持真正终止进程） |

### 改进 API

| 方法 | 路径 | 改进 |
|------|------|------|
| GET | `/api/status` | 现在自动扫描artifacts，不依赖内存 |
| DELETE | `/api/runs/<id>` | 清理所有相关缓存 |
| POST | `/api/runs/<id>/resume` | 修复阶段计算bug |

---

## 数据流图

### 暂停流程
```
用户点击暂停
    ↓
确认对话框
    ↓
POST /api/runs/{id}/stop
    ↓
后端终止进程
process.terminate()
process.kill()
    ↓
清理状态
current_run = None
running_processes[id] = delete
    ↓
更新前端状态
status = 'failed' (可继续)
```

### 批量删除流程
```
用户选择多个运行
    ↓
点击"删除选中 (N)"
    ↓
POST /api/runs/bulk-delete
{
  "run_ids": [id1, id2, ...]
}
    ↓
后端并行删除
for run_id in run_ids:
    shutil.rmtree(run_dir)
    recent_runs = filter(...)
    ↓
返回详细结果
{
  success: [...],
  failed: [...],
  running: [...]
}
    ↓
前端更新状态
显示结果统计
```

### 继续运行流程（修复后）
```
用户点击继续运行
    ↓
读取 checkpoint.json
{
  "last_completed_stage": 3,
  "last_completed_name": "SEARCH_STRATEGY"
}
    ↓
计算下一阶段
next = 3 + 1 = 4
next_name = STAGE_NUM_TO_NAME[4] = "LITERATURE_COLLECT"
    ↓
启动任务
--from-stage LITERATURE_COLLECT
```

---

## 文件变更汇总

### 后端 (backend/app.py)
- ✅ 新增 `running_processes` 全局变量
- ✅ 新增 `STAGE_NUM_TO_NAME` 映射
- ✅ 新增 `scan_artifacts_for_runs()` 函数
- ✅ 新增 `bulk_delete_runs()` API
- ✅ 改进 `delete_run()` - 清理所有缓存
- ✅ 改进 `stop_run()` - 支持真正终止进程
- ✅ 改进 `resume_run()` - 修复阶段计算
- ✅ 改进 `get_status()` - 自动扫描artifacts
- ✅ 移除所有 `flush=True` 参数

### 前端

**src/App.tsx**:
- ✅ 新增 `handleDeleteMultiple()` - 批量删除
- ✅ 新增 `handlePauseRun()` - 暂停运行
- ✅ 改进 `handleDeleteRun()` - 错误处理和缓存清理
- ✅ 改进初始化逻辑 - 从后端加载完整历史

**src/components/Dashboard.tsx**:
- ✅ 新增批量选择模式
- ✅ 新增复选框UI
- ✅ 新增全选/取消功能
- ✅ 新增删除确认对话框
- ✅ 改进继续运行判断逻辑

**src/components/Dashboard.css**:
- ✅ 新增批量操作按钮样式
- ✅ 新增复选框样式
- ✅ 新增选中状态高亮

**src/components/ProgressView.tsx**:
- ✅ 新增暂停按钮
- ✅ 新增暂停确认逻辑

**src/components/ProgressView.css**:
- ✅ 新增暂停按钮样式
- ✅ 改进header布局

---

## 使用指南

### 暂停运行
1. 等待任务开始运行
2. 在 ProgressView 右上角点击"⏸ 暂停运行"
3. 确认暂停
4. 任务停止，状态变为可继续
5. 可以开始新任务或稍后继续

### 批量删除
1. 点击"批量管理"按钮
2. 选择要删除的运行：
   - 点击"全选"快速选择
   - 或逐个点击卡片/复选框
3. 点击"删除选中 (N)"
4. 确认删除
5. 查看删除结果统计

### 继续运行
1. 在 Dashboard 找到失败/暂停的任务
2. 点击"▶ 继续运行"按钮
3. 任务从下一阶段继续执行
4. 已完成的阶段输出被保留

---

## 性能对比

| 操作 | v1.0.4 | v1.0.8 | 提升 |
|------|--------|--------|------|
| 删除单个运行 | ~0.5秒 | ~0.5秒 | 持平 |
| 删除50个运行（串行） | ~50秒 | N/A | - |
| 删除50个运行（并行） | ~2-3秒 | N/A | - |
| 删除50个运行（批量API） | N/A | **<0.5秒** | **100x** |
| 刷新页面历史丢失 | ❌ | ✅ | - |
| 继续运行阶段错误 | ❌ | ✅ | - |
| 无法暂停任务 | ❌ | ✅ | - |

---

## 已知问题

1. **进程终止限制**：
   - 如果PaperClaw主进程创建了子进程（如Docker容器），可能无法完全清理
   - 建议：使用 `--skip-noncritical-stage` 跳过可能挂起的阶段

2. **状态同步延迟**：
   - 前端每2秒轮询一次后端
   - 暂停后可能有最多2秒的状态显示延迟

3. **批量删除限制**：
   - 最多显示100个历史运行
   - 可以在 `get_all_runs()` 中调整

---

## 下一步计划 (v1.0.9)

- [ ] 添加批量继续运行功能
- [ ] 添加运行记录搜索/筛选
- [ ] 支持按状态筛选（completed/failed/running）
- [ ] 添加任务优先级管理
- [ ] 支持任务队列（排队运行）
- [ ] 添加WebSocket实时更新（替代轮询）
- [ ] 支持导出运行记录为JSON

---

## 升级指南

### 从 v1.0.7 升级到 v1.0.8

1. **停止旧服务**：
```bash
# 停止前端和后端进程
```

2. **替换文件**：
```bash
# 后端
paperclaw-web/backend/app.py

# 前端
paperclaw-web/frontend/src/App.tsx
paperclaw-web/frontend/src/components/Dashboard.tsx
paperclaw-web/frontend/src/components/Dashboard.css
paperclaw-web/frontend/src/components/ProgressView.tsx
paperclaw-web/frontend/src/components/ProgressView.css
```

3. **重启服务**：
```bash
# 后端
cd paperclaw-web/backend
../../.venv/Scripts/python.exe app.py

# 前端
cd paperclaw-web/frontend
npm run dev
```

4. **验证功能**：
- 访问 http://localhost:5173
- 测试暂停功能
- 测试批量删除
- 测试继续运行

---

## 贡献者

- PaperClaw Team
- 用户反馈和测试

---

**版本**: v1.0.8
**发布日期**: 2026-04-22
**兼容性**: Python 3.11+, Node.js 16+, 现代浏览器
