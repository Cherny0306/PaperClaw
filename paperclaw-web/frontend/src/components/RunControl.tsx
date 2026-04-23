import { useState, useEffect } from 'react'
import './RunControl.css'

interface RunControlProps {
  onRunStart: (run: any) => void
}

// Provider configurations with available models
const PROVIDERS = [
  {
    value: 'deepseek',
    label: 'DeepSeek',
    needsKey: true,
    needsBaseUrl: false,
    models: [
      { value: 'deepseek-chat', label: 'DeepSeek-V3 (推荐)' },
      { value: 'deepseek-coder', label: 'DeepSeek-Coder' },
    ]
  },
  {
    value: 'openai',
    label: 'OpenAI',
    needsKey: true,
    needsBaseUrl: false,
    models: [
      { value: 'gpt-4o', label: 'GPT-4o (推荐)' },
      { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
      { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
      { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
    ]
  },
  {
    value: 'anthropic',
    label: 'Anthropic Claude',
    needsKey: true,
    needsBaseUrl: false,
    models: [
      { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet (推荐)' },
      { value: 'claude-3-5-haiku-20241022', label: 'Claude 3.5 Haiku' },
      { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus' },
    ]
  },
  {
    value: 'openrouter',
    label: 'OpenRouter (200+ Models)',
    needsKey: true,
    needsBaseUrl: false,
    models: [
      { value: 'anthropic/claude-3.5-sonnet', label: 'Claude 3.5 Sonnet (推荐)' },
      { value: 'openai/gpt-4o', label: 'GPT-4o' },
      { value: 'google/gemini-pro-1.5', label: 'Gemini Pro 1.5' },
      { value: 'deepseek/deepseek-chat', label: 'DeepSeek V3' },
    ]
  },
  {
    value: 'novita',
    label: 'Novita AI',
    needsKey: true,
    needsBaseUrl: false,
    models: [
      { value: 'anthropic/claude-3.5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
      { value: 'openai/gpt-4o', label: 'GPT-4o' },
    ]
  },
  {
    value: 'qwen',
    label: '通义千问 (阿里云)',
    needsKey: true,
    needsBaseUrl: false,
    models: [
      { value: 'qwen-plus', label: 'Qwen-Plus (推荐)' },
      { value: 'qwen-turbo', label: 'Qwen-Turbo' },
      { value: 'qwen-max', label: 'Qwen-Max' },
    ]
  },
  {
    value: 'zhipu',
    label: '智谱AI (GLM)',
    needsKey: true,
    needsBaseUrl: false,
    models: [
      { value: 'glm-4-plus', label: 'GLM-4-Plus (推荐)' },
      { value: 'glm-4-flash', label: 'GLM-4-Flash' },
      { value: 'glm-4-air', label: 'GLM-4-Air' },
      { value: 'glm-4-0520', label: 'GLM-4-0520' },
    ]
  },
  {
    value: 'ernie',
    label: '文心一言 (百度)',
    needsKey: true,
    needsBaseUrl: false,
    models: [
      { value: 'ernie-4.0-8k', label: 'ERNIE 4.0 8K' },
      { value: 'ernie-3.5-8k', label: 'ERNIE 3.5 8K' },
      { value: 'ernie-speed', label: 'ERNIE Speed' },
    ]
  },
  {
    value: 'hunyuan',
    label: '腾讯混元',
    needsKey: true,
    needsBaseUrl: false,
    models: [
      { value: 'hunyuan-pro', label: 'Hunyuan Pro (推荐)' },
      { value: 'hunyuan-standard', label: 'Hunyuan Standard' },
      { value: 'hunyuan-lite', label: 'Hunyuan Lite' },
    ]
  },
  {
    value: 'baichuan',
    label: '百川智能',
    needsKey: true,
    needsBaseUrl: false,
    models: [
      { value: 'baichuan4', label: 'Baichuan 4' },
    ]
  },
  {
    value: 'moonshot',
    label: 'Moonshot AI (Kimi)',
    needsKey: true,
    needsBaseUrl: false,
    models: [
      { value: 'moonshot-v1-8k', label: 'Moonshot V1 8K' },
      { value: 'moonshot-v1-32k', label: 'Moonshot V1 32K' },
    ]
  },
  {
    value: 'custom',
    label: '自定义端点 (OpenAI兼容)',
    needsKey: true,
    needsBaseUrl: true,
    models: [
      { value: 'gpt-4o', label: 'GPT-4o (默认)' },
      { value: 'custom-model', label: '自定义模型' },
    ]
  },
]

// Stage skip options (使用阶段名称)
const STAGE_OPTIONS = [
  { value: 'TOPIC_INIT', label: 'Stage 1: 从头开始 (TOPIC_INIT)', description: '包含文献搜索' },
  { value: 'LITERATURE_SCREEN', label: 'Stage 5: 跳过搜索 (LITERATURE_SCREEN)', description: '使用本地文献库' },
  { value: 'SYNTHESIS', label: 'Stage 7: 跳过文献研究 (SYNTHESIS)', description: '跳过全部文献阶段' },
  { value: 'EXPERIMENT_DESIGN', label: 'Stage 9: 仅实验 (EXPERIMENT_DESIGN)', description: '仅保留实验设计' },
]

export default function RunControl({ onRunStart }: RunControlProps) {
  const [topic, setTopic] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [provider, setProvider] = useState('zhipu')
  const [model, setModel] = useState('glm-4-plus')
  const [customBaseUrl, setCustomBaseUrl] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [fromStage, setFromStage] = useState('TOPIC_INIT')

  // 获取当前provider的可用模型
  const currentProvider = PROVIDERS.find(p => p.value === provider) || PROVIDERS[0]
  const availableModels = currentProvider.models || []

  // 从localStorage加载保存的配置
  useEffect(() => {
    const savedApiKey = localStorage.getItem('paperclaw_api_key')
    const savedProvider = localStorage.getItem('paperclaw_provider')
    const savedModel = localStorage.getItem('paperclaw_model')
    const savedBaseUrl = localStorage.getItem('paperclaw_base_url')
    if (savedApiKey) setApiKey(savedApiKey)
    if (savedProvider) {
      setProvider(savedProvider)
      // 检查保存的模型是否在当前provider的可用模型中
      const providerModels = PROVIDERS.find(p => p.value === savedProvider)?.models || []
      if (savedModel && providerModels.some((m: any) => m.value === savedModel)) {
        setModel(savedModel)
      } else if (providerModels.length > 0) {
        setModel(providerModels[0].value)
      }
    }
    if (savedBaseUrl) setCustomBaseUrl(savedBaseUrl)
  }, [])

  // 保存API Key到localStorage
  const handleApiKeyChange = (value: string) => {
    setApiKey(value)
    localStorage.setItem('paperclaw_api_key', value)
  }

  // 保存Provider到localStorage并更新模型
  const handleProviderChange = (value: string) => {
    setProvider(value)
    localStorage.setItem('paperclaw_provider', value)

    // 更新为该provider的第一个模型
    const newProviderModels = PROVIDERS.find(p => p.value === value)?.models || []
    if (newProviderModels.length > 0) {
      const firstModel = newProviderModels[0].value
      setModel(firstModel)
      localStorage.setItem('paperclaw_model', firstModel)
    }
  }

  // 保存模型到localStorage
  const handleModelChange = (value: string) => {
    setModel(value)
    localStorage.setItem('paperclaw_model', value)
  }

  // 保存自定义BaseUrl到localStorage
  const handleBaseUrlChange = (value: string) => {
    setCustomBaseUrl(value)
    localStorage.setItem('paperclaw_base_url', value)
  }

  const handleStart = async () => {
    if (!topic || !apiKey) {
      alert('Please enter research topic and API Key')
      return
    }

    if (provider === 'custom' && !customBaseUrl) {
      alert('Please enter custom API base URL')
      return
    }

    setIsRunning(true)
    try {
      const response = await fetch('http://localhost:5001/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic,
          api_key: apiKey,
          provider,
          model,
          base_url: provider === 'custom' ? customBaseUrl : undefined,
          from_stage: fromStage !== 'TOPIC_INIT' ? fromStage : undefined
        })
      })
      const data = await response.json()
      onRunStart(data.run)
    } catch (error) {
      console.error('Failed to start run:', error)
      alert('Failed to start. Please check if backend server is running.')
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <div className="run-control">
      <h2>Start New Research</h2>
      <div className="form-group">
        <label>Research Topic</label>
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g., LLM applications in code generation"
          disabled={isRunning}
        />
      </div>
      <div className="form-group">
        <label>LLM Provider</label>
        <select value={provider} onChange={(e) => handleProviderChange(e.target.value)} disabled={isRunning}>
          {PROVIDERS.map(p => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
      </div>

      {/* 模型选择下拉菜单 */}
      <div className="form-group">
        <label>Model</label>
        <select value={model} onChange={(e) => handleModelChange(e.target.value)} disabled={isRunning}>
          {availableModels.map(m => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>
      </div>

      {currentProvider.needsBaseUrl && (
        <div className="form-group">
          <label>Custom API Base URL</label>
          <input
            type="text"
            value={customBaseUrl}
            onChange={(e) => handleBaseUrlChange(e.target.value)}
            placeholder="https://api.example.com/v1"
            disabled={isRunning}
          />
          <small style={{ color: '#888', fontSize: '12px' }}>
            支持 OpenAI 兼容接口 (Ollama, LM Studio, vLLM 等)
          </small>
        </div>
      )}
      <div className="form-group">
        <label>Start From Stage (跳过联网搜索)</label>
        <select value={fromStage} onChange={(e) => setFromStage(e.target.value)} disabled={isRunning}>
          {STAGE_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        <small style={{ color: '#888', fontSize: '12px' }}>
          {STAGE_OPTIONS.find(opt => opt.value === fromStage)?.description}
        </small>
      </div>
      <div className="form-group">
        <label>API Key (Auto-saved)</label>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => handleApiKeyChange(e.target.value)}
          placeholder="sk-..."
          disabled={isRunning}
        />
      </div>
      <button
        className="start-button"
        onClick={handleStart}
        disabled={isRunning}
      >
        {isRunning ? 'Starting...' : 'Start Research'}
      </button>
    </div>
  )
}
