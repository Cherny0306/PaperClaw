import React, { useState, useEffect } from 'react';
import './AnalysisPanel.css';

interface AnalysisPanelProps {
  datasetId: string;
  onNextStep?: () => void;
}

interface Hypothesis {
  id: string;
  question: string;
  null_hypothesis: string;
  alternative_hypothesis: string;
  test_method: string;
  novelty_score: number;
  feasibility_score: number;
}

interface Pattern {
  id: string;
  type: string;
  description: string;
  significance: number;
}

export const AnalysisPanel: React.FC<AnalysisPanelProps> = ({ datasetId, onNextStep }) => {
  const [loading, setLoading] = useState(true);
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [selectedHypotheses, setSelectedHypotheses] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (datasetId) {
      generateHypotheses();
    }
  }, [datasetId]);

  const generateHypotheses = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:5001/api/research/hypotheses/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dataset_id: datasetId,
          domain: 'remote_sensing',
        }),
      });

      const result = await response.json();

      if (result.success) {
        setPatterns(result.patterns || []);
        setHypotheses(result.hypotheses || []);
        // Select first two by default
        setSelectedHypotheses(new Set(result.hypotheses?.slice(0, 2).map((h: Hypothesis) => h.id) || []));
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  const toggleHypothesis = (id: string) => {
    setSelectedHypotheses(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const renderStars = (score: number): string => {
    const stars = Math.ceil(score * 5);
    return '⭐'.repeat(stars);
  };

  if (loading) {
    return (
      <div className="analysis-panel loading">
        <div className="loading-spinner">🔬 正在生成假设...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="analysis-panel error">
        <div className="error-message">
          <h3>假设生成失败</h3>
          <p>{error}</p>
          <button onClick={generateHypotheses}>重试</button>
        </div>
      </div>
    );
  }

  return (
    <div className="analysis-panel-container">
      <div className="panel-header">
        <h2>研究假设</h2>
        <p>基于数据分析发现的规律，生成可验证的研究假设</p>
      </div>

      <div className="patterns-section">
        <h3>发现的数据规律</h3>
        <div className="patterns-list">
          {patterns.length > 0 ? patterns.map((pattern: Pattern) => (
            <div key={pattern.id} className="pattern-item">
              <span className="pattern-icon">
                {pattern.significance > 0.8 ? '🟢' : pattern.significance > 0.5 ? '🟡' : '🔴'}
              </span>
              <span className="pattern-desc">{pattern.description}</span>
            </div>
          )) : (
            <div className="no-patterns">
              <p>未发现显著的数据规律</p>
            </div>
          )}
        </div>
      </div>

      <div className="hypotheses-section">
        <h3>生成的研究假设</h3>
        <div className="hypotheses-list">
          {hypotheses.map((h: Hypothesis) => (
            <div
              key={h.id}
              className={`hypothesis-item ${selectedHypotheses.has(h.id) ? 'selected' : ''}`}
              onClick={() => toggleHypothesis(h.id)}
            >
              <div className="hypothesis-header">
                <input
                  type="checkbox"
                  checked={selectedHypotheses.has(h.id)}
                  onChange={() => {}}
                />
                <span className="hypothesis-id">H{h.id.replace('h_', '')}</span>
              </div>
              <div className="hypothesis-question">{h.question}</div>
              <div className="hypothesis-details">
                <span className="detail-item">
                  <strong>H₀:</strong> {h.null_hypothesis}
                </span>
                <span className="detail-item">
                  <strong>检验方法:</strong> {h.test_method}
                </span>
              </div>
              <div className="hypothesis-scores">
                <span className="score-item">
                  {renderStars(h.novelty_score)} 创新性
                </span>
                <span className="score-item">
                  {renderStars(h.feasibility_score)} 可行性
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="panel-actions">
        <button className="btn-secondary" onClick={generateHypotheses}>
          🔄 重新生成
        </button>
        <button
          className="btn-primary"
          disabled={selectedHypotheses.size === 0}
          onClick={onNextStep}
        >
          下一步: 设计实验 →
        </button>
      </div>
    </div>
  );
};

export default AnalysisPanel;
