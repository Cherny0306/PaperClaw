import React, { useState, useCallback } from 'react';
import './DataUpload.css';

interface DataUploadProps {
  onUploadComplete?: (datasetId: string) => void;
  onNextStep?: () => void;
}

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  message?: string;
  preview?: any[];
}

const SUPPORTED_FORMATS = ['.csv', '.xlsx', '.xls', '.json', '.geojson', '.tif', '.tiff', '.png', '.jpg'];

export const DataUpload: React.FC<DataUploadProps> = ({ onUploadComplete, onNextStep }) => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [dataType, setDataType] = useState<string>('training');

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  }, [dataType]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    handleFiles(files);
  }, [dataType]);

  const handleFiles = async (files: File[]) => {
    const newFiles: UploadedFile[] = files.map(file => ({
      id: `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      name: file.name,
      size: file.size,
      type: file.type || getFileType(file.name),
      status: 'pending' as const,
    }));

    setUploadedFiles(prev => [...prev, ...newFiles]);

    // Upload each file
    for (const file of newFiles) {
      await uploadFile(file);
    }
  };

  const uploadFile = async (file: UploadedFile) => {
    setUploadedFiles(prev =>
      prev.map(f => f.id === file.id ? { ...f, status: 'uploading' as const } : f)
    );

    try {
      const fileContent = await readFileAsBase64(file.name);
      const response = await fetch('http://localhost:5001/api/research/data/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_content: fileContent,
          filename: file.name,
          data_type: dataType,
        }),
      });

      const result = await response.json();

      if (result.success) {
        setUploadedFiles(prev =>
          prev.map(f => f.id === file.id ? {
            ...f,
            status: 'success' as const,
            preview: result.dataset.preview,
          } : f)
        );
        onUploadComplete?.(result.dataset_id);
      } else {
        setUploadedFiles(prev =>
          prev.map(f => f.id === file.id ? {
            ...f,
            status: 'error' as const,
            message: result.error,
          } : f)
        );
      }
    } catch (error) {
      setUploadedFiles(prev =>
        prev.map(f => f.id === file.id ? {
          ...f,
          status: 'error' as const,
          message: String(error),
        } : f)
      );
    }
  };

  const readFileAsBase64 = (filename: string): Promise<string> => {
    return new Promise((resolve, reject) => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = SUPPORTED_FORMATS.join(',');

      input.onchange = async (e: any) => {
        const file = e.target.files?.[0];
        if (!file) {
          reject(new Error('No file selected'));
          return;
        }

        const reader = new FileReader();
        reader.onload = () => {
          const result = reader.result as string;
          // Convert to base64 if not already
          if (result.startsWith('data:')) {
            resolve(result);
          } else {
            resolve(btoa(result));
          }
        };
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(file);
      };

      input.click();
    });
  };

  const getFileType = (filename: string): string => {
    const ext = filename.split('.').pop()?.toLowerCase();
    const typeMap: Record<string, string> = {
      csv: 'text/csv',
      xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      xls: 'application/vnd.ms-excel',
      json: 'application/json',
      geojson: 'application/geo+json',
      tif: 'image/tiff',
      tiff: 'image/tiff',
      png: 'image/png',
      jpg: 'image/jpeg',
    };
    return typeMap[ext || ''] || 'application/octet-stream';
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const removeFile = (fileId: string) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const successCount = uploadedFiles.filter(f => f.status === 'success').length;
  const hasSuccess = successCount > 0;

  return (
    <div className="data-upload-container">
      <div className="upload-header">
        <h2>数据上传</h2>
        <p>支持上传训练数据、验证数据、模型结果等多种格式</p>
      </div>

      <div className="upload-options">
        <label>数据类型:</label>
        <select value={dataType} onChange={(e) => setDataType(e.target.value)}>
          <option value="training">训练数据</option>
          <option value="validation">验证数据</option>
          <option value="results">模型结果</option>
          <option value="ground_truth">真值标注</option>
        </select>
      </div>

      <div
        className={`drop-zone ${dragActive ? 'drag-active' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          id="file-input"
          multiple
          accept={SUPPORTED_FORMATS.join(',')}
          onChange={handleFileSelect}
        />
        <label htmlFor="file-input" className="drop-zone-content">
          <div className="drop-icon">📁</div>
          <p className="drop-text">拖拽文件到此处或点击上传</p>
          <p className="drop-formats">
            支持格式: {SUPPORTED_FORMATS.join(', ')}
          </p>
        </label>
      </div>

      {uploadedFiles.length > 0 && (
        <div className="uploaded-files">
          <h3>已上传文件 ({successCount}/{uploadedFiles.length})</h3>
          <div className="file-list">
            {uploadedFiles.map((file) => (
              <div key={file.id} className={`file-item file-${file.status}`}>
                <div className="file-icon">
                  {getFileIcon(file.name)}
                </div>
                <div className="file-info">
                  <div className="file-name">{file.name}</div>
                  <div className="file-meta">
                    <span>{formatFileSize(file.size)}</span>
                    <span className="file-type">{file.type}</span>
                  </div>
                  {file.message && (
                    <div className="file-message">{file.message}</div>
                  )}
                </div>
                <div className="file-status">
                  {file.status === 'uploading' && <span className="status-uploading">⏳ 上传中</span>}
                  {file.status === 'success' && <span className="status-success">✓</span>}
                  {file.status === 'error' && <span className="status-error">✗</span>}
                  {file.status === 'pending' && <span className="status-pending">⏳</span>}
                </div>
                <button
                  className="file-remove"
                  onClick={() => removeFile(file.id)}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {uploadedFiles.length > 0 && hasSuccess && (
        <div className="data-preview">
          <h3>数据预览</h3>
          <div className="preview-content">
            {uploadedFiles
              .filter(f => f.status === 'success' && f.preview)
              .map(f => (
                <table key={f.id} className="preview-table">
                  <thead>
                    <tr>
                      {f.preview && f.preview[0] && Object.keys(f.preview[0]).map(key => (
                        <th key={key}>{key}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(f.preview || []).slice(0, 5).map((row: any, i: number) => (
                      <tr key={i}>
                        {Object.values(row).map((val: any, j: number) => (
                          <td key={j}>{String(val)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              ))}
          </div>
        </div>
      )}

      <div className="upload-actions">
        <button
          className="btn-primary"
          disabled={!hasSuccess}
          onClick={onNextStep}
        >
          下一步: 数据分析 →
        </button>
      </div>
    </div>
  );
};

const getFileIcon = (filename: string): string => {
  const ext = filename.split('.').pop()?.toLowerCase();
  const iconMap: Record<string, string> = {
    csv: '📄',
    xlsx: '📊',
    xls: '📊',
    json: '{ }',
    geojson: '🗺️',
    tif: '🖼️',
    tiff: '🖼️',
    png: '🖼️',
    jpg: '🖼️',
  };
  return iconMap[ext || ''] || '📄';
};

export default DataUpload;
