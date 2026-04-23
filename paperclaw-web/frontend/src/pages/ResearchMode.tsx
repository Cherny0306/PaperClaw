import React, { useState } from 'react';
import ResearchWizard from '../components/ResearchWizard';
import './ResearchMode.css';

interface ResearchModeProps {
  onBack?: () => void;
}

export const ResearchMode: React.FC<ResearchModeProps> = ({ onBack }) => {
  const [isComplete, setIsComplete] = useState(false);

  const handleComplete = () => {
    setIsComplete(true);
  };

  const handleBack = () => {
    if (onBack) {
      onBack();
    } else {
      setIsComplete(false);
    }
  };

  if (isComplete) {
    return (
      <div className="research-mode-complete">
        <div className="completion-card">
          <div className="completion-icon">🎉</div>
          <h2>研究流程完成!</h2>
          <p>您的原创研究论文已经生成完成</p>
          <div className="completion-actions">
            <button className="btn-secondary" onClick={() => setIsComplete(false)}>
              继续修改
            </button>
            <button className="btn-primary" onClick={handleBack}>
              返回主页
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="research-mode">
      <div className="mode-header">
        <button className="back-button" onClick={handleBack}>
          ← 返回
        </button>
        <div className="header-title">
          <h1>PaperClaw</h1>
          <span className="mode-badge">原创研究模式</span>
        </div>
      </div>
      <ResearchWizard onComplete={handleComplete} />
    </div>
  );
};

export default ResearchMode;
