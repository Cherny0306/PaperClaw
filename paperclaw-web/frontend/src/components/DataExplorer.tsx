import React, { useState, useEffect } from 'react';
import './DataExplorer.css';

interface DataExplorerProps {
  datasetId: string;
  onAnalysisComplete?: () => void;
  onNextStep?: () => void;
}

interface StatsData {
  shape: { rows: number; cols: number };
  descriptive_stats: Record<string, any>;
  correlations: any[];
  outlier_count: number;
  column_types: Record<string, string>;
}

export const DataExplorer: React.FC<DataExplorerProps> = ({ datasetId, onAnalysisComplete, onNextStep }) => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'distribution' | 'correlation'>('overview');

  useEffect(() => {
    if (datasetId) {
      analyzeData();
    }
  }, [datasetId]);

  const analyzeData = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:5001/api/research/analyze/data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_id: datasetId }),
      });

      const result = await response.json();

      if (result.success) {
        setStats({
          shape: { rows: result.shape[0], cols: result.shape[1] },
          descriptive_stats: result.descriptive_stats,
          correlations: result.correlations || [],
          outlier_count: result.outlier_count,
          column_types: result.column_types,
        });
        onAnalysisComplete?.();
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="data-explorer loading">
        <div className="loading-spinner">⏳ 分析中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="data-explorer error">
        <div className="error-message">
          <h3>分析失败</h3>
          <p>{error}</p>
          <button onClick={analyzeData}>重试</button>
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="data-explorer empty">
        <p>暂无数据</p>
      </div>
    );
  }

  return (
    <div className="data-explorer-container">
      <div className="explorer-header">
        <h2>数据探索与分析</h2>
        <p>基于上传数据进行的统计分析结果</p>
      </div>

      <div className="explorer-tabs">
        <button
          className={activeTab === 'overview' ? 'active' : ''}
          onClick={() => setActiveTab('overview')}
        >
          统计概览
        </button>
        <button
          className={activeTab === 'distribution' ? 'active' : ''}
          onClick={() => setActiveTab('distribution')}
        >
          分布分析
        </button>
        <button
          className={activeTab === 'correlation' ? 'active' : ''}
          onClick={() => setActiveTab('correlation')}
        >
          相关性分析
        </button>
      </div>

      <div className="explorer-content">
        {activeTab === 'overview' && (
          <div className="tab-overview">
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-label">样本数</div>
                <div className="stat-value">{stats.shape.rows.toLocaleString()}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">特征数</div>
                <div className="stat-value">{stats.shape.cols}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">异常值</div>
                <div className="stat-value">{stats.outlier_count}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">显著相关</div>
                <div className="stat-value">{stats.correlations.length}</div>
              </div>
            </div>

            <div className="descriptive-stats">
              <h3>描述性统计</h3>
              <div className="stats-table-container">
                <table className="stats-table">
                  <thead>
                    <tr>
                      <th>指标</th>
                      <th>均值</th>
                      <th>中位数</th>
                      <th>标准差</th>
                      <th>最小值</th>
                      <th>最大值</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(stats.descriptive_stats).slice(0, 10).map(([col, s]: [string, any]) => (
                      <tr key={col}>
                        <td className="col-name">{col}</td>
                        <td>{s.mean?.toFixed(4) || '-'}</td>
                        <td>{s.median?.toFixed(4) || '-'}</td>
                        <td>{s.std?.toFixed(4) || '-'}</td>
                        <td>{s.min?.toFixed(4) || '-'}</td>
                        <td>{s.max?.toFixed(4) || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'distribution' && (
          <div className="tab-distribution">
            <div className="distribution-info">
              <h3>分布分析</h3>
              <p>查看各数值特征的分布情况，包括直方图和正态性检验</p>
            </div>
            <div className="distribution-placeholder">
              <div className="placeholder-chart">
                <span>📊</span>
                <p>直方图将在此处显示</p>
                <p className="hint">选择上方表格中的特征查看详细分布</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'correlation' && (
          <div className="tab-correlation">
            <h3>相关性分析</h3>
            {stats.correlations.length > 0 ? (
              <div className="correlation-list">
                {stats.correlations.map((corr: any, i: number) => (
                  <div key={i} className="correlation-item">
                    <div className="corr-pair">
                      <span className="var1">{corr.var1}</span>
                      <span className="connector">↔</span>
                      <span className="var2">{corr.var2}</span>
                    </div>
                    <div className="corr-value">
                      <span className={`corr-coef ${Math.abs(corr.correlation) > 0.7 ? 'strong' : ''}`}>
                        r = {corr.correlation.toFixed(4)}
                      </span>
                      <span className="corr-pvalue">p = {corr.p_value.toFixed(4)}</span>
                    </div>
                    <div className="corr-bar">
                      <div
                        className="corr-fill"
                        style={{ width: `${Math.abs(corr.correlation) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="no-correlations">
                <p>未发现显著相关性 (p &lt; 0.05)</p>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="explorer-actions">
        <button className="btn-secondary" onClick={analyzeData}>
          🔄 重新分析
        </button>
        <button className="btn-primary" onClick={onNextStep}>
          下一步: 生成假设 →
        </button>
      </div>
    </div>
  );
};

export default DataExplorer;
