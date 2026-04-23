import { useState, useEffect, useRef } from 'react'
import './StatsPanel.css'

interface ModelStats {
  total_tokens: number
  prompt_tokens: number
  completion_tokens: number
  api_calls: number
  current_model: string
  context_length: number
  tools_used: string[]
  estimated_cost: number
}

interface StatsPanelProps {
  runId: string | null
  isRunning: boolean
}

export default function StatsPanel({ runId, isRunning }: StatsPanelProps) {
  const [stats, setStats] = useState<ModelStats>({
    total_tokens: 0,
    prompt_tokens: 0,
    completion_tokens: 0,
    api_calls: 0,
    current_model: '-',
    context_length: 0,
    tools_used: [],
    estimated_cost: 0
  })
  const [position, setPosition] = useState({ x: 20, y: 100 })
  const [isDragging, setIsDragging] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(false)
  const dragRef = useRef<HTMLDivElement>(null)
  const dragOffset = useRef({ x: 0, y: 0 })

  // 获取统计数据
  useEffect(() => {
    if (!runId) return

    const fetchStats = async () => {
      try {
        const response = await fetch(`http://localhost:5001/api/stats/${runId}`)
        if (response.ok) {
          const data = await response.json()
          setStats(data)
        }
      } catch (error) {
        console.error('Failed to fetch stats:', error)
      }
    }

    fetchStats()
    const interval = setInterval(fetchStats, 2000)
    return () => clearInterval(interval)
  }, [runId])

  // 拖拽功能
  const handleMouseDown = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement
    if (target.closest('.stats-panel-header')) {
      setIsDragging(true)
      dragOffset.current = {
        x: e.clientX - position.x,
        y: e.clientY - position.y
      }
    }
  }

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging) {
        setPosition({
          x: e.clientX - dragOffset.current.x,
          y: e.clientY - dragOffset.current.y
        })
      }
    }

    const handleMouseUp = () => {
      setIsDragging(false)
    }

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging])

  // 格式化数字
  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    return num.toString()
  }

  // 格式化成本
  const formatCost = (cost: number) => {
    if (cost === 0) return '¥0.00'
    return `¥${cost.toFixed(4)}`
  }

  return (
    <div
      ref={dragRef}
      className={`stats-panel ${isCollapsed ? 'collapsed' : ''}`}
      style={{ left: `${position.x}px`, top: `${position.y}px` }}
      onMouseDown={handleMouseDown}
    >
      <div className="stats-panel-header">
        <span className="stats-panel-title">📊 模型统计</span>
        <div className="stats-panel-controls">
          <button
            className="stats-panel-btn"
            onClick={() => setIsCollapsed(!isCollapsed)}
            title={isCollapsed ? '展开' : '收起'}
          >
            {isCollapsed ? '◀' : '▶'}
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <div className="stats-panel-content">
          <div className="stats-section">
            <div className="stats-label">当前模型</div>
            <div className="stats-value stats-model">{stats.current_model}</div>
          </div>

          <div className="stats-section">
            <div className="stats-label">API 调用次数</div>
            <div className="stats-value">{stats.api_calls}</div>
          </div>

          <div className="stats-section">
            <div className="stats-label">上下文长度</div>
            <div className="stats-value">{formatNumber(stats.context_length)}</div>
          </div>

          <div className="stats-section stats-tokens">
            <div className="stats-label">Token 消耗</div>
            <div className="stats-tokens-grid">
              <div>
                <span className="stats-token-label">输入</span>
                <span className="stats-token-value">{formatNumber(stats.prompt_tokens)}</span>
              </div>
              <div>
                <span className="stats-token-label">输出</span>
                <span className="stats-token-value">{formatNumber(stats.completion_tokens)}</span>
              </div>
              <div>
                <span className="stats-token-label">总计</span>
                <span className="stats-token-value stats-total">{formatNumber(stats.total_tokens)}</span>
              </div>
            </div>
          </div>

          <div className="stats-section">
            <div className="stats-label">预估成本</div>
            <div className="stats-value stats-cost">{formatCost(stats.estimated_cost)}</div>
          </div>

          {stats.tools_used.length > 0 && (
            <div className="stats-section">
              <div className="stats-label">调用工具</div>
              <div className="stats-tools">
                {stats.tools_used.map((tool, index) => (
                  <span key={index} className="stats-tool-tag">{tool}</span>
                ))}
              </div>
            </div>
          )}

          {!isRunning && runId && (
            <div className="stats-status stats-stopped">运行已结束</div>
          )}
        </div>
      )}
    </div>
  )
}
