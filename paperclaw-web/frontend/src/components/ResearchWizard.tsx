import React, { useState } from 'react';
import DataUpload from './DataUpload';
import DataExplorer from './DataExplorer';
import AnalysisPanel from './AnalysisPanel';
import './ResearchWizard.css';

type Step = 'upload' | 'explore' | 'hypothesize' | 'experiment' | 'paper';

interface ResearchWizardProps {
  onComplete?: () => void;
}

export const ResearchWizard: React.FC<ResearchWizardProps> = ({ onComplete }) => {
  const [currentStep, setCurrentStep] = useState<Step>('upload');
  const [datasetId, setDatasetId] = useState<string | null>(null);

  const steps: { key: Step; label: string; icon: string }[] = [
    { key: 'upload', label: '数据上传', icon: '📁' },
    { key: 'explore', label: '数据分析', icon: '📊' },
    { key: 'hypothesize', label: '假设生成', icon: '💡' },
    { key: 'experiment', label: '实验设计', icon: '🔬' },
    { key: 'paper', label: '论文撰写', icon: '📝' },
  ];

  const currentStepIndex = steps.findIndex(s => s.key === currentStep);

  const handleUploadComplete = (id: string) => {
    setDatasetId(id);
    setCurrentStep('explore');
  };

  const handleNextStep = () => {
    const currentIndex = steps.findIndex(s => s.key === currentStep);
    if (currentIndex < steps.length - 1) {
      setCurrentStep(steps[currentIndex + 1].key);
    }
  };

  const handlePrevStep = () => {
    const currentIndex = steps.findIndex(s => s.key === currentStep);
    if (currentIndex > 0) {
      setCurrentStep(steps[currentIndex - 1].key);
    }
  };

  const renderStep = () => {
    switch (currentStep) {
      case 'upload':
        return (
          <DataUpload
            onUploadComplete={handleUploadComplete}
            onNextStep={handleNextStep}
          />
        );
      case 'explore':
        return datasetId ? (
          <DataExplorer
            datasetId={datasetId}
            onNextStep={handleNextStep}
          />
        ) : (
          <div className="wizard-empty">
            <p>请先上传数据</p>
            <button onClick={() => setCurrentStep('upload')}>返回上传</button>
          </div>
        );
      case 'hypothesize':
        return datasetId ? (
          <AnalysisPanel
            datasetId={datasetId}
            onNextStep={handleNextStep}
          />
        ) : (
          <div className="wizard-empty">
            <p>请先上传数据</p>
            <button onClick={() => setCurrentStep('upload')}>返回上传</button>
          </div>
        );
      case 'experiment':
        return (
          <div className="experiment-design">
            <h2>实验设计</h2>
            <p>配置实验参数和对照组设置</p>
            <div className="experiment-placeholder">
              <span>🔬</span>
              <p>实验设计界面开发中...</p>
            </div>
            <div className="wizard-actions">
              <button className="btn-secondary" onClick={handlePrevStep}>
                ← 上一步
              </button>
              <button className="btn-primary" onClick={handleNextStep}>
                下一步: 论文撰写 →
              </button>
            </div>
          </div>
        );
      case 'paper':
        return (
          <div className="paper-writing">
            <h2>论文撰写</h2>
            <p>生成IMRaD结构的研究论文</p>
            <div className="paper-placeholder">
              <span>📝</span>
              <p>论文生成功能开发中...</p>
              <button className="btn-primary" onClick={onComplete}>
                完成研究流程
              </button>
            </div>
            <div className="wizard-actions">
              <button className="btn-secondary" onClick={handlePrevStep}>
                ← 上一步
              </button>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="research-wizard">
      <div className="wizard-header">
        <h1>🔬 原创研究模式</h1>
        <p>基于自有数据的研究论文撰写</p>
      </div>

      <div className="wizard-progress">
        {steps.map((step, index) => (
          <div
            key={step.key}
            className={`progress-step ${
              index <= currentStepIndex ? 'active' : ''
            } ${index < currentStepIndex ? 'completed' : ''}`}
          >
            <div className="step-icon">{step.icon}</div>
            <div className="step-label">{step.label}</div>
            {index < steps.length - 1 && <div className="step-connector" />}
          </div>
        ))}
      </div>

      <div className="wizard-content">
        {renderStep()}
      </div>
    </div>
  );
};

export default ResearchWizard;
