import { useState, useEffect } from 'react'
import './Dashboard.css'

interface RunStats {
  total_tokens: number
  prompt_tokens: number
  completion_tokens: number
  api_calls: number
  current_model: string
  estimated_cost: number
}

interface PipelineRun {
  run_id: string
  topic: string
  status: 'running' | 'completed' | 'failed'
  current_stage: number
  total_stages: number
  stage_name: string
  progress: number
  stats?: RunStats
}

interface DashboardProps {
  runs: PipelineRun[]
  onDeleteRun?: (runId: string) => void
  onDeleteMultiple?: (runIds: string[]) => void
  onResumeRun?: (runId: string) => void
}

export default function Dashboard({ runs, onDeleteRun, onDeleteMultiple, onResumeRun }: DashboardProps) {
  const [expandedRuns, setExpandedRuns] = useState<Set<string>>(new Set())
  const [runsStats, setRunsStats] = useState<Map<string, RunStats>>(new Map())
  const [resumingRun, setResumingRun] = useState<string | null>(null)
  const [selectedRuns, setSelectedRuns] = useState<Set<string>>(new Set())
  const [isBulkDelete, setIsBulkDelete] = useState(false)

  // 获取每个运行的统计信息
  useEffect(() => {
    runs.forEach(run => {
      if (run.status !== 'running') {
        fetchStats(run.run_id)
      }
    })
  }, [runs])

  const fetchStats = async (runId: string) => {
    try {
      const response = await fetch(`http://localhost:5001/api/stats/${runId}`)
      if (response.ok) {
        const data = await response.json()
        setRunsStats(prev => new Map(prev).set(runId, data))
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }

  const handleDelete = async (runId: string, e: React.MouseEvent) => {
    e.stopPropagation()

    // 确认对话框
    const confirmed = window.confirm(
      `确定要删除运行记录 ${runId} 吗？\n\n` +
      `此操作将删除：\n` +
      `- artifacts 目录下的所有文件\n` +
      `- 日志文件\n` +
      `- 所有阶段的输出\n\n` +
      `此操作不可撤销！`
    )

    if (!confirmed) {
      return
    }

    if (onDeleteRun) {
      await onDeleteRun(runId)
    }
  }

  const handleResume = async (runId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (onResumeRun) {
      setResumingRun(runId)
      try {
        await onResumeRun(runId)
      } finally {
        setResumingRun(null)
      }
    }
  }

  const toggleExpand = (runId: string) => {
    setExpandedRuns(prev => {
      const newSet = new Set(prev)
      if (newSet.has(runId)) {
        newSet.delete(runId)
      } else {
        newSet.add(runId)
        fetchStats(runId)
      }
      return newSet
    })
  }

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    return num.toString()
  }

  const formatCost = (cost: number) => {
    if (cost === 0) return '¥0.00'
    return `¥${cost.toFixed(4)}`
  }

  const getStats = (run: PipelineRun) => {
    return runsStats.get(run.run_id) || run.stats || {
      total_tokens: 0,
      prompt_tokens: 0,
      completion_tokens: 0,
      api_calls: 0,
      current_model: '-',
      estimated_cost: 0
    }
  }

  // 批量选择处理
  const toggleSelectRun = (runId: string) => {
    setSelectedRuns(prev => {
      const newSet = new Set(prev)
      if (newSet.has(runId)) {
        newSet.delete(runId)
      } else {
        newSet.add(runId)
      }
      return newSet
    })
  }

  const toggleSelectAll = () => {
    if (selectedRuns.size === runs.length) {
      // 如果已全选，则取消全选
      setSelectedRuns(new Set())
    } else {
      // 否则全选所有非运行中的任务
      const deletableRuns = runs.filter(r => r.status !== 'running').map(r => r.run_id)
      setSelectedRuns(new Set(deletableRuns))
    }
  }

  const handleBulkDelete = async () => {
    if (selectedRuns.size === 0) {
      return
    }

    const count = selectedRuns.size
    const confirmed = window.confirm(
      `确定要删除选中的 ${count} 个运行记录吗？\n\n` +
      `此操作将删除：\n` +
      `- artifacts 目录下的所有文件\n` +
      `- 日志文件\n` +
      `- 所有阶段的输出\n\n` +
      `此操作不可撤销！`
    )

    if (!confirmed) {
      return
    }

    if (onDeleteMultiple) {
      await onDeleteMultiple(Array.from(selectedRuns))
      setSelectedRuns(new Set())
      setIsBulkDelete(false)
    }
  }

  const isAllSelected = runs.length > 0 && selectedRuns.size === runs.filter(r => r.status !== 'running').length
  const hasSelection = selectedRuns.size > 0

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>Recent Runs</h2>
        <div className="bulk-actions">
          {!isBulkDelete ? (
            <button
              className="bulk-toggle-btn"
              onClick={() => setIsBulkDelete(true)}
              disabled={runs.length === 0}
            >
              ☰ 批量管理
            </button>
          ) : (
            <>
              <button
                className="select-all-btn"
                onClick={toggleSelectAll}
                disabled={runs.length === 0}
              >
                {isAllSelected ? '☑ 取消全选' : '☐ 全选'}
              </button>
              <button
                className="bulk-delete-btn"
                onClick={handleBulkDelete}
                disabled={!hasSelection}
                title={hasSelection ? `删除选中的 ${selectedRuns.size} 个运行` : '请先选择要删除的运行'}
              >
                🗑 删除选中 ({selectedRuns.size})
              </button>
              <button
                className="cancel-btn"
                onClick={() => {
                  setIsBulkDelete(false)
                  setSelectedRuns(new Set())
                }}
              >
                ✕ 取消
              </button>
            </>
          )}
        </div>
      </div>

      {runs.length === 0 ? (
        <p className="empty-state">No runs yet</p>
      ) : (
        <div className="runs-list">
          {runs.map((run) => {
            const stats = getStats(run)
            const isExpanded = expandedRuns.has(run.run_id)
            const isSelected = selectedRuns.has(run.run_id)
            const canDelete = run.status !== 'running'
            // 改进的继续运行判断逻辑：
            // 1. 不是running状态
            // 2. 不是completed状态（或者阶段未完成）
            // 3. 有已完成的阶段（current_stage > 0）
            const canResume = run.status !== 'running' &&
                             (run.status === 'failed' || run.current_stage < run.total_stages) &&
                             run.current_stage > 0
            const isResuming = resumingRun === run.run_id

            return (
              <div
                key={run.run_id}
                className={`run-card ${isExpanded ? 'expanded' : ''} ${isSelected ? 'selected' : ''} ${isBulkDelete ? 'bulk-mode' : ''}`}
                onClick={() => isBulkDelete && canDelete && toggleSelectRun(run.run_id)}
              >
                {/* 批量选择复选框 */}
                {isBulkDelete && (
                  <div className="checkbox-wrapper">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelectRun(run.run_id)}
                      disabled={!canDelete}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>
                )}

                {!isBulkDelete && (
                  <button
                    className="delete-btn"
                    onClick={(e) => handleDelete(run.run_id, e)}
                    title="Delete this run"
                  >
                    ✕
                  </button>
                )}

                <div className="run-header">
                  <span className={`status-badge ${run.status}`}>
                    {run.status === 'running' ? 'RUNNING' :
                     run.status === 'completed' ? 'COMPLETED' : 'FAILED'}
                  </span>
                  <span className="run-id">{run.run_id}</span>
                </div>

                <h3>{run.topic}</h3>

                <div className="run-progress">
                  <div className="progress-bar-mini" style={{ width: `${run.progress}%` }} />
                </div>

                <p className="run-stage">
                  Stage {run.current_stage}/{run.total_stages} - {run.stage_name}
                </p>

                {/* 可展开的统计信息 */}
                <div className={`run-stats ${isExpanded ? 'show' : ''}`}>
                  <div className="stats-grid">
                    <div className="stat-item">
                      <span className="stat-label">API Calls</span>
                      <span className="stat-value">{stats.api_calls}</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">Tokens</span>
                      <span className="stat-value">{formatNumber(stats.total_tokens)}</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">Cost</span>
                      <span className="stat-value stat-cost">{formatCost(stats.estimated_cost)}</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">Model</span>
                      <span className="stat-value stat-model">{stats.current_model}</span>
                    </div>
                  </div>
                </div>

                {/* 操作按钮 */}
                <div className="run-actions">
                  <button
                    className="expand-btn"
                    onClick={() => toggleExpand(run.run_id)}
                  >
                    {isExpanded ? '收起详情' : '查看详情'}
                  </button>
                  {canResume && (
                    <button
                      className="resume-btn"
                      onClick={(e) => handleResume(run.run_id, e)}
                      disabled={isResuming}
                      title={run.status === 'completed' ? '继续运行下一阶段' : '从断点继续运行'}
                    >
                      {isResuming ? '启动中...' : '▶ 继续运行'}
                    </button>
                  )}
                  {!canResume && run.status === 'running' && (
                    <span className="running-badge">运行中...</span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
