import { useState } from 'react'
import './ProgressView.css'

interface PipelineRun {
  run_id: string
  topic: string
  status: 'running' | 'completed' | 'failed'
  current_stage: number
  total_stages: number
  stage_name: string
  progress: number
}

interface ProgressViewProps {
  run: PipelineRun
  onPause?: () => void
}

const STAGES = [
  'TOPIC_INIT', 'PROBLEM_DECOMPOSE', 'SEARCH_STRATEGY', 'LITERATURE_COLLECT',
  'LITERATURE_SCREEN', 'KNOWLEDGE_EXTRACT', 'SYNTHESIS', 'HYPOTHESIS_GEN',
  'EXPERIMENT_DESIGN', 'CODE_GENERATION', 'RESOURCE_PLANNING', 'EXPERIMENT_RUN',
  'ITERATIVE_REFINE', 'RESULT_ANALYSIS', 'RESEARCH_DECISION', 'PAPER_OUTLINE',
  'PAPER_DRAFT', 'PEER_REVIEW', 'PAPER_REVISION', 'QUALITY_GATE',
  'KNOWLEDGE_ARCHIVE', 'EXPORT_PUBLISH', 'CITATION_VERIFY'
]

// Stage descriptions
const STAGE_DESCRIPTIONS: Record<string, string> = {
  TOPIC_INIT: '初始化研究主题，收集用户需求和硬件配置信息',
  PROBLEM_DECOMPOSE: '将研究问题分解为可管理的子问题树',
  SEARCH_STRATEGY: '制定文献搜索策略，确定关键词和数据源',
  LITERATURE_COLLECT: '收集相关文献和参考资料',
  LITERATURE_SCREEN: '筛选高质量的文献',
  KNOWLEDGE_EXTRACT: '从文献中提取关键知识卡片',
  SYNTHESIS: '综合分析现有研究，识别研究差距',
  HYPOTHESIS_GEN: '生成研究假设和创新点',
  EXPERIMENT_DESIGN: '设计实验方案和验证计划',
  CODE_GENERATION: '生成实验代码',
  RESOURCE_PLANNING: '规划计算资源和时间预算',
  EXPERIMENT_RUN: '在 Docker 容器中执行实验',
  ITERATIVE_REFINE: '迭代优化实验结果',
  RESULT_ANALYSIS: '分析实验结果和性能指标',
  RESEARCH_DECISION: '做出研究决策，确定下一步方向',
  PAPER_OUTLINE: '制定论文大纲结构',
  PAPER_DRAFT: '撰写论文初稿',
  PEER_REVIEW: '进行同行评审',
  PAPER_REVISION: '根据反馈修订论文',
  QUALITY_GATE: '质量检查关口',
  KNOWLEDGE_ARCHIVE: '归档研究成果到知识库',
  EXPORT_PUBLISH: '导出并准备发布',
  CITATION_VERIFY: '验证引用格式和完整性'
}

export default function ProgressView({ run, onPause }: ProgressViewProps) {
  const [selectedStage, setSelectedStage] = useState<number | null>(null)
  const [stageLog, setStageLog] = useState<string>('')
  const [loadingLog, setLoadingLog] = useState(false)
  const [expandedStage, setExpandedStage] = useState<number | null>(null)

  const handlePause = () => {
    if (onPause) {
      onPause()
    }
  }

  const statusText = run.status === 'running' ? 'RUNNING' : run.status === 'completed' ? 'COMPLETED' : 'FAILED'
  const statusClass = run.status === 'running' ? 'status-running' : run.status === 'completed' ? 'status-completed' : 'status-failed'

  // 加载指定阶段的日志
  const loadStageLog = async (stageNum: number) => {
    setLoadingLog(true)
    setSelectedStage(stageNum)
    try {
      // 从后端API获取日志
      const response = await fetch(`http://localhost:5001/api/logs/${run.run_id}/${stageNum}`)
      if (response.ok) {
        const data = await response.json()
        setStageLog(data.log || '暂无日志内容')
      } else {
        // 如果API不可用，显示模拟数据
        setStageLog(`[Stage ${stageNum}] ${STAGES[stageNum - 1]}\n\n状态: ${stageNum < run.current_stage ? '已完成' : stageNum === run.current_stage ? '运行中' : '等待中'}\n\n${STAGE_DESCRIPTIONS[STAGES[stageNum - 1]] || '暂无描述'}\n\n---\n提示: 后端日志API正在开发中，当前显示为示例内容。`)
      }
    } catch (error) {
      setStageLog(`[Stage ${stageNum}] ${STAGES[stageNum - 1]}\n\n状态: ${stageNum < run.current_stage ? '已完成' : stageNum === run.current_stage ? '运行中' : '等待中'}\n\n${STAGE_DESCRIPTIONS[STAGES[stageNum - 1]] || '暂无描述'}\n\n---\n提示: 无法连接到后端日志服务`)
    }
    setLoadingLog(false)
  }

  // 点击阶段卡片
  const handleStageClick = (stageNum: number) => {
    if (expandedStage === stageNum) {
      setExpandedStage(null)
    } else {
      setExpandedStage(stageNum)
      loadStageLog(stageNum)
    }
  }

  // 关闭详情弹窗
  const closeDetail = () => {
    setSelectedStage(null)
  }

  // 点击遮罩层关闭
  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      closeDetail()
    }
  }

  return (
    <div className="progress-view">
      <div className="progress-header">
        <div className="header-left">
          <h2>
            <span className={`status-badge ${statusClass}`}>{statusText}</span>
          </h2>
          <p className="run-id">Run ID: {run.run_id}</p>
          <p className="topic">Topic: {run.topic}</p>
        </div>
        {run.status === 'running' && onPause && (
          <button className="pause-btn" onClick={handlePause} title="暂停运行">
            ⏸ 暂停运行
          </button>
        )}
      </div>

      <div className="progress-bar-container">
        <div className="progress-bar" style={{ width: `${run.progress}%` }}>
          <span className="progress-text">{Math.round(run.progress)}%</span>
        </div>
      </div>

      <div className="stage-info">
        <p>Current Stage: <strong>{run.current_stage}/{run.total_stages}</strong> - {run.stage_name}</p>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
          点击下方阶段卡片可查看详细日志
        </p>
      </div>

      <div className="stages-grid">
        {STAGES.map((stage, index) => {
          const stageNum = index + 1
          const isCompleted = stageNum < run.current_stage
          const isCurrent = stageNum === run.current_stage
          const isPending = stageNum > run.current_stage
          const isExpanded = expandedStage === stageNum

          return (
            <div
              key={stage}
              className={`stage-item ${isCompleted ? 'completed' : ''} ${isCurrent ? 'current' : ''} ${isPending ? 'pending' : ''} ${isExpanded ? 'expanded' : ''}`}
              onClick={() => handleStageClick(stageNum)}
            >
              <div className="stage-number">{stageNum}</div>
              <div className="stage-name">{stage}</div>
            </div>
          )
        })}
      </div>

      {/* Stage Detail Modal */}
      {selectedStage && (
        <div className="stage-detail-overlay" onClick={handleOverlayClick}>
          <div className="stage-detail-modal">
            <div className="stage-detail-header">
              <h3>
                Stage {selectedStage}: {STAGES[selectedStage - 1]}
              </h3>
              <button className="stage-detail-close" onClick={closeDetail}>×</button>
            </div>
            <div className="stage-detail-content">
              {loadingLog ? (
                <div className="stage-detail-empty">Loading...</div>
              ) : (
                <>
                  <div className="stage-description">
                    {STAGE_DESCRIPTIONS[STAGES[selectedStage - 1]]}
                  </div>
                  <div className="stage-detail-log">
                    {stageLog || '暂无日志内容'}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
