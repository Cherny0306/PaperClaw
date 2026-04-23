import { useState, useEffect } from 'react'
import './App.css'
import Dashboard from './components/Dashboard'
import RunControl from './components/RunControl'
import ProgressView from './components/ProgressView'
import ResultsView from './components/ResultsView'
import StatsPanel from './components/StatsPanel'
import ResearchMode from './pages/ResearchMode'

const VERSION = '1.0.8'

type AppMode = 'review' | 'research'

interface PipelineRun {
  run_id: string
  topic: string
  status: 'running' | 'completed' | 'failed'
  current_stage: number
  total_stages: number
  stage_name: string
  progress: number
}

function App() {
  const [currentRun, setCurrentRun] = useState<PipelineRun | null>(null)
  const [runs, setRuns] = useState<PipelineRun[]>([])
  const [activeTab, setActiveTab] = useState<'dashboard' | 'results'>('dashboard')
  const [appMode, setAppMode] = useState<AppMode>('review')

  const switchToReviewMode = () => setAppMode('review')
  const switchToResearchMode = () => setAppMode('research')

  // 删除运行记录
  const handleDeleteRun = async (runId: string) => {
    // 先调用后端 API 删除实际文件
    try {
      const response = await fetch(`http://localhost:5001/api/runs/${runId}`, {
        method: 'DELETE'
      })

      const data = await response.json()

      if (!response.ok) {
        // 处理错误情况
        if (data.is_running) {
          alert('无法删除正在运行的任务。请等待任务完成或先停止它。')
        } else {
          alert(`删除失败: ${data.error || '未知错误'}`)
        }
        return false
      }

      console.log(`[Delete] Successfully deleted run: ${runId}`)

      // 后端删除成功后，更新前端状态
      setRuns(prev => prev.filter(r => r.run_id !== runId))

      // 如果删除的是当前运行，清空 currentRun
      if (currentRun && currentRun.run_id === runId) {
        setCurrentRun(null)
      }

      // 清理 localStorage
      const savedRuns = localStorage.getItem('paperclaw_runs')
      if (savedRuns) {
        try {
          const parsedRuns = JSON.parse(savedRuns)
          const filteredRuns = parsedRuns.filter((r: PipelineRun) => r.run_id !== runId)
          localStorage.setItem('paperclaw_runs', JSON.stringify(filteredRuns))
          console.log(`[Delete] Updated localStorage, removed ${runId}`)
        } catch (e) {
          console.error('Failed to update saved runs:', e)
        }
      }

      return true
    } catch (error) {
      console.error('Failed to delete run files:', error)
      alert('删除失败，请检查后端服务是否正常运行')
      return false
    }
  }

  // 批量删除运行记录
  const handleDeleteMultiple = async (runIds: string[]) => {
    if (runIds.length === 0) {
      return
    }

    console.log(`[Bulk Delete] Deleting ${runIds.length} runs in single request...`)

    try {
      const response = await fetch('http://localhost:5001/api/runs/bulk-delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_ids: runIds })
      })

      const data = await response.json()

      if (!response.ok) {
        alert(`批量删除失败: ${data.error || '未知错误'}`)
        return
      }

      const { results } = data
      const successCount = results.success.length
      const failCount = results.failed.length
      const runningCount = results.running.length

      console.log(`[Bulk Delete] Completed: ${successCount} success, ${failCount} failed, ${runningCount} skipped`)

      // 更新前端状态 - 移除成功删除的运行
      setRuns(prev => prev.filter(r => !results.success.includes(r.run_id)))

      // 清理 localStorage
      const savedRuns = localStorage.getItem('paperclaw_runs')
      if (savedRuns) {
        try {
          const parsedRuns = JSON.parse(savedRuns)
          const filteredRuns = parsedRuns.filter((r: PipelineRun) => !results.success.includes(r.run_id))
          localStorage.setItem('paperclaw_runs', JSON.stringify(filteredRuns))
        } catch (e) {
          console.error('Failed to update saved runs:', e)
        }
      }

      // 显示结果
      if (failCount === 0 && runningCount === 0) {
        alert(`成功删除 ${successCount} 个运行记录`)
      } else if (successCount === 0) {
        const errors = results.failed.map((f: any) => `${f.run_id}: ${f.error}`)
        const running = results.running.join(', ')
        alert(`删除失败！\n\n失败: ${errors.join('\n')}\n\n跳过（正在运行）: ${running}`)
      } else {
        const errors = results.failed.map((f: any) => `${f.run_id}: ${f.error}`)
        const running = results.running.length > 0 ? `\n跳过（正在运行）: ${results.running.join(', ')}` : ''
        alert(`批量删除完成：\n成功: ${successCount} 个\n失败: ${failCount} 个\n跳过: ${runningCount} 个${running ? '\n' + running : ''}\n\n失败详情：\n${errors.join('\n')}`)
      }
    } catch (error) {
      console.error('Failed to bulk delete:', error)
      alert('批量删除失败，请检查后端服务是否正常运行')
    }
  }

  // 继续运行
  const handleResumeRun = async (runId: string) => {
    try {
      const response = await fetch(`http://localhost:5001/api/runs/${runId}/resume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      if (response.ok) {
        const data = await response.json()
        setCurrentRun(data.run)
        // 更新运行状态为 running
        setRuns(prev => prev.map(r =>
          r.run_id === runId
            ? { ...r, status: 'running' as const }
            : r
        ))
      } else {
        const error = await response.json()
        alert(`Failed to resume: ${error.error || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to resume run:', error)
      alert('Failed to resume. Please check if backend server is running.')
    }
  }

  // 暂停运行
  const handlePauseRun = async () => {
    if (!currentRun) {
      return
    }

    const confirmed = window.confirm(
      `确定要暂停运行 "${currentRun.run_id}" 吗？\n\n` +
      `暂停后：\n` +
      `- 当前进度会被保存\n` +
      `- 可以稍后继续执行\n` +
      `- 可以开始其他任务`
    )

    if (!confirmed) {
      return
    }

    try {
      const response = await fetch(`http://localhost:5001/api/runs/${currentRun.run_id}/stop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })

      if (response.ok) {
        const data = await response.json()
        console.log('[Pause] Run paused:', data)

        // 更新当前运行状态为 failed（可继续）
        setCurrentRun(prev => prev ? { ...prev, status: 'failed' as const } : null)

        // 更新 runs 列表
        setRuns(prev => prev.map(r =>
          r.run_id === currentRun.run_id
            ? { ...r, status: 'failed' as const }
            : r
        ))

        alert('任务已暂停，您可以稍后继续执行或开始新任务')
      } else {
        const error = await response.json()
        alert(`暂停失败: ${error.error || '未知错误'}`)
      }
    } catch (error) {
      console.error('Failed to pause run:', error)
      alert('暂停失败，请检查后端服务是否正常运行')
    }
  }

  // 从后端加载所有历史运行记录
  useEffect(() => {
    const fetchAllRuns = async () => {
      try {
        const response = await fetch('http://localhost:5001/api/runs')
        if (response.ok) {
          const data = await response.json()
          if (data.runs && data.runs.length > 0) {
            setRuns(data.runs)
            console.log(`[App] Loaded ${data.runs.length} runs from backend`)
          }
        }
      } catch (error) {
        console.error('Failed to fetch all runs:', error)
        // 如果后端不可用，尝试从localStorage加载
        const savedRuns = localStorage.getItem('paperclaw_runs')
        if (savedRuns) {
          try {
            const parsedRuns = JSON.parse(savedRuns)
            setRuns(parsedRuns)
            console.log('[App] Loaded runs from localStorage fallback')
          } catch (e) {
            console.error('Failed to parse saved runs:', e)
          }
        }
      }
    }

    fetchAllRuns()
  }, [])

  // 保存运行记录到 localStorage
  useEffect(() => {
    if (runs.length > 0) {
      localStorage.setItem('paperclaw_runs', JSON.stringify(runs.slice(0, 20)))
    }
  }, [runs])

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch('http://localhost:5001/api/status')
        const data = await response.json()

        // 更新当前运行
        if (data.current_run) {
          setCurrentRun(data.current_run)
        }

        // 后端现在会从artifacts扫描所有运行，直接使用后端返回的列表
        if (data.recent_runs && data.recent_runs.length > 0) {
          setRuns(data.recent_runs)
        }
      } catch (error) {
        console.error('Failed to fetch status:', error)
      }
    }

    fetchStatus()
    const interval = setInterval(fetchStatus, 2000) // 改为2秒轮询
    return () => clearInterval(interval)
  }, [])

  // Mode selection view
  if (appMode === 'research') {
    return (
      <div className="app">
        <ResearchMode onBack={switchToReviewMode} />
      </div>
    )
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="logo-section">
          <h1>PaperClaw</h1>
          <p className="subtitle">AI-Powered Research Automation Platform</p>
        </div>
        <nav className="nav-tabs">
          <button
            className={activeTab === 'dashboard' ? 'active' : ''}
            onClick={() => setActiveTab('dashboard')}
          >
            Dashboard
          </button>
          <button
            className={activeTab === 'results' ? 'active' : ''}
            onClick={() => setActiveTab('results')}
          >
            Results
          </button>
          <button
            className="mode-switch-btn"
            onClick={switchToResearchMode}
            title="Switch to Original Research Mode"
          >
            🔬 原创研究
          </button>
        </nav>
      </header>

      <main className="app-main">
        {activeTab === 'dashboard' ? (
          <>
            <RunControl onRunStart={setCurrentRun} />
            {currentRun && <ProgressView run={currentRun} onPause={handlePauseRun} />}
            <Dashboard
              runs={runs}
              onDeleteRun={handleDeleteRun}
              onDelete
}

export default App
